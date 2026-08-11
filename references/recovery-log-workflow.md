# Timestamped Recovery Log Workflow

Use this fallback when the affected speaker is reachable but its official web page or **Generate Log** control times out, renders incompletely, or fails to download a log.

## Preserve the failure marker

Before any restart, record in the conversation:

- the exact failure time in ISO format with the customer's local timezone;
- the symptom visible at that time;
- ping loss and latency;
- whether TCP ports 80 and 443 responded;
- whether the official page timed out, rendered incompletely, or returned a visible error;
- the current app visibility and playback state when known.

Use the tool-observed timestamp when available. Do not estimate silently. Ask before saving the marker to a local file or support report.

## Protect evidence before restarting

Explain that a power cycle may erase volatile logs. First attempt, when available:

1. the approved read-only Lithe support-log connector;
2. the visible **Generate Log** control;
3. relevant router or access-point history for the marked time.

If none is available, state that the restart is a recovery step and may reduce diagnostic evidence. Ask separate permission immediately before the power cycle and explain the expected interruption.

## Retry after the approved power cycle

1. Record the restart time in the same local timezone.
2. Wait for the supplied IP to answer the target-only check; do not scan for a replacement address.
3. Run the 20-ping check and record the recovered measurements.
4. Open `http://<supplied-private-IP>/` through the browser. Do not assume HTTPS when port 443 does not respond.
5. Use only the visible official interface. Click **Generate Log** or its clearly equivalent visible control; do not guess a download URL.
6. Pause and tell the customer: **"Please open Chrome Downloads using the Downloads button at the top right, or press Ctrl+J. Find the speaker log. If Chrome shows Keep or Discard for this local download, click Keep, then tell me when it says the download is complete."**
7. Wait for the customer to reply **Kept** or **No Keep option shown**. Do not continue to file inspection while the download decision is pending. If Chrome describes the file as dangerous, suspicious or malicious, tell the customer not to keep it and stop the download workflow.
8. After the customer's confirmation, wait for the download to finish and verify that a new file exists. Inspect only the expected recent log file; do not enumerate or expose unrelated downloads.
9. If the page returns to **Generate Log** but no file appears, check once more for a hidden or pending browser download prompt. Do not label the speaker's log generator faulty until the prompt state is resolved.
10. Analyse the downloaded file with `scripts/analyze_speaker_logs.py`, passing the pre-restart failure timestamp and local timezone.
11. Confirm whether `failure_time_covered` is `true` before correlating an event with the failure.

## Browser download decisions

- Treat **Keep / Discard** as a browser delivery decision, not a speaker log-generation result.
- Pause and let the customer make the choice when the browser presents a security warning.
- If the customer chooses **Keep**, confirm completion and analyse the saved file.
- If the customer chooses **Discard**, record that the log was generated but not retained; do not claim the generator failed.
- If the prompt describes the file as dangerous, suspicious or malicious rather than merely insecure because it came from local HTTP, do not override it. Stop and recommend an official support handoff.

## Smoking-gun standard

- If the log covers the pre-restart time and a device-matched causal event aligns with the failure, classify it using the normal Confirmed/Likely/Possible standard.
- If the log starts after the restart, say: **"The recovered log does not contain the pre-restart failure window."** Treat startup events only as recovery evidence.
- If the log has no usable timestamps, say that correlation is unavailable.
- Never label the power cycle itself, a normal startup line, or an event outside the marked window as the smoking gun.
- Never label a missing local file as a generation failure until browser blocking, pending confirmation and download completion have been checked.

Keep the original timestamp in the final support handoff even when the post-restart log does not cover it.
