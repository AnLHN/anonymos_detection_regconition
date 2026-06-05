import json
from typing import Any

import pika

from config import RABBITMQ_URL

ALERT_EVENTS_QUEUE = "alert_events"


class RabbitMQEventPublisher:
    def __init__(self, rabbitmq_url: str = RABBITMQ_URL, queue_name: str = ALERT_EVENTS_QUEUE) -> None:
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name

    def publish_alert_event(self, event: dict[str, Any]) -> None:
        parameters = pika.URLParameters(self.rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(event, ensure_ascii=False).encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )
        finally:
            connection.close()
