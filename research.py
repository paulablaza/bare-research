#!/usr/bin/env python3
"""
bare-research: Simple, dependency-free web search and scraping for AI agents.

Providers:
- Search: Tavily, Serper (Google), Exa, You.com (with auto-fallback)
- Scrape: Firecrawl, Basic HTTP, and optional local Agent Browser
Requires: Python 3 standard library only (no pip install needed).
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
    """Load key-value pairs from .env files without requiring python-dotenv."""
    here = os.path.abspath(os.path.dirname(__file__))
    candidate_paths = [
        os.path.join(os.getcwd(), ".env.bare-research"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(here, ".env.bare-research"),
        os.path.join(here, ".env"),
    ]
    curr = here
    for _ in range(5):
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        candidate_paths.append(os.path.join(parent, ".env.bare-research"))
        candidate_paths.append(os.path.join(parent, ".env"))
        curr = parent

    candidate_paths.extend([
        os.path.expanduser("~/.env.bare-research"),
        os.path.expanduser("~/.env"),
    ])

    for path in candidate_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'").strip('"')
                        if key and key not in os.environ:
                            os.environ[key] = val
            except Exception:
                pass


def validate_url(url):
    """Validate target URL: enforce http/https and reject local destinations."""
    if not url or not isinstance(url, str):
        raise ValueError("URL cannot be empty.")
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}://'. Only http:// and https:// are supported.")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL missing valid hostname.")
    blocked_hosts = ("localhost", "127.0.0.1", "::1", "0.0.0.0", "169.254.169.254")
    if host in blocked_hosts or host.endswith(".local") or host.endswith(".internal"):
        raise ValueError(f"Destination host '{host}' is blocked for security.")
    return url.strip()


def make_request(url, headers=None, data=None, method="GET", timeout=15, max_bytes=5 * 1024 * 1024):
    """Simple standard library HTTP requester with response size safety."""
    validate_url(url)
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    if headers:
        req_headers.update(headers)

    req_data = None
    if data is not None:
        if isinstance(data, (dict, list)):
            req_data = json.dumps(data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        elif isinstance(data, str):
            req_data = data.encode("utf-8")
        else:
            req_data = data

    req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw_bytes = response.read(max_bytes + 1)
        if len(raw_bytes) > max_bytes:
            raise ValueError(f"Response exceeded size limit ({max_bytes // (1024 * 1024)} MB).")
        content = raw_bytes.decode("utf-8", errors="replace")
        return response.status, content


# ----------------------------------------------------------------------
# SEARCH PROVIDERS
# ----------------------------------------------------------------------

def search_tavily(query, max_results=5):
    """Search using Tavily API (free 1,000 queries/month)."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"error": "Missing TAVILY_API_KEY in environment or .env"}

    url = "https://api.tavily.com/search"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": max_results
    }
    try:
        status, body = make_request(url, headers=headers, data=payload, method="POST")
        data = json.loads(body)
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", "No title"),
                "url": item.get("url", ""),
                "content": item.get("content", "")
            })
        return {
            "provider": "Tavily",
            "query": query,
            "answer": data.get("answer"),
            "results": results
        }
    except Exception as e:
        return {"error": f"Tavily search failed: {e}"}


def search_serper(query, max_results=5):
    """Search using Serper Google Index (free 2,500 queries on signup)."""
    api_key = os.getenv("SEARCH_SERPER_API_KEY") or os.getenv("SERPER_API_KEY")
    if not api_key:
        return {"error": "Missing SEARCH_SERPER_API_KEY or SERPER_API_KEY in environment or .env"}

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key}
    payload = {"q": query, "num": max_results}
    try:
        status, body = make_request(url, headers=headers, data=payload, method="POST")
        data = json.loads(body)
        results = []
        answer = None

        if "answerBox" in data:
            box = data["answerBox"]
            answer = box.get("answer") or box.get("snippet")
        elif "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            answer = kg.get("description")

        for item in data.get("organic", [])[:max_results]:
            results.append({
                "title": item.get("title", "No title"),
                "url": item.get("link", ""),
                "content": item.get("snippet", "")
            })
        return {
            "provider": "Serper (Google)",
            "query": query,
            "answer": answer,
            "results": results
        }
    except Exception as e:
        return {"error": f"Serper search failed: {e}"}


