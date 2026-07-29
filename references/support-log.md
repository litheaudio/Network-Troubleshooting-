# Redacted Support Log

Create a local report only after the customer asks for one. Show it for customer review before it is shared.

## Recommended fields

Pass fields to `scripts/create_support_report.py` as repeated `--field "name=value"` arguments.

Allowed names:

- `symptom`
- `frequency`
- `first_seen`
- `last_occurrence`
- `customer_impact`
- `router_model`
- `network_type`
- `access_point`
- `band`
- `signal_dbm`
- `retries_percent`
- `dhcp_reserved`
- `distance_m`
- `walls`
- `floors`
- `barriers`
- `speaker_location`
- `other_devices`
- `log_source`
- `log_window`
- `log_evidence`
- `likely_cause`
- `confidence`
- `changes`
- `rollback`
- `verification`
- `customer_notes`

Example:

```powershell
python scripts/create_support_report.py `
  --diagnostic-json diagnostic.json `
  --output Lithe-Support-Report.md `
  --field "symptom=Audio pauses and the speaker disappears" `
  --field "frequency=About once a week" `
  --field "distance_m=8" `
  --field "walls=Two brick walls" `
  --field "barriers=TV and metal equipment cabinet" `
  --field "signal_dbm=-76" `
  --field "log_source=Customer-provided speaker diagnostic log" `
  --field "log_window=15 minutes around the reported dropout" `
  --field "log_evidence=Wi-Fi disassociation aligned with the dropout" `
  --field "confidence=Confirmed by speaker event and router client history" `
  --field "changes=Created a DHCP reservation" `
  --field "verification=20/20 replies; five-minute playback passed"
```

The script rejects unknown fields, masks full MAC addresses, redacts likely secrets and public IP addresses, and does not upload the report.

## Support handoff

Include:

- the affected private speaker IP;
- masked MAC, if available;
- diagnostic timestamp and local measurements;
- symptoms and frequency;
- relevant physical barriers;
- source, time window, and redacted summary of relevant log evidence;
- whether the cause is confirmed, likely, or possible;
- router/AP evidence;
- exactly what changed;
- before/after measurements;
- verification outcome;
- unresolved questions.

Exclude:

- router or Wi-Fi passwords;
- usernames, emails, MFA or recovery codes;
- tokens, cookies, API keys, or internal endpoints;
- public/WAN IP addresses;
- unrelated client names, IPs, or MAC addresses;
- router configuration exports;
- screenshots of a login page.
