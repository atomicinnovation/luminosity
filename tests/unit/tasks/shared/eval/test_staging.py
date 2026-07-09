from typing import TYPE_CHECKING

from tasks.shared.eval.staging import stage_plugin

if TYPE_CHECKING:
    from pathlib import Path


def _fake_repo(root: Path) -> Path:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        '{"name":"luminosity","skills":["./skills/config/"]}'
    )
    skill = root / "skills" / "config" / "configure"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: configure\n---\nbody")
    return root


class TestStagePlugin:
    def test_stages_manifest_skill_and_real_binary(self, tmp_path: Path):
        repo = _fake_repo(tmp_path / "repo")
        binary = tmp_path / "luminosity-host"
        binary.write_text("#!/bin/sh\necho real\n")
        dest = tmp_path / "staged"

        result = stage_plugin(repo_root=repo, host_binary=binary, dest=dest)

        assert result == dest
        assert (dest / ".claude-plugin" / "plugin.json").is_file()
        assert (dest / "skills" / "config" / "configure" / "SKILL.md").is_file()
        launcher = dest / "bin" / "luminosity"
        assert launcher.read_text() == "#!/bin/sh\necho real\n"
        assert launcher.stat().st_mode & 0o111

    def test_is_idempotent_replacing_a_prior_staging(self, tmp_path: Path):
        repo = _fake_repo(tmp_path / "repo")
        binary = tmp_path / "luminosity-host"
        binary.write_text("binary")
        dest = tmp_path / "staged"
        (dest / "bin").mkdir(parents=True)
        (dest / "bin" / "stale").write_text("leftover")

        stage_plugin(repo_root=repo, host_binary=binary, dest=dest)

        assert not (dest / "bin" / "stale").exists()
        assert (dest / "bin" / "luminosity").read_text() == "binary"
