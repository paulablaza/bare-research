#!/usr/bin/env python3
"""
bare-research: Simple, dependency-free web search and scraping for AI agents.

Supported Search: Tavily, Serper (Google), Exa, You.com
Supported Scrape: Firecrawl, Basic HTTP, Agent Browser
Requirements: Python 3 standard library only.
"""

import os
import sys
import json
import argparse
import shutil
import subprocess
import re
import html
import time
import urllib.request
import urllib.parse
import urllib.error

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_env():
    """Load API keys from .env files without extra packages."""
    dirs = [os.getcwd(), os.path.dirname(os.path.abspath(__file__)), os.path.expanduser("~")]
    for d in dirs:
        for fname in [".env", ".env.bare-research"]:
            p = os.path.join(d, fname)
            if os.path.isfile(p):
                try:
                    with open(p, encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                k, v = line.strip().split("=", 1)
                                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
                except Exception:
                    pass


def check_url(url):
    """Basic URL check: enforce http/https and block local network lookups."""
    if not url.startswith(("http://", "https://")):
        sys.exit(f"Error: Invalid URL '{url}'. Must start with http:// or https://")
    host = urllib.parse.urlparse(url).hostname or ""
    if host.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        sys.exit(f"Error: Blocked request to local host '{host}'.")


def request_json(url, headers=None, data=None, method=None):
    """Send an HTTP request and parse the JSON response."""
    check_url(url)
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else data.encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
        method = method or "POST"

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


# ----------------------------------------------------------------------
# SEARCH
# ----------------------------------------------------------------------

def search_tavily(query, max_results=5):
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return None
    try:
        data = request_json("https://api.tavily.com/search",
                            headers={"Authorization": f"Bearer {key}"},
                            data={"query": query, "max_results": max_results, "include_answer": True})
        results = [{"title": r.get("title", ""), "url": r.get("url", ""), "desc": r.get("content", "")}
                   for r in data.get("results", [])]
        return {"provider": "Tavily", "answer": data.get("answer"), "results": results}
    except Exception as e:
        return {"error": f"Tavily error: {e}"}


def search_serper(query, max_results=5):
    key = os.getenv("SEARCH_SERPER_API_KEY") or os.getenv("SERPER_API_KEY")
    if not key:
        return None
    try:
        data = request_json("https://google.serper.dev/search",
                            headers={"X-API-KEY": key},
                            data={"q": query, "num": max_results})
        ans = data.get("answerBox", {}).get("answer") or data.get("answerBox", {}).get("snippet") or data.get("knowledgeGraph", {}).get("description")
        results = [{"title": r.get("title", ""), "url": r.get("link", ""), "desc": r.get("snippet", "")}
                   for r in data.get("organic", [])[:max_results]]
        return {"provider": "Serper (Google)", "answer": ans, "results": results}
    except Exception as e:
        return {"error": f"Serper error: {e}"}


def search_exa(query, max_results=5):
    key = os.getenv("EXA_API_KEY")
    if not key:
        return None
    try:
        data = request_json("https://api.exa.ai/search",
                            headers={"x-api-key": key},
                            data={"query": query, "numResults": max_results, "contents": {"text": {"maxCharacters": 500}}})
        results = [{"title": r.get("title", ""), "url": r.get("url", ""), "desc": r.get("text", "")}
                   for r in data.get("results", [])]
        return {"provider": "Exa", "answer": None, "results": results}
    except Exception as e:
        return {"error": f"Exa error: {e}"}


def search_you(query, max_results=5):
    key = os.getenv("YOU_API_KEY")
    if not key:
        return None
    try:
        q = urllib.parse.quote(query)
        data = request_json(f"https://api.you.com/v1/search?query={q}&count={max_results}",
                            headers={"X-API-Key": key})
        hits = data.get("results", {}).get("web", []) or data.get("hits", [])
        results = []
        for h in hits[:max_results]:
            snips = h.get("snippets")
            desc = " ".join(snips) if isinstance(snips, list) else h.get("description", "")
            results.append({"title": h.get("title", ""), "url": h.get("url", ""), "desc": desc})
        return {"provider": "You.com", "answer": None, "results": results}
    except Exception as e:
        return {"error": f"You.com error: {e}"}


def run_search(query, provider="auto", max_results=5):
    if provider != "auto":
        lookup = {"tavily": search_tavily, "serper": search_serper, "exa": search_exa, "you": search_you}
        res = lookup[provider](query, max_results)
        if not res:
            sys.exit(f"Error: Missing API key for {provider}. Set it in your .env file.")
        if "error" in res:
            sys.exit(res["error"])
        return res

    # Auto fallback chain: Tavily -> Serper -> Exa -> You.com
    chain = [search_tavily, search_serper, search_exa, search_you]
    for fn in chain:
        res = fn(query, max_results)
        if res and "error" not in res and res.get("results"):
            return res

    sys.exit("Error: No working search API key found. Add TAVILY_API_KEY or SEARCH_SERPER_API_KEY to your .env file.")


# ----------------------------------------------------------------------
# SCRAPE
# ----------------------------------------------------------------------

def scrape_firecrawl(url):
    key = os.getenv("FIRECRAWL_API_KEY")
    if not key:
        return None
    try:
        data = request_json("https://api.firecrawl.dev/v1/scrape",
                            headers={"Authorization": f"Bearer {key}"},
                            data={"url": url, "formats": ["markdown"]})
        md = data.get("data", {}).get("markdown", "").strip()
        return md if md else None
    except Exception:
        return None


def scrape_basic(url):
    try:
        check_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
        text = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        lines = [l.strip() for l in html.unescape(text).splitlines() if l.strip()]
        return "\n\n".join(lines[:120])
    except Exception as e:
        sys.exit(f"Error scraping {url}: {e}")


def scrape_browser(url):
    check_url(url)
    cmd = shutil.which("agent-browser")
    if not cmd:
        sys.exit("Error: agent-browser CLI is not installed.\nTo inspect Cloudflare pages with Chrome, run: npm install -g agent-browser")

    sid = f"bare-{int(time.time())}"
    print(f"[Notice] Opening {url} with local Chrome...", file=sys.stderr)
    try:
        subprocess.run([cmd, "--session", sid, "open", url], check=True, timeout=20)
        res = subprocess.run([cmd, "--session", sid, "snapshot"], capture_output=True, text=True, timeout=15)
        return res.stdout.strip()
    except Exception as e:
        sys.exit(f"Error launching browser: {e}")
    finally:
        subprocess.run([cmd, "--session", sid, "close"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_scrape(url, provider="auto"):
    check_url(url)
    if provider == "browser":
        return scrape_browser(url)
    if provider == "firecrawl":
        res = scrape_firecrawl(url)
        if not res:
            sys.exit("Error: Firecrawl failed or FIRECRAWL_API_KEY not set.")
        return res
    if provider == "basic":
        return scrape_basic(url)

    # Auto fallback: Firecrawl -> basic HTTP
    res = scrape_firecrawl(url) if os.getenv("FIRECRAWL_API_KEY") else None
    if res:
        return res
    return scrape_basic(url)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    load_env()

    parser = argparse.ArgumentParser(description="bare-research: Simple, dependency-free web search and scraping for AI agents.")
    subparsers = parser.add_subparsers(dest="command")

    # search
    p_search = subparsers.add_parser("search", help="Search the web")
    p_search.add_argument("query", help="Search query string")
    p_search.add_argument("--provider", choices=["auto", "tavily", "serper", "exa", "you"], default="auto")
    p_search.add_argument("--max", type=int, default=5, help="Number of results (1-50)")

    # scrape
    p_scrape = subparsers.add_parser("scrape", help="Extract text from a URL")
    p_scrape.add_argument("url", help="URL to scrape")
    p_scrape.add_argument("--provider", choices=["auto", "firecrawl", "basic", "browser"], default="auto")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        q = args.query.strip()
        if not q:
            sys.exit("Error: Search query cannot be empty.")
        data = run_search(q, provider=args.provider, max_results=max(1, min(args.max, 50)))

        print(f"## Search Results: {q}\n*Source: {data['provider']}*\n")
        if data.get("answer"):
            print(f"> **Answer:** {data['answer']}\n")
        for i, r in enumerate(data.get("results", []), 1):
            print(f"{i}. [{r['title']}]({r['url']})")
            if r.get("desc"):
                print(f"   {r['desc'].strip()}\n")

    elif args.command == "scrape":
        url = args.url.strip()
        content = run_scrape(url, provider=args.provider)
        print(f"# Content: {url}\n")
        print(content)


if __name__ == "__main__":
    main()