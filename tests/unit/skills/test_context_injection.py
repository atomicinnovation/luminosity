"""Enforce the context-injection wiring across every skill.

Claude Code discovers a plugin's skills by walking each directory listed in
`.claude-plugin/plugin.json`'s `skills` array for `SKILL.md` files. This suite
mirrors that walk and asserts, for every discovered skill, that it carries the
canonical injection line — naming *its own* skill — directly under its H1 and
grants the `context` command in `allowed-tools`, the two halves that make
injection fire at runtime.

The injected `--skill` argument is the skill's frontmatter `name:`, so the suite
also pins that name to the Rust `SkillName` allow-list and to the directory a
user must create by hand: an unrepresentable or mismatched name would otherwise
surface only at runtime, where clap would reject it *outside* the `--fail-safe`
boundary and discard the whole prompt.
"""

import json
import re
import subprocess
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
#
# --skill=<name> uses the equals form deliberately: a bare `--skill <name>`
# would let a name beginning with `-` be parsed by clap as an option — a
# non-zero exit outside the fail-safe boundary.
# The `${{...}}` doubling is str.format escaping: the rendered line carries a
# literal `${CLAUDE_PLUGIN_ROOT}` for the ! preprocessor to expand.
INJECTION_TEMPLATE = (
    "!`${{CLAUDE_PLUGIN_ROOT}}/bin/luminosity context "
    "--skill={skill} --fail-safe`"
)
CONTEXT_GRANT = "Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)"

# The Python mirror of SkillName::parse (cli/config/src/source.rs). Matched with
# `fullmatch`, not `match`: Python's `$` also matches before a trailing newline,
# so `match` would accept a "configure\n" that the Rust allow-list rejects.
SKILL_NAME_ALLOW_LIST = re.compile(r"[A-Za-z0-9_-]+")

_NAME_FIELD = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)


def _injection_line(skill_name: str) -> str:
    return INJECTION_TEMPLATE.format(skill=skill_name)


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

    def test_the_frontmatter_name_satisfies_the_skill_name_allow_list(
        self, skill_file: Path
    ) -> None:
        assert SKILL_NAME_ALLOW_LIST.fullmatch(_skill_name(skill_file))

    def test_the_frontmatter_name_matches_the_skill_directory_name(
        self, skill_file: Path
    ) -> None:
        # The name a user types into `.luminosity/skills/<name>/` is the name
        # the skill is invoked by, not its category directory.
        assert _skill_name(skill_file) == skill_file.parent.name

    def test_line_sits_under_the_h1_before_any_subsection(
        self, skill_file: Path
    ) -> None:
        injection_line = _injection_line(_skill_name(skill_file))
        _, body = _split_frontmatter_and_body(skill_file.read_text())
        lines = body.splitlines()
        h1 = next(
            index for index, line in enumerate(lines) if line.startswith("# ")
        )
        injection = next(
            index
            for index, line in enumerate(lines)
            if line.strip() == injection_line
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

    def test_carries_the_managing_skill_context_section(self) -> None:
        assert "## Managing skill-specific context" in _CONFIGURE.read_text()

    def test_names_both_skill_context_paths_as_the_source(self) -> None:
        text = _CONFIGURE.read_text()
        assert ".luminosity/skills/configure/context.md" in text
        assert ".luminosity/skills/configure/context.local.md" in text

    def test_states_the_naming_rule_and_the_silence_caveat(self) -> None:
        text = _CONFIGURE.read_text()
        assert "invoked by" in text
        assert "nothing" in text
        assert "unterminated" in text

    def test_shows_the_explain_diagnostic_for_a_skill(self) -> None:
        assert (
            "${CLAUDE_PLUGIN_ROOT}/bin/luminosity context "
            "--skill=configure --explain" in _CONFIGURE.read_text()
        )


class TestGitignore:
    _FIXTURE = (
        "tests/evals/skills/configure/fixtures/context_skill_both_levels"
        "/.luminosity/skills/configure"
    )

    def test_hides_a_personal_skill_context(self) -> None:
        assert _is_ignored(".luminosity/skills/configure/context.local.md")

    def test_tracks_a_team_skill_context(self) -> None:
        assert not _is_ignored(".luminosity/skills/configure/context.md")

    def test_tracks_a_personal_skill_context_in_the_eval_fixtures(self) -> None:
        assert not _is_ignored(f"{self._FIXTURE}/context.local.md")

    def test_tracks_a_team_skill_context_in_the_eval_fixtures(self) -> None:
        assert not _is_ignored(f"{self._FIXTURE}/context.md")
