"""RabbitMQ publishing shared by the API and the worker."""
import json
import os

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
IMAGE_QUEUE = "image_processing"


def publish(queue: str, payload: dict) -> None:
    """One short connection per message.
    ponytail: fine at upload rates; keep a channel open if this gets hot."""
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
    finally:
        connection.close()
