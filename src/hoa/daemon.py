"""Background daemon orchestration."""

import time
from pathlib import Path

from hoa.config import Config, load_config
from hoa.idle import IdleMonitor
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
from hoa.scheduler import HealthScheduler, calculate_daily_goal_ml
from hoa.state import (
    State,
    increment_snooze,
    load_state,
    log_completion,
    log_drink,
    reset_snoozes,
    save_state,
)

DEFAULT_STATE_PATH = Path.home() / ".hoa" / "state.json"


class Daemon:
    """Main daemon tying scheduler, idle detection, state, and notifications."""

    def __init__(self, config_path: Path | None = None, state_path: Path | None = None):
        self._state_path = state_path or DEFAULT_STATE_PATH
        self.config = load_config(config_path)
        self.state = load_state(self._state_path, self.config.max_snoozes)
        self.idle_monitor = IdleMonitor(self.config.idle_threshold_min * 60)
        self.scheduler = HealthScheduler(
            config=self.config,
            on_water=self._on_water,
            on_sedentary=self._on_sedentary,
            on_eye_rest=self._on_eye_rest,
            on_end_of_day=self._on_end_of_day,
        )
        self._pending_timers: dict[str, float] = {}

    def run(self):
        """Main loop: start scheduler, poll idle every 30s."""
        self.scheduler.start()
        try:
            while True:
                self._check_idle()
                time.sleep(30)
        except KeyboardInterrupt:
            self.scheduler.stop()

    def _check_idle(self):
        """Poll idle state and pause/resume scheduler."""
        self.idle_monitor.check()
        if self.idle_monitor.just_became_idle:
            self.scheduler.pause()
        elif self.idle_monitor.just_resumed:
            self.scheduler.resume()
            send_toast(build_welcome_back_toast())

    def _on_water(self):
        """Handle water timer firing."""
        now = time.time()
        self._pending_timers["water"] = now
        self._fire_pending()

    def _on_sedentary(self):
        """Handle sedentary timer firing."""
        now = time.time()
        self._pending_timers["sedentary"] = now
        self._fire_pending()

    def _on_eye_rest(self):
        """Handle eye rest timer firing."""
        now = time.time()
        self._pending_timers["eye"] = now
        self._fire_pending()

    def _on_end_of_day(self):
        """Send end-of-day summary."""
        goal = calculate_daily_goal_ml(self.config.weight_kg)
        toast = build_summary_toast(
            consumed_ml=self.state.consumed_ml,
            goal_ml=goal,
            sedentary=self.state.sedentary_completions,
            eye_rest=self.state.eye_rest_completions,
        )
        send_toast(toast)

    def _fire_pending(self):
        """Check merge window and fire pending timers."""
        now = time.time()
        window = self.config.merge_window_min * 60
        due = should_merge(self._pending_timers, now, window)

        if not due:
            return

        callbacks = {}
        for t in due:
            if t == "water":
                callbacks[t] = {
                    "on_drink": self._drink,
                    "on_snooze": lambda: self._snooze("water"),
                }
            elif t == "sedentary":
                callbacks[t] = {
                    "on_done": lambda: self._complete("sedentary"),
                    "on_snooze": lambda: self._snooze("sedentary"),
                }
            elif t == "eye":
                callbacks[t] = {
                    "on_done": lambda: self._complete("eyes"),
                    "on_snooze": lambda: self._snooze("eyes"),
                }

        toast = build_merged_toast(due, callbacks)
        send_toast(toast)

        # Clear fired timers
        for t in due:
            self._pending_timers.pop(t, None)

    def _drink(self, ml: int):
        """Log a drink and persist state."""
        self.state = log_drink(self.state, ml)
        self.state = reset_snoozes(self.state, "water")
        save_state(self.state, self._state_path)

    def _snooze(self, timer_type: str):
        """Handle snooze, respecting max."""
        self.state, allowed = increment_snooze(
            self.state, timer_type, self.config.max_snoozes
        )
        if not allowed:
            self.state = reset_snoozes(self.state, timer_type)
        save_state(self.state, self._state_path)

    def _complete(self, timer_type: str):
        """Log timer completion and persist."""
        self.state = log_completion(self.state, timer_type)
        self.state = reset_snoozes(self.state, timer_type)
        save_state(self.state, self._state_path)
