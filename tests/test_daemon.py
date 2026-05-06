"""Tests for daemon orchestration."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hoa.config import Config
from hoa.daemon import Daemon
from hoa.state import State


@pytest.fixture
def tmp_config(tmp_path):
    """Config path that doesn't exist (uses defaults)."""
    return tmp_path / "config.json"


@pytest.fixture
def tmp_state(tmp_path):
    return tmp_path / "state.json"


@pytest.fixture
def daemon(tmp_config, tmp_state):
    with patch("hoa.daemon.IdleMonitor"):
        d = Daemon(config_path=tmp_config, state_path=tmp_state)
    return d


class TestInit:
    def test_loads_config_and_state(self, tmp_config, tmp_state):
        with patch("hoa.daemon.IdleMonitor"):
            d = Daemon(config_path=tmp_config, state_path=tmp_state)
        assert isinstance(d.config, Config)
        assert isinstance(d.state, State)

    def test_creates_scheduler(self, daemon):
        assert daemon.scheduler is not None


class TestIdleDetection:
    def test_idle_pauses_scheduler(self, daemon):
        daemon.idle_monitor.just_became_idle = True
        daemon.idle_monitor.just_resumed = False
        daemon.idle_monitor.check = MagicMock()

        daemon._check_idle()

        assert daemon.scheduler.is_paused

    def test_resume_sends_welcome_back(self, daemon):
        daemon.idle_monitor.just_became_idle = False
        daemon.idle_monitor.just_resumed = True
        daemon.idle_monitor.check = MagicMock()
        daemon.scheduler.pause()

        with patch("hoa.daemon.send_toast") as mock_toast:
            daemon._check_idle()

        assert not daemon.scheduler.is_paused
        mock_toast.assert_called_once()
        toast_arg = mock_toast.call_args[0][0]
        assert "Welcome back" in toast_arg["text"]


class TestWaterCallback:
    def test_sends_toast(self, daemon):
        with patch("hoa.daemon.send_toast") as mock_toast:
            daemon._on_water()
        mock_toast.assert_called_once()

    def test_drink_logs_to_state(self, daemon, tmp_state):
        daemon._state_path = tmp_state
        daemon._drink(250)
        assert daemon.state.consumed_ml == 250

    def test_drink_resets_snoozes(self, daemon, tmp_state):
        daemon._state_path = tmp_state
        daemon.state.snooze_counts["water"] = 2
        daemon._drink(250)
        assert daemon.state.snooze_counts["water"] == 0


class TestSedentaryCallback:
    def test_sends_toast(self, daemon):
        with patch("hoa.daemon.send_toast") as mock_toast:
            daemon._on_sedentary()
        mock_toast.assert_called_once()

    def test_complete_logs(self, daemon, tmp_state):
        daemon._state_path = tmp_state
        daemon._complete("sedentary")
        assert daemon.state.sedentary_completions == 1


class TestEyeCallback:
    def test_sends_toast(self, daemon):
        with patch("hoa.daemon.send_toast") as mock_toast:
            daemon._on_eye_rest()
        mock_toast.assert_called_once()

    def test_complete_logs(self, daemon, tmp_state):
        daemon._state_path = tmp_state
        daemon._complete("eyes")
        assert daemon.state.eye_rest_completions == 1


class TestSnooze:
    def test_increments_count(self, daemon, tmp_state):
        daemon._state_path = tmp_state
        daemon._snooze("water")
        assert daemon.state.snooze_counts["water"] == 1

    def test_max_snoozes_resets(self, daemon, tmp_state):
        daemon._state_path = tmp_state
        daemon.state.snooze_counts["water"] = daemon.config.max_snoozes
        daemon._snooze("water")
        assert daemon.state.snooze_counts["water"] == 0


class TestEndOfDay:
    def test_sends_summary(self, daemon):
        with patch("hoa.daemon.send_toast") as mock_toast:
            daemon._on_end_of_day()
        mock_toast.assert_called_once()
        toast_arg = mock_toast.call_args[0][0]
        assert "summary" in toast_arg["text"].lower()


class TestMerge:
    def test_timers_within_window_merged(self, daemon):
        now = time.time()
        daemon._pending_timers = {"water": now, "sedentary": now + 30}
        # merge_window_min=2 → 120s window
        with patch("hoa.daemon.send_toast") as mock_toast:
            with patch("time.time", return_value=now):
                daemon._fire_pending()
        # Should send one merged toast
        mock_toast.assert_called_once()
        toast_arg = mock_toast.call_args[0][0]
        assert "water" in toast_arg["text"].lower() or "Drink" in toast_arg["text"]
