# RSS候補の構造化指示書（v2・2026-08-29改訂）

## 入力: `data/candidates_todo.json`（`data/raw_candidates.json` ではない）

`python -m src.candidates todo --today $(TZ=Asia/Tokyo date +%F)` が生成する。
処理済みURL・60日より古い記事・同一話題の別媒体（`also_urls` に束ねてある）を
除いた、**今日はじめて見る候補だけ**が入っている。新しい順。

各候補: `title` / `url` / `also_urls`（同じ話題の別媒体URL） / `published_date` / `summary` / `source`

## やること

候補のタイトルを一通り眺め、東京都内の「新店カフェ・スイーツ・コーヒー・
パンケーキ・ベーカリー」または「ポップアップ・催事」に該当しそうなものを絞り込み、
裏取りして下記スキーマに変換し、`data/incoming/rss_structured.json` に追記する。

## 裏取りの方法

候補の `url` が `news.google.com` の場合、WebFetch では中身が取れない（JSリダイレクト）。
まず **タイトルで WebSearch して記事の実URLを見つけ**、そのURLを **WebFetch で開いて**
店名・住所・期間を確認する（`prtimes.jp` 等の直URLならそのまま WebFetch でよい）。
記事に住所がなければ、店名＋エリアでWebSearchして公式サイト・プレスリリースで補完する。

もし WebFetch が `EGRESS_BLOCKED` で失敗したら（設定が戻っている場合）、
以降は WebSearch の複数結果を突き合わせる方式に切り替える。プロキシの調査に時間を使わない。

いずれにせよ **`sources` には記事の実URL**（prtimes.jp、公式サイト、媒体の記事URL）を入れる。
`news.google.com` の中間URLは不可。

## 出力スキーマ（1件分）

```json
{"type": "new_cafe|popup|event", "genre": ["カフェ|スイーツ|コーヒー|パンケーキ|ベーカリー|コラボカフェ"],
 "name": "店名/イベント名（媒体名を含めない）", "area": "駅・街名", "address": "東京都〜（番地まで）",
 "lat": null, "lng": null,
 "period": {"start": "YYYY-MM-DD|null", "end": "YYYY-MM-DD|null"},
 "confidence": "official|media|unverified", "sources": ["記事の実URL"],
 "summary": "2〜3行・事実のみ", "collected_at": "今日の日付（JST）"}
```

## 採否のルール

- **アニメ・キャラクター・アイドル・ブランドIPのコラボカフェ／テーマカフェは、`genre` に必ず「コラボカフェ」を含める**（カフェ好き用途と分けてアプリで絞り込むため）。飲食要素があれば対象、グッズのみは対象外

- **推測で埋めない。** 住所・期間が確認できなければ出さない（少ないほうがマシ）
- **住所**: 番地まで確認できれば通常どおり。**番地が見つからないが丁目までは確実**な
  有望店は、`address` を丁目まで（例「東京都世田谷区北沢2丁目」）にして
  `confidence: "unverified"` で出してよい（アプリで🔴要確認表示になる）。
  町名すら不明なら出さない
- **new_cafe はオープン日を `period.start` に必ず入れる。** オープンから365日超は対象外
- **終了済みのポップアップ・催事は出さない**（今日より前に `end` が過ぎているもの）
- **グッズ販売のみのポップアップストア**（飲食要素なし）は対象外
- 「おすすめ10選」等のまとめ記事、東京都外、リニューアルのみ・単なる新メニューは対象外
- `confidence`: 公式プレスリリース・公式サイトで確認 → `official`、報道記事のみ → `media`
- 既に収録済みの店（`data/incoming/*.json` や `data/archive.json` に同名・同住所）は
  出しても構わない — 重複は `src.incoming append` が弾く。**わざわざ探して除外する必要はない**

## 書き出し方（必ずこの手順）

1. 新規アイテムの配列を `/tmp/rss_new.json` に書く（0件なら `[]`）
2. `python -m src.incoming append data/incoming/rss_structured.json /tmp/rss_new.json`
   → 検証・重複除外・追記を安全に行う。`invalid` が出たらその件を直して再実行
3. `python -m src.candidates mark-reviewed --today $(TZ=Asia/Tokyo date +%F)`
   → 今日見た候補を処理済みにする（明日のtodoから消える）

**`data/incoming/*.json` を直接編集・上書きしないこと。**
