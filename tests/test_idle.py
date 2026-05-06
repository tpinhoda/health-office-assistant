"""Tests for idle detection."""

from unittest.mock import patch

from hoa.idle import IdleMonitor, IdleState, get_idle_seconds


class TestGetIdleSeconds:
    @patch("hoa.idle._get_idle_seconds_impl")
    def test_returns_mocked_value(self, mock_impl):
        mock_impl.return_value = 42.5
        assert get_idle_seconds() == 42.5


class TestIdleMonitor:
    @patch("hoa.idle._get_idle_seconds_impl")
    def test_transitions_active_to_idle(self, mock_impl):
        monitor = IdleMonitor(threshold_seconds=60)
        mock_impl.return_value = 61.0
        state = monitor.check()
        assert state == IdleState.IDLE
        assert monitor.just_became_idle is True
        assert monitor.just_resumed is False

    @patch("hoa.idle._get_idle_seconds_impl")
    def test_transitions_idle_to_active(self, mock_impl):
        monitor = IdleMonitor(threshold_seconds=60)
        # First go idle
        mock_impl.return_value = 61.0
        monitor.check()
        # Then resume
        mock_impl.return_value = 2.0
        state = monitor.check()
        assert state == IdleState.ACTIVE
        assert monitor.just_resumed is True
        assert monitor.just_became_idle is False

    @patch("hoa.idle._get_idle_seconds_impl")
    def test_flags_reset_on_subsequent_check(self, mock_impl):
        monitor = IdleMonitor(threshold_seconds=60)
        mock_impl.return_value = 61.0
        monitor.check()
        assert monitor.just_became_idle is True
        # Check again still idle - flag should reset
        monitor.check()
        assert monitor.just_became_idle is False

    @patch("hoa.idle._get_idle_seconds_impl")
    def test_stays_active_below_threshold(self, mock_impl):
        monitor = IdleMonitor(threshold_seconds=60)
        mock_impl.return_value = 30.0
        state = monitor.check()
        assert state == IdleState.ACTIVE
        assert monitor.just_became_idle is False
        assert monitor.just_resumed is False
