# Supervised Browser Support

Follow this workflow when the customer asks Codex to inspect or fix the router because they are unsure.

## 1. Set expectations

Tell the customer:

- control is limited to the router and affected-speaker diagnosis;
- they can watch every action and say **stop** at any time;
- initial inspection is read-only;
- every settings change requires a separate confirmation;
- they must type passwords and MFA codes themselves;
- a redacted support log can be saved locally for review.

Do not proceed until the customer explicitly agrees to read-only inspection.

## 2. Open and authenticate safely

1. Ask the customer to open their router's normal local management page or official router app page.
2. If the page is already signed in, use that existing session.
3. If login is required, pause control and ask the customer to type the credentials directly into the page.
4. Ask the customer to complete MFA personally.
5. Resume only after the customer confirms the page is open.

Never ask for credentials in chat. Never inspect a password manager, saved-password screen, cookie store, developer tools, browser history, or unrelated tab.

## 3. Perform read-only inspection

Inspect only what is relevant:

- LAN subnet and DHCP lease/reservation state;
- the affected speaker client entry;
- current IP and masked MAC;
- online/offline history where shown;
- band, channel, channel width, signal/RSSI, retries, and connected AP;
- mesh node and backhaul status;
- client isolation, guest-network placement, multicast/discovery controls;
- fast-roaming and minimum-RSSI settings;
- AP retry/drop/load statistics when available.

Do not export the router configuration or enumerate unrelated clients. If the router client list is needed to find the supplied IP, look only for that address and avoid recording other device details.

## 4. Explain the diagnosis

State:

1. the observed evidence;
2. the likely cause;
3. the smallest proposed change;
4. which devices may reconnect;
5. how to roll back;
6. how the result will be verified.

Ask: **Would you like me to make this exact change now?**

Do not treat permission for one setting as permission for another.

## 5. Make one approved change

Prefer reversible actions:

- create or correct the affected speaker's DHCP reservation;
- remove an unsuitable AP lock;
- disable fast roaming for the speaker SSID;
- retain BSS transition when appropriate;
- set a stable 2.4 GHz channel and 20 MHz width;
- move the speaker to a healthier AP when the router supports a reversible association control;
- correct guest/client-isolation settings only for the required local network.

Stop if the UI is ambiguous, the setting affects the WAN, the change conflicts with the observed topology, or rollback is unclear.

Require separate approval for a restart. Do not perform factory resets, firmware upgrades, WAN changes, firewall disablement, remote-management enablement, port forwarding, or new cloud-account linking in this workflow.

## 6. Verify

After the customer-approved change:

1. wait for reconnection;
2. confirm the expected IP and AP;
3. run the 20-ping check;
4. compare signal, loss, latency, and retries;
5. ask the customer to play audio;
6. confirm the speaker remains visible in the app;
7. record the change and outcome in the redacted log.

If the change worsens the result, offer the documented rollback and obtain confirmation before applying it.

## 7. End cleanly

Summarize completed changes and any remaining observation period. Ask whether the customer wants the support log saved. If the computer is shared, ask whether they want to sign out of the router; do not sign out without asking.

If browser or computer-control tools are unavailable, say so plainly. Continue with guided steps and compile the support report; never pretend to have taken control.
