---
name: bare-research
description: Simple, dependency-free web search and page scraping for AI coding agents. Uses available free search keys (Tavily, Serper, Exa, You.com) with automatic fallback, and page extraction (Firecrawl, basic HTTP).
metadata:
  repository: https://github.com/paulablaza/bare-research
  install: npx skills add https://github.com/paulablaza/bare-research --skill bare-research
---

# bare-research

A lightweight research and scraping skill for coding agents (Hermes, Claude Code, Antigravity, OpenCode).

- Standard library Python only (no external packages or build steps).
- Never auto-installs system packages or spawns background browsers automatically.
- Falls back automatically between configured search keys.

---

## Capabilities

1. **Web Search (`search`):** Search the web for documentation, solutions, and facts. Tries Tavily (answers + sources), then Serper (Google index), Exa, and You.com.
2. **Page Scraping (`scrape`):** Extract page text using Firecrawl or lightweight built-in HTTP fetch.
3. **Manual Browser (`browser`):** Uses local Chrome via `agent-browser` only when explicitly requested for sites with heavy bot protection.

---

## Usage

Run `research.py` directly from the terminal or via your bash tool:

### Web Search
```bash
# Auto search (tries available keys in order: Tavily -> Serper -> Exa -> You.com)
python research.py search "how to configure Hermes Agent"

# Use a specific provider
python research.py search "site:reddit.com/r/LocalLLaMA Qwen 2.5" --provider serper
python research.py search "what is the latest Python release" --provider tavily
python research.py search "machine learning research papers" --provider exa
```

### Web Scraping
```bash
# Auto scrape (tries Firecrawl first, then basic HTTP)
python research.py scrape "https://example.com/docs"

# Force basic text fetch (no API keys needed)
python research.py scrape "https://example.com/article" --provider basic
```

---

## Browser Fallback Rules

- Never run `npm install -g agent-browser` automatically. If a page fails due to bot protection and the user needs browser extraction, notify the user:
  `Page is protected by Cloudflare. To inspect locally using Chrome, install agent-browser: npm install -g agent-browser`
- Never launch browser extraction silently. Only use `--provider browser` if explicitly requested.

---

## Environment Keys

Keys are read from `.env` in the current workspace, script directory, or parent folders:

```env
# Tavily: Direct answers and sources (https://tavily.com)
TAVILY_API_KEY=

# Serper: Google search index (https://serper.dev)
SEARCH_SERPER_API_KEY=
# Note: SERPER_API_KEY is also accepted

# Firecrawl: Clean Markdown extraction (https://firecrawl.dev)
FIRECRAWL_API_KEY=

# Exa: Semantic technical search (https://exa.ai)
EXA_API_KEY=

# You.com: Web index fallback (https://you.com)
YOU_API_KEY=
```