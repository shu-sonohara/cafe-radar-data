import json
from pathlib import Path

from src.incoming import append_items

ITEM = {
    "type": "new_cafe", "genre": ["カフェ"], "name": "八三六", "area": "谷中",
    "address": "東京都台東区谷中3-13-2", "lat": None, "lng": None,
    "period": {"start": "2026-06-11", "end": None},
    "confidence": "official", "sources": ["https://o.example.com"],
    "summary": "古民家カフェ", "collected_at": "2026-08-29",
}


def test_append_creates_file_and_adds_valid_items(tmp_path):
    target = tmp_path / "rss_structured.json"
    result = append_items(str(target), [ITEM])
    assert result == {"added": 1, "duplicate": 0, "invalid": 0}
    assert json.loads(target.read_text(encoding="utf-8"))[0]["name"] == "八三六"


def test_append_skips_duplicates_by_name_and_address(tmp_path):
    target = tmp_path / "rss_structured.json"
    append_items(str(target), [ITEM])
    dup = {**ITEM, "name": "八三六（Hachi San Roku）"}          # 表記ゆれ
    same_key = {**ITEM, "address": "東京都台東区谷中３丁目１３−２"}  # 住所の全角
    result = append_items(str(target), [same_key, dup])
    assert result["duplicate"] == 1 and result["added"] == 1
    assert len(json.loads(target.read_text(encoding="utf-8"))) == 2


def test_append_rejects_invalid_and_keeps_existing(tmp_path):
    target = tmp_path / "rss_structured.json"
    append_items(str(target), [ITEM])
    bad = {**ITEM, "name": "出典なし", "address": "東京都北区1-1", "sources": []}
    result = append_items(str(target), [bad])
    assert result == {"added": 0, "duplicate": 0, "invalid": 1}
    assert len(json.loads(target.read_text(encoding="utf-8"))) == 1


def test_append_preserves_existing_formatting(tmp_path):
    target = tmp_path / "rss_structured.json"
    append_items(str(target), [ITEM])
    before = target.read_text(encoding="utf-8")
    other = {**ITEM, "name": "別の店", "address": "東京都渋谷区1-1"}
    append_items(str(target), [other])
    after = target.read_text(encoding="utf-8")
    assert after.startswith(before[:-3])  # 既存部分は末尾の "]" 直前まで一致（再整形しない）


def test_append_never_shrinks_file_on_empty_input(tmp_path):
    target = tmp_path / "rss_structured.json"
    append_items(str(target), [ITEM])
    append_items(str(target), [])
    assert len(json.loads(target.read_text(encoding="utf-8"))) == 1
