---
name: bare-research
description: The $0 research, search, and page scraping skill for AI coding agents. Uses 100% free API keys (Tavily, Serper, Firecrawl, Exa, You.com) with automatic fallback and optional local Agent Browser inspection for bot-protected pages.
---

# Bare-Research: The $0 Agent Research Stack

A lightweight, portable research and scraping skill designed for AI agents (Hermes Agent, Claude Code, Antigravity, OpenCode).

Built to comply with strict security audits (Gen Agent Trust Hub, Socket, Snyk):
- Zero external package dependencies (pure Python standard library).
- Zero automated package installation (hands-off policy).
- Zero silent background browser processes.

---

## Core Capabilities

1. **Web Search (`search`):** Query the web and return summarized facts and direct source links. Automatically tries Tavily (direct answers), then Serper (Google index), then Exa (neural search).
2. **Page Scraping (`scrape`):** Extract clean, ad-free Markdown from any URL using Firecrawl API or lightweight direct fetch.
3. **Optional Browser Inspection (`browser`):** Uses local Chrome via `agent-browser` only when explicitly invoked by the user for bot-protected pages.

---

## Agent Usage Instructions

When you need fresh information from the web or need to read the contents of a specific URL, run `research.py` via your bash or terminal tool.

### 1. Web Search (Facts, News, Documentation, Alternatives)

```bash
# Auto search (uses Tavily -> Serper -> Exa)
python research.py search "how to configure Hermes Agent Bot Mode"

# Force specific provider
python research.py search "best free AI APIs 2026" --provider tavily
python research.py search "site:reddit.com/r/LocalLLaMA DeepSeek R1" --provider serper
python research.py search "high quality technical blog posts on MoE" --provider exa
```

### 2. URL Scraping (Reading Docs, Articles, Repos)

```bash
# Auto scrape (uses Firecrawl -> basic HTTP)
python research.py scrape "https://example.com/docs"

# Force Firecrawl clean markdown
python research.py scrape "https://example.com/article" --provider firecrawl
```

---

## Browser and Security Rules

### 1. Hands-off installation (Never auto-install)
If `agent-browser` is not installed on the user's computer, never run `npm install -g agent-browser` or download binaries automatically.

Tell the user:
> *"Notice: This page has bot protection. To inspect it using headless Chrome, you can install Agent Browser by running: `npm install -g agent-browser`."*

### 2. Never silently launch Chrome
Browser scraping never runs automatically. If you run `--provider browser` at the user's request, print a notice first:
> *"Notice: Launching local headless Chrome via Agent Browser to inspect [URL]..."*

---

## Environment Configuration

Keys are read from `.env` in the current working directory, project folder, or user home folder:

```bash
# Tavily: 1,000 free searches / month (Recommended primary search key)
TAVILY_API_KEY=tvly-...

# Serper: 2,500 free Google searches on signup (Recommended for Reddit / official links)
SERPER_API_KEY=...

# Firecrawl: 500-1,000 free scrape credits / month (Recommended for page extraction)
FIRECRAWL_API_KEY=fc-...

# Exa: $10/month free credit (Neural semantic search)
EXA_API_KEY=...

# You.com: $100 trial credit (Fast web index)
YOU_API_KEY=...
```
