# Deep Service Health Check

Use this check when the speaker is reachable but service behaviour conflicts, for example AirPlay or Spotify is visible while the Lithe Audio app or speaker page fails.

Ask permission:

> May I run a deeper read-only service check against this speaker only? It tests a fixed list of publicly documented Lithe service ports and requests only the standard homepage. It sends no login, API or control command.

After approval, run:

```powershell
python scripts/check_speaker_services.py 192.168.1.45 --json
```

Replace the example with the supplied private IP.

The script checks only TCP listeners documented in Lithe Audio's public router guidance and performs one unauthenticated `GET /` request. It does not follow links, guess endpoints, authenticate, enumerate the LAN, issue speaker commands, expose response content or upload data.

## Interpret the result

- `responsive`: the standard HTTP page completed within the timeout.
- `partial_or_stalled`: HTTP headers arrived but the response did not complete. Treat this as evidence that the web service may be stalled while the network stack remains alive.
- `incomplete_headers`: some bytes arrived but no complete HTTP headers were received.
- `listener_no_http_response`: TCP port 80 accepted a connection but returned no HTTP response.
- `no_listener`: the standard HTTP service did not accept a connection.

Use the fixed service results only for correlation:

- AirPlay or Spotify visible plus a stalled Lithe page and missing Lithe app entry supports a **Likely** Lithe control/web-service fault.
- Healthy ping plus no web listener isolates the symptom to the service layer, not general Wi-Fi reachability.
- A listener does not prove the service works fully.
- A closed TCP port does not prove a named feature is absent; discovery may use multicast, UDP, Bluetooth or a cloud account.

Do not call service-port results internal logs or a smoking gun. Use the timestamped recovery-log workflow to obtain causal evidence.
