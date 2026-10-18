# Real-Time E-Commerce Data Platform

A streaming data pipeline: fake store events flow through Kafka, get validated and stored in PostgreSQL, and show up on a live dashboard.

![Dashboard](docs/dashboard.png)

## Architecture

    Event generator (Python)
            |
            v
    Kafka (topic: ecommerce-events)
            |
            v
    Consumer (Python: validate, dedupe, aggregate)
            |
            v
    PostgreSQL (raw_events, orders, revenue_per_minute)
            |
            v
    Streamlit dashboard (auto-refresh every 5 seconds)

## Tech stack

Python, Apache Kafka (confluent-kafka), PostgreSQL, Docker Compose, Streamlit, pandas, pytest

## Features

- Producer generates page_view, add_to_cart and order events
- Consumer validates every event, skips invalid ones and logs a warning
- Idempotent writes: a duplicate event_id is ignored (ON CONFLICT DO NOTHING)
- Raw layer (raw_events) and transformed layer (orders, revenue_per_minute)
- Kafka offsets are committed only after an event is handled
- Logging to console and to files in logs/
- Unit tests for the validation rules

## Project structure

    src/producer.py      generates events and sends them to Kafka
    src/consumer.py      reads from Kafka, validates, writes to PostgreSQL
    src/validation.py    event validation rules
    src/dashboard.py     Streamlit live dashboard
    src/config.py        settings from environment variables
    sql/init.sql         table definitions
    tests/               pytest unit tests
    docker-compose.yml   Kafka and PostgreSQL

## How to run

Create a .env file with POSTGRES_USER=ecom, POSTGRES_PASSWORD=ecom123 and POSTGRES_DB=ecommerce (it is not committed to git).

Start Kafka and PostgreSQL:

    docker compose up -d

Create the Kafka topic:

    docker exec kafka /opt/kafka/bin/kafka-topics.sh --create --topic ecommerce-events --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

Install dependencies:

    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt

Run each of these in its own terminal:

    python -m src.producer
    python -m src.consumer
    python -m streamlit run src/dashboard.py

The dashboard opens at http://localhost:8501

Run the tests:

    python -m pytest -v

## Design notes

- Timestamps are stored in UTC
- Delivery is at-least-once: offsets are committed after processing, and duplicates are handled by idempotent inserts
- PostgreSQL is exposed on host port 5433 to avoid clashing with other local databases

## Possible improvements

- Dead-letter topic for invalid events
- Run the producer, consumer and dashboard as Docker services
- Add batch rollups with Airflow or dbt
