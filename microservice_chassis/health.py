# microservice_chassis/health.py
import logging
import os
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Protocol

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .rabbitmq_logger import RabbitMQLogPublisher  # ya existe en el Chassis

logger = logging.getLogger(__name__)


class DBDependency(Protocol):
    """Protocolo para el dependency get_db de FastAPI."""

    async def __call__(self) -> AsyncSession:  # pragma: no cover - solo typing
        ...


RabbitCheck = Callable[[], Awaitable[bool]]


@dataclass
class HealthConfig:
    """
    Config común para generar el endpoint /service/health en cualquier microservicio.
    - service_name: nombre del servicio (para logs).
    - get_db: dependency de FastAPI que devuelve AsyncSession (get_db).
    - logger_mq: publisher de RabbitMQ para logs (opcional).
    - rabbit_check: función async que comprueba la conexión RabbitMQ (opcional).
    - public_key_path: ruta a la clave pública a comprobar (opcional).
    """

    service_name: str
    get_db: DBDependency
    logger_mq: Optional[RabbitMQLogPublisher] = None
    rabbit_check: Optional[RabbitCheck] = None
    public_key_path: Optional[str] = None


def create_health_router(config: HealthConfig) -> APIRouter:
    """
    Crea un router FastAPI con el endpoint /service/health que:
      - Comprueba DB (SELECT 1).
      - Comprueba RabbitMQ (rabbit_check o publish_log).
      - Comprueba que exista la public key (si se indica ruta).
    Devuelve 200 si todo OK, 503 si algo falla.
    """
    router = APIRouter(tags=["Health"])

    async def _check_db_connection(db: AsyncSession) -> bool:
        try:
            await db.execute(text("SELECT 1"))
            return True
        except Exception as exc:  # pylint: disable=broad-except
            message = f"[{config.service_name}] DB health check failed: {exc}"
            logger.exception(message)
            if config.logger_mq:
                config.logger_mq.publish_log("ERROR", message)
            return False

    async def _check_rabbitmq_connection() -> bool:
        # Si no se configuró nada, consideramos que el check no aplica
        if not config.logger_mq and not config.rabbit_check:
            return True

        # Si el servicio pasa un check específico, lo usamos
        if config.rabbit_check is not None:
            try:
                return await config.rabbit_check()
            except Exception as exc:  # pylint: disable=broad-except
                message = f"[{config.service_name}] RabbitMQ custom health check failed: {exc}"
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
            config.logger_mq.publish_log("ERROR", message)
            return False

    def _check_public_key() -> bool:
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
