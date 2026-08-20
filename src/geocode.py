"""住所→座標の変換。国土地理院APIを使う（無料・APIキー不要）。

Google Geocoding APIは結果をGoogleマップ以外の地図に表示できない規約のため
使用しない（仕様書v1.1 §3・§6）。地理院で引けなかったアイテムは座標なしの
まま通し、アプリ側で地図非表示・新着リストのみ表示となる（同§7）。
"""
import time
from urllib.parse import quote

GSI_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch?q={q}"


def gsi_geocode(address: str, http_get_json):
    try:
        results = http_get_json(GSI_URL.format(q=quote(address)))
    except Exception:
        return None
    if not results:
        return None
    lng, lat = results[0]["geometry"]["coordinates"]
    return (float(lat), float(lng))


def geocode_items(items: list[dict], http_get_json, sleep_sec: float = 0.0) -> list[dict]:
    out = []
    for item in items:
        item = dict(item)
        if item.get("lat") is None or item.get("lng") is None:
            coords = gsi_geocode(item["address"], http_get_json)
            if coords:
                item["lat"], item["lng"] = coords
            if sleep_sec:
                time.sleep(sleep_sec)  # 公共APIへの配慮
        out.append(item)
    return out
