"""Outbound host and address policy for user-supplied provider endpoints.

This module owns every rule that decides whether a provider hostname or the
addresses it resolves to may be contacted. Keeping it free of persistence,
secret handling and provider construction lets both connection probing and
job-time provider building depend on the same guard without an import cycle.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlsplit

from edcraft_backend.services.provider_errors import ProviderConnectionInvalid

BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

PRIVATE_HOST_BLOCKED = (
    "This provider address is not allowed. Use a public host, or set "
    "PROVIDER_ALLOW_PRIVATE_HOSTS=true only for local development."
)
HOST_NOT_ALLOWED = "This provider host is not allowed."
ADDRESS_NOT_ALLOWED = "This provider address is not allowed."

Address = ipaddress.IPv4Address | ipaddress.IPv6Address


def normalize_host(hostname: str) -> str:
    """Compare hostnames case-insensitively and without a trailing dot."""
    return hostname.removesuffix(".").lower()


def parse_ip(hostname: str) -> Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


def allow_private_provider_hosts() -> bool:
    """Development-only escape hatch; disabled unless explicitly enabled."""
    value = os.getenv("PROVIDER_ALLOW_PRIVATE_HOSTS", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def is_loopback(hostname: str) -> bool:
    host = normalize_host(hostname)
    if host == "localhost":
        return True
    address = parse_ip(host)
    return address is not None and address.is_loopback


def reject_unsafe_host(hostname: str) -> None:
    """Reject literal hostnames that must never be contacted."""
    host = normalize_host(hostname)
    if host in BLOCKED_HOSTNAMES:
        raise ProviderConnectionInvalid(HOST_NOT_ALLOWED)
    if host == "localhost" or host.endswith(".localhost"):
        if not allow_private_provider_hosts():
            raise ProviderConnectionInvalid(PRIVATE_HOST_BLOCKED)
        return
    address = parse_ip(host)
    if address is None:
        return
    reject_unsafe_address(address)


def reject_unsafe_address(address: Address) -> None:
    """Reject literal or resolved addresses outside the allowed policy."""
    # These ranges are never valid provider destinations, even in development.
    if address.is_link_local or address.is_multicast or address.is_unspecified:
        raise ProviderConnectionInvalid(ADDRESS_NOT_ALLOWED)
    if getattr(address, "is_shared", False):
        raise ProviderConnectionInvalid(ADDRESS_NOT_ALLOWED)
    if allow_private_provider_hosts():
        if address.is_loopback or (address.is_private and not address.is_reserved):
            return
        raise ProviderConnectionInvalid(ADDRESS_NOT_ALLOWED)
    if address.is_global:
        return
    raise ProviderConnectionInvalid(PRIVATE_HOST_BLOCKED)


def assert_public_provider_host(base_url: str) -> None:
    """Reject a hostname that resolves to a non-public address.

    Resolution failures are left to the HTTP request so they surface as the
    existing sanitized 502 instead of a validation error.
    """
    try:
        parts = urlsplit(base_url)
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ProviderConnectionInvalid("Base URL has an invalid host or port.") from exc
    if not hostname:
        raise ProviderConnectionInvalid("Base URL must include a host.")
    host = normalize_host(hostname)
    reject_unsafe_host(host)
    resolved_port = port or (443 if parts.scheme == "https" else 80)
    try:
        results = socket.getaddrinfo(host, resolved_port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError):
        return
    for _family, _type, _proto, _canonname, sockaddr in results:
        address = parse_ip(str(sockaddr[0]))
        if address is not None:
            reject_unsafe_address(address)


__all__ = [
    "BLOCKED_HOSTNAMES",
    "ProviderConnectionInvalid",
    "allow_private_provider_hosts",
    "assert_public_provider_host",
    "is_loopback",
    "normalize_host",
    "parse_ip",
    "reject_unsafe_address",
    "reject_unsafe_host",
]
