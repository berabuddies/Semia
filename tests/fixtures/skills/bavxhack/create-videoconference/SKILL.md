---
name: meetling-default
description: Default video conferences via Meetling. Instant calls always use /m/ rooms + share payload for Claw default sending. Scheduled calls return link + email invite template. Secure contacts loading (no env-controlled file paths).
version: 1.3.0
metadata:
  openclaw:
    requires:
      bins:
        - node
      env:
        - MEETLING_INSTANT_THRESHOLD_MINUTES
        - SKILL_LANGUAGE_DEFAULT
---

# Meetling Default (Video Conferences) — Secure

## Hardcoded Meetling host
This skill always uses:
https://app.meetling.de

No environment variable can change the base URL.

## Security: contacts loading
- Contacts are loaded **only** from `./contacts.json` (current working directory).
- No environment variable can override the file path.
- The skill does **not** output the contacts file path.

If `contacts.json` is missing or invalid JSON, the skill continues with an empty map and marks recipients as unresolved.

## Behavior

### Instant / Ad-hoc (always `/m/`)
Triggers if ANY is true:
- Text contains “now / right now / asap / immediately”
- OR contains German equivalents “jetzt / jetzt gleich / sofort / gleich”
- OR `start_time` is within `MEETLING_INSTANT_THRESHOLD_MINUTES` minutes from now
- OR participants are present but no `start_time` is provided

Returns:
- `url`: https://app.meetling.de/m/<slug>
- `share`: message + resolved recipients for your Claw default sending path

### Scheduled
If `start_time` is more than the threshold minutes in the future:
- returns `email_invite` (subject + body) plus the Meetling link

Note: This skill does not automate Meetling dashboard creation or Meetling-sent invites (requires an official API or robust UI automation).
