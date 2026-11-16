#!/usr/bin/env python3
"""
ai-site-check — Is your website visible to AI?

Checks whether a website can actually be seen, crawled and understood by
AI systems (ChatGPT, Claude, Perplexity, Google AI Overviews):

  1. robots.txt  — are the major AI crawlers allowed in?
  2. llms.txt    — does the site explain itself to LLMs, in the llms.txt format?
  3. sitemap.xml — can crawlers discover every page?
  4. Raw HTML    — is the real content in the HTML, or hidden behind JavaScript?

Also generates a starter llms.txt from your sitemap (--generate-llms).

Zero dependencies. Python 3.10+. By NewKwLab — https://api.newkwlab.com
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone

VERSION = "1.0.0"
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
GPTBOT_UA = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2; +https://openai.com/gptbot"

# AI crawlers that matter in 2026: (robots token, display name, used by)
AI_BOTS = [
    ("gptbot", "GPTBot", "ChatGPT training crawl"),
    ("oai-searchbot", "OAI-SearchBot", "ChatGPT search index"),
    ("chatgpt-user", "ChatGPT-User", "ChatGPT live browsing"),
    ("claudebot", "ClaudeBot", "Claude (Anthropic)"),
    ("perplexitybot", "PerplexityBot", "Perplexity"),
    ("google-extended", "Google-Extended", "Gemini / AI Overviews"),
]

CTX = ssl.create_default_context()
TIMEOUT = 20


def _fetch_once(url: str, ua: str) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "text/html,application/xml,text/plain;q=0.9,*/*;q=0.5",
        "Accept-Encoding": "identity",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
            status, headers = r.status, dict(r.headers)
            try:
                raw = r.read(4_000_000)
            except Exception as read_err:
                # Truncated transfer: a partial page still answers most checks.
                partial = getattr(read_err, "partial", b"")
                if not partial:
                    raise
                raw = partial
            charset = r.headers.get_content_charset() or "utf-8"
            return status, headers, raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        try:
            raw = e.read(200_000)
            return e.code, dict(e.headers or {}), raw.decode("utf-8", errors="replace")
        except Exception:
            return e.code, {}, ""
    except Exception:
        return 0, {}, ""


def fetch(url: str, ua: str = BROWSER_UA) -> tuple[int, dict, str]:
    """Return (status, headers, body_text). Status 0 = network error.
    Network errors retry with backoff — a dropped packet is not a finding."""
    import time
    status, headers, body = _fetch_once(url, ua)
    for delay in (2, 4):
        if status != 0:
            break
        time.sleep(delay)
        status, headers, body = _fetch_once(url, ua)
    return status, headers, body


def origin_of(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}"


# ---------------------------------------------------------------- robots.txt
@dataclass
class RobotsGroup:
    agents: list[str] = field(default_factory=list)
    rules: list[tuple[str, str]] = field(default_factory=list)  # (allow|disallow, path)


def parse_robots(text: str) -> tuple[list[RobotsGroup], list[str]]:
    groups: list[RobotsGroup] = []
    sitemaps: list[str] = []
    current: RobotsGroup | None = None
    seen_rule = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key == "sitemap":
            sitemaps.append(val)
        elif key == "user-agent":
            if current is None or seen_rule:
                current = RobotsGroup()
                groups.append(current)
                seen_rule = False
            current.agents.append(val.lower())
        elif key in ("allow", "disallow") and current is not None:
            current.rules.append((key, val))
            seen_rule = True
    return groups, sitemaps


def bot_allowed(groups: list[RobotsGroup], token: str, path: str = "/") -> bool | None:
    """True/False if a rule decides, None if no group mentions the bot or *."""
    mentioned = False
    best: tuple[int, bool] | None = None  # (path length, allowed)
    for g in groups:
        if token not in g.agents and "*" not in g.agents:
            continue
        if token in g.agents:
            mentioned = True
        for kind, rule_path in g.rules:
            if rule_path == "":
                continue
            if path.startswith(rule_path):
                cand = (len(rule_path), kind == "allow")
                if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1]):
                    best = cand
    if best is not None:
        return best[1]
    return True if mentioned or groups else None


# ------------------------------------------------------------------- checks
@dataclass
class Check:
    group: str
    name: str
    status: str  # pass | warn | fail
    points: float
    max_points: float
    detail: str


from html.parser import HTMLParser


class _PageParser(HTMLParser):
    """Regex-free extraction: visible text, title, H1s, meta description, canonical."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.h1_texts: list[str] = []
        self.meta_desc = ""
        self.canonical = False
        self._in_title = False
        self._h1_buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._h1_buf = []
        elif tag == "meta" and a.get("name", "").lower() == "description":
            self.meta_desc = a.get("content", "")
        elif tag == "link" and "canonical" in a.get("rel", ""):
            self.canonical = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "h1" and self._h1_buf is not None:
            self.h1_texts.append(re.sub(r"\s+", " ", "".join(self._h1_buf)).strip())
            self._h1_buf = None

    def handle_data(self, data):
        if self.skip:
            return
        self.parts.append(data)
        if self._in_title:
            self.title_parts.append(data)
        if self._h1_buf is not None:
            self._h1_buf.append(data)


