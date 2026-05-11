# meetling-default (secure)

## Install
```bash
npm i
```

## Run (plain text)
```bash
node index.js "Create a call now with Max and Yvonne"
```

## Run (JSON via stdin)
```bash
echo '{
  "text":"Schedule a call tomorrow at 10:00 with a@x.de and b@y.de",
  "participants":["a@x.de","b@y.de"],
  "start_time":"2026-02-19T10:00:00+01:00",
  "title":"Project Sync"
}' | node index.js
```

## Environment variables
- MEETLING_INSTANT_THRESHOLD_MINUTES (default: 30)
- SKILL_LANGUAGE_DEFAULT (default: en)

## Contacts mapping
Copy `contacts.json.example` to `contacts.json` and edit it.

Security note: the skill loads contacts only from `./contacts.json` (no env override).
