"""Enforce the instructions-injection wiring across every skill.

Claude Code discovers a plugin's skills by walking each directory listed in
`.claude-plugin/plugin.json`'s `skills` array for `SKILL.md` files. This suite
mirrors that walk and asserts, for every discovered skill, that it carries the
instructions injection line — naming *its own* skill — at the **end** of its
body, after the top-of-body context line and after every `## ` subsection, and
grants the `instructions` command in `allowed-tools`.

Placement is a SKILL.md concern: the `## Additional Instructions` block lands
last because no top-of-body invocation can produce an end-of-body block, so the
"context early / instructions last" ordering is realised by two separate
`!`-preprocessor lines. This suite is the positional inverse of the context
suite — the context line sits under the H1 before any subsection; the
instructions line sits after them all.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGIN_JSON = _REPO_ROOT / ".claude-plugin" / "plugin.json"
_CONFIGURE = _REPO_ROOT / "skills" / "config" / "configure" / "SKILL.md"

# --fail-safe and the --skill=<name> equals form are load-bearing for the same
# reasons as the context line: the ! preprocessor discards the whole prompt on a
# non-zero exit, so a malformed instructions file must degrade to a visible
# stdout notice rather than fail loud, and a bare `--skill <name>` would let a
# name beginning with `-` be parsed by clap as an option outside that boundary.
# The `${{...}}` doubling is str.format escaping: the rendered line carries a
# literal `${CLAUDE_PLUGIN_ROOT}` for the ! preprocessor to expand.
INJECTION_TEMPLATE = (
    "!`${{CLAUDE_PLUGIN_ROOT}}/bin/luminosity instructions "
    "--skill={skill} --fail-safe`"
)
CONTEXT_INJECTION_TEMPLATE = (
    "!`${{CLAUDE_PLUGIN_ROOT}}/bin/luminosity context "
    "--skill={skill} --fail-safe`"
)
INSTRUCTIONS_GRANT = "Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity instructions*)"

_NAME_FIELD = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)


def _injection_line(skill_name: str) -> str:
    return INJECTION_TEMPLATE.format(skill=skill_name)


def _context_injection_line(skill_name: str) -> str:
    return CONTEXT_INJECTION_TEMPLATE.format(skill=skill_name)


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


def _skill_name(skill_file: Path) -> str:
    frontmatter, _ = _split_frontmatter_and_body(skill_file.read_text())
    match = _NAME_FIELD.search(frontmatter)
    if match is None:
        message = f"no frontmatter name: field in {skill_file}"
        raise AssertionError(message)
    return match.group(1)


def _is_ignored(relative_path: str) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", relative_path],
            cwd=_REPO_ROOT,
            check=False,
        ).returncode
        == 0
    )


def test_the_walk_discovers_at_least_one_skill() -> None:
    # Guard against a vacuous suite: an empty discovery would pass every
    # parametrized assertion below by having no cases at all.
    assert _SKILL_FILES, "no SKILL.md discovered under the registered skills"


@pytest.mark.parametrize(
    "skill_file", _SKILL_FILES, ids=lambda path: path.parent.name
)
class TestEverySkillIsWired:
    def test_carries_the_exact_injection_line(self, skill_file: Path) -> None:
        expected = _injection_line(_skill_name(skill_file))
        assert expected in skill_file.read_text()

    def test_line_sits_at_the_end_after_the_context_line_and_all_subsections(
        self, skill_file: Path
    ) -> None:
        name = _skill_name(skill_file)
        _, body = _split_frontmatter_and_body(skill_file.read_text())
        lines = body.splitlines()
        instructions = next(
            index
            for index, line in enumerate(lines)
            if line.strip() == _injection_line(name)
        )
        context = next(
            index
            for index, line in enumerate(lines)
            if line.strip() == _context_injection_line(name)
        )
        h1 = next(
            index for index, line in enumerate(lines) if line.startswith("# ")
        )
        last_subsection = max(
            (
                index
                for index, line in enumerate(lines)
                if line.startswith("## ")
            ),
            default=h1,
        )
        assert instructions > context
        assert instructions > last_subsection

    def test_allowed_tools_grants_the_instructions_command(
        self, skill_file: Path
    ) -> None:
        frontmatter, _ = _split_frontmatter_and_body(skill_file.read_text())
        assert INSTRUCTIONS_GRANT in frontmatter


class TestConfigureSurface:
    def test_carries_the_managing_skill_instructions_section(self) -> None:
        assert (
            "## Managing skill-specific instructions" in _CONFIGURE.read_text()
        )

    def test_names_both_skill_instructions_paths_as_the_source(self) -> None:
        text = _CONFIGURE.read_text()
        assert ".luminosity/skills/configure/instructions.md" in text
        assert ".luminosity/skills/configure/instructions.local.md" in text

    def test_shows_the_explain_diagnostic_for_instructions(self) -> None:
        assert (
            "${CLAUDE_PLUGIN_ROOT}/bin/luminosity instructions "
            "--skill=configure --explain" in _CONFIGURE.read_text()
        )


class TestGitignore:
    # This fixture (added in the eval-coverage phase) is the committed witness
    # that the .gitignore negation commits a personal *skill instructions* file
    # under the eval fixtures — the analogue of context_skill_both_levels.
    _FIXTURE = (
        "tests/evals/skills/configure/fixtures/instructions_skill_both_levels"
        "/.luminosity/skills/configure"
    )

    def test_hides_a_personal_skill_instructions(self) -> None:
        assert _is_ignored(".luminosity/skills/configure/instructions.local.md")

    def test_tracks_a_team_skill_instructions(self) -> None:
        assert not _is_ignored(".luminosity/skills/configure/instructions.md")

    def test_tracks_a_personal_skill_instructions_in_the_eval_fixtures(
        self,
    ) -> None:
        assert not _is_ignored(f"{self._FIXTURE}/instructions.local.md")

    def test_tracks_a_team_skill_instructions_in_the_eval_fixtures(
        self,
    ) -> None:
        assert not _is_ignored(f"{self._FIXTURE}/instructions.md")
