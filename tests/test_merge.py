from src.merge import haversine_m, name_similarity, dedupe_by_location


def _item(name, lat, lng, confidence="media", source="https://x.example.com"):
    return {
        "id": name, "type": "new_cafe", "genre": ["カフェ"], "name": name,
        "area": "X", "address": f"東京都X区 {name}", "lat": lat, "lng": lng,
        "period": {"start": "2026-08-01", "end": None},
        "confidence": confidence, "sources": [source],
        "summary": "t", "collected_at": "2026-08-19",
    }


def test_haversine_zero_and_rough_distance():
    assert haversine_m(35.0, 139.0, 35.0, 139.0) == 0
    assert 100 < haversine_m(35.0, 139.0, 35.001, 139.0) < 125


def test_name_similarity():
    assert name_similarity("BUTTER & STACK 自由が丘", "BUTTER&STACK 自由が丘店") > 0.6
    assert name_similarity("BUTTER & STACK", "抹茶フェス渋谷") < 0.4


def test_nearby_similar_items_merge():
    a = _item("Cafe Kissa", 35.60000, 139.60000, "media", "https://m.example.com")
    b = _item("CafeKissa 東京", 35.60020, 139.60000, "official", "https://o.example.com")
    out = dedupe_by_location([a, b])
    assert len(out) == 1
    assert out[0]["confidence"] == "official"
    assert len(out[0]["sources"]) == 2


def test_nearby_but_different_names_stay_separate():
    a = _item("Cafe Kissa", 35.60000, 139.60000)
    b = _item("抹茶フェス渋谷", 35.60010, 139.60000)
    assert len(dedupe_by_location([a, b])) == 2


def test_items_without_coords_pass_through():
    a = _item("A", None, None)
    b = _item("B", None, None)
    assert len(dedupe_by_location([a, b])) == 2


def test_far_apart_same_name_stay_separate():
    a = _item("Cafe Kissa", 35.60000, 139.60000)
    b = _item("Cafe Kissa", 35.70000, 139.70000)
    assert len(dedupe_by_location([a, b])) == 2
