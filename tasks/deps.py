import re

from invoke import Context, Exit, task

from tasks.shared.rust import PUP_NIGHTLY, PUP_VERSION
from tasks.shared.targets import TARGETS

_CROSS_TARGETS = tuple(triple for triple, _ in TARGETS)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


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
