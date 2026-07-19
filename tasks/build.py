import json
import platform
from collections.abc import Callable

from invoke import Context, Exit, task

from tasks.shared.files import atomic_write_text
from tasks.shared.hashing import compute_sha256
from tasks.shared.paths import (
    CHECKSUMS,
    SHIM_CRATE,
    WORKSPACE_ROOT,
    binary_path,
    debug_archive_path,
    shim_path,
)
from tasks.shared.rust import LAUNCHER_CRATE
from tasks.shared.targets import (
    MACOS_DEPLOYMENT_TARGET,
    TARGETS,
    host_targets,
    host_triple,
)

_SYSTEM_LIBRARY_PREFIXES = ("/usr/lib/", "/System/Library/")


def is_statically_linked(
    file_output: str, ldd_output: str | None = None
) -> bool:
    """Whether a musl release binary is static, per `file`/`ldd` output.

    Accepts both the plain-static and static-PIE phrasings the tools emit
    ("statically linked", "static-pie linked", "not a dynamic executable").
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

    Rejects both the wrong arch and a fat/universal binary carrying both.
    """
    normalised = arch_output.replace("x86-64", "x86_64")
    expected = "x86_64" if "x86_64" in triple else "arm64"
    other = "arm64" if expected == "x86_64" else "x86_64"
    return expected in normalised and other not in normalised


def links_only_system_libraries(link_output: str) -> bool:
    """Whether a darwin binary links nothing outside the OS-provided libraries.

    Parses `otool -L` / `llvm-objdump --macho --dylibs-used` output and rejects
    any dylib outside `/usr/lib/` or `/System/Library/`.
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


# Verification depends on both the build host and the target family, not the
# target triple alone.
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

    The returned digest is the bare lowercase sha256 hex of the staged binary.
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


def _release_build_triple(
    context: Context, triple: str, host_system: str
) -> None:
    result = context.run(
        f"cargo build --release --bin {LAUNCHER_CRATE} --target {triple}",
        warn=True,
        pty=False,
    )
    if result.exited != 0:
        raise Exit(f"release build failed: {triple}", code=1)
    _verify_output(context, triple, host_system)


@task
def launcher(context: Context) -> None:
    """Release-build the host-native triples, checking link/arch invariants."""
    host_system = platform.system()
    with context.cd(str(WORKSPACE_ROOT)):
        for triple in host_targets(host_system):
            _release_build_triple(context, triple, host_system)


@task
def launcher_host(context: Context) -> None:
    """Release-build only this host's single native triple (arch + OS).

    The eval tiers run — and byte-compare — the one binary this host executes.
    They do not need the sibling-arch cross build that `launcher` also produces,
    and which would demand a cross-linker the unit-test CI job does not install.
    """
    host_system = platform.system()
    triple = host_triple(host_system, platform.machine())
    with context.cd(str(WORKSPACE_ROOT)):
        _release_build_triple(context, triple, host_system)


@task
def release(context: Context) -> None:
    """Cross-build all four shipped triples from one host via cargo-zigbuild.

    Stages each binary + debug archive into `cli/launcher/bin/` and records the
    per-triple sha256 into `checksums.json`.
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
            _build_and_stage_shim(context, triple, target_platform)
    _write_checksums(digests)


def _build_and_stage_shim(
    context: Context, triple: str, target_platform: str
) -> None:
    """Cross-build the root-of-trust verify shim and stage it into the package.

    The shim ships committed in the plugin package; the launcher is fetched on
    demand.
    """
    result = context.run(
        f"cargo zigbuild --release --bin {SHIM_CRATE} --target {triple}",
        warn=True,
        pty=False,
        env=_release_build_env(triple),
    )
    if result.exited != 0:
        raise Exit(f"shim build failed: {triple}", code=1)
    source = f"target/{triple}/release/{SHIM_CRATE}"
    destination = shim_path(target_platform)
    destination.parent.mkdir(parents=True, exist_ok=True)
    context.run(f"cp {source} {destination}", pty=False)
