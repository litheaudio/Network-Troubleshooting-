#!/usr/bin/env python3
"""Create a redacted local Markdown support report from diagnostic evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any


ALLOWED_FIELDS = {
    "symptom": "Reported symptom",
    "frequency": "Frequency",
    "first_seen": "First noticed",
    "router_model": "Router or mesh model",
    "network_type": "Network type",
    "access_point": "Connected access point",
    "band": "Wi-Fi band",
    "signal_dbm": "Signal (dBm)",
    "retries_percent": "Retries (%)",
    "dhcp_reserved": "DHCP reservation",
    "distance_m": "Approximate distance (m)",
    "walls": "Walls between speaker and AP",
    "floors": "Floors between speaker and AP",
    "barriers": "Other barriers",
    "speaker_location": "Speaker location",
    "other_devices": "Other affected devices",
    "changes": "Changes tried",
    "verification": "Verification outcome",
    "customer_notes": "Customer notes",
}
SECRET_RE = re.compile(
    r"(?i)\b(password|passcode|passwd|token|api[ _-]?key|secret|"
    r"mfa|recovery[ _-]?code|username|email)\b\s*[:=]\s*([^\s,;]+)"
)
MAC_RE = re.compile(r"\b([0-9a-fA-F]{2})(?:[:-]([0-9a-fA-F]{2})){5}\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def mask_mac(match: re.Match[str]) -> str:
    parts = re.split(r"[:-]", match.group(0).upper())
    return ":".join(parts[:3] + ["XX", "XX", parts[5]])


def redact_public_ip(match: re.Match[str]) -> str:
    value = match.group(0)
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return "[REDACTED INVALID IP]"
    if address.is_private:
        return value
    return "[REDACTED PUBLIC IP]"


def sanitise(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = MAC_RE.sub(mask_mac, text)
    text = IPV4_RE.sub(redact_public_ip, text)
    return text[:500] or "Not provided"


def parse_fields(items: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Field must use name=value: {item}")
        name, value = item.split("=", 1)
        name = name.strip()
        if name not in ALLOWED_FIELDS:
            raise ValueError(
                f"Unknown field '{name}'. Allowed: {', '.join(sorted(ALLOWED_FIELDS))}"
            )
        fields[name] = sanitise(value)
    return fields


def load_diagnostic(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = {
        "target_ip",
        "selected_local_source",
        "masked_mac",
        "status",
        "ping",
        "safe_tcp_connect",
        "recommended_next_step",
        "privacy",
    }
    return {key: data[key] for key in allowed if key in data}


def line(label: str, value: Any) -> str:
    return f"- **{label}:** {sanitise(value)}"


def build_report(diagnostic: dict[str, Any], fields: dict[str, str]) -> str:
    now = dt.datetime.now().astimezone()
    report_id = str(uuid.uuid4())[:8].upper()
    ping = diagnostic.get("ping") if isinstance(diagnostic.get("ping"), dict) else {}
    ports = (
        diagnostic.get("safe_tcp_connect")
        if isinstance(diagnostic.get("safe_tcp_connect"), dict)
        else {}
    )
    tcp_response = ", ".join(str(k) for k, value in ports.items() if value) or "None"

    sections = [
        "# Lithe Audio Network Support Report",
        "",
        line("Report ID", report_id),
        line("Created locally", now.isoformat(timespec="seconds")),
        line("Data handling", "Redacted local report; not uploaded by this tool"),
        "",
        "## Customer-reported issue",
        "",
    ]
    issue_order = ["symptom", "frequency", "first_seen", "other_devices", "customer_notes"]
    for key in issue_order:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend(["", "## Home and Wi-Fi environment", ""])
    environment_order = [
        "router_model",
        "network_type",
        "distance_m",
        "walls",
        "floors",
        "barriers",
        "speaker_location",
    ]
    for key in environment_order:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend(
        [
            "",
            "## Local diagnostic",
            "",
            line("Speaker private IP", diagnostic.get("target_ip", "Not captured")),
            line("Masked MAC", diagnostic.get("masked_mac", "Not captured")),
            line("Status", diagnostic.get("status", "Not captured")),
            line("Replies", f"{ping.get('received', '?')}/{ping.get('sent', '?')}"),
            line("Packet loss", f"{ping.get('loss_percent', '?')}%"),
            line("Average latency", f"{ping.get('average_ms', '?')} ms"),
            line("Maximum latency", f"{ping.get('maximum_ms', '?')} ms"),
            line("Safe TCP response", tcp_response),
            "",
            "## Router observations",
            "",
        ]
    )
    router_order = [
        "access_point",
        "band",
        "signal_dbm",
        "retries_percent",
        "dhcp_reserved",
    ]
    for key in router_order:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend(["", "## Actions and verification", ""])
    for key in ["changes", "verification"]:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend(
        [
            "",
            "## Privacy checklist",
            "",
            "- No router, Wi-Fi, or Lithe account password included.",
            "- No MFA code, token, cookie, API key, or recovery code included.",
            "- No public IP address or unrelated network client included.",
            "- Full MAC addresses were masked.",
            "- The report was saved locally and must be reviewed before sharing.",
            "",
        ]
    )
    return "\n".join(sections)


def run_self_test() -> int:
    sample = {
        "target_ip": "192.168.1.45",
        "masked_mac": "AA:BB:CC:XX:XX:FF",
        "status": "degraded",
        "ping": {
            "sent": 20,
            "received": 19,
            "loss_percent": 5,
            "average_ms": 61,
            "maximum_ms": 140,
        },
        "safe_tcp_connect": {"80": False, "443": False},
    }
    fields = parse_fields(
        [
            "walls=Two brick walls",
            "customer_notes=password=hunter2 public=8.8.8.8 mac=AA:BB:CC:DD:EE:FF",
        ]
    )
    report = build_report(sample, fields)
    checks = [
        "hunter2" not in report,
        "8.8.8.8" not in report,
        "AA:BB:CC:DD:EE:FF" not in report,
        "AA:BB:CC:XX:XX:FF" in report,
        "Two brick walls" in report,
    ]
    if all(checks):
        print("Self-test passed.")
        return 0
    print("Self-test failed.", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a redacted local Lithe Audio support report."
    )
    parser.add_argument("--diagnostic-json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--field", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()
    if args.output is None:
        parser.error("--output is required unless --self-test is used.")
    if args.output.exists():
        print(f"Refusing to overwrite existing report: {args.output}", file=sys.stderr)
        return 3

    try:
        diagnostic = load_diagnostic(args.diagnostic_json)
        fields = parse_fields(args.field)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Cannot create report: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_report(diagnostic, fields), encoding="utf-8")
    print(f"Saved redacted local support report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
