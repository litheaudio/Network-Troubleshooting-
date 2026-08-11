# Redacted Support Log

Always render the redacted closing report in chat. Create a local report only after the customer approves saving it. Show it for customer review before it is shared.

## Recommended fields

Pass fields to `scripts/create_support_report.py` as repeated `--field "name=value"` arguments.

When redacted collector/analyser JSON exists, pass it with `--log-analysis-json`. Let the script populate log status, coverage, ranked evidence, confidence and next proof. Use explicit `--field` values only to add customer context or override a reviewed value.

Allowed names:

- `product_name`
- `firmware_version`
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
- `log_status`
- `likely_cause`
- `confidence`
- `initial_findings`
- `meaning`
- `before_measurements`
- `approved_fix`
- `changes`
- `expected_improvement`
- `after_measurements`
- `rollback`
- `verification`
- `customer_outcome`
- `faults_found`
- `fixes_completed`
- `outstanding`
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
  --field "initial_findings=5 percent loss and 140 ms maximum latency" `
  --field "meaning=The live Wi-Fi path was unstable during the test" `
  --field "before_measurements=19/20 replies; 5 percent loss; 61 ms average" `
  --field "approved_fix=Moved the speaker to the nearer access point" `
  --field "expected_improvement=Reduce packet loss and audio interruptions" `
  --field "after_measurements=20/20 replies; 0 percent loss; 12 ms average" `
  --field "customer_outcome=Playback and app visibility passed for five minutes" `
  --field "verification=Improved; recurring fault still requires monitoring"
```

The script rejects unknown fields, masks full MAC addresses, redacts likely secrets and public IP addresses, and does not upload the report.

## Empty or unavailable logs

Check the exported file size before analysis. Treat a zero-byte file as a failed collection, never as an empty or clean log. Set:

- `log_status=Failed - exported file contained zero bytes`;
- `log_evidence=No speaker-log evidence was available`;
- `outstanding=Speaker log export requires investigation`, unless later evidence resolves it.

Retry the customer-visible export only once. Do not keep extending the session with repeated attempts.

## Support handoff

Include:

- product name and firmware version, when visible;
- the affected private speaker IP;
- masked MAC, if available;
- diagnostic timestamp and local measurements;
- symptoms and frequency;
- relevant physical barriers;
- source, time window, and redacted summary of relevant log evidence;
- whether the cause is confirmed, likely, or possible;
- router/AP evidence;
- exactly what changed;
- why it changed and the expected improvement;
- before/after measurements;
- the customer-reported outcome;
- verification outcome;
- unresolved questions.

Write the report so the customer can attach it directly to an email to Lithe Audio support. End it with a short customer acknowledgement and **Thank you for your time today.** State that the report was not emailed or uploaded automatically.

Exclude:

- router or Wi-Fi passwords;
- usernames, emails, MFA or recovery codes;
- tokens, cookies, API keys, or internal endpoints;
- public/WAN IP addresses;
- unrelated client names, IPs, or MAC addresses;
- router configuration exports;
- screenshots of a login page.
