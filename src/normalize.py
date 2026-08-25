"""表記ゆれの正規化と1次重複判定（店名＋住所文字列）。仕様書v1.1 §4.3。"""
import re
import unicodedata

from src.models import make_id

CONF_RANK = {"unverified": 0, "media": 1, "official": 2}
_STRIP = re.compile(r"[\s　・‐−–—\-]+")


def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    return _STRIP.sub("", s)


def normalize_address(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("丁目", "-").replace("番地", "-").replace("番", "-").replace("号", "")
    return _STRIP.sub("", s).rstrip("-")


def _key(item: dict) -> str:
    return f"{normalize_name(item['name'])}|{normalize_address(item['address'])}"


def _merge(base: dict, other: dict) -> dict:
    merged = dict(base)
    merged["sources"] = list(dict.fromkeys(base["sources"] + other["sources"]))
    if CONF_RANK[other["confidence"]] > CONF_RANK[base["confidence"]]:
        merged["confidence"] = other["confidence"]
    # 座標・開始日・終了日は「埋まっている方」を優先
    for f in ("lat", "lng"):
        if merged[f] is None and other[f] is not None:
            merged[f] = other[f]
    period = dict(merged["period"])
    for f in ("start", "end"):
        if period[f] is None and other["period"][f] is not None:
            period[f] = other["period"][f]
    merged["period"] = period
    # 再収集されたら collected_at を更新（終了日不明popupの30日TTLを延長。仕様§4.3）
    if other["collected_at"] > merged["collected_at"]:
        merged["collected_at"] = other["collected_at"]
    return merged


def dedupe_by_key(items: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for item in items:
        k = _key(item)
        seen[k] = _merge(seen[k], item) if k in seen else dict(item)
    out = []
    for item in seen.values():
        item["id"] = make_id(normalize_name(item["name"]),
                             normalize_address(item["address"]))
        out.append(item)
    return out
