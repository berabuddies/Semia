# DeadClaw — iPhone Home Screen Setup Guide

This guide walks you through creating a big red DeadClaw button on your iPhone home screen. When you tap it, it sends the kill command to your OpenClaw Telegram bot, which stops all your running agents instantly.

**Time required**: About 5 minutes.

**What you need before starting**:

- An iPhone running iOS 15 or later
- The Telegram app installed and logged in
- Your OpenClaw Telegram bot set up and connected (you should already be able to send messages to it)
- Your Telegram bot's chat ID or group chat ID

If you don't have a Telegram bot connected to OpenClaw yet, set that up first using the OpenClaw docs, then come back here.

---

## Step 1: Open the Shortcuts App

Find the **Shortcuts** app on your iPhone. It has a blue and pink icon that looks like overlapping squares. It comes pre-installed on every iPhone.

If you can't find it, swipe down on your home screen to open search, then type "Shortcuts" and tap it.

<!-- SCREENSHOT_PLACEHOLDER: shortcuts-app-icon.png -->

---

## Step 2: Create a New Shortcut

Tap the **+** button in the top-right corner. This opens a new, blank shortcut.

<!-- SCREENSHOT_PLACEHOLDER: new-shortcut-screen.png -->

---

## Step 3: Add the "Get Contents of URL" Action

This is the action that sends the kill message to your Telegram bot.

1. Tap **Add Action** (or tap the search bar at the bottom)
2. In the search field, type **URL**
3. Tap **Get Contents of URL** from the results

<!-- SCREENSHOT_PLACEHOLDER: search-get-contents-url.png -->

---

## Step 4: Configure the Telegram API Call

Now you need to fill in the details so the shortcut sends a message to your Telegram bot.

1. Tap the **URL** field and enter:
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN_HERE/sendMessage
   ```
   **REPLACE** `YOUR_BOT_TOKEN_HERE` with your actual Telegram bot token. It looks something like `7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`. You got this when you created your bot with BotFather.

2. Tap **Show More** (or the arrow next to the URL)

3. Change **Method** to **POST**

4. Under **Request Body**, tap **JSON**

5. Add two fields:
   - Key: `chat_id` — Value: your chat ID (a number like `123456789` or `-100123456789` for a group)
   - Key: `text` — Value: `deadclaw`

   To add each field:
   - Tap **Add new field**
   - Choose **Text** as the type
   - Enter the key name and value

<!-- SCREENSHOT_PLACEHOLDER: configure-url-action.png -->

---

## Step 5: Test It

Before adding it to your home screen, test it.

1. Tap the **Play** button (triangle) in the bottom-right corner
2. The shortcut will run and send "deadclaw" to your Telegram bot
3. Check Telegram — you should see the message arrive and DeadClaw's confirmation response

If it doesn't work, double-check your bot token and chat ID. The most common issue is a typo in the bot token.

<!-- SCREENSHOT_PLACEHOLDER: test-run-result.png -->

---

## Step 6: Name Your Shortcut

1. Tap the dropdown arrow at the top of the screen (next to the default name)
2. Tap **Rename**
3. Type **DeadClaw**

<!-- SCREENSHOT_PLACEHOLDER: rename-shortcut.png -->

---

## Step 7: Set the Icon

Give it a red icon so it's immediately recognizable on your home screen.

1. Tap the dropdown arrow at the top again
2. Tap **Choose Icon**
3. Tap the **Color** circle and choose **Red**
4. For the glyph/symbol, search for and select the **stop** icon (a square), or **xmark.circle** (an X in a circle) — whichever feels more like an emergency button to you

<!-- SCREENSHOT_PLACEHOLDER: set-icon-red.png -->

---

## Step 8: Add to Home Screen

This is the step that puts the button on your home screen.

1. Tap the dropdown arrow at the top one more time
2. Tap **Add to Home Screen**
3. You'll see a preview of how it will look
4. Tap **Add** in the top-right corner

The DeadClaw button now appears on your home screen like any other app.

<!-- SCREENSHOT_PLACEHOLDER: add-to-homescreen.png -->

---

## Step 9: Move It Where You Want It

Long-press the DeadClaw icon and drag it wherever you want. Some suggestions:

- **Your main home screen** — so it's always one tap away
- **The dock** — if you want maximum accessibility
- **A "Tools" folder** — if you prefer a tidier home screen but still want quick access

---

## Step 10: Test From the Home Screen

Tap the DeadClaw button on your home screen. It should:

1. Flash briefly as the shortcut runs
2. Send "deadclaw" to your Telegram bot
3. Your bot should respond with the kill confirmation

That's it. You now have a one-tap emergency kill switch on your phone.

---

## Optional: Make It Work From the Lock Screen

If you want even faster access, you can add the shortcut to your Lock Screen (iOS 16+):

1. Long-press your Lock Screen
2. Tap **Customize**
3. Tap the Lock Screen
4. Tap one of the bottom widget slots
5. Choose **Shortcuts** and select your DeadClaw shortcut

Now you can trigger a kill without even unlocking your phone.

---

## Troubleshooting

**"The shortcut ran but nothing happened in Telegram"**
Check your bot token. Go to Telegram, find your chat with @BotFather, and verify the token matches what you entered in the shortcut.

**"I get an error about the chat_id"**
Make sure you're using the numeric chat ID, not a username. You can get your chat ID by messaging @userinfobot on Telegram.

**"The shortcut asks for permission every time"**
Go to Settings > Shortcuts > Advanced, and turn on **Allow Running Scripts**. Also make sure **Private Sharing** is enabled.

**"I want to change the trigger word"**
Edit the shortcut (long-press the icon, tap Edit Shortcut) and change the `text` value in the JSON body to whatever trigger word you prefer.
