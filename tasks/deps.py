import re
from pathlib import Path

from invoke import Context, Exit, task

from tasks.shared.rust import PUP_NIGHTLY, PUP_VERSION
from tasks.shared.targets import TARGETS

_CROSS_TARGETS = tuple(triple for triple, _ in TARGETS)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

_CLAUDE_NPM_TOOL = "npm:@anthropic-ai/claude-code"


@task
def install_python(context: Context) -> None:
    """Install all Python dependencies."""
    context.run("uv sync --all-groups --frozen")


@task
def install_rust_targets(context: Context) -> None:
    """Install the Rust cross-compile targets needed for release builds."""
    context.run(f"rustup target add {' '.join(_CROSS_TARGETS)}")


@task
def install_zigbuild(context: Context) -> None:
    """Provision the zig + cargo-zigbuild cross-compile toolchain.

    Verifies the uv-managed ziglang and cargo-zigbuild are usable, then adds the
    rustup cross-targets.
    """
    checks = (
        ('uv run python -c "import ziglang"', "ziglang is not importable"),
        ("uv run cargo-zigbuild --version", "cargo-zigbuild is not runnable"),
    )
    for command, message in checks:
        if context.run(command, warn=True, pty=False).exited != 0:
            raise Exit(f"deps:install:zigbuild: {message}", code=1)
    install_rust_targets(context)


@task
def install_claude_native(context: Context) -> None:
    """Fetch the platform-native Claude Code binary the npm shim bootstraps.

    mise's npm backend installs the pinned @anthropic-ai/claude-code with
    --ignore-scripts, so the postinstall that downloads the platform-native
    binary never runs and the `claude` shim errors. This runs that postinstall
    against the mise-managed install — the same rustup-provisions-cargo-pup
    pattern for a tool mise cannot pin end-to-end. Idempotent: skipped when
    `claude` already works.
    """
    if _claude_runs(context):
        return
    where = context.run(
        f"mise where {_CLAUDE_NPM_TOOL}", warn=True, pty=False, hide=True
    )
    if where.exited != 0:
        raise Exit(
            "deps:install:claude-native: the pinned claude npm tool is not "
            "installed — run `mise install` first",
            code=1,
        )
    install_script = (
        Path(where.stdout.strip())
        / "lib/node_modules/@anthropic-ai/claude-code/install.cjs"
    )
    if not install_script.is_file():
        raise Exit(
            f"deps:install:claude-native: postinstall script not found at "
            f"{install_script}",
            code=1,
        )
    with context.cd(str(install_script.parent)):
        context.run("node install.cjs", warn=True, pty=False)
    if not _claude_runs(context):
        raise Exit(
            "deps:install:claude-native: failed to provision the native "
            "claude binary",
            code=1,
        )


def _claude_runs(context: Context) -> bool:
    return (
        context.run("claude --version", warn=True, pty=False, hide=True).exited
        == 0
    )


@task
def install_rust_components(context: Context) -> None:
    """Install the rustfmt, clippy, and llvm-tools-preview components.

    Provisioned explicitly rather than via mise's [tools] `components` field,
    which is silently skipped when the toolchain is already present. Installing
    llvm-tools-preview here also stops the parallel coverage tasks racing on
    `cargo llvm-cov`'s implicit `rustup component add`.
    """
    context.run("rustup component add rustfmt clippy llvm-tools-preview")


def _pup_already_installed(context: Context) -> bool:
    # Token match, not substring: "0.1.8" must not match "0.1.80". cargo-pup
    # colourises even when piped, so strip ANSI before splitting into tokens.
    probe = context.run(
        f"cargo +{PUP_NIGHTLY} pup --version", warn=True, pty=False
    )
    return PUP_VERSION in _ANSI.sub("", probe.stdout).split()


@task
def install_pup(context: Context) -> None:
    """Provision the cargo-pup nightly toolchain + the pinned cargo-pup.

    The nightly is rustup-managed (not a mise [tool]) and invoked via
    `cargo +<nightly>`. Idempotent, so it is cheap to run ahead of pup:check.
    """
    nightly = context.run(
        f"rustup toolchain install {PUP_NIGHTLY} --profile minimal "
        "--component rustc-dev --component rust-src "
        "--component llvm-tools-preview",
        warn=True,
        pty=False,
    )
    if nightly.exited != 0:
        raise Exit(
            f"failed to install {PUP_NIGHTLY} (GC'd from static.rust-lang.org?)"
            " — bump PUP_NIGHTLY + PUP_VERSION together to a compatible pair",
            code=1,
        )

    # Guard the multi-minute source build: `cargo install --locked` is not a
    # pure no-op (it resolves and can rebuild/hit the network).
    if not _pup_already_installed(context):
        install = context.run(
            f"cargo +{PUP_NIGHTLY} install cargo_pup "
            f"--version {PUP_VERSION} --locked",
            warn=True,
            pty=False,
        )
        if install.exited != 0:
            raise Exit(f"failed to install cargo-pup {PUP_VERSION}", code=1)

    # Confirm the `+toolchain` override resolves here rather than as an opaque
    # rustc_private load error inside pup:check.
    preflight = context.run(
        f"cargo +{PUP_NIGHTLY} --version", warn=True, pty=False
    )
    if preflight.exited != 0:
        raise Exit(
            f"`cargo +{PUP_NIGHTLY}` does not resolve — is ~/.cargo/bin "
            "(rustup's proxies) on PATH ahead of any cargo shim?",
            code=1,
        )
