from src.geocode import gsi_geocode, geocode_items

GSI_OK = [{"geometry": {"coordinates": [139.669, 35.6075]},
           "properties": {"title": "東京都目黒区自由が丘一丁目"}}]


def test_gsi_geocode_returns_lat_lng():
    got = gsi_geocode("東京都目黒区自由が丘1-2-3", lambda url: GSI_OK)
    assert got == (35.6075, 139.669)


def test_gsi_geocode_empty_result_returns_none():
    assert gsi_geocode("存在しない住所", lambda url: []) is None


def test_gsi_geocode_network_error_returns_none():
    def boom(url):
        raise IOError("down")
    assert gsi_geocode("東京都新宿区1-1", boom) is None


def test_geocode_items_fills_only_missing():
    items = [
        {"name": "A", "address": "東京都目黒区自由が丘1-2-3", "lat": None, "lng": None},
        {"name": "B", "address": "東京都新宿区1-1", "lat": 35.69, "lng": 139.70},
    ]
    out = geocode_items(items, lambda url: GSI_OK)
    assert out[0]["lat"] == 35.6075 and out[0]["lng"] == 139.669
    assert out[1]["lat"] == 35.69  # 既存座標は上書きしない


def test_geocode_items_leaves_none_when_lookup_fails():
    items = [{"name": "A", "address": "架空の住所", "lat": None, "lng": None}]
    out = geocode_items(items, lambda url: [])
    assert out[0]["lat"] is None and out[0]["lng"] is None
