"""鮮度管理。仕様書v1.1 §4.3。

- 終了日を過ぎたものは非表示
- 終了日不明の popup / event は収集から30日で非表示
- new_cafe はオープンから90日だけ「新着」扱い（データ自体は保持）
"""
from datetime import date

UNKNOWN_END_TTL_DAYS = 30
NEW_BADGE_DAYS = 90


def _d(s: str) -> date:
    return date.fromisoformat(s)


def is_visible(item: dict, today: str) -> bool:
    t = _d(today)
    end = item["period"]["end"]
    if end is not None:
        return t <= _d(end)
    if item["type"] in ("popup", "event"):
        return (t - _d(item["collected_at"])).days <= UNKNOWN_END_TTL_DAYS
    return True  # new_cafe（常設）


def is_new_badge(item: dict, today: str) -> bool:
    if item["type"] != "new_cafe":
        return False
    start = item["period"]["start"] or item["collected_at"]
    return 0 <= (_d(today) - _d(start)).days <= NEW_BADGE_DAYS
