#!/usr/bin/env python3
"""Correlate redacted Lithe diagnostic evidence without contacting any device."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


MAX_BYTES = 5 * 1024 * 1024

CAUSES = {
    "dhcp_ip": {
        "label": "DHCP/IP lease instability or address conflict",
        "fix": "Create or correct a router-side DHCP reservation after checking for duplicate use.",
        "benefit": "Keep the speaker on one conflict-free address across lease renewals.",
    },
    "rf": {
        "label": "Weak or unstable Wi-Fi radio path",
        "fix": "Improve the speaker-to-AP path or serving AP/channel using the measured RF evidence.",
        "benefit": "Reduce retries, packet loss and audio interruptions.",
    },
    "multicast_mdns": {
        "label": "Multicast/mDNS discovery path blocked",
        "fix": "Place phone and speaker on the same permitted LAN and correct the proven isolation or multicast control.",
        "benefit": "Restore reliable discovery in the Lithe Audio app without changing general Internet access.",
    },
    "ap_behavior": {
        "label": "Access-point roaming, channel or backhaul interruption",
        "fix": "Correct the evidenced AP steering, DFS/channel or backhaul condition for this stationary speaker.",
        "benefit": "Prevent AP-driven reassociation and connectivity gaps.",
    },
    "cast_service": {
        "label": "Speaker control/discovery service stalled while cast services remained available",
        "fix": "Preserve the logs and follow the product-specific recovery or firmware escalation path.",
        "benefit": "Restore Lithe app/control service availability while preserving causal evidence.",
    },
    "speaker_restart": {
        "label": "Speaker reboot or watchdog restart",
        "fix": "Preserve the timestamped log and escalate the reboot/watchdog evidence before broad network changes.",
        "benefit": "Target the restart cause and avoid unnecessary router changes.",
    },
    "basic_connectivity": {
        "label": "Current IP connectivity degradation",
        "fix": "Use RF, DHCP and AP evidence to correct the source of the measured loss or latency.",
        "benefit": "Improve current reachability and reduce packet loss or delay.",
    },
    "wired_topology": {
        "label": "Wired topology, switch-port or AP-backhaul interruption",
        "fix": "Correct the failure-window switch, STP/RSTP, port-error or backhaul condition.",
        "benefit": "Restore a stable LAN path between the router, AP and speaker.",
    },
    "subnet_gateway": {
        "label": "Controller, speaker or gateway subnet/VLAN mismatch",
        "fix": "Correct the intended subnet/VLAN relationship and allow only the required local discovery path.",
        "benefit": "Restore local control and discovery between the controller and speaker.",
    },
    "dns": {
        "label": "DNS response failure or excessive latency",
        "fix": "Correct the evidenced resolver or upstream DNS issue without changing local multicast settings.",
        "benefit": "Improve cloud-service name resolution and startup reliability.",
    },
}


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f"Input exceeds 5 MB: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def value(data: dict[str, Any], section: str, key: str) -> Any:
    block = data.get(section)
    return block.get(key) if isinstance(block, dict) else None


def add(candidates: dict[str, dict[str, Any]], cause: str, weight: int, source: str,
        detail: str, at_fault: bool = False, log_smoking_gun: bool = False) -> None:
    item = candidates.setdefault(cause, {
        "cause": cause, "score": 0, "sources": set(), "evidence": [],
        "at_fault": False, "log_smoking_gun": False,
    })
    item["score"] += weight
    item["sources"].add(source)
    item["evidence"].append(detail)
    item["at_fault"] = item["at_fault"] or at_fault
    item["log_smoking_gun"] = item["log_smoking_gun"] or log_smoking_gun


def layer(status: str, evidence: str) -> dict[str, str]:
    return {"status": status, "evidence": evidence}


def check(status: str, flag: str, evidence: str) -> dict[str, str]:
    return {"status": status, "flag": flag, "evidence": evidence}


def timeline_seconds(timestamp: str) -> int | None:
    for pattern in ("%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = dt.datetime.strptime(timestamp, pattern)
            return parsed.hour * 3600 + parsed.minute * 60 + parsed.second
        except ValueError:
            continue
    return None


def correlate(network: dict[str, Any], services: dict[str, Any], logs: dict[str, Any],
              observed: dict[str, Any]) -> dict[str, Any]:
    candidates: dict[str, dict[str, Any]] = {}
    layers: dict[str, dict[str, str]] = {}

    ping = network.get("ping") if isinstance(network.get("ping"), dict) else {}
    status = str(network.get("status", "unknown")).lower()
    loss = ping.get("loss_percent")
    average = ping.get("average_ms")
    maximum = ping.get("maximum_ms")
    if status in {"healthy", "icmp_blocked"}:
        layers["basic_connectivity"] = layer("Pass", f"Live status {status}; this sample does not prove later layers healthy.")
    elif status in {"degraded", "unreachable", "route_warning"}:
        layers["basic_connectivity"] = layer("Concern", f"Live status {status}; loss={loss}, average_ms={average}, maximum_ms={maximum}.")
        add(candidates, "basic_connectivity", 2, "live_network", f"Live network status was {status}.")
    else:
        layers["basic_connectivity"] = layer("Evidence unavailable", "No trustworthy live connectivity classification.")

    dhcp_signals = []
    for key, text in [
        ("renewal_failure_at_fault", "DHCP renewal failed at the fault"),
        ("address_changed_at_fault", "speaker address changed at the fault"),
        ("conflict", "address conflict was reported"),
    ]:
        if value(observed, "dhcp", key) is True:
            dhcp_signals.append(text)
            add(candidates, "dhcp_ip", 3, "router_dhcp", text, at_fault=key.endswith("at_fault"))
    if dhcp_signals:
        layers["dhcp_ip"] = layer("Concern", "; ".join(dhcp_signals))
    elif value(observed, "dhcp", "lease_stable") is True:
        layers["dhcp_ip"] = layer("Pass", "Router evidence shows a stable current lease; historical churn still requires the fault window.")
    else:
        layers["dhcp_ip"] = layer("Evidence unavailable", "Lease, renewal, conflict and address-change history was not available.")

    rf_signals = []
    rssi = value(observed, "rf", "rssi_dbm")
    retries = value(observed, "rf", "retries_percent")
    if isinstance(rssi, (int, float)) and rssi <= -70:
        rf_signals.append(f"RSSI {rssi} dBm")
        add(candidates, "rf", 2, "ap_rf", f"RSSI was {rssi} dBm.")
    if isinstance(retries, (int, float)) and retries >= 15:
        rf_signals.append(f"retries {retries}%")
        add(candidates, "rf", 2, "ap_rf", f"Retry rate was {retries}%.")
    if value(observed, "rf", "disconnects_at_fault") is True:
        rf_signals.append("radio disconnect at the fault")
        add(candidates, "rf", 3, "ap_history", "Radio disconnect aligned with the fault.", at_fault=True)
    if rf_signals:
        layers["rf"] = layer("Concern", "; ".join(rf_signals))
    elif rssi is not None or retries is not None:
        layers["rf"] = layer("Pass", f"No threshold concern in available RF sample; RSSI={rssi}, retries={retries}.")
    else:
        layers["rf"] = layer("Evidence unavailable", "RSSI, retries and failure-window disconnect data were not available.")

    same_lan = value(observed, "discovery", "same_lan")
    app_visible = value(observed, "discovery", "lithe_app_visible")
    isolation = value(observed, "discovery", "client_isolation")
    multicast_blocked = value(observed, "discovery", "multicast_blocked")
    if isolation is True or multicast_blocked is True or same_lan is False:
        details = "Discovery path has different LAN/VLAN, isolation or multicast blocking evidence."
        layers["multicast_mdns"] = layer("Concern", details)
        add(candidates, "multicast_mdns", 3, "router_discovery", details)
    elif same_lan is True and app_visible is True:
        layers["multicast_mdns"] = layer("Pass", "Phone and speaker share the LAN and the Lithe app currently discovers the speaker.")
    elif app_visible is False:
        layers["multicast_mdns"] = layer("Concern", "The Lithe app cannot discover a currently addressed speaker; multicast controls need proof.")
        add(candidates, "multicast_mdns", 1, "customer_app", "Lithe app discovery failed while an address was available.")
    else:
        layers["multicast_mdns"] = layer("Evidence unavailable", "LAN/VLAN, isolation, multicast and app-discovery evidence was incomplete.")

    ap_signals = []
    for key, text in [
        ("ap_changed_at_fault", "serving AP changed at the fault"),
        ("dfs_or_channel_change_at_fault", "DFS or channel change aligned with the fault"),
        ("backhaul_interruption_at_fault", "AP backhaul interruption aligned with the fault"),
    ]:
        if value(observed, "ap", key) is True:
            ap_signals.append(text)
            add(candidates, "ap_behavior", 3, "ap_history", text, at_fault=True)
    if ap_signals:
        layers["ap_behavior"] = layer("Concern", "; ".join(ap_signals))
    elif any(value(observed, "ap", key) is not None for key in ["ap_changed_at_fault", "dfs_or_channel_change_at_fault", "backhaul_interruption_at_fault"]):
        layers["ap_behavior"] = layer("Pass", "No AP change, DFS/channel event or backhaul interruption was shown in the supplied fault window.")
    else:
        layers["ap_behavior"] = layer("Evidence unavailable", "Serving-AP, channel and backhaul history was not available.")

    airplay = value(observed, "cast", "airplay_visible")
    spotify = value(observed, "cast", "spotify_visible")
    playback = value(observed, "cast", "playback_success")
    web = services.get("root_web_health") if isinstance(services.get("root_web_health"), dict) else {}
    web_status = web.get("status")
    if (airplay is True or spotify is True) and app_visible is False and web_status in {"partial_or_stalled", "incomplete_headers", "listener_no_http_response", "no_listener"}:
        detail = f"Cast visibility remained while Lithe app discovery failed and web status was {web_status}."
        layers["cast_services"] = layer("Concern", detail)
        add(candidates, "cast_service", 3, "cast_observation", detail)
    elif playback is True or airplay is True or spotify is True:
        layers["cast_services"] = layer("Pass", "At least one cast/playback path was visible or working; this does not prove Lithe control services healthy.")
    elif web_status is not None or playback is not None or airplay is not None or spotify is not None:
        layers["cast_services"] = layer("Concern", f"No successful cast/playback evidence; root web status={web_status}.")
    else:
        layers["cast_services"] = layer("Evidence unavailable", "Cast visibility, playback and service-health evidence were not available.")

    analysis = logs.get("analysis", logs)
    findings = analysis.get("findings", []) if isinstance(analysis, dict) else []
    log_details = []
    category_map = {
        "dhcp": "dhcp_ip", "wifi_disconnect": "rf", "timeout_or_loss": "basic_connectivity",
        "discovery": "multicast_mdns", "roaming_or_ap_change": "ap_behavior",
        "reboot_or_watchdog": "speaker_restart",
    }
    for finding in findings if isinstance(findings, list) else []:
        if not isinstance(finding, dict):
            continue
        category = str(finding.get("category", "unknown"))
        mapped = category_map.get(category)
        if mapped:
            smoking = finding.get("smoking_gun_candidate") is True
            detail = f"Speaker log category {category}; events={finding.get('event_count', '?')}; failure-window candidate={smoking}."
            log_details.append(detail)
            add(candidates, mapped, 4 if smoking else 1, "speaker_log", detail, at_fault=smoking, log_smoking_gun=smoking)
    if log_details:
        layers["speaker_logs"] = layer("Concern", " ".join(log_details[:3]))
    elif logs:
        layers["speaker_logs"] = layer("Pass", "Usable log evidence contained no supported failure pattern in the analysed window.")
    else:
        layers["speaker_logs"] = layer("Evidence unavailable", "No usable speaker-log analysis was supplied.")

    checks: dict[str, dict[str, str]] = {}
    jitter = ping.get("jitter_ms")
    burst = ping.get("maximum_loss_burst_seconds")
    latency_concern = (
        status == "degraded"
        or (isinstance(jitter, (int, float)) and jitter > 20)
        or (isinstance(burst, (int, float)) and burst >= 1)
    )
    checks["latency_jitter_bursts"] = check(
        "Concern" if latency_concern else ("Pass" if ping else "Evidence unavailable"),
        "RED" if latency_concern else "INFO",
        f"loss={loss}, average_ms={average}, maximum_ms={maximum}, jitter_ms={jitter}, maximum_loss_burst_seconds={burst}",
    )

    duplicate = value(observed, "dhcp", "conflict")
    multiple = value(observed, "dhcp", "multiple_servers")
    arp_stable = value(observed, "dhcp", "arp_identity_stable")
    gateway_loss = value(observed, "dhcp", "gateway_loss_percent")
    subnet_consistent = value(observed, "dhcp", "subnet_consistent")
    dns_ok = value(observed, "dhcp", "dns_healthy")
    dns_latency = value(observed, "dhcp", "dns_latency_ms")
    if multiple is True:
        add(candidates, "dhcp_ip", 4, "dhcp_capture_or_logs", "More than one unintended DHCP responder was evidenced.", at_fault=True)
    if arp_stable is False:
        add(candidates, "dhcp_ip", 4, "arp_history", "ARP identity for the speaker IP changed.", at_fault=True)
    if isinstance(gateway_loss, (int, float)) and gateway_loss > 0:
        add(candidates, "basic_connectivity", 3, "speaker_or_ap_gateway", f"Gateway loss was {gateway_loss}%.", at_fault=True)
    if subnet_consistent is False:
        add(candidates, "subnet_gateway", 4, "addressing_evidence", "Controller, speaker or gateway subnet/VLAN mismatch was evidenced.")
    if dns_ok is False or (isinstance(dns_latency, (int, float)) and dns_latency > 100):
        add(candidates, "dns", 2, "dns_test", f"DNS healthy={dns_ok}; latency_ms={dns_latency}.")
    duplicate_concern = duplicate is True or arp_stable is False
    checks["duplicate_ip"] = check(
        "Concern" if duplicate_concern else ("Pass" if duplicate is False and arp_stable is True else "Evidence unavailable"),
        "RED" if duplicate_concern else "INFO",
        f"conflict={duplicate}; arp_identity_stable={arp_stable}",
    )
    checks["multiple_dhcp_servers"] = check(
        "Concern" if multiple is True else ("Pass" if multiple is False else "Evidence unavailable"),
        "RED" if multiple is True else "INFO",
        f"multiple_servers={multiple}; require authoritative logs or permitted capture",
    )
    checks["gateway_stability"] = check(
        "Concern" if isinstance(gateway_loss, (int, float)) and gateway_loss > 0 else ("Pass" if gateway_loss == 0 else "Evidence unavailable"),
        "RED" if isinstance(gateway_loss, (int, float)) and gateway_loss > 0 else "INFO",
        f"speaker/AP-reported gateway_loss_percent={gateway_loss}",
    )
    checks["subnet_consistency"] = check(
        "Concern" if subnet_consistent is False else ("Pass" if subnet_consistent is True else "Evidence unavailable"),
        "RED" if subnet_consistent is False else "INFO",
        f"subnet_consistent={subnet_consistent}",
    )
    dns_concern = dns_ok is False or (isinstance(dns_latency, (int, float)) and dns_latency > 100)
    checks["dns_health"] = check(
        "Concern" if dns_concern else ("Pass" if dns_ok is True else "Evidence unavailable"),
        "AMBER" if dns_concern else "INFO",
        f"healthy={dns_ok}; latency_ms={dns_latency}",
    )
    dhcp_health = {
        "dhcp_server": value(observed, "dhcp", "server_ip"),
        "speaker_ip": network.get("target_ip"),
        "subnet": value(observed, "dhcp", "subnet"),
        "gateway": value(observed, "dhcp", "gateway"),
        "lease_duration": value(observed, "dhcp", "lease_duration"),
        "renew_rebind": "Concern" if value(observed, "dhcp", "renewal_failure_at_fault") is True else ("Pass" if value(observed, "dhcp", "lease_stable") is True else "Evidence unavailable"),
        "duplicate_ip": checks["duplicate_ip"],
        "multiple_dhcp_servers": checks["multiple_dhcp_servers"],
        "arp_identity_stable": arp_stable,
        "gateway_loss_percent": gateway_loss,
        "ip_change_observed": value(observed, "dhcp", "address_changed_at_fault"),
        "result": layers["dhcp_ip"]["status"],
    }

    width = value(observed, "rf", "channel_width_mhz")
    overlap = value(observed, "rf", "channel_overlap")
    density = value(observed, "rf", "audible_ap_count")
    frequent_roam = value(observed, "rf", "frequent_ap_roaming")
    if width == 40:
        add(candidates, "rf", 1, "ap_config", "2.4 GHz channel width was 40 MHz.")
    if str(overlap).lower() == "severe":
        add(candidates, "rf", 3, "rf_scan", "Severe same/overlapping-channel interference was evidenced.")
    if frequent_roam is True:
        add(candidates, "ap_behavior", 3, "ap_history", "Stationary speaker changed AP frequently.", at_fault=True)
    rf_channel_concern = width == 40 or str(overlap).lower() == "severe"
    checks["rf_channel_plan"] = check(
        "Concern" if rf_channel_concern else ("Pass" if width is not None and overlap is not None else "Evidence unavailable"),
        "RED" if str(overlap).lower() == "severe" else ("AMBER" if width == 40 else "INFO"),
        f"2.4GHz_width_mhz={width}; overlap={overlap}; audible_ap_count={density}",
    )
    checks["rssi_retries"] = check(
        "Concern" if rf_signals else ("Pass" if rssi is not None or retries is not None else "Evidence unavailable"),
        "RED" if rf_signals else "INFO",
        f"rssi_dbm={rssi}; retries_percent={retries}",
    )

    speaker_band = value(observed, "rf", "speaker_band")
    controller_band = value(observed, "rf", "controller_band")
    network_mode = value(observed, "rf", "network_mode")
    cross_band_mdns = value(observed, "discovery", "cross_band_mdns")
    if speaker_band and controller_band and speaker_band != controller_band and same_lan is True and cross_band_mdns is False:
        detail = "Speaker and controller are on different bands in the same subnet, but cross-band mDNS failed."
        add(candidates, "multicast_mdns", 4, "cross_band_mdns_test", detail)
        layers["multicast_mdns"] = layer("Concern", detail)
        dual_result = "RED - HIGH PROBABILITY NETWORK CONFIGURATION ISSUE"
    elif speaker_band and controller_band and same_lan is True and cross_band_mdns is True:
        dual_result = "Pass"
    else:
        dual_result = "Evidence unavailable"
    dual_band = {
        "network_mode": network_mode,
        "speaker_band": speaker_band,
        "controller_band": controller_band,
        "same_subnet": same_lan,
        "cross_band_mdns": cross_band_mdns,
        "client_isolation": isolation,
        "multicast_discovery": app_visible,
        "result": dual_result,
    }
    checks["mdns_udp_5353"] = check(
        "Concern" if cross_band_mdns is False else ("Pass" if cross_band_mdns is True else "Evidence unavailable"),
        "RED" if cross_band_mdns is False else "INFO",
        f"cross_band_mdns={cross_band_mdns}; speaker_band={speaker_band}; controller_band={controller_band}; same_subnet={same_lan}",
    )

    stp = value(observed, "ap", "stp_event_at_fault")
    port_errors = value(observed, "ap", "switch_port_errors")
    if stp is True or port_errors is True:
        detail = f"Wired path concern: stp_event_at_fault={stp}; switch_port_errors={port_errors}."
        add(candidates, "wired_topology", 4, "switch_or_ap", detail, at_fault=stp is True)
    checks["wired_topology_events"] = check(
        "Concern" if stp is True or port_errors is True else ("Pass" if stp is False and port_errors is False else "Evidence unavailable"),
        "RED" if stp is True or port_errors is True else "INFO",
        f"stp_event_at_fault={stp}; switch_port_errors={port_errors}",
    )
    cast_reconnect = value(observed, "cast", "reconnect_at_fault")
    if cast_reconnect is True:
        add(candidates, "cast_service", 3, "cast_history", "Cast reconnected in the failure window.", at_fault=True)
    checks["cast_connectivity"] = check(
        "Concern" if cast_reconnect is True or layers["cast_services"]["status"] == "Concern" else ("Pass" if layers["cast_services"]["status"] == "Pass" else "Evidence unavailable"),
        "RED" if cast_reconnect is True else ("AMBER" if layers["cast_services"]["status"] == "Concern" else "INFO"),
        f"airplay={airplay}; spotify={spotify}; playback={playback}; reconnect_at_fault={cast_reconnect}; web={web_status}",
    )

    band_steering = value(observed, "ap", "band_steering")
    ap_lock = value(observed, "ap", "ap_lock_enabled")
    ap_lock_best = value(observed, "ap", "ap_lock_best_ap")
    minimum_rssi = value(observed, "ap", "minimum_rssi_dbm")
    roaming_r = value(observed, "ap", "fast_roaming_80211r")
    steering_kv = value(observed, "ap", "steering_80211kv")
    checks["band_steering"] = check("Review" if band_steering is True else ("Pass" if band_steering is False else "Evidence unavailable"), "AMBER" if band_steering is True else "INFO", f"enabled={band_steering}; correlate with speaker band/AP changes")
    checks["ap_lock"] = check("Concern" if ap_lock is True and ap_lock_best is False else ("Review" if ap_lock is True else ("Pass" if ap_lock is False else "Evidence unavailable")), "AMBER" if ap_lock is True else "INFO", f"enabled={ap_lock}; locked_to_best_ap={ap_lock_best}")
    aggressive_minimum = isinstance(minimum_rssi, (int, float)) and minimum_rssi >= -70
    checks["minimum_rssi"] = check("Review" if aggressive_minimum else ("Pass" if minimum_rssi is not None else "Evidence unavailable"), "AMBER" if aggressive_minimum else "INFO", f"minimum_rssi_dbm={minimum_rssi}")
    checks["roaming_80211r"] = check("Review" if roaming_r is True else ("Pass" if roaming_r is False else "Evidence unavailable"), "AMBER" if roaming_r is True else "INFO", f"enabled={roaming_r}; investigate only with roaming/reconnect evidence")
    checks["steering_80211kv"] = check("Information" if steering_kv is not None else "Evidence unavailable", "AMBER" if steering_kv is True and frequent_roam is True else "INFO", f"enabled={steering_kv}; frequent_ap_roaming={frequent_roam}")
    checks["client_isolation"] = check("Concern" if isolation is True else ("Pass" if isolation is False else "Evidence unavailable"), "RED" if isolation is True else "INFO", f"enabled={isolation}")

    igmp_snooping = value(observed, "multicast", "igmp_snooping")
    querier_required = value(observed, "multicast", "igmp_querier_required")
    querier_present = value(observed, "multicast", "igmp_querier_present")
    multicast_reachable = value(observed, "multicast", "reachability")
    multicast_enhancement = value(observed, "multicast", "multicast_to_unicast")
    vlan_allowed = value(observed, "multicast", "vlan_path_allowed")
    querier_missing = querier_required is True and querier_present is False
    checks["igmp_snooping"] = check("Information" if igmp_snooping is not None else "Evidence unavailable", "AMBER" if igmp_snooping is True else "INFO", f"enabled={igmp_snooping}; configuration requires topology correlation")
    checks["igmp_querier"] = check("Concern" if querier_missing else ("Pass" if querier_required is True and querier_present is True else "Not required" if querier_required is False else "Evidence unavailable"), "RED" if querier_missing else "INFO", f"required={querier_required}; present={querier_present}")
    checks["multicast_reachability"] = check("Concern" if multicast_reachable is False else ("Pass" if multicast_reachable is True else "Evidence unavailable"), "RED" if multicast_reachable is False else "INFO", f"reachable={multicast_reachable}")
    checks["multicast_enhancement"] = check("Review" if multicast_enhancement is True else ("Pass" if multicast_enhancement is False else "Evidence unavailable"), "AMBER" if multicast_enhancement is True else "INFO", f"multicast_to_unicast={multicast_enhancement}")
    checks["vlan_relationship"] = check("Concern" if vlan_allowed is False else ("Pass" if vlan_allowed is True else "Evidence unavailable"), "RED" if vlan_allowed is False else "INFO", f"required_local_discovery_path_allowed={vlan_allowed}")
    if multicast_reachable is False or querier_missing or vlan_allowed is False:
        add(candidates, "multicast_mdns", 3, "multicast_topology", f"Multicast topology concern: reachable={multicast_reachable}, querier_missing={querier_missing}, vlan_path_allowed={vlan_allowed}.")

    failure_scope = observed.get("failure_scope")
    checks["internet_lan_wifi_scope"] = check(
        "Classified" if failure_scope else "Evidence unavailable",
        "INFO",
        f"failure_scope={failure_scope}; distinguish WAN, LAN, Wi-Fi and speaker-service failure",
    )

    correlation_timeline: list[dict[str, Any]] = []
    timeline = observed.get("timeline")
    if isinstance(timeline, list):
        cleaned = []
        for event in timeline:
            if not isinstance(event, dict):
                continue
            seconds = timeline_seconds(str(event.get("timestamp", "")))
            name = str(event.get("event", ""))
            source = str(event.get("source", "unknown"))
            if seconds is not None and name:
                cleaned.append({"seconds": seconds, "timestamp": str(event.get("timestamp")), "event": name, "source": source})
        cleaned.sort(key=lambda item: item["seconds"])
        wanted = ["dhcp_renew", "gateway_unreachable", "dhcp_ack", "cast_reconnect"]
        matched = []
        cursor = 0
        for event in cleaned:
            if cursor < len(wanted) and event["event"] == wanted[cursor]:
                matched.append(event)
                cursor += 1
        if len(matched) == len(wanted) and matched[-1]["seconds"] - matched[0]["seconds"] <= 15:
            correlation_timeline = matched
            detail = " -> ".join(f"{item['timestamp']} {item['event']}" for item in matched)
            for source in sorted({item["source"] for item in matched}):
                add(candidates, "dhcp_ip", 2, source, detail, at_fault=True)

    ranked = sorted(candidates.values(), key=lambda item: (item["score"], len(item["sources"])), reverse=True)
    rendered = []
    for item in ranked[:3]:
        corroborated = len(item["sources"]) >= 2
        if item["log_smoking_gun"] and item["at_fault"] and corroborated:
            confidence = "Confirmed"
        elif corroborated and item["score"] >= 4:
            confidence = "Likely"
        else:
            confidence = "Possible"
        meta = CAUSES[item["cause"]]
        rendered.append({
            "cause": item["cause"], "label": meta["label"], "score": item["score"],
            "confidence": confidence, "smoking_gun": confidence == "Confirmed",
            "sources": sorted(item["sources"]), "evidence": item["evidence"][:4],
            "targeted_fix": meta["fix"], "expected_improvement": meta["benefit"],
        })

    if rendered:
        top = rendered[0]
        root = {
            "label": top["label"], "confidence": top["confidence"],
            "smoking_gun": top["smoking_gun"], "evidence": top["evidence"],
            "targeted_fix": top["targeted_fix"],
            "expected_improvement": top["expected_improvement"],
        }
    else:
        root = {
            "label": "Undetermined - insufficient correlated evidence",
            "confidence": "Undetermined", "smoking_gun": False,
            "evidence": ["No cause reached the minimum evidence threshold."],
            "targeted_fix": "Collect the missing failure-window layer evidence before changing settings.",
            "expected_improvement": "Avoid an unsupported change and identify the actual failing layer.",
        }

    topology = observed.get("topology") if isinstance(observed.get("topology"), dict) else {}
    topology_assessment = {
        "path": topology.get("path", "Evidence unavailable"),
        "physical_topology": topology.get("physical", "evidence_unavailable"),
        "dhcp_topology": topology.get("dhcp", layers["dhcp_ip"]["status"].lower().replace(" ", "_")),
        "multicast_topology": topology.get("multicast", layers["multicast_mdns"]["status"].lower().replace(" ", "_")),
        "rf_topology": topology.get("rf", layers["rf"]["status"].lower().replace(" ", "_")),
        "cast_discovery": topology.get("cast", layers["cast_services"]["status"].lower().replace(" ", "_")),
    }

    return {
        "layers": layers,
        "check_matrix": checks,
        "dhcp_health": dhcp_health,
        "dual_band_assessment": dual_band,
        "topology_assessment": topology_assessment,
        "correlated_timeline": correlation_timeline,
        "probable_root_cause": root,
        "ranked_candidates": rendered,
        "logic_note": "Basic connectivity is one layer only; a pass does not pass DHCP, RF, discovery, AP, cast or speaker services.",
    }


def run_self_test() -> int:
    network = {"status": "healthy", "ping": {"loss_percent": 0, "average_ms": 4, "maximum_ms": 8}}
    services = {"root_web_health": {"status": "partial_or_stalled"}}
    observed = {
        "dhcp": {"server_ip": "192.168.1.1", "lease_stable": True, "conflict": False, "multiple_servers": False, "arp_identity_stable": True, "gateway_loss_percent": 0, "subnet_consistent": True},
        "rf": {"speaker_band": "2.4 GHz", "controller_band": "5 GHz", "network_mode": "combined_2_4_5", "rssi_dbm": -62, "retries_percent": 4, "channel_width_mhz": 20, "channel_overlap": "low"},
        "discovery": {"same_lan": True, "lithe_app_visible": False, "cross_band_mdns": False, "client_isolation": False, "multicast_blocked": False},
        "ap": {"ap_changed_at_fault": False, "dfs_or_channel_change_at_fault": False, "backhaul_interruption_at_fault": False, "stp_event_at_fault": False, "switch_port_errors": False},
        "cast": {"airplay_visible": True, "spotify_visible": True, "playback_success": True, "reconnect_at_fault": False},
        "multicast": {"igmp_snooping": True, "igmp_querier_required": False, "reachability": False, "multicast_to_unicast": False, "vlan_path_allowed": True},
        "topology": {"path": "Router > Switch > AP > Speaker", "physical": "pass"},
        "failure_scope": "speaker_service_only",
        "timeline": [
            {"timestamp": "14:31:05", "event": "dhcp_renew", "source": "speaker_log"},
            {"timestamp": "14:31:06", "event": "gateway_unreachable", "source": "speaker_log"},
            {"timestamp": "14:31:08", "event": "dhcp_ack", "source": "router_log"},
            {"timestamp": "14:31:09", "event": "cast_reconnect", "source": "cast_history"},
        ],
    }
    logs = {"analysis": {"findings": [{"category": "discovery", "event_count": 2, "smoking_gun_candidate": True}]}}
    result = correlate(network, services, logs, observed)
    checks = [
        result["layers"]["basic_connectivity"]["status"] == "Pass",
        result["layers"]["multicast_mdns"]["status"] == "Concern",
        result["probable_root_cause"]["label"] != "Product fault",
        result["probable_root_cause"]["confidence"] in {"Confirmed", "Likely"},
        result["dual_band_assessment"]["result"] == "RED - HIGH PROBABILITY NETWORK CONFIGURATION ISSUE",
        "dhcp_server" in result["dhcp_health"],
        "physical_topology" in result["topology_assessment"],
        len(result["correlated_timeline"]) == 4,
        result["check_matrix"]["multicast_reachability"]["flag"] == "RED",
        "Basic connectivity is one layer only" in result["logic_note"],
    ]
    print("Self-test passed." if all(checks) else "Self-test failed.")
    return 0 if all(checks) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Correlate redacted Lithe diagnostic evidence locally.")
    parser.add_argument("--network-json", type=Path)
    parser.add_argument("--service-json", type=Path)
    parser.add_argument("--log-json", type=Path)
    parser.add_argument("--evidence-json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    try:
        result = correlate(load_json(args.network_json), load_json(args.service_json), load_json(args.log_json), load_json(args.evidence_json))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Cannot correlate diagnostics: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2)
    if args.output:
        if args.output.exists():
            print(f"Refusing to overwrite existing output: {args.output}", file=sys.stderr)
            return 3
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Saved correlation result: {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
