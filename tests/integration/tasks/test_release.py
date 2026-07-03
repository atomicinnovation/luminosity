from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from invoke import Context

import tasks.build as tb
import tasks.git as tgit
import tasks.github as gh
import tasks.marketplace as tm
import tasks.release as tr
import tasks.version as tv
from tasks.release import (
    _refuse_under_ci,
    prerelease,
    prerelease_finalise,
    prerelease_prepare,
    release,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def ctx():
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(return_code=0, stdout="")
    return m


class TestRefuseUnderCi:
    def test_raises_when_github_actions_set(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.delenv("CI", raising=False)
        with pytest.raises(RuntimeError, match="local-dev convenience task"):
            _refuse_under_ci("prerelease")

    def test_raises_when_ci_set_to_1(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CI", "1")
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        with pytest.raises(RuntimeError, match="local-dev convenience task"):
            _refuse_under_ci("prerelease")

    def test_raises_when_ci_set_to_yes(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CI", "yes")
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        with pytest.raises(RuntimeError):
            _refuse_under_ci("prerelease")

    def test_silent_outside_ci(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("CI", raising=False)
        _refuse_under_ci("prerelease")

    def test_empty_string_treated_as_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("GITHUB_ACTIONS", "")
        monkeypatch.setenv("CI", "")
        _refuse_under_ci("prerelease")


class TestPrereleasePrepare:
    def _setup(self, mocker: MockerFixture):
        mocker.patch.object(tgit, "configure")
        mocker.patch.object(tgit, "pull")
        mocker.patch.object(tv, "bump")
        mock_read = mocker.patch.object(tv, "read", return_value=MagicMock())
        mock_read.return_value.__str__ = lambda _: "1.21.0-pre.1"
        # Mocked so tests never mutate the real on-disk
        # .claude-plugin/marketplace-prerelease.json.
        mocker.patch.object(tm, "update_prerelease_version")
        # Mocked so tests never trigger a real four-triple cargo-zigbuild.
        mocker.patch.object(tb, "release")

    def test_calls_configure_and_pull(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        self._setup(mocker)
        prerelease_prepare(ctx)
        tgit.configure.assert_called_once_with(ctx)
        tgit.pull.assert_called_once_with(ctx)

    def test_bumps_pre_version(self, ctx: MagicMock, mocker: MockerFixture):
        self._setup(mocker)
        prerelease_prepare(ctx)
        tv.bump.assert_called_once()

    def test_cross_builds_the_release_binaries(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        self._setup(mocker)
        prerelease_prepare(ctx)
        tb.release.assert_called_once_with(ctx)


class TestReleasePrepare:
    def _setup(self, mocker: MockerFixture):
        mocker.patch.object(tgit, "configure")
        mocker.patch.object(tgit, "pull")
        mocker.patch.object(tv, "bump")
        mocker.patch.object(tm, "update_version")
        mocker.patch.object(tr.changelog, "release")
        mocker.patch.object(tb, "release")

    def test_cross_builds_the_release_binaries(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        self._setup(mocker)
        tr.release_prepare(ctx)
        tb.release.assert_called_once_with(ctx)


class TestPrereleaseFinalise:
    def test_commits_before_upload(self, ctx: MagicMock, mocker: MockerFixture):
        mocker.patch.object(
            tv, "read", return_value=MagicMock(__str__=lambda _: "1.21.0-pre.1")
        )
        mock_commit = mocker.patch.object(tgit, "commit_version")
        mock_upload = mocker.patch.object(gh, "upload_and_verify")
        mocker.patch.object(tgit, "tag_version")
        mocker.patch.object(tgit, "push")
        mocker.patch.object(gh, "create_release")

        prerelease_finalise(ctx)

        assert mock_commit.called
        assert mock_upload.called

    def test_creates_release_before_upload(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        mocker.patch.object(
            tv, "read", return_value=MagicMock(__str__=lambda _: "1.21.0-pre.1")
        )
        mocker.patch.object(tgit, "commit_version")
        mocker.patch.object(tgit, "tag_version")
        mocker.patch.object(tgit, "push")
        mock_create = mocker.patch.object(gh, "create_release")
        mock_upload = mocker.patch.object(gh, "upload_and_verify")

        prerelease_finalise(ctx)

        assert mock_create.called
        assert mock_upload.called


class TestLocalDevGuards:
    def test_prerelease_raises_under_ci(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("CI", "true")
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        with pytest.raises(RuntimeError):
            prerelease(ctx)

    def test_release_raises_under_ci(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.delenv("CI", raising=False)
        with pytest.raises(RuntimeError):
            release(ctx)

    def test_prerelease_composes_prepare_and_finalise(
        self,
        ctx: MagicMock,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("CI", raising=False)
        mock_prepare = mocker.patch.object(tr, "prerelease_prepare")
        mock_finalise = mocker.patch.object(tr, "prerelease_finalise")
        prerelease(ctx)
        mock_prepare.assert_called_once_with(ctx)
        mock_finalise.assert_called_once_with(ctx)

    def test_release_calls_all_four_halves(
        self,
        ctx: MagicMock,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("CI", raising=False)
        mock_rp = mocker.patch.object(tr, "release_prepare")
        mock_rf = mocker.patch.object(tr, "release_finalise")
        mock_pp = mocker.patch.object(tr, "prerelease_prepare")
        mock_pf = mocker.patch.object(tr, "prerelease_finalise")
        release(ctx)
        mock_rp.assert_called_once_with(ctx)
        mock_rf.assert_called_once_with(ctx)
        mock_pp.assert_called_once_with(ctx)
        mock_pf.assert_called_once_with(ctx)
