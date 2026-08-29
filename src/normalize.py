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


_PAREN = re.compile(r"[（(【\[][^）)】\]]*[）)】\]]")
_ADDR_CORE = re.compile(r"^(.*?\d+-\d+(?:-\d+)?)")  # 「…5-4-7」までを住所の核とみなす


def key_name(name: str) -> str:
    """重複判定用の店名: 「（東京会場）」等の括弧書きを無視する。"""
    return normalize_name(_PAREN.sub("", name))


_WS = re.compile(r"[\s　・]+")
_DASHES = re.compile(r"[‐−–—]")


def key_address(address: str) -> str:
    """重複判定用の住所: 番地（例「赤坂5-4-7」）までで切り、建物名・階の表記ゆれを無視する。
    normalize_address はハイフンも落とすため、ここではハイフンを残した形で番地を切り出す。
    番地まで無い住所（丁目レベルの unverified 等）は normalize_address にフォールバック。"""
    s = unicodedata.normalize("NFKC", address).lower()
    s = s.replace("丁目", "-").replace("番地", "-").replace("番", "-").replace("号", "")
    s = _DASHES.sub("-", _WS.sub("", s))
    m = _ADDR_CORE.match(s)
    return m.group(1) if m else normalize_address(address)


def _key(item: dict) -> str:
    return f"{key_name(item['name'])}|{key_address(item['address'])}"


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
