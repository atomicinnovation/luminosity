from typing import TYPE_CHECKING

from common.eval import WORKDIR_PREFIX
from tasks.shared.eval.workdirs import cleanup_workdirs

if TYPE_CHECKING:
    from pathlib import Path


def _workdir(root: Path, suffix: str) -> Path:
    path = root / f"{WORKDIR_PREFIX}{suffix}"
    path.mkdir()
    (path / ".luminosity").mkdir()
    return path


class TestCleanupWorkdirs:
    def test_removes_every_seeded_workdir(self, tmp_path: Path):
        workdirs = [_workdir(tmp_path, suffix) for suffix in ("a", "b")]
        assert cleanup_workdirs(tmp_path) == 2
        assert not any(workdir.exists() for workdir in workdirs)

    def test_leaves_unrelated_temp_entries_alone(self, tmp_path: Path):
        bystander = tmp_path / "someone-elses-tmpdir"
        bystander.mkdir()
        file_ = tmp_path / f"{WORKDIR_PREFIX}not-a-directory"
        file_.write_text("")

        assert cleanup_workdirs(tmp_path) == 0
        assert bystander.exists()
        assert file_.exists()

    def test_is_a_no_op_on_an_empty_root(self, tmp_path: Path):
        assert cleanup_workdirs(tmp_path) == 0

    def test_sweeps_leftovers_from_an_earlier_crashed_run(self, tmp_path: Path):
        _workdir(tmp_path, "stale")
        assert cleanup_workdirs(tmp_path) == 1
        assert list(tmp_path.iterdir()) == []
