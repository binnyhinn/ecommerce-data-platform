VALID_TYPES = {"page_view", "add_to_cart", "order"}
REQUIRED = ["event_id", "event_type", "user_id", "product_id", "timestamp"]


def validate_event(event):
    if not isinstance(event, dict):
        return False, "event is not an object"
    for field in REQUIRED:
        if field not in event:
            return False, "missing " + field
    if event["event_type"] not in VALID_TYPES:
        return False, "invalid event_type"
    if event["event_type"] == "order":
        if event.get("quantity", 0) <= 0:
            return False, "bad quantity"
        if event.get("amount", 0) <= 0:
            return False, "bad amount"
    return True, ""
