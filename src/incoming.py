"""data/incoming/*.json への安全な追記。

毎朝のルーチンがその場しのぎのPythonで追記していたため、
- 2026-08-21: 上書きで8件消失
- 2026-08-26/29: 再シリアライズで2700行の無意味な差分
が起きた。追記はこのコマンドに一本化する:

    python -m src.incoming append data/incoming/rss_structured.json new_items.json

検証（仕様§4.1）→ 既存との重複（店名＋住所の正規化一致）をスキップ → 追記。
既存アイテムは一切変更せず、ファイルが縮むことはない。
"""
import argparse
import json
from pathlib import Path

from src.models import validate_item
from src.normalize import normalize_address, normalize_name


def _key(item: dict) -> str:
    return f"{normalize_name(item['name'])}|{normalize_address(item['address'])}"


def append_items(path: str, new_items: list) -> dict:
    target = Path(path)
    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else []
    known = {_key(i) for i in existing}
    stats = {"added": 0, "duplicate": 0, "invalid": 0}
    for item in new_items:
        item = dict(item)
        item.setdefault("id", "")
        item.setdefault("lat", None)
        item.setdefault("lng", None)
        if validate_item(item):
            stats["invalid"] += 1
            continue
        k = _key(item)
        if k in known:
            stats["duplicate"] += 1
            continue
        known.add(k)
        existing.append(item)
        stats["added"] += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(existing, ensure_ascii=False, indent=1), encoding="utf-8")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["append"])
    ap.add_argument("target", help="data/incoming/rss_structured.json など")
    ap.add_argument("source", help="追記するアイテム配列のJSONファイル")
    args = ap.parse_args()
    new_items = json.loads(Path(args.source).read_text(encoding="utf-8"))
    stats = append_items(args.target, new_items)
    print(json.dumps({"target": args.target, **stats}, ensure_ascii=False))
    if stats["invalid"]:
        print("※ invalid はスキーマ違反（仕様§4.1）。出典なし・住所なし等を確認してください")


if __name__ == "__main__":
    main()
