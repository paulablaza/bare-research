#!/usr/bin/env python3
"""
bare-research: Simple, dependency-free web search and scraping for AI agents.
Standard library only. No pip packages needed.
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_env():
    """Load API keys from .env files."""
    for directory in [os.getcwd(), os.path.dirname(os.path.abspath(__file__)), os.path.expanduser("~")]:
        for fname in [".env", ".env.bare-research"]:
            filepath = os.path.join(directory, fname)
            if os.path.isfile(filepath):
                try:
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                key, val = line.strip().split("=", 1)
                                os.environ.setdefault(key.strip(), val.strip().strip("\"'"))
                except Exception:
                    pass


def check_url(url):
    """Basic safety: require http/https and block local network lookups."""
    if not url.startswith(("http://", "https://")):
        sys.exit(f"Error: Invalid URL '{url}'. Must start with http:// or https://")
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        sys.exit(f"Error: Blocked request to local host '{host}'.")


def http_json(url, headers=None, data=None):
    """Send an HTTP request and return JSON response."""
    check_url(url)
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=req_headers)
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))


# ----------------------------------------------------------------------
# SEARCH PROVIDERS (Can be called separately or via auto-fallback)
# ----------------------------------------------------------------------

def search_tavily(query, count=5):
    """Search Tavily (direct answers + sources)."""
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return None
    try:
        data = http_json("https://api.tavily.com/search",
                         headers={"Authorization": f"Bearer {key}"},
                         data={"query": query, "max_results": count, "include_answer": True})
        results = [{"title": r.get("title", ""), "url": r.get("url", ""), "desc": r.get("content", "")}
                   for r in data.get("results", [])]
        return {"provider": "Tavily", "answer": data.get("answer"), "results": results}
    except Exception:
        return None


def search_serper(query, count=5):
    """Search Google via Serper API."""
    key = os.getenv("SEARCH_SERPER_API_KEY") or os.getenv("SERPER_API_KEY")
    if not key:
        return None
    try:
        data = http_json("https://google.serper.dev/search",
                         headers={"X-API-KEY": key},
                         data={"q": query, "num": count})
        ans = data.get("answerBox", {}).get("snippet") or data.get("knowledgeGraph", {}).get("description")
        results = [{"title": r.get("title", ""), "url": r.get("link", ""), "desc": r.get("snippet", "")}
                   for r in data.get("organic", [])[:count]]
        return {"provider": "Serper (Google)", "answer": ans, "results": results}
    except Exception:
        return None


def search_exa(query, count=5):
    """Search Exa (technical / neural search)."""
    key = os.getenv("EXA_API_KEY")
    if not key:
        return None
    try:
        data = http_json("https://api.exa.ai/search",
                         headers={"x-api-key": key},
                         data={"query": query, "numResults": count, "contents": {"text": {"maxCharacters": 400}}})
        results = [{"title": r.get("title", ""), "url": r.get("url", ""), "desc": r.get("text", "")}
                   for r in data.get("results", [])]
        return {"provider": "Exa", "answer": None, "results": results}
    except Exception:
        return None


def search_you(query, count=5):
    """Search You.com web index."""
    key = os.getenv("YOU_API_KEY")
    if not key:
        return None
    try:
        q = urllib.parse.quote(query)
        data = http_json(f"https://api.you.com/v1/search?query={q}&count={count}",
                         headers={"X-API-Key": key})
        items = data.get("results", {}).get("web", []) or data.get("hits", [])
        results = []
        for i in items[:count]:
            desc = " ".join(i.get("snippets")) if isinstance(i.get("snippets"), list) else i.get("description", "")
            results.append({"title": i.get("title", ""), "url": i.get("url", ""), "desc": desc})
        return {"provider": "You.com", "answer": None, "results": results}
    except Exception:
        return None


def print_search(data, query):
    """Print clean search output."""
    print(f"## Search Results: {query}")
    print(f"*Source: {data['provider']}*\n")
    if data.get("answer"):
        print(f"> **Answer:** {data['answer']}\n")
    for i, r in enumerate(data.get("results", []), 1):
        print(f"{i}. [{r['title']}]({r['url']})")
        if r.get("desc"):
            print(f"   {r['desc'].strip()}\n")


def run_search(query, provider="auto", count=5):
    """Run search: specific provider or auto-fallback."""
    providers = {
        "tavily": search_tavily,
        "serper": search_serper,
        "exa": search_exa,
        "you": search_you,
    }

    # If specific provider requested
    if provider in providers:
        res = providers[provider](query, count)
        if not res:
            sys.exit(f"Error: Missing API key for {provider} in .env, or provider failed.")
        print_search(res, query)
        return

    # Auto fallback: try each in order
    for name, fn in providers.items():
        res = fn(query, count)
        if res and res.get("results"):
            print_search(res, query)
            return

    sys.exit("Error: No working search key found. Set TAVILY_API_KEY or SEARCH_SERPER_API_KEY in .env.")


# ----------------------------------------------------------------------
# SCRAPE PROVIDERS
# ----------------------------------------------------------------------

def scrape_firecrawl(url):
    """Scrape using Firecrawl (clean Markdown)."""
    key = os.getenv("FIRECRAWL_API_KEY")
    if not key:
        return None
    try:
        data = http_json("https://api.firecrawl.dev/v1/scrape",
                         headers={"Authorization": f"Bearer {key}"},
                         data={"url": url, "formats": ["markdown"]})
        return data.get("data", {}).get("markdown", "").strip() or None
    except Exception:
        return None


def scrape_basic(url):
    """Fallback text scraper using standard urllib."""
    check_url(url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=15) as res:
            raw = res.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
        text = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return "\n\n".join(lines[:120])
    except Exception as e:
        sys.exit(f"Error scraping '{url}': {e}")


def run_scrape(url, provider="auto"):
    """Run scrape: Firecrawl, basic text, or auto-fallback."""
    check_url(url)

    if provider == "firecrawl":
        md = scrape_firecrawl(url)
        if not md:
            sys.exit("Error: Firecrawl scrape failed or FIRECRAWL_API_KEY is not set.")
        print(f"# Content: {url}\n*Source: Firecrawl*\n\n{md}")
        return

    if provider == "basic":
        print(f"# Content: {url}\n*Source: Basic HTTP*\n\n{scrape_basic(url)}")
        return

    # Auto fallback: try Firecrawl first, then basic
    if os.getenv("FIRECRAWL_API_KEY"):
        md = scrape_firecrawl(url)
        if md:
            print(f"# Content: {url}\n*Source: Firecrawl*\n\n{md}")
            return

    print(f"# Content: {url}\n*Source: Basic HTTP*\n\n{scrape_basic(url)}")


# ----------------------------------------------------------------------
# CLI ENTRY POINT
# ----------------------------------------------------------------------

def main():
    load_env()

    parser = argparse.ArgumentParser(description="bare-research: Simple search and scrape script for AI agents.")
    subparsers = parser.add_subparsers(dest="command")

    # search
    p_search = subparsers.add_parser("search", help="Search the web")
    p_search.add_argument("query", help="Query string")
    p_search.add_argument("--provider", choices=["auto", "tavily", "serper", "exa", "you"], default="auto", help="Search provider")
    p_search.add_argument("--max", type=int, default=5, help="Number of results")

    # scrape
    p_scrape = subparsers.add_parser("scrape", help="Extract text from a webpage")
    p_scrape.add_argument("url", help="Webpage URL to scrape")
    p_scrape.add_argument("--provider", choices=["auto", "firecrawl", "basic"], default="auto", help="Scrape provider")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        query = args.query.strip()
        if not query:
            sys.exit("Error: Search query cannot be empty.")
        run_search(query, provider=args.provider, count=max(1, min(args.max, 50)))

    elif args.command == "scrape":
        run_scrape(args.url.strip(), provider=args.provider)


if __name__ == "__main__":
    main()