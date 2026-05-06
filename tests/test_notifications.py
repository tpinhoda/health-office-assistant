"""Tests for notification delivery."""

from unittest.mock import MagicMock

from hoa.notifications import (
    build_eye_toast,
    build_merged_toast,
    build_sedentary_toast,
    build_summary_toast,
    build_water_toast,
    build_welcome_back_toast,
    send_toast,
    should_merge,
)


class TestBuildWaterToast:
    def test_returns_dict_with_text_and_buttons(self):
        on_drink = MagicMock()
        on_snooze = MagicMock()
        result = build_water_toast(on_drink, on_snooze)

        assert isinstance(result, dict)
        assert "text" in result
        assert "buttons" in result
        assert len(result["buttons"]) == 4  # 150ml, 250ml, 500ml, Snooze

    def test_button_labels(self):
        result = build_water_toast(MagicMock(), MagicMock())
        labels = [b["label"] for b in result["buttons"]]
        assert "150ml" in labels
        assert "250ml" in labels
        assert "500ml" in labels
        assert "Snooze" in labels

    def test_drink_callbacks_pass_amount(self):
        on_drink = MagicMock()
        on_snooze = MagicMock()
        result = build_water_toast(on_drink, on_snooze)

        # Find the 250ml button and invoke its callback
        btn = next(b for b in result["buttons"] if b["label"] == "250ml")
        btn["callback"]()
        on_drink.assert_called_once_with(250)

    def test_snooze_callback(self):
        on_drink = MagicMock()
        on_snooze = MagicMock()
        result = build_water_toast(on_drink, on_snooze)

        btn = next(b for b in result["buttons"] if b["label"] == "Snooze")
        btn["callback"]()
        on_snooze.assert_called_once()


class TestBuildSedentaryToast:
    def test_structure(self):
        result = build_sedentary_toast(MagicMock(), MagicMock())
        assert "stand" in result["text"].lower()
        assert len(result["buttons"]) == 2

    def test_button_labels(self):
        result = build_sedentary_toast(MagicMock(), MagicMock())
        labels = [b["label"] for b in result["buttons"]]
        assert "Done" in labels
        assert "Snooze" in labels


class TestBuildEyeToast:
    def test_structure(self):
        result = build_eye_toast(MagicMock(), MagicMock())
        assert "20" in result["text"]
        assert len(result["buttons"]) == 2

    def test_done_callback(self):
        on_done = MagicMock()
        result = build_eye_toast(on_done, MagicMock())
        btn = next(b for b in result["buttons"] if b["label"] == "Done")
        btn["callback"]()
        on_done.assert_called_once()


class TestBuildMergedToast:
    def test_combines_types(self):
        callbacks = {
            "water": {"on_drink": MagicMock(), "on_snooze": MagicMock()},
            "sedentary": {"on_done": MagicMock(), "on_snooze": MagicMock()},
        }
        result = build_merged_toast(["water", "sedentary"], callbacks)
        assert isinstance(result, dict)
        assert "water" in result["text"].lower() or "drink" in result["text"].lower()
        assert len(result["buttons"]) > 0

    def test_single_type_delegates(self):
        callbacks = {
            "eye": {"on_done": MagicMock(), "on_snooze": MagicMock()},
        }
        result = build_merged_toast(["eye"], callbacks)
        assert "20" in result["text"]


class TestBuildSummaryToast:
    def test_contains_stats(self):
        result = build_summary_toast(
            consumed_ml=1500, goal_ml=2000, sedentary=5, eye_rest=8
        )
        assert "1500" in result["text"] or "1.5" in result["text"]
        assert isinstance(result, dict)
        assert "buttons" in result


class TestBuildWelcomeBackToast:
    def test_structure(self):
        result = build_welcome_back_toast()
        assert "welcome" in result["text"].lower()
        assert isinstance(result, dict)


class TestShouldMerge:
    def test_nothing_due(self):
        next_due = {"water": 100.0, "sedentary": 200.0, "eye": 150.0}
        result = should_merge(next_due, now=50.0, window_seconds=10.0)
        assert result == []

    def test_single_due(self):
        next_due = {"water": 100.0, "sedentary": 200.0, "eye": 150.0}
        result = should_merge(next_due, now=95.0, window_seconds=10.0)
        assert result == ["water"]

    def test_multiple_due_within_window(self):
        next_due = {"water": 100.0, "sedentary": 105.0, "eye": 150.0}
        result = should_merge(next_due, now=95.0, window_seconds=15.0)
        assert sorted(result) == ["sedentary", "water"]

    def test_all_due(self):
        next_due = {"water": 100.0, "sedentary": 105.0, "eye": 108.0}
        result = should_merge(next_due, now=95.0, window_seconds=15.0)
        assert sorted(result) == ["eye", "sedentary", "water"]


class TestSendToast:
    def test_noop_without_library(self, monkeypatch):
        import hoa.notifications as mod

        monkeypatch.setattr(mod, "HAS_TOASTS", False)
        # Should not raise
        send_toast({"text": "hello", "buttons": []})
