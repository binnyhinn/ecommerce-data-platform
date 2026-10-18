import json
import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import Json
from confluent_kafka import Consumer

from src.config import (
    KAFKA_BOOTSTRAP, KAFKA_TOPIC, POSTGRES_HOST, POSTGRES_PORT,
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB,
)
from src.validation import validate_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/consumer.log")],
)
log = logging.getLogger("consumer")


def get_conn():
    return psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, user=POSTGRES_USER,
        password=POSTGRES_PASSWORD, dbname=POSTGRES_DB,
    )


def save_event(cur, event):
    cur.execute(
        "INSERT INTO raw_events (event_id, event_type, payload) "
        "VALUES (%s, %s, %s) ON CONFLICT (event_id) DO NOTHING",
        (event["event_id"], event["event_type"], Json(event)),
    )
    if cur.rowcount == 0:
        return False
    if event["event_type"] == "order":
        created_at = datetime.fromisoformat(event["timestamp"]).replace(tzinfo=None)
        cur.execute(
            "INSERT INTO orders (order_id, user_id, product_id, quantity, amount, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (order_id) DO NOTHING",
            (event["event_id"], event["user_id"], event["product_id"],
             event["quantity"], event["amount"], created_at),
        )
        cur.execute(
            "INSERT INTO revenue_per_minute (minute, order_count, revenue) "
            "VALUES (date_trunc('minute', %s::timestamp), 1, %s) "
            "ON CONFLICT (minute) DO UPDATE SET "
            "order_count = revenue_per_minute.order_count + 1, "
            "revenue = revenue_per_minute.revenue + EXCLUDED.revenue",
            (created_at, event["amount"]),
        )
    return True


def handle_message(conn, raw):
    try:
        event = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        log.warning("Invalid JSON, skipped")
        return "invalid"
    ok, reason = validate_event(event)
    if not ok:
        log.warning("Invalid event skipped: %s", reason)
        return "invalid"
    try:
        with conn.cursor() as cur:
            is_new = save_event(cur, event)
        conn.commit()
    except Exception:
        conn.rollback()
        log.exception("DB error, event not saved")
        return "error"
    return "saved" if is_new else "duplicate"


def main():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": "ecom-consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([KAFKA_TOPIC])
    conn = get_conn()
    counts = {"saved": 0, "duplicate": 0, "invalid": 0, "error": 0}
    log.info("Consumer started, reading topic '%s'", KAFKA_TOPIC)
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                log.error("Kafka error: %s", msg.error())
                continue
            result = handle_message(conn, msg.value())
            counts[result] += 1
            consumer.commit(msg)
            total = sum(counts.values())
            if total % 20 == 0:
                log.info("Processed %d events: %s", total, counts)
    except KeyboardInterrupt:
        log.info("Stopping consumer...")
    finally:
        consumer.close()
        conn.close()
        log.info("Done. Final counts: %s", counts)


if __name__ == "__main__":
    main()
