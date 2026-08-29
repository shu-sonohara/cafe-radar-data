"""配信データの機械チェック（仕様書v1.1 §8の実データ検証を補助する）。

人の目で確かめるべきは「その店が本当に実在するか」「情報が最新か」で、
そこは自動化できない。このモジュールは機械的に判定できる異常だけを拾い、
目視レビューの範囲を狭めるためのもの。
"""
import argparse
import json
from datetime import date
from pathlib import Path

from src.merge import haversine_m, name_similarity
from src.normalize import key_address

DUP_DIST_M = 5000      # 同名の店が5km以内に2つあれば重複を疑う
DUP_SIM = 0.85


def _issue(item, kind, detail):
    return {"kind": kind, "name": item["name"], "detail": detail}


def find_issues(items: list, today: str) -> list:
    issues = []
    for item in items:
        if not item["address"].startswith("東京都"):
            issues.append(_issue(item, "都外", item["address"]))
        if item.get("lat") is None or item.get("lng") is None:
            issues.append(_issue(item, "位置なし", item["address"]))

        start, end = item["period"]["start"], item["period"]["end"]
        if start and end and end < start:
            issues.append(_issue(item, "期間が逆転", f"{start} → {end}"))
        if item["type"] in ("popup", "event") and end is None:
            issues.append(_issue(item, "終了日なし", "30日TTLで自動的に消える"))
        if end and end < today:
            issues.append(_issue(item, "終了済みなのに配信中", f"end={end}"))
        if not item.get("sources"):
            issues.append(_issue(item, "出典なし", ""))
        elif any("news.google.com" in u for u in item["sources"]):
            # アプリの「出典を見る」がGoogleニュースの中間ページに飛んでしまう。
            # 記事URLを直接記録させる必要がある（prompts/structure.md 参照）
            issues.append(_issue(item, "出典がGoogleニュース経由", item["sources"][0][:60]))

    for a, b in ((items[i], items[j])
                 for i in range(len(items)) for j in range(i + 1, len(items))):
        if (a["type"] in ("popup", "event") and a["type"] == b["type"]
                and a["period"] == b["period"] and a["period"]["end"] is not None
                and key_address(a["address"]) == key_address(b["address"])):
            issues.append(_issue(a, "同住所・同期間", f'{b["name"]} と同一の可能性'))
            continue
        if name_similarity(a["name"], b["name"]) < DUP_SIM:
            continue
        if None in (a.get("lat"), a.get("lng"), b.get("lat"), b.get("lng")):
            continue
        if haversine_m(a["lat"], a["lng"], b["lat"], b["lng"]) <= DUP_DIST_M:
            issues.append(_issue(a, "重複の疑い", f'{b["name"]} と類似'))
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="docs/data/items.json")
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()

    data = json.loads(Path(args.items).read_text(encoding="utf-8"))
    items = data["items"]
    issues = find_issues(items, args.today)

    print(f'配信日: {data["updated_at"]} / {len(items)}件')
    types = {}
    confs = {}
    for i in items:
        types[i["type"]] = types.get(i["type"], 0) + 1
        confs[i["confidence"]] = confs.get(i["confidence"], 0) + 1
    print("種別:", types)
    print("確度:", confs)
    print(f'\n機械チェックで引っかかった件数: {len(issues)}')
    by_kind = {}
    for i in issues:
        by_kind.setdefault(i["kind"], []).append(i)
    for kind, group in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
        print(f'\n■ {kind}（{len(group)}件）')
        for g in group[:10]:
            print(f'   - {g["name"][:38]}  {g["detail"]}')
        if len(group) > 10:
            print(f'   … 他{len(group) - 10}件')

    print("\n--- 以下は目視で確認する（自動判定できない）---")
    for i in items:
        end = i["period"]["end"] or "常設"
        print(f'  [{i["confidence"]:<9}] {i["name"][:36]:<36} {i["area"][:10]:<10} ~{end}')
        print(f'              {i["sources"][0][:88]}')


if __name__ == "__main__":
    main()
