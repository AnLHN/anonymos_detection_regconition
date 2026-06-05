import json
import signal
import sys
import time
from pathlib import Path
from typing import Any

import pika

ROOT = Path(__file__).resolve().parents[2]
AI_WORKER_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AI_WORKER_DIR))

from config import RABBITMQ_URL
from postgres_event_service import PostgresEventService
from rabbitmq_event_publisher import ALERT_EVENTS_QUEUE


class AlertConsumer:
    def __init__(self) -> None:
        self.event_service = PostgresEventService()
        self.should_stop = False
        self.connection: pika.BlockingConnection | None = None

    def run(self) -> None:
        while not self.should_stop:
            try:
                self._consume()
            except pika.exceptions.AMQPError as error:
                print(f"RabbitMQ consumer connection error: {error}")
                time.sleep(5)

    def stop(self, *_: object) -> None:
        self.should_stop = True
        if self.connection and self.connection.is_open:
            self.connection.close()

    def _consume(self) -> None:
        parameters = pika.URLParameters(RABBITMQ_URL)
        self.connection = pika.BlockingConnection(parameters)
        channel = self.connection.channel()
        channel.queue_declare(queue=ALERT_EVENTS_QUEUE, durable=True)
        channel.basic_qos(prefetch_count=10)
        channel.basic_consume(queue=ALERT_EVENTS_QUEUE, on_message_callback=self._handle_message)
        print(f"Alert consumer listening on queue: {ALERT_EVENTS_QUEUE}")
        channel.start_consuming()

    def _handle_message(self, channel: Any, method: Any, _properties: Any, body: bytes) -> None:
        try:
            event = json.loads(body.decode("utf-8"))
            self.event_service.insert_unknown_event(event)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            print("alert persisted", event.get("camera_id"), event.get("warning_type"), event.get("event_id"))
        except Exception as error:
            print(f"Failed to persist alert event, requeueing: {error}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    consumer = AlertConsumer()
    signal.signal(signal.SIGINT, consumer.stop)
    signal.signal(signal.SIGTERM, consumer.stop)
    consumer.run()


if __name__ == "__main__":
    main()