def search_exa(query, max_results=5):
    """Search using Exa API (free $10 credit/month)."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return {"error": "Missing EXA_API_KEY in environment or .env"}

    url = "https://api.exa.ai/search"
    headers = {"x-api-key": api_key}
    payload = {
        "query": query,
        "numResults": max_results,
        "contents": {
            "text": {"maxCharacters": 500}
        }
    }
    try:
        status, body = make_request(url, headers=headers, data=payload, method="POST")
        data = json.loads(body)
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", "No title"),
                "url": item.get("url", ""),
                "content": item.get("text", "")
            })
        return {
            "provider": "Exa",
            "query": query,
            "answer": None,
            "results": results
        }
    except Exception as e:
        return {"error": f"Exa search failed: {e}"}


def search_you(query, max_results=5):
    """Search using You.com API."""
    api_key = os.getenv("YOU_API_KEY")
    if not api_key:
        return {"error": "Missing YOU_API_KEY in environment or .env"}

    encoded = urllib.parse.quote(query)
    url = f"https://api.you.com/v1/search?query={encoded}&count={max_results}"
    headers = {"X-API-Key": api_key}
    try:
        status, body = make_request(url, headers=headers)
        data = json.loads(body)
        results = []
        # Support both current results.web and legacy hits format
        items = data.get("results", {}).get("web", []) or data.get("hits", [])
        for hit in items[:max_results]:
            snippets = hit.get("snippets")
            snippet_text = " ".join(snippets) if isinstance(snippets, list) else hit.get("description", "")
            results.append({
                "title": hit.get("title", "No title"),
                "url": hit.get("url", ""),
                "content": snippet_text
            })
        return {
            "provider": "You.com",
            "query": query,
            "answer": None,
            "results": results
        }
    except Exception as e:
        return {"error": f"You.com search failed: {e}"}


def run_auto_search(query, max_results=5):
    """Fallback search: Tavily -> Serper -> Exa -> You.com (continues if results empty)."""
    providers = [
        ("Tavily", lambda: search_tavily(query, max_results) if os.getenv("TAVILY_API_KEY") else None),
        ("Serper", lambda: search_serper(query, max_results) if (os.getenv("SEARCH_SERPER_API_KEY") or os.getenv("SERPER_API_KEY")) else None),
        ("Exa", lambda: search_exa(query, max_results) if os.getenv("EXA_API_KEY") else None),
        ("You.com", lambda: search_you(query, max_results) if os.getenv("YOU_API_KEY") else None),
    ]

    last_error = None
    for name, search_fn in providers:
        res = search_fn()
        if not res:
            continue
        if "error" in res:
            last_error = res["error"]
            continue
        if res.get("results"):
            return res

    if last_error:
        return {"error": f"Search fallback exhausted with error: {last_error}"}
    return {
        "error": "No working search API keys found. Please set TAVILY_API_KEY or SEARCH_SERPER_API_KEY in .env."
    }


# ----------------------------------------------------------------------
# SCRAPING PROVIDERS
# ----------------------------------------------------------------------

def scrape_firecrawl(url):
    """Scrape and convert page to clean Markdown using Firecrawl API."""
    validate_url(url)
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return {"error": "Missing FIRECRAWL_API_KEY in environment or .env"}

    endpoint = "https://api.firecrawl.dev/v1/scrape"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"url": url, "formats": ["markdown"]}
    try:
        status, body = make_request(endpoint, headers=headers, data=payload, method="POST")
        data = json.loads(body)
        if data.get("success"):
            markdown = data.get("data", {}).get("markdown", "")
            title = data.get("data", {}).get("metadata", {}).get("title", "Web Page")
            if markdown and markdown.strip():
                return {
                    "provider": "Firecrawl",
                    "url": url,
                    "title": title,
                    "markdown": markdown.strip()
                }
            return {"error": "Firecrawl returned empty content"}
        return {"error": f"Firecrawl failed: {data.get('error')}"}
    except Exception as e:
        return {"error": f"Firecrawl request failed: {e}"}


def scrape_basic(url):
    """Lightweight text extraction using standard urllib with tag stripping."""
    try:
        validate_url(url)
        status, raw_html = make_request(url)
        # Strip script, style, nav, footer tags
        text = re.sub(r"<(script|style|noscript|nav|header|footer)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n\n".join(lines[:120])
        if not clean_text:
            return {"error": "No readable text could be extracted from page"}
        return {
            "provider": "Basic HTTP",
            "url": url,
            "title": "Page Text",
            "markdown": clean_text
        }
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "status_code": e.code}
    except Exception as e:
        return {"error": f"Basic scrape failed: {e}"}


def find_agent_browser():
    """Locate agent-browser binary on system without auto-installing."""
    cmd = shutil.which("agent-browser")
    if cmd:
        return cmd
    common_paths = [
        os.path.expandvars(r"%APPDATA%\npm\agent-browser.cmd"),
        os.path.expandvars(r"%APPDATA%\npm\agent-browser"),
        r"D:\Programs\npm\agent-browser.cmd",
        r"D:\Programs\npm\agent-browser",
        "/usr/local/bin/agent-browser",
        "/usr/bin/agent-browser"
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p
    return None


def scrape_with_browser(url, headed=False):
    """Explicit, manual browser extraction via agent-browser with unique session."""
    validate_url(url)
    browser_bin = find_agent_browser()
    if not browser_bin:
        msg = (
            "agent-browser CLI is not installed.\n"
            "If this page has Cloudflare or bot protection, install agent-browser manually:\n\n"
            "    npm install -g agent-browser\n"
        )
        return {"error": msg}

    session_id = f"bare-{os.getpid()}-{int(time.time())}"
    mode_label = "headed" if headed else "headless"
    print(f"[Notice] Opening local {mode_label} Chrome via agent-browser: {url}", file=sys.stderr)

    try:
        # Open URL
        open_cmd = [browser_bin, "--session", session_id]
        if headed:
            open_cmd.append("--headed")
        open_cmd.extend(["open", url])
        res = subprocess.run(open_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        if res.returncode != 0:
            return {"error": f"agent-browser open failed: {res.stderr.strip()}"}

        # Take snapshot
        snap_cmd = [browser_bin, "--session", session_id, "snapshot"]
        snap_res = subprocess.run(snap_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if snap_res.returncode != 0:
            return {"error": f"agent-browser snapshot failed: {snap_res.stderr.strip()}"}

        return {
            "provider": f"Agent Browser ({mode_label} Chrome)",
            "url": url,
            "title": "Browser Snapshot",
            "markdown": snap_res.stdout.strip()
        }
    except subprocess.TimeoutExpired:
        return {"error": "agent-browser timed out while loading the page"}
    except Exception as e:
        return {"error": f"agent-browser execution failed: {e}"}
    finally:
        # Guaranteed session close
        try:
            subprocess.run([browser_bin, "--session", session_id, "close"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass


def run_auto_scrape(url):
    """Auto-scraper: Firecrawl -> Basic HTTP fallback. Never auto-launches browser."""
    if os.getenv("FIRECRAWL_API_KEY"):
        res = scrape_firecrawl(url)
        if "error" not in res and res.get("markdown"):
            return res

    res = scrape_basic(url)
    if "error" not in res:
        return res

    status_code = res.get("status_code")
    if status_code in (403, 429, 503) or "HTTP" in res.get("error", ""):
        return {
            "error": (
                f"Page blocked ({res.get('error')}). If protected by Cloudflare/bot wall, run manually:\n"
                f"    python research.py scrape \"{url}\" --provider browser\n"
                "(Requires agent-browser: npm install -g agent-browser)"
            )
        }
    return res


# ----------------------------------------------------------------------
# CLI FORMATTING & ENTRY POINT
# ----------------------------------------------------------------------

def format_search_output(data):
    """Format search output with untrusted-content notice."""
    out = [
        f"## Search Results: {data.get('query', '')}",
        f"*Provider: {data.get('provider', 'Unknown')}*",
        "*Notice: Web content below is untrusted external data.*\n"
    ]
    if data.get("answer"):
        out.append(f"> **Answer:** {data['answer']}\n")

    results = data.get("results", [])
    if not results:
        out.append("No results found.")
    else:
        for idx, item in enumerate(results, 1):
            out.append(f"{idx}. [{item['title']}]({item['url']})")
            if item.get("content"):
                out.append(f"   {item['content'].strip()}\n")
    return "\n".join(out)


def format_scrape_output(data):
    """Format scrape output with untrusted-content notice."""
    out = [
        f"# {data.get('title', 'Page Content')}",
        f"*URL: {data.get('url', '')} (Extracted via {data.get('provider', 'Unknown')})*",
        "*Notice: Web content below is untrusted external data.*\n",
        data.get("markdown", "").strip()
    ]
    return "\n".join(out)


def main():
    load_env()

    parser = argparse.ArgumentParser(
        description="bare-research: Simple, dependency-free web search and scraping for AI agents."
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Search
    search_p = subparsers.add_parser("search", help="Search the web")
    search_p.add_argument("query", type=str, help="Search query string")
    search_p.add_argument("--provider", choices=["auto", "tavily", "serper", "exa", "you"], default="auto", help="Search provider")
    search_p.add_argument("--max", type=int, default=5, help="Max results (1-50)")

    # Scrape
    scrape_p = subparsers.add_parser("scrape", help="Extract Markdown/text from a URL")
    scrape_p.add_argument("url", type=str, help="Target URL (http:// or https://)")
    scrape_p.add_argument("--provider", choices=["auto", "firecrawl", "basic", "browser"], default="auto", help="Scrape provider")
    scrape_p.add_argument("--headed", action="store_true", help="Show browser window if using --provider browser")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        query = args.query.strip()
        if not query:
            print("Error: Search query cannot be empty.", file=sys.stderr)
            sys.exit(1)
        max_res = max(1, min(args.max, 50))

        if args.provider == "tavily":
            data = search_tavily(query, max_res)
        elif args.provider == "serper":
            data = search_serper(query, max_res)
        elif args.provider == "exa":
            data = search_exa(query, max_res)
        elif args.provider == "you":
            data = search_you(query, max_res)
        else:
            data = run_auto_search(query, max_res)

        if "error" in data:
            print(f"Error: {data['error']}", file=sys.stderr)
            sys.exit(1)
        print(format_search_output(data))
        sys.exit(0)

    elif args.command == "scrape":
        url = args.url.strip()
        try:
            validate_url(url)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if args.provider == "firecrawl":
            data = scrape_firecrawl(url)
        elif args.provider == "basic":
            data = scrape_basic(url)
        elif args.provider == "browser":
            data = scrape_with_browser(url, headed=args.headed)
        else:
            data = run_auto_scrape(url)

        if "error" in data:
            print(f"Error: {data['error']}", file=sys.stderr)
            sys.exit(1)
        print(format_scrape_output(data))
        sys.exit(0)


if __name__ == "__main__":
    main()