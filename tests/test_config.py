"""Tests for configuration management."""

import json
from pathlib import Path

import pytest

from hoa.config import Config, DEFAULT_CONFIG, load_config, save_config


class TestLoadConfigDefaults:
    """load_config returns defaults when no file exists."""

    def test_returns_config_with_defaults_when_no_file(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.json")
        assert config.weight_kg == 75.0
        assert config.work_start == "09:00"
        assert config.work_end == "17:00"
        assert config.water_interval_min == 30
        assert config.sedentary_interval_min == 45
        assert config.eye_interval_min == 20
        assert config.idle_threshold_min == 5
        assert config.snooze_duration_min == 5
        assert config.max_snoozes == 3
        assert config.merge_window_min == 2
        assert config.sound_enabled is True


class TestLoadConfigFromFile:
    """load_config reads from file and merges with defaults."""

    def test_overrides_specified_values(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"weight_kg": 90.0, "max_snoozes": 5}))
        config = load_config(config_file)
        assert config.weight_kg == 90.0
        assert config.max_snoozes == 5
        # Unspecified values remain defaults
        assert config.work_start == "09:00"
        assert config.sound_enabled is True

    def test_ignores_unknown_keys(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"unknown_key": "value"}))
        config = load_config(config_file)
        assert config.weight_kg == 75.0


class TestConfigValidation:
    """Validation rejects invalid values."""

    def test_negative_water_interval(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"water_interval_min": -1}))
        with pytest.raises(ValueError, match="water_interval_min"):
            load_config(config_file)

    def test_negative_sedentary_interval(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"sedentary_interval_min": 0}))
        with pytest.raises(ValueError, match="sedentary_interval_min"):
            load_config(config_file)

    def test_work_end_before_work_start(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"work_start": "17:00", "work_end": "09:00"}))
        with pytest.raises(ValueError, match="work_end.*before.*work_start"):
            load_config(config_file)

    def test_negative_weight(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"weight_kg": -10}))
        with pytest.raises(ValueError, match="weight_kg"):
            load_config(config_file)


class TestSaveConfig:
    """save_config writes JSON."""

    def test_roundtrip(self, tmp_path):
        config_file = tmp_path / "config.json"
        config = Config(weight_kg=80.0, max_snoozes=2)
        save_config(config, config_file)
        loaded = load_config(config_file)
        assert loaded.weight_kg == 80.0
        assert loaded.max_snoozes == 2

    def test_creates_parent_directories(self, tmp_path):
        config_file = tmp_path / "sub" / "dir" / "config.json"
        config = Config()
        save_config(config, config_file)
        assert config_file.exists()
