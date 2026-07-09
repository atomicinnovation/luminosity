from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from invoke import Context

import tasks.release as release_module
from tasks.release import (
    _publish,
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


class TestLeakGuard:
    def test_publish_aborts_when_a_secret_would_leak(
        self, ctx: MagicMock, mocker: MockerFixture
    ) -> None:
        ctx.run.return_value = MagicMock(
            stdout="?? keys/luminosity-release.key\n"
        )
        mocker.patch.object(release_module.version, "check")
        mocker.patch.object(
            release_module.version, "read", return_value="1.0.0"
        )
        commit = mocker.patch.object(release_module.git, "commit_version")
        with pytest.raises(RuntimeError):
            _publish(ctx)
        commit.assert_not_called()

    def test_publish_aborts_when_a_staged_binary_would_leak(
        self, ctx: MagicMock, mocker: MockerFixture
    ) -> None:
        ctx.run.return_value = MagicMock(
            stdout="?? cli/launcher/bin/luminosity-darwin-arm64\n"
        )
        mocker.patch.object(release_module.version, "check")
        mocker.patch.object(
            release_module.version, "read", return_value="1.0.0"
        )
        commit = mocker.patch.object(release_module.git, "commit_version")
        with pytest.raises(RuntimeError):
            _publish(ctx)
        commit.assert_not_called()

    def test_publish_allows_clean_version_anchors(
        self, ctx: MagicMock, mocker: MockerFixture
    ) -> None:
        ctx.run.return_value = MagicMock(
            stdout=" M cli/launcher/bin/checksums.json\n"
            " M cli/launcher/bin/manifest.json\n"
        )
        mocker.patch.object(release_module.version, "check")
        mocker.patch.object(
            release_module.version, "read", return_value="1.0.0"
        )
        commit = mocker.patch.object(release_module.git, "commit_version")
        mocker.patch.object(release_module.git, "tag_version")
        mocker.patch.object(release_module.git, "push")
        mocker.patch.object(release_module.github, "create_release")
        mocker.patch.object(release_module.github, "upload_and_verify")
        _publish(ctx)
        commit.assert_called_once_with(ctx)
