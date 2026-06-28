import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks.lint import cli as lint_cli
from tasks.lint import scripts as lint

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

REPO_ROOT = Path(__file__).resolve().parents[3]
LINT_BASHISMS = REPO_ROOT / "scripts/lint-bashisms.sh"


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="")
    return m


def _command(ctx: MagicMock) -> str:
    return ctx.run.call_args.args[0]


_FLAGS_NOW_OWNED_BY_SHELLCHECKRC = ("-x", "--severity")


class TestShellcheckTask:
    def test_invokes_shellcheck_with_no_inline_flags(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        mocker.patch.object(
            lint, "shell_sources", return_value=["a.sh", "b.sh"]
        )
        lint.shellcheck(ctx)
        cmd = _command(ctx)
        assert cmd.startswith("shellcheck ")
        for flag in _FLAGS_NOW_OWNED_BY_SHELLCHECKRC:
            assert flag not in cmd
        assert "a.sh" in cmd
        assert "b.sh" in cmd

    def test_raises_on_findings(self, ctx: MagicMock, mocker: MockerFixture):
        mocker.patch.object(lint, "shell_sources", return_value=["a.sh"])
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            lint.shellcheck(ctx)

    def test_raises_when_source_discovery_is_empty(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        mocker.patch.object(lint, "shell_sources", return_value=[])
        with pytest.raises(Exit):
            lint.shellcheck(ctx)
        ctx.run.assert_not_called()


class TestBashismsTask:
    def test_command(self, ctx: MagicMock, mocker: MockerFixture):
        mocker.patch.object(lint, "shell_sources", return_value=["a.sh"])
        lint.bashisms(ctx)
        assert _command(ctx).startswith("bash scripts/lint-bashisms.sh ")

    def test_raises_on_findings(self, ctx: MagicMock, mocker: MockerFixture):
        mocker.patch.object(lint, "shell_sources", return_value=["a.sh"])
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            lint.bashisms(ctx)

    def test_raises_when_source_discovery_is_empty(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        mocker.patch.object(lint, "shell_sources", return_value=[])
        with pytest.raises(Exit):
            lint.bashisms(ctx)
        ctx.run.assert_not_called()


def _run_lint(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(LINT_BASHISMS), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _lint_shell_body(
    tmp_path: Path, body: str
) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "x.sh"
    script.write_text(f"#!/usr/bin/env bash\n{body}")
    return _run_lint(script)


def _flagged(result: subprocess.CompletedProcess[str]) -> bool:
    return result.returncode != 0


class TestBashismsScript:
    def test_flags_associative_array(self, tmp_path: Path):
        result = _lint_shell_body(tmp_path, "declare -A MAP\n")
        assert _flagged(result)
        assert "associative array" in result.stdout

    def test_flags_bash_4_nameref(self, tmp_path: Path):
        result = _lint_shell_body(tmp_path, 'f() { local -n ref="$1"; }\n')
        assert _flagged(result)
        assert "nameref" in result.stdout

    def test_flags_escaped_brace_in_expansion_default(self, tmp_path: Path):
        # `${x:-{\}}` keeps the literal backslash ("{\}") on the bash-3.2 floor
        # but yields "{}" on bash 4+ — a silent data-corruption divergence.
        result = _lint_shell_body(tmp_path, 'v="${1:-{\\}}"\n')
        assert _flagged(result)
        assert "escaped brace" in result.stdout

    def test_unescaped_braces_in_default_are_not_flagged(self, tmp_path: Path):
        result = _lint_shell_body(tmp_path, 'v="${1:-{}}"\necho "$v"\n')
        assert not _flagged(result), result.stdout

    def test_substitution_with_escaped_brace_not_flagged(self, tmp_path: Path):
        result = _lint_shell_body(tmp_path, 'v="${var//\\}/x}"\necho "$v"\n')
        assert not _flagged(result), result.stdout

    def test_comment_naming_a_construct_is_not_flagged(self, tmp_path: Path):
        result = _lint_shell_body(
            tmp_path, "# do not use declare -A here\necho ok\n"
        )
        assert not _flagged(result), result.stdout

    def test_inline_opt_out_marker(self, tmp_path: Path):
        result = _lint_shell_body(
            tmp_path, "declare -A MAP # lint-bashisms: ignore\n"
        )
        assert not _flagged(result), result.stdout

    def test_parameter_expansion_strip_is_not_a_case_mod(self, tmp_path: Path):
        result = _lint_shell_body(tmp_path, 'echo "${x#prefix}"\n')
        assert not _flagged(result), result.stdout

    def test_clean_file_passes(self, tmp_path: Path):
        result = _lint_shell_body(
            tmp_path, 'for i in 1 2 3; do echo "$i"; done\n'
        )
        assert not _flagged(result), result.stdout


class TestLintCliCheck:
    def test_runs_clippy_with_deny_warnings(self, ctx: MagicMock):
        lint_cli.check(ctx)
        assert _command(ctx) == (
            "cargo clippy --workspace --all-targets --all-features "
            "-- -D warnings"
        )

    def test_raises_on_findings(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            lint_cli.check(ctx)


class TestLintCliFix:
    def test_runs_clippy_fix_rewriting_dirty_tree(self, ctx: MagicMock):
        lint_cli.fix(ctx)
        assert _command(ctx) == (
            "cargo clippy --workspace --all-targets --all-features "
            "--fix --allow-dirty --allow-staged"
        )

    def test_warns_when_autofix_fails(
        self, ctx: MagicMock, capsys: pytest.CaptureFixture[str]
    ):
        ctx.run.return_value = MagicMock(exited=1)
        lint_cli.fix(ctx)
        assert "WARNING" in capsys.readouterr().out
