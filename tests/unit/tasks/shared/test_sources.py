from typing import TYPE_CHECKING

from tasks.shared.sources import _is_in_scope, shell_sources

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str = "#!/usr/bin/env bash\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class TestInScopePredicate:
    def test_keeps_a_normal_script(self):
        assert _is_in_scope("scripts/foo.sh")

    def test_keeps_fixtures_at_any_depth(self):
        assert _is_in_scope("skills/x/test-fixtures/seed.sh")
        assert _is_in_scope("test-fixtures/a.sh")

    def test_excludes_workspaces(self):
        assert not _is_in_scope("workspaces/ws/a.sh")

    def test_keeps_test_helpers(self):
        assert _is_in_scope("scripts/test-helpers.sh")


class TestShellSourcesDiscovery:
    def test_keeps_fixtures_and_helpers_excludes_only_workspaces(
        self, tmp_path: Path
    ):
        _write(tmp_path / "scripts/normal.sh")
        _write(tmp_path / "scripts/test-helpers.sh")
        _write(tmp_path / "scripts/test-fixtures/seed.sh")
        _write(tmp_path / "workspaces/ws.sh")
        _write(tmp_path / "scripts/readme.md", "not a shell script\n")

        assert shell_sources(root=tmp_path) == [
            "scripts/normal.sh",
            "scripts/test-fixtures/seed.sh",
            "scripts/test-helpers.sh",
        ]

    def test_honours_gitignored_directories(self, tmp_path: Path):
        _write(tmp_path / ".gitignore", "node_modules/\ndist/\n")
        _write(tmp_path / "scripts/keep.sh")
        _write(tmp_path / "node_modules/pkg/install.sh")
        _write(tmp_path / "skills/app/node_modules/pkg/run.sh")
        _write(tmp_path / "skills/app/dist/bundle.sh")

        assert shell_sources(root=tmp_path) == ["scripts/keep.sh"]

    def test_honours_gitignored_file_patterns(self, tmp_path: Path):
        _write(tmp_path / ".gitignore", "*.generated.sh\n")
        _write(tmp_path / "scripts/real.sh")
        _write(tmp_path / "scripts/thing.generated.sh")

        assert shell_sources(root=tmp_path) == ["scripts/real.sh"]

    def test_never_descends_into_vcs_metadata(self, tmp_path: Path):
        _write(tmp_path / "scripts/keep.sh")
        _write(tmp_path / ".git/hooks/pre-commit.sh")
        _write(tmp_path / ".jj/working_copy/snapshot.sh")

        assert shell_sources(root=tmp_path) == ["scripts/keep.sh"]

    def test_finds_scripts_in_nested_directories(self, tmp_path: Path):
        _write(tmp_path / "a.sh")
        _write(tmp_path / "skills/x/scripts/deep.sh")

        assert shell_sources(root=tmp_path) == [
            "a.sh",
            "skills/x/scripts/deep.sh",
        ]

    def test_no_gitignore_present_is_tolerated(self, tmp_path: Path):
        _write(tmp_path / "scripts/keep.sh")

        assert shell_sources(root=tmp_path) == ["scripts/keep.sh"]
