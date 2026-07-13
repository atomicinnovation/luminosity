from invoke import Exit

TARGETS = (
    ("aarch64-apple-darwin", "darwin-arm64"),
    ("x86_64-apple-darwin", "darwin-x64"),
    ("aarch64-unknown-linux-musl", "linux-arm64"),
    ("x86_64-unknown-linux-musl", "linux-x64"),
)

# Minimum macOS supported by the cross-built darwin artifacts, exported as
# MACOSX_DEPLOYMENT_TARGET. 11.0 (Big Sur) is the floor for arm64 and x86_64.
MACOS_DEPLOYMENT_TARGET = "11.0"

# platform.system() value -> the OS substring its release triples carry.
_HOST_OS_MARKERS = {
    "Darwin": "apple-darwin",
    "Linux": "unknown-linux",
}

# platform.machine() value -> the arch prefix its release triples carry.
_HOST_ARCH_MARKERS = {
    "arm64": "aarch64",
    "aarch64": "aarch64",
    "x86_64": "x86_64",
    "AMD64": "x86_64",
}


def host_targets(system: str) -> tuple[str, ...]:
    """Release triples whose OS matches `system` (a `platform.system()` value).

    Raises on an unsupported host rather than returning empty, which would make
    `build:launcher` run zero builds and false-green the static-link guard.
    """
    marker = _HOST_OS_MARKERS.get(system)
    if marker is None:
        supported = ", ".join(_HOST_OS_MARKERS)
        raise Exit(
            f"build:launcher: unsupported host OS {system!r}; "
            f"supported: {supported}",
            code=1,
        )
    return tuple(triple for triple, _ in TARGETS if marker in triple)


def host_triple(system: str, machine: str) -> str:
    """Return the one release triple matching this host's OS and architecture.

    `host_targets` narrows to an OS and so still yields both of its arches;
    callers that need the single binary this host actually builds want this.
    """
    arch = _HOST_ARCH_MARKERS.get(machine)
    if arch is None:
        supported = ", ".join(_HOST_ARCH_MARKERS)
        raise Exit(
            f"unsupported host architecture {machine!r}; "
            f"supported: {supported}",
            code=1,
        )
    for triple in host_targets(system):
        if triple.startswith(arch):
            return triple
    raise Exit(
        f"no release triple for host {system!r}/{machine!r}",
        code=1,
    )