def parse_page(html: str) -> _PageParser:
    p = _PageParser()
    try:
        p.feed(html)
    except Exception:
        pass
    return p


def strip_to_text(html: str) -> str:
    return re.sub(r"\s+", " ", " ".join(parse_page(html).parts)).strip()


def page_meta(html: str) -> tuple[str, str]:
    p = parse_page(html)
    return re.sub(r"\s+", " ", "".join(p.title_parts)).strip(), p.meta_desc.strip()


def run_checks(base_url: str) -> tuple[list[Check], dict]:
    checks: list[Check] = []
    facts: dict = {}
    origin = origin_of(base_url)

    # Fetch the homepage the way an AI crawler would first.
    status_ai, _, html_ai = fetch(base_url, ua=GPTBOT_UA)
    facts["gptbot_http_status"] = status_ai
    if status_ai in (401, 403):
        checks.append(Check("Raw HTML", "GPTBot can fetch the homepage", "fail", 0, 5,
                            f"Server answered GPTBot with HTTP {status_ai} — ChatGPT's crawler is refused at the door."))
        status, _, html = fetch(base_url)
    else:
        checks.append(Check("Raw HTML", "GPTBot can fetch the homepage",
                            "pass" if status_ai == 200 else "warn",
                            5 if status_ai == 200 else 2, 5,
                            f"GPTBot received HTTP {status_ai}."))
        status, html = status_ai, html_ai
    facts["homepage_http_status"] = status
    if status != 200 or not html:
        checks.append(Check("Raw HTML", "Homepage is reachable", "fail", 0, 5,
                            f"Homepage returned HTTP {status}; content checks skipped."))
        return checks, facts

    # ------------------------------------------------------------- robots
    r_status, _, robots_txt = fetch(origin + "/robots.txt")
    if r_status == 200 and robots_txt.strip():
        groups, sitemaps = parse_robots(robots_txt)
        facts["robots_sitemaps"] = sitemaps
        checks.append(Check("robots.txt", "robots.txt exists", "pass", 10, 10, "Found and parsed."))
        blocked, allowed = [], []
        for token, name, _ in AI_BOTS:
            verdict = bot_allowed(groups, token)
            (allowed if verdict else blocked).append(name)
        per_bot = 15 / len(AI_BOTS)
        pts = per_bot * len(allowed)
        if not blocked:
            checks.append(Check("robots.txt", "AI crawlers are allowed", "pass", pts, 15,
                                "All 6 major AI crawlers may crawl /: " + ", ".join(allowed) + "."))
        elif not allowed:
            checks.append(Check("robots.txt", "AI crawlers are allowed", "fail", 0, 15,
                                "Every major AI crawler is blocked from /: " + ", ".join(blocked) + "."))
        else:
            checks.append(Check("robots.txt", "AI crawlers are allowed", "warn", pts, 15,
                                "Allowed: " + ", ".join(allowed) + ". Blocked: " + ", ".join(blocked) + "."))
    else:
        sitemaps = []
        checks.append(Check("robots.txt", "robots.txt exists", "fail", 0, 10,
                            f"No usable robots.txt (HTTP {r_status}). Crawlers guess; AI crawlers get no explicit welcome."))
        checks.append(Check("robots.txt", "AI crawlers are allowed", "warn", 7.5, 15,
                            "No robots.txt means nothing is blocked — but nothing is explicitly allowed or guided either."))

    # ------------------------------------------------------------- llms.txt
    l_status, _, llms = fetch(origin + "/llms.txt")
    if l_status == 200 and llms.strip():
        links = re.findall(r"\[[^\]]+\]\([^)]+\)", llms)
        has_h1 = bool(re.search(r"(?m)^#\s+\S", llms))
        words = len(llms.split())
        facts["llms_links"] = len(links)
        pts, notes = 15, []
        if has_h1 and len(links) >= 3:
            pts += 10
            notes.append(f"Valid structure: H1 title and {len(links)} links ({words} words).")
        elif has_h1 or links:
            pts += 5
            notes.append(f"Present but thin: H1={'yes' if has_h1 else 'no'}, {len(links)} links, {words} words.")
        else:
            notes.append("File exists but has no H1 title and no markdown links — LLMs will ignore it.")
        checks.append(Check("llms.txt", "llms.txt exists and is usable",
                            "pass" if pts >= 25 else "warn", pts, 25, " ".join(notes)))
    else:
        checks.append(Check("llms.txt", "llms.txt exists and is usable", "fail", 0, 25,
                            f"No llms.txt (HTTP {l_status}). The site never introduces itself to LLMs in the format built for them."))

    # ------------------------------------------------------------- sitemap
    sm_url = sitemaps[0] if sitemaps else origin + "/sitemap.xml"
    s_status, _, sm = fetch(sm_url)
    locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sm) if s_status == 200 else []
    facts["sitemap_url_count"] = len(locs)
    if s_status == 200 and locs:
        pts, detail = 8, f"{len(locs)} URLs listed in {sm_url}."
        if len(locs) >= 5:
            pts += 4
        ok = 0
        for u in locs[:5]:
            st, _, _ = fetch(u.strip())
            ok += 1 if st == 200 else 0
        pts += 3 if ok == min(5, len(locs)) else (1 if ok else 0)
        detail += f" Sample check: {ok}/{min(5, len(locs))} of the first URLs answer HTTP 200."
        checks.append(Check("sitemap.xml", "Sitemap lists reachable pages",
                            "pass" if pts >= 13 else "warn", pts, 15, detail))
    else:
        checks.append(Check("sitemap.xml", "Sitemap lists reachable pages", "fail", 0, 15,
                            f"No usable sitemap at {sm_url} (HTTP {s_status}). Crawlers must guess your page list."))

    # ------------------------------------------------------------- raw HTML
    page = parse_page(html)
    text = re.sub(r"\s+", " ", " ".join(page.parts)).strip()
    words = len(text.split())
    facts["homepage_words"] = words
    title = re.sub(r"\s+", " ", "".join(page.title_parts)).strip()
    facts["title"] = title
    checks.append(Check("Raw HTML", "Page has a <title>",
                        "pass" if title else "fail", 5 if title else 0, 5,
                        f"Title: “{title[:80]}”" if title else "No <title> tag found."))
    desc = page.meta_desc.strip()
    checks.append(Check("Raw HTML", "Page has a meta description",
                        "pass" if desc else "warn", 5 if desc else 0, 5,
                        "Present." if desc else "Missing — AI answers and search results must improvise your summary."))
    h1s = page.h1_texts
    h1_text = h1s[0] if h1s else ""
    checks.append(Check("Raw HTML", "Page has exactly one clear H1",
                        "pass" if len(h1s) == 1 and h1_text else "warn",
                        5 if len(h1s) == 1 and h1_text else 2, 5,
                        f"H1: “{h1_text[:80]}”" if h1_text else f"Found {len(h1s)} H1 elements."))
    if words >= 300:
        checks.append(Check("Raw HTML", "Real content ships in the raw HTML", "pass", 10, 10,
                            f"{words} words of text are in the raw HTML — AI crawlers read it without running JavaScript."))
    elif words >= 120:
        checks.append(Check("Raw HTML", "Real content ships in the raw HTML", "warn", 5, 10,
                            f"Only {words} words in the raw HTML. Thin for AI citation; key facts may live behind JavaScript."))
    else:
        checks.append(Check("Raw HTML", "Real content ships in the raw HTML", "fail", 0, 10,
                            f"Only {words} words in the raw HTML — the page is a JavaScript shell to most AI crawlers."))
    checks.append(Check("Raw HTML", "Canonical URL is declared",
                        "pass" if page.canonical else "warn", 5 if page.canonical else 0, 5,
                        "Present." if page.canonical else "No canonical link — duplicate URLs can split your citations."))

    return checks, facts


