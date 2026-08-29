"""収集済みアイテムを検証・統合し、配信用 items.json を書き出す。

data/incoming/*.json（LLMが構造化したアイテム配列）を読み、
検証 → 1次重複排除 → ジオコーディング → 2次重複排除 → 鮮度判定 の順に
通したものを docs/data/items.json として出力する。
"""
import argparse
import json
from datetime import date
from pathlib import Path

from src.collab import tag_collab
from src.freshness import freshness_bucket, is_new_badge, is_visible
from src.geocode import geocode_items
from src.merge import dedupe_by_location
from src.models import validate_item
from src.normalize import dedupe_by_key


def run(incoming_dir: str, out_path: str, today: str, http_get_json,
        sleep_sec: float = 0.0, cache_path: str = "", archive_path: str = "") -> dict:
    cache = {}
    if cache_path and Path(cache_path).exists():
        cache = json.loads(Path(cache_path).read_text(encoding="utf-8"))

    # アーカイブ（過去に取り込んだ全アイテム）を先に読む。incoming が
    # 上書き・縮小されても、一度配信したアイテムはここから復元される。
    raw: list[dict] = []
    if archive_path and Path(archive_path).exists():
        raw.extend(json.loads(Path(archive_path).read_text(encoding="utf-8")))
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
    if archive_path:
        Path(archive_path).parent.mkdir(parents=True, exist_ok=True)
        Path(archive_path).write_text(
            json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    # 鮮度判定を先に通す。終了済みアイテムに座標は要らないので、
    # ここで落としておけば無駄なジオコーディング問い合わせをしない
    # （アーカイブには鮮度に関係なく全件残す。仕様§4.3「データは保持」）。
    items = [i for i in items if is_visible(i, today)]
    items = geocode_items(items, http_get_json, sleep_sec=sleep_sec, cache=cache)
    if cache_path:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(
            json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8")
    items = dedupe_by_location(items)

    published = []
    for item in items:
        item = tag_collab(item)  # コラボカフェの安全網タグ付け
        item["is_new"] = is_new_badge(item, today)
        item["freshness"] = freshness_bucket(item, today)
        published.append(item)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"updated_at": today, "items": published},
        ensure_ascii=False, indent=1), encoding="utf-8")

    stats = {
        "in": len(raw), "valid": len(valid), "published": len(published),
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
    ap.add_argument("--cache", default="data/geocode_cache.json")
    ap.add_argument("--archive", default="data/archive.json")
    args = ap.parse_args()
    run(args.incoming, args.out, args.today,
        http_get_json=lambda u: requests.get(u, timeout=30).json(),
        sleep_sec=0.5,  # 地理院APIへの配慮
        cache_path=args.cache, archive_path=args.archive)


if __name__ == "__main__":
    main()
