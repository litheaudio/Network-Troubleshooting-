#!/usr/bin/env python3
"""Analyse customer-authorised local speaker logs without exposing raw content."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_SAMPLE_TIMESTAMPS = 3

PATTERNS: dict[str, re.Pattern[str]] = {
    "dhcp": re.compile(
        r"(?:\b(?:dhcp|lease)\b.{0,100}\b(?:nak|conflict|duplicate|expire[ds]?|"
        r"lost|fail(?:ed|ure)?|timeout|timed out|no offer|no ack|declined?)\b|"
        r"\b(?:address conflict|duplicate ip|dhcp nak)\b)",
        re.IGNORECASE,
    ),
    "wifi_disconnect": re.compile(
        r"\b(?:deauth(?:enticated)?|disassoc(?:iated)?|association lost|"
        r"authentication fail(?:ed|ure)?|wifi.{0,20}(?:down|lost|reconnect)|"
        r"reconnect.{0,20}wifi|wlan.{0,20}disconnect(?:ed)?)\b",
        re.IGNORECASE,
    ),
    "timeout_or_loss": re.compile(
        r"\b(?:packet loss|retransmit|socket timeout|connection timeout|timed out|"
        r"no response|retry limit)\b",
        re.IGNORECASE,
    ),
    "route_or_gateway": re.compile(
        r"\b(?:gateway unreachable|no route|arp fail|host unreachable|network unreachable)\b",
        re.IGNORECASE,
    ),
    "reboot_or_watchdog": re.compile(
        r"\b(?:watchdog|reboot|restarting|boot sequence|uptime reset|kernel panic|"
        r"unexpected reset)\b",
        re.IGNORECASE,
    ),
    "discovery": re.compile(
        r"\b(?:multicast|mdns|discovery).{0,35}(?:fail|blocked|timeout|lost|leave)\b",
        re.IGNORECASE,
    ),
    "roaming_or_ap_change": re.compile(
        r"\b(?:roam|bssid.{0,20}change|access point.{0,20}change|ap.{0,12}change|"
        r"channel.{0,20}change|dfs event)\b",
        re.IGNORECASE,
    ),
}

NEXT_PROOF = {
    "dhcp": "Compare the router lease history and DHCP reservation for this IP.",
    "wifi_disconnect": "Compare the serving AP, RSSI and retry history at these times.",
    "timeout_or_loss": "Compare ping loss and AP retry/drop counters in the same window.",
    "route_or_gateway": "Check gateway reachability, VLAN placement and client isolation.",
    "reboot_or_watchdog": "Compare speaker uptime and power history before changing Wi-Fi settings.",
    "discovery": "Check guest isolation and multicast discovery while confirming IP reachability.",
    "roaming_or_ap_change": "Check AP association history, backhaul and fast-roaming settings.",
}

EVIDENCE_WEIGHT = {
    "reboot_or_watchdog": 90,
    "route_or_gateway": 85,
    "wifi_disconnect": 80,
    "dhcp": 75,
    "roaming_or_ap_change": 65,
    "discovery": 60,
    "timeout_or_loss": 50,
}

TARGETED_FIX = {
    "dhcp": (
        "Create a router-side DHCP reservation for the speaker's current address after "
        "checking that no other client owns it.",
        "This prevents lease churn and duplicate-address conflicts without setting a "
        "manual address on the speaker.",
    ),
    "wifi_disconnect": (
        "Correct the serving access point or radio path shown at the event time, then "
        "retest signal and retries.",
        "The log shows loss of Wi-Fi association; changing DHCP alone would not repair "
        "the radio interruption.",
    ),
    "timeout_or_loss": (
        "Reduce retry or packet-loss conditions on the serving access point and retest "
        "before changing another setting.",
        "Timeout evidence identifies an interrupted data path but needs AP counters to "
        "select channel, placement or load as the exact cause.",
    ),
    "route_or_gateway": (
        "Correct the speaker's LAN/VLAN gateway path or client-isolation setting after "
        "confirming the router state.",
        "The speaker could not reach its local gateway or route, so radio tuning alone "
        "would not restore the path.",
    ),
    "reboot_or_watchdog": (
        "Preserve the log, verify power and firmware state, and escalate the restart "
        "evidence before making broad Wi-Fi changes.",
        "A reboot or watchdog reset points to speaker power or software recovery rather "
        "than proving a router fault.",
    ),
    "discovery": (
        "Keep the phone and speaker on the same trusted LAN and correct client isolation "
        "or multicast discovery controls.",
        "The IP path can remain reachable while isolation prevents the Lithe Audio app "
        "from discovering the speaker.",
    ),
    "roaming_or_ap_change": (
        "Stabilise the stationary speaker on a proven access point or disable unsuitable "
        "fast roaming for its SSID, one reversible change at a time.",
        "The interruption aligns with an AP, BSSID or channel transition.",
    ),
}


@dataclass
class Finding:
    category: str
    event_count: int
    first_event: Optional[str]
    last_event: Optional[str]
    sample_timestamps: list[str]
    relation_to_failure: str
    next_proof: str
    smoking_gun_candidate: bool
    targeted_fix: str
    why_this_fix: str
    evidence_score: int


@dataclass
class CategoryAccumulator:
    count: int = 0
    first: Optional[datetime] = None
    last: Optional[datetime] = None
    samples: list[str] | None = None

    def __post_init__(self) -> None:
        if self.samples is None:
            self.samples = []

    def add(self, timestamp: Optional[datetime]) -> None:
        self.count += 1
        if timestamp is None:
            return
        if self.first is None or timestamp < self.first:
            self.first = timestamp
        if self.last is None or timestamp > self.last:
            self.last = timestamp
        rendered = timestamp.isoformat(sep=" ", timespec="seconds")
        if rendered not in self.samples and len(self.samples) < MAX_SAMPLE_TIMESTAMPS:
            self.samples.append(rendered)


def parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Use an ISO-style time such as 2026-07-29 14:30:00."
        ) from exc


def timezone_name(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise argparse.ArgumentTypeError(
            "Use an IANA timezone such as Europe/London."
        ) from exc
    return value


def window_minutes(value: str) -> int:
    try:
        minutes = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Window must be 1 to 1440 minutes.") from exc
    if not 1 <= minutes <= 1440:
        raise argparse.ArgumentTypeError("Window must be 1 to 1440 minutes.")
    return minutes


def extract_timestamp(line: str, default_year: int) -> Optional[datetime]:
    full = re.search(
        r"\b(\d{4}[-/]\d{2}[-/]\d{2})[T ]"
        r"(\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)",
        line,
    )
    if full:
        value = f"{full.group(1).replace('/', '-')} {full.group(2)}"
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        offset = re.search(r"([+-]\d{2})(\d{2})$", value)
        if offset and ":" not in offset.group(0):
            value = value[: offset.start()] + f"{offset.group(1)}:{offset.group(2)}"
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    syslog = re.search(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
        r"(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\b",
        line,
        re.IGNORECASE,
    )
    if syslog:
        try:
            return datetime.strptime(
                f"{default_year} {syslog.group(1).title()} {syslog.group(2)} "
                f"{syslog.group(3)}",
                "%Y %b %d %H:%M:%S",
            )
        except ValueError:
            return None
    return None


def within_window(
    timestamp: Optional[datetime],
    failure_time: Optional[datetime],
    minutes: int,
) -> bool:
    if failure_time is None:
        return True
    if timestamp is None:
        return False
    if timestamp.tzinfo is not None and failure_time.tzinfo is None:
        failure_time = failure_time.replace(tzinfo=timestamp.tzinfo)
    elif timestamp.tzinfo is None and failure_time.tzinfo is not None:
        timestamp = timestamp.replace(tzinfo=failure_time.tzinfo)
    return abs(timestamp - failure_time) <= timedelta(minutes=minutes)


def analyse_lines(
    lines: Iterable[str],
    failure_time: Optional[datetime],
    minutes: int,
) -> tuple[
    int,
    int,
    dict[str, CategoryAccumulator],
    Optional[datetime],
    Optional[datetime],
]:
    scanned = 0
    matched_outside_window = 0
    accumulators = {category: CategoryAccumulator() for category in PATTERNS}
    default_year = failure_time.year if failure_time else datetime.now().year
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None

    for line in lines:
        scanned += 1
        timestamp = extract_timestamp(line, default_year)
        if (
            timestamp is not None
            and timestamp.tzinfo is None
            and failure_time is not None
            and failure_time.tzinfo is not None
        ):
            timestamp = timestamp.replace(tzinfo=failure_time.tzinfo)
        if timestamp is not None:
            if earliest_timestamp is None or timestamp < earliest_timestamp:
                earliest_timestamp = timestamp
            if latest_timestamp is None or timestamp > latest_timestamp:
                latest_timestamp = timestamp
        matched_categories = [
            category for category, pattern in PATTERNS.items() if pattern.search(line)
        ]
        if not matched_categories:
            continue
        if not within_window(timestamp, failure_time, minutes):
            matched_outside_window += 1
            continue
        for category in matched_categories:
            accumulators[category].add(timestamp)
    return (
        scanned,
        matched_outside_window,
        accumulators,
        earliest_timestamp,
        latest_timestamp,
    )


def failure_is_covered(
    failure_time: Optional[datetime],
    earliest_timestamp: Optional[datetime],
    latest_timestamp: Optional[datetime],
) -> Optional[bool]:
    if failure_time is None or earliest_timestamp is None or latest_timestamp is None:
        return None
    candidate = failure_time
    earliest = earliest_timestamp
    latest = latest_timestamp
    if candidate.tzinfo is not None and earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=candidate.tzinfo)
        latest = latest.replace(tzinfo=candidate.tzinfo)
    elif candidate.tzinfo is None and earliest.tzinfo is not None:
        candidate = candidate.replace(tzinfo=earliest.tzinfo)
    return earliest <= candidate <= latest


def iter_log_lines(paths: list[Path]) -> Iterable[str]:
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            yield from handle


def validate_paths(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    total_bytes = 0
    for value in values:
        path = Path(value).expanduser()
        if not path.is_file():
            raise argparse.ArgumentTypeError(f"Log file not found: {path}")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise argparse.ArgumentTypeError(
                f"Log file exceeds the 100 MB local-analysis limit: {path.name}"
            )
        total_bytes += path.stat().st_size
        if total_bytes > MAX_FILE_BYTES:
            raise argparse.ArgumentTypeError(
                "Combined logs exceed the 100 MB local-analysis limit."
            )
        paths.append(path)
    return paths


def build_findings(
    accumulators: dict[str, CategoryAccumulator],
    failure_time: Optional[datetime],
    failure_covered: Optional[bool],
) -> list[Finding]:
    findings: list[Finding] = []
    for category, accumulator in accumulators.items():
        if accumulator.count == 0:
            continue
        targeted_fix, why_this_fix = TARGETED_FIX[category]
        findings.append(
            Finding(
                category=category,
                event_count=accumulator.count,
                first_event=(
                    accumulator.first.isoformat(sep=" ", timespec="seconds")
                    if accumulator.first
                    else None
                ),
                last_event=(
                    accumulator.last.isoformat(sep=" ", timespec="seconds")
                    if accumulator.last
                    else None
                ),
                sample_timestamps=accumulator.samples or [],
                relation_to_failure=(
                    "inside_selected_failure_window"
                    if failure_time
                    else "observed_without_failure_window"
                ),
                next_proof=NEXT_PROOF[category],
                smoking_gun_candidate=bool(
                    failure_time and failure_covered is True and accumulator.first
                ),
                targeted_fix=targeted_fix,
                why_this_fix=why_this_fix,
                evidence_score=EVIDENCE_WEIGHT[category]
                + min(accumulator.count, 10),
            )
        )
    return sorted(findings, key=lambda finding: finding.evidence_score, reverse=True)


def run_self_test() -> int:
    failure = datetime.fromisoformat("2026-07-29 14:30:00")
    sample = [
        "2026-07-29 14:29:40 DHCP lease renew failed",
        "2026-07-29 14:30:04 WiFi disassociated and reconnect started",
        "2026-07-29 14:30:10 socket timeout",
        "2026-07-29 18:00:00 reboot",
        "line without a relevant event",
    ]
    scanned, outside, accumulators, earliest, latest = analyse_lines(sample, failure, 15)
    _, _, _, post_restart_earliest, post_restart_latest = analyse_lines(
        ["2026-07-29 14:35:00 boot sequence", "2026-07-29 14:36:00 wifi up"],
        failure,
        15,
    )
    findings = build_findings(accumulators, failure, True)
    finding_by_category = {finding.category: finding for finding in findings}
    checks = [
        scanned == 5,
        outside == 1,
        accumulators["dhcp"].count == 1,
        accumulators["wifi_disconnect"].count == 1,
        accumulators["timeout_or_loss"].count == 1,
        accumulators["reboot_or_watchdog"].count == 0,
        earliest == datetime.fromisoformat("2026-07-29 14:29:40"),
        latest == datetime.fromisoformat("2026-07-29 18:00:00"),
        failure_is_covered(failure, earliest, latest) is True,
        failure_is_covered(
            failure, post_restart_earliest, post_restart_latest
        ) is False,
        finding_by_category["dhcp"].smoking_gun_candidate is True,
        "DHCP reservation" in finding_by_category["dhcp"].targeted_fix,
        bool(finding_by_category["dhcp"].why_this_fix),
        analyse_lines(
            ["2026-07-29 14:30:00 DHCP lease renewed successfully"],
            failure,
            15,
        )[2]["dhcp"].count
        == 0,
        analyse_lines(
            ["2026-07-29 14:30:00 user selected disconnect menu"],
            failure,
            15,
        )[2]["wifi_disconnect"].count
        == 0,
    ]
    if all(checks):
        print("Self-test passed.")
        return 0
    print("Self-test failed.", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analyse customer-authorised local speaker logs and emit redacted "
            "event-category evidence. No network request or upload is performed."
        )
    )
    parser.add_argument("logs", nargs="*", help="One or more local log files")
    parser.add_argument("--failure-time", type=parse_datetime)
    parser.add_argument("--window-minutes", type=window_minutes, default=15)
    parser.add_argument("--timezone", type=timezone_name)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if not args.logs:
        parser.error("Provide at least one customer-authorised local log file.")
    try:
        paths = validate_paths(args.logs)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    timezone_label = args.timezone or "Computer local time"
    zone = ZoneInfo(args.timezone) if args.timezone else datetime.now().astimezone().tzinfo
    if args.failure_time is not None and args.failure_time.tzinfo is None:
        args.failure_time = args.failure_time.replace(tzinfo=zone)

    scanned, outside, accumulators, earliest, latest = analyse_lines(
        iter_log_lines(paths),
        args.failure_time,
        args.window_minutes,
    )
    covered = failure_is_covered(args.failure_time, earliest, latest)
    findings = build_findings(accumulators, args.failure_time, covered)
    result = {
        "files_analysed": [path.name for path in paths],
        "timezone_label": timezone_label,
        "failure_time": (
            args.failure_time.isoformat(sep=" ", timespec="seconds")
            if args.failure_time
            else None
        ),
        "window_minutes_each_side": args.window_minutes if args.failure_time else None,
        "lines_scanned": scanned,
        "log_time_coverage": {
            "earliest": (
                earliest.isoformat(sep=" ", timespec="seconds") if earliest else None
            ),
            "latest": (
                latest.isoformat(sep=" ", timespec="seconds") if latest else None
            ),
        },
        "failure_time_covered": covered,
        "matching_lines_outside_window_or_without_timestamp": outside,
        "findings": [asdict(finding) for finding in findings],
        "interpretation": (
            "Timestamp-correlated smoking-gun candidate(s) found; corroborate before "
            "assigning a confirmed cause or applying the targeted fix."
            if findings and args.failure_time
            else "Patterns found without a precise failure window; correlation is unproven."
            if findings
            else "No supported evidence pattern was found in the selected scope."
        ),
        "privacy": (
            "Local read-only analysis. Raw log lines, credentials, full MAC addresses "
            "and internal paths are not emitted or uploaded."
        ),
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Files analysed: {', '.join(result['files_analysed'])}")
    print(f"Lines scanned: {scanned}")
    if args.failure_time:
        print(
            f"Failure window: +/- {args.window_minutes} minutes around "
            f"{result['failure_time']} ({timezone_label})"
        )
        if result["failure_time_covered"] is False:
            print("Coverage: the log does not contain the supplied failure time.")
        elif result["failure_time_covered"] is True:
            print("Coverage: the log contains the supplied failure time.")
        else:
            print("Coverage: unavailable because usable log timestamps are missing.")
    if not findings:
        print("Evidence: no supported pattern found in the selected scope.")
    for finding in findings:
        print(
            f"Evidence: {finding.category} - {finding.event_count} event(s), "
            f"{finding.relation_to_failure}"
        )
        if finding.sample_timestamps:
            print(f"Times: {', '.join(finding.sample_timestamps)}")
        print(f"Next proof: {finding.next_proof}")
        print(f"Targeted fix: {finding.targeted_fix}")
        print(f"Why: {finding.why_this_fix}")
    print(f"Interpretation: {result['interpretation']}")
    print(f"Privacy: {result['privacy']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
