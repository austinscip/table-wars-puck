"""Slice J — mDNS advertisement so pucks can find the server by name
instead of a hardcoded IP. After this lands, bar deployment doesn't need
a firmware rebuild per venue — the puck looks up `tablewars-server.local`
on the local network and the bar's router resolves it via mDNS.

Two services advertised:
  _http._tcp     — for browser / curl / general HTTP clients
  _tablewars._tcp — application-specific so pucks can filter

Both point at the same host:port. The DNS-SD service name lets pucks
distinguish a Table Wars server from anything else broadcasting on
:5001 / :5002.

Failure mode: zeroconf is optional. If the platform doesn't support
multicast or the network blocks UDP 5353, advertisement fails silently
and Flask still serves over its bound IP. Pucks must then fall back to
a configured IP (the existing path) or a QR code scan.

Usage:
    from mdns_advertise import advertise_mdns
    advertise_mdns(port=5001, instance="prod")    # or "sandbox" / venue slug
"""
from __future__ import annotations

import atexit
import socket
import sys
from typing import Optional


_zc = None  # one-shot Zeroconf instance


def _lan_ip() -> str:
    """Best-effort local LAN IP. zeroconf needs the IP to bind/register.
    Using 0.0.0.0 wouldn't be addressable by clients. We open a UDP
    socket to a public IP and read .getsockname()[0] — no packets are
    actually sent (UDP connect is local-only)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:  # noqa: BLE001
        return "127.0.0.1"
    finally:
        s.close()


def advertise_mdns(*, port: int, instance: str = "tablewars-server",
                   service_name: str = "_tablewars._tcp.local.",
                   ttl: int = 60) -> Optional[str]:
    """Start advertising the server on the LAN.

    Returns the advertised hostname ("tablewars-server.local" or
    "<instance>.local") on success, or None on failure.

    Idempotent: calling twice replaces the previous registration so
    Flask's reloader (debug=True forks the process and re-runs this)
    doesn't accumulate stale services.
    """
    global _zc
    try:
        from zeroconf import IPVersion, ServiceInfo, Zeroconf
    except ImportError:
        print("[mdns_advertise] zeroconf not installed — skipping",
              file=sys.stderr)
        return None

    hostname = f"{instance}.local"
    ip = _lan_ip()

    info = ServiceInfo(
        service_name,
        f"{instance}.{service_name}",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={
            "version": "1",
            "instance": instance,
            # Lets a puck verify it's hitting a Table Wars server.
            "app": "tablewars",
        },
        server=hostname + ".",
    )

    try:
        if _zc is None:
            _zc = Zeroconf(ip_version=IPVersion.V4Only)
            atexit.register(_shutdown)
        else:
            try:
                _zc.unregister_all_services()
            except Exception:  # noqa: BLE001
                pass
        _zc.register_service(info, ttl=ttl)
    except Exception as e:  # noqa: BLE001
        print(f"[mdns_advertise] register failed: {e}", file=sys.stderr)
        return None
    print(f"[mdns_advertise] {hostname} -> {ip}:{port} "
          f"({service_name})", flush=True)
    return hostname


def _shutdown() -> None:
    global _zc
    if _zc is not None:
        try:
            _zc.unregister_all_services()
            _zc.close()
        except Exception:  # noqa: BLE001
            pass
        _zc = None
