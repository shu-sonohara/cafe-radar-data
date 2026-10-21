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

**WebFetch が失敗したときの判断**（エラー文字列は環境更新で変わるので文字列に依存しない）:
- 特定サイトだけ 403 / 503 / 404 → そのサイトのbot対策や欠番。別の媒体のURLを試す
- `prtimes.jp` と `example.com` の両方が失敗する（`EGRESS_BLOCKED`、`ENOTFOUND`、CONNECT 403 など種類を問わず）
  → 環境のネットワークが閉じている。以降は WebSearch の複数結果を突き合わせる方式に切り替え、
  最後の報告で「WebFetch不可（エラー: …）」と伝える。プロキシの調査に時間を使わない

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
- **オープン日や住所が「11月下旬」「○○駅前」のように未確定だが有望な候補は、捨てずに保留する**（下記「書き出し方」の手順2）。
  確定したら通常どおり出力する。`todo` の先頭に `source: "pending:再確認"` として再浮上するので、そのときに改めて調べる
- **終了済みのポップアップ・催事は出さない**（今日より前に `end` が過ぎているもの）
- **グッズ販売のみのポップアップストア**（飲食要素なし）は対象外
- 「おすすめ10選」等のまとめ記事、東京都外、リニューアルのみ・単なる新メニューは対象外
- `confidence`: 公式プレスリリース・公式サイトで確認 → `official`、報道記事のみ → `media`
- 既に収録済みの店（`data/incoming/*.json` や `data/archive.json` に同名・同住所）は
  出しても構わない — 重複は `src.incoming append` が弾く。**わざわざ探して除外する必要はない**

## 書き出し方（必ずこの手順）

1. 新規アイテムの配列を `/tmp/rss_new.json` に書く（0件なら `[]`）
2. `python3 -m src.incoming append data/incoming/rss_structured.json /tmp/rss_new.json`
   → 検証・重複除外・追記を安全に行う。`invalid` が出たらその件を直して再実行
3. 日付・住所が未確定の有望候補は保留する（該当なしなら省略）:
   `python3 -m src.candidates hold --today "$TODAY" --url "<候補のurl>" --title "<店名>" --note "<未確定の理由と分かっていること>" --days 7`
   → 7日後の todo に「pending:再確認」として再浮上する。再確認してもまだ未確定なら同じコマンドで再保留（初出から60日で自動的に諦める）
4. `python3 -m src.candidates mark-reviewed --today "$TODAY"`
   → 今日見た候補を処理済みにする（明日のtodoから消える。保留した候補は期日まで消える）

**`data/incoming/*.json` と `data/pending.json` を直接編集・上書きしないこと。**
