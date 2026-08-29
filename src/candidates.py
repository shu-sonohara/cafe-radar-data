"""RSS候補の選別: 処理済み除外・古い記事の除外・同一話題の束ね。

毎朝のルーチン報告で繰り返し挙がった問題への対策:
- GoogleニュースRSSは2013〜2025年の古い記事を大量に返す（420件中約300件）
- 同じ店が5〜10媒体に再配信され、同じ話題を何度も裏取りしていた
- 処理済みの記録がなく、3日分の候補を毎朝また最初から走査していた

`python -m src.candidates todo` が data/candidates_todo.json を書き、
LLMはそれだけを見ればよい。構造化が終わったら
`python -m src.candidates mark-reviewed` で処理済みに記録する。
"""
import argparse
import json
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from src.normalize import normalize_name

RAW_PATH = "data/raw_candidates.json"
TODO_PATH = "data/candidates_todo.json"
REVIEWED_PATH = "data/reviewed_urls.json"
MAX_AGE_DAYS = 60          # これより古い記事は「新規オープン」の候補にしない
REVIEWED_KEEP_DAYS = 45    # 処理済み記録の保持期間（raw側の保持3日より十分長ければよい）
DUP_TITLE_SIM = 0.8

_OUTLET_SUFFIX = re.compile(r"\s+[-–—|｜]\s+[^-–—|｜]{1,40}$")


def strip_outlet(title: str) -> str:
    """GoogleニュースRSSのタイトル末尾「 - 媒体名」を落とす。"""
    return _OUTLET_SUFFIX.sub("", title).strip()


def parse_published(published: str):
    """RFC822形式（Thu, 20 Aug 2026 06:05:00 GMT）→ 'YYYY-MM-DD'。解析不能はNone。"""
    if not published:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(published.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def drop_stale(candidates: list, today: str, max_age_days: int = MAX_AGE_DAYS) -> list:
    """記事日付が max_age_days より古い候補を落とす（取得時に使う）。日付不明は残す。"""
    cutoff = (date.fromisoformat(today) - timedelta(days=max_age_days)).isoformat()
    out = []
    for c in candidates:
        pub = parse_published(c.get("published", ""))
        if pub is not None and pub < cutoff:
            continue
        out.append(c)
    return out


def select_todo(candidates: list, reviewed_urls: set, today: str,
                max_age_days: int = MAX_AGE_DAYS) -> list:
    cutoff = (date.fromisoformat(today) - timedelta(days=max_age_days)).isoformat()
    fresh = []
    for c in candidates:
        if c["url"] in reviewed_urls:
            continue
        pub = parse_published(c.get("published", ""))
        if pub is not None and pub < cutoff:
            continue
        fresh.append({**c, "published_date": pub})

    # 新しい順に並べ、同じ話題（タイトル類似）は最初の1件に束ねる
    fresh.sort(key=lambda c: c["published_date"] or "0000-00-00", reverse=True)
    kept: list = []
    for c in fresh:
        key = normalize_name(strip_outlet(c["title"]))
        for k in kept:
            if SequenceMatcher(None, key, k["_key"]).ratio() >= DUP_TITLE_SIM:
                k["also_urls"].append(c["url"])
                break
        else:
            kept.append({**c, "_key": key, "also_urls": []})
    for k in kept:
        del k["_key"]
    return kept


def _load(path: str, default):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _write(path: str, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_todo(today: str) -> int:
    raw = _load(RAW_PATH, [])
    reviewed = _load(REVIEWED_PATH, {})
    todo = select_todo(raw, set(reviewed), today)
    _write(TODO_PATH, todo)
    print(f"候補 {len(raw)} 件 → 処理済み除外・{MAX_AGE_DAYS}日超除外・同話題束ね → 要確認 {len(todo)} 件")
    return len(todo)


def cmd_mark_reviewed(today: str) -> int:
    reviewed = _load(REVIEWED_PATH, {})
    keep_after = (date.fromisoformat(today) - timedelta(days=REVIEWED_KEEP_DAYS)).isoformat()
    reviewed = {u: d for u, d in reviewed.items() if d >= keep_after}
    for c in _load(TODO_PATH, []):
        reviewed[c["url"]] = today
        for u in c.get("also_urls", []):
            reviewed[u] = today
    _write(REVIEWED_PATH, reviewed)
    _write(TODO_PATH, [])
    print(f"処理済みURL {len(reviewed)} 件を記録")
    return len(reviewed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["todo", "mark-reviewed"])
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()
    if args.command == "todo":
        cmd_todo(args.today)
    else:
        cmd_mark_reviewed(args.today)


if __name__ == "__main__":
    main()
