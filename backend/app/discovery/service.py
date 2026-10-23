from .ping import ping_device
from .scanner import scan_network


def check_device(ip: str):
    return ping_device(ip)


def discover_network(network: str):
    return scan_network(network)