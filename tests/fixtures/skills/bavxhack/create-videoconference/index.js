/* meetling-default (secure)
 * - Meetling base URL is hardcoded: https://app.meetling.de
 * - Contacts file path cannot be controlled by env vars (prevents LFI via CONTACTS_JSON)
 * - Output does not reveal file paths
 */

const fs = require("fs");
const path = require("path");

const MEETLING_BASE = "https://app.meetling.de";
const DEFAULT_THRESHOLD_MIN = 30;

function nowDate() {
  return new Date();
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

function toCompactStamp(d) {
  // YYYYMMDD-HHMM local time
  const y = d.getFullYear();
  const m = pad2(d.getMonth() + 1);
  const da = pad2(d.getDate());
  const h = pad2(d.getHours());
  const mi = pad2(d.getMinutes());
  return `${y}${m}${da}-${h}${mi}`;
}

function normalizeGerman(s) {
  return s
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue")
    .replace(/Ä/g, "ae").replace(/Ö/g, "oe").replace(/Ü/g, "ue")
    .replace(/ß/g, "ss");
}

function slugify(input) {
  return normalizeGerman(String(input || ""))
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data.trim()));
    process.stdin.on("error", () => resolve(""));
    if (process.stdin.isTTY) setTimeout(() => resolve(""), 0);
  });
}

function safeJsonParse(s) {
  try { return JSON.parse(s); } catch { return null; }
}

function detectLanguage(text) {
  const t = String(text || "").toLowerCase();
  const de = /\b(jetzt|jetzt gleich|sofort|gleich|bitte|mach|erstelle|plane|einladen|teilnehmer|videokonferenz|konferenz|termin|morgen|heute|übermorgen)\b/.test(t);
  const en = /\b(now|right now|asap|immediately|please|create|schedule|invite|participants|video call|conference|meeting|appointment|tomorrow|today)\b/.test(t);
  if (de === en) return (process.env.SKILL_LANGUAGE_DEFAULT || "en").toLowerCase() === "de" ? "de" : "en";
  return de ? "de" : "en";
}

function containsExplicitOtherProvider(text) {
  const t = String(text || "").toLowerCase();
  return /\b(zoom|teams|microsoft teams|google meet|webex|jitsi)\b/.test(t);
}

function isInstantByText(text) {
  const t = String(text || "").toLowerCase();
  return /\b(now|right now|asap|immediately)\b/.test(t) || /\b(jetzt|jetzt gleich|sofort|gleich)\b/.test(t);
}

function parseStartTime(start_time) {
  if (!start_time) return null;
  const d = new Date(start_time);
  return Number.isNaN(d.getTime()) ? null : d;
}

function minutesBetween(a, b) {
  return Math.round((b.getTime() - a.getTime()) / 60000);
}

function extractParticipantsFromText(text, lang) {
  const t = String(text || "");
  const re = lang === "de" ? /\bmit\b(.+)$/i : /\bwith\b(.+)$/i;
  const m = t.match(re);
  if (!m) return [];
  const tail = m[1].replace(/[.?!]$/g, "").trim();
  return tail
    .split(/\bund\b|\band\b|&|,|\+/i)
    .map((x) => x.trim())
    .filter(Boolean);
}

/**
 * Secure contacts loading:
 * - only ./contacts.json
 * - no env override, no user-controlled path
 * - size limit to reduce accidental reads
 */
function loadContactsSafe() {
  const p = path.resolve(process.cwd(), "contacts.json");
  try {
    const st = fs.statSync(p);
    if (!st.isFile() || st.size > 256 * 1024) return {};
    const raw = fs.readFileSync(p, "utf8");
    const obj = JSON.parse(raw);
    return (obj && typeof obj === "object") ? obj : {};
  } catch {
    return {};
  }
}

function resolveRecipients(participants, contactsMap) {
  const resolved = [];
  const unresolved = [];
  for (const p of participants) {
    const key = String(p).trim().toLowerCase();
    if (!key) continue;
    const hit = contactsMap[key];
    if (hit && typeof hit === "object" && hit.id) {
      resolved.push({ input: p, channel: hit.channel || "default", id: hit.id });
    } else {
      unresolved.push(p);
    }
  }
  return { resolved, unresolved };
}

function buildInstantInviteText(url, title, participants, lang) {
  const names = participants && participants.length ? participants.join(", ") : "";
  if (lang === "de") {
    const t = title ? `**${title}**\n` : "";
    const toLine = names ? `Für: ${names}\n` : "";
    return `${t}${toLine}Meetling-Link (jetzt): ${url}`;
  }
  const t = title ? `**${title}**\n` : "";
  const toLine = names ? `For: ${names}\n` : "";
  return `${t}${toLine}Meetling link (now): ${url}`;
}

