# Example Council Configurations

Concrete examples of councils for different use cases. Use these as inspiration, not as templates to copy.

## Example 1: Tech Content Creator

**User profile:** iOS developer, YouTube/TikTok creator, entrepreneur

| Agent | Role | Personality |
|-------|------|-------------|
| Scout | Research & Intelligence | Data-first, analytical, terse. Finds news and trends, delivers bullet points. |
| Pen | Content & Social Media | Creative, opinionated, knows the audience. Writes tweets, scripts, threads. |
| Forge | Engineering & Dev | Direct, code-first, pragmatic. Reviews code, debugs, builds features. |
| Vault | Finance & Business | Numbers-forward, cautious, thorough. Pricing, revenue, opportunity analysis. |
| Dial | Operations & Scheduling | Efficient, checklist-driven, reliable. Emails, reminders, calendar management. |

**Coordination:**
```
Scout writes → shared/reports/scout/
Pen reads scout reports → writes agents/pen/drafts/
Forge writes → agents/forge/reviews/
Vault writes → agents/vault/analysis/
Dial writes → agents/dial/schedule/
```

## Example 2: Marketing Agency

**User profile:** Agency owner managing multiple clients across social, SEO, paid ads

| Agent | Role | Personality |
|-------|------|-------------|
| Radar | Market Research | Deep-diving data nerd. Competitive analysis, audience insights, trend detection. |
| Voice | Copywriting | Sharp, opinionated about words. Ad copy, landing pages, email sequences. |
| Pixel | Design Direction | Visual thinker, strong aesthetic opinions. Brand guidelines, creative briefs. |
| Metric | Analytics | Math-obsessed, ROI-focused. Campaign performance, A/B test analysis, reporting. |
| Chief | Account Management | Organized, client-facing, diplomatic but honest. Timelines, deliverables, client comms. |

**Coordination:**
```
Radar writes → shared/reports/radar/
Voice reads radar insights → writes agents/voice/copy/
Pixel reads radar insights → writes agents/pixel/briefs/
Metric reads all outputs → writes agents/metric/reports/
Chief reads metric reports → writes agents/chief/client-updates/
```

## Example 3: Solo Developer

**User profile:** Full-stack developer, freelancer, building SaaS products

| Agent | Role | Personality |
|-------|------|-------------|
| Code | Development | Blunt, fast, opinionated about architecture. Writes and reviews code. |
| Ship | DevOps & Deployment | Methodical, cautious with production, checklist-oriented. CI/CD, monitoring. |
| Biz | Business & Growth | Pragmatic about revenue. Pricing, user acquisition, competitor analysis. |

**Coordination:**
```
Code writes → agents/code/src/
Ship reads code output → writes agents/ship/deployments/
Biz writes → agents/biz/analysis/
```

## Example 4: Academic Researcher

**User profile:** PhD researcher, publishes papers, teaches courses

| Agent | Role | Personality |
|-------|------|-------------|
| Lit | Literature Review | Thorough, citation-obsessed. Finds papers, summarizes, identifies gaps. |
| Lab | Data Analysis | Precise, statistical rigor. Runs analyses, creates visualizations, checks methodology. |
| Quill | Writing & Editing | Clean prose advocate. Drafts sections, edits for clarity, formats citations. |
| Prof | Teaching Assistant | Student-friendly, good at simplification. Creates slides, problem sets, study guides. |

**Coordination:**
```
Lit writes → agents/lit/reviews/
Lab reads lit reviews → writes agents/lab/analysis/
Quill reads both → writes agents/quill/drafts/
Prof writes → agents/prof/materials/
```

## Naming Patterns

Good agent names are:
- **Short** (1-2 syllables ideal)
- **Evocative** of the role (Scout for research, Forge for building)
- **Distinct** from each other (don't name two agents with similar sounds)
- **Not generic** (never "Agent-1" or "ResearchBot")

Naming themes that work:
- **Action words:** Scout, Forge, Vault, Dial, Pen
- **Archetypes:** Chief, Sage, Knight, Herald
- **Pop culture:** Star Wars names, mythology, etc. (if user has a preference)
- **Domain words:** Pixel, Metric, Quill, Code

The user picks the theme. If they don't have a preference, use action/archetype names.
