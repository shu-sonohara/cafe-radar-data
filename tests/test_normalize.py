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
