"""アイテムのスキーマ検証とID採番（仕様書v1.1 §4.1）。"""
import hashlib
import re

TYPES = {"new_cafe", "popup", "event"}
CONFIDENCES = {"official", "media", "unverified"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED = ["id", "type", "genre", "name", "area", "address",
            "lat", "lng", "period", "confidence", "sources",
            "summary", "collected_at"]


def make_id(name: str, address: str) -> str:
    return hashlib.sha1(f"{name}|{address}".encode("utf-8")).hexdigest()[:12]


def _valid_date(v) -> bool:
    return v is None or (isinstance(v, str) and bool(DATE_RE.match(v)))


def validate_item(item: dict) -> list[str]:
    errors = []
    for key in REQUIRED:
        if key not in item:
            errors.append(f"missing field: {key}")
    if errors:
        return errors
    if item["type"] not in TYPES:
        errors.append(f"invalid type: {item['type']}")
    if item["confidence"] not in CONFIDENCES:
        errors.append(f"invalid confidence: {item['confidence']}")
    if not isinstance(item["sources"], list) or len(item["sources"]) == 0:
        errors.append("sources must be a non-empty list")
    if not isinstance(item["genre"], list):
        errors.append("genre must be a list")
    for who in ("name", "area", "address", "summary"):
        if not isinstance(item[who], str) or not item[who].strip():
            errors.append(f"{who} must be a non-empty string")
    period = item["period"]
    if not isinstance(period, dict) or "start" not in period or "end" not in period:
        errors.append("period must have start and end")
    elif not (_valid_date(period["start"]) and _valid_date(period["end"])):
        errors.append("period dates must be YYYY-MM-DD or null")
    if item["collected_at"] is None or not _valid_date(item["collected_at"]):
        errors.append("collected_at must be YYYY-MM-DD")
    for coord in ("lat", "lng"):
        if item[coord] is not None and not isinstance(item[coord], (int, float)):
            errors.append(f"{coord} must be number or null")
    return errors
