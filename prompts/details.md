# 営業時間の確認指示書（v1・2026-10-31）

アプリの詳細シートに「営業時間・定休日」を出すため、配信中の店を少しずつ調べて登録する。
1日の上限は `--limit`（既定 15 件）。全部を一気に調べようとしない。

## 入力: `data/details_todo.json`

```bash
python3 -m src.details todo --today "$TODAY"        # 上限を変えるなら --limit 20
```

未確認の店を優先順（90日以内の新店 → 開催中のポップアップ・催事 → それ以外）に並べたもの。
各件: `id` / `type` / `name` / `area` / `address` / `period` / `sources`（記事URL、3つまで）/ `summary` /
`previous`（前回調べた結果。再確認のときだけ入る）

## 調べ方（1件あたり WebSearch 1〜2回 ＋ WebFetch 1回が目安）

1. まず `sources` の記事を WebFetch し、営業時間・定休日の記載があればそれを使う（プレスリリースには大抵ある）
2. 無ければ `店名 エリア 営業時間` で WebSearch → **公式サイト・公式SNSの固定ページ・施設（百貨店・商業施設）の公式ページ** を WebFetch
3. それでも見つからなければ `hours: null` で登録する（「調べた」記録になり、30日後に再挑戦する）

**使わない出典**: 食べログ・Retty・Googleマップ等の口コミ・まとめサイト（bot対策で取れず、規約的にも避ける）。
ポップアップ・催事は **会場の営業時間**（例: 百貨店の営業時間）でよい。

## 書き方

- `hours`: 自由文。例 `11:00–19:00（L.O.18:30）`、`平日 8:00–18:00 / 土日祝 9:00–18:00`、`10:00–21:00（施設に準ずる）`
  - 時刻の区切りは `–`（enダッシュ）または `-`、曜日ごとに違えば `/` で区切る。推測で埋めない
- `closed`: 定休日。例 `月曜`、`不定休`、`無休`、`施設に準ずる`。不明なら `null`
- `source`: 営業時間を確認したページの実URL（`hours` を入れるときは必須）
- `note`: 補足（任意）。例 `予約制`、`11/3のみ特別営業`

## 出力（配列を `/tmp/details_new.json` に書く）

```json
[
 {"id": "<todoのid>", "hours": "8:00–19:00（L.O.18:30）", "closed": "水曜",
  "source": "https://example.com/shop", "note": ""},
 {"id": "<todoのid>", "hours": null, "closed": null, "source": null, "note": "公式に営業時間の記載なし"}
]
```

```bash
python3 -m src.details append /tmp/details_new.json --today "$TODAY"
```

→ `data/details.json` に登録される（`added` / `updated` / `invalid` / `unknown_id` が出る。`invalid` があれば直して再実行）。
**`data/details.json` を直接編集しないこと。** 配信JSONへの合流は GitHub Actions 側で自動的に行われる。
