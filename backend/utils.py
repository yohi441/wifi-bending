from datetime import datetime

from zoneinfo import ZoneInfo

PH_TZ = ZoneInfo("Asia/Manila")
UTC_TZ = ZoneInfo("UTC")


def ph_time(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(PH_TZ).strftime(fmt)
