import consul
import dns.resolver
import dns
import logging
from os import environ
import uuid
import socket


def get_ip():
    # Gets the primary IP of the host (similar to hostname -i)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable; just forces selection of the default interface
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def get_advertise_ip():
    """
    IP address to register in Consul.
    - If ADVERTISE_IP is set, use it (best practice for service discovery).
    - Otherwise, fall back to container IP.
    """
    ip = environ.get("ADVERTISE_IP")
    if ip and ip.strip():
        return ip.strip()
    return get_ip()


CONSUL_HOST = environ.get("CONSUL_HOST", "172.28.0.10")
CONSUL_PORT = environ.get("CONSUL_PORT", 8500)
CONSUL_DNS_PORT = environ.get("CONSUL_DNS_PORT", 8600)
PORT = int(environ.get("PORT", '8000'))
SERVICE_NAME = environ.get("SERVICE_NAME", "service")
# SERVICE_ID = environ.get("SERVICE_ID", "s1r0")
# GENERATE UUID FOR SERVICE_ID
SERVICE_ID = SERVICE_NAME + "_" + str(uuid.uuid4())
IP = get_advertise_ip()

logger = logging.getLogger(__name__)

# Consul instance
consul_instance = consul.Consul(
    host=CONSUL_HOST,
    port=CONSUL_PORT
)

# DNS resolver
consul_resolver = dns.resolver.Resolver(configure=False)
consul_resolver.port = CONSUL_DNS_PORT
consul_resolver.nameservers = [CONSUL_HOST]

# Store a variable as an example
consul_instance.kv.put("aas_example_variable", "aas_example_value")


def register_consul_service(
        cons=consul_instance,
        ip=IP,
        port=PORT,
        service_name=SERVICE_NAME,
        service_id=SERVICE_ID
):
    """Register service in consul"""
    logger.debug(
        f"Registering {service_name} service ({service_id}, {ip}:{port})")
    cons.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=ip,
        port=port,
        tags=["python", "microservice", "aas"],
        check={
            "http": 'http://{ip}:{port}/service/health'.format(
                ip=ip,
                port=port
            ),
            "interval": '5s'  # @ToDo: Change to larger number on production
        }
    )
    logger.info(f"Registered {service_name} service ({service_id})")


def deregister_consul_service(cons=consul_instance, service_id: str = SERVICE_ID):
    """Unregister a service in Consul."""
    if cons is None:
        logger.error("Consul instance is not set. Cannot unregister service")
        return
    response = cons.agent.service.deregister(service_id)
    logger.info(f"Unregistered service {service_id} -> {response}")


def get_consul_service(service_name, consul_dns_resolver=consul_resolver):
    """Get service from consul"""
    ret = {
        "Address": None,
        "Port": None
    }
    try:
        #  srv_results = consul_dns_resolver.query("{}.service.consul".format(service_name), "srv")

        srv_results = consul_dns_resolver.resolve(
            "{}.service.consul".format(service_name),
            "srv"
        )  # SRV DNS query
        srv_list = srv_results.response.answer  # PORT - target_name relation
        a_list = srv_results.response.additional  # IP - target_name relation

        # DNS returns a list of replicas, supposedly sorted using Round Robin. We always get the 1st element: [0]
        srv_replica = srv_list[0][0]
        port = srv_replica.port
        target_name = srv_replica.target

        # From all the IPs, get the one with the chosen target_name
        for a in a_list:
            if a.name == target_name:
                ret['Address'] = a[0]
                ret['Port'] = port
                break

    except dns.exception.DNSException as e:
        logger.error("Could not get service url: {}".format(e))
    return ret


def get_consul_key_value_item(key, cons=consul_instance):
    """Get consul item value for the given key. It only works for string items!"""
    index, data = cons.kv.get(key)
    value = None
    if data and data['Value']:
        value = data['Value'].decode('utf-8')
    return key, value


def get_consul_service_catalog(cons=consul_instance):
    """List al consul services"""
    return cons.catalog.services()


def get_consul_service_replicas(cons=consul_instance):
    """Get all services including replicas"""
    return cons.agent.services()
