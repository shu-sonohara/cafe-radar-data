# cafe-radar-data

東京都内の新規オープンカフェ・ポップアップ・催事情報を毎日収集し、
静的JSONとして配信する収集パイプライン。

配信URL: `https://<owner>.github.io/cafe-radar-data/data/items.json`

## 仕組み

```
① RSS取得（2時間おき / GitHub Actions）
   PR TIMES + GoogleニュースRSS → キーワード抽出 → 60日超の古い記事を除外
   → data/raw_candidates.json に蓄積 → 処理済み・同話題を除いた
   data/candidates_todo.json を生成（src/candidates.py）
② LLM収集・構造化（毎朝 / Claudeスケジュール実行）
   candidates_todo.json だけを見て prompts/structure.md で構造化、
   prompts/collect.md でWeb検索収集。追記は `python -m src.incoming append`
   に一本化（検証・重複除外・整形を担保）。処理済みURLは
   data/reviewed_urls.json に記録（src/candidates.py mark-reviewed）
③ 統合・配信（2時間おき / GitHub Actions / run_pipeline.py）
   検証 → 1次重複排除（店名+住所）→ 鮮度判定 → ジオコーディング（国土地理院API）
   → 2次重複排除（座標50m+店名類似）→ docs/data/items.json
```

**なぜ③がActions側なのか**: Claudeルーチンが動くクラウドサンドボックスからは
国土地理院API（msearch.gsi.go.jp）に到達できず、座標取得が100%失敗した。
外部APIを叩く処理はActionsに寄せ、ルーチンは収集・構造化に専念させている。
引けた住所は `data/geocode_cache.json` に記録し、次回以降は問い合わせない
（実測: 46件で40秒 → キャッシュヒット時0秒）。

## 開発

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q                                  # テスト
.venv/bin/python fetch_and_save.py                   # RSS取得
.venv/bin/python -m src.run_pipeline --today $(date +%F)  # 統合・配信JSON生成
```

## 収集の見直し（2026-08-29）

毎朝のルーチン報告で繰り返し挙がった問題への対策:
- 候補プールの汚染（2013〜2025年の古い記事、同一店の多媒体再配信）→ 取得時に60日超を除外、同話題を束ねる
- 未処理候補の再走査 → `reviewed_urls.json` で処理済みを記録し、todoだけを見せる
- LLMのその場しのぎ追記による上書き・整形崩れ → `src.incoming append` に一本化
- 外部サイト直接取得の遮断 → 指示書でWebSearch突き合わせを正式な裏取り手順に
- 固定クエリの陳腐化 → 年月・季節語を含める

## 配信データの点検

```bash
python -m src.review --items docs/data/items.json
```

機械的に判定できる異常（都外・位置なし・期間の逆転・重複の疑い・
出典がGoogleニュース経由など）を拾い、そのあとに目視確認用の一覧を出す。
「その店が実在するか」は自動判定できないので人の目で見る。

## データスキーマ

`docs/data/items.json` は `{"updated_at": "YYYY-MM-DD", "items": [...]}`。
各アイテムのフィールドは仕様書v1.1 §4.1に準拠し、配信時に `is_new`（新着バッジ）を付与。

確度ラベル: `official`（公式発表）/ `media`（報道）/ `unverified`（個人ブログ等）
