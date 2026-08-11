#!/usr/bin/env python3
"""Collect one approved local speaker log, analyse it, then delete the raw file."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

import analyze_speaker_logs as analyzer
import download_speaker_logs as downloader


def build_result(
    log_path: Path,
    provenance: dict,
    failure_time: datetime | None,
    window_minutes: int,
    timezone_label: str,
) -> dict:
    scanned, outside, accumulators, earliest, latest = analyzer.analyse_lines(
        analyzer.iter_log_lines([log_path]), failure_time, window_minutes
    )
    covered = analyzer.failure_is_covered(failure_time, earliest, latest)
    findings = analyzer.build_findings(accumulators, failure_time, covered)
    now = datetime.now(timezone.utc)
    future_clock_warning = False
    if latest is not None:
        comparable = latest
        if comparable.tzinfo is None:
            comparable = comparable.replace(tzinfo=failure_time.tzinfo if failure_time else timezone.utc)
        future_clock_warning = comparable.astimezone(timezone.utc) > now + timedelta(minutes=15)

    rendered_findings = [asdict(finding) for finding in findings]
    if future_clock_warning:
        for finding in rendered_findings:
            finding["smoking_gun_candidate"] = False

    return {
        "collection": {
            "status": provenance["status"],
            "source": provenance["source"],
            "target_ip": provenance["target_ip"],
            "bytes": provenance["bytes"],
            "sha256": provenance["sha256"],
            "collected_at_utc": now.isoformat(timespec="seconds"),
            "raw_log_retained": False,
        },
        "analysis": {
            "timezone_label": timezone_label,
            "failure_time": (
                failure_time.isoformat(sep=" ", timespec="seconds")
                if failure_time
                else None
            ),
            "window_minutes_each_side": window_minutes if failure_time else None,
            "lines_scanned": scanned,
            "log_time_coverage": {
                "earliest": earliest.isoformat(sep=" ", timespec="seconds") if earliest else None,
                "latest": latest.isoformat(sep=" ", timespec="seconds") if latest else None,
            },
            "failure_time_covered": covered,
            "future_clock_warning": future_clock_warning,
            "matching_lines_outside_window_or_without_timestamp": outside,
            "findings": rendered_findings,
            "interpretation": (
                "Speaker clock appears ahead of collection time; do not correlate until "
                "the clock offset is resolved."
                if future_clock_warning
                else "Time-correlated evidence candidates found; corroboration is required."
                if rendered_findings and failure_time
                else "Patterns found without a precise failure time; correlation is unproven."
                if rendered_findings
                else "No supported fault pattern was found in the selected scope."
            ),
        },
        "privacy": (
            "The raw log was analysed in a temporary directory and deleted. Only this "
            "redacted summary remains in the command output."
        ),
    }


def run_self_test() -> int:
    failure = datetime.fromisoformat("2026-08-11 10:00:00+01:00")
    with TemporaryDirectory() as directory:
        path = Path(directory) / "speaker.log"
        path.write_text(
            "2026-08-11 10:00:01+01:00 DHCP renew failed\n"
            "2026-08-11 10:00:02+01:00 WiFi disassociated\n",
            encoding="utf-8",
        )
        result = build_result(
            path,
            {
                "status": "downloaded",
                "source": "customer_supplied_private_speaker",
                "target_ip": "192.168.1.85",
                "bytes": path.stat().st_size,
                "sha256": "test",
            },
            failure,
            15,
            "Europe/London",
        )
    checks = (
        result["analysis"]["failure_time_covered"] is False,
        len(result["analysis"]["findings"]) == 2,
        not any(
            finding["smoking_gun_candidate"]
            for finding in result["analysis"]["findings"]
        ),
        result["collection"]["raw_log_retained"] is False,
        "raw log" in result["privacy"].lower(),
    )
    if all(checks):
        print("Self-test passed.")
        return 0
    print("Self-test failed.", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download and analyse one approved local Lithe speaker log without retaining "
            "the raw file. No scan, authentication, upload or setting change."
        )
    )
    parser.add_argument("ip", nargs="?", type=downloader.private_ipv4)
    parser.add_argument("--failure-time", type=analyzer.parse_datetime)
    parser.add_argument("--window-minutes", type=analyzer.window_minutes, default=15)
    parser.add_argument("--timezone", type=analyzer.timezone_name)
    parser.add_argument("--timeout", type=downloader.positive_timeout, default=15.0)
    parser.add_argument("--save-json", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if args.ip is None:
        parser.error("Provide the customer-supplied private speaker IP.")

    timezone_label = args.timezone or "Computer local time"
    zone = ZoneInfo(args.timezone) if args.timezone else datetime.now().astimezone().tzinfo
    failure_time = args.failure_time
    if failure_time is not None and failure_time.tzinfo is None:
        failure_time = failure_time.replace(tzinfo=zone)

    try:
        with TemporaryDirectory(prefix="lithe-speaker-log-") as directory:
            path = Path(directory) / "speaker.log"
            provenance = downloader.download(args.ip, path, args.timeout)
            result = build_result(
                path,
                provenance,
                failure_time,
                args.window_minutes,
                timezone_label,
            )
    except Exception:  # Convert local collection failures into safe structured output.
        print(
            json.dumps(
                {
                    "collection": {
                        "status": "failed",
                        "reason": "Speaker log collection did not return usable data.",
                    },
                    "raw_log_retained": False,
                },
                indent=2,
            )
        )
        return 1

    payload = json.dumps(result, indent=2)
    if args.save_json is not None:
        output = args.save_json.expanduser().resolve()
        if output.exists():
            print(f"Refusing to overwrite existing analysis: {output.name}", file=sys.stderr)
            return 3
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
