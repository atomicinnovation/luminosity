from invoke import Exit

TARGETS = (
    ("aarch64-apple-darwin", "darwin-arm64"),
    ("x86_64-apple-darwin", "darwin-x64"),
    ("aarch64-unknown-linux-musl", "linux-arm64"),
    ("x86_64-unknown-linux-musl", "linux-x64"),
)

# The minimum macOS the cross-built darwin artifacts support, set explicitly so
# the supported range is a conscious, reproducible choice rather than whatever
# the host toolchain happens to default to. 11.0 (Big Sur) is the common floor
# for both arm64 (which requires >= 11.0) and x86_64. Bump deliberately when the
# support window moves; the darwin release builds export it as
# MACOSX_DEPLOYMENT_TARGET.
MACOS_DEPLOYMENT_TARGET = "11.0"

# platform.system() value -> the OS substring its release triples carry.
_HOST_OS_MARKERS = {
    "Darwin": "apple-darwin",
    "Linux": "unknown-linux",
}


def host_targets(system: str) -> tuple[str, ...]:
    """Release triples whose OS matches `system` (a `platform.system()` value).

    Partitions the single `TARGETS` tuple by OS substring so the per-OS build
    set provably shares one definition with the install and shipped sets.
    Exits — rather than returning empty — on an unsupported host: an empty
    result would make `build:launcher` run zero builds and exit 0, a
    false-green on the static-link guard.
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
