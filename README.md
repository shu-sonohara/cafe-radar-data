# cafe-radar-data

東京都内の新規オープンカフェ・ポップアップ・催事情報を毎日収集し、
静的JSONとして配信する収集パイプライン。

配信URL: `https://<owner>.github.io/cafe-radar-data/data/items.json`

## 仕組み

```
① RSS取得（2時間おき / GitHub Actions）
   PR TIMES全件フィード → キーワード抽出 → data/raw_candidates.json に蓄積
② LLM収集・構造化（毎朝 / Claudeスケジュール実行）
   prompts/collect.md でWeb検索収集 + prompts/structure.md で①を構造化
   → data/incoming/*.json
③ 統合（毎朝 / run_pipeline.py）
   検証 → 1次重複排除（店名+住所）→ ジオコーディング（国土地理院API）
   → 2次重複排除（座標50m+店名類似）→ 鮮度判定 → docs/data/items.json
```

## 開発

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q                                  # テスト
.venv/bin/python fetch_and_save.py                   # RSS取得
.venv/bin/python -m src.run_pipeline --today $(date +%F)  # 統合・配信JSON生成
```

## データスキーマ

`docs/data/items.json` は `{"updated_at": "YYYY-MM-DD", "items": [...]}`。
各アイテムのフィールドは仕様書v1.1 §4.1に準拠し、配信時に `is_new`（新着バッジ）を付与。

確度ラベル: `official`（公式発表）/ `media`（報道）/ `unverified`（個人ブログ等）
