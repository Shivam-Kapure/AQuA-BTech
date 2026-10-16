"""Helpers for provider rate limits (Groq free tier: per-minute and per-day caps)."""

from __future__ import annotations

import re
from collections.abc import Mapping

_DURATION = re.compile(r"try again in ((?:\d+h)?(?:\d+m)?(?:[\d.]+s)?)", re.IGNORECASE)
_PARTS = re.compile(r"([\d.]+)([hms])")

# Waits longer than this are not worth blocking a request for; switch models instead.
MAX_WAIT_S = 60.0


def retry_delay_s(message: str, headers: Mapping[str, str] | None = None) -> float | None:
    """Seconds the provider asks us to wait, from Retry-After or text like 'try again in 1m20.5s'."""
    if headers:
        try:
            return float(headers.get("retry-after", ""))
        except ValueError:
            pass
    match = _DURATION.search(message or "")
    if not match or not match.group(1):
        return None
    scale = {"h": 3600.0, "m": 60.0, "s": 1.0}
    return sum(float(value) * scale[unit] for value, unit in _PARTS.findall(match.group(1)))


def is_daily_limit(message: str) -> bool:
    """True for per-day caps (tokens/requests per day), which short retries cannot fix."""
    text = (message or "").lower()
    return "per day" in text or "(tpd)" in text or "(rpd)" in text
