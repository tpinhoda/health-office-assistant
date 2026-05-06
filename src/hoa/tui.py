"""Textual TUI dashboard for Health Office Assistant."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, ProgressBar, Static

from hoa.config import load_config
from hoa.daemon import DEFAULT_STATE_PATH
from hoa.scheduler import calculate_daily_goal_ml
from hoa.state import load_state, log_drink, save_state

DRINK_SIZES = [150, 200, 250, 300, 500]


class HoaDashboard(App):
    """Health Office Assistant TUI dashboard."""

    CSS = """
    #water-section { height: auto; margin: 1 2; }
    #counters { height: auto; margin: 1 2; }
    #counters Horizontal { height: auto; }
    #counters Label { width: 1fr; }
    #timers { height: auto; margin: 1 2; }
    #timers Horizontal { height: auto; }
    #timers Label { width: 1fr; }
    #drinks-table { height: 1fr; margin: 1 2; }
    #size-selector { height: auto; margin: 1 2; display: none; }
    ProgressBar { width: 100%; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "log_drink", "Log Drink"),
        Binding("p", "pause_resume", "Pause/Resume"),
    ]

    TITLE = "Health Office Assistant"

    def __init__(self):
        super().__init__()
        self._paused = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Vertical(id="water-section"):
                yield Label("Water Progress", id="water-label")
                yield ProgressBar(total=100, show_eta=False, id="water-bar")
            with Vertical(id="counters"):
                with Horizontal():
                    yield Label("Sedentary breaks: 0", id="sedentary-count")
                    yield Label("Eye rests: 0", id="eye-count")
            with Vertical(id="timers"):
                with Horizontal():
                    yield Label("Water: --:--", id="timer-water")
                    yield Label("Sedentary: --:--", id="timer-sedentary")
                    yield Label("Eyes: --:--", id="timer-eyes")
            with Vertical(id="drinks-table"):
                yield DataTable(id="drinks")
            with Vertical(id="size-selector"):
                yield Label("Select size: " + " ".join(f"[{i+1}]{s}ml" for i, s in enumerate(DRINK_SIZES)), id="size-prompt")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#drinks", DataTable)
        table.add_columns("Time", "Amount (ml)")
        self._refresh_data()
        self.set_interval(5, self._refresh_data)

    def _refresh_data(self) -> None:
        if self._paused:
            return
        config = load_config()
        state = load_state(DEFAULT_STATE_PATH, config.max_snoozes)
        goal = calculate_daily_goal_ml(config.weight_kg)

        # Water progress
        pct = min(100, int(state.consumed_ml / goal * 100)) if goal > 0 else 0
        self.query_one("#water-label", Label).update(
            f"Water: {state.consumed_ml} / {goal} ml ({pct}%)"
        )
        bar = self.query_one("#water-bar", ProgressBar)
        bar.update(progress=pct)

        # Counters
        self.query_one("#sedentary-count", Label).update(
            f"Sedentary breaks: {state.sedentary_completions}"
        )
        self.query_one("#eye-count", Label).update(
            f"Eye rests: {state.eye_rest_completions}"
        )

        # Timer countdowns (read from state file timestamps if available)
        self.query_one("#timer-water", Label).update(
            f"Water: every {config.water_interval_min}min"
        )
        self.query_one("#timer-sedentary", Label).update(
            f"Sedentary: every {config.sedentary_interval_min}min"
        )
        self.query_one("#timer-eyes", Label).update(
            f"Eyes: every {config.eye_interval_min}min"
        )

        # Drinks table
        table = self.query_one("#drinks", DataTable)
        table.clear()
        for drink in state.drinks:
            table.add_row(drink["time"], str(drink["ml"]))

    def action_log_drink(self) -> None:
        selector = self.query_one("#size-selector")
        selector.styles.display = "block" if selector.styles.display == "none" else "none"

    def on_key(self, event) -> None:
        selector = self.query_one("#size-selector")
        if selector.styles.display != "none" and event.key in "12345":
            idx = int(event.key) - 1
            if 0 <= idx < len(DRINK_SIZES):
                self._do_log_drink(DRINK_SIZES[idx])
                selector.styles.display = "none"

    def _do_log_drink(self, ml: int) -> None:
        config = load_config()
        state = load_state(DEFAULT_STATE_PATH, config.max_snoozes)
        state = log_drink(state, ml)
        save_state(state, DEFAULT_STATE_PATH)
        self._refresh_data()
        self.notify(f"Logged {ml}ml drink")

    def action_pause_resume(self) -> None:
        self._paused = not self._paused
        status = "paused" if self._paused else "resumed"
        self.notify(f"Refresh {status}")


def run_tui() -> None:
    """Launch the TUI dashboard."""
    app = HoaDashboard()
    app.run()
