from src.models import validate_item, make_id

VALID = {
    "id": "abc123",
    "type": "new_cafe",
    "genre": ["パンケーキ"],
    "name": "BUTTER & STACK 自由が丘",
    "area": "自由が丘",
    "address": "東京都目黒区自由が丘1-2-3",
    "lat": 35.6075,
    "lng": 139.6690,
    "period": {"start": "2026-08-01", "end": None},
    "confidence": "media",
    "sources": ["https://example.com/article"],
    "summary": "発酵バターのパンケーキ専門店。",
    "collected_at": "2026-08-19",
}


def test_valid_item_passes():
    assert validate_item(VALID) == []


def test_missing_sources_fails():
    item = {**VALID, "sources": []}
    assert any("sources" in e for e in validate_item(item))


def test_bad_type_fails():
    item = {**VALID, "type": "restaurant"}
    assert any("type" in e for e in validate_item(item))


def test_bad_date_fails():
    item = {**VALID, "period": {"start": "8/1", "end": None}}
    assert any("period" in e for e in validate_item(item))


def test_lat_lng_may_be_null():
    item = {**VALID, "lat": None, "lng": None}
    assert validate_item(item) == []


def test_make_id_is_stable_and_distinct():
    a = make_id("店A", "東京都X区1-1")
    assert a == make_id("店A", "東京都X区1-1")
    assert a != make_id("店B", "東京都X区1-1")
