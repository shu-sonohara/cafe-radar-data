from src.candidates import select_todo, parse_published, strip_outlet


def _c(url, title, published="Thu, 20 Aug 2026 06:05:00 GMT", seen_at="2026-08-28"):
    return {"source": "gnews:x", "title": title, "url": url,
            "published": published, "summary": "", "seen_at": seen_at}


def test_parse_published_rfc822_and_garbage():
    assert parse_published("Thu, 20 Aug 2026 06:05:00 GMT") == "2026-08-20"
    assert parse_published("") is None
    assert parse_published("not a date") is None


def test_strip_outlet_suffix():
    assert strip_outlet("八三六が谷中にオープン - ファッションプレス") == "八三六が谷中にオープン"
    assert strip_outlet("タイトルのみ") == "タイトルのみ"


def test_select_todo_drops_reviewed_urls():
    cands = [_c("https://a", "A店オープン"), _c("https://b", "B店オープン")]
    todo = select_todo(cands, reviewed_urls={"https://a"}, today="2026-08-29")
    assert [c["url"] for c in todo] == ["https://b"]


def test_select_todo_drops_stale_articles_but_keeps_unparsable():
    cands = [_c("https://old", "コンフォートスタンド新橋にオープン", published="Fri, 11 Oct 2019 07:00:00 GMT"),
             _c("https://new", "新店オープン"),
             _c("https://unk", "日付不明の記事", published="")]
    todo = select_todo(cands, reviewed_urls=set(), today="2026-08-29", max_age_days=60)
    assert {c["url"] for c in todo} == {"https://new", "https://unk"}


def test_select_todo_collapses_near_duplicate_titles():
    cands = [_c("https://a", "東京国立博物館にカフェ＆レストランがオープン - ファッションプレス"),
             _c("https://b", "東京国立博物館にカフェ＆レストランがオープン！ - レッツエンジョイ東京"),
             _c("https://c", "全く別の店が渋谷にオープン - PR TIMES")]
    todo = select_todo(cands, reviewed_urls=set(), today="2026-08-29")
    assert len(todo) == 2
    grouped = [c for c in todo if c["url"] == "https://a"][0]
    assert grouped["also_urls"] == ["https://b"]  # 同じ話題の別媒体URLを束ねる


def test_select_todo_sorted_newest_first():
    cands = [_c("https://a", "A", published="Mon, 10 Aug 2026 00:00:00 GMT"),
             _c("https://b", "B", published="Thu, 27 Aug 2026 00:00:00 GMT")]
    todo = select_todo(cands, reviewed_urls=set(), today="2026-08-29")
    assert [c["url"] for c in todo] == ["https://b", "https://a"]


def test_drop_stale_removes_old_keeps_recent_and_unparsable():
    from src.candidates import drop_stale
    cands = [_c("https://old", "古い", published="Fri, 11 Oct 2019 07:00:00 GMT"),
             _c("https://new", "新しい"),
             _c("https://unk", "不明", published="")]
    out = drop_stale(cands, today="2026-08-29", max_age_days=60)
    assert [c["url"] for c in out] == ["https://new", "https://unk"]
