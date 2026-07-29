#!/usr/bin/env python3
"""Privacy-safe, target-only diagnostics for a private IPv4 speaker address."""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import platform
import re
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
SAFE_PORTS = (80, 443)


@dataclass
class PingResult:
    available: bool
    sent: int
    received: int
    loss_percent: Optional[float]
    minimum_ms: Optional[float]
    average_ms: Optional[float]
    maximum_ms: Optional[float]
    note: str


def private_ipv4(value: str) -> ipaddress.IPv4Address:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Enter a valid IPv4 address.") from exc
    if not isinstance(address, ipaddress.IPv4Address):
        raise argparse.ArgumentTypeError("IPv6 is not supported by this local check.")
    if not any(address in network for network in PRIVATE_NETWORKS):
        raise argparse.ArgumentTypeError(
            "For privacy and safety, enter only a private home-network address "
            "(10.x.x.x, 172.16-31.x.x, or 192.168.x.x)."
        )
    return address


def ping_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Ping count must be a number from 1 to 30.") from exc
    if not 1 <= count <= 30:
        raise argparse.ArgumentTypeError("Ping count must be from 1 to 30.")
    return count


def timeout_milliseconds(value: str) -> int:
    try:
        timeout = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Timeout must be a number from 250 to 5000 milliseconds."
        ) from exc
    if not 250 <= timeout <= 5000:
        raise argparse.ArgumentTypeError(
            "Timeout must be from 250 to 5000 milliseconds."
        )
    return timeout


def ping_command(address: str, count: int, timeout_ms: int) -> list[str]:
    system = platform.system()
    if system == "Windows":
        return ["ping", "-n", str(count), "-w", str(timeout_ms), address]
    if system == "Darwin":
        return ["ping", "-c", str(count), "-W", str(timeout_ms), address]
    return [
        "ping",
        "-c",
        str(count),
        "-W",
        str(max(1, math.ceil(timeout_ms / 1000))),
        address,
    ]