# ------------------------------------------------------------- llms.txt gen
def generate_llms(base_url: str) -> str:
    origin = origin_of(base_url)
    _, _, robots_txt = fetch(origin + "/robots.txt")
    _, sitemaps = parse_robots(robots_txt) if robots_txt else ([], [])
    sm_url = sitemaps[0] if sitemaps else origin + "/sitemap.xml"
    _, _, sm = fetch(sm_url)
    locs = [u.strip() for u in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sm)][:50]
    if not locs:
        locs = [base_url]
    _, _, home = fetch(base_url)
    home_title, home_desc = page_meta(home)
    site_title = home_title if home_title else urllib.parse.urlparse(base_url).netloc
    site_desc = home_desc if home_desc else f"The website of {site_title}."

    sections: dict[str, list[str]] = {}
    for u in locs:
        st, _, page = fetch(u)
        if st != 200:
            continue
        t, d = page_meta(page)
        name = t if t else u
        summary = d
        path = urllib.parse.urlparse(u).path.strip("/")
        seg = path.split("/")[0] if path else "home"
        seg = re.sub(r"\.(html?|php|aspx)$", "", seg)
        section = seg.replace("-", " ").replace("_", " ").title() or "Home"
        line = f"- [{name}]({u})" + (f": {summary}" if summary else "")
        sections.setdefault(section, []).append(line)

    out = [f"# {site_title}", "", f"> {site_desc}", ""]
    for section in sorted(sections, key=lambda s: (s != "Home", s)):
        out.append(f"## {section}")
        out.extend(sections[section][:15])
        out.append("")
    out.append("<!-- Generated with newkwlab-ai-site-check by NewKwLab: "
               "https://github.com/binbin7418-dotcom/newkwlab-ai-site-check -->")
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------- reports
def grade(score: float) -> str:
    return ("A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50
            else "D" if score >= 30 else "F")


