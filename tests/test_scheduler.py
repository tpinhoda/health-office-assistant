"""Tests for reminder scheduling."""

from datetime import datetime, time
from unittest.mock import MagicMock, patch

import pytest

from hoa.config import Config
from hoa.scheduler import (
    HealthScheduler,
    calculate_daily_goal_ml,
    calculate_suggested_ml,
    is_work_hours,
    seconds_until_work_start,
)


class TestIsWorkHours:
    def test_within_work_hours(self):
        now = datetime(2024, 1, 15, 10, 30)
        assert is_work_hours(now, "09:00", "17:00") is True

    def test_before_work_hours(self):
        now = datetime(2024, 1, 15, 7, 0)
        assert is_work_hours(now, "09:00", "17:00") is False

    def test_after_work_hours(self):
        now = datetime(2024, 1, 15, 18, 0)
        assert is_work_hours(now, "09:00", "17:00") is False

    def test_at_start_boundary(self):
        now = datetime(2024, 1, 15, 9, 0)
        assert is_work_hours(now, "09:00", "17:00") is True

    def test_at_end_boundary(self):
        now = datetime(2024, 1, 15, 17, 0)
        assert is_work_hours(now, "09:00", "17:00") is False


class TestCalculateDailyGoalMl:
    def test_standard_weight(self):
        assert calculate_daily_goal_ml(75.0) == 2625

    def test_light_weight(self):
        assert calculate_daily_goal_ml(50.0) == 1750

    def test_heavy_weight(self):
        assert calculate_daily_goal_ml(100.0) == 3500


class TestCalculateSuggestedMl:
    def test_even_distribution(self):
        assert calculate_suggested_ml(2000, 0, 10) == 200

    def test_partial_consumed(self):
        assert calculate_suggested_ml(2000, 1000, 5) == 200

    def test_goal_already_met(self):
        assert calculate_suggested_ml(2000, 2000, 5) == 0

    def test_goal_exceeded(self):
        assert calculate_suggested_ml(2000, 2500, 5) == 0

    def test_no_remaining_intervals(self):
        assert calculate_suggested_ml(2000, 1000, 0) == 0


class TestSecondsUntilWorkStart:
    def test_before_work_start_same_day(self):
        now = datetime(2024, 1, 15, 7, 0, 0)
        result = seconds_until_work_start(now, "09:00")
        assert result == 7200.0  # 2 hours

    def test_after_work_start_wraps_to_tomorrow(self):
        now = datetime(2024, 1, 15, 10, 0, 0)
        result = seconds_until_work_start(now, "09:00")
        # Should be 23 hours = 82800 seconds
        assert result == 82800.0

    def test_at_exact_work_start(self):
        now = datetime(2024, 1, 15, 9, 0, 0)
        result = seconds_until_work_start(now, "09:00")
        # Already at start, wraps to tomorrow
        assert result == 86400.0


class TestHealthScheduler:
    def _make_scheduler(self):
        config = Config()
        callbacks = {
            "on_water": MagicMock(),
            "on_sedentary": MagicMock(),
            "on_eye_rest": MagicMock(),
            "on_end_of_day": MagicMock(),
        }
        scheduler = HealthScheduler(
            config,
            on_water=callbacks["on_water"],
            on_sedentary=callbacks["on_sedentary"],
            on_eye_rest=callbacks["on_eye_rest"],
            on_end_of_day=callbacks["on_end_of_day"],
        )
        return scheduler, callbacks

    def test_initial_state_not_paused(self):
        scheduler, _ = self._make_scheduler()
        assert scheduler.is_paused is False

    def test_pause(self):
        scheduler, _ = self._make_scheduler()
        scheduler.pause()
        assert scheduler.is_paused is True

    def test_resume(self):
        scheduler, _ = self._make_scheduler()
        scheduler.pause()
        scheduler.resume()
        assert scheduler.is_paused is False

    @patch("hoa.scheduler.BackgroundScheduler")
    def test_start_starts_scheduler(self, mock_cls):
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        scheduler, _ = self._make_scheduler()
        scheduler._scheduler = mock_instance
        scheduler.start()
        mock_instance.start.assert_called_once()

    @patch("hoa.scheduler.BackgroundScheduler")
    def test_stop_shuts_down_scheduler(self, mock_cls):
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        scheduler, _ = self._make_scheduler()
        scheduler._scheduler = mock_instance
        scheduler.stop()
        mock_instance.shutdown.assert_called_once()
