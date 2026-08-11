# Customer Email Handoff

Use this workflow only after the redacted report has been generated and shown to the customer.

## Draft-first workflow

1. Offer **Create an Outlook email with the report attached** or **Keep the report on this computer**.
2. If email is chosen, confirm the exact support recipient address. Do not infer, search for or substitute an address.
3. Confirm that an approved Outlook Email connector is available. If it is unavailable, keep the report local and explain how to attach it manually.
4. Create a new Outlook draft with the redacted report attached. Outlook write actions use plain text.
5. Show the customer:
   - recipient;
   - subject;
   - complete body;
   - attachment name.
6. Offer **Send**, **Edit** or **Cancel**.
7. Send only after the customer explicitly chooses **Send** for that displayed draft.
8. Report success only when the email tool confirms it. If sending fails, keep the draft and report local and explain the failure.

## Suggested email

Subject:

```text
Lithe Audio network diagnostic report - [product name]
```

Body:

```text
Hello Lithe Audio Support,

Please find attached the network diagnostic report for my Lithe Audio speaker.

Product: [product name]
Firmware: [firmware version]
Reported fault: [brief symptom and frequency]
Current status: [resolved, improved, unchanged or monitoring]
Outstanding: [brief outstanding item or none]

The attached report was reviewed before sharing and contains redacted diagnostic information.

Kind regards
```

## Privacy and safety

- Attach only the generated redacted report, never raw speaker logs or router exports unless the customer separately requests and approves them.
- Do not include passwords, tokens, cookies, MFA codes, public IP addresses, full MAC addresses or unrelated devices.
- Treat recipient selection, attachment and sending as external data transmission.
- Do not save email credentials in the skill or ask the customer to provide them in chat. Use the connector's official sign-in flow.
- Never enable automatic unattended sending.
