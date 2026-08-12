# Layered Diagnostic and Correlation Model

Run every applicable layer in order. Record **Pass**, **Concern**, or **Evidence unavailable** for each layer. A pass at one layer never proves later layers are healthy.

## Required order

1. **Basic connectivity** - current reachability, loss, latency, route and safe TCP response.
2. **DHCP/IP** - current address, lease stability, reservation, conflicts, renew failures and address changes.
3. **RF** - serving band/AP, RSSI, retries, drops, channel use and physical path.
4. **Multicast/mDNS** - phone and speaker LAN/VLAN, guest/client isolation, multicast controls and Lithe app discovery.
5. **AP behaviour** - roaming, BSSID/AP changes, DFS/channel changes, re-association, AP load and backhaul interruption.
6. **Cast/service behaviour** - AirPlay, Spotify Connect, Lithe app, playback and the approved service-health check.
7. **Speaker logs** - official log coverage, timestamp alignment, DHCP, disconnect, timeout, discovery, AP-change, reboot and watchdog events.
8. **Correlation engine** - rank time-aligned evidence and state the probable root cause, confidence, smoking-gun status and smallest targeted fix.

## Required check matrix

Establish each item from a named source. Use a red flag only for proven high-impact evidence, an amber flag for a risk requiring correlation, and **Evidence unavailable** when it was not measured.

| Check | Establish | Flag condition |
|---|---|---|
| DHCP lease stability | IP, server, subnet, gateway, duration, renew/rebind and address history | Red: address change, renewal/rebind failure or dropout |
| Duplicate IP | ARP identity and conflict evidence for the speaker IP | Red: identity changes or conflict evidence |
| Multiple DHCP servers | Authoritative DHCP/log/capture evidence of responders | Red: more than one unintended responder |
| Gateway stability | Speaker-reported or AP-observed gateway reachability | Red: loss at the fault |
| Subnet consistency | Speaker, controller and gateway subnet/VLAN | Red: unintended mismatch |
| DNS health | Resolver response and latency | Amber: failure or excessive latency; do not use DNS to explain local-only discovery without evidence |
| Band and SSID mode | Speaker/controller band and 2.4-only, split 2.4/5, combined 2.4/5, or combined 2.4/5/6 mode | Information; amber only when steering correlates with the fault |
| 2.4 GHz width/channel | 20/40 MHz and channel plan | Amber: 40 MHz or poor plan |
| Channel overlap/AP density | Same/overlapping channels and audible AP count | Red: severe overlap; amber: excess density |
| RSSI/retries | Signal plus retries/retransmissions | Red: poor signal or high retries |
| AP roaming/policy | AP changes, lock target, minimum RSSI, 802.11r/k/v | Red: frequent changes; amber: aggressive or unsuitable policy |
| Client isolation | Local client communication policy | Red: blocks required local communication |
| mDNS UDP 5353 | Discovery across the actual controller/speaker bands and VLANs | Red: required discovery fails |
| IGMP/multicast | Snooping, querier where required, reachability and multicast-to-unicast enhancement | Red: required path absent; amber: configuration risk |
| VLAN relationship | Controller/speaker VLAN and allowed discovery path | Red: blocked path; amber: intentional routed design needing proof |
| Wired topology | Router, switch chain, APs, backhaul, STP/RSTP and switch errors | Red: failure-window topology event, CRC errors or drops |
| WAN vs LAN | Whether Internet, LAN, Wi-Fi or only the speaker service failed | Diagnostic classification |
| Cast and reconnect history | Cast endpoints plus Wi-Fi, DHCP and Cast reconnect timestamps | Red: failure-window reconnect sequence |
| Latency/jitter/bursts | Minimum, average, maximum, jitter and 1-10 second loss bursts | Red: excessive or fault-aligned |

Never report **None detected** unless the evidence source was capable of detecting the condition over the relevant window. Prefer **Not observed in [source/window]**.

## Dual-band test

Ask or detect the network mode after the first live test and during Read mode:

1. 2.4 GHz only;
2. separate 2.4 and 5 GHz SSIDs;
3. combined 2.4/5 GHz SSID;
4. combined 2.4/5/6 GHz SSID.

Record controller and speaker independently. Different bands are acceptable when they share the intended subnet/VLAN and cross-band mDNS works.

```text
Speaker: 2.4 GHz
Controller: 5 GHz
Same subnet: Yes
mDNS between bands: Pass
Client isolation: Pass
Multicast discovery: Pass
Result: Pass
```

If the same-subnet cross-band mDNS test fails, report **RED - HIGH PROBABILITY NETWORK CONFIGURATION ISSUE**. Do not warn merely because the devices use different bands.

## DHCP health block

Show the fields rather than a bare pass/fail:

```text
DHCP HEALTH
DHCP server: [address/source]
Speaker IP: [private address]
Subnet: [mask/prefix]
Gateway: [address]
Lease duration: [duration]
Renew/rebind: [result]
Duplicate IP: [result and evidence window]
Multiple DHCP servers: [result and evidence window]
ARP identity stable: [Yes/No/Unavailable]
Gateway loss: [speaker/AP reported value or Unavailable]
IP change observed: [Yes/No/Unavailable]
Result: [Pass/Concern/Evidence unavailable]
```

