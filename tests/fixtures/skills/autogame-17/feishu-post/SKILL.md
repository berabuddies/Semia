# Feishu Post (RichText) Skill

Send Rich Text (Post) messages to Feishu.
This format is distinct from Cards. It supports native rich text elements but is less flexible in layout than cards.
It is better for long-form text mixed with images/links.

## Prerequisites

- Install `feishu-common` first.
- This skill depends on `../feishu-common/index.js` via `utils/feishu-client.js`.

## Features
- **Native Emoji Support**: Automatically converts `[微笑]`, `[得意]` etc. to Feishu native emoji tags.
- **Markdown-like Parsing**: Supports simple newlines and paragraphs.
- **Rich Text**: Uses Feishu's Post content structure.

## Usage

```bash
node skills/feishu-post/send.js --target "ou_..." --text-file "temp/msg.md" --title "Optional Title"
```

## Options
- `-t, --target <id>`: Target ID (user `ou_...` or chat `oc_...`).
- `-x, --text <text>`: Text content (supports `\n` for newlines and `[emoji]` tags).
- `-f, --text-file <path>`: Read content from file.
- `--title <text>`: Title of the post.
- `--reply-to <id>`: Message ID to reply to.

## Emoji List
Supported emojis include: `[微笑]`, `[色]`, `[亲亲]`, `[大哭]`, `[强]`, `[加油]`, and many more.
See `emoji-map.js` for the full mapping.
