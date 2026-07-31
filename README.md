# Lithe Speaker Network Check

A privacy-focused Codex skill that helps customers diagnose Lithe Audio speaker dropouts, delays, disappearing speakers, DHCP problems, weak Wi-Fi, interference, mesh roaming, and local discovery issues.

Customers can choose guided self-service or supervised support. In supervised support, Codex can inspect the router through an available browser-control tool and make only the changes the customer explicitly approves.

## Key features

- Opens as a friendly Lithe Audio support conversation rather than a sample checklist.
- Requests the affected speaker IP, asks exactly five essential diagnostic questions, then starts real tests without extending the intake.
- Includes router, mesh, extender and serving access-point details, including location, band and backhaul when known.
- Checks one customer-provided private speaker IP address.
- Measures reachability, packet loss, minimum/average/maximum latency, and safe TCP response.
- Analyses customer-authorised speaker and router logs locally for time-correlated DHCP, Wi-Fi, timeout, packet-loss, reboot, roaming, access-point and discovery evidence.
- Distinguishes confirmed evidence from likely and possible causes instead of overstating a single log warning.
- Detects likely DHCP, VPN-routing, weak-signal, interference, roaming, access-point, and client-isolation problems.
- Asks about distance, walls, floors, brick, concrete, metal, cabinets, router placement, mesh nodes, and wireless backhaul.
- Provides plain-language, step-by-step fixes.
- Supports supervised router inspection when browser or computer-control tools are available.
- Requests separate permission before inspection, each settings change, and each restart.
- Creates a redacted local Markdown report for support.
- Retests after every approved change and loops back according to the customer's feedback: resolved, improved, unchanged, or worse.
- Uses Python's standard library only.

## Privacy and safety

The skill is deliberately limited to local home-network diagnostics.

- It accepts only private IPv4 ranges: `10.0.0.0/8`, `172.16.0.0/12`, and `192.168.0.0/16`.
- It checks only the IP supplied by the customer.
- It does not scan the subnet or enumerate unrelated devices.
- It does not call or reveal an internal or undocumented Lithe API.
- It does not send HTTP requests to the speaker.
- It does not upload diagnostic data.
- It masks full MAC addresses in support reports.
- It redacts likely passwords, tokens, public IPs, usernames, emails, and recovery codes.
- It never asks the customer to paste or dictate router credentials.

When router login is required, the customer types their password and completes MFA directly in the router page. Codex must pause while this happens and must never record or repeat the credentials.

## Requirements

- Codex with support for local skills.
- Python 3.10 or newer.
- A Windows, macOS, or Linux computer connected to the same home network as the speaker.
- The speaker's private IP address from the Lithe Audio app.
- Optional: browser or computer-control tools for supervised router support.

No third-party Python packages are required by the diagnostic scripts.

## Installation

### Recommended: install directly in Codex

Open a new Codex task and type:

```text
Use $skill-installer to install the skill from:
https://github.com/litheaudio/Network-Troubleshooting-/tree/main/plugins/lithe-speaker-network-check/skills/diagnose-lithe-speaker-network
```

After Codex confirms installation, start a new task and type:

```text
Help me diagnose my Lithe Audio speaker.
```

Codex will start the real customer-support workflow, ask for the affected speaker's private IP address and then ask five short diagnostic questions one at a time before running the checks.

### Alternative: install the Lithe Audio plugin

The plugin contains the diagnostic skill and provides a live-support starter prompt in plugin surfaces that support custom starters.

Lithe Audio should publish or share the validated [lithe-speaker-network-check-plugin-v1.5.1.zip](lithe-speaker-network-check-plugin-v1.5.1.zip) as a plugin. The customer installs **Lithe Speaker Network Check** from the supplied plugin link, then selects **Try in chat**.

Some Codex and ChatGPT installation screens insert this platform-owned draft:

```text
I just added the “diagnose-lithe-speaker-network” skill. Let's explore
what it does with an example. Make up a realistic user prompt and then
use the full Skill end to end.
```

That draft is not supplied by the Lithe Audio skill and cannot be replaced by `SKILL.md` or the plugin manifest. It is still in the message composer and has not run yet.

The customer may send the draft as shown. The skill recognises it as a first-run launcher, ignores the request to invent an example, and starts the real customer workflow. Alternatively, replace the draft with:

