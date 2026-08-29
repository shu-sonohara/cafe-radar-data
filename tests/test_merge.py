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


def _popup(name, lat, lng, start, end, source):
    i = _item(name, lat, lng, "media", source)
    i["type"] = "popup"
    i["period"] = {"start": start, "end": end}
    return i


def test_same_spot_same_period_popups_merge_even_with_different_names():
    # リラックマ×SASUKE が3つの名前で登録された実データ（2026-08-29）
    a = _popup("アニメ「リラックマ」×「SASUKE」コラボカフェ（ブランチパーク）", 35.6720, 139.7370, "2026-08-27", "2026-09-13", "https://a.example.com")
    b = _popup("Rilakkuma cafe てくてく世界旅行（SASUKEワールドカップ2026コラボ）", 35.6720, 139.7370, "2026-08-27", "2026-09-13", "https://b.example.com")
    out = dedupe_by_location([a, b])
    assert len(out) == 1
    assert len(out[0]["sources"]) == 2


def test_same_spot_different_period_popups_stay_separate():
    # 同じ会場（BOX cafe&space 等）で期間が違うコラボは別イベント
    a = _popup("Aカフェ", 35.6720, 139.7370, "2026-08-01", "2026-08-31", "https://a.example.com")
    b = _popup("Bカフェ", 35.6720, 139.7370, "2026-09-01", "2026-09-30", "https://b.example.com")
    assert len(dedupe_by_location([a, b])) == 2


def test_same_spot_same_period_new_cafes_do_not_merge_by_period():
    # 常設店は period が同じ（end null）でも別の店なら別
    a = _item("Cafe A", 35.6720, 139.7370)
    b = _item("抹茶スタンドB", 35.6720, 139.7370)
    assert len(dedupe_by_location([a, b])) == 2
