import pytest

from tasks.shared.eval import gate


class TestBelowFloor:
    def test_below_floor_is_true_under_the_bar(self):
        assert gate.below_floor(0.79) is True

    def test_at_floor_is_false(self):
        assert gate.below_floor(0.8) is False

    def test_above_floor_is_false(self):
        assert gate.below_floor(1.0) is False


class TestLiveRunEnabled:
    def test_defaults_on_when_env_absent(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("LUMINOSITY_EVAL_LIVE", raising=False)
        assert gate.live_run_enabled() is True

    @pytest.mark.parametrize(
        "value", ["off", "false", "0", "no", "OFF", " off "]
    )
    def test_falsey_values_disable(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ):
        monkeypatch.setenv("LUMINOSITY_EVAL_LIVE", value)
        assert gate.live_run_enabled() is False