```text
Start my live Lithe Audio speaker and network support session.
```

After the message is sent, the first response greets the customer as their Lithe Audio helper and asks for the affected speaker IP. It then asks exactly five diagnostic questions one at a time, waiting for each answer before running the target-only checks.

There are no API keys or Lithe Audio account credentials to enter.

For local development from this repository:

```text
codex plugin marketplace add <path-to-this-repository>
codex plugin add lithe-speaker-network-check@lithe-audio
```

Start a new Codex task after installing or updating the plugin.

If an older installation still shows all five questions together, remove the existing skill or plugin from Codex, install the current version again, and start a new task. Already-open tasks may retain the earlier skill instructions.

### Standalone skill fallback

The standalone [diagnose-lithe-speaker-network-v1.5.1.zip](diagnose-lithe-speaker-network-v1.5.1.zip) remains available for environments that install only individual skills. Its diagnostic workflow is the same. The surrounding product may supply its own generic **Try in chat** draft; the installed skill handles that draft only after it is sent.

If **Install** or **Plugins** is unavailable, ask the Codex workspace administrator to enable plugin installation.

## Find the speaker IP address

The exact labels may vary by app version:

1. Open the Lithe Audio app.
2. Open **Settings**.
3. Select the affected speaker or zone.
4. Open its network or device information.
5. Copy the **IP address**, normally similar to `192.168.1.45`.

The computer running Codex must be connected to the same home network. Disconnect VPN software and avoid guest Wi-Fi before testing.

## Use the skill

Start a Codex task with:

```text
Use $diagnose-lithe-speaker-network to help me with a Lithe Audio
speaker problem as a friendly support specialist.
```

The skill starts a live support conversation and helps the customer find the speaker IP in **Lithe Audio app > Settings > affected speaker > device or network information**. Once the IP is validated, it asks exactly five questions covering the symptom, timing, affected devices, router/access-point path and physical Wi-Fi path. It then runs real measurements.

If the IP is already known:

```text
Use $diagnose-lithe-speaker-network to help with my speaker at
192.168.1.45. It drops out about once a week.
```

The skill offers two modes:

| Mode | What happens |
|---|---|
| **Guide me** | Codex explains each router or Wi-Fi step for the customer to complete. |
| **Supervised support** | With permission, Codex inspects the customer-opened router page and performs only separately approved changes. |

The customer can say **stop** at any time.

## What the skill checks

| Check | What it helps identify |
|---|---|
| Private-IP validation | Incorrect, public, or unsupported addresses |
| Targeted ping sample | Reachability, packet loss, and latency |
| Selected local source | VPN or incorrect network routing |
| Target-only neighbour lookup | Local device presence with a masked MAC |
| TCP connection to ports 80 and 443 | A reachable device when ICMP/ping is blocked |
| DHCP evidence | Changing addresses, lease problems, or conflicts |
| Signal and RSSI | Weak Wi-Fi coverage |
| Retry and drop rates | Interference or access-point congestion |
| Band, channel, and width | Unstable 2.4 GHz or 5 GHz configuration |
| AP or mesh association | Poor roaming or an unsuitable AP lock |
| Isolation and discovery | A reachable speaker missing from the app |
| Physical environment | Walls, floors, metal, cabinets, and placement problems |

## Result meanings

- **Healthy:** the speaker responds with no measured loss and stable local latency.
- **Degraded:** the test found packet loss, average latency above 50 ms, or spikes above 100 ms.
- **ICMP blocked:** ping failed but a safe TCP connection succeeded; the speaker may still be online.
- **Unreachable:** neither ping nor the safe TCP checks responded.
- **Route warning:** the computer may be using a VPN or an unexpected network route.

A healthy short test cannot completely rule out a weekly or intermittent fault. The skill continues with DHCP history and router evidence when needed.

## Typical fixes

Depending on the evidence, the skill can guide or supervise:

- creating a router-side DHCP reservation;
- correcting a changed or conflicting speaker IP;
- improving access-point placement;
- selecting a stable 2.4 GHz channel with 20 MHz width;
- moving a speaker away from weak 5 GHz coverage;
- removing an unsuitable AP lock;
- disabling fast roaming for a speaker or IoT SSID;
- correcting guest or client-isolation settings;
- checking multicast/local-discovery controls;
- moving a speaker to a healthier access point.

