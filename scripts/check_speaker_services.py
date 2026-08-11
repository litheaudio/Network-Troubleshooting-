#!/usr/bin/env python3
"""Target-only checks of documented public speaker services and the root page."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import time
from dataclasses import asdict, dataclass
from typing import Optional


PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)

# Fixed public service list from Lithe Audio's router-configuration guidance.
SERVICE_PORTS = {
    80: "web_http",
    443: "secure_control",
    8008: "cast_http",
    8443: "cast_secure",
    9095: "spotify_connect",
    9096: "spotify_connect",
    9097: "spotify_connect",
    9098: "spotify_connect",
    9099: "spotify_connect",
    8000: "qobuz_connect",
    9090: "tidal_connect",
    49494: "upnp_dmr",
    3689: "airplay_daap",
}
MAX_RESPONSE_BYTES = 64 * 1024


@dataclass
class TcpResult:
    port: int
    service: str
    listening: bool
    connect_ms: Optional[float]


def private_ipv4(value: str) -> str:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Enter a valid IPv4 address.") from exc
    if not isinstance(address, ipaddress.IPv4Address):
        raise argparse.ArgumentTypeError("IPv6 is not supported.")
    if not any(address in network for network in PRIVATE_NETWORKS):
        raise argparse.ArgumentTypeError("Enter only a private home-network IPv4 address.")
    return str(address)


def tcp_probe(address: str, port: int, timeout: float) -> TcpResult:
    started = time.monotonic()
    try:
        with socket.create_connection((address, port), timeout=timeout):
            elapsed = round((time.monotonic() - started) * 1000, 1)
            return TcpResult(port, SERVICE_PORTS[port], True, elapsed)
    except OSError:
        return TcpResult(port, SERVICE_PORTS[port], False, None)


def classify_web(
    connected: bool,
    received_bytes: int,
    headers_complete: bool,
    response_complete: bool,
    timed_out: bool,
) -> str:
    if not connected:
        return "no_listener"
    if received_bytes == 0:
        return "listener_no_http_response"
    if not headers_complete:
        return "incomplete_headers"
    if timed_out and not response_complete:
        return "partial_or_stalled"
    return "responsive"


def root_http_probe(address: str, connect_timeout: float, response_timeout: float) -> dict:
    connected = False
    first_byte_ms: Optional[float] = None
    status_code: Optional[int] = None
    received = bytearray()
    timed_out = False
    closed = False
    started = time.monotonic()

    try:
        with socket.create_connection((address, 80), timeout=connect_timeout) as sock:
            connected = True
            sock.settimeout(response_timeout)
            request = (
                f"GET / HTTP/1.0\r\nHost: {address}\r\n"
                "User-Agent: Lithe-Network-Diagnostic\r\n"
                "Accept: text/html\r\nConnection: close\r\n\r\n"
            ).encode("ascii")
            sock.sendall(request)
            while len(received) < MAX_RESPONSE_BYTES:
                try:
                    chunk = sock.recv(min(4096, MAX_RESPONSE_BYTES - len(received)))
                except socket.timeout:
                    timed_out = True
                    break
                if not chunk:
                    closed = True
                    break
                if first_byte_ms is None:
                    first_byte_ms = round((time.monotonic() - started) * 1000, 1)
                received.extend(chunk)
    except OSError:
        pass

    header_end = received.find(b"\r\n\r\n")
    headers_complete = header_end >= 0
    content_length: Optional[int] = None
    body_bytes = 0
    if headers_complete:
        header_blob = bytes(received[:header_end]).decode("iso-8859-1", errors="replace")
        status_match = re.match(r"HTTP/\d(?:\.\d)?\s+(\d{3})", header_blob)
        if status_match:
            status_code = int(status_match.group(1))
        length_match = re.search(r"(?im)^Content-Length:\s*(\d+)\s*$", header_blob)
        if length_match:
            content_length = int(length_match.group(1))
        body_bytes = len(received) - header_end - 4

    response_complete = bool(
        headers_complete
        and (
            closed
            or (content_length is not None and body_bytes >= content_length)
            or len(received) >= MAX_RESPONSE_BYTES
        )
    )
    status = classify_web(
        connected, len(received), headers_complete, response_complete, timed_out
    )
    return {
        "status": status,
        "tcp_connected": connected,
        "first_byte_ms": first_byte_ms,
        "http_status_code": status_code,
        "headers_complete": headers_complete,
        "response_complete": response_complete,
        "timed_out": timed_out,
        "bytes_observed": len(received),
        "note": "Read-only GET of the standard root page; response content is not emitted or saved.",
    }


def run_self_test() -> int:
    checks = [
        private_ipv4("192.168.1.45") == "192.168.1.45",
        classify_web(False, 0, False, False, False) == "no_listener",
        classify_web(True, 0, False, False, True) == "listener_no_http_response",
        classify_web(True, 20, False, False, True) == "incomplete_headers",
        classify_web(True, 200, True, False, True) == "partial_or_stalled",
        classify_web(True, 200, True, True, False) == "responsive",
    ]
    try:
        private_ipv4("8.8.8.8")
        checks.append(False)
    except argparse.ArgumentTypeError:
        checks.append(True)
    if all(checks):
        print("Self-test passed.")
        return 0
    print("Self-test failed.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check one private speaker's documented public TCP services and root page. "
            "No authentication, hidden endpoint, API command, subnet scan or upload."
        )
    )
    parser.add_argument("ip", nargs="?", type=private_ipv4)
    parser.add_argument("--connect-timeout", type=float, default=0.6)
    parser.add_argument("--web-timeout", type=float, default=5.0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        return run_self_test()
    if args.ip is None:
        raise SystemExit("Enter the private IP shown in the Lithe Audio app.")
    if not 0.25 <= args.connect_timeout <= 2.0:
        raise SystemExit("Connect timeout must be from 0.25 to 2 seconds.")
    if not 1.0 <= args.web_timeout <= 10.0:
        raise SystemExit("Web timeout must be from 1 to 10 seconds.")

    tcp_results = [
        tcp_probe(args.ip, port, args.connect_timeout) for port in SERVICE_PORTS
    ]
    web = root_http_probe(args.ip, args.connect_timeout, args.web_timeout)
    listening_groups = sorted({item.service for item in tcp_results if item.listening})
    result = {
        "target_ip": args.ip,
        "documented_tcp_services": [asdict(item) for item in tcp_results],
        "listening_service_groups": listening_groups,
        "root_web_health": web,
        "interpretation_limits": (
            "A TCP listener supports service-health correlation but does not prove that "
            "the service is fully working. A closed TCP port does not disprove discovery "
            "through multicast, UDP, Bluetooth or a cloud account."
        ),
        "privacy": (
            "One supplied private target only; fixed public service list; one read-only "
            "root-page request; no credentials, hidden endpoints, API commands or upload."
        ),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Root web health: {web['status']}")
        print(
            "Listening service groups: "
            + (", ".join(listening_groups) if listening_groups else "none")
        )
        print(result["interpretation_limits"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
