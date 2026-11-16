# newkwlab-ai-site-check

**Is your website visible to AI?** A free, zero-dependency checker that tells you whether ChatGPT, Claude, Perplexity and Google AI can actually see, crawl and understand your site — plus a starter `llms.txt` generator.

By [NewKwLab](https://api.newkwlab.com) · MIT license · Python 3.10+, no packages to install.

```bash
python3 ai_site_check.py https://your-site.com
```

```
✅ [robots.txt] robots.txt exists (10/10) — Found and parsed.
✅ [robots.txt] AI crawlers are allowed (15/15) — All 6 major AI crawlers may crawl / …
✅ [llms.txt] llms.txt exists and is usable (25/25) — Valid structure: H1 title and 14 links (612 words).
✅ [sitemap.xml] Sitemap lists reachable pages (15/15) — 23 URLs listed …
✅ [Raw HTML] Real content ships in the raw HTML (10/10) — 1,316 words of text are in the raw HTML …

Score: 100/100 (grade A) · reports in ./report.md and report.html
```

## Why this exists

Search is splitting in two. People still Google — but they also ask ChatGPT, Claude and Perplexity, and those systems answer from what their crawlers could fetch and understand. Most sites were never checked for that second audience:

- A `robots.txt` copied from a template can silently block GPTBot, ClaudeBot or PerplexityBot.
- Almost no site ships an `llms.txt` — the file format built so LLMs can understand a site's structure and facts.
- JavaScript-heavy pages often serve AI crawlers an empty shell: the content exists only after scripts run, and most AI crawlers don't run them.

This tool checks those four things in one run and writes a shareable report (`report.md` / `report.html`) you can hand to a client, a teammate, or your future self.

## What it checks

| Area | Checks |
| --- | --- |
| robots.txt | File exists; whether GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, PerplexityBot and Google-Extended may crawl `/` |
| llms.txt | File exists; valid structure (H1 title, markdown links, substance) |
| sitemap.xml | Discovered via robots.txt or the default path; URL count; sample of listed URLs actually answers HTTP 200 |
| Raw HTML | Homepage fetchable as GPTBot; `<title>`, meta description, single H1, canonical; at least ~300 words of real text in the raw HTML (no JavaScript executed) |

Scoring is out of 100, graded A–F. The checks encode a simple rule we use for every site we ship: content in raw HTML, an explicit welcome for AI crawlers, a complete sitemap, and an llms.txt that introduces the site.

## Generate a starter llms.txt

```bash
python3 ai_site_check.py https://your-site.com --generate-llms llms.txt
```

Reads your sitemap, visits each page (up to 50), and drafts an `llms.txt` grouped by section with page titles and descriptions. Review it, fix the wording, ship it — it takes ten minutes and gives LLMs a map of your site written for them.

## Use it in CI

```bash
python3 ai_site_check.py https://your-site.com --fail-under 70
# exits 1 when the score drops below 70
```

`--json results.json` writes the raw checks and facts for your own dashboards.

## Honest limits

- A high score means AI crawlers *can* see and understand your site. It does not guarantee being cited in AI answers — nobody can promise that, and you should distrust anyone who does.
- The checker fetches pages the way crawlers do (no JavaScript execution). If your framework server-renders, you're fine; if it doesn't, the report shows you exactly what crawlers see.
- robots.txt evaluation covers the `/` path and the six crawlers above, using longest-match rules — the cases that decide real-world access.

## Doing this at scale

Checking one site is free forever with this tool. If you need portfolio-wide checks, scheduled re-checks and change alerts across many domains, that's what the [NewKwLab API](https://api.newkwlab.com/bundle) is for — the same checks, run in bulk, with credits that never expire.

## License

MIT. Use it, fork it, ship it. A link back is appreciated but not required.