The workflow does not enable remote administration, add port forwarding, disable the firewall, expose the speaker to the internet, or perform an early factory reset.

## Run the diagnostic script manually

From the skill directory:

```bash
python scripts/check_speaker_network.py 192.168.1.45 --count 10
```

For a longer intermittent-fault sample:

```bash
python scripts/check_speaker_network.py 192.168.1.45 --count 20
```

Structured output:

```bash
python scripts/check_speaker_network.py 192.168.1.45 --count 20 --json
```

Save a local diagnostic for a support report:

```bash
python scripts/check_speaker_network.py 192.168.1.45 \
  --count 20 \
  --save-json diagnostic.json
```

The script refuses to overwrite an existing saved diagnostic.

## Analyse an authorised speaker log

After exporting an official speaker support log or obtaining a customer-authorised router log, run:

```bash
python scripts/analyze_speaker_logs.py speaker.log \
  --failure-time "2026-07-29 14:30:00" \
  --timezone "Europe/London" \
  --json
```

The analyser reads local files only. It emits redacted event-category counts and timestamps for DHCP, Wi-Fi disconnects, timeouts/loss, gateway failures, reboots, discovery problems, roaming and access-point changes. It never uploads the log and does not automatically claim that an event is the root cause.

## Create a redacted support report

Create the diagnostic JSON first, then run:

```bash
python scripts/create_support_report.py \
  --diagnostic-json diagnostic.json \
  --output Lithe-Support-Report.md \
  --field "symptom=Speaker drops out weekly" \
  --field "frequency=About once a week" \
  --field "walls=Two brick walls" \
  --field "barriers=TV and metal equipment cabinet" \
  --field "router_model=Customer-provided router model" \
  --field "changes=Created a DHCP reservation" \
  --field "verification=20/20 replies and playback test passed"
```

Supported report fields:

```text
symptom
frequency
first_seen
router_model
network_type
access_point
band
signal_dbm
retries_percent
dhcp_reserved
distance_m
walls
floors
barriers
speaker_location
other_devices
changes
verification
customer_notes
```

The report remains on the local computer. The customer should review it before sending it to support.

## Supervised router support

Supervised support requires a Codex environment with suitable browser or computer-control tools.

The workflow is:

1. Explain the inspection scope and obtain permission.
2. Ask the customer to open the router's normal management page.
3. Pause while the customer types credentials and completes MFA.
4. Inspect relevant settings without changing them.
5. Explain the evidence, proposed change, expected interruption, and rollback.
6. Ask permission for that exact change.
7. Apply one reversible change.
8. Retest the speaker and record before-and-after results.
9. Repeat only when another change is justified and separately approved.
10. Create a redacted report if requested.

If browser control is unavailable, the skill falls back to guided instructions and support-report creation. It must never claim that it inspected or changed the router when it did not.

## Recommended success targets

- Packet loss: `0%`
- Average local latency: preferably below `20 ms`
- Large latency spikes: none above `100 ms`
- Wi-Fi signal: preferably `-67 dBm` or better
- Retry rate: preferably below `10%`
- DHCP reservation: enabled for the speaker

## Troubleshooting installation

If Codex does not detect the skill:

1. Confirm the folder is named `diagnose-lithe-speaker-network`.
2. Confirm `SKILL.md` is directly inside that folder.
3. Confirm the folder is under `.codex/skills`.
4. Restart Codex.
5. Invoke it explicitly with `$diagnose-lithe-speaker-network`.

If `python` is not found, install Python 3.10 or newer and ensure it is available on the system path.

## Repository structure

```text
diagnose-lithe-speaker-network/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── privacy-and-safety.md
│   ├── customer-conversation.md
│   ├── remediation.md
│   ├── speaker-log-analysis.md
│   ├── supervised-support.md
│   └── support-log.md
└── scripts/
    ├── analyze_speaker_logs.py
    ├── check_speaker_network.py
    └── create_support_report.py
```

## Important limitations

- The skill diagnoses local network conditions; it does not prove that every audio or firmware function is healthy.
- Router menus and available statistics vary by manufacturer.
- A weekly fault may require observation through the next normal DHCP lease cycle.
- Router changes can briefly disconnect devices.
- The customer remains responsible for authorising and reviewing changes made on their network.


