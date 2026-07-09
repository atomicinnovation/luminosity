import pytest

from tasks.shared.env import env_flag_enabled


class TestEnvFlagEnabled:
    def test_defaults_on_when_env_absent(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("LUMINOSITY_TEST_FLAG", raising=False)
        assert env_flag_enabled("LUMINOSITY_TEST_FLAG", default="on") is True

    def test_defaults_off_when_env_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_TEST_FLAG", raising=False)
        assert env_flag_enabled("LUMINOSITY_TEST_FLAG", default="off") is False

    @pytest.mark.parametrize("value", [" OFF ", "FALSE", "No", "0", "off"])
    def test_falsey_values_disable(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ):
        # Case/whitespace variants prove both .strip() and .lower() are
        # load-bearing: a regression dropping either normalisation is caught.
        monkeypatch.setenv("LUMINOSITY_TEST_FLAG", value)
        assert env_flag_enabled("LUMINOSITY_TEST_FLAG", default="on") is False

    @pytest.mark.parametrize("value", ["on", "1", "yes", "true", " ON ", "x"])
    def test_non_falsey_values_enable(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ):
        monkeypatch.setenv("LUMINOSITY_TEST_FLAG", value)
        assert env_flag_enabled("LUMINOSITY_TEST_FLAG", default="off") is True
