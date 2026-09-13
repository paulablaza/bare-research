#!/usr/bin/env python3
"""
bare-research: Simple, dependency-free web search and scraping for AI agents.

This script lets AI coding agents search the web and scrape pages using
free API tiers from Tavily, Serper, Exa, You.com, and Firecrawl.

Built with pure Python standard library (no pip packages needed).
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Ensure UTF-8 output on Windows consoles so special characters don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ======================================================================
# 1. SETUP & HELPERS
# ======================================================================

def load_env():
    """
    Look for .env or .env.bare-research in the current directory,
    the script directory, or the user's home directory.
    """
    search_directories = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.expanduser("~")
    ]

    for directory in search_directories:
        for filename in [".env", ".env.bare-research"]:
            filepath = os.path.join(directory, filename)
            if not os.path.isfile(filepath):
                continue

            try:
                with open(filepath, encoding="utf-8", errors="ignore") as file:
                    for line in file:
                        line = line.strip()
                        # Ignore comments and blank lines
                        if not line or line.startswith("#") or "=" not in line:
                            continue

                        key, value = line.split("=", 1)
                        clean_key = key.strip()
                        clean_value = value.strip().strip("\"'")

                        # Only set if not already in the environment
                        if clean_key and clean_key not in os.environ:
                            os.environ[clean_key] = clean_value
            except Exception:
                pass


def validate_url(url):
    """
    Basic sanity check:
    - Must be http:// or https://
    - Blocks local network addresses (localhost, 127.0.0.1)
    """
    if not url or not isinstance(url, str):
        sys.exit("Error: Please provide a valid URL.")

    if not url.startswith(("http://", "https://")):
        sys.exit(f"Error: Invalid URL '{url}'. URLs must start with http:// or https://")

    parsed = urllib.parse.urlparse(url)
    hostname = (parsed.hostname or "").lower()

    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        sys.exit(f"Error: Blocked request to local address '{hostname}'.")

    return url


def send_request(url, headers=None, payload=None, method=None):
    """
    Send an HTTP request using urllib and return the parsed JSON response.
    """
    validate_url(url)

    request_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if headers:
        request_headers.update(headers)

    request_data = None
    if payload is not None:
        request_data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
        method = method or "POST"

    req = urllib.request.Request(
        url,
        data=request_data,
        headers=request_headers,
        method=method
    )

    with urllib.request.urlopen(req, timeout=15) as response:
        response_body = response.read().decode("utf-8", errors="replace")
        return json.loads(response_body)


# ======================================================================
# 2. SEARCH PROVIDERS
# ======================================================================

def search_tavily(query, count=5):
    """
    Search using Tavily API (free 1,000 searches/month at tavily.com).
    Great for direct answers and quick summaries.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "query": query,
        "max_results": count,
        "include_answer": True
    }

    try:
        data = send_request("https://api.tavily.com/search", headers=headers, payload=payload)

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", "No Title"),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")
            })

        return {
            "provider": "Tavily",
            "answer": data.get("answer"),
            "results": results
        }
    except Exception as e:
        return {"error": f"Tavily search failed: {e}"}


def search_serper(query, count=5):
    """
    Search Google index using Serper API (free 2,500 searches on signup at serper.dev).
    Great for raw Google search, official documentation, and Reddit threads.
    """
    api_key = os.getenv("SEARCH_SERPER_API_KEY") or os.getenv("SERPER_API_KEY")
    if not api_key:
        return None

    headers = {
        "X-API-KEY": api_key
    }
    payload = {
        "q": query,
        "num": count
    }

    try:
        data = send_request("https://google.serper.dev/search", headers=headers, payload=payload)

        # Check for answer box or knowledge graph
        answer = None
        if "answerBox" in data:
            answer = data["answerBox"].get("answer") or data["answerBox"].get("snippet")
        elif "knowledgeGraph" in data:
            answer = data["knowledgeGraph"].get("description")

        results = []
        for item in data.get("organic", [])[:count]:
            results.append({
                "title": item.get("title", "No Title"),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })

        return {
            "provider": "Serper (Google)",
            "answer": answer,
            "results": results
        }
    except Exception as e:
        return {"error": f"Serper search failed: {e}"}


