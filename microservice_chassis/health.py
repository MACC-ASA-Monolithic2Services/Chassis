# microservice_chassis/health.py
import logging
import os
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional, Protocol

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .rabbitmq_logger import RabbitMQLogPublisher  # ya existe en el Chassis

logger = logging.getLogger(__name__)


class DBDependency(Protocol):
    """Protocolo para el dependency get_db de FastAPI."""

    async def __call__(self) -> AsyncSession:  # pragma: no cover, solo typing
        ...


RabbitCheck = Callable[[], Awaitable[bool]]


@dataclass
class HealthConfig:
    """
    Config comun para generar el endpoint /service/health en cualquier
    microservicio.

    - service_name: nombre del servicio (para logs).
    - get_db: dependency de FastAPI que devuelve AsyncSession (get_db).
    - logger_mq: publisher de RabbitMQ para logs (opcional).
    - rabbit_check: funcion async que comprueba la conexion RabbitMQ (opcional).
    - public_key_path: ruta a la clave publica a comprobar (opcional).
    - db_cache_ttl_seconds: segundos que dura la cache de estado de BD.
    - rabbit_cache_ttl_seconds: segundos que dura la cache de estado de Rabbit.
    - public_key_cache_ttl_seconds: segundos que dura la cache de la public key.
    """

    service_name: str
    get_db: DBDependency
    logger_mq: Optional[RabbitMQLogPublisher] = None
    rabbit_check: Optional[RabbitCheck] = None
    public_key_path: Optional[str] = None

    db_cache_ttl_seconds: int = 30
    rabbit_cache_ttl_seconds: int = 30
    public_key_cache_ttl_seconds: int = 60


