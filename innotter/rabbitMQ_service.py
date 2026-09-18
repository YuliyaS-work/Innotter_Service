"""
This file contains helper functions for working with RabbitMQ.
It creates the needed queues and listens for messages from the broker.
The functions help the service process user deletion events asynchronously.
"""
import json
import logging

import aio_pika

from config import settings
from innotter.serializers import IncomingBodyMessage
from innotter.tasks import delete_user_data

logger = logging.getLogger(__name__)

async def get_connection() -> aio_pika.RobustConnection:
    """ Create a connection to RabbitMQ using the URL from settings."""
    connection =  await aio_pika.connect_robust(settings.RABBITMQ_URL)
    logger.info("RabbitMq connection was established")
    return connection


async def setup_rabbitmq() -> None:
    """
    Set up RabbitMQ queues and exchanges for user deletion messages.
    It creates the main queue, a waiting queue, and a dead-letter queue.
    """
    connection = await get_connection()
    try:
        channel = await connection.channel()
        logger.info("RabbitMq channel was established")

        await channel.set_qos(prefetch_count=10)

        waiting_deletion_exchange = await channel.declare_exchange("waiting_deletion_exchange", "direct")

        await channel.declare_queue(
            "delete-user-data",
            durable=True,
            arguments={
                "x-dead-letter-exchange": "waiting_deletion_exchange",
                "x-dead-letter-routing-key": "waiting_deletion_key"
            }
        )

        waiting_deletion = await channel.declare_queue(
            "wait-deletion-user-data",
            durable=True,
            arguments={
                "x-message-ttl": 30000,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": "delete-user-data"
            }
        )

        await waiting_deletion.bind(waiting_deletion_exchange, "waiting_deletion_key")

        await channel.declare_queue(
            "delete-user-data-dlq",
            durable=True
        )

        logger.info("Queues was created.")

    except Exception:
        logger.exception("Failed to initialized RabbitMq")
        raise
    finally:
        await connection.close()


async def consume_message() -> None:
    """
    Start reading messages from the main RabbitMQ queue.
    The function waits for new messages and sends each one to the processor.
    """
    connection = await get_connection()
    async with connection:
        channel = await connection.channel()
        queue =  await channel.get_queue("delete-user-data")

        default_exchange = channel.default_exchange

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await process_message(message, default_exchange)


async def process_message(
        message: aio_pika.IncomingMessage,
        default_exchange: aio_pika.Exchange
) -> None:
    """
    Process a single RabbitMQ message.
    It checks JSON format, validates the data, and sends the task to Celery.
    If the message is invalid, it is moved to the dead-letter queue.
    """
    try:
        body_dict = json.loads(message.body.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Message is not a valid JSON: {e}")
        await default_exchange.publish(
            aio_pika.Message(body=message.body),
            routing_key="delete-user-data-dlq"
        )
        await message.ack()
        return

    serializer = IncomingBodyMessage(data=body_dict)

    if not serializer.is_valid():
        logger.error("Invalid body message")
        await default_exchange.publish(
            aio_pika.Message(body=message.body),
            routing_key="delete-user-data-dlq"
        )
        await message.ack()
        return

    user_id = serializer.validated_data.get("user_id")

    logger.info(f"Validated incoming message data, user ID={user_id}")


    try:
        delete_user_data.delay(user_id)
        await message.ack()
        logger.info(f"User was deleted successfully, user ID={user_id}")

    except Exception as e:
        logger.error(f"Error: failed user data deletion, user ID={user_id}, {e} ")
        await message.nack(requeue=False)