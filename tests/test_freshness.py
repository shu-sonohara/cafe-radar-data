from src.freshness import is_visible, is_new_badge


def _item(type_, start, end, collected_at="2026-08-01"):
    return {"type": type_, "period": {"start": start, "end": end},
            "collected_at": collected_at}


def test_ended_event_hidden():
    assert is_visible(_item("event", "2026-08-01", "2026-08-10"), "2026-08-19") is False


def test_running_event_visible():
    assert is_visible(_item("event", "2026-08-01", "2026-08-31"), "2026-08-19") is True


def test_event_visible_on_its_last_day():
    assert is_visible(_item("event", "2026-08-01", "2026-08-19"), "2026-08-19") is True


def test_popup_unknown_end_hidden_after_30_days():
    item = _item("popup", "2026-07-01", None, collected_at="2026-07-01")
    assert is_visible(item, "2026-07-30") is True
    assert is_visible(item, "2026-08-01") is False


def test_new_cafe_unknown_end_always_visible():
    item = _item("new_cafe", "2026-01-01", None, collected_at="2026-01-01")
    assert is_visible(item, "2026-08-19") is True


def test_new_badge_within_90_days_only():
    assert is_new_badge(_item("new_cafe", "2026-06-01", None), "2026-08-19") is True
    assert is_new_badge(_item("new_cafe", "2026-01-01", None), "2026-08-19") is False


def test_events_never_get_new_badge():
    assert is_new_badge(_item("event", "2026-08-18", "2026-08-31"), "2026-08-19") is False


def test_missing_start_treated_as_collected_date():
    item = _item("popup", None, None, collected_at="2026-08-01")
    assert is_visible(item, "2026-08-19") is True
    assert is_visible(item, "2026-09-15") is False


def test_future_opening_gets_no_new_badge_yet():
    assert is_new_badge(_item("new_cafe", "2026-09-01", None), "2026-08-19") is False
