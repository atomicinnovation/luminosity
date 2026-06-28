import platform

from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT
from tasks.shared.rust import CLI_CRATE
from tasks.shared.targets import host_targets


def is_statically_linked(
    file_output: str, ldd_output: str | None = None
) -> bool:
    """Whether a musl release binary is static, per `file`/`ldd` output.

    The native-tls ban is necessary-but-not-sufficient (other system-C `*-sys`
    crates link dynamically too), so the static guarantee is turned into a
    checked fact rather than inferred.

    Accepts both the plain-static and static-PIE phrasings each tool emits: the
    aarch64 musl build links non-PIE static ("statically linked"), while the
    modern x86_64 musl default links static-PIE, which `file` reports as
    "static-pie linked" and `ldd` reports as "statically linked" (not "not a
    dynamic executable"). All denote a binary with no dynamic dependencies.
    """
    if "statically linked" in file_output or "static-pie linked" in file_output:
        return True
    if ldd_output is None:
        return False
    return (
        "not a dynamic executable" in ldd_output
        or "statically linked" in ldd_output
    )


def has_expected_arch(triple: str, arch_output: str) -> bool:
    """Whether a darwin release binary is the single arch `triple` expects.

    Rejects the wrong arch AND a fat/universal binary carrying both, so the
    cross-arch slice (x86_64 built on an arm64 runner) is a checked fact.
    """
    expected = "x86_64" if "x86_64" in triple else "arm64"
    other = "arm64" if expected == "x86_64" else "x86_64"
    return expected in arch_output and other not in arch_output


def _binary(triple: str) -> str:
    return f"target/{triple}/release/{CLI_CRATE}"


def _verify_output(context: Context, triple: str) -> None:
    binary = _binary(triple)
    if "unknown-linux" in triple:
        file_output = context.run(f"file {binary}", warn=True, pty=False).stdout
        ldd = context.run(f"ldd {binary}", warn=True, pty=False)
        ldd_output = f"{ldd.stdout}\n{ldd.stderr}"
        if not is_statically_linked(file_output, ldd_output):
            raise Exit(
                f"release binary is not statically linked: {triple}", code=1
            )
    else:
        arch_output = context.run(
            f"lipo -archs {binary}", warn=True, pty=False
        ).stdout
        if not has_expected_arch(triple, arch_output):
            raise Exit(f"release binary has the wrong arch: {triple}", code=1)


@task
def cli(context: Context) -> None:
    """Release-build the host-native triples, checking link/arch invariants.

    Host-native only (the two musl triples on Linux, the two darwin triples on
    macOS); CI's `build-cli` matrix covers all four across both OSes. Builds
    the binary (`--bin`, not just `-p`) so the link step — the whole point of a
    per-triple build — is always exercised.
    """
    with context.cd(str(REPO_ROOT)):
        for triple in host_targets(platform.system()):
            result = context.run(
                f"cargo build --release --bin {CLI_CRATE} --target {triple}",
                warn=True,
                pty=False,
            )
            if result.exited != 0:
                raise Exit(f"release build failed: {triple}", code=1)
            _verify_output(context, triple)
