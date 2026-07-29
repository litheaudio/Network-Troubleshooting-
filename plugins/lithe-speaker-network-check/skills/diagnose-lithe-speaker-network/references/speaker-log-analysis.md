# Speaker and Network Log Analysis

Analyse only customer-provided logs or logs visible through an official, supported Lithe Audio or router interface. Obtain permission first. Do not probe undocumented endpoints or expose proprietary implementation details.

## Prepare the evidence

1. Ask for the customer's local timezone and the best known failure window.
2. Confirm which speaker the log belongs to using only the supplied private IP or a masked MAC.
3. Limit review to the smallest useful time window, normally 15 minutes before and after the fault.
4. Redact credentials, tokens, public IPs, full MAC addresses, emails, usernames, unrelated clients, and internal endpoint paths.
5. Check timestamp continuity and note clock resets or missing intervals.

## Evidence patterns

| Pattern near the failure time | Interpretation | Corroborate with |
|---|---|---|
| DHCP discover/request repeats, lease loss, address change, duplicate-IP warning | DHCP churn or address conflict | Router lease history, reservation state, old/new IP |
| Wi-Fi deauthentication, disassociation, authentication failure, repeated reconnect | Radio loss, roaming, security handshake, or AP steering | RSSI, retries, AP changes, channel events |
| Packet loss, retransmit, socket timeout, connection timeout | Connectivity interruption | Ping loss/latency, AP retry/drop counters |
| Gateway unreachable, ARP failure, no route | Local path or VLAN/isolation problem | Selected source route, LAN/VLAN, client isolation |
| Reboot, watchdog, boot sequence, uptime reset | Speaker restarted | Power event, router offline history, timestamp gap |
| DNS or NTP failures only | Supporting evidence, not proof of audio failure | General internet outage, clock jump, gateway state |
| Multicast/discovery join failure while IP remains reachable | Local discovery blocked | Guest network, VLAN, multicast or client isolation |
| AP/channel change at the same time as audio interruption | Roaming or RF event | Connected AP history, channel/DFS event, RSSI |

## Smoking-gun standard

Call evidence **confirmed** only when:

- the event time overlaps the reported failure;
- it belongs to the affected speaker;
- the event directly explains loss of reachability, address, association, restart, or discovery; and
- another observation supports it when available.

Use **likely** when two or more independent observations align but a direct failure event is absent. Use **possible** for a single ambiguous warning.

Do not infer causation from ordinary startup messages, historic warnings outside the failure window, one timeout without customer impact, or a clean short sample.

## Customer explanation

Explain evidence in this order:

1. **What happened:** the shortest safe description of the event.
2. **When:** customer-local time and relation to the reported dropout.
3. **Meaning:** plain-language impact.
4. **Confidence:** confirmed, likely, or possible.
5. **Next proof:** one check that would confirm or reject the cause.
6. **Smallest fix:** one reversible action tied to the evidence.

Never paste a large raw log into chat or a report. Preserve only redacted event summaries and measurements needed for support.
