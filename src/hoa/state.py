"""State persistence for Health Office Assistant."""

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass
class State:
    """Daily state tracking."""

    date: str
    consumed_ml: int = 0
    drinks: list[dict] = field(default_factory=list)
    sedentary_completions: int = 0
    eye_rest_completions: int = 0
    snooze_counts: dict[str, int] = field(
        default_factory=lambda: {"water": 0, "sedentary": 0, "eyes": 0}
    )


def _fresh_state() -> State:
    return State(date=date.today().isoformat())


def load_state(path: Path, max_snoozes: int) -> State:
    """Load state from JSON, resetting if date != today."""
    if not path.exists():
        return _fresh_state()

    data = json.loads(path.read_text())
    today = date.today().isoformat()

    if data.get("date") != today:
        return _fresh_state()

    return State(
        date=data["date"],
        consumed_ml=data.get("consumed_ml", 0),
        drinks=data.get("drinks", []),
        sedentary_completions=data.get("sedentary_completions", 0),
        eye_rest_completions=data.get("eye_rest_completions", 0),
        snooze_counts=data.get("snooze_counts", {"water": 0, "sedentary": 0, "eyes": 0}),
    )


def save_state(state: State, path: Path) -> None:
    """Save state to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2) + "\n")


def log_drink(state: State, ml: int) -> State:
    """Log a drink, returning new state."""
    now = datetime.now()
    new_drinks = [*state.drinks, {"time": now.strftime("%H:%M"), "ml": ml}]
    return State(
        date=state.date,
        consumed_ml=state.consumed_ml + ml,
        drinks=new_drinks,
        sedentary_completions=state.sedentary_completions,
        eye_rest_completions=state.eye_rest_completions,
        snooze_counts=dict(state.snooze_counts),
    )


def log_completion(state: State, timer_type: str) -> State:
    """Log a timer completion, returning new state."""
    sed = state.sedentary_completions
    eye = state.eye_rest_completions

    if timer_type == "sedentary":
        sed += 1
    elif timer_type == "eyes":
        eye += 1

    return State(
        date=state.date,
        consumed_ml=state.consumed_ml,
        drinks=list(state.drinks),
        sedentary_completions=sed,
        eye_rest_completions=eye,
        snooze_counts=dict(state.snooze_counts),
    )


def increment_snooze(state: State, timer_type: str, max_snoozes: int) -> tuple[State, bool]:
    """Increment snooze count if under max. Returns (new_state, was_allowed)."""
    current = state.snooze_counts.get(timer_type, 0)
    if current >= max_snoozes:
        return state, False

    new_counts = dict(state.snooze_counts)
    new_counts[timer_type] = current + 1

    new_state = State(
        date=state.date,
        consumed_ml=state.consumed_ml,
        drinks=list(state.drinks),
        sedentary_completions=state.sedentary_completions,
        eye_rest_completions=state.eye_rest_completions,
        snooze_counts=new_counts,
    )
    return new_state, True


def reset_snoozes(state: State, timer_type: str) -> State:
    """Reset snooze count for a specific timer type."""
    new_counts = dict(state.snooze_counts)
    new_counts[timer_type] = 0

    return State(
        date=state.date,
        consumed_ml=state.consumed_ml,
        drinks=list(state.drinks),
        sedentary_completions=state.sedentary_completions,
        eye_rest_completions=state.eye_rest_completions,
        snooze_counts=new_counts,
    )