def search_exa(query, count=5):
    """
    Search using Exa API (free starter credits at exa.ai).
    Great for finding technical blogs, repositories, and engineering papers.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return None

    headers = {
        "x-api-key": api_key
    }
    payload = {
        "query": query,
        "numResults": count,
        "contents": {
            "text": {"maxCharacters": 500}
        }
    }

    try:
        data = send_request("https://api.exa.ai/search", headers=headers, payload=payload)

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", "No Title"),
                "url": item.get("url", ""),
                "snippet": item.get("text", "")
            })

        return {
            "provider": "Exa",
            "answer": None,
            "results": results
        }
    except Exception as e:
        return {"error": f"Exa search failed: {e}"}


def search_you(query, count=5):
    """
    Search using You.com API (free trial credits at you.com).
    Backup general web search index.
    """
    api_key = os.getenv("YOU_API_KEY")
    if not api_key:
        return None

    headers = {
        "X-API-Key": api_key
    }
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.you.com/v1/search?query={encoded_query}&count={count}"

    try:
        data = send_request(url, headers=headers, method="GET")

        # Support both results.web and legacy hits format
        items = data.get("results", {}).get("web", []) or data.get("hits", [])
        results = []
        for item in items[:count]:
            snippets = item.get("snippets")
            snippet_text = " ".join(snippets) if isinstance(snippets, list) else item.get("description", "")

            results.append({
                "title": item.get("title", "No Title"),
                "url": item.get("url", ""),
                "snippet": snippet_text
            })

        return {
            "provider": "You.com",
            "answer": None,
            "results": results
        }
    except Exception as e:
        return {"error": f"You.com search failed: {e}"}


def run_search(query, provider="auto", count=5):
    """
    Execute search.
    If provider is 'auto', it tries Tavily -> Serper -> Exa -> You.com
    and uses whichever has a working key and returns results.
    """
    # If user asked for a specific provider
    if provider != "auto":
        provider_map = {
            "tavily": search_tavily,
            "serper": search_serper,
            "exa": search_exa,
            "you": search_you
        }
        search_function = provider_map.get(provider)
        response = search_function(query, count)

        if response is None:
            sys.exit(f"Error: Missing API key for {provider}. Please add it to your .env file.")
        if "error" in response:
            sys.exit(response["error"])

        return response

    # Auto fallback chain: Tavily -> Serper -> Exa -> You.com
    search_chain = [search_tavily, search_serper, search_exa, search_you]

    for search_function in search_chain:
        response = search_function(query, count)
        # Check that we got a valid response with at least 1 result
        if response and "error" not in response and response.get("results"):
            return response

    sys.exit(
        "Error: No working search API key found.\n"
        "Please add TAVILY_API_KEY or SEARCH_SERPER_API_KEY to your .env file."
    )


# ======================================================================
# 3. SCRAPE PROVIDERS
# ======================================================================

def scrape_firecrawl(url):
    """
    Scrape a webpage and convert it to clean Markdown using Firecrawl.
    Free tier allowance at firecrawl.dev.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "url": url,
        "formats": ["markdown"]
    }

    try:
        data = send_request("https://api.firecrawl.dev/v1/scrape", headers=headers, payload=payload)
        markdown = data.get("data", {}).get("markdown", "").strip()
        return markdown if markdown else None
    except Exception:
        return None


def scrape_basic(url):
    """
    Fallback scraper: fetches page via urllib and strips HTML tags.
    Requires no API keys and works offline/locally.
    """
    validate_url(url)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw_html = response.read(2 * 1024 * 1024).decode("utf-8", errors="replace")

        # Strip scripts, styles, and navigation bars
        cleaned = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
        # Strip remaining HTML tags
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        # Convert HTML entities like &amp; to &
        cleaned = html.unescape(cleaned)

        # Collect non-empty lines
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        return "\n\n".join(lines[:120])
    except Exception as e:
        sys.exit(f"Error scraping '{url}': {e}")


