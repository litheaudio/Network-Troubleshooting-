#!/usr/bin/env python3
"""Download the approved read-only Lithe speaker log from one private IPv4 target."""

from __future__ import annotations

import argparse
import hashlib
import io
import ipaddress
import json
import os
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


LOG_PATH = "/devcielogs.txt"
MAX_BYTES = 100 * 1024 * 1024
RFC1918 = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise urllib.error.HTTPError(newurl, code, "Redirect refused", headers, fp)


def private_ipv4(value: str) -> ipaddress.IPv4Address:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Provide a valid private IPv4 address.") from exc
    if not isinstance(address, ipaddress.IPv4Address) or not any(
        address in network for network in RFC1918
    ):
        raise argparse.ArgumentTypeError("Only a private IPv4 speaker address is allowed.")
    return address


def positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Timeout must be between 1 and 60 seconds.") from exc
    if not 1 <= timeout <= 60:
        raise argparse.ArgumentTypeError("Timeout must be between 1 and 60 seconds.")
    return timeout


def download(
    address: ipaddress.IPv4Address,
    destination: Path,
    timeout: float,
    opener=None,  # Test injection only; production uses the hardened local opener.
) -> dict:
    url = f"http://{address}{LOG_PATH}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Lithe-Audio-Network-Diagnostic/1.0"},
        method="GET",
    )
    if opener is None:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect()
        )
    destination = destination.expanduser().resolve()
    if destination.exists():
        raise RuntimeError(f"Output file already exists: {destination.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    byte_count = 0
    digest = hashlib.sha256()

    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"Speaker returned HTTP {response.status}.")
            declared = response.headers.get("Content-Length")
            if declared:
                try:
                    declared_bytes = int(declared)
                except ValueError as exc:
                    raise RuntimeError("Speaker returned an invalid content length.") from exc
                if declared_bytes > MAX_BYTES:
                    raise RuntimeError("Speaker log exceeds the 100 MB safety limit.")

            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, dir=destination.parent, prefix=".lithe-log-"
            ) as handle:
                temp_name = handle.name
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    byte_count += len(chunk)
                    if byte_count > MAX_BYTES:
                        raise RuntimeError("Speaker log exceeds the 100 MB safety limit.")
                    digest.update(chunk)
                    handle.write(chunk)

        if byte_count == 0:
            raise RuntimeError("The speaker returned a zero-byte log.")

        first_bytes = Path(temp_name).read_bytes()[:512].lstrip().lower()
        if first_bytes.startswith((b"<!doctype html", b"<html")):
            raise RuntimeError("The speaker returned a web page instead of a log file.")

        os.replace(temp_name, destination)
        temp_name = None
        return {
            "status": "downloaded",
            "source": "customer_supplied_private_speaker",
            "target_ip": str(address),
            "file": destination.name,
            "bytes": byte_count,
            "sha256": digest.hexdigest(),
            "read_only": True,
        }
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download the approved read-only support log from one customer-supplied "
            "private Lithe speaker IP. No scan, authentication, upload or setting change."
        )
    )
    parser.add_argument("ip", nargs="?", type=private_ipv4)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=positive_timeout, default=15.0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def run_self_test() -> int:
    payload = b"2026-08-11 10:00:00 DHCP lease renew failed\n"

    class FakeResponse(io.BytesIO):
        status = 200
        headers = {"Content-Length": str(len(payload))}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):  # noqa: ANN001
            self.close()

    class FakeOpener:
        requested_url = ""

        def open(self, request, timeout):  # noqa: ANN001
            self.requested_url = request.full_url
            return FakeResponse(payload)

    opener = FakeOpener()
    with TemporaryDirectory() as directory:
        output = Path(directory) / "speaker.log"
        result = download(
            ipaddress.ip_address("192.168.1.85"), output, 1.0, opener=opener
        )
        checks = (
            opener.requested_url == f"http://192.168.1.85{LOG_PATH}",
            output.read_bytes() == payload,
            result["bytes"] == len(payload),
            result["sha256"] == hashlib.sha256(payload).hexdigest(),
            result["read_only"] is True,
        )
    if all(checks):
        print("Self-test passed.")
        return 0
    print("Self-test failed.")
    return 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if args.ip is None:
        parser.error("Provide the customer-supplied private speaker IP.")
    output = args.output or Path(
        f"lithe-speaker-log-{datetime.now().astimezone():%Y%m%d-%H%M%S}.txt"
    )
    try:
        result = download(args.ip, output, args.timeout)
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        message = {"status": "failed", "reason": str(exc), "read_only": True}
        if args.json:
            print(json.dumps(message, indent=2))
        else:
            print(f"Log download failed: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Downloaded {result['file']} ({result['bytes']} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
