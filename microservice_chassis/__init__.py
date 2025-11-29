"""Public exports for the microservice_chassis package."""

from .config import Settings, settings
from .consul_utils import (
    deregister_consul_service,
    get_consul_key_value_item,
    get_consul_service,
    get_consul_service_catalog,
    get_consul_service_replicas,
    register_consul_service,
)
from .dependencies import verify_jwt_token
from .health import HealthConfig, create_health_router
from .rabbitmq_logger import RabbitMQLogPublisher

__all__ = [
    "Settings",
    "settings",
    "verify_jwt_token",
    "RabbitMQLogPublisher",
    "HealthConfig",
    "create_health_router",
    "register_consul_service",
    "deregister_consul_service",
    "get_consul_service",
    "get_consul_key_value_item",
    "get_consul_service_catalog",
    "get_consul_service_replicas",
]
