import re

import yaml

from tasks.shared.paths import REPO_ROOT, binary_path
from tasks.shared.targets import TARGETS

_EVAL_DIR = REPO_ROOT / "tests" / "evals" / "skills" / "configure"
_DOCKERFILE = _EVAL_DIR / "Dockerfile"
_COMPOSE = _EVAL_DIR / "compose.yaml"

_AMD64_ALIAS = "linux-x64"
_AMD64_TRIPLE = "x86_64-unknown-linux-musl"
_COMPOSE_PLATFORM = "linux/amd64"


def _copy_source() -> str:
    for line in _DOCKERFILE.read_text().splitlines():
        match = re.match(r"COPY\s+(\S+)\s+(\S+)", line)
        if match and "luminosity" in match.group(1):
            return match.group(1)
    raise AssertionError("no luminosity COPY in the eval Dockerfile")


def test_copy_source_matches_the_staged_release_binary():
    expected = binary_path(_AMD64_ALIAS).relative_to(REPO_ROOT).as_posix()
    assert _copy_source() == expected


def test_compose_pins_the_amd64_platform():
    compose = yaml.safe_load(_COMPOSE.read_text())
    assert compose["services"]["default"]["platform"] == _COMPOSE_PLATFORM


def test_the_amd64_alias_maps_to_the_x86_64_musl_triple():
    # The COPY alias + platform pin mirror targets.py by hand; guard that the
    # alias still denotes the amd64 (x86_64) triple.
    assert (_AMD64_TRIPLE, _AMD64_ALIAS) in TARGETS
    assert _COMPOSE_PLATFORM.endswith("amd64")
    assert _AMD64_TRIPLE.startswith("x86_64")
