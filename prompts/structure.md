# RSS候補の構造化指示書

`data/raw_candidates.json` の各候補（source/title/url/summary/published/seen_at）を読み、
東京都内の「新店カフェ・スイーツ・コーヒー・パンケーキ店」または
「ポップアップ・催事」に該当するものだけを、以下のJSONに変換して
`data/incoming/rss_structured.json` に配列で保存する。

## 出力スキーマ（1件分）

```json
{"type": "new_cafe|popup|event", "genre": ["カフェ|スイーツ|コーヒー|パンケーキ"],
 "name": "店名/イベント名", "area": "駅・街名", "address": "住所（都道府県から）",
 "lat": null, "lng": null,
 "period": {"start": "YYYY-MM-DD|null", "end": "YYYY-MM-DD|null"},
 "confidence": "official|media", "sources": ["候補のurl"],
 "summary": "2〜3行・事実のみ", "collected_at": "今日の日付"}
```

## ルール

- 必要なら候補のURL先を読んで住所・期間を補完する
- 東京都外・判定不能・住所不明のものは出力しない
- `confidence`: 出典がプレスリリース・公式サイトなら `official`、報道記事なら `media`
- 推測で埋めない。終了日が書かれていなければ `end` は `null`
  （終了日不明の popup / event は収集から30日で自動的に非表示になる）
- `id` / `lat` / `lng` はPython側で付与するので触らない（id省略可、lat/lngはnull）
- 該当が0件なら空配列 `[]` を書く（ファイルを消さない）
