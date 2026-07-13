"""Enforce the plugin-global context-injection wiring across every skill.

Claude Code discovers a plugin's skills by walking each directory listed in
`.claude-plugin/plugin.json`'s `skills` array for `SKILL.md` files. This suite
mirrors that walk and asserts, for every discovered skill, that it carries the
canonical injection line directly under its H1 and grants the `context` command
in `allowed-tools` — the two halves that make injection fire at runtime.
"""

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGIN_JSON = _REPO_ROOT / ".claude-plugin" / "plugin.json"
_CONFIGURE = _REPO_ROOT / "skills" / "config" / "configure" / "SKILL.md"

# --fail-safe is load-bearing. The reader is fail-loud, and the ! preprocessor
# discards the whole prompt on a non-zero exit — so a single malformed config
# file would otherwise make every skill refuse to load, including the one a user
# would reach for to diagnose it. The flag renders the read failure as a visible
# stdout notice naming the file, so a broken config stays loud in every skill
# without disabling any of them.
INJECTION_LINE = "!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --fail-safe`"
CONTEXT_GRANT = "Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)"


def _registered_skill_dirs() -> list[Path]:
    plugin = json.loads(_PLUGIN_JSON.read_text())
    return [_REPO_ROOT / entry for entry in plugin["skills"]]


def _discover_skill_files() -> list[Path]:
    files: list[Path] = []
    for directory in _registered_skill_dirs():
        files.extend(sorted(directory.rglob("SKILL.md")))
    return files


_SKILL_FILES = _discover_skill_files()


def _split_frontmatter_and_body(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    _, frontmatter, body = text.split("---", 2)
    return frontmatter, body


def test_the_walk_discovers_at_least_one_skill() -> None:
    # Guard against a vacuous suite: an empty discovery would pass every
    # parametrized assertion below by having no cases at all.
    assert _SKILL_FILES, "no SKILL.md discovered under the registered skills"


@pytest.mark.parametrize(
    "skill_file", _SKILL_FILES, ids=lambda path: path.parent.name
)
class TestEverySkillIsWired:
    def test_carries_the_exact_injection_line(self, skill_file: Path) -> None:
        assert INJECTION_LINE in skill_file.read_text()

    def test_line_sits_under_the_h1_before_any_subsection(
        self, skill_file: Path
    ) -> None:
        _, body = _split_frontmatter_and_body(skill_file.read_text())
        lines = body.splitlines()
        h1 = next(
            index for index, line in enumerate(lines) if line.startswith("# ")
        )
        injection = next(
            index
            for index, line in enumerate(lines)
            if line.strip() == INJECTION_LINE
        )
        first_subsection = next(
            (
                index
                for index, line in enumerate(lines)
                if line.startswith("## ")
            ),
            len(lines),
        )
        assert injection > h1
        assert all(
            not lines[index].strip() for index in range(h1 + 1, injection)
        )
        assert injection < first_subsection

    def test_allowed_tools_grants_the_context_command(
        self, skill_file: Path
    ) -> None:
        frontmatter, _ = _split_frontmatter_and_body(skill_file.read_text())
        assert CONTEXT_GRANT in frontmatter


class TestConfigureSurface:
    def test_carries_the_managing_project_context_section(self) -> None:
        assert "## Managing project context" in _CONFIGURE.read_text()

    def test_names_both_config_body_paths_as_the_source(self) -> None:
        text = _CONFIGURE.read_text()
        assert ".luminosity/config.md" in text
        assert ".luminosity/config.local.md" in text
