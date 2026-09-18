"""
This file defines a Django management command that runs a RabbitMQ consumer.
The command connects to RabbitMQ and listens for new messages.
It works in an async loop and stops only when the process is closed.
"""
import asyncio
from typing import Any

from django.core.management.base import BaseCommand

from innotter.rabbitMQ_service import setup_rabbitmq, consume_message


class Command(BaseCommand):
    """
    This command starts a RabbitMQ consumer for the service.
    It helps the app listen to messages from RabbitMQ.
    """
    help = "Runs RabbitMQ consumer for deletion user data in the Innotter Service"

    def handle(self, *args: Any, **options: Any) -> None:
        """
        This method runs when the command starts.
        It prints a start message and calls the async runner.
        It also handles manual stop with Ctrl+C.
        """
        self.stdout.write(self.style.SUCCESS("Starting RabbitMQ consumer"))

        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nConsumer stopped manually."))

    async def run_async(self) -> None:
        """
        This method sets up the RabbitMQ connection.
        It creates the needed queues and starts listening for messages.
        """
        await setup_rabbitmq()

        await consume_message()