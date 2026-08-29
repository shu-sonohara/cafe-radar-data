from src.collab import is_collab_cafe, tag_collab


def _i(name, genre=("カフェ",)):
    return {"name": name, "genre": list(genre), "type": "popup"}


def test_detects_collab_keywords():
    for n in ["ブルーロックカフェ -青い監獄-コラボ", "映画ちいかわ Collaboration CAFE",
              "「くまのプーさん」OH MY CAFE", "とっとこハムちゃんずCAFE（THEキャラCAFE）",
              "呪術廻戦カフェ2026 5th Anniversary", "初音ミク テーマカフェ"]:
        assert is_collab_cafe(_i(n)), n


def test_plain_cafes_are_not_collab():
    for n in ["八三六（Hachi San Roku）", "秋の栗スイーツフェア", "Bacha Coffee 新丸ビル"]:
        assert not is_collab_cafe(_i(n)), n


def test_tag_adds_genre_once_and_keeps_others():
    item = tag_collab(_i("BLEACH コラボカフェ", ("カフェ", "スイーツ")))
    assert item["genre"] == ["カフェ", "スイーツ", "コラボカフェ"]
    assert tag_collab(item)["genre"].count("コラボカフェ") == 1


def test_tag_leaves_non_collab_untouched():
    item = _i("八三六")
    assert tag_collab(item)["genre"] == ["カフェ"]
