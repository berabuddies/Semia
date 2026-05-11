# Ryot Skill - Publishing Guide

## Files Ready for Publishing

✅ **Skill Package**: `/home/node/clawd/skills/ryot.skill` (2.8 KB)

## What's Included

- **SKILL.md** - Main skill documentation with workflow and examples
- **scripts/ryot_api.py** - Python script for Ryot GraphQL operations

## Installation Instructions (for users)

1. Download `ryot.skill`
2. Install in OpenClaw:
   ```bash
   openclaw skill install ryot.skill
   ```

## Configuration Required

Users need to create `/home/node/clawd/config/ryot.json`:

```json
{
  "url": "https://your-ryot-instance.com",
  "api_token": "YOUR_API_TOKEN_HERE"
}
```

## Skill Features

- Search for movies, TV shows, books, anime, games
- Get detailed metadata (title, year, description)
- Mark media as completed/watched

## Testing

The script has been developed and tested with:
- Ryot instance: https://ryot.federicoliva.it
- GraphQL API version: latest

## Publishing to ClawHub

Upload `ryot.skill` to https://clawhub.com with:
- **Title**: Ryot Media Tracker
- **Description**: Track and manage your media consumption (movies, TV shows, books, anime, games) via Ryot self-hosted tracker
- **Category**: Productivity / Media
- **Tags**: ryot, media-tracker, movies, tv-shows, books, anime, graphql

## Future Improvements

- [ ] Add support for rating media
- [ ] List current watching/reading progress
- [ ] Add media to custom lists
- [ ] Export watched history