## Topology assessment

Build the smallest evidence-backed topology, including switch hops and wired or wireless backhaul. Do not infer that wired backhaul is healthy.

Report separately:

- Physical topology: Pass/Concern/Unavailable;
- DHCP topology: Pass/Concern/Unavailable;
- Multicast topology: Pass/Concern/Unavailable;
- RF topology: Pass/Concern/Unavailable;
- Cast discovery: Pass/Concern/Unavailable.

Correlate STP/RSTP changes, switch CRC/errors/drops, AP backhaul events and speaker reconnects to the same fault window.

Do not skip DHCP/IP, RF, multicast/mDNS, AP or cast checks merely because ping succeeds. If router/AP access or a measurement is unavailable, mark that layer **Evidence unavailable** and name the missing proof.

## Evidence input

Create a small local JSON file containing only evidence for the supplied speaker. Do not include credentials or unrelated clients.

```json
{
  "dhcp": {
    "server_ip": "192.168.1.1",
    "subnet": "255.255.255.0",
    "gateway": "192.168.1.1",
    "lease_duration": "24 hours",
    "lease_stable": true,
    "reservation": false,
    "renewal_failure_at_fault": false,
    "address_changed_at_fault": false,
    "conflict": false,
    "multiple_servers": false,
    "arp_identity_stable": true,
    "gateway_loss_percent": 0,
    "subnet_consistent": true,
    "dns_healthy": true,
    "dns_latency_ms": 12
  },
  "rf": {
    "speaker_band": "2.4 GHz",
    "controller_band": "5 GHz",
    "network_mode": "combined_2_4_5",
    "rssi_dbm": -67,
    "retries_percent": 8,
    "disconnects_at_fault": false,
    "channel_width_mhz": 20,
    "channel_overlap": "low",
    "audible_ap_count": 3,
    "frequent_ap_roaming": false
  },
  "discovery": {
    "same_lan": true,
    "lithe_app_visible": false,
    "cross_band_mdns": true,
    "client_isolation": false,
    "multicast_blocked": false
  },
  "ap": {
    "ap_changed_at_fault": false,
    "dfs_or_channel_change_at_fault": false,
    "backhaul_interruption_at_fault": false,
    "stp_event_at_fault": false,
    "switch_port_errors": false,
    "band_steering": true,
    "ap_lock_enabled": false,
    "ap_lock_best_ap": null,
    "minimum_rssi_dbm": null,
    "fast_roaming_80211r": false,
    "steering_80211kv": true
  },
  "multicast": {
    "igmp_snooping": true,
    "igmp_querier_required": false,
    "igmp_querier_present": null,
    "reachability": true,
    "multicast_to_unicast": false,
    "vlan_path_allowed": true
  },
  "cast": {
    "airplay_visible": true,
    "spotify_visible": true,
    "playback_success": true,
    "reconnect_at_fault": false
  },
  "topology": {
    "path": "Router > Switch > AP1 > Speaker",
    "physical": "pass",
    "dhcp": "pass",
    "multicast": "pass",
    "rf": "pass",
    "cast": "pass"
  },
  "failure_scope": "speaker_service_only",
  "timeline": [
    {"timestamp": "14:31:05", "event": "dhcp_renew", "source": "speaker_log"},
    {"timestamp": "14:31:06", "event": "gateway_unreachable", "source": "speaker_log"},
    {"timestamp": "14:31:08", "event": "dhcp_ack", "source": "router_log"},
    {"timestamp": "14:31:09", "event": "cast_reconnect", "source": "cast_history"}
  ]
}
```

Use `null` or omit a value when it was not observed. Never convert unknown evidence into `false`.

## Run correlation

```powershell
python scripts/correlate_diagnostics.py `
  --network-json network.json `
  --service-json services.json `
  --log-json log-analysis.json `
  --evidence-json layer-evidence.json `
  --output correlation.json
```

Omit an unavailable input rather than inventing values.

## Confidence rules

- **Confirmed:** a failure-window speaker-log event directly explains the fault and at least one independent live/router/AP observation corroborates it.
- **Likely:** at least two independent sources support the same cause, but the confirmed standard is not met.
- **Possible:** one relevant source or ambiguous evidence supports the cause.
- **Undetermined:** evidence is missing, contradictory or below the threshold.

Use **Smoking gun: Yes** only for a Confirmed cause. A probable root cause may be Likely without being a smoking gun.

## Customer checkpoint

Before Write mode, show:

```text
Layer results:
- Basic connectivity: [Pass/Concern/Unavailable] - [evidence]
- DHCP/IP: ...
- RF: ...
- Multicast/mDNS: ...
- AP behaviour: ...
- Cast/services: ...
- Speaker logs: ...

Probable root cause: [cause or Undetermined]
Confidence: [Confirmed/Likely/Possible/Undetermined]
Smoking gun: [Yes/No]
Why: [short correlated evidence chain]
Targeted fix: [one reversible action or next proof]
Expected improvement: [specific expected outcome]
```

Never use **product fault** as a catch-all result. Name the failed subsystem, or state that the evidence is insufficient.
