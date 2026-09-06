#!/usr/bin/env python3
"""
bare-research: The $0 Research & Scraping Stack for AI Agents
Supports Tavily, Serper, Firecrawl, Exa, You.com.
Zero external pip dependencies required. Pure standard library.
Strictly hands-off: Never auto-installs system packages or spawns silent background browsers.
"""

import os
import sys
import json
import argparse
import shutil
import subprocess
import re
import urllib.request
import urllib.parse
import urllib.error

# Ensure UTF-8 output on Windows consoles to prevent cp1252 crashes
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_env():
    """Load key-value pairs from .env files without requiring python-dotenv."""
    candidate_paths = [
        os.path.join(os.getcwd(), ".env.bare-research"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.bare-research"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.bare-research"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        "D:/paul-knowledge-base/.env",
        os.path.expanduser("~/.env.bare-research"),
        os.path.expanduser("~/.env")
    ]
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


def make_request(url, headers=None, data=None, method="GET", timeout=15):
    """Simple standard library HTTP requester with zero external dependencies."""
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
        content = response.read().decode("utf-8", errors="replace")
        return response.status, content


# ----------------------------------------------------------------------
# SEARCH PROVIDERS
# ----------------------------------------------------------------------

def search_tavily(query, max_results=5):
    """Search using Tavily API (Free tier: 1,000 queries/month, no card)."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"error": "Missing TAVILY_API_KEY in environment or .env"}

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": max_results
    }
    try:
        status, body = make_request(url, data=payload, method="POST")
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
    """Search using Serper Google Index (Free tier: 2,500 queries on signup)."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {"error": "Missing SERPER_API_KEY in environment or .env"}

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
    """Search using Exa AI API (Free tier: $10/month credit, no card)."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return {"error": "Missing EXA_API_KEY in environment or .env"}

    url = "https://api.exa.ai/search"
    headers = {"x-api-key": api_key}
    payload = {
        "query": query,
        "numResults": max_results,
        "type": "neural",
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
            "provider": "Exa (Neural)",
            "query": query,
            "answer": None,
            "results": results
        }
    except Exception as e:
        return {"error": f"Exa search failed: {e}"}


def search_you(query, max_results=5):
    """Search using You.com API (Free tier: $100 trial credit)."""
    api_key = os.getenv("YOU_API_KEY")
    if not api_key:
        return {"error": "Missing YOU_API_KEY in environment or .env"}

    encoded = urllib.parse.quote(query)
    url = f"https://api.ydc-index.io/search?query={encoded}&count={max_results}"
    headers = {"X-API-Key": api_key}
    try:
        status, body = make_request(url, headers=headers)
        data = json.loads(body)
        results = []
        for hit in data.get("hits", [])[:max_results]:
            results.append({
                "title": hit.get("title", "No title"),
                "url": hit.get("url", ""),
                "content": " ".join(hit.get("snippets", []))
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
    """Smart fallback search: Tavily -> Serper -> Exa -> You.com."""
    # Priority 1: Tavily (direct answers + citations)
    if os.getenv("TAVILY_API_KEY"):
        res = search_tavily(query, max_results)
        if "error" not in res:
            return res

    # Priority 2: Serper (raw Google index)
    if os.getenv("SERPER_API_KEY"):
        res = search_serper(query, max_results)
        if "error" not in res:
            return res

    # Priority 3: Exa (neural semantic search)
    if os.getenv("EXA_API_KEY"):
        res = search_exa(query, max_results)
        if "error" not in res:
            return res

    # Priority 4: You.com
    if os.getenv("YOU_API_KEY"):
        res = search_you(query, max_results)
        if "error" not in res:
            return res

    return {
        "error": "No working search API keys found. Please set TAVILY_API_KEY or SERPER_API_KEY in your .env file."
    }


# ----------------------------------------------------------------------
# SCRAPING & CONTENT EXTRACTION
# ----------------------------------------------------------------------

def scrape_firecrawl(url):
    """Scrape and convert page to clean Markdown using Firecrawl API."""
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
            return {
                "provider": "Firecrawl",
                "url": url,
                "title": title,
                "markdown": markdown
            }
        else:
            return {"error": f"Firecrawl failed: {data.get('error')}"}
    except Exception as e:
        return {"error": f"Firecrawl request failed: {e}"}


def scrape_basic(url):
    """Lightweight fallback scraper using standard urllib without external dependencies."""
    try:
        status, html = make_request(url)
        # Simple HTML tag stripper
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<noscript[^>]*>.*?</noscript>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n\n".join(lines[:120])
        return {
            "provider": "Basic HTTP",
            "url": url,
            "title": "Raw Page Extraction",
            "markdown": clean_text
        }
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "status_code": e.code}
    except Exception as e:
        return {"error": f"Basic scrape failed: {e}"}


def find_agent_browser():
    """Locate agent-browser executable on the system without installing anything."""
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
    """
    Explicit browser inspection using local Chrome via agent-browser.
    Strictly manual and transparent. Never launched silently in auto mode.
    """
    browser_bin = find_agent_browser()
    if not browser_bin:
        msg = (
            "\n" + "=" * 60 + "\n"
            + "[NOTICE] agent-browser CLI is not installed on your system.\n\n"
            + "This site has bot protection or requires live JavaScript rendering.\n"
            + "To inspect this page locally using headless Chrome, you can install\n"
            + "agent-browser yourself by running:\n\n"
            + "    npm install -g agent-browser\n\n"
            + "No automatic installation will be performed on your system.\n"
            + "=" * 60 + "\n"
        )
        return {"error": msg, "uninstalled": True}

    mode_label = "headed" if headed else "headless"
    print("\n" + "=" * 60, file=sys.stderr)
    print(f"[NOTICE] Launching local {mode_label} Chrome via Agent Browser...", file=sys.stderr)
    print(f"Target URL: {url}", file=sys.stderr)
    print("Reason: Explicit browser extraction requested.", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    session_id = "bare-research-session"
    try:
        # Open URL with a strict 15s timeout
        open_cmd = [browser_bin, "--session", session_id]
        if headed:
            open_cmd.append("--headed")
        open_cmd.extend(["open", url])
        subprocess.run(open_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)

        # Snapshot with a strict 10s timeout
        snap_cmd = [browser_bin, "--session", session_id, "snapshot"]
        res = subprocess.run(snap_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        content = res.stdout

        # Clean close
        close_cmd = [browser_bin, "--session", session_id, "close"]
        subprocess.run(close_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)

        return {
            "provider": f"Agent Browser ({mode_label} Chrome)",
            "url": url,
            "title": "Browser Snapshot",
            "markdown": content.strip()
        }
    except subprocess.TimeoutExpired:
        # If it hangs, kill session and exit cleanly
        try:
            subprocess.run([browser_bin, "--session", session_id, "close"], timeout=3)
        except Exception:
            pass
        return {"error": "Agent Browser timed out while loading the page."}
    except Exception as e:
        return {"error": f"Agent Browser execution failed: {e}"}


def run_auto_scrape(url):
    """
    Safe auto-scraper: Firecrawl -> Basic HTTP.
    NOTE: Never spawns browser automatically to avoid surprise processes and security flags.
    If blocked by bot protection, informs the user with instructions for manual browser fallback.
    """
    # Priority 1: Firecrawl (clean markdown)
    if os.getenv("FIRECRAWL_API_KEY"):
        res = scrape_firecrawl(url)
        if "error" not in res:
            return res

    # Priority 2: Basic HTTP fetch
    res = scrape_basic(url)
    if "error" not in res:
        return res

    # If blocked by 403/429/Cloudflare, return a clean explanatory notice
    status_code = res.get("status_code")
    if status_code in [403, 429, 503] or "HTTP" in res.get("error", ""):
        return {
            "error": (
                f"Page returned {res.get('error', 'access blocked')} (bot protection or Cloudflare).\n"
                "To inspect this page locally with headless Chrome, run:\n"
                f"    python research.py scrape \"{url}\" --provider browser\n"
                "(Requires agent-browser CLI installed: npm install -g agent-browser)"
            )
        }

    return res


# ----------------------------------------------------------------------
# CLI FORMATTING & ENTRY POINT
# ----------------------------------------------------------------------

def format_search_output(data):
    """Format search results into clean Markdown."""
    if "error" in data:
        return f"Error: {data['error']}"

    out = []
    out.append(f"## Search Results: {data['query']}")
    out.append(f"*Source: {data['provider']}*\n")

    if data.get("answer"):
        out.append(f"> **Quick Answer:** {data['answer']}\n")

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
    """Format scrape output into clean Markdown."""
    if "error" in data:
        return f"Error: {data['error']}"

    out = []
    out.append(f"# {data.get('title', 'Page Content')}")
    out.append(f"*URL: {data['url']} (Extracted via {data['provider']})*\n")
    out.append(data.get("markdown", "").strip())
    return "\n".join(out)


def main():
    load_env()

    parser = argparse.ArgumentParser(
        description="bare-research: The $0 Research & Scraping Stack for AI Agents"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search subparser
    search_parser = subparsers.add_parser("search", help="Search the web")
    search_parser.add_argument("query", type=str, help="Search query string")
    search_parser.add_argument(
        "--provider",
        choices=["auto", "tavily", "serper", "exa", "you"],
        default="auto",
        help="Search provider to use (default: auto)"
    )
    search_parser.add_argument(
        "--max",
        type=int,
        default=5,
        help="Maximum results to return (default: 5)"
    )

    # Scrape subparser
    scrape_parser = subparsers.add_parser("scrape", help="Extract clean Markdown from a URL")
    scrape_parser.add_argument("url", type=str, help="Target URL to scrape")
    scrape_parser.add_argument(
        "--provider",
        choices=["auto", "firecrawl", "basic", "browser"],
        default="auto",
        help="Extraction provider to use (default: auto, browser requires explicit flag)"
    )
    scrape_parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode if browser extraction is explicitly requested"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        if args.provider == "tavily":
            data = search_tavily(args.query, args.max)
        elif args.provider == "serper":
            data = search_serper(args.query, args.max)
        elif args.provider == "exa":
            data = search_exa(args.query, args.max)
        elif args.provider == "you":
            data = search_you(args.query, args.max)
        else:
            data = run_auto_search(args.query, args.max)

        print(format_search_output(data))

    elif args.command == "scrape":
        if args.provider == "firecrawl":
            data = scrape_firecrawl(args.url)
        elif args.provider == "basic":
            data = scrape_basic(args.url)
        elif args.provider == "browser":
            data = scrape_with_browser(args.url, headed=args.headed)
        else:
            data = run_auto_scrape(args.url)

        print(format_scrape_output(data))


if __name__ == "__main__":
    main()
