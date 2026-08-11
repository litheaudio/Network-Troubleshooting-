# Approved Lithe Support-Log Connector

Use a connector only when it is supplied or explicitly approved by Lithe Audio and is available as a callable Codex tool. A skill is workflow guidance; it cannot create API access by itself.

## Required safeguards

- Use read-only diagnostic and event-log operations.
- Ask the customer for permission immediately before retrieval.
- Use the connector's official authentication flow. Never ask for credentials, tokens, cookies or MFA codes in chat.
- Restrict the query to the affected speaker and the smallest useful time window, normally 15 minutes either side of the failure.
- Do not enumerate other speakers or customers.
- Do not request configuration secrets, Wi-Fi keys, account data or raw credential-bearing packets.
- Do not display or document endpoint paths, protocol commands, tokens or implementation details.
- Do not save raw results unless the customer separately asks for a local support report.

## Minimum evidence returned

Accept a result only when it identifies:

- that the event belongs to the affected speaker;
- the source and local-time window;
- event timestamps;
- redacted event categories such as DHCP, Wi-Fi association, timeout, gateway/route, reboot/watchdog, discovery, roaming or AP/channel change;
- whether collection was complete, partial or unavailable.

Treat a connector error, empty response or unsupported device as **logs unavailable**, not as a healthy result.

## Correlation workflow

1. Align events with the customer's failure time and target-only monitor samples.
2. Look for a causal sequence, for example association loss followed by DHCP failure and loss of reachability.
3. Compare independent router/AP evidence.
4. Label the cause **Confirmed** only when an event directly explains the failure and belongs to the affected speaker.
5. Label two aligned independent observations **Likely**.
6. Label one ambiguous observation **Possible** and state the next proof.
7. Return at most three ranked potential causes and one smallest reversible next action.

## Unavailable connector

Say plainly that direct Lithe support-log access is not available. Continue with an official visible log view, a customer-provided export, or a target-only timed monitor. Never invent a connector, endpoint, result or smoking gun.
