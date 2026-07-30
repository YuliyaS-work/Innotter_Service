from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from innotter.rabbitMQ_service import get_connection, setup_rabbitmq, consume_message, process_message


@pytest.mark.asyncio
@patch("innotter.rabbitMQ_service.aio_pika.connect_robust")
async def test_get_connection(mock_connection, mock_conn,  caplog):
    """ This test checks a connection to the RabbitMQ."""
    # Arrange
    mock_connection.return_value = mock_conn
    caplog.set_level("INFO")

    # Act
    await get_connection()

    # Assert
    assert "RabbitMq connection was established" in caplog.text


@pytest.mark.asyncio
@patch("innotter.rabbitMQ_service.get_connection")
async def test_setup_rabbitmq_success(mock_connection, mock_conn, caplog):
    """
    Test checks that RabbitMQ queues and exchanges are created successfully
    and the connection is closed.
    """
    # Arrange
    mock_connection.return_value = mock_conn
    channel = AsyncMock()
    mock_conn.channel = AsyncMock(return_value=channel)
    mock_conn.close = AsyncMock()

    channel.set_qos = AsyncMock()
    channel.declare_exchange = AsyncMock()

    main_queue = AsyncMock()
    retry_queue = AsyncMock()
    dlq = AsyncMock()

    channel.declare_queue = AsyncMock(side_effect=[main_queue, retry_queue, dlq])
    retry_queue.bind = AsyncMock()

    caplog.set_level("INFO")

    # Act
    await setup_rabbitmq()

    # Assert
    assert "Queues was created." in caplog.text
    channel.set_qos.assert_awaited_once()
    channel.declare_exchange.assert_awaited_once_with("waiting_deletion_exchange", "direct")
    assert channel.declare_queue.await_count == 3
    retry_queue.bind.assert_awaited_once_with(channel.declare_exchange.return_value, "waiting_deletion_key")
    mock_conn.close.assert_awaited_once()


@pytest.mark.asyncio
@patch("innotter.rabbitMQ_service.get_connection")
async def test_setup_rabbitmq_fail(mock_connection, mock_conn, caplog):
    """
    Test checks that setup_rabbitmq logs an error and raises an exception
    when channel initialization fails.
    """
    # Arrange
    mock_connection.return_value = mock_conn
    mock_conn.channel.side_effect = Exception()

    caplog.set_level("ERROR")

    # Act
    with pytest.raises(Exception):
        await setup_rabbitmq()

    # Assert
    assert "Failed to initialized RabbitMq" in caplog.text


@pytest.mark.asyncio
@patch("innotter.rabbitMQ_service.process_message", new_callable=AsyncMock)
@patch("innotter.rabbitMQ_service.get_connection")
async def test_consume_message(
        mock_connection,
        mock_process_message,
        mock_conn
):
    """
    Test checks that consume_message reads messages from the queue
    and processes each one successfully.
    """
    # Arrange
    mock_connection.return_value = mock_conn
    mock_conn.__aenter__.return_value = mock_conn
    mock_conn.__aexit__.return_value = False

    channel = AsyncMock()
    mock_conn.channel = AsyncMock(return_value=channel)

    queue = AsyncMock()
    channel.get_queue = AsyncMock(return_value=queue)

    channel.default_exchange = AsyncMock()

    msg = AsyncMock()
    async def fake_iter():
        yield msg


    fake_iterator = MagicMock()
    fake_iterator.__aenter__.return_value = fake_iter()
    fake_iterator.__aexit__.return_value = False

    queue.iterator = MagicMock(return_value=fake_iterator)

    # Act
    await consume_message()

    # Assert
    mock_conn.channel.assert_awaited_once()
    channel.get_queue.assert_awaited_once_with("delete-user-data")
    mock_process_message.assert_awaited_once_with(msg, channel.default_exchange)


@pytest.mark.asyncio
@patch("innotter.rabbitMQ_service.IncomingBodyMessage")
@patch("innotter.rabbitMQ_service.delete_user_data")
async def test_process_message_success(
        mock_delete,
        mock_serializer
):
    """
    Test checks that a valid message triggers delete_user_data.delay
    and message is acknowledgment.
    """
    # Arrange
    message = MagicMock()
    message.body = b'{"user_id": "123"}'
    message.ack = AsyncMock()

    default_exchange = MagicMock()

    mock_serializer.return_value.is_valid.return_value = True
    mock_serializer.return_value.validated_data = {"user_id": "123"}

    # Act
    await process_message(message, default_exchange)

    # Assert
    mock_delete.delay.assert_called_once_with("123")
    message.ack.assert_awaited_once()


@pytest.mark.asyncio
@patch("innotter.rabbitMQ_service.delete_user_data")
async def test_process_message_invalid_json(mock_delete):
    """
    Test checks that the message has an invalid JSON body
    and one is sent to the DLQ and acknowledged.
    """
    # Arrange
    message = MagicMock()
    message.body = b"{invalid json"
    message.ack = AsyncMock()

    default_exchange = MagicMock()
    default_exchange.publish = AsyncMock()

    # Act
    await process_message(message, default_exchange)

    # Assert
    default_exchange.publish.assert_awaited_once()
    message.ack.assert_awaited_once()
    mock_delete.delay.assert_not_called()


@pytest.mark.asyncio
@patch("innotter.rabbitMQ_service.IncomingBodyMessage")
@patch("innotter.rabbitMQ_service.delete_user_data")
async def test_process_message_not_valid_data(
        mock_delete,
        mock_serializer
):
    """
    Test checks that the serializer data is invalid
    and message is published to DLQ.
    """
    # Arrange
    message = MagicMock()
    message.body = b'{"user_id": "123"}'
    message.ack = AsyncMock()

    default_exchange = MagicMock()
    default_exchange.publish = AsyncMock()

    mock_serializer.return_value.is_valid.return_value = False

    # Act
    await process_message(message, default_exchange)

    # Assert
    mock_delete.delay.assert_not_called()
    message.ack.assert_awaited_once()


@pytest.mark.asyncio
@patch("innotter.rabbitMQ_service.IncomingBodyMessage")
@patch("innotter.rabbitMQ_service.delete_user_data")
async def test_process_message_not_delete(
        mock_delete,
        mock_serializer
):
    """
    Test checks that the deletion of data user was failed
    and the message returns to the main queue.
    """
    # Arrange
    message = MagicMock()
    message.body = b'{"user_id": "123"}'
    message.ack = AsyncMock()
    message.nack = AsyncMock()

    default_exchange = MagicMock()

    mock_serializer.return_value.is_valid.return_value = True
    mock_serializer.return_value.validated_data = {"user_id": "123"}

    mock_delete.delay.side_effect = Exception()

    # Act
    await process_message(message, default_exchange)

    # Assert
    mock_delete.delay.assert_called_once_with("123")
    message.ack.assert_not_called()
    message.nack.assert_awaited_once()