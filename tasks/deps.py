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

    ziglang and cargo-zigbuild are uv-managed build-group deps (pinned in
    pyproject.toml, frozen in uv.lock); this verifies both are usable and adds
    the rustup cross-targets, so the four-triple `build:release` has everything
    the cross-compile needs. Mirrors deps:install:rust-targets.
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

    Not trusted to mise's [tools] rust `components` field: that is silently
    skipped when the toolchain is already present (a cached/pre-installed
    stable on a CI runner), so the components must be provisioned explicitly —
    mirroring deps:install:rust-targets and deps:install:pup. Adds to the
    active (RUSTUP_TOOLCHAIN-pinned) toolchain, the one launcher:check runs
    against.

    llvm-tools-preview is included so the coverage test tasks do not each
    trigger `cargo llvm-cov`'s implicit `rustup component add` at runtime —
    two such installs racing on ~/.rustup fails the parallel test:unit roll-up.
    """
    context.run("rustup component add rustfmt clippy llvm-tools-preview")


def _pup_already_installed(context: Context) -> bool:
    # Token equality on the version line, not a substring match (0.1.80 would
    # false-match 0.1.8) and not a whole-line match (cargo-pup colourises its
    # output even when piped, so anchored matching is brittle). Strip ANSI,
    # then split: "cargo-pup version 0.1.8" -> PUP_VERSION is a token.
    probe = context.run(
        f"cargo +{PUP_NIGHTLY} pup --version", warn=True, pty=False
    )
    return PUP_VERSION in _ANSI.sub("", probe.stdout).split()


@task
def install_pup(context: Context) -> None:
    """Provision the cargo-pup nightly toolchain + the pinned cargo-pup.

    Not a mise [tool]: mise cannot pin two rust toolchains and has no
    rust-nightly short-name, so the nightly is rustup-managed here and invoked
    via `cargo +<nightly>`. Idempotent — both steps no-op when the pinned
    versions are already present — so it is cheap to run ahead of pup:check.
    """
    # Step 1 — the nightly. If the dated nightly has been GC'd from
    # static.rust-lang.org this fails HERE, before any `+nightly` invocation
    # emits an opaque "override does not resolve" error; the recovery is to
    # bump PUP_NIGHTLY + PUP_VERSION together to a compatible pair.
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

    # Step 2 — cargo-pup itself, guarded by a presence probe so the multi-minute
    # source build is skipped in steady state (`cargo install --locked` is not a
    # pure no-op — it resolves and can rebuild/hit the network).
    if not _pup_already_installed(context):
        install = context.run(
            f"cargo +{PUP_NIGHTLY} install cargo_pup "
            f"--version {PUP_VERSION} --locked",
            warn=True,
            pty=False,
        )
        if install.exited != 0:
            raise Exit(f"failed to install cargo-pup {PUP_VERSION}", code=1)

    # Step 3 — pre-flight: confirm rustup's `+toolchain` override actually
    # resolves on this machine (that ~/.cargo/bin's proxy is the `cargo` on
    # PATH), so a broken override fails here rather than as an opaque
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
