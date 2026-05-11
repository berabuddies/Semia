---
name: ryot
description: Complete Ryot media tracker with progress tracking, reviews, collections, analytics, calendar, and automated daily/weekly reports. Track TV shows, movies, books, anime, games with full GraphQL API integration.
metadata:
  credentials:
    required:
      - name: RYOT_CONFIG
        description: Config file at /home/node/clawd/config/ryot.json with "url" (Ryot instance URL) and "api_token" (API authentication token)
        path: /home/node/clawd/config/ryot.json
        format: |
          {
            "url": "https://your-ryot-instance.com",
            "api_token": "your_api_token_here"
          }
---

# Ryot Media Tracker - Complete Suite

Full-featured Ryot integration with progress tracking, reviews, collections, analytics, calendar, and automated reports.

## Setup (Required)

Before using this skill, you must configure your Ryot instance:

1. **Create config file** at `/home/node/clawd/config/ryot.json`:

```json
{
  "url": "https://your-ryot-instance.com",
  "api_token": "your_api_token_here"
}
```

2. **Set your Ryot instance URL** - Replace `https://your-ryot-instance.com` with your actual Ryot server address
3. **Get your API token** from your Ryot instance settings
4. **Save the config** - The skill will read this file automatically

## Usage

Use `scripts/ryot_api.py` for all Ryot operations.

## 🚀 Quick Start - Automated Setup

```bash
cd /home/node/clawd/skills/ryot/scripts
./setup-automation.sh
```

This will:
- ✅ Set up daily upcoming episodes notification (07:30)
- ✅ Set up weekly stats report (Monday 08:00)
- ✅ Set up daily recent activity (20:00)
- ✅ Configure WhatsApp delivery

## Common Tasks

### 1. Progress Tracking 📊

```bash
# Check your progress on a TV show
python3 scripts/ryot_api.py progress met_XXXXX

# Example output:
# Galaxy Express 999
# Season 1, Episode 35/113 (30%)
```

### 2. Reviews & Ratings ⭐

```bash
# Add review with rating (0-100)
python3 scripts/ryot_reviews.py add met_XXXXX 85 "Amazing show!"

# Rating only
python3 scripts/ryot_reviews.py add met_XXXXX 90
```

### 3. Collections 📚

```bash
# List your collections
python3 scripts/ryot_collections.py list

# Create new collection
python3 scripts/ryot_collections.py create "Top Anime 2026" "My favorite anime of the year"

# Add media to collection
python3 scripts/ryot_collections.py add <collection_id> met_XXXXX
```

### 4. Analytics & Stats 📈

```bash
# View your statistics
python3 scripts/ryot_stats.py analytics
# Output: Total media, shows, movies, watch time

# Recently consumed
python3 scripts/ryot_stats.py recent
# Output: Last 10 media you watched/read
```

### 5. Calendar & Upcoming 📅

```bash
# Upcoming episodes this week
python3 scripts/ryot_calendar.py upcoming

# Calendar for next 30 days
python3 scripts/ryot_calendar.py calendar 30
```

### 6. Search & Details 🔍

```bash
# Search for TV shows
python3 scripts/ryot_api.py search "The Wire" --type SHOW

# Search for movies
python3 scripts/ryot_api.py search "Inception" --type MOVIE

# Get details
python3 scripts/ryot_api.py details met_XXXXX
```

### 7. Mark as Completed ✅

```bash
# Mark media as completed
python3 scripts/ryot_api.py complete met_XXXXX
```

### 8. Bulk Episode Marking 🎬

```bash
# Search for a show to get metadata_id
python3 scripts/ryot-mark-episodes.py search "Galaxy Express 999"
# Output: Found: met_huCCEo1Pu0xM (source: TMDB, type: SHOW)

# Mark range of episodes as watched (e.g., episodes 1-46 of season 1)
python3 scripts/ryot-mark-episodes.py met_huCCEo1Pu0xM 1 1 46
# Marks all episodes from 1 to 46 in season 1

# Mark single season episodes
python3 scripts/ryot-mark-episodes.py met_XXXXX 2 1 24
# Marks season 2, episodes 1-24
```

**Use cases:**
- Catching up on a series you've already watched elsewhere
- Bulk importing viewing history
- Marking entire seasons at once

**Note:** Each episode is marked individually with `createNewInProgress` + `showSeasonNumber`/`showEpisodeNumber`.

## Workflow

1. **User request** → "How many episodes of Galaxy Express 999 have I watched?"
2. **Search** → Find the correct metadata ID
3. **Check progress** → `python3 scripts/ryot_api.py progress met_XXX`
4. **Mark complete** → When finished, deploy bulk progress update

## Media Types

Supported `lot` values:
- `SHOW` - TV series
- `MOVIE` - Films
- `BOOK` - Books
- `ANIME` - Anime series
- `GAME` - Video games

## Important Notes

- **Before first use:** Check if `/home/node/clawd/config/ryot.json` exists. If not, ask the user for their Ryot instance URL and API token, then create the config file.
- Always search first to get the correct metadata ID
- Verify the year if multiple results match the title
- The API uses GraphQL at `/backend/graphql`
- Metadata IDs start with `met_`

## Resources

### scripts/ryot_api.py

Python script for Ryot GraphQL operations. Supports:
- `search` - Find media by title
- `details` - Get metadata details
- `complete` - Mark as completed
