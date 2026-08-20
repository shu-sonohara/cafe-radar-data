"""RSSを取得し、カフェ・イベント関連の候補記事だけを抽出・蓄積する。"""
from datetime import date, timedelta
from urllib.parse import quote

import feedparser
import yaml


def _load_config(config_path: str) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


GNEWS_URL = "https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja"


def load_sources(config_path: str) -> list[dict]:
    """購読するフィード一覧を返す。

    直接RSSを出している媒体は PR TIMES のみで、東京のカフェ・ポップアップを
    扱うメディア（Fashion Press、Time Out、レッツエンジョイ東京 等）は
    RSS未提供かbot遮断。GoogleニュースRSSはクエリを指定して購読でき、
    それらの媒体の記事をまとめて拾えるため、google_news_queries の各クエリを
    1ソースとして展開する。
    """
    config = _load_config(config_path)
    sources = list(config.get("sources", []))
    for q in config.get("google_news_queries", []):
        sources.append({"name": f"gnews:{q}", "url": GNEWS_URL.format(q=quote(q))})
    return sources


def _matches(text: str, config: dict) -> bool:
    lowered = text.lower()
    has_genre = any(w.lower() in lowered for w in config["genre_words"])
    has_signal = any(w.lower() in lowered for w in config["signal_words"])
    return has_genre and has_signal


def extract_candidates(feed_xml: str, source_name: str, config_path: str) -> list[dict]:
    config = _load_config(config_path)
    parsed = feedparser.parse(feed_xml)
    out = []
    for e in parsed.entries:
        title = e.get("title", "")
        summary = e.get("summary", "")
        if not _matches(f"{title} {summary}", config):
            continue
        out.append({
            "source": source_name,
            "title": title,
            "url": e.get("link", ""),
            "published": e.get("published", ""),
            "summary": summary,
        })
    return out


def fetch_all(sources: list[dict], http_get, config_path: str) -> list[dict]:
    out = []
    for s in sources:
        try:
            xml = http_get(s["url"])
        except Exception:
            continue  # ソース1つの死で全体を止めない（仕様書§7）
        out.extend(extract_candidates(xml, s["name"], config_path))
    return out


def merge_candidates(existing: list[dict], fresh: list[dict], today: str,
                     keep_days: int = 3) -> list[dict]:
    """候補を蓄積する。

    PR TIMESの全件フィードは最新200件しか保持せず当日分で入れ替わるため、
    数時間おきに取得して積み上げる。URLで重複排除し、keep_days より古い
    候補は捨てる（構造化済みの候補を何日も持ち回らないため）。
    """
    cutoff = date.fromisoformat(today) - timedelta(days=keep_days)
    merged: dict[str, dict] = {}
    for c in existing:
        if date.fromisoformat(c.get("seen_at", today)) < cutoff:
            continue
        merged[c["url"]] = c
    for c in fresh:
        if c["url"] in merged:
            continue  # 既知の候補は初出日（seen_at）を保つ
        merged[c["url"]] = {**c, "seen_at": today}
    return list(merged.values())
