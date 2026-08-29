"""数時間おきにActionsから実行: RSS候補を取得して蓄積する。

PR TIMESの全件フィードは当日分（最新200件）しか保持しないため、
1日1回では取りこぼす。取得のたびに data/raw_candidates.json へ
URL重複排除しながら積み上げ、3日より古い候補は捨てる。
"""
import json
from datetime import date
from pathlib import Path

import requests

from src.candidates import drop_stale
from src.fetch_rss import fetch_all, load_sources, merge_candidates

TODAY = date.today().isoformat()  # Actions側は TZ=Asia/Tokyo を設定して呼ぶ
STORE = Path("data/raw_candidates.json")

fresh = fetch_all(
    load_sources("sources.yaml"),
    lambda u: requests.get(
        u, timeout=30, headers={"User-Agent": "cafe-radar/0.1"}).text,
    config_path="sources.yaml",
)
# GoogleニュースRSSは数年前の記事も返すため、記事日付が60日より古いものはここで落とす
fresh = drop_stale(fresh, today=TODAY)
existing = json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else []
merged = merge_candidates(existing, fresh, today=TODAY)

STORE.parent.mkdir(parents=True, exist_ok=True)
STORE.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"今回取得 {len(fresh)} 件 / 蓄積 {len(merged)} 件")