def scrape_browser(url):
    """
    Inspect a page locally using Chrome via agent-browser.
    Used for sites with heavy bot protection or Cloudflare walls.
    """
    validate_url(url)

    browser_cmd = shutil.which("agent-browser")
    if not browser_cmd:
        sys.exit(
            "Error: agent-browser CLI is not installed.\n"
            "To inspect Cloudflare pages with Chrome, run:\n"
            "    npm install -g agent-browser"
        )

    session_id = f"bare-session-{int(time.time())}"
    print(f"[Notice] Opening {url} with local Chrome...", file=sys.stderr)

    try:
        # Open URL
        subprocess.run([browser_cmd, "--session", session_id, "open", url], check=True, timeout=20)
        # Snapshot page text
        snapshot = subprocess.run([browser_cmd, "--session", session_id, "snapshot"], capture_output=True, text=True, timeout=15)
        return snapshot.stdout.strip()
    except Exception as e:
        sys.exit(f"Error running agent-browser: {e}")
    finally:
        # Always close session
        subprocess.run([browser_cmd, "--session", session_id, "close"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_scrape(url, provider="auto"):
    """
    Execute scrape.
    If provider is 'auto', it tries Firecrawl first.
    If no key or blocked, it falls back to basic HTML stripping.
    """
    validate_url(url)

    if provider == "browser":
        return scrape_browser(url)

    if provider == "firecrawl":
        content = scrape_firecrawl(url)
        if not content:
            sys.exit("Error: Firecrawl scrape failed or FIRECRAWL_API_KEY is not set.")
        return content

    if provider == "basic":
        return scrape_basic(url)

    # Auto mode: try Firecrawl first, then basic fetch
    if os.getenv("FIRECRAWL_API_KEY"):
        content = scrape_firecrawl(url)
        if content:
            return content

    return scrape_basic(url)


# ======================================================================
# 4. CLI INTERFACE
# ======================================================================

def main():
    load_env()

    parser = argparse.ArgumentParser(
        description="bare-research: Simple, dependency-free web search and scraping for AI agents."
    )
    subparsers = parser.add_subparsers(dest="command")

    # Command: search
    search_parser = subparsers.add_parser("search", help="Search the web")
    search_parser.add_argument("query", help="What to search for")
    search_parser.add_argument("--provider", choices=["auto", "tavily", "serper", "exa", "you"], default="auto", help="Search provider to use")
    search_parser.add_argument("--max", type=int, default=5, help="Number of results (1 to 50)")

    # Command: scrape
    scrape_parser = subparsers.add_parser("scrape", help="Extract text or Markdown from a URL")
    scrape_parser.add_argument("url", help="Webpage URL to scrape")
    scrape_parser.add_argument("--provider", choices=["auto", "firecrawl", "basic", "browser"], default="auto", help="Extraction method to use")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # --- Execute Search ---
    if args.command == "search":
        clean_query = args.query.strip()
        if not clean_query:
            sys.exit("Error: Search query cannot be empty.")

        max_results = max(1, min(args.max, 50))
        data = run_search(clean_query, provider=args.provider, count=max_results)

        print(f"## Search Results: {clean_query}")
        print(f"*Source: {data['provider']}*\n")

        if data.get("answer"):
            print(f"> **Answer:** {data['answer']}\n")

        results = data.get("results", [])
        if not results:
            print("No results found.")
        else:
            for index, item in enumerate(results, start=1):
                print(f"{index}. [{item['title']}]({item['url']})")
                if item.get("snippet"):
                    print(f"   {item['snippet'].strip()}\n")

    # --- Execute Scrape ---
    elif args.command == "scrape":
        clean_url = args.url.strip()
        content = run_scrape(clean_url, provider=args.provider)

        print(f"# Content: {clean_url}\n")
        print(content)


if __name__ == "__main__":
    main()