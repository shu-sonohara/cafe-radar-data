"""日付未確定の有望店を「保留」して、数日後に再確認する仕組み（2026-10-21）。"""
import json
from pathlib import Path

from src.candidates import cmd_hold, cmd_mark_reviewed, cmd_todo


def _setup(tmp_path, monkeypatch, raw=None, reviewed=None, pending=None, todo=None):
    import src.candidates as c
    monkeypatch.setattr(c, "RAW_PATH", str(tmp_path / "raw.json"))
    monkeypatch.setattr(c, "REVIEWED_PATH", str(tmp_path / "reviewed.json"))
    monkeypatch.setattr(c, "PENDING_PATH", str(tmp_path / "pending.json"))
    monkeypatch.setattr(c, "TODO_PATH", str(tmp_path / "todo.json"))
    for name, data in (("raw", raw), ("reviewed", reviewed), ("pending", pending), ("todo", todo)):
        if data is not None:
            (tmp_path / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _read(tmp_path, name):
    return json.loads((tmp_path / f"{name}.json").read_text(encoding="utf-8"))


def test_hold_records_entry_with_hold_until(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, raw=[], reviewed={}, pending=[])
    cmd_hold(today="2026-10-21", url="https://a", title="ペンギンベーカリー高田馬場店",
             note="開店日が「11月下旬」のみ。住所は新宿区高田馬場2-1-2", days=7)
    p = _read(tmp_path, "pending")
    assert p[0]["url"] == "https://a"
    assert p[0]["hold_until"] == "2026-10-28"
    assert p[0]["first_seen"] == "2026-10-21"


def test_todo_resurfaces_due_pending_even_if_reviewed(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, raw=[], reviewed={"https://a": "2026-10-21"},
           pending=[{"url": "https://a", "title": "保留店", "note": "日付未確定",
                     "first_seen": "2026-10-21", "hold_until": "2026-10-28"}])
    cmd_todo(today="2026-10-27")
    assert _read(tmp_path, "todo") == []            # まだ期日前
    cmd_todo(today="2026-10-28")
    todo = _read(tmp_path, "todo")
    assert [c["url"] for c in todo] == ["https://a"]
    assert todo[0]["source"] == "pending:再確認"
    assert "日付未確定" in todo[0]["summary"]


def test_mark_reviewed_drops_due_pending_but_keeps_reheld(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, raw=[], reviewed={},
           pending=[{"url": "https://a", "title": "A", "note": "", "first_seen": "2026-10-21", "hold_until": "2026-10-28"},
                    {"url": "https://b", "title": "B", "note": "", "first_seen": "2026-10-21", "hold_until": "2026-10-28"}],
           todo=[{"url": "https://a", "title": "A", "also_urls": [], "source": "pending:再確認"},
                 {"url": "https://b", "title": "B", "also_urls": [], "source": "pending:再確認"}])
    cmd_hold(today="2026-10-28", url="https://b", title="B", note="まだ未確定", days=7)  # Bは再保留
    cmd_mark_reviewed(today="2026-10-28")
    p = _read(tmp_path, "pending")
    assert [e["url"] for e in p] == ["https://b"]
    assert p[0]["hold_until"] == "2026-11-04"
    assert p[0]["first_seen"] == "2026-10-21"      # 初出日は引き継ぐ
    assert "https://a" in _read(tmp_path, "reviewed")


def test_pending_expires_after_max_days(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, raw=[], reviewed={},
           pending=[{"url": "https://old", "title": "古い保留", "note": "", "first_seen": "2026-08-01", "hold_until": "2026-10-21"}])
    cmd_todo(today="2026-10-21")
    assert _read(tmp_path, "todo") == []           # 60日超は諦めて出さない
    assert _read(tmp_path, "pending") == []        # pending からも消える
