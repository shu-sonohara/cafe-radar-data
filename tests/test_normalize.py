from src.normalize import normalize_name, normalize_address, dedupe_by_key


def test_normalize_name_unifies_width_case_spaces():
    assert normalize_name("ＢＵＴＴＥＲ　＆ Stack ") == normalize_name("butter&stack")


def test_normalize_address_unifies_numbers():
    a = normalize_address("東京都目黒区自由が丘１丁目２−３")
    b = normalize_address("東京都目黒区自由が丘1丁目2-3")
    assert a == b


def _item(name, address, confidence, source):
    return {
        "id": "", "type": "new_cafe", "genre": ["カフェ"],
        "name": name, "area": "自由が丘", "address": address,
        "lat": None, "lng": None,
        "period": {"start": "2026-08-01", "end": None},
        "confidence": confidence, "sources": [source],
        "summary": "テスト", "collected_at": "2026-08-19",
    }


def test_dedupe_merges_sources_and_promotes_confidence():
    items = [
        _item("Cafe A", "東京都X区1-1", "media", "https://m1.example.com"),
        _item("Ｃａｆｅ　Ａ", "東京都X区１−１", "official", "https://o.example.com"),
    ]
    out = dedupe_by_key(items)
    assert len(out) == 1
    assert out[0]["confidence"] == "official"
    assert set(out[0]["sources"]) == {"https://m1.example.com", "https://o.example.com"}
    assert out[0]["id"] != ""


def test_dedupe_keeps_distinct_items():
    items = [
        _item("Cafe A", "東京都X区1-1", "media", "https://a.example.com"),
        _item("Cafe B", "東京都X区2-2", "media", "https://b.example.com"),
    ]
    assert len(dedupe_by_key(items)) == 2


def test_dedupe_takes_latest_collected_at_and_fills_start():
    # 再収集されたら collected_at を新しい方に更新する（30日TTLの延長。仕様§4.3）
    a = _item("Cafe A", "東京都X区1-1", "media", "https://m1.example.com")
    a["collected_at"] = "2026-08-01"
    b = _item("Cafe A", "東京都X区1-1", "media", "https://m2.example.com")
    b["collected_at"] = "2026-08-25"
    b["period"] = {"start": None, "end": None}
    a["period"] = {"start": None, "end": None}
    out = dedupe_by_key([a, b])
    assert out[0]["collected_at"] == "2026-08-25"

    # start は「埋まっている方」を採用
    c = _item("Cafe B", "東京都X区2-2", "media", "https://m3.example.com")
    c["period"] = {"start": None, "end": None}
    d = _item("Cafe B", "東京都X区2-2", "media", "https://m4.example.com")
    d["period"] = {"start": "2026-08-10", "end": None}
    out = dedupe_by_key([c, d])
    assert out[0]["period"]["start"] == "2026-08-10"


def test_dedupe_ignores_parenthetical_suffix_in_name():
    # 「（東京会場）」の有無だけ違う同一イベント（実データ 2026-08-29）
    a = _item("はなまるおばけのはなまるごほうびカフェ（東京会場）", "東京都渋谷区神宮前6-28-6 キュープラザ原宿3F", "official", "https://a.example.com")
    b = _item("はなまるおばけのはなまるごほうびカフェ", "東京都渋谷区神宮前6丁目28番6号 キュープラザ原宿3F", "official", "https://b.example.com")
    assert len(dedupe_by_key([a, b])) == 1


def test_dedupe_ignores_building_name_suffix_in_address():
    # 「5-4-7 THE HEXAGON 1F ブランチパーク」と「5丁目4-7 THE HEXAGON 1F」は同じ場所
    a = _item("Cafe X", "東京都港区赤坂5-4-7 THE HEXAGON 1F ブランチパーク", "media", "https://a.example.com")
    b = _item("Cafe X", "東京都港区赤坂5丁目4-7 THE HEXAGON 1F", "media", "https://b.example.com")
    assert len(dedupe_by_key([a, b])) == 1
