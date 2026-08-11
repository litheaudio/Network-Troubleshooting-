#!/usr/bin/env python3
"""Run a consent-gated, target-only intermittent connectivity monitor."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import check_speaker_network as network


def duration_minutes(value: str) -> int:
    try:
        minutes = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Duration must be 1 to 10080 minutes.") from exc
    if not 1 <= minutes <= 10080:
        raise argparse.ArgumentTypeError("Duration must be 1 to 10080 minutes.")
    return minutes


def interval_seconds(value: str) -> int:
    try:
        seconds = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Interval must be 5 to 3600 seconds.") from exc
    if not 5 <= seconds <= 3600:
        raise argparse.ArgumentTypeError("Interval must be 5 to 3600 seconds.")
    return seconds


def sample(address: str, timeout_ms: int) -> dict:
    ping = network.run_ping(address, 1, timeout_ms)
    ports = network.safe_tcp_checks(address, min(1.5, timeout_ms / 1000))
    status = network.classify(ping, ports, network.selected_source(address))
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "ping_available": ping.available,
        "reply": ping.received > 0,
        "latency_ms": ping.average_ms,
        "tcp_80": ports.get("80", False),
        "tcp_443": ports.get("443", False),
    }


def summarise(samples: list[dict]) -> dict:
    outages = [item for item in samples if item["status"] == "unreachable"]
    degraded = [item for item in samples if item["status"] == "degraded"]
    unknown = [item for item in samples if item["status"] == "probe_unavailable"]
    conclusive = len(samples) - len(unknown)
    transitions = []
    previous = None
    for item in samples:
        if item["status"] != previous:
            transitions.append(
                {"timestamp": item["timestamp"], "status": item["status"]}
            )
            previous = item["status"]
    latencies = [item["latency_ms"] for item in samples if item["latency_ms"] is not None]
    return {
        "samples": len(samples),
        "unreachable_samples": len(outages),
        "degraded_samples": len(degraded),
        "inconclusive_samples": len(unknown),
        "availability_percent": (
            round((conclusive - len(outages)) * 100 / conclusive, 3)
            if conclusive
            else None
        ),
        "maximum_latency_ms": max(latencies) if latencies else None,
        "transitions": transitions[:50],
        "transition_list_truncated": len(transitions) > 50,
    }


def run_self_test() -> int:
    samples = [
        {"timestamp": "2026-08-11T10:00:00+01:00", "status": "healthy", "latency_ms": 2},
        {"timestamp": "2026-08-11T10:01:00+01:00", "status": "unreachable", "latency_ms": None},
        {"timestamp": "2026-08-11T10:02:00+01:00", "status": "healthy", "latency_ms": 4},
    ]
    result = summarise(samples)
    checks = (
        result["samples"] == 3,
        result["unreachable_samples"] == 1,
        result["maximum_latency_ms"] == 4,
        len(result["transitions"]) == 3,
    )
    if all(checks):
        print("Self-test passed.")
        return 0
    print("Self-test failed.", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Monitor one customer-supplied private speaker IP for intermittent loss. "
            "Writes only timestamped target status and measurements; no scan or upload."
        )
    )
    parser.add_argument("ip", nargs="?", type=network.private_ipv4)
    parser.add_argument("--duration-minutes", type=duration_minutes, default=15)
    parser.add_argument("--interval-seconds", type=interval_seconds, default=30)
    parser.add_argument("--timeout", type=network.timeout_milliseconds, default=1000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if args.ip is None:
        parser.error("Provide the customer-supplied private speaker IP.")
    if args.output is None:
        parser.error("Provide --output after the customer agrees to save monitor data.")
    output = args.output.expanduser().resolve()
    if output.exists():
        print(f"Refusing to overwrite existing monitor: {output.name}", file=sys.stderr)
        return 3
    output.parent.mkdir(parents=True, exist_ok=True)

    address = str(args.ip)
    deadline = time.monotonic() + args.duration_minutes * 60
    samples: list[dict] = []
    try:
        with output.open("x", encoding="utf-8") as handle:
            while True:
                item = sample(address, args.timeout)
                samples.append(item)
                handle.write(json.dumps(item, separators=(",", ":")) + "\n")
                handle.flush()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(args.interval_seconds, remaining))
    except KeyboardInterrupt:
        pass

    result = {
        "target_ip": address,
        "output": output.name,
        "summary": summarise(samples),
        "privacy": "Target-only local measurements; no raw traffic, credentials, scan or upload.",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
