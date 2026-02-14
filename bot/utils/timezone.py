from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

OFFSET_RE = re.compile(r"^[+-](?:[0-9]|1[0-4])$")


def normalize_timezone_input(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None

    if OFFSET_RE.fullmatch(candidate):
        return f"UTC{candidate}"

    try:
        ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return None
    return candidate


def tzinfo_from_stored(value: str) -> timezone | ZoneInfo:
    if value.startswith("UTC+") or value.startswith("UTC-"):
        hours = int(value.split("UTC", maxsplit=1)[1])
        return timezone(timedelta(hours=hours))
    return ZoneInfo(value)


def local_now_from_timezone(value: str) -> datetime:
    return datetime.now(tz=timezone.utc).astimezone(tzinfo_from_stored(value))
