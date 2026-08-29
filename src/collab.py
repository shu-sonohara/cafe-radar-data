"""コラボカフェ（アニメ・キャラクター・ブランドIPのテーマカフェ）の判定とタグ付け。

nao の判断（2026-08-29）: コラボカフェは配信に残し、アプリ側で
「コラボカフェ」チップで絞り込めるようにする。LLMの指示書でも genre に
必ず「コラボカフェ」を入れるよう求めるが、漏れた場合の安全網としてここで
店名からも判定する。
"""
import re

COLLAB_GENRE = "コラボカフェ"
_PATTERNS = re.compile(
    r"コラボ|collaboration|collabo|oh my cafe|theキャラ|キャラcafe|キャラカフェ|"
    r"テーマカフェ|anniversary|記念カフェ|カフェ20\d\d|×",
    re.IGNORECASE,
)


def is_collab_cafe(item: dict) -> bool:
    if COLLAB_GENRE in item.get("genre", []):
        return True
    return bool(_PATTERNS.search(item.get("name", "")))


def tag_collab(item: dict) -> dict:
    if not is_collab_cafe(item) or COLLAB_GENRE in item["genre"]:
        return item
    return {**item, "genre": list(item["genre"]) + [COLLAB_GENRE]}
