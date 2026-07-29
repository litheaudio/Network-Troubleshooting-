# Speaker, Router and Access-Point Evidence

Use only customer-authorised logs, official supported interfaces and the supplied private speaker IP. Do not probe hidden endpoints or expose proprietary details.

## Acquire evidence

After the five-question intake and live target check, ask one read-only permission checkpoint.

When browser or computer control is available:

1. Open the customer-approved official speaker, router, access-point or mesh interface.
2. Let the customer enter credentials and MFA.
3. Search directly for the supplied speaker IP.
4. Avoid recording unrelated client details.
5. Open only supported event, diagnostics or support-log views.
6. Restrict the time window to 15 minutes before and after the reported fault when possible.
7. Record the current/historical serving AP, band, RSSI, retries, drops, roaming, backhaul and DHCP state when shown.

If no supported log view is visible, guide the customer to export the official support log. Never guess a URL or call an undocumented log endpoint.

## Run local analysis

Use:

```powershell
python scripts/analyze_speaker_logs.py speaker.log `
  --failure-time "2026-07-29 14:30:00" `
  --timezone "Europe/London" `
  --json
```

The analyser:

- reads local files only;
- scans no device or network;
- emits category counts and timestamps rather than raw lines;
- identifies DHCP, Wi-Fi disconnect, timeout/loss, route/gateway, reboot/watchdog, discovery and roaming/AP-change patterns;
- separates events inside the selected failure window from unrelated history;
- does not declare a root cause automatically.

## Correlate evidence

| Pattern near the failure | Meaning to test | Corroborate with |
|---|---|---|
| DHCP renew/lease failure, address change or conflict | DHCP churn or duplicate address | Router lease history and reservation |
| Deauthentication, disassociation or reconnect | Radio loss, steering or roaming | Serving AP, RSSI, retries and AP change |
| Timeout, retransmit or packet loss | Connectivity interruption | Ping loss and AP retry/drop counters |
| Gateway unreachable, ARP failure or no route | Local path, VLAN or isolation issue | Gateway, LAN/VLAN and client isolation |
| Reboot, watchdog or uptime reset | Speaker restarted | Uptime, power history and timestamp gap |
| Discovery or multicast failure while IP remains reachable | Local discovery blocked | Guest network, VLAN and multicast controls |
| Roam, BSSID/AP or channel change | AP steering, RF or DFS event | AP history, backhaul, channel and RSSI |

## Confidence standard

Use **Confirmed** only when the event:

- belongs to the affected speaker;
- overlaps the reported failure;
- directly explains lost address, association, reachability, restart or discovery; and
- has corroborating evidence when available.

Use **Likely** when at least two independent observations align. Use **Possible** for one ambiguous event.

Do not call startup messages, old warnings, one timeout outside the failure window or a clean short sample a smoking gun.

## Customer result

Report:

1. measured live loss and latency;
2. the shortest redacted event summary;
3. serving access-point evidence;
4. confidence;
5. one next proof;
6. one smallest reversible fix.

Never paste complete logs, credentials, public IPs, full MAC addresses, unrelated clients or internal paths into chat or a support report.
