"""営業時間などの詳細情報（data/details.json）。

ルーチンが毎朝、未確認の店を上限件数だけ調べて登録する。
配信JSONを作るとき（run_pipeline）に各アイテムへ `hours` として合流する。

details.json の形:
  {"<item id>": {"hours": "11:00–19:00（L.O.18:30）" | null, "closed": "月曜" | null,
                 "source": "https://..." | null, "note": "...", "checked_at": "YYYY-MM-DD"}}
  hours が null = 調べたが公式の記載が見つからなかった（RETRY_DAYS 後に再挑戦）。
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

DETAILS_PATH = "data/details.json"
TODO_PATH = "data/details_todo.json"
ITEMS_PATH = "docs/data/items.json"
DEFAULT_LIMIT = 15      # 1日に調べる上限（ルーチンの所要時間に直結する）
RECHECK_DAYS = 90       # 確認済みでもこれを過ぎたら再確認（営業時間は変わる）
RETRY_DAYS = 30         # 見つからなかった店の再挑戦


def _load(path, default):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _write(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True),
                          encoding="utf-8")


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def needs_check(detail: dict | None, today: str) -> bool:
    if not detail:
        return True
    age = _days(detail["checked_at"], today)
    return age >= (RETRY_DAYS if detail.get("hours") is None else RECHECK_DAYS)


def priority(item: dict, today: str) -> int:
    """0=90日以内の新店, 1=開催中（または終了日未確認）のポップアップ・催事, 2=それ以外"""
    start = item["period"].get("start")
    end = item["period"].get("end")
    if item["type"] == "new_cafe":
        return 0 if start and _days(start, today) <= 90 else 2
    if end is None or _days(today, end) >= 0:
        return 1
    return 2


def _order_key(item: dict, today: str):
    p = priority(item, today)
    start = item["period"].get("start") or ""
    end = item["period"].get("end")
    if p == 0:
        return (0, _neg_date(start))                 # 新しくオープンした順
    if p == 1:
        return (1, end or "9999-12-31")              # 終了が近い順、終了日未確認は後
    return (2, _neg_date(item.get("collected_at", "")))


def _neg_date(s: str) -> str:
    # 文字列の降順を昇順キーに変換（"2026-10-31" → 各桁を 9 から引く）
    return "".join(str(9 - int(c)) if c.isdigit() else c for c in s)


def select_todo(items: list[dict], details: dict, today: str, limit: int) -> list[dict]:
    todo = [i for i in items if needs_check(details.get(i["id"]), today)]
    todo.sort(key=lambda i: _order_key(i, today))
    out = []
    for i in todo[:limit]:
        prev = details.get(i["id"])
        out.append({
            "id": i["id"], "type": i["type"], "name": i["name"], "area": i["area"],
            "address": i["address"], "period": i["period"],
            "sources": i["sources"][:3], "summary": i["summary"][:120],
            "previous": ({"hours": prev.get("hours"), "closed": prev.get("closed"),
                          "checked_at": prev["checked_at"]} if prev else None),
        })
    return out


def validate_entry(e: dict) -> list[str]:
    errors = []
    if not isinstance(e, dict):
        return ["entry must be an object"]
    if not isinstance(e.get("id"), str) or not e["id"]:
        errors.append("id must be a non-empty string")
    hours = e.get("hours")
    if hours is not None and (not isinstance(hours, str) or not hours.strip()):
        errors.append("hours must be a non-empty string or null")
    closed = e.get("closed")
    if closed is not None and not isinstance(closed, str):
        errors.append("closed must be a string or null")
    src = e.get("source")
    if hours is not None and (not isinstance(src, str) or not src.startswith("http")):
        errors.append("source URL is required when hours is given")
    if src is not None and not (isinstance(src, str) and src.startswith("http")):
        errors.append("source must be an http(s) URL or null")
    return errors


def append_entries(details: dict, entries: list[dict], today: str,
                   known_ids: set[str] | None = None) -> dict:
    stats = {"added": 0, "updated": 0, "invalid": 0, "unknown_id": 0}
    for e in entries:
        if validate_entry(e):
            stats["invalid"] += 1
            continue
        if known_ids is not None and e["id"] not in known_ids:
            stats["unknown_id"] += 1
            continue
        rec = {"hours": e.get("hours"), "closed": e.get("closed"),
               "source": e.get("source"), "note": e.get("note", ""), "checked_at": today}
        stats["updated" if e["id"] in details else "added"] += 1
        details[e["id"]] = rec
    return stats


def attach(items: list[dict], details: dict) -> list[dict]:
    """配信アイテムに hours を付ける（無ければ null）。"""
    for item in items:
        d = details.get(item["id"])
        item["hours"] = ({"text": d.get("hours"), "closed": d.get("closed"),
                          "checked_at": d["checked_at"], "source": d.get("source")}
                         if d else None)
    return items


def cmd_todo(today: str, limit: int) -> int:
    items = _load(ITEMS_PATH, {"items": []})["items"]
    details = _load(DETAILS_PATH, {})
    todo = select_todo(items, details, today, limit)
    _write(TODO_PATH, todo)
    remaining = sum(1 for i in items if needs_check(details.get(i["id"]), today))
    print(f"営業時間 未確認 {remaining} 件 → 今日調べる {len(todo)} 件（上限 {limit}）")
    return len(todo)


def cmd_append(path: str, today: str) -> dict:
    entries = _load(path, [])
    details = _load(DETAILS_PATH, {})
    items = _load(ITEMS_PATH, {"items": []})["items"]
    known = {i["id"] for i in items} if items else None
    stats = append_entries(details, entries, today, known)
    _write(DETAILS_PATH, details)
    print(json.dumps({"target": DETAILS_PATH, **stats}, ensure_ascii=False))
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["todo", "append"])
    ap.add_argument("path", nargs="?", help="append: 追記する JSON 配列ファイル")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = ap.parse_args()
    if args.command == "todo":
        cmd_todo(args.today, args.limit)
    else:
        if not args.path:
            ap.error("append には JSON ファイルのパスが必要")
        cmd_append(args.path, args.today)


if __name__ == "__main__":
    main()