def parse_ping(output: str, requested_count: int) -> PingResult:
    text = output
    sent = requested_count
    received = 0
    loss: Optional[float] = None
    minimum: Optional[float] = None
    average: Optional[float] = None
    maximum: Optional[float] = None

    windows_packets = re.search(
        r"Sent\s*=\s*(\d+).*?Received\s*=\s*(\d+).*?Lost\s*=\s*(\d+).*?\(([\d.]+)%\s*loss\)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    unix_packets = re.search(
        r"(\d+)\s+packets transmitted,\s*(\d+)\s+(?:packets\s+)?received.*?([\d.]+)%\s*packet loss",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if windows_packets:
        sent = int(windows_packets.group(1))
        received = int(windows_packets.group(2))
        loss = float(windows_packets.group(4))
    elif unix_packets:
        sent = int(unix_packets.group(1))
        received = int(unix_packets.group(2))
        loss = float(unix_packets.group(3))
    else:
        replies = len(re.findall(r"(?:Reply from|bytes from|bytes=)", text, re.IGNORECASE))
        received = min(replies, requested_count)
        if requested_count:
            loss = round((requested_count - received) * 100 / requested_count, 1)

    windows_times = re.search(
        r"Minimum\s*=\s*<?([\d.]+)ms.*?Maximum\s*=\s*<?([\d.]+)ms.*?Average\s*=\s*<?([\d.]+)ms",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    unix_times = re.search(
        r"(?:rtt|round-trip).*?=\s*([\d.]+)/([\d.]+)/([\d.]+)/",
        text,
        re.IGNORECASE,
    )
    if windows_times:
        minimum = float(windows_times.group(1))
        maximum = float(windows_times.group(2))
        average = float(windows_times.group(3))
    elif unix_times:
        minimum = float(unix_times.group(1))
        average = float(unix_times.group(2))
        maximum = float(unix_times.group(3))

    return PingResult(
        available=True,
        sent=sent,
        received=received,
        loss_percent=loss,
        minimum_ms=minimum,
        average_ms=average,
        maximum_ms=maximum,
        note="Target-only ping completed.",
    )


def run_ping(address: str, count: int, timeout_ms: int) -> PingResult:
    command = ping_command(address, count, timeout_ms)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(8, count * (timeout_ms / 1000 + 1)),
            check=False,
        )
    except FileNotFoundError:
        return PingResult(False, 0, 0, None, None, None, None, "Ping is not installed.")
    except subprocess.TimeoutExpired:
        return PingResult(
            True, count, 0, 100.0, None, None, None, "Ping timed out."
        )
    return parse_ping((completed.stdout or "") + "\n" + (completed.stderr or ""), count)


def selected_source(address: str) -> Optional[str]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((address, 9))
        return str(sock.getsockname()[0])
    except OSError:
        return None
    finally:
        sock.close()


def safe_tcp_checks(address: str, timeout_seconds: float) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for port in SAFE_PORTS:
        try:
            with socket.create_connection((address, port), timeout=timeout_seconds):
                results[str(port)] = True
        except OSError:
            results[str(port)] = False
    return results


def neighbour_command(address: str) -> list[str]:
    system = platform.system()
    if system == "Windows":
        return ["arp", "-a", address]
    if system == "Linux":
        return ["ip", "neigh", "show", address]
    return ["arp", "-n", address]


def masked_neighbour(address: str) -> Optional[str]:
    try:
        completed = subprocess.run(
            neighbour_command(address),
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    match = re.search(
        r"\b([0-9a-fA-F]{2}(?:[:-][0-9a-fA-F]{2}){5})\b",
        (completed.stdout or "") + "\n" + (completed.stderr or ""),
    )
    if not match:
        return None
    parts = re.split(r"[:-]", match.group(1).upper())
    return ":".join(parts[:3] + ["XX", "XX", parts[5]])


def classify(ping: PingResult, ports: dict[str, bool], source: Optional[str]) -> str:
    if source:
        try:
            if not any(ipaddress.ip_address(source) in network for network in PRIVATE_NETWORKS):
                return "route_warning"
        except ValueError:
            return "route_warning"
    any_tcp = any(ports.values())
    if ping.received == 0:
        return "icmp_blocked" if any_tcp else "unreachable"
    if (
        (ping.loss_percent is not None and ping.loss_percent > 0)
        or (ping.average_ms is not None and ping.average_ms > 50)
        or (ping.maximum_ms is not None and ping.maximum_ms > 100)
    ):
        return "degraded"
    return "healthy"


def advice_for(status: str) -> str:
    return {
        "healthy": (
            "The local IP connection looks stable in this sample. Confirm a DHCP "
            "reservation and review router Wi-Fi history if the fault is intermittent."
        ),
        "degraded": (
            "Check signal, retries, channel congestion, and the connected access point. "
            "Aim for 0% loss, signal of -67 dBm or better, and retries below 10%."
        ),
        "icmp_blocked": (
            "The speaker may be online even though ping is blocked. Confirm it in the "
            "router client list and check that the app and speaker use the same LAN."
        ),
        "unreachable": (
            "Check speaker power, the IP shown in the Lithe Audio app, the router client "
            "list, guest isolation, and whether DHCP assigned a different address."
        ),
        "route_warning": (
            "The computer selected an unexpected route. Disconnect VPN software, join "
            "the same home Wi-Fi as the speaker, and run the check again."
        ),
    }[status]


def run_self_test() -> int:
    windows = """
Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Minimum = 2ms, Maximum = 9ms, Average = 4ms
"""
    unix = """
4 packets transmitted, 3 received, 25% packet loss, time 3004ms
rtt min/avg/max/mdev = 2.100/4.200/8.300/1.000 ms
"""
    first = parse_ping(windows, 4)
    second = parse_ping(unix, 4)
    checks = [
        first.received == 4,
        first.loss_percent == 0,
        first.average_ms == 4,
        second.received == 3,
        second.loss_percent == 25,
        second.maximum_ms == 8.3,
        str(private_ipv4("192.168.1.45")) == "192.168.1.45",
    ]
    try:
        private_ipv4("8.8.8.8")
        checks.append(False)
    except argparse.ArgumentTypeError:
        checks.append(True)
    if all(checks):
        print("Self-test passed.")
        return 0
    print("Self-test failed.", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run privacy-safe checks against one private Lithe speaker IP. "
            "No API calls, authentication, LAN scan, or internet upload is performed."
        )
    )
    parser.add_argument("ip", nargs="?", type=private_ipv4, help="Private speaker IPv4")
    parser.add_argument("--count", type=ping_count, default=10)
    parser.add_argument("--timeout", type=timeout_milliseconds, default=1000)
    parser.add_argument("--json", action="store_true", help="Print structured JSON")
    parser.add_argument(
        "--save-json",
        metavar="PATH",
        help="Save a new local redacted diagnostic JSON file",
    )
    parser.add_argument("--self-test", action="store_true", help="Run offline parser tests")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if args.ip is None:
        parser.error("Enter the private IP shown in the Lithe Audio app.")

    address = str(args.ip)
    source = selected_source(address)
    ping = run_ping(address, args.count, args.timeout)
    ports = safe_tcp_checks(address, min(1.5, args.timeout / 1000))
    mac = masked_neighbour(address)
    status = classify(ping, ports, source)
    result = {
        "target_ip": address,
        "selected_local_source": source,
        "masked_mac": mac,
        "status": status,
        "ping": asdict(ping),
        "safe_tcp_connect": ports,
        "recommended_next_step": advice_for(status),
        "privacy": (
            "Target-only local checks; no API, credentials, HTTP request, subnet scan, "
            "or internet upload."
        ),
    }
    payload = json.dumps(result, indent=2)

    if args.save_json:
        report_path = Path(args.save_json).expanduser()
        if report_path.exists():
            print(
                f"Refusing to overwrite existing report: {report_path}",
                file=sys.stderr,
            )
            return 3
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(payload + "\n", encoding="utf-8")
        print(f"Saved local diagnostic: {report_path}")

    if args.json:
        print(payload)
        return 0

    labels = {
        "healthy": "Healthy",
        "degraded": "Degraded",
        "icmp_blocked": "ICMP blocked",
        "unreachable": "Unreachable",
        "route_warning": "Route warning",
    }
    print(f"Result: {labels[status]}")
    print(f"Speaker IP: {address}")
    print(f"Local source: {source or 'Unavailable'}")
    print(f"Masked MAC: {mac or 'Not available'}")
    if ping.available:
        print(
            f"Ping: {ping.received}/{ping.sent} replies, "
            f"{ping.loss_percent if ping.loss_percent is not None else 'unknown'}% loss"
        )
        if ping.average_ms is not None:
            print(
                "Latency: "
                f"min {ping.minimum_ms:g} ms / avg {ping.average_ms:g} ms / "
                f"max {ping.maximum_ms:g} ms"
            )
    else:
        print(f"Ping: unavailable ({ping.note})")
    open_ports = [port for port, open_ in ports.items() if open_]
    print(f"Safe TCP response: {', '.join(open_ports) if open_ports else 'none'}")
    print(f"Next step: {advice_for(status)}")
    print("Privacy: no API, credentials, HTTP request, LAN scan, or internet upload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
