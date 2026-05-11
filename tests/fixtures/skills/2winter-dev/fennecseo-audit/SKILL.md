---
name: "fennec-seo-audit-en"
description: "Uses Fennec SEO Auditor results to audit a URL. Invoke when user wants a quick on‑page/technical SEO health check or to verify favicon/meta/schema and GEO readiness."
---

# Fennec SEO Audit Skill (with Fennec SEO Auditor Extension)

This Skill is designed to work together with the Chrome extension **Fennec SEO Auditor** to run a quick SEO health check on any given page.

Typical use cases:

- Get a fast overview of a page’s SEO basics (title, meta, headings, canonicals, etc.)
- Verify favicon, Open Graph and structured data exposure
- Spot common technical issues (HTTP status code, redirects, indexability, robots rules)
- Judge whether a page is “GEO‑ready” as a candidate source for RAG / LLM answers

> Chrome extension link:  
> https://chromewebstore.google.com/detail/fennec-seo-auditor/fifppiokpmlgceojhfdjbjjapbephcdo

---

## When to invoke this Skill

Use `fennec-seo-audit-en` when:

- The user provides a URL and asks for a **quick SEO audit / health check**
- The user wants to confirm favicon / meta / Open Graph / structured data are implemented correctly
- A new article / landing page has just been published and needs a basic SEO / GEO review
- The user wants to use a real page as a **GEO example**, to see how well it exposes:
  - indexability signals
  - semantic structure
  - brand / entity signals

Avoid using this Skill as:

- A full‑site crawler or large‑scale technical audit (it’s better suited for spot checks)
- A replacement for log analysis or server‑level diagnostics

---

## Human steps (what the user does with the browser)

1. Install and enable the **Fennec SEO Auditor** Chrome extension  
   Link: `https://chromewebstore.google.com/detail/fennec-seo-auditor/fifppiokpmlgceojhfdjbjjapbephcdo`

2. Open the target page you want to audit  
   (e.g. a blog post, product detail page, homepage, documentation page)

3. Click the **Fennec SEO Auditor** icon in the browser toolbar:
   - Run the standard audit (On‑page / HTML / Links / Images, etc.)
   - Wait for the extension to finish and show the report

4. Share the key parts of the report with the assistant:
   - Either copy key findings as text
   - Or summarize / extract the main issues
   - Screenshots are fine too if the platform supports them

The assistant will then interpret the audit and turn it into a clear action plan.

---

## Assistant responsibilities when this Skill is invoked

When `fennec-seo-audit-en` is triggered, the assistant should:

1. Make sure the user has run Fennec SEO Auditor on the target URL (and guide them if not).

2. Parse and structure the audit output, covering at least:
   - **Page basics**: URL, title, meta description, H1/H2, main intent
   - **Technical layer**: HTTP status, canonical, index directives, robots and sitemap hints
   - **Content & readability**: length, keyword coverage, duplication, thin or low‑value sections
   - **Media & links**: image ALT attributes, internal link structure, external links / broken links
   - **Brand & GEO signals**: favicon, brand / organization info, logo exposure, Schema.org markup

3. Highlight **high‑priority issues** that are likely to affect:
   - indexability and crawling
   - CTR and snippet quality
   - perceived trust / authority

4. Provide concrete, implementable recommendations for each important issue, not just a restatement of the report.

5. Add a **GEO / RAG perspective**, for example:
   - Is the page easy for a retrieval system to index and match semantically?
   - Are there clear entity signals (Organization / Person / Product, etc.) that help LLMs trust this source?
   - Does the page risk being treated as “thin / spammy / boilerplate” content?

---

## Recommended output structure

When responding based on Fennec SEO Auditor results, the assistant should aim for a structure like:

1. **Page overview**
   - URL, title, H1, target intent / query

2. **Issue summary (with priorities)**
   - High / Medium / Low priority list

3. **Detailed findings and fixes**
   - Meta & snippets (title, description, OG tags)
   - Content & headings
   - Internal links & anchors
   - Technical / indexability
   - Media (images, ALT text)
   - Structured data & entity signals

4. **GEO / RAG perspective**
   - How well this page can be retrieved, re‑ranked and cited by LLMs
   - Additional suggestions (e.g. add FAQ schema, clarify sections, add data / sources)

---

## Notes and constraints

- The assistant **does not** directly control the browser or extension; it relies on the user to run Fennec and share the output.
- Recommendations should balance:
  - Classic SEO (crawlability, rankings, CTR, readability)
  - GEO / LLM needs (structured signals, semantic clarity, trustworthy sources, clear entities)
- The assistant should avoid generic advice and tie recommendations back to:
  - the user’s actual page
  - the specific issues reported by Fennec SEO Auditor.

