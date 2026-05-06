"""Configuration management for Health Office Assistant."""

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

DEFAULT_CONFIG = {
    "weight_kg": 75.0,
    "work_start": "09:00",
    "work_end": "17:00",
    "water_interval_min": 30,
    "sedentary_interval_min": 45,
    "eye_interval_min": 20,
    "idle_threshold_min": 5,
    "snooze_duration_min": 5,
    "max_snoozes": 3,
    "merge_window_min": 2,
    "sound_enabled": True,
}


@dataclass
class Config:
    """Application configuration."""

    weight_kg: float = 75.0
    work_start: str = "09:00"
    work_end: str = "17:00"
    water_interval_min: int = 30
    sedentary_interval_min: int = 45
    eye_interval_min: int = 20
    idle_threshold_min: int = 5
    snooze_duration_min: int = 5
    max_snoozes: int = 3
    merge_window_min: int = 2
    sound_enabled: bool = True


def _validate(config: Config) -> None:
    """Validate config values, raising ValueError on invalid."""
    if config.weight_kg <= 0:
        raise ValueError("weight_kg must be positive")

    positive_intervals = [
        "water_interval_min",
        "sedentary_interval_min",
        "eye_interval_min",
        "idle_threshold_min",
        "snooze_duration_min",
        "max_snoozes",
        "merge_window_min",
    ]
    for field_name in positive_intervals:
        if getattr(config, field_name) <= 0:
            raise ValueError(f"{field_name} must be positive")

    if config.work_end <= config.work_start:
        raise ValueError("work_end must not be before work_start")


def load_config(path: Path | None = None) -> Config:
    """Load config from JSON file, merging with defaults.

    Args:
        path: Path to config file. Defaults to ~/.hoa/config.json.

    Returns:
        Validated Config instance.
    """
    if path is None:
        path = Path.home() / ".hoa" / "config.json"

    data = {}
    if path.exists():
        data = json.loads(path.read_text())

    # Filter to known fields only
    known = {f.name for f in fields(Config)}
    filtered = {k: v for k, v in data.items() if k in known}

    config = Config(**filtered)
    _validate(config)
    return config


def save_config(config: Config, path: Path | None = None) -> None:
    """Save config to JSON file.

    Args:
        config: Config instance to save.
        path: Path to config file. Defaults to ~/.hoa/config.json.
    """
    if path is None:
        path = Path.home() / ".hoa" / "config.json"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2) + "\n")
