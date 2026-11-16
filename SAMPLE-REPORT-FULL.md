# Sample report (full) — https://api.newkwlab.com

This is a complete, unedited-in-substance report from a real run of
[newkwlab-ai-site-check](https://github.com/binbin7418-dotcom/newkwlab-ai-site-check)
against our own production site, run 2026-11-16. Every number below is the tool's
actual output for that run — nothing is rounded, mocked or carried over from an
earlier run. The machine output of this exact run is archived in the repo at
`test-runs/api-newkwlab-20261116-report.md` (markdown), `test-runs/api-newkwlab-20261116.json`
(raw checks and facts) and `test-runs/api-newkwlab-20261116-stdout.txt` (console log).

**Checked:** https://api.newkwlab.com · 2026-11-16 11:19 UTC
**Score: 95/100 — grade A**
**Result at a glance:** 10 checks — 9 pass, 1 warning, 0 fail. One fixable gap costs the only 5 points.

---

## Itemised results

| # | Area | Check | Result | Points | What the checker found |
|---|------|-------|--------|--------|------------------------|
| 1 | Raw HTML | GPTBot can fetch the homepage | ✅ Pass | 5/5 | GPTBot received HTTP 200. |
| 2 | robots.txt | robots.txt exists | ✅ Pass | 10/10 | Found and parsed. |
| 3 | robots.txt | AI crawlers are allowed | ✅ Pass | 15/15 | All 6 major AI crawlers may crawl /: GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, PerplexityBot, Google-Extended. |
| 4 | llms.txt | llms.txt exists and is usable | ⚠️ Warning | 20/25 | Present but thin: H1=yes, 0 links, 339 words. |
| 5 | sitemap.xml | Sitemap lists reachable pages | ✅ Pass | 15/15 | 9 URLs listed in https://api.newkwlab.com/sitemap.xml. Sample check: 5/5 of the first URLs answer HTTP 200. |
| 6 | Raw HTML | Page has a `<title>` | ✅ Pass | 5/5 | Title: "NewKWLab — Small tools, finished results" |
| 7 | Raw HTML | Page has a meta description | ✅ Pass | 5/5 | Present. |
| 8 | Raw HTML | Page has exactly one clear H1 | ✅ Pass | 5/5 | H1: "Small tools. Finished results." |
| 9 | Raw HTML | Real content ships in the raw HTML | ✅ Pass | 10/10 | 475 words of text are in the raw HTML — AI crawlers read it without running JavaScript. |
| 10 | Raw HTML | Canonical URL is declared | ✅ Pass | 5/5 | Present. |
| | | **Total** | | **95/100** | |

Section subtotals: robots.txt 25/25 · llms.txt 20/25 · sitemap.xml 15/15 · Raw HTML & fetchability 35/35.

---

## Key findings (ordered by impact)

1. **The only deduction is the llms.txt (−5 points).** The file exists and has a
   valid H1, but it contains **0 links** across 339 words. As it stands, an AI
   system that reads it gets a prose introduction to the site but no map of its
   pages — the links are the part of the format that tells crawlers where the
   substance lives. This is a content gap in one file, not a structural problem.
2. **Crawler access is fully open and explicit (25/25 on robots.txt).** All six
   major AI crawlers — GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot,
   PerplexityBot and Google-Extended — are allowed to crawl `/`. Nothing in
   robots.txt silently blocks the AI audience.
3. **The homepage is readable without JavaScript (35/35 on raw HTML).**
   GPTBot fetches it with HTTP 200 and finds 475 words of real text in the raw
   HTML, plus a title, a meta description, exactly one H1 and a canonical URL.
   Crawlers that never execute scripts still get the full message.
4. **The sitemap is complete and alive (15/15).** 9 URLs are listed, and every
   sampled URL (5/5) answers HTTP 200 — no dead entries diluting the map.

---

## Action plan

| # | Change | Why (tied to the check above) | Expected effect on the report |
|---|--------|-------------------------------|-------------------------------|
| 1 | Add markdown links to `llms.txt`: one link per page (the 9 URLs already in the sitemap), each with a one-line description of what the page does. | Check #4 is the only non-perfect item: the file has an H1 and 339 words but 0 links, so AI readers get prose with no page map. | llms.txt item 20/25 → 25/25; total score 95 → 100. |
| 2 | Change nothing else on the homepage, robots.txt or sitemap. | Checks #1–3 and #5–10 are all at full points; touching them risks regressing a passing item. | Keeps the other 75 points stable. |
| 3 | Re-run the checker after change #1 and archive the new report next to this one. | A fix only counts when a fresh run shows it; the tool exits non-zero under a threshold with `--fail-under`, so the re-run doubles as the verification gate. | Confirms 100/100 (grade A) on a dated, reproducible run. |

---

*Checked with newkwlab-ai-site-check v1.0.0 by NewKwLab. A high score means AI
crawlers can see and understand the site; it is not a promise of being cited in
AI answers. Need this across a whole portfolio, on a schedule, with change
alerts? The NewKwLab API runs it in bulk: https://api.newkwlab.com/bundle*
