---
name: Goals
description: Build a personal goal-setting system with milestones, tracking, and regular reviews.
metadata: {"clawdbot":{"emoji":"🎯","os":["linux","darwin","win32"]}}
---

## Core Behavior
- User mentions an aspiration → help clarify and structure as goal
- Track progress without nagging → surface when relevant
- Regular reviews → quarterly and yearly reflection
- Create `~/goals/` as workspace

## Goal vs Project vs Habit
- Goal: outcome you want (run a marathon, save €10k, learn Spanish)
- Project: defined end state, series of tasks (plan the wedding)
- Habit: recurring behavior (exercise 4x/week)
- Goals often spawn projects and habits to achieve them

## When User States a Goal
- "What does success look like specifically?"
- "By when?" — deadline creates urgency
- "Why does this matter to you?" — motivation for hard days
- "What's the first small step?"

## Goal File Structure
One file per goal: `run-a-marathon.md`
- What: specific outcome
- Why: motivation and meaning
- By when: target date
- Milestones: checkpoints along the way
- Current status: on track, behind, ahead
- Progress log: dated updates

## Milestone Design
Break big goals into checkable milestones:
- Marathon: 5k → 10k → half marathon → full
- Save €10k: €2.5k per quarter
- Learn Spanish: A1 → A2 → B1
- Each milestone is a mini-celebration

## Folder Structure
```
~/goals/
├── active/
│   ├── run-marathon-2024.md
│   └── save-10k.md
├── achieved/
├── abandoned/
└── someday.md
```

## Progress Tracking
- Log updates when progress happens
- Quantify when possible: "Week 8: ran 15km"
- Note blockers and breakthroughs
- Keep log brief — not a journal

## Review Cadence
- Weekly: glance at active goals, any action needed?
- Monthly: real progress check, adjust if needed
- Quarterly: deep review, add/remove goals
- Yearly: major reflection, set next year's goals

## Quarterly Review Prompts
- Which goals progressed? Which stalled?
- Any goals no longer matter? → abandon or pause
- New goals to add?
- Are milestones still realistic?
- What's blocking the stuck ones?

## Yearly Review
- What did you achieve this year?
- What did you learn from abandoned goals?
- What themes emerge?
- What do you want next year to be about?
- 3-5 goals maximum for the year

## Goal Limits
- Maximum 3-5 active goals — more means diluted focus
- One "big" goal at a time — marathon training doesn't mix with startup launch
- Someday list for future goals — parking lot, not commitment
- Quarterly rotation — finish or abandon before adding

## When Goals Stall
- No progress in 30+ days → surface in review
- Ask: still important? → if no, abandon guilt-free
- Ask: what's blocking? → solve or accept
- Ask: break down smaller? → maybe milestone too big

## Abandoning Goals
- Not failure — priorities change, that's life
- Move to abandoned with note: why stopped
- Extract lessons: what would you do differently?
- Make room for goals that matter now

## What NOT To Suggest
- SMART goals framework obsessively — clarity matters, acronyms don't
- Too many goals — focus beats quantity
- Guilt about abandoned goals — they served their purpose
- Complex tracking systems — simple file is enough

## Motivation Maintenance
- Revisit "why" when motivation dips
- Celebrate milestones — don't just move to next
- Share with accountability partner if helpful
- Visualize completion — what does life look like after?

## Goal Categories (Optional)
- Health & fitness
- Career & work
- Financial
- Relationships
- Learning & growth
- Creative
- Don't force categories — use if helpful

## Integration Points
- Projects: goals spawn projects
- Habits: goals require habits
- Journal: reflect on goal progress
- Calendar: milestone deadlines

## Someday Goals
- Ideas not ready for commitment
- Review quarterly — promote or keep parking
- No shame in long someday list
- "Would be nice but not now" is valid
