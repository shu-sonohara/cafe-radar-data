"""収集済みアイテムを検証・統合し、配信用 items.json を書き出す。

data/incoming/*.json（LLMが構造化したアイテム配列）を読み、
検証 → 1次重複排除 → ジオコーディング → 2次重複排除 → 鮮度判定 の順に
通したものを docs/data/items.json として出力する。
"""
import argparse
import json
from datetime import date
from pathlib import Path

from src.freshness import is_new_badge, is_visible
from src.geocode import geocode_items
from src.merge import dedupe_by_location
from src.models import validate_item
from src.normalize import dedupe_by_key


def run(incoming_dir: str, out_path: str, today: str, http_get_json,
        sleep_sec: float = 0.0) -> dict:
    raw: list[dict] = []
    for p in sorted(Path(incoming_dir).glob("*.json")):
        raw.extend(json.loads(p.read_text(encoding="utf-8")))

    valid = []
    invalid = 0
    for item in raw:
        item.setdefault("id", "")
        item.setdefault("lat", None)
        item.setdefault("lng", None)
        if validate_item(item):
            invalid += 1
            continue
        valid.append(item)

    items = dedupe_by_key(valid)
    items = geocode_items(items, http_get_json, sleep_sec=sleep_sec)
    items = dedupe_by_location(items)

    published = []
    for item in items:
        if not is_visible(item, today):
            continue
        item["is_new"] = is_new_badge(item, today)
        published.append(item)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"updated_at": today, "items": published},
        ensure_ascii=False, indent=1), encoding="utf-8")

    stats = {
        "in": len(raw), "valid": len(items), "published": len(published),
        "invalid": invalid,
        "no_coords": sum(1 for i in published if i["lat"] is None),
    }
    print(json.dumps(stats, ensure_ascii=False))
    return stats


def main():
    import requests

    ap = argparse.ArgumentParser()
    ap.add_argument("--incoming", default="data/incoming")
    ap.add_argument("--out", default="docs/data/items.json")
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()
    run(args.incoming, args.out, args.today,
        http_get_json=lambda u: requests.get(u, timeout=30).json(),
        sleep_sec=0.5)  # 地理院APIへの配慮


if __name__ == "__main__":
    main()
