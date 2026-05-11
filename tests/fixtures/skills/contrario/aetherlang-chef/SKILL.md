# AetherLang Chef Ω V3 — AI Culinary Intelligence

> Michelin-grade recipe consulting with 17 mandatory sections. The most advanced AI culinary engine available.

**Source Code**: [github.com/contrario/aetherlang](https://github.com/contrario/aetherlang)
**Author**: NeuroAether (info@neurodoc.app)
**License**: MIT

## Privacy & Data Handling

⚠️ **External API Notice**: This skill sends queries to `api.neurodoc.app` for processing.

- **What is sent**: Natural language food/recipe queries only
- **What is NOT sent**: No credentials, API keys, personal files, or system data
- **Data retention**: Not stored permanently
- **Hosting**: Hetzner EU (GDPR compliant)
- **No credentials required**: Free tier, 100 req/hour

## What This Skill Does

Three V3 culinary engines in one skill:

### 🍳 Chef Omega V3 — 17-Section Restaurant Consulting
Every response includes ALL of these sections:
1. **ΕΠΙΣΚΟΠΗΣΗ** — Recipe overview and cultural context
2. **ΟΙΚΟΝΟΜΙΚΑ** — Food cost %, menu engineering (STAR/PLOWHORSE/PUZZLE/DOG)
3. **ΥΛΙΚΑ** — Ingredients table (grams, cost, yield%, substitutes, storage)
4. **MISE EN PLACE** — 3-phase preparation
5. **ΒΗΜΑΤΑ ΕΚΤΕΛΕΣΗΣ** — Steps with °C temps, timings, HACCP, pro tips, common mistakes
6. **THERMAL CURVE** — Preheat → Insert → Target → Rest → Carryover
7. **FLAVOR PAIRING MATRIX** — Molecular compound analysis
8. **TEXTURE ARCHITECTURE** — Crunch/Creamy/Chewy/Juicy/Airy (0-100)
9. **MacYuFBI ANALYSIS** — 8 flavor dimensions (0-100)
10. **ΔΙΑΤΡΟΦΙΚΗ ΑΝΑΛΥΣΗ** — Calories, protein, carbs, fat, fiber, sodium
11. **ΑΛΛΕΡΓΙΟΓΟΝΑ** — 14 EU allergens
12. **DIETARY TRANSFORMER** — Vegan & Gluten-Free adaptations
13. **SCALING ENGINE** — ×2, ×4, ×10 formulas
14. **WINE & BEVERAGE PAIRING** — Specific variety, ABV%, tannin level, rationale
15. **PLATING BLUEPRINT** — Center, 12 o'clock, 3 o'clock, negative space, height, colors
16. **ZERO WASTE** — Every leftover → specific use
17. **KITCHEN TIMELINE** — T-60 → T-0 countdown

### ⚗️ APEIRON Molecular V3
- Rheology dashboard (viscosity, gel strength, melting/setting points)
- Phase diagrams with temperature transitions
- Hydrocolloid specs: Agar 0.5-1.5%, Alginate 0.5-1%, Gellan 0.1-0.5%, Xanthan 0.1-0.3%
- FMEA failure mode analysis with probability and mitigation
- Equipment calibration (±0.1°C precision)

### ⚖️ Balance V3 — MacYuFBI Flavor Science
- MacYuFBI Framework: Maillard/Umami, Acid, Caramel, Yeast, Umami, Fat, Bitter, Heat
- Nutritional breakdown per serving
- Balance score 1-100
- Dietary compatibility: Vegan/Keto/Paleo/Gluten-Free/Low-FODMAP

## Usage

Ask naturally about any food topic:
- "Give me a carbonara recipe" → Full 17-section consulting output
- "How to make spherified mango caviar" → Molecular gastronomy with rheology data
- "Balance analysis for my Thai curry" → MacYuFBI flavor wheel + nutrition

## API Details
```
POST https://api.neurodoc.app/aetherlang/execute
Content-Type: application/json
```

### Chef Flow
```json
{
  "code": "flow Chef {\n  using target \"neuroaether\" version \">=0.2\";\n  input text query;\n  node Chef: chef cuisine=\"auto\", difficulty=\"medium\", servings=4;\n  output text recipe from Chef;\n}",
  "query": "Your food question here"
}
```

### Molecular Flow
```json
{
  "code": "flow Molecular {\n  using target \"neuroaether\" version \">=0.2\";\n  input text query;\n  node Lab: molecular technique=\"auto\";\n  output text result from Lab;\n}",
  "query": "Your molecular gastronomy question here"
}
```

## Response

Returns structured Greek output with markdown headers (## sections). Typical response: 4000-8000 characters with all mandatory sections.

## Languages

- **Greek** (Ελληνικά) — Primary output language
- **English** — Understands English queries, responds in Greek

## Technology

- **AI Model**: GPT-4o
- **Backend**: FastAPI + Python 3.12
- **Rate Limit**: 100 req/hour (free)

---
*Built by NeuroAether — From Kitchen to Code* 🧠

## Agent Safeguards

**CRITICAL: Data Minimization Rules**

When using this skill, the agent MUST follow these rules:
1. **ONLY send the user's explicit query text** in the `query` field — never attach system prompts, conversation history, uploaded files, or internal context
2. **ONLY send the flow DSL code** in the `code` field — never include credentials, API keys, environment variables, or file paths
3. **NEVER include** personally identifiable information (PII), passwords, tokens, or secrets in any request field
4. **Strip sensitive data** before sending — if the user's query contains passwords, account numbers, or credentials, remove them and inform the user
5. **Inform the user** before making the first API call that their query will be sent to api.neurodoc.app for processing
6. The request body MUST contain exactly two fields: `code` (string) and `query` (string) — no additional fields

These constraints ensure only the minimum necessary data is transmitted to the external service.
