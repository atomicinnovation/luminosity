from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from invoke import Context

import tasks.release as release_module
from tasks.release import (
    _publish,
    prerelease_prepare,
    prerelease_sign,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="", stderr="")
    return m


def _patch_publish_collaborators(mocker: MockerFixture) -> None:
    mocker.patch.object(release_module.version, "check")
    mocker.patch.object(release_module.version, "read", return_value="1.0.0")
    mocker.patch.object(release_module.git, "commit_version")
    mocker.patch.object(release_module.git, "tag_version")
    mocker.patch.object(release_module.git, "push")
    mocker.patch.object(release_module.github, "create_release")
    mocker.patch.object(release_module.github, "upload_and_verify")


class TestPublish:
    def test_publish_does_not_sign(
        self, ctx: MagicMock, mocker: MockerFixture
    ) -> None:
        signed = mocker.patch.object(release_module.sign, "sign")
        _patch_publish_collaborators(mocker)
        _publish(ctx)
        signed.assert_not_called()


class TestSignTasks:
    def test_sign_tasks_delegate_to_sign(
        self, ctx: MagicMock, mocker: MockerFixture
    ) -> None:
        signed = mocker.patch.object(release_module.sign, "sign")
        prerelease_sign(ctx)
        signed.assert_called_once_with(ctx)


class TestPrereleasePrepare:
    def test_updates_the_luminosity_prerelease_marketplace(
        self, ctx: MagicMock, mocker: MockerFixture
    ) -> None:
        update = mocker.patch.object(
            release_module.marketplace, "update_prerelease_version"
        )
        mocker.patch.object(release_module.git, "configure")
        mocker.patch.object(release_module.git, "pull")
        mocker.patch.object(release_module.version, "bump")
        mocker.patch.object(release_module.build, "release")
        prerelease_prepare(ctx)
        update.assert_called_once_with(ctx, plugin="luminosity")


class TestLeakGuard:
    def test_publish_runs_the_leak_guard_before_committing(
        self, ctx: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(release_module.version, "check")
        mocker.patch.object(
            release_module.version, "read", return_value="1.0.0"
        )
        mocker.patch.object(
            release_module.assertions,
            "no_leaked_artifacts",
            side_effect=RuntimeError,
        )
        commit = mocker.patch.object(release_module.git, "commit_version")
        with pytest.raises(RuntimeError):
            _publish(ctx)
        commit.assert_not_called()
