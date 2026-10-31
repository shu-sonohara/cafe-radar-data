import json
from pathlib import Path

from src import details
from src.details import (append_entries, attach, needs_check, priority,
                         select_todo, validate_entry)

TODAY = "2026-10-31"


def item(id_, type_="new_cafe", start="2026-10-01", end=None, collected="2026-10-20"):
    return {"id": id_, "type": type_, "name": f"店{id_}", "area": "渋谷",
            "address": "東京都渋谷区1-1", "period": {"start": start, "end": end},
            "sources": ["https://o.example.com/a", "https://o.example.com/b",
                        "https://o.example.com/c", "https://o.example.com/d"],
            "summary": "s" * 200, "collected_at": collected}


def test_needs_check_rules():
    assert needs_check(None, TODAY)
    fresh = {"hours": "10:00–19:00", "checked_at": "2026-10-01"}
    assert not needs_check(fresh, TODAY)                                   # 30日前・確認済み
    assert needs_check({"hours": "10:00–19:00", "checked_at": "2026-08-01"}, TODAY)  # 91日
    assert needs_check({"hours": None, "checked_at": "2026-10-01"}, TODAY)           # 不明は30日で再挑戦
    assert not needs_check({"hours": None, "checked_at": "2026-10-15"}, TODAY)


def test_priority_and_order():
    new_recent = item("a", start="2026-10-20")
    new_old = item("b", start="2026-05-01")
    popup_active = item("c", "popup", start="2026-10-01", end="2026-11-10")
    popup_soon = item("d", "popup", start="2026-10-01", end="2026-11-02")
    popup_noend = item("e", "popup", start="2026-10-01", end=None)
    popup_ended = item("f", "popup", start="2026-09-01", end="2026-10-30")
    new_recent2 = item("g", start="2026-10-25")
    assert priority(new_recent, TODAY) == 0
    assert priority(new_old, TODAY) == 2
    assert priority(popup_active, TODAY) == 1
    assert priority(popup_noend, TODAY) == 1
    assert priority(popup_ended, TODAY) == 2
    todo = select_todo([new_recent, new_old, popup_active, popup_soon, popup_noend,
                        popup_ended, new_recent2], {}, TODAY, limit=10)
    assert [t["id"] for t in todo] == ["g", "a", "d", "c", "e", "b", "f"]


def test_select_todo_respects_limit_and_skips_checked():
    items = [item(str(i), start="2026-10-01") for i in range(5)]
    det = {"0": {"hours": "x", "checked_at": "2026-10-30"}}
    todo = select_todo(items, det, TODAY, limit=2)
    assert len(todo) == 2 and "0" not in {t["id"] for t in todo}
    assert todo[0]["sources"] == ["https://o.example.com/a", "https://o.example.com/b",
                                  "https://o.example.com/c"]   # 出典は3つまで
    assert len(todo[0]["summary"]) == 120
    assert todo[0]["previous"] is None


def test_validate_entry():
    assert validate_entry({"id": "a", "hours": "10:00–19:00", "closed": None,
                           "source": "https://x.example.com"}) == []
    assert validate_entry({"id": "a", "hours": None, "closed": None, "source": None}) == []
    assert validate_entry({"id": "a", "hours": "10:00–19:00"})        # 出典なしは不可
    assert validate_entry({"id": "", "hours": None})
    assert validate_entry({"id": "a", "hours": "  "})
    assert validate_entry({"id": "a", "hours": "10:00", "source": "ftp://x"})


def test_append_entries_adds_updates_and_rejects():
    det = {}
    stats = append_entries(det, [
        {"id": "a", "hours": "10:00–19:00", "closed": "水曜", "source": "https://x.example.com"},
        {"id": "b", "hours": None, "closed": None, "source": None, "note": "公式記載なし"},
        {"id": "zzz", "hours": "9:00–17:00", "source": "https://x.example.com"},
        {"id": "c", "hours": "bad"},
    ], TODAY, known_ids={"a", "b", "c"})
    assert stats == {"added": 2, "updated": 0, "invalid": 1, "unknown_id": 1}
    assert det["a"]["checked_at"] == TODAY and det["a"]["closed"] == "水曜"
    assert det["b"]["hours"] is None and det["b"]["note"] == "公式記載なし"
    stats2 = append_entries(det, [{"id": "a", "hours": "11:00–20:00", "source": "https://y.example.com"}],
                            "2026-11-05", known_ids={"a", "b"})
    assert stats2["updated"] == 1 and det["a"]["hours"] == "11:00–20:00"
    assert det["a"]["checked_at"] == "2026-11-05"


def test_attach_adds_hours_or_null():
    det = {"a": {"hours": "10:00–19:00", "closed": None, "source": "https://x.example.com",
                 "note": "", "checked_at": TODAY}}
    out = attach([item("a"), item("b")], det)
    assert out[0]["hours"] == {"text": "10:00–19:00", "closed": None,
                               "checked_at": TODAY, "source": "https://x.example.com"}
    assert out[1]["hours"] is None


def test_cli_todo_and_append(tmp_path, monkeypatch):
    monkeypatch.setattr(details, "ITEMS_PATH", str(tmp_path / "items.json"))
    monkeypatch.setattr(details, "DETAILS_PATH", str(tmp_path / "details.json"))
    monkeypatch.setattr(details, "TODO_PATH", str(tmp_path / "todo.json"))
    (tmp_path / "items.json").write_text(json.dumps({"items": [item("a"), item("b")]}), encoding="utf-8")
    assert details.cmd_todo(TODAY, limit=1) == 1
    new = tmp_path / "new.json"
    new.write_text(json.dumps([{"id": "a", "hours": "10:00–19:00", "source": "https://x.example.com"}]),
                   encoding="utf-8")
    assert details.cmd_append(str(new), TODAY)["added"] == 1
    saved = json.loads((tmp_path / "details.json").read_text(encoding="utf-8"))
    assert saved["a"]["hours"] == "10:00–19:00"
    assert details.cmd_todo(TODAY, limit=5) == 1   # a は確認済みなので b だけ
