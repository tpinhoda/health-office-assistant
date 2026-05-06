"""Tests for state persistence."""

import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from hoa.state import (
    State,
    increment_snooze,
    load_state,
    log_completion,
    log_drink,
    reset_snoozes,
    save_state,
)


class TestLoadState:
    """Tests for load_state."""

    def test_fresh_state_when_file_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = load_state(path, max_snoozes=3)
        assert state.date == date.today().isoformat()
        assert state.consumed_ml == 0
        assert state.drinks == []
        assert state.sedentary_completions == 0
        assert state.eye_rest_completions == 0
        assert state.snooze_counts == {"water": 0, "sedentary": 0, "eyes": 0}

    def test_resets_when_date_changed(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        old_state = {
            "date": "2020-01-01",
            "consumed_ml": 500,
            "drinks": [{"time": "10:00", "ml": 500}],
            "sedentary_completions": 2,
            "eye_rest_completions": 3,
            "snooze_counts": {"water": 1, "sedentary": 2, "eyes": 0},
        }
        path.write_text(json.dumps(old_state))
        state = load_state(path, max_snoozes=3)
        assert state.date == date.today().isoformat()
        assert state.consumed_ml == 0
        assert state.drinks == []

    def test_loads_current_date_state(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        today = date.today().isoformat()
        data = {
            "date": today,
            "consumed_ml": 250,
            "drinks": [{"time": "09:30", "ml": 250}],
            "sedentary_completions": 1,
            "eye_rest_completions": 0,
            "snooze_counts": {"water": 0, "sedentary": 0, "eyes": 0},
        }
        path.write_text(json.dumps(data))
        state = load_state(path, max_snoozes=3)
        assert state.consumed_ml == 250
        assert state.drinks == [{"time": "09:30", "ml": 250}]


class TestLogDrink:
    """Tests for log_drink."""

    @patch("hoa.state.datetime")
    def test_increments_consumed_and_appends(self, mock_dt: object) -> None:
        mock_dt.now.return_value = datetime(2024, 1, 1, 10, 30)
        state = State(date="2024-01-01")
        new = log_drink(state, 250)
        assert new.consumed_ml == 250
        assert new.drinks == [{"time": "10:30", "ml": 250}]
        # Original unchanged
        assert state.consumed_ml == 0


class TestLogCompletion:
    """Tests for log_completion."""

    def test_increments_sedentary(self) -> None:
        state = State(date="2024-01-01")
        new = log_completion(state, "sedentary")
        assert new.sedentary_completions == 1

    def test_increments_eye_rest(self) -> None:
        state = State(date="2024-01-01")
        new = log_completion(state, "eyes")
        assert new.eye_rest_completions == 1


class TestIncrementSnooze:
    """Tests for increment_snooze."""

    def test_allows_snooze_under_max(self) -> None:
        state = State(date="2024-01-01")
        new, allowed = increment_snooze(state, "water", max_snoozes=3)
        assert allowed is True
        assert new.snooze_counts["water"] == 1

    def test_rejects_snooze_at_max(self) -> None:
        state = State(
            date="2024-01-01",
            snooze_counts={"water": 3, "sedentary": 0, "eyes": 0},
        )
        new, allowed = increment_snooze(state, "water", max_snoozes=3)
        assert allowed is False
        assert new.snooze_counts["water"] == 3


class TestResetSnoozes:
    """Tests for reset_snoozes."""

    def test_resets_specific_timer(self) -> None:
        state = State(
            date="2024-01-01",
            snooze_counts={"water": 2, "sedentary": 1, "eyes": 0},
        )
        new = reset_snoozes(state, "water")
        assert new.snooze_counts["water"] == 0
        assert new.snooze_counts["sedentary"] == 1


class TestSaveState:
    """Tests for save_state."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = State(date="2024-01-01", consumed_ml=500)
        save_state(state, path)
        loaded = json.loads(path.read_text())
        assert loaded["consumed_ml"] == 500
        assert loaded["date"] == "2024-01-01"
