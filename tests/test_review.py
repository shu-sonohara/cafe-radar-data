from src.review import find_issues


def _item(**kw):
    base = {
        "id": "x", "type": "new_cafe", "genre": ["カフェ"], "name": "A",
        "area": "渋谷", "address": "東京都渋谷区1-1", "lat": 35.6, "lng": 139.7,
        "period": {"start": "2026-08-01", "end": None},
        "confidence": "media", "sources": ["https://a.example.com"],
        "summary": "t", "collected_at": "2026-08-21", "is_new": True,
    }
    base.update(kw)
    return base


def test_flags_non_tokyo_address():
    issues = find_issues([_item(address="神奈川県横浜市1-1")], today="2026-08-21")
    assert any(i["kind"] == "都外" for i in issues)


def test_flags_missing_coordinates():
    issues = find_issues([_item(lat=None, lng=None)], today="2026-08-21")
    assert any(i["kind"] == "位置なし" for i in issues)


def test_flags_end_before_start():
    issues = find_issues(
        [_item(type="popup", period={"start": "2026-08-20", "end": "2026-08-10"})],
        today="2026-08-21")
    assert any(i["kind"] == "期間が逆転" for i in issues)


def test_flags_popup_without_end_date():
    issues = find_issues([_item(type="popup", period={"start": "2026-08-01", "end": None})],
                         today="2026-08-21")
    assert any(i["kind"] == "終了日なし" for i in issues)


def test_new_cafe_without_end_is_not_flagged():
    issues = find_issues([_item(type="new_cafe", period={"start": "2026-08-01", "end": None})],
                         today="2026-08-21")
    assert not any(i["kind"] == "終了日なし" for i in issues)


def test_flags_near_duplicate_names():
    items = [_item(name="Cafe Kissa", address="東京都渋谷区1-1", lat=35.6000, lng=139.7000),
             _item(name="CafeKissa", address="東京都渋谷区1-2", lat=35.6300, lng=139.7000)]
    issues = find_issues(items, today="2026-08-21")
    assert any(i["kind"] == "重複の疑い" for i in issues)


def test_clean_items_produce_no_issues():
    assert find_issues([_item()], today="2026-08-21") == []


def test_flags_google_news_redirect_source():
    issues = find_issues(
        [_item(sources=["https://news.google.com/rss/articles/CBMiT0FV?oc=5"])],
        today="2026-08-21")
    assert any(i["kind"] == "出典がGoogleニュース経由" for i in issues)


def test_direct_article_source_is_not_flagged():
    issues = find_issues([_item(sources=["https://prtimes.jp/main/html/rd/p/1.html"])],
                         today="2026-08-21")
    assert not any(i["kind"] == "出典がGoogleニュース経由" for i in issues)


def test_flags_same_address_same_period_popups():
    a = _item(name="Aコラボカフェ", type="popup", address="東京都港区赤坂5-4-7 THE HEXAGON 1F",
              period={"start": "2026-08-27", "end": "2026-09-13"})
    b = _item(name="Rilakkuma cafe", type="popup", address="東京都港区赤坂5丁目4-7 THE HEXAGON 1F",
              period={"start": "2026-08-27", "end": "2026-09-13"})
    issues = find_issues([a, b], today="2026-08-29")
    assert any(i["kind"] == "同住所・同期間" for i in issues)
