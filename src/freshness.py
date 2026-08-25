"""鮮度管理。仕様書v1.1 §4.3（v1.2で鮮度タグと365日ルールを追加）。

- 終了日を過ぎたものは非表示
- 終了日不明の popup / event は収集から30日で非表示
- new_cafe はオープンから365日で配信終了（1年経った店は「新規オープン」ではない）
- new_cafe には鮮度バケット（30/90/180/365日）を付け、アプリがタグ表示する
"""
from datetime import date

UNKNOWN_END_TTL_DAYS = 30
NEW_BADGE_DAYS = 90
NEW_CAFE_MAX_DAYS = 365
FRESHNESS_TIERS = (30, 90, 180, 365)


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _opened_days_ago(item: dict, today: str) -> int:
    start = item["period"]["start"] or item["collected_at"]
    return (_d(today) - _d(start)).days


def is_visible(item: dict, today: str) -> bool:
    t = _d(today)
    end = item["period"]["end"]
    if end is not None:
        return t <= _d(end)
    if item["type"] in ("popup", "event"):
        return (t - _d(item["collected_at"])).days <= UNKNOWN_END_TTL_DAYS
    return _opened_days_ago(item, today) <= NEW_CAFE_MAX_DAYS


def freshness_bucket(item: dict, today: str):
    """new_cafe の鮮度タグ。オープンからの日数が収まる最小の区切りを返す。

    30 / 90 / 180 / 365 のいずれか。オープン前（未来日付）は 30 扱い。
    popup / event は期間表示があるので対象外（None）。
    """
    if item["type"] != "new_cafe":
        return None
    days = max(0, _opened_days_ago(item, today))
    for tier in FRESHNESS_TIERS:
        if days <= tier:
            return tier
    return None  # 365日超は is_visible が False になるので通常ここには来ない


def is_new_badge(item: dict, today: str) -> bool:
    bucket = freshness_bucket(item, today)
    return bucket is not None and bucket <= NEW_BADGE_DAYS
