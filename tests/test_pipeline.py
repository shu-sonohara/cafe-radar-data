import json
from pathlib import Path

from src.run_pipeline import run

GSI_OK = [{"geometry": {"coordinates": [139.669, 35.6075]}}]

RAW = {
    "type": "popup", "genre": ["スイーツ"], "name": "抹茶POP-UP",
    "area": "渋谷", "address": "東京都渋谷区1-1", "lat": None, "lng": None,
    "period": {"start": "2026-08-10", "end": "2026-08-31"},
    "confidence": "official", "sources": ["https://o.example.com"],
    "summary": "抹茶の期間限定ストア", "collected_at": "2026-08-19",
}
ENDED = {**RAW, "name": "終了済イベント", "address": "東京都港区2-2",
         "period": {"start": "2026-07-01", "end": "2026-07-31"}}
BROKEN = {**RAW, "name": "出典なし", "address": "東京都北区3-3", "sources": []}


def _setup(tmp_path: Path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "a.json").write_text(
        json.dumps([RAW, ENDED, BROKEN], ensure_ascii=False), encoding="utf-8")
    return str(incoming), str(tmp_path / "items.json")


def test_run_publishes_only_valid_visible_items(tmp_path):
    incoming, out = _setup(tmp_path)
    stats = run(incoming, out, today="2026-08-19", http_get_json=lambda u: GSI_OK)
    data = json.loads(Path(out).read_text(encoding="utf-8"))
    assert data["updated_at"] == "2026-08-19"
    names = [i["name"] for i in data["items"]]
    assert names == ["抹茶POP-UP"]
    assert data["items"][0]["lat"] == 35.6075
    assert data["items"][0]["id"]
    assert data["items"][0]["is_new"] is False
    assert stats == {"in": 3, "valid": 2, "published": 1, "invalid": 1, "no_coords": 0}


def test_run_with_empty_incoming_writes_empty_list(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    out = str(tmp_path / "items.json")
    run(str(incoming), out, today="2026-08-19", http_get_json=lambda u: GSI_OK)
    data = json.loads(Path(out).read_text(encoding="utf-8"))
    assert data["items"] == []


def test_run_counts_items_without_coords(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "a.json").write_text(json.dumps([RAW], ensure_ascii=False), encoding="utf-8")
    out = str(tmp_path / "items.json")
    stats = run(str(incoming), out, today="2026-08-19", http_get_json=lambda u: [])
    assert stats["no_coords"] == 1
    assert json.loads(Path(out).read_text(encoding="utf-8"))["items"][0]["lat"] is None


def test_run_merges_same_store_across_files(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "a.json").write_text(json.dumps([RAW], ensure_ascii=False), encoding="utf-8")
    dup = {**RAW, "confidence": "media", "sources": ["https://m.example.com"]}
    (incoming / "b.json").write_text(json.dumps([dup], ensure_ascii=False), encoding="utf-8")
    out = str(tmp_path / "items.json")
    run(str(incoming), out, today="2026-08-19", http_get_json=lambda u: GSI_OK)
    items = json.loads(Path(out).read_text(encoding="utf-8"))["items"]
    assert len(items) == 1
    assert len(items[0]["sources"]) == 2
    assert items[0]["confidence"] == "official"


def test_run_persists_geocode_cache(tmp_path):
    incoming, out = _setup(tmp_path)
    cache_path = tmp_path / "geocode_cache.json"
    run(incoming, out, today="2026-08-19", http_get_json=lambda u: GSI_OK,
        cache_path=str(cache_path))
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cache["東京都渋谷区1-1"] == [35.6075, 139.669]


def test_run_reuses_existing_cache_without_lookup(tmp_path):
    incoming, out = _setup(tmp_path)
    cache_path = tmp_path / "geocode_cache.json"
    cache_path.write_text(json.dumps({"東京都渋谷区1-1": [1.5, 2.5]}), encoding="utf-8")
    calls = []

    def spy(url):
        calls.append(url)
        return GSI_OK

    run(incoming, out, today="2026-08-19", http_get_json=spy, cache_path=str(cache_path))
    item = json.loads(Path(out).read_text(encoding="utf-8"))["items"][0]
    assert (item["lat"], item["lng"]) == (1.5, 2.5)
    assert calls == []  # 終了済みは鮮度判定で先に落ちるので問い合わせも起きない
