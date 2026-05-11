# Changelog

## [1.2.0] - 2026-02-23

### Added - Bulk Episode Marking 🎬
- **New script: `ryot-mark-episodes.py`** - Mark multiple episodes at once
  - `search <title>` - Find show and get metadata ID
  - `<metadata_id> <season> <from_ep> <to_ep>` - Mark range of episodes
  - Example: `ryot-mark-episodes.py met_huCCEo1Pu0xM 1 1 46` marks episodes 1-46 of season 1
  - Perfect for: Catching up on binged series, bulk importing viewing history
  - Uses GraphQL `createNewInProgress` mutation with `showSeasonNumber`/`showEpisodeNumber`

### Technical
- Multi-source search (TMDB, ANILIST, MAL, IGDB)
- Automatic fallback between sources
- Proper User-Agent headers to avoid 403 errors
- Individual episode marking for accurate progress tracking

## [1.1.0] - 2026-02-22

### 🚀 Major Release - Complete Ryot Suite

### Added - Reviews & Ratings ⭐
- **New script: `ryot_reviews.py`** - Add reviews with ratings (0-100)
  - `add <metadata_id> <rating> [review_text]` - Add review with rating
  - Example: `ryot_reviews.py add met_XXX 85 "Amazing show!"`

### Added - Collections 📚
- **New script: `ryot_collections.py`** - Manage personal collections
  - `list` - List all your collections
  - `create <name> [description]` - Create new collection
  - `add <collection_id> <metadata_id>` - Add media to collection
  - Perfect for: "To Watch", "Favorites 2026", "Completed Anime"

### Added - Analytics & Stats 📈
- **New script: `ryot_stats.py`** - View your statistics
  - `analytics` - Total media tracked, watch time, breakdowns
  - `recent` - Last 10 media watched/read with dates

### Added - Calendar & Upcoming 📅
- **New script: `ryot_calendar.py`** - Never miss new episodes
  - `upcoming` - This week's upcoming episodes
  - `calendar [days]` - Calendar for next N days (default 30)
  - Shows season/episode info for each release

### Added - Automated Reports 🤖
- **New script: `setup-automation.sh`** - One-command setup for cron jobs
  - Interactive WhatsApp number input
  - Creates 3 cron jobs automatically:
    1. **Daily Upcoming** (07:30) - Today's new episodes
    2. **Weekly Stats** (Monday 08:00) - Your viewing statistics
    3. **Daily Recent** (20:00) - What you watched recently
  - Dry-run mode: `./setup-automation.sh --dry-run`
  - Uses Gemini Flash for cost efficiency

### Changed
- **SKILL.md** completely rewritten with all new features
- Added Quick Start section for setup-automation.sh
- Reorganized documentation by feature category
- Added emojis for better readability

### Technical
- All scripts follow consistent GraphQL pattern
- Error handling for missing config
- User-Agent headers for API tracking
- Timezone-aware calendar queries
- Modular design for easy extension

### Migration from 1.0.x
- All existing commands work unchanged
- New features are opt-in via separate scripts
- Config file format unchanged
- No breaking changes

## [1.0.4] - 2026-02-22

### Added
- **New command: `progress`** - Check viewing/reading progress for TV shows
  - Shows current episode vs total episodes
  - Displays percentage completion
  - Example: `python3 scripts/ryot_api.py progress met_huCCEo1Pu0xM`
  - Output: "Galaxy Express 999 - Season 1, Episode 35/113 (30%)"

### Changed
- Updated documentation with progress command examples
- Improved workflow section in SKILL.md

### Technical
- Added `get_progress()` function using `userMetadataDetails` GraphQL query
- Query includes `inProgress.showExtraInformation` for episode tracking
- Combines metadata details with user progress in single response

## [1.0.3] - 2026-02-22

### Fixed
- Minor bug fixes and improvements

## [1.0.2] - 2026-02-20

### Fixed
- Configuration path handling
- GraphQL query optimization

## [1.0.1] - 2026-02-20

### Added
- Initial ClawHub release
- Search, details, and complete commands
- Support for SHOW, MOVIE, BOOK, ANIME, GAME types

## [1.0.0] - 2026-02-20

### Added
- First stable release
- Core functionality: search, details, mark completed
- GraphQL API integration
- Configuration via ryot.json
