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
from tempfile import TemporaryDirectory
from typing import Any


ALLOWED_FIELDS = {
    "product_name": "Product name",
    "firmware_version": "Firmware version",
    "symptom": "Reported symptom",
    "frequency": "Frequency",
    "first_seen": "First noticed",
    "last_occurrence": "Last occurrence",
    "customer_impact": "Customer impact",
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
    "log_source": "Log source",
    "log_window": "Relevant log window",
    "log_evidence": "Redacted log evidence",
    "log_status": "Log collection status",
    "likely_cause": "Likely cause",
    "confidence": "Diagnostic confidence",
    "layer_results": "Layer results",
    "dhcp_health": "DHCP health",
    "dual_band_assessment": "Dual-band assessment",
    "topology_assessment": "Topology assessment",
    "probable_root_cause": "Probable root cause",
    "smoking_gun": "Smoking gun",
    "correlation_evidence": "Correlation evidence",
    "correlated_timeline": "Failure-window timeline",
    "initial_findings": "Initial findings",
    "meaning": "What the findings mean",
    "before_measurements": "Before change",
    "approved_fix": "Approved fix",
    "changes": "Changes tried",
    "expected_improvement": "Expected improvement",
    "after_measurements": "After change",
    "rollback": "Rollback",
    "verification": "Verification outcome",
    "customer_outcome": "Customer-reported outcome",
    "faults_found": "Faults identified",
    "fixes_completed": "Improvements completed",
    "outstanding": "Outstanding items",
    "customer_notes": "Customer notes",
}
SECRET_RE = re.compile(
    r"(?i)\b(password|passcode|passwd|token|api[ _-]?key|secret|"
    r"mfa|recovery[ _-]?code|username|email)\b\s*[:=]\s*"
    r"(?:\"[^\"]*\"|'[^']*'|[^,;\n]+)"
)
MAC_RE = re.compile(r"\b([0-9a-fA-F]{2})(?:[:-]([0-9a-fA-F]{2})){5}\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_RE = re.compile(
    r"(?<![\w:])(?:[0-9a-fA-F]{1,4}:){2,}[0-9a-fA-F:]{0,39}(?![\w:])"
)
MAX_JSON_BYTES = 5 * 1024 * 1024
EMAIL_RE = re.compile(
    r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
)


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


def redact_ipv6(match: re.Match[str]) -> str:
    value = match.group(0)
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return value
    return value if address.is_private else "[REDACTED PUBLIC IPv6]"


