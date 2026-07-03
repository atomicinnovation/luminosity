import json
import platform
from collections.abc import Callable

from invoke import Context, Exit, task

from tasks.shared.files import atomic_write_text
from tasks.shared.hashing import compute_sha256
from tasks.shared.paths import (
    CHECKSUMS,
    WORKSPACE_ROOT,
    binary_path,
    debug_archive_path,
)
from tasks.shared.rust import LAUNCHER_CRATE
from tasks.shared.targets import (
    MACOS_DEPLOYMENT_TARGET,
    TARGETS,
    host_targets,
)

_SYSTEM_LIBRARY_PREFIXES = ("/usr/lib/", "/System/Library/")


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
    Normalises `llvm-objdump`'s hyphenated "x86-64" to lipo's "x86_64" so both
    verification tools read the same way.
    """
    normalised = arch_output.replace("x86-64", "x86_64")
    expected = "x86_64" if "x86_64" in triple else "arm64"
    other = "arm64" if expected == "x86_64" else "x86_64"
    return expected in normalised and other not in normalised


def links_only_system_libraries(link_output: str) -> bool:
    """Whether a darwin binary links nothing outside the OS-provided libraries.

    Parses `otool -L` / `llvm-objdump --macho --dylibs-used` output — both list
    one dylib path per line after a `<binary>:` header — and rejects any dylib
    that lives outside `/usr/lib/` or `/System/Library/`. An empty list passes
    vacuously (a fully static-except-libSystem binary lists only system paths).
    """
    non_system = []
    for line in link_output.splitlines():
        token = line.strip().split(" ", 1)[0]
        if not token.startswith("/") or token.endswith(":"):
            continue
        if not token.startswith(_SYSTEM_LIBRARY_PREFIXES):
            non_system.append(token)
    return not non_system


def _binary(triple: str) -> str:
    return f"target/{triple}/release/{LAUNCHER_CRATE}"


def _target_family(triple: str) -> str:
    return "musl" if "unknown-linux" in triple else "darwin"


def _verify_musl_with_ldd(context: Context, binary: str, triple: str) -> None:
    file_output = context.run(f"file {binary}", warn=True, pty=False).stdout
    ldd = context.run(f"ldd {binary}", warn=True, pty=False)
    ldd_output = f"{ldd.stdout}\n{ldd.stderr}"
    if not is_statically_linked(file_output, ldd_output):
        raise Exit(f"release binary is not statically linked: {triple}", code=1)


def _verify_musl_with_file(context: Context, binary: str, triple: str) -> None:
    # A Linux binary cross-built on macOS: `ldd` is unavailable, so the static
    # guarantee rests on `file` alone (the musl host leg re-checks with ldd).
    file_output = context.run(f"file {binary}", warn=True, pty=False).stdout
    if not is_statically_linked(file_output):
        raise Exit(f"release binary is not statically linked: {triple}", code=1)


def _verify_darwin_with_lipo_otool(
    context: Context, binary: str, triple: str
) -> None:
    arch_output = context.run(
        f"lipo -archs {binary}", warn=True, pty=False
    ).stdout
    if not has_expected_arch(triple, arch_output):
        raise Exit(f"release binary has the wrong arch: {triple}", code=1)
    link_output = context.run(f"otool -L {binary}", warn=True, pty=False).stdout
    if not links_only_system_libraries(link_output):
        raise Exit(
            f"release binary links non-system libraries: {triple}", code=1
        )


def _verify_darwin_with_objdump(
    context: Context, binary: str, triple: str
) -> None:
    # A darwin binary cross-built on Linux: `lipo`/`otool` are absent, so
    # verification uses `llvm-objdump --macho` from the pinned
    # llvm-tools-preview (which travels with the toolchain, keeping the check
    # host-independent).
    arch_output = context.run(
        f"llvm-objdump --macho {binary}", warn=True, pty=False
    ).stdout
    if not has_expected_arch(triple, arch_output):
        raise Exit(f"release binary has the wrong arch: {triple}", code=1)
    link_output = context.run(
        f"llvm-objdump --macho --dylibs-used {binary}", warn=True, pty=False
    ).stdout
    if not links_only_system_libraries(link_output):
        raise Exit(
            f"release binary links non-system libraries: {triple}", code=1
        )


# The verification tool depends on BOTH the build host and the target family,
# not the target triple alone — a darwin binary is inspected differently on a
# macOS host (lipo/otool) than on a Linux host (llvm-objdump). Modelled as an
# explicit strategy mapping rather than nested conditionals.
_VerifyStrategy = Callable[[Context, str, str], None]
_VERIFY_STRATEGIES: dict[tuple[str, str], _VerifyStrategy] = {
    ("Darwin", "darwin"): _verify_darwin_with_lipo_otool,
    ("Darwin", "musl"): _verify_musl_with_file,
    ("Linux", "darwin"): _verify_darwin_with_objdump,
    ("Linux", "musl"): _verify_musl_with_ldd,
}


def _verify_output(context: Context, triple: str, host_system: str) -> None:
    binary = _binary(triple)
    strategy = _VERIFY_STRATEGIES.get((host_system, _target_family(triple)))
    if strategy is None:
        raise Exit(
            f"no verification strategy for host {host_system!r} "
            f"building {triple}",
            code=1,
        )
    strategy(context, binary, triple)


def _release_build_env(triple: str) -> dict[str, str] | None:
    if "apple-darwin" in triple:
        return {"MACOSX_DEPLOYMENT_TARGET": MACOS_DEPLOYMENT_TARGET}
    return None


def _stage_artifacts(
    context: Context, triple: str, target_platform: str
) -> str:
    """Copy the built binary into the staging dir, archive it, return its hash.

    The `.debug.tar.gz` carries the release binary as the symbol-bearing
    artifact the publish flow uploads alongside it; the returned digest is the
    bare lowercase sha256 hex of the staged binary.
    """
    source = _binary(triple)
    destination = binary_path(target_platform)
    destination.parent.mkdir(parents=True, exist_ok=True)
    context.run(f"cp {source} {destination}", pty=False)
    archive = debug_archive_path(target_platform)
    context.run(
        f"tar -czf {archive} -C {destination.parent} {destination.name}",
        pty=False,
    )
    return compute_sha256(destination)


def _write_checksums(digests: dict[str, str]) -> None:
    data = json.loads(CHECKSUMS.read_text())
    data["binaries"] = {
        platform_alias: f"sha256:{digest}"
        for platform_alias, digest in digests.items()
    }
    atomic_write_text(CHECKSUMS, json.dumps(data, indent=2) + "\n")


@task
def launcher(context: Context) -> None:
    """Release-build the host-native triples, checking link/arch invariants.

    Host-native only (the two musl triples on Linux, the two darwin triples on
    macOS); CI's `build-launcher` matrix covers all four across both OSes.
    Builds the binary (`--bin`, not just `-p`) so the link step — the whole
    point of a per-triple build — is always exercised.
    """
    host_system = platform.system()
    with context.cd(str(WORKSPACE_ROOT)):
        for triple in host_targets(host_system):
            result = context.run(
                f"cargo build --release --bin {LAUNCHER_CRATE} "
                f"--target {triple}",
                warn=True,
                pty=False,
            )
            if result.exited != 0:
                raise Exit(f"release build failed: {triple}", code=1)
            _verify_output(context, triple, host_system)


@task
def release(context: Context) -> None:
    """Cross-build all four shipped triples from one host via cargo-zigbuild.

    Iterates every shipped triple (not just the host-native set), stages each
    binary + debug archive into `cli/launcher/bin/`, and records the per-triple
    sha256 into `checksums.json`. Verification is host-aware (arch AND linkage
    for every triple); runtime behaviour is execution-verified on host triples
    by `build:launcher`.
    """
    host_system = platform.system()
    digests: dict[str, str] = {}
    with context.cd(str(WORKSPACE_ROOT)):
        for triple, target_platform in TARGETS:
            result = context.run(
                f"cargo zigbuild --release --bin {LAUNCHER_CRATE} "
                f"--target {triple}",
                warn=True,
                pty=False,
                env=_release_build_env(triple),
            )
            if result.exited != 0:
                raise Exit(f"release build failed: {triple}", code=1)
            _verify_output(context, triple, host_system)
            digests[target_platform] = _stage_artifacts(
                context, triple, target_platform
            )
    _write_checksums(digests)