def render_reports(base_url: str, checks: list[Check], facts: dict) -> tuple[str, str, float]:
    score = round(sum(c.points for c in checks), 1)
    max_score = sum(c.max_points for c in checks)
    pct = round(100 * score / max_score) if max_score else 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}

    md = [f"# AI Visibility Report — {base_url}", "",
          f"**Score: {pct}/100 (grade {grade(pct)})** · checked {now} · "
          f"tool: newkwlab-ai-site-check v{VERSION} by NewKwLab", ""]
    cur = None
    for c in checks:
        if c.group != cur:
            md += ["", f"## {c.group}"]
            cur = c.group
        md.append(f"- {icon[c.status]} **{c.name}** ({c.points:g}/{c.max_points:g}) — {c.detail}")
    md += ["", "---",
           "Checked with [newkwlab-ai-site-check](https://github.com/binbin7418-dotcom/newkwlab-ai-site-check) "
           "by [NewKwLab](https://api.newkwlab.com). "
           "Need this for a whole portfolio, on a schedule, with change alerts? "
           "The NewKwLab API runs it in bulk: https://api.newkwlab.com/bundle", ""]
    md_text = "\n".join(md)

    rows = "\n".join(
        f"<tr><td>{c.group}</td><td>{icon[c.status]} {c.name}</td>"
        f"<td>{c.points:g}/{c.max_points:g}</td><td>{c.detail}</td></tr>" for c in checks)
    html_text = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>AI Visibility Report — {base_url}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:880px;margin:40px auto;padding:0 16px;color:#111}}
.score{{font-size:44px;font-weight:700}} table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}} th{{background:#f5f5f5}}
footer{{margin-top:32px;color:#555;font-size:14px}}</style></head><body>
<h1>AI Visibility Report</h1>
<p><strong>{base_url}</strong> · checked {now}</p>
<p class="score">{pct}/100 · grade {grade(pct)}</p>
<table><tr><th>Area</th><th>Check</th><th>Points</th><th>Detail</th></tr>
{rows}
</table>
<footer>Checked with <a href="https://github.com/binbin7418-dotcom/newkwlab-ai-site-check">newkwlab-ai-site-check</a>
by <a href="https://api.newkwlab.com">NewKwLab</a>. Need this for a whole portfolio, on a schedule, with
change alerts? The NewKwLab API runs it in bulk: <a href="https://api.newkwlab.com/bundle">api.newkwlab.com/bundle</a></footer>
</body></html>
"""
    return md_text, html_text, pct


def main() -> int:
    ap = argparse.ArgumentParser(description="Check whether AI systems can see your website.")
    ap.add_argument("url", help="Website URL, e.g. https://example.com")
    ap.add_argument("--out", default=".", help="Directory for report.md / report.html (default: current)")
    ap.add_argument("--generate-llms", metavar="FILE", help="Also generate a starter llms.txt to FILE")
    ap.add_argument("--fail-under", type=int, default=None, help="Exit 1 if the score is below N (for CI)")
    ap.add_argument("--json", metavar="FILE", help="Also write the raw results as JSON")
    args = ap.parse_args()

    url = args.url if re.match(r"^https?://", args.url) else "https://" + args.url
    print(f"Checking {url} …")
    checks, facts = run_checks(url)
    md_text, html_text, pct = render_reports(url, checks, facts)

    import os
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "report.md"), "w") as f:
        f.write(md_text)
    with open(os.path.join(args.out, "report.html"), "w") as f:
        f.write(html_text)
    if args.json:
        with open(args.json, "w") as f:
            json.dump({"url": url, "score": pct, "facts": facts,
                       "checks": [vars(c) for c in checks]}, f, indent=2)
    if args.generate_llms:
        with open(args.generate_llms, "w") as f:
            f.write(generate_llms(url))
        print(f"Starter llms.txt written to {args.generate_llms}")

    icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
    for c in checks:
        print(f"{icon[c.status]} [{c.group}] {c.name} ({c.points:g}/{c.max_points:g}) — {c.detail}")
    print(f"\nScore: {pct}/100 (grade {grade(pct)}) · reports in {args.out}/report.md and report.html")

    if args.fail_under is not None and pct < args.fail_under:
        print(f"FAIL: score {pct} is below --fail-under {args.fail_under}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
