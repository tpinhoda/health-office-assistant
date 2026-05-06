"""Reminder scheduling logic."""

from datetime import datetime, time, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from hoa.config import Config


def is_work_hours(now: datetime, start: str, end: str) -> bool:
    """Check if current time is within work hours.

    Args:
        now: Current datetime.
        start: Work start time as "HH:MM".
        end: Work end time as "HH:MM".

    Returns:
        True if now is >= start and < end.
    """
    h, m = map(int, start.split(":"))
    start_time = time(h, m)
    h, m = map(int, end.split(":"))
    end_time = time(h, m)
    current = now.time()
    return start_time <= current < end_time


def calculate_daily_goal_ml(weight_kg: float) -> int:
    """Calculate daily water goal: 35ml per kg of body weight."""
    return int(weight_kg * 35)


def calculate_suggested_ml(goal_ml: int, consumed_ml: int, remaining_intervals: int) -> int:
    """How much to drink per interval to hit goal.

    Returns 0 if goal already met or no intervals remain.
    """
    remaining = goal_ml - consumed_ml
    if remaining <= 0 or remaining_intervals <= 0:
        return 0
    return remaining // remaining_intervals


def seconds_until_work_start(now: datetime, work_start: str) -> float:
    """Seconds until next work start (today or tomorrow).

    If now is before work_start today, returns seconds until today's start.
    Otherwise returns seconds until tomorrow's start.
    """
    h, m = map(int, work_start.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target > now:
        return (target - now).total_seconds()
    # Next day
    target += timedelta(days=1)
    return (target - now).total_seconds()


class HealthScheduler:
    """Manages periodic health reminder timers using APScheduler."""

    def __init__(
        self,
        config: Config,
        on_water,
        on_sedentary,
        on_eye_rest,
        on_end_of_day,
    ):
        self._config = config
        self._on_water = on_water
        self._on_sedentary = on_sedentary
        self._on_eye_rest = on_eye_rest
        self._on_end_of_day = on_end_of_day
        self._paused = False
        self._scheduler = BackgroundScheduler()

        # Interval jobs
        self._scheduler.add_job(
            self._fire_water,
            "interval",
            minutes=config.water_interval_min,
            id="water",
        )
        self._scheduler.add_job(
            self._fire_sedentary,
            "interval",
            minutes=config.sedentary_interval_min,
            id="sedentary",
        )
        self._scheduler.add_job(
            self._fire_eye_rest,
            "interval",
            minutes=config.eye_interval_min,
            id="eye_rest",
        )

        # End-of-day cron job
        h, m = map(int, config.work_end.split(":"))
        self._scheduler.add_job(
            self._fire_end_of_day,
            "cron",
            hour=h,
            minute=m,
            id="end_of_day",
        )

    def _fire_water(self):
        if not self._paused:
            self._on_water()

    def _fire_sedentary(self):
        if not self._paused:
            self._on_sedentary()

    def _fire_eye_rest(self):
        if not self._paused:
            self._on_eye_rest()

    def _fire_end_of_day(self):
        self._on_end_of_day()

    def start(self):
        """Start the scheduler."""
        self._scheduler.start()

    def stop(self):
        """Stop the scheduler."""
        self._scheduler.shutdown()

    def pause(self):
        """Pause reminder delivery."""
        self._paused = True

    def resume(self):
        """Resume reminder delivery."""
        self._paused = False

    @property
    def is_paused(self) -> bool:
        """Whether reminders are currently paused."""
        return self._paused
