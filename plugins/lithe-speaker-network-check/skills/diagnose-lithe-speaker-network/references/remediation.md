# Step-by-Step Remediation

Choose the section that matches the measured evidence. Make one change, retest, and stop when the success targets are met.

## Decision Table

| Finding | Likely cause | First action |
|---|---|---|
| Speaker disappears every few days or weekly | DHCP lease or address conflict | Reserve its IP in DHCP |
| IP no longer appears in the router | Power, Wi-Fi join, or changed DHCP address | Check power and connected-device list |
| Loss above 0% or latency spikes above 100 ms | Weak/interfered Wi-Fi or overloaded AP | Improve signal and channel conditions |
| RSSI weaker than -73 dBm | Poor coverage | Move/add an access point or change placement |
| Retries above 20% | Interference, congestion, or problematic AP | Change channel or move the client |
| Good signal but high retries on one AP | AP radio issue or congestion | Test another AP; do not lock to the bad AP |
| Speaker moves between mesh nodes and audio pauses | Roaming instability | Disable fast roaming for the speaker SSID |
| App cannot discover a reachable speaker | Guest isolation or multicast blocking | Use the main LAN and permit local discovery |
| Ping fails but TCP responds | ICMP blocked | Verify the router client state; do not treat as offline |
| Diagnostic source route is unexpected | VPN or alternate adapter | Disconnect VPN and reconnect to home Wi-Fi |

## Reserve the Speaker IP with DHCP

Use this first for periodic disappearances, changed addresses, or address conflicts.

1. Open the router app or browse to the router's local management page.
2. Open **Connected devices**, **Clients**, or **Network map**.
3. Select the speaker matching the IP from the Lithe Audio app.
4. Choose **Reserve IP**, **Fixed IP**, **Static lease**, or **DHCP reservation**.
5. Keep the current IP when the router says it is available.
6. Confirm that the address is inside the router's LAN subnet and not already assigned to another device.
7. Save the change.
8. Restart only the speaker, or disconnect and reconnect it, so it renews the lease.
9. Confirm the router shows the same IP after reconnection.

Do not set a manual static address on the speaker unless the product documentation specifically requires it. Router-side DHCP reservation avoids duplicate addresses and is easier to manage.

## Improve Weak Wi-Fi

Use signal thresholds as guidance:

- `-30` to `-60 dBm`: strong;
- `-61` to `-67 dBm`: good;
- `-68` to `-73 dBm`: usable but watch for retries;
- weaker than `-73 dBm`: improve coverage;
- weaker than `-80 dBm`: unreliable for stable audio.

Steps:

1. Keep the access point in the open and away from metal, TVs, amplifiers, cabinets, and dense masonry.
2. Move the nearest access point closer or add a wired access point between the router and speaker.
3. Avoid adding an extra wireless repeater unless wired backhaul is impossible; each wireless hop can add delay.
4. Retest signal, loss, and latency.
5. Use an AP lock only after proving that AP has good signal and low retries.

Do not lock a speaker to an access point weaker than `-70 dBm` or one showing high radio retries/dropped packets.

## Reduce 2.4 GHz Interference

2.4 GHz is often more reliable through walls but is easily congested.

1. Set channel width to `20 MHz`.
2. Use channel `1`, `6`, or `11`.
3. Select the least congested of those channels using the router's channel scan if available.
4. Avoid automatic channel changes during the customer's normal listening hours when the router supports a schedule.
5. Retest after the access point returns online.

## Stabilise 5 GHz

5 GHz can provide lower latency but has shorter range.

1. Keep the speaker on 5 GHz only when signal is about `-67 dBm` or better and retries remain low.
2. If signal is weak through walls, allow 2.4 GHz or improve access-point placement.
3. Prefer stable non-DFS channels when unexplained channel changes cause interruptions.
4. Retest playback and the 20-ping sample.

## Fix Roaming Delays

Use this when a stationary speaker changes mesh nodes or pauses during reassociation.

1. Open the Wi-Fi network's advanced settings.
2. Turn off **Fast Roaming**, **802.11r**, or **Fast Transition** for the speaker's SSID.
3. Leave **BSS Transition** or `802.11v` enabled initially when available.
4. Leave minimum-RSSI forced disconnects off unless coverage is carefully designed.
5. Reconnect the speaker and retest.

If other mobile devices need fast roaming, create a separate speaker/IoT SSID instead of weakening the main network.

## Restore Local Discovery

Use this when the IP is reachable but the app cannot find the speaker.

1. Put the phone and speaker on the same main LAN or trusted IoT network.
2. Do not use a guest SSID.
3. Turn off **Client isolation**, **AP isolation**, or **Block LAN to WLAN multicast** for that network.
4. If phone and speaker use different VLANs, allow only the required local discovery/multicast traffic according to the router vendor's documented method.
5. Reopen the Lithe Audio app and check discovery.

Do not broadly disable the firewall or expose the speaker to the internet.

## Check an Overloaded Access Point

Use this when signal is good but the speaker or the AP shows high retry/drop rates.

1. Open the access point's radio statistics.
2. Compare retry and dropped-packet rates on nearby APs.
3. Move the speaker to a cleaner channel or a healthier nearby AP.
4. Avoid AP locking until the better AP is proven for at least one listening session.
5. If one AP remains abnormal for all clients, update it using the router vendor's supported firmware process and restart it during an agreed maintenance window.

## Verification

After every change:

1. Confirm the reserved IP is still correct.
2. Confirm `0%` packet loss in a 20-ping sample.
3. Aim for average latency below `20 ms`.
4. Check for no spikes above `100 ms`.
5. Aim for signal `-67 dBm` or better.
6. Aim for retry rate below `10%`.
7. Play audio for at least five minutes.
8. Confirm the speaker stays visible in the app.

If the symptom happens weekly, ask the customer to observe it through the next normal lease cycle. A clean short test does not prove that a periodic fault is permanently resolved.
