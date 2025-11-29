# Chassis

A lightweight Python package that centralizes JWT helpers, RabbitMQ logging
utilities, Consul helpers, and a shared health-check router for our services.

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/MACC-ASA-Monolithic2Services/Chassis.git
```

## Module overview and environment variables

### `microservice_chassis/__init__.py`
Aggregates the public API so consumers can import helpers from a single place.
Environment variables: _None_. This module simply re-exports the rest.

### `microservice_chassis/config.py`
Wraps `pydantic-settings` so configuration can be pulled from the environment or
an optional `.env` file.

- `PRIVATE_KEY_PATH`: absolute or relative path to the RSA private key used to
  sign service-to-service JWTs when needed.
- `PUBLIC_KEY_PATH`: path to the RSA public key used to verify inbound JWTs.

### `microservice_chassis/dependencies.py`
Provides the FastAPI `verify_jwt_token` dependency. It loads the RSA public key
via `settings`.

- `PUBLIC_KEY_PATH`: same variable as above; the dependency reads the public key
  on every request to validate tokens.

### `microservice_chassis/health.py`
Creates a FastAPI router that checks the database, RabbitMQ, and the presence of
the JWT public key. All parameters are passed through the `HealthConfig`
dataclass, so there are no hard-coded environment variables.

Environment variables: _None_. Provide the desired values when instantiating
`HealthConfig`.

### `microservice_chassis/rabbitmq_logger.py`
Implements `RabbitMQLogPublisher`, a small async publisher that emits logs to an
exchange. You typically pass connection details (URL, certificates, exchange
name, etc.) from your own configuration layer.

Environment variables: _None_. Feed connection data from your service settings.

### `microservice_chassis/consul_utils.py`
Utility functions to register/deregister services in Consul, perform DNS lookups,
and read Consul KV values.

- `CONSUL_HOST` (default `172.28.0.10`)
- `CONSUL_PORT` (default `8500`)
- `CONSUL_DNS_PORT` (default `8600`)
- `PORT` (default `8000`): local FastAPI app port exposed to Consul.
- `SERVICE_NAME` (default `service`): logical name advertised to Consul.
- `SERVICE_ID` (optional): if omitted, the module auto-generates one.
