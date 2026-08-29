"""2次重複判定（座標の近接＋店名の類似）と出典統合。仕様書v1.1 §4.3。"""
import math
from difflib import SequenceMatcher

from src.normalize import CONF_RANK, normalize_name

DIST_THRESHOLD_M = 50
SIM_THRESHOLD = 0.6


def haversine_m(lat1, lng1, lat2, lng2) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def _same_period_event(a: dict, b: dict) -> bool:
    """同じ地点で開始日・終了日が完全に一致する popup/event は、
    媒体ごとに名前が違っても同一イベントとみなす（リラックマ×SASUKE が
    3つの名前で登録された実例への対策）。常設店（new_cafe）には適用しない。"""
    if a["type"] != b["type"] or a["type"] not in ("popup", "event"):
        return False
    pa, pb = a["period"], b["period"]
    return pa["start"] is not None and pa["end"] is not None and pa == pb


def _same(a: dict, b: dict) -> bool:
    if None in (a["lat"], a["lng"], b["lat"], b["lng"]):
        return False
    if haversine_m(a["lat"], a["lng"], b["lat"], b["lng"]) > DIST_THRESHOLD_M:
        return False
    if _same_period_event(a, b):
        return True
    return name_similarity(a["name"], b["name"]) > SIM_THRESHOLD


def dedupe_by_location(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in items:
        merged = False
        for kept in out:
            if _same(kept, item):
                kept["sources"] = list(dict.fromkeys(kept["sources"] + item["sources"]))
                if CONF_RANK[item["confidence"]] > CONF_RANK[kept["confidence"]]:
                    kept["confidence"] = item["confidence"]
                merged = True
                break
        if not merged:
            out.append(dict(item))
    return out
