import asyncio
import json
import logging
import ssl
import threading
from datetime import datetime, timezone
from typing import Optional, Union

import aio_pika
from aio_pika import DeliveryMode, ExchangeType


class RabbitMQLogPublisher:
    """Simple helper to push logs to a RabbitMQ exchange."""

    def __init__(
        self,
        url: str,
        service_name: str,
        exchange_name: str,
        ca_cert_path: str,
        client_cert_path: str,
        client_key_path: str,
    ) -> None:
        self.url = url
        self.service_name = service_name
        self.exchange_name = exchange_name

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
        )
        self._thread.start()

        self._ssl_context = self._build_ssl_context(
            ca_cert_path, client_cert_path, client_key_path
        )
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

        # Fail fast when params are wrong.
        self._run(self._connect())

    def _run(self, coro: asyncio.Future) -> None:
        asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    @staticmethod
    def _build_ssl_context(ca: str, cert: str, key: str) -> ssl.SSLContext:
        ctx = ssl.create_default_context(cafile=ca)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.load_cert_chain(certfile=cert, keyfile=key)
        return ctx

    async def _connect(self) -> None:
        self._connection = await aio_pika.connect_robust(
            self.url,
            ssl_context=self._ssl_context,
        )
        self._channel = await self._connection.channel(publisher_confirms=True)
        await self._channel.set_qos(prefetch_count=1)
        self._exchange = await self._channel.declare_exchange(
            self.exchange_name,
            type=ExchangeType.TOPIC,
            durable=True,
        )

    async def _ensure_ready(self) -> None:
        if not self._connection or self._connection.is_closed:
            await self._connect()
            return
        if not self._channel or self._channel.is_closed:
            self._channel = await self._connection.channel(publisher_confirms=True)
            await self._channel.set_qos(prefetch_count=1)
        if not self._exchange:
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name,
                type=ExchangeType.TOPIC,
                durable=True,
            )

    @staticmethod
    def _severity_name(value: Union[int, str]) -> str:
        if isinstance(value, int):
            name = logging.getLevelName(value)
        else:
            name = value.upper()
        if isinstance(name, str) and name in logging._nameToLevel:
            return name
        raise ValueError(f"Invalid severity {value}")

    def publish_log(
        self,
        severity: Union[int, str],
        message: str,
        file_name: Optional[str] = None,
    ) -> None:
        """Send a log entry with a timestamp."""
        level = self._severity_name(severity)
        payload = {
            "service": self.service_name,
            "severity": level,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if file_name:
            payload["file"] = file_name
        routing_key = f"{self.service_name}.{level}"
        self._run(self._publish(routing_key, payload))

    async def _publish(self, routing_key: str, payload: dict) -> None:
        await self._ensure_ready()
        if not self._exchange:
            raise RuntimeError("RabbitMQ exchange is not available")
        message = aio_pika.Message(
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=routing_key)

    def close(self) -> None:
        try:
            self._run(self._close_async())
        finally:
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join()

    async def _close_async(self) -> None:
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