function buildScheduledEmailInvite(url, title, startTime, participants, lang) {
  const whenText = startTime ? startTime.toString() : "";
  if (lang === "de") {
    const subject = title ? `Einladung: ${title}` : "Einladung: Videokonferenz";
    const bodyLines = [
      "Hallo,",
      "",
      title ? `ich lade euch zur Videokonferenz ein: ${title}` : "ich lade euch zur Videokonferenz ein.",
      whenText ? `Wann: ${whenText}` : null,
      participants && participants.length ? `Teilnehmer: ${participants.join(", ")}` : null,
      "",
      `Link: ${url}`,
      "",
      "Viele Grüße"
    ].filter(Boolean);
    return { subject, body: bodyLines.join("\n") };
  }

  const subject = title ? `Invitation: ${title}` : "Invitation: Video conference";
  const bodyLines = [
    "Hi,",
    "",
    title ? `You're invited to a video call: ${title}` : "You're invited to a video call.",
    whenText ? `When: ${whenText}` : null,
    participants && participants.length ? `Participants: ${participants.join(", ")}` : null,
    "",
    `Link: ${url}`,
    "",
    "Best regards"
  ].filter(Boolean);

  return { subject, body: bodyLines.join("\n") };
}

function decideMode({ text, startTime, participants, thresholdMin }) {
  if (isInstantByText(text)) return "instant";
  if (participants && participants.length && !startTime) return "instant";
  if (startTime) {
    const mins = minutesBetween(nowDate(), startTime);
    if (mins <= thresholdMin) return "instant";
    return "scheduled";
  }
  return "instant";
}

function buildRoomSlug({ title, participants }) {
  const base =
    slugify(title) ||
    slugify((participants || []).slice(0, 3).join("-")) ||
    "call";
  return `${base}-${toCompactStamp(nowDate())}`;
}

function buildMeetlingUrl(slug) {
  return `${MEETLING_BASE}/m/${slug}`;
}

async function main() {
  const thresholdMin = Number(process.env.MEETLING_INSTANT_THRESHOLD_MINUTES || DEFAULT_THRESHOLD_MIN);

  const stdin = await readStdin();
  const json = stdin ? safeJsonParse(stdin) : null;

  const argvText = process.argv.slice(2).join(" ").trim();
  const text = (json && json.text) ? String(json.text) : (argvText || "");
  const title = (json && json.title) ? String(json.title) : "";
  const startTime = parseStartTime(json && json.start_time);

  const language = detectLanguage(text);

  if (containsExplicitOtherProvider(text)) {
    const out = {
      ok: false,
      reason: "User explicitly requested a different provider. This skill is Meetling-default only.",
      provider_detected: "other",
      text,
      language
    };
    process.stdout.write(JSON.stringify(out, null, 2));
    return;
  }

  const participantsInput = (json && Array.isArray(json.participants))
    ? json.participants.map(String)
    : extractParticipantsFromText(text, language);

  const contactsMap = loadContactsSafe();
  const { resolved, unresolved } = resolveRecipients(participantsInput, contactsMap);

  const mode = decideMode({ text, startTime, participants: participantsInput, thresholdMin });

  const slug = buildRoomSlug({ title: title || text, participants: participantsInput });
  const url = buildMeetlingUrl(slug);

  if (mode === "instant") {
    const message = buildInstantInviteText(url, title, participantsInput, language);
    const out = {
      ok: true,
      provider: "meetling",
      language,
      mode: "instant",
      url,
      slug,
      share: {
        message,
        recipients: resolved.map(r => ({ channel: r.channel, id: r.id })),
        recipients_unresolved: unresolved
      },
      unresolved_recipients: unresolved
    };
    process.stdout.write(JSON.stringify(out, null, 2));
    return;
  }

  const emailInvite = buildScheduledEmailInvite(url, title, startTime, participantsInput, language);
  const out = {
    ok: true,
    provider: "meetling",
    language,
    mode: "scheduled",
    url,
    slug,
    scheduled_for: startTime ? startTime.toISOString() : null,
    email_invite: emailInvite,
    share: {
      message: `${emailInvite.subject}\n\n${emailInvite.body}`,
      recipients: resolved.map(r => ({ channel: r.channel, id: r.id })),
      recipients_unresolved: unresolved
    },
    unresolved_recipients: unresolved,
    limitations: [
      "This skill does not create scheduled meetings inside the Meetling dashboard.",
      "Meetling-sent email invitations require an official API or robust UI automation.",
      "This output includes a reliable /m link plus an email template as a fallback."
    ]
  };
  process.stdout.write(JSON.stringify(out, null, 2));
}

main().catch((err) => {
  const out = { ok: false, error: String(err && err.message ? err.message : err) };
  process.stdout.write(JSON.stringify(out, null, 2));
});
