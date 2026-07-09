import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

import tasks.sign as sign_module
from tasks.shared import minisign
from tasks.shared.targets import TARGETS
from tasks.sign import MANIFEST_SCHEMA_VERSION, build_manifest, sign

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_PLATFORMS = tuple(platform for _, platform in TARGETS)
_MINISIGN_ABSENT = shutil.which(minisign.MINISIGN) is None

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED_MANIFEST_FIXTURE = (
    REPO_ROOT
    / "cli"
    / "launcher"
    / "tests"
    / "fixtures"
    / "manifest.example.json"
)


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="", stderr="")
    return m


class TestBuildManifest:
    def _manifest(self) -> dict[str, Any]:
        digests = {p: str(i) * 64 for i, p in enumerate(_PLATFORMS, start=1)}
        signatures = {p: f"sig-for-{p}" for p in _PLATFORMS}
        return build_manifest("0.1.0-pre.1", digests, signatures)

    def test_is_name_keyed_with_a_luminosity_entry(self):
        manifest = self._manifest()
        assert "luminosity" in manifest["binaries"]
        assert manifest["binaries"]["luminosity"]["description"]

    def test_carries_schema_version_and_version(self):
        manifest = self._manifest()
        assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
        assert manifest["version"] == "0.1.0-pre.1"

    def test_each_platform_has_bare_sha256_and_signature(self):
        platforms = self._manifest()["binaries"]["luminosity"]["platforms"]
        assert set(platforms) == set(_PLATFORMS)
        for entry in platforms.values():
            assert not entry["sha256"].startswith("sha256:")
            assert entry["signature"]


class TestSharedManifestFixture:
    """The fixture the Rust reader also consumes — the shared contract."""

    def _fixture(self) -> dict[str, Any]:
        return json.loads(SHARED_MANIFEST_FIXTURE.read_text())

    def test_parses_and_has_expected_schema(self):
        manifest = self._fixture()
        assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION

    def test_lists_a_synthetic_sub_binary_with_a_description(self):
        # The name-keyed shape lets each sub-binary carry its own description
        # (what help synthesis renders).
        foo = self._fixture()["binaries"]["foo"]
        assert foo["description"] == "Bar tool"
        assert "darwin-arm64" in foo["platforms"]

    def test_writer_shape_matches_the_fixtures_launcher_entry(self):
        digests = {p: str(i) * 64 for i, p in enumerate(_PLATFORMS, start=1)}
        signatures = {p: f"sig-{p}" for p in _PLATFORMS}
        built = build_manifest("0.1.0-pre.1", digests, signatures)
        fixture_launcher = self._fixture()["binaries"]["luminosity"]
        built_launcher = built["binaries"]["luminosity"]
        assert set(built_launcher) == set(fixture_launcher)
        assert set(built_launcher["platforms"]["darwin-arm64"]) == set(
            fixture_launcher["platforms"]["darwin-arm64"]
        )


class TestSignTask:
    def _setup(self, mocker: MockerFixture, tmp_path: Path) -> None:
        checksums = tmp_path / "checksums.json"
        checksums.write_text(
            json.dumps(
                {
                    "version": "0.1.0-pre.1",
                    "binaries": dict.fromkeys(_PLATFORMS, f"sha256:{'a' * 64}"),
                }
            )
        )
        mocker.patch.object(sign_module, "CHECKSUMS", checksums)
        mocker.patch.object(sign_module, "MANIFEST", tmp_path / "manifest.json")
        mocker.patch.object(
            sign_module, "MANIFEST_SIGNATURE", tmp_path / "manifest.minisig"
        )
        mocker.patch.object(
            sign_module, "binary_path", lambda p: tmp_path / f"luminosity-{p}"
        )

        def signature_path(p: str) -> Path:
            path = tmp_path / f"luminosity-{p}.minisig"
            path.write_text(f"sig-for-{p}")
            return path

        mocker.patch.object(sign_module, "signature_path", signature_path)

    def test_requires_the_secret_key_env(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_RELEASE_SECRET_KEY", raising=False)
        with pytest.raises(Exit):
            sign(ctx)

    def test_signs_each_binary_and_manifest(
        self,
        ctx: MagicMock,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        self._setup(mocker, tmp_path)
        monkeypatch.setenv("LUMINOSITY_RELEASE_SECRET_KEY", "fake-key-material")
        mock_sign = mocker.patch.object(minisign, "sign")
        sign(ctx)
        # One signature per binary + one for the manifest.
        assert mock_sign.call_count == len(_PLATFORMS) + 1
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert set(manifest["binaries"]["luminosity"]["platforms"]) == set(
            _PLATFORMS
        )


def _generate_keypair(tmp_path: Path, name: str) -> tuple[Path, Path]:
    public_key = tmp_path / f"{name}.pub"
    secret_key = tmp_path / f"{name}.key"
    subprocess.run(
        [
            minisign.MINISIGN,
            "-G",
            "-W",
            "-f",
            "-p",
            str(public_key),
            "-s",
            str(secret_key),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return public_key, secret_key


@pytest.mark.skipif(_MINISIGN_ABSENT, reason="minisign not on PATH")
class TestMinisignRoundTrip:
    def test_sign_then_verify_succeeds(self, tmp_path: Path):
        public_key, secret_key = _generate_keypair(tmp_path, "release")
        payload = tmp_path / "payload.bin"
        payload.write_bytes(b"the-launcher")
        sig = tmp_path / "payload.bin.minisig"
        minisign.sign(secret_key, payload, sig)
        minisign.verify(payload, sig, public_key)

    def test_verify_rejects_a_non_release_key(self, tmp_path: Path):
        _, release_secret = _generate_keypair(tmp_path, "release")
        attacker_pub, _ = _generate_keypair(tmp_path, "attacker")
        payload = tmp_path / "payload.bin"
        payload.write_bytes(b"the-launcher")
        sig = tmp_path / "payload.bin.minisig"
        minisign.sign(release_secret, payload, sig)
        with pytest.raises(minisign.MinisignError):
            minisign.verify(payload, sig, attacker_pub)