def sanitise(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = EMAIL_RE.sub("[REDACTED EMAIL]", text)
    text = MAC_RE.sub(mask_mac, text)
    text = IPV4_RE.sub(redact_public_ip, text)
    text = IPV6_RE.sub(redact_ipv6, text)
    text = re.sub(r"([`*\[\]()<>])", r"\\\1", text)
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
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("Diagnostic JSON exceeds the 5 MB limit.")
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


def fields_from_log_analysis(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("Log-analysis JSON exceeds the 5 MB limit.")
    data = json.loads(path.read_text(encoding="utf-8"))
    analysis = data.get("analysis", data)
    collection = data.get("collection", {})
    findings = analysis.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("Log-analysis JSON contains an invalid findings list.")
    rendered = []
    for finding in findings[:3]:
        if not isinstance(finding, dict):
            continue
        rendered.append(
            f"{finding.get('category', 'unknown')} ({finding.get('event_count', '?')} event(s))"
        )
    fields: dict[str, str] = {
        "log_status": sanitise(collection.get("status", "Analysed locally")),
        "log_source": "Approved local speaker log",
        "log_window": sanitise(
            f"{analysis.get('failure_time') or 'No precise failure time'}; "
            f"coverage={analysis.get('failure_time_covered')}"
        ),
        "log_evidence": sanitise(", ".join(rendered) if rendered else "No supported pattern found"),
    }
    if findings and isinstance(findings[0], dict):
        first = findings[0]
        fields["likely_cause"] = sanitise(first.get("category", "Unconfirmed"))
        fields["confidence"] = sanitise(
            "Smoking-gun candidate; corroboration required"
            if first.get("smoking_gun_candidate")
            else "Possible; timestamp or corroboration incomplete"
        )
        fields["outstanding"] = sanitise(first.get("next_proof", "Review router/AP evidence"))
    return fields


def fields_from_correlation(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("Correlation JSON exceeds the 5 MB limit.")
    data = json.loads(path.read_text(encoding="utf-8"))
    root = data.get("probable_root_cause", {})
    layers = data.get("layers", {})
    dhcp = data.get("dhcp_health", {})
    dual = data.get("dual_band_assessment", {})
    topology = data.get("topology_assessment", {})
    timeline = data.get("correlated_timeline", [])
    if not all(isinstance(item, dict) for item in [root, layers, dhcp, dual, topology]):
        raise ValueError("Correlation JSON contains an invalid object.")
    layer_text = "; ".join(
        f"{name}={item.get('status', 'unknown')}"
        for name, item in layers.items()
        if isinstance(item, dict)
    )
    evidence = root.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = [str(evidence)]
    timeline_text = "; ".join(
        f"{item.get('timestamp', '?')} {item.get('event', 'event')} [{item.get('source', 'unknown')}]"
        for item in timeline
        if isinstance(item, dict)
    ) if isinstance(timeline, list) else ""
    return {
        "layer_results": sanitise(layer_text or "No layer results"),
        "dhcp_health": sanitise(json.dumps(dhcp, separators=(",", ":"))),
        "dual_band_assessment": sanitise(json.dumps(dual, separators=(",", ":"))),
        "topology_assessment": sanitise(json.dumps(topology, separators=(",", ":"))),
        "probable_root_cause": sanitise(root.get("label", "Undetermined")),
        "confidence": sanitise(root.get("confidence", "Undetermined")),
        "smoking_gun": "Yes" if root.get("smoking_gun") is True else "No",
        "correlation_evidence": sanitise("; ".join(str(item) for item in evidence[:4])),
        "correlated_timeline": sanitise(timeline_text or "No complete failure-window sequence established"),
        "approved_fix": sanitise(root.get("targeted_fix", "No evidence-backed fix selected")),
        "expected_improvement": sanitise(root.get("expected_improvement", "Not established")),
    }


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
        "## Product details",
        "",
    ]
    for key in ["product_name", "firmware_version"]:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend([
        "",
        "## Customer-reported issue",
        "",
    ])
    issue_order = [
        "symptom",
        "customer_impact",
        "frequency",
        "first_seen",
        "last_occurrence",
        "other_devices",
        "customer_notes",
    ]
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

    sections.extend(["", "## Correlated log evidence", ""])
    for key in [
        "log_status",
        "log_source",
        "log_window",
        "log_evidence",
        "likely_cause",
        "confidence",
    ]:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend(["", "## Layered correlation and probable root cause", ""])
    for key in [
        "layer_results",
        "dhcp_health",
        "dual_band_assessment",
        "topology_assessment",
        "probable_root_cause",
        "confidence",
        "smoking_gun",
        "correlation_evidence",
        "correlated_timeline",
    ]:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend(["", "## Problem and diagnosis", ""])
    for key in [
        "initial_findings",
        "meaning",
        "faults_found",
    ]:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend(["", "## Fix completed and expected improvement", ""])
    for key in [
        "approved_fix",
        "fixes_completed",
        "changes",
        "expected_improvement",
        "rollback",
    ]:
        if key in fields:
            sections.append(line(ALLOWED_FIELDS[key], fields[key]))

    sections.extend(["", "## Before and after verification", ""])
    for key in [
        "before_measurements",
        "after_measurements",
        "customer_outcome",
        "verification",
        "outstanding",
    ]:
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
            "## Customer handoff",
            "",
            "This report is ready for the customer to review and attach to an email to Lithe Audio support. It was not emailed or uploaded automatically.",
            "",
            "## Further help - Lithe Audio Support",
            "",
            "- **Telephone:** +44 (0)1293 922015",
            "- **Email:** support@litheaudio.com",
            "- **Support portal:** https://support.litheaudio.com",
            "",
            "Thank you for your time today.",
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
            "product_name=Lithe Audio WiFi Speaker",
            "firmware_version=TEST.1",
            "walls=Two brick walls",
            "log_status=Failed - exported file contained zero bytes",
            "initial_findings=5 percent loss and 140 ms maximum latency",
            "meaning=The live path was unstable during the sample",
            "before_measurements=19/20 replies and 5 percent loss",
            "approved_fix=Created a DHCP reservation",
            "expected_improvement=Prevent address changes after lease renewal",
            "after_measurements=20/20 replies and 0 percent loss",
            "customer_outcome=Playback passed for five minutes",
            "outstanding=Speaker log export requires investigation",
            "customer_notes=password=hunter2 public=8.8.8.8 mac=AA:BB:CC:DD:EE:FF",
            "outstanding=Contact customer@example.com; token=correct horse battery staple",
        ]
    )
    report = build_report(sample, fields)
    with TemporaryDirectory() as directory:
        analysis_path = Path(directory) / "analysis.json"
        analysis_path.write_text(
            json.dumps(
                {
                    "collection": {"status": "downloaded"},
                    "analysis": {
                        "failure_time": "2026-08-11 10:00:00+01:00",
                        "failure_time_covered": True,
                        "findings": [
                            {
                                "category": "dhcp",
                                "event_count": 1,
                                "smoking_gun_candidate": True,
                                "next_proof": "Compare router lease history",
                            }
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        derived = fields_from_log_analysis(analysis_path)
        correlation_path = Path(directory) / "correlation.json"
        correlation_path.write_text(
            json.dumps(
                {
                    "layers": {"basic_connectivity": {"status": "Pass"}},
                    "dhcp_health": {"result": "Pass"},
                    "dual_band_assessment": {"result": "Pass"},
                    "topology_assessment": {"physical_topology": "pass"},
                    "correlated_timeline": [
                        {"timestamp": "14:31:05", "event": "dhcp_renew", "source": "speaker_log"},
                        {"timestamp": "14:31:09", "event": "cast_reconnect", "source": "cast_history"},
                    ],
                    "probable_root_cause": {
                        "label": "DHCP lease instability",
                        "confidence": "Confirmed",
                        "smoking_gun": True,
                        "evidence": ["Renewal failure aligned with dropout"],
                        "targeted_fix": "Create a router-side reservation",
                        "expected_improvement": "Keep the address stable",
                    },
                }
            ),
            encoding="utf-8",
        )
        correlated = fields_from_correlation(correlation_path)
    checks = [
        "hunter2" not in report,
        "8.8.8.8" not in report,
        "AA:BB:CC:DD:EE:FF" not in report,
        "AA:BB:CC:XX:XX:FF" in report,
        "Two brick walls" in report,
        "Failed - exported file contained zero bytes" in report,
        "Thank you for your time today." in report,
        "## Problem and diagnosis" in report,
        "## Fix completed and expected improvement" in report,
        "## Before and after verification" in report,
        "Prevent address changes after lease renewal" in report,
        "+44 (0)1293 922015" in report,
        "support@litheaudio.com" in report,
        "REDACTED EMAIL" in report,
        "https://support.litheaudio.com" in report,
        "customer@example.com" not in report,
        "correct horse battery staple" not in report,
        "REDACTED EMAIL" in report,
        "2001:4860:4860::8888" not in sanitise("WAN 2001:4860:4860::8888"),
        fields_from_log_analysis(None) == {},
        derived["likely_cause"] == "dhcp",
        "corroboration required" in derived["confidence"],
        correlated["smoking_gun"] == "Yes",
        correlated["probable_root_cause"] == "DHCP lease instability",
        "cast_reconnect" in correlated["correlated_timeline"],
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
    parser.add_argument("--log-analysis-json", type=Path)
    parser.add_argument("--correlation-json", type=Path)
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
        fields = fields_from_log_analysis(args.log_analysis_json)
        fields.update(fields_from_correlation(args.correlation_json))
        fields.update(parse_fields(args.field))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Cannot create report: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_report(diagnostic, fields), encoding="utf-8")
    print(f"Saved redacted local support report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
