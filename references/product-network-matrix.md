# Product-Aware Network Decisions

Identify the product family and firmware from an official speaker page, log header, app or customer label before changing band, roaming, static addressing, WMM, UPnP or multicast settings. If the identity is unavailable, state **product capability unknown** and avoid a model-specific change.

## Product guardrails

- Treat original Wi-Fi V1 speakers as 2.4 GHz-only unless the exact product documentation says otherwise.
- Treat Wi-Fi V2, Pro and supported Subwoofer products as dual-band only when the exact model/firmware confirms it.
- Treat Cinema Hub/WiSA faults as a separate topology. Do not apply ordinary multiroom Wi-Fi radio conclusions to the WiSA speaker link.
- Do not infer the product generation from an open port, hostname or appearance alone.

## Addressing decision

Prefer a router-side DHCP reservation when the router supports it because it is centrally visible and reversible. Before saving, prove that the current address belongs to the affected speaker and is not already reserved or used by another client.

Use speaker-side static addressing only when the exact Lithe product documentation calls for it and all current IP, subnet mask, gateway and DNS values are proven. Do not automate speaker-side static addressing in Write mode; guide or escalate it because one incorrect value can make the speaker unreachable.

## Router-feature decision

- Treat documented service ports as LAN/service evidence only. Never create WAN port forwarding or expose the speaker to the internet.
- Change multicast, IGMP, UPnP or isolation only after proving a discovery fault and determining the setting's scope.
- Do not toggle WMM generically. Confirm the product guidance and router vendor behaviour first because the setting can affect every client on the SSID.
- Do not force 2.4 GHz, 5 GHz, a channel or a channel width until the product capability, serving AP, signal, retries and competing-channel evidence are known.

## Sources to re-check before release

- `https://support.litheaudio.com/portal/en/kb/articles/minimum-network-requirements`
- `https://support.litheaudio.com/portal/en/kb/articles/connecting-to-mesh-ap-wi-fi-network`
- `https://support.litheaudio.com/portal/en/kb/articles/how-to-configure-your-router-to-work-with-lithe-audio`
- `https://support.litheaudio.com/portal/en/kb/articles/how-to-make-a-dhcp-static-ip`
- `https://support.litheaudio.com/portal/en/kb/articles/how-to-setup-a-dhcp-static-ip-address-for-a-wi-fi-speaker`

Review this matrix whenever Lithe product or support documentation changes.
