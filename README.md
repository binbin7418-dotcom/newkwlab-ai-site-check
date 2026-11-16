# AI Site Check — Is your website visible to AI?

**One command tells you whether ChatGPT, Claude, Perplexity and Google AI can actually fetch, crawl and understand your site — scored out of 100, with a report you can share.**

Zero dependencies. One Python file. No account, no API key, nothing phones home.

## See it run

This is a real run against one of our own sites (2026-11-16). It scored 95/100 — and the one failing check is the point:

```bash
$ python3 ai_site_check.py https://pitchreel.newkwlab.com
```

```
✅ [Raw HTML] GPTBot can fetch the homepage (5/5) — GPTBot received HTTP 200.
✅ [robots.txt] robots.txt exists (10/10) — Found and parsed.
✅ [robots.txt] AI crawlers are allowed (15/15) — All 6 major AI crawlers may crawl / …
✅ [llms.txt] llms.txt exists and is usable (25/25) — Valid structure: H1 title and 7 links (202 words).
✅ [sitemap.xml] Sitemap lists reachable pages (15/15) — 9 URLs listed … 5/5 of the first URLs answer HTTP 200.
✅ [Raw HTML] Page has a <title> (5/5) — Title: “PitchReel — Your resume, on camera.”
✅ [Raw HTML] Page has a meta description (5/5) — Present.
✅ [Raw HTML] Page has exactly one clear H1 (5/5) — H1: “Your resume, on camera.”
✅ [Raw HTML] Real content ships in the raw HTML (10/10) — 987 words of text are in the raw HTML …
⚠️ [Raw HTML] Canonical URL is declared (0/5) — No canonical link — duplicate URLs can split your citations.

Score: 95/100 (grade A) · reports in ./report.md and report.html
```

Every run also writes a shareable `report.md` and `report.html`. Full sample: [SAMPLE-REPORT.md](SAMPLE-REPORT.md) — Firecrawl's own site, 100/100.

### Real scores from the first runs (2026-11-16)

| Site | Score | What decided it |
| --- | --- | --- |
| firecrawl.dev | 100/100 (A) | llms.txt with 205 links, 4,046 words in raw HTML |
| pitchreel.newkwlab.com (ours) | 95/100 (A) | Everything passed except a missing canonical |
| api.newkwlab.com (ours) | 75/100 (B) | **No llms.txt at all (HTTP 404)** — fixed the same day |
| example.com | 21/100 (F) | No llms.txt, no sitemap, 20-odd words of content |

We built this because our own sites were failing checks we didn't know existed. Yours might be too — it takes one command to find out.

## Run it in 2 minutes

Requires Python 3.10+. Nothing to install — the checker is a single file using only the standard library.

```bash
# grab the file (or clone this repo)
curl -O https://raw.githubusercontent.com/binbin7418-dotcom/newkwlab-ai-site-check/main/ai_site_check.py

# check any site
python3 ai_site_check.py https://your-site.com
```

That's it. The score prints in the terminal; the detailed report lands in `./report.md` and `./report.html`.

## What it checks

Search now has two audiences. People still Google — but they also ask ChatGPT, Claude and Perplexity, and those systems answer from what *their* crawlers could fetch and understand. Most sites have never been checked for that second audience. This tool checks the four things that decide it, in one run:

| Area | Points | What it verifies |
| --- | --- | --- |
| GPTBot fetch | 5 | The homepage is fetched *as GPTBot* first — a 401/403 here means ChatGPT's crawler is refused at the door |
| robots.txt | 10 + 15 | File exists and parses; whether GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, PerplexityBot and Google-Extended may crawl `/` (longest-match rules, the way crawlers actually resolve them) |
| llms.txt | 25 | The file exists and is usable: H1 title, real markdown links, actual substance — weighted highest because it's the biggest binary gap on most sites |
| sitemap.xml | 15 | Discovered via robots.txt or the default path; URL count; a sample of listed URLs actually answers HTTP 200 |
| Raw HTML | 30 | `<title>`, meta description, exactly one H1, canonical, and at least ~300 words of real text in the HTML *as served* — no JavaScript executed, because most AI crawlers don't run it |

Scores grade A (≥85) to F (<30). The checks encode the rule we now apply to every site we ship: real content in the raw HTML, an explicit welcome for AI crawlers, a complete sitemap, and an llms.txt that introduces the site.

## A complete sample report

So you can see exactly what you get before you run anything, here is a full
report — our own production site, checked with this tool on 2026-11-16:

**https://api.newkwlab.com — Score: 95/100 (grade A)** · 10 checks: 9 pass, 1 warning, 0 fail

| Area | Result |
| --- | --- |
| robots.txt | ✅ 25/25 — file found; all 6 major AI crawlers (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, PerplexityBot, Google-Extended) allowed to crawl `/` |
| llms.txt | ⚠️ 20/25 — present with a valid H1, but thin: 0 links, 339 words |
| sitemap.xml | ✅ 15/15 — 9 URLs listed; sample check 5/5 answer HTTP 200 |
| Raw HTML | ✅ 35/35 — GPTBot fetches HTTP 200; title, meta description, single H1 and canonical present; 475 words of real text in the raw HTML |

**Key finding:** the only lost points come from the `llms.txt` — it introduces
the site in prose but links to none of its pages, so AI readers get a summary
with no map.

**Action plan (from the same report):** add one markdown link per page to
`llms.txt` (the 9 sitemap URLs, one-line description each) → llms.txt 20/25 →
25/25 and the score 95 → 100; change nothing else; re-run the checker to
confirm the new score on a dated run.

📄 **[Read the full sample report](SAMPLE-REPORT-FULL.md)** — every check
itemised with its evidence, findings ordered by impact, and the full action
plan. The machine output of the same run lives in `test-runs/`
(`api-newkwlab-20261116-report.md` / `.json` / `-stdout.txt`).

## Found a problem? Generate a starter llms.txt

```bash
python3 ai_site_check.py https://your-site.com --generate-llms llms.txt
```

Reads your sitemap, visits each page (up to 50), and drafts an `llms.txt` grouped by section with page titles and descriptions. Review it, fix the wording, ship it — ten minutes from "missing" to "done".

## Use it in CI

```bash
python3 ai_site_check.py https://your-site.com --fail-under 70
# exits 1 when the score drops below 70
```

`--json results.json` writes the raw checks and facts for your own dashboards. `--out DIR` changes where the reports go.

## Honest limits

- A high score means AI crawlers *can* see and understand your site. It does not guarantee being cited in AI answers — nobody can promise that, and you should distrust anyone who does.
- The checker fetches pages the way crawlers do (no JavaScript execution). If your framework server-renders, you're fine; if it doesn't, the report shows you exactly what crawlers see.
- robots.txt evaluation covers the `/` path and the six crawlers above — the cases that decide real-world access.

## Issues and ideas

Found a site that scores wrong, or a check you wish existed? Open an issue — real-world failures are how the check list grows. The roadmap follows feedback: what people actually hit gets built first.

---

## Built by NewKwLab

Made by [NewKwLab](https://api.newkwlab.com), a one-person studio shipping small APIs and tools. We run this check on every site we launch; the five-gate launch checklist it comes from is how our own llms.txt 404 got caught.

Checking one site is free forever with this tool. If you need portfolio-wide checks, scheduled re-checks and change alerts across many domains, that's the [NewKwLab API bundle](https://api.newkwlab.com/bundle?utm_source=github&utm_medium=readme&utm_campaign=ai-site-check) — the same checks, run in bulk, with credits that never expire.

## License

MIT. Use it, fork it, ship it. A link back is appreciated but not required.
