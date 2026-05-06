"""Windows toast notification delivery."""

from __future__ import annotations

try:
    from windows_toasts import Toast, ToastButton, ToastText, WindowsToaster  # noqa: F401

    HAS_TOASTS = True
except ImportError:
    HAS_TOASTS = False


def build_water_toast(on_drink_callback, on_snooze_callback) -> dict:
    """Build a hydration reminder toast with volume buttons."""
    buttons = []
    for ml in (150, 250, 500):
        buttons.append(
            {"label": f"{ml}ml", "callback": lambda m=ml: on_drink_callback(m)}
        )
    buttons.append({"label": "Snooze", "callback": on_snooze_callback})
    return {"text": "Time to drink water!", "buttons": buttons}


def build_sedentary_toast(on_done_callback, on_snooze_callback) -> dict:
    """Build a stand-up reminder toast."""
    return {
        "text": "Time to stand up! Stretch for a minute.",
        "buttons": [
            {"label": "Done", "callback": on_done_callback},
            {"label": "Snooze", "callback": on_snooze_callback},
        ],
    }


def build_eye_toast(on_done_callback, on_snooze_callback) -> dict:
    """Build a 20-20-20 eye rest toast."""
    return {
        "text": "20-20-20: Look away for 20 seconds",
        "buttons": [
            {"label": "Done", "callback": on_done_callback},
            {"label": "Snooze", "callback": on_snooze_callback},
        ],
    }


def build_merged_toast(timer_types: list[str], callbacks: dict) -> dict:
    """Build a combined toast for multiple timers due at once."""
    if len(timer_types) == 1:
        t = timer_types[0]
        cb = callbacks[t]
        if t == "water":
            return build_water_toast(cb["on_drink"], cb["on_snooze"])
        elif t == "sedentary":
            return build_sedentary_toast(cb["on_done"], cb["on_snooze"])
        elif t == "eye":
            return build_eye_toast(cb["on_done"], cb["on_snooze"])

    # Multiple timers: combined text + simplified buttons
    parts = []
    buttons = []
    for t in timer_types:
        cb = callbacks[t]
        if t == "water":
            parts.append("Drink water")
            buttons.append(
                {"label": "250ml", "callback": lambda c=cb: c["on_drink"](250)}
            )
        elif t == "sedentary":
            parts.append("Stand up")
            buttons.append({"label": "Stood up", "callback": cb["on_done"]})
        elif t == "eye":
            parts.append("Eye rest (20s)")
            buttons.append({"label": "Eyes done", "callback": cb["on_done"]})

    # Single snooze for all
    first_snooze = callbacks[timer_types[0]].get(
        "on_snooze", callbacks[timer_types[-1]].get("on_snooze")
    )
    if first_snooze:
        buttons.append({"label": "Snooze all", "callback": first_snooze})

    return {"text": " + ".join(parts), "buttons": buttons}


def build_summary_toast(
    consumed_ml: int, goal_ml: int, sedentary: int, eye_rest: int
) -> dict:
    """Build end-of-day summary toast."""
    text = (
        f"Daily summary: {consumed_ml}/{goal_ml}ml water, "
        f"{sedentary} stand-ups, {eye_rest} eye rests"
    )
    return {"text": text, "buttons": []}


def build_welcome_back_toast() -> dict:
    """Build a welcome back toast after idle."""
    return {"text": "Welcome back!", "buttons": []}


def should_merge(
    next_due_times: dict[str, float], now: float, window_seconds: float
) -> list[str]:
    """Return timer types due within the merge window."""
    return [
        timer_type
        for timer_type, due_time in next_due_times.items()
        if due_time <= now + window_seconds
    ]


def send_toast(toast_config: dict) -> None:
    """Send a toast notification via windows_toasts. No-op on Linux."""
    if not HAS_TOASTS:
        return

    toaster = WindowsToaster("Health Office Assistant")
    toast = Toast()
    toast.text_fields = [ToastText(toast_config["text"])]
    for btn in toast_config.get("buttons", []):
        toast.AddAction(ToastButton(btn["label"], callback=btn["callback"]))
    toaster.show_toast(toast)
