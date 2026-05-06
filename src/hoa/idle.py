"""Idle detection via Win32 GetLastInputInfo with cross-platform fallback."""

import ctypes
import ctypes.wintypes
import sys
from enum import Enum


class IdleState(Enum):
    ACTIVE = "active"
    IDLE = "idle"


def _get_idle_seconds_win32() -> float:
    """Get seconds since last user input via Win32 GetLastInputInfo."""

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.UINT),
            ("dwTime", ctypes.wintypes.DWORD),
        ]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))  # type: ignore[attr-defined]
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime  # type: ignore[attr-defined]
    return millis / 1000.0


def _get_idle_seconds_fallback() -> float:
    """Fallback for non-Windows: always report active (0 seconds idle)."""
    return 0.0


# Select implementation based on platform
if sys.platform == "win32":
    _get_idle_seconds_impl = _get_idle_seconds_win32
else:
    _get_idle_seconds_impl = _get_idle_seconds_fallback


def get_idle_seconds() -> float:
    """Get seconds since last user input. Cross-platform."""
    return _get_idle_seconds_impl()


class IdleMonitor:
    """Monitor idle state with transition detection."""

    def __init__(self, threshold_seconds: float):
        self.threshold = threshold_seconds
        self._state = IdleState.ACTIVE
        self._just_became_idle = False
        self._just_resumed = False

    def check(self) -> IdleState:
        """Poll idle state. Sets transition flags."""
        self._just_became_idle = False
        self._just_resumed = False

        idle_secs = _get_idle_seconds_impl()

        if idle_secs >= self.threshold:
            if self._state == IdleState.ACTIVE:
                self._just_became_idle = True
            self._state = IdleState.IDLE
        else:
            if self._state == IdleState.IDLE:
                self._just_resumed = True
            self._state = IdleState.ACTIVE

        return self._state

    @property
    def just_became_idle(self) -> bool:
        return self._just_became_idle

    @property
    def just_resumed(self) -> bool:
        return self._just_resumed

    @property
    def state(self) -> IdleState:
        return self._state
