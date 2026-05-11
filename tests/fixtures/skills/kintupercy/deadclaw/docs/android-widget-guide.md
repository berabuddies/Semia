# DeadClaw — Android Home Screen Setup Guide

This guide walks you through creating a big red DeadClaw button on your Android home screen. When you tap it, it sends the kill command to your OpenClaw Telegram bot, which stops all your running agents instantly.

**Time required**: About 5 minutes.

**What you need before starting**:

- An Android phone running Android 8.0 or later
- The Telegram app installed and logged in
- Your OpenClaw Telegram bot set up and connected
- Your Telegram bot token and chat ID

Two options are covered below. Choose whichever you prefer:

- **Option A: Tasker** — More powerful, costs a few dollars, recommended if you already have it
- **Option B: HTTP Shortcuts app** — Free, simpler, recommended for most people

---

## Option A: Using Tasker

Tasker is a powerful automation app for Android. If you already have it, this is straightforward. If you don't, Option B (HTTP Shortcuts) is free and easier.

### A1: Install Tasker

If you don't already have it, install **Tasker** from the Google Play Store. It costs about $3.50.

### A2: Create a New Task

1. Open Tasker
2. Tap the **Tasks** tab at the top
3. Tap the **+** button at the bottom
4. Name it **DeadClaw**
5. Tap the checkmark

### A3: Add an HTTP Request Action

1. In the task editor, tap the **+** button to add an action
2. Tap **Net**
3. Tap **HTTP Request**
4. Fill in:
   - **Method**: POST
   - **URL**: `https://api.telegram.org/botYOUR_BOT_TOKEN_HERE/sendMessage`
     (Replace `YOUR_BOT_TOKEN_HERE` with your actual bot token)
   - **Content Type**: `application/json`
   - **Body**: `{"chat_id": "YOUR_CHAT_ID_HERE", "text": "deadclaw"}`
     (Replace `YOUR_CHAT_ID_HERE` with your numeric chat ID)
5. Tap the back arrow to save

<!-- SCREENSHOT_PLACEHOLDER: tasker-http-request.png -->

### A4: Test the Task

1. Tap the **Play** button (triangle) at the bottom of the task editor
2. Check Telegram — you should see "deadclaw" arrive and DeadClaw's confirmation response

### A5: Add a Home Screen Widget

1. Go to your Android home screen
2. Long-press on an empty spot
3. Tap **Widgets**
4. Find **Tasker** in the widget list
5. Tap and hold **Task Shortcut** (1x1) and drag it to your home screen
6. Select your **DeadClaw** task
7. For the icon:
   - Tap the icon to change it
   - Choose a red circle or stop icon
   - (Or use any icon that says "emergency" to you)
8. Tap the checkmark to confirm

<!-- SCREENSHOT_PLACEHOLDER: tasker-widget-homescreen.png -->

Tap the widget to test. Done.

---

## Option B: Using HTTP Shortcuts (Free)

HTTP Shortcuts is a free app that does exactly what we need — sends an HTTP request when you tap a home screen shortcut. No scripting knowledge needed.

### B1: Install HTTP Shortcuts

Open the Google Play Store, search for **HTTP Shortcuts** (by Roland Meyer), and install it. It's free.

<!-- SCREENSHOT_PLACEHOLDER: http-shortcuts-playstore.png -->

### B2: Create a New Shortcut

1. Open HTTP Shortcuts
2. Tap the **+** button (floating action button)
3. Tap **Regular Shortcut**

### B3: Configure the Basics

1. **Name**: DeadClaw
2. **Description**: Emergency kill switch for OpenClaw agents
3. **Method**: POST
4. **URL**: `https://api.telegram.org/botYOUR_BOT_TOKEN_HERE/sendMessage`

   Replace `YOUR_BOT_TOKEN_HERE` with your actual Telegram bot token. You got this from BotFather when you created your bot. It looks like `7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.

<!-- SCREENSHOT_PLACEHOLDER: http-shortcuts-basic.png -->

### B4: Set Up the Request Body

1. Tap **Request Body / Parameters**
2. Change the body type to **Custom Text**
3. Set Content Type to **application/json**
4. In the body text field, enter:
   ```json
   {"chat_id": "YOUR_CHAT_ID_HERE", "text": "deadclaw"}
   ```
   Replace `YOUR_CHAT_ID_HERE` with your numeric Telegram chat ID.

<!-- SCREENSHOT_PLACEHOLDER: http-shortcuts-body.png -->

### B5: Set the Icon

1. Go back to the main shortcut settings
2. Tap the **Icon** field
3. Choose a built-in icon — look for a circle or stop symbol
4. Tap the **Color** option and choose **red**

<!-- SCREENSHOT_PLACEHOLDER: http-shortcuts-icon.png -->

### B6: Set the Response Handling

1. Tap **Response Handling**
2. Under **Success Message**, choose **Show simple toast** — this shows a brief confirmation when the kill fires
3. Tap save/back

### B7: Test It

1. Back in the HTTP Shortcuts main screen, tap on your **DeadClaw** shortcut
2. It should fire the request and show a toast message
3. Check Telegram — "deadclaw" should appear and your bot should confirm the kill

### B8: Add to Home Screen

1. Long-press on the **DeadClaw** shortcut in the HTTP Shortcuts app
2. Tap **Place on home screen** (or **Add to home screen**)
3. The DeadClaw button appears on your home screen

Alternatively:
1. Go to your home screen
2. Long-press an empty area
3. Tap **Widgets**
4. Find **HTTP Shortcuts** in the widget list
5. Drag the 1x1 widget to your home screen
6. Select your **DeadClaw** shortcut

<!-- SCREENSHOT_PLACEHOLDER: http-shortcuts-homescreen.png -->

---

## Finding Your Telegram Bot Token and Chat ID

If you're not sure where to find these, here's how:

**Bot token:**
1. Open Telegram
2. Search for **@BotFather**
3. If you already have a bot, send `/mybots`, select your bot, then tap **API Token**
4. If you need a new bot, send `/newbot` and follow the prompts
5. Copy the token (looks like `7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

**Chat ID:**
1. Open Telegram
2. Search for **@userinfobot** and start a chat with it
3. It will reply with your chat ID (a number like `123456789`)
4. If you're using a group chat, add @userinfobot to the group — it will post the group's chat ID (starts with `-100`)

---

## Troubleshooting

**"Nothing happens when I tap the button"**
Check that your phone has an internet connection. Then verify your bot token — one wrong character and it won't work.

**"I see the request was sent but Telegram doesn't respond"**
Make sure your OpenClaw instance is running and connected to the Telegram bot. The message "deadclaw" needs to reach an active OpenClaw agent to trigger the kill.

**"The widget disappeared after a phone restart"**
Some Android launchers remove widgets on restart. Try adding it again. If it keeps disappearing, check your battery optimization settings — some phones aggressively kill background apps and widgets.

**"I want a bigger button"**
In Tasker, you can create a 2x2 or larger widget. In HTTP Shortcuts, the widget is fixed at 1x1 but you can place it in a prominent spot on your home screen.

**"Can I use this without Telegram?"**
Yes — if you have another messaging channel connected to OpenClaw (WhatsApp, Discord, Slack), you can modify the shortcut to send the kill trigger through that channel's API instead. The concept is the same: send the word "deadclaw" to a channel your OpenClaw agent is listening on.
