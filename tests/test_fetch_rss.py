from pathlib import Path

from src.fetch_rss import extract_candidates, load_sources, fetch_all

FEED = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text()
CONF = str(Path(__file__).parent.parent / "sources.yaml")


def test_extract_keeps_cafe_and_event_drops_printer():
    got = extract_candidates(FEED, "sample", config_path=CONF)
    titles = [c["title"] for c in got]
    assert len(got) == 2
    assert any("BUTTER" in t for t in titles)
    assert any("抹茶" in t for t in titles)


def test_candidate_shape():
    c = extract_candidates(FEED, "sample", config_path=CONF)[0]
    assert set(c) == {"source", "title", "url", "published", "summary"}
    assert c["source"] == "sample"
    assert c["url"].startswith("https://")


def test_fetch_all_uses_injected_http_get():
    sources = load_sources(CONF)
    calls = []

    def fake_get(url):
        calls.append(url)
        return FEED

    got = fetch_all(sources, fake_get, config_path=CONF)
    assert len(calls) == len(sources)
    assert len(got) == 2 * len(sources)


def test_fetch_all_survives_dead_source():
    sources = load_sources(CONF)

    def half_dead(url):
        if url == sources[0]["url"]:
            raise IOError("down")
        return FEED

    got = fetch_all(sources, half_dead, config_path=CONF)
    assert len(got) == 2 * (len(sources) - 1)


def _c(url, seen_at):
    return {"source": "s", "title": "t", "url": url,
            "published": "", "summary": "", "seen_at": seen_at}


def test_merge_candidates_adds_new_and_dedupes_by_url():
    from src.fetch_rss import merge_candidates
    existing = [_c("https://a", "2026-08-20")]
    fresh = [{"source": "s", "title": "t", "url": "https://a",
              "published": "", "summary": ""},
             {"source": "s", "title": "t2", "url": "https://b",
              "published": "", "summary": ""}]
    out = merge_candidates(existing, fresh, today="2026-08-20")
    assert [c["url"] for c in out] == ["https://a", "https://b"]
    assert out[1]["seen_at"] == "2026-08-20"


def test_merge_candidates_drops_entries_older_than_keep_days():
    from src.fetch_rss import merge_candidates
    existing = [_c("https://old", "2026-08-10"), _c("https://recent", "2026-08-19")]
    out = merge_candidates(existing, [], today="2026-08-20", keep_days=3)
    assert [c["url"] for c in out] == ["https://recent"]


def test_merge_candidates_keeps_original_seen_at_on_repeat():
    from src.fetch_rss import merge_candidates
    existing = [_c("https://a", "2026-08-19")]
    fresh = [{"source": "s", "title": "t", "url": "https://a",
              "published": "", "summary": ""}]
    out = merge_candidates(existing, fresh, today="2026-08-20")
    assert len(out) == 1
    assert out[0]["seen_at"] == "2026-08-19"


def test_load_sources_expands_google_news_queries(tmp_path):
    from src.fetch_rss import load_sources
    conf = tmp_path / "s.yaml"
    conf.write_text(
        "genre_words: [カフェ]\nsignal_words: [オープン]\narea_words: [東京]\n"
        "google_news_queries:\n  - 東京 カフェ オープン\n  - 東京 パンケーキ\n"
        "sources:\n  - name: prtimes_all\n    url: https://prtimes.jp/index.rdf\n",
        encoding="utf-8")
    got = load_sources(str(conf))
    assert len(got) == 3
    assert got[0]["name"] == "prtimes_all"
    gn = [s for s in got if s["name"].startswith("gnews:")]
    assert [s["name"] for s in gn] == ["gnews:東京 カフェ オープン", "gnews:東京 パンケーキ"]
    assert gn[0]["url"].startswith("https://news.google.com/rss/search?q=")
    assert "%E6%9D%B1%E4%BA%AC" in gn[0]["url"]        # 「東京」がURLエンコードされている
    assert gn[0]["url"].endswith("&hl=ja&gl=JP&ceid=JP:ja")


def test_load_sources_without_queries_is_unchanged(tmp_path):
    from src.fetch_rss import load_sources
    conf = tmp_path / "s.yaml"
    conf.write_text(
        "genre_words: [カフェ]\nsignal_words: [オープン]\narea_words: [東京]\n"
        "sources:\n  - name: prtimes_all\n    url: https://prtimes.jp/index.rdf\n",
        encoding="utf-8")
    got = load_sources(str(conf))
    assert [s["name"] for s in got] == ["prtimes_all"]
