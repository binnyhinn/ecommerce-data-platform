from src.validation import validate_event


def base_event(**overrides):
    event = {
        "event_id": "11111111-1111-1111-1111-111111111111",
        "event_type": "page_view",
        "user_id": 1,
        "product_id": 101,
        "timestamp": "2026-10-18T14:00:00+00:00",
    }
    event.update(overrides)
    return event


def test_valid_page_view():
    ok, _ = validate_event(base_event())
    assert ok


def test_valid_order():
    ok, _ = validate_event(base_event(event_type="order", quantity=2, amount=998.0))
    assert ok


def test_missing_field():
    event = base_event()
    del event["user_id"]
    ok, reason = validate_event(event)
    assert not ok
    assert "user_id" in reason


def test_invalid_event_type():
    ok, _ = validate_event(base_event(event_type="refund"))
    assert not ok


def test_order_bad_quantity():
    ok, _ = validate_event(base_event(event_type="order", quantity=0, amount=100.0))
    assert not ok


def test_order_bad_amount():
    ok, _ = validate_event(base_event(event_type="order", quantity=1, amount=-5))
    assert not ok


def test_not_a_dict():
    ok, _ = validate_event("hello")
    assert not ok