def create_health_router(config: HealthConfig) -> APIRouter:
    """
    Crea un router FastAPI con el endpoint /service/health que:
      - Comprueba DB con cache (SELECT 1 solo cada X segundos).
      - Comprueba RabbitMQ con cache.
      - Comprueba que exista la public key con cache.
    Devuelve 200 si todo OK, 503 si algo falla.
    """
    router = APIRouter(tags=["Health"])

    # --------------- CACHE DE ESTADO DE BD ---------------

    db_status_cache: bool = False
    db_last_check: Optional[datetime] = None
    db_cache_lock = asyncio.Lock()
    db_ttl = timedelta(seconds=config.db_cache_ttl_seconds)

    async def _refresh_db_status(db: AsyncSession) -> None:
        """
        Ejecuta realmente el SELECT 1 y actualiza la cache.
        """
        nonlocal db_status_cache, db_last_check

        try:
            await db.execute(text("SELECT 1"))
            db_status_cache = True
        except Exception as exc:  # pylint: disable=broad-except
            message = f"[{config.service_name}] DB health check failed: {exc}"
            logger.exception(message)
            if config.logger_mq:
                config.logger_mq.publish_log("ERROR", message)
            db_status_cache = False
        finally:
            db_last_check = datetime.utcnow()

    async def _check_db_connection(db: AsyncSession) -> bool:
        """
        Devuelve el estado de la cache de BD.
        Solo refresca si ha pasado mas tiempo que el TTL.
        """
        nonlocal db_status_cache, db_last_check

        now = datetime.utcnow()
        needs_refresh = db_last_check is None or (now - db_last_check) > db_ttl

        if needs_refresh:
            # Evitar que multiples peticiones refresquen a la vez
            async with db_cache_lock:
                # Comprobamos de nuevo dentro del lock por si otra peticion
                # ya ha refrescado mientras esperabamos.
                now = datetime.utcnow()
                if db_last_check is None or (now - db_last_check) > db_ttl:
                    await _refresh_db_status(db)

        return db_status_cache

    # --------------- CACHE DE RABBITMQ ---------------

    rabbit_status_cache: bool = True
    rabbit_last_check: Optional[datetime] = None
    rabbit_cache_lock = asyncio.Lock()
    rabbit_ttl = timedelta(seconds=config.rabbit_cache_ttl_seconds)

    async def _do_rabbitmq_check() -> bool:
        """
        Ejecuta realmente el health check de RabbitMQ.
        """
        # Si no se configuro nada, consideramos que el check no aplica
        if not config.logger_mq and not config.rabbit_check:
            return True

        # Si el servicio pasa un check especifico, lo usamos
        if config.rabbit_check is not None:
            try:
                return await config.rabbit_check()
            except Exception as exc:  # pylint: disable=broad-except
                message = (
                    f"[{config.service_name}] RabbitMQ custom health "
                    f"check failed: {exc}"
                )
                logger.exception(message)
                if config.logger_mq:
                    config.logger_mq.publish_log("ERROR", message)
                return False

        # Fallback: probar a publicar un log
        try:
            assert config.logger_mq is not None  # para el type checker
            config.logger_mq.publish_log(
                "DEBUG",
                f"[{config.service_name}] RabbitMQ health check test message",
            )
            return True
        except Exception as exc:  # pylint: disable=broad-except
            message = f"[{config.service_name}] RabbitMQ health check failed: {exc}"
            logger.exception(message)
            if config.logger_mq:
                config.logger_mq.publish_log("ERROR", message)
            return False

    async def _check_rabbitmq_connection() -> bool:
        """
        Usa una cache que se refresca cada rabbit_cache_ttl_seconds.
        """
        nonlocal rabbit_status_cache, rabbit_last_check

        now = datetime.utcnow()
        needs_refresh = (
            rabbit_last_check is None or (now - rabbit_last_check) > rabbit_ttl
        )

        if needs_refresh:
            async with rabbit_cache_lock:
                # Re comprobar dentro del lock por si otra peticion ya refresco
                now = datetime.utcnow()
                if rabbit_last_check is None or (now - rabbit_last_check) > rabbit_ttl:
                    rabbit_status_cache = await _do_rabbitmq_check()
                    rabbit_last_check = now

        return rabbit_status_cache

    # --------------- CACHE DE PUBLIC KEY ---------------

    public_key_status_cache: bool = True
    public_key_last_check: Optional[datetime] = None
    public_key_ttl = timedelta(seconds=config.public_key_cache_ttl_seconds)

    def _do_public_key_check() -> bool:
        if not config.public_key_path:
            # No aplica a este microservicio
            return True

        try:
            if not os.path.exists(config.public_key_path):
                message = (
                    f"[{config.service_name}] Public key not found at "
                    f"{config.public_key_path}"
                )
                logger.warning(message)
                if config.logger_mq:
                    config.logger_mq.publish_log("WARNING", message)
                return False

            if os.path.getsize(config.public_key_path) == 0:
                message = (
                    f"[{config.service_name}] Public key file is empty at "
                    f"{config.public_key_path}"
                )
                logger.warning(message)
                if config.logger_mq:
                    config.logger_mq.publish_log("WARNING", message)
                return False

            return True
        except Exception as exc:  # pylint: disable=broad-except
            message = f"[{config.service_name}] Public key check failed: {exc}"
            logger.exception(message)
            if config.logger_mq:
                config.logger_mq.publish_log("ERROR", message)
            return False

    def _check_public_key() -> bool:
        """
        Version cacheada de la comprobacion de la clave publica.
        """
        nonlocal public_key_status_cache, public_key_last_check

        # Si no hay ruta configurada, no aplica y devolvemos siempre True
        if not config.public_key_path:
            return True

        now = datetime.utcnow()
        needs_refresh = (
            public_key_last_check is None
            or (now - public_key_last_check) > public_key_ttl
        )

        if needs_refresh:
            public_key_status_cache = _do_public_key_check()
            public_key_last_check = now

        return public_key_status_cache

    # --------------- ENDPOINT /service/health ---------------

    @router.get(
        "/service/health",
        summary="Service health endpoint",
    )
    async def service_health(
        response: Response,
        db: AsyncSession = Depends(config.get_db),  # type: ignore[arg-type]
    ):
        message = f"GET '/service/health' endpoint called in {config.service_name}"
        logger.debug(message)
        if config.logger_mq:
            config.logger_mq.publish_log("DEBUG", message)

        db_ok = await _check_db_connection(db)
        rabbitmq_ok = await _check_rabbitmq_connection()
        public_key_ok = _check_public_key()

        all_ok = db_ok and rabbitmq_ok and public_key_ok

        if not all_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "detail": "OK" if all_ok else "UNAVAILABLE",
            "checks": {
                "database": db_ok,
                "rabbitmq": rabbitmq_ok,
                "public_key": public_key_ok,
            },
        }

    return router
