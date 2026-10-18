import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer

from src.config import KAFKA_BOOTSTRAP, KAFKA_TOPIC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/producer.log")],
)
log = logging.getLogger("producer")

PRODUCTS = {101: 499.0, 102: 1299.0, 103: 249.0, 104: 899.0, 105: 59.0}
EVENT_TYPES = ["page_view", "add_to_cart", "order"]
EVENT_WEIGHTS = [70, 20, 10]


def make_event():
    event_type = random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS)[0]
    product_id = random.choice(list(PRODUCTS))
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "user_id": random.randint(1, 500),
        "product_id": product_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if event_type == "order":
        qty = random.randint(1, 3)
        event["quantity"] = qty
        event["amount"] = round(PRODUCTS[product_id] * qty, 2)
    return event


def on_delivery(err, msg):
    if err is not None:
        log.error("Delivery failed: %s", err)


def main():
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    log.info("Producer started, sending to topic '%s'", KAFKA_TOPIC)
    sent = 0
    try:
        while True:
            event = make_event()
            producer.produce(
                KAFKA_TOPIC,
                key=str(event["user_id"]),
                value=json.dumps(event),
                callback=on_delivery,
            )
            producer.poll(0)
            sent += 1
            if sent % 20 == 0:
                log.info("Sent %d events", sent)
            time.sleep(random.uniform(0.2, 1.0))
    except KeyboardInterrupt:
        log.info("Stopping producer...")
    finally:
        producer.flush()
        log.info("Done. Total events sent: %d", sent)


if __name__ == "__main__":
    main()
