from invoke import Exit

TARGETS = (
    ("aarch64-apple-darwin", "darwin-arm64"),
    ("x86_64-apple-darwin", "darwin-x64"),
    ("aarch64-unknown-linux-musl", "linux-arm64"),
    ("x86_64-unknown-linux-musl", "linux-x64"),
)

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
    result would make `build:cli` run zero builds and exit 0, a false-green on
    the static-link guard.
    """
    marker = _HOST_OS_MARKERS.get(system)
    if marker is None:
        supported = ", ".join(_HOST_OS_MARKERS)
        raise Exit(
            f"build:cli: unsupported host OS {system!r}; "
            f"supported: {supported}",
            code=1,
        )
    return tuple(triple for triple, _ in TARGETS if marker in triple)
