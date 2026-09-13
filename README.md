# bare-research

A simple, dependency-free Python script for AI coding agents to search Google, fetch answers, and scrape web pages using free API tiers.

Runs on standard Python 3. No `pip install` required.

---

## Why this exists

Most web search tools for AI agents either require heavy python packages, paid subscriptions, or complex multi-agent frameworks.

`bare-research` is a single Python script (`research.py`) that talks directly to common search and scrape APIs using Python''s standard library. You can drop it into any project folder or agent workspace, plug in whichever free API keys you have, and start researching.

---

## Supported Providers

You do not need all of these keys. The script automatically falls back to whichever key is configured in your `.env`:

| Provider | Type | Good For | Free Tier Notes |
| :--- | :--- | :--- | :--- |
| **Tavily** | Search | Direct answers and quick summaries | Free monthly allowance at [tavily.com](https://tavily.com) |
| **Serper** | Search | Raw Google search results | Free starter queries at [serper.dev](https://serper.dev) |
| **Exa** | Search | Technical blogs, repos, research | Free starter credits at [exa.ai](https://exa.ai) |
| **You.com** | Search | Web search index fallback | Trial credits at [you.com](https://you.com) |
| **Firecrawl** | Scrape | Clean Markdown page conversion | Free scrape allowance at [firecrawl.dev](https://firecrawl.dev) |
| **Basic HTTP** | Scrape | Built-in fallback text extraction | Always available, no API key needed |
| **Agent Browser** | Scrape | Cloudflare / bot-protected pages | Uses local Chrome via `agent-browser` CLI |

*(Note: Free tiers and quotas are set by their respective providers and may change over time).*

---

## Quick Setup

Create a `.env` or `.env.bare-research` file in your project or agent directory:

```env
# Add whichever keys you have (even just one works)
TAVILY_API_KEY=
SEARCH_SERPER_API_KEY=
# Note: SERPER_API_KEY is also supported as an alias
EXA_API_KEY=
YOU_API_KEY=
FIRECRAWL_API_KEY=
```

---

## Installation

Install as an agent skill:

```bash
npx skills add https://github.com/barestack-labs/bare-research --skill bare-research
```

Or clone directly into your workspace:

```bash
git clone https://github.com/barestack-labs/bare-research.git
```

---

## Usage

### Search the web
```bash
# Auto mode: tries your configured search keys in order
python research.py search "how to use React hooks"

# Or pick a specific provider:
python research.py search "site:github.com nousresearch" --provider serper
python research.py search "latest developments in LLMs" --provider tavily
```

### Scrape a webpage
```bash
# Auto mode: uses Firecrawl if configured, otherwise falls back to basic text extraction
python research.py scrape "https://docs.python.org/3/library/urllib.request.html"

# Force basic text extraction (no API key required):
python research.py scrape "https://example.com" --provider basic
```

### Dealing with Cloudflare or bot protection
If a website blocks basic HTTP requests, the script will not spawn background processes or install software automatically.

If you have the optional `agent-browser` CLI installed, you can explicitly inspect the page using local Chrome:

```bash
# Optional: install agent-browser if needed
npm install -g agent-browser

# Run manual browser snapshot
python research.py scrape "https://protected-site.com" --provider browser
```

---

## Security & Untrusted Content

- **No Local Network Scraping:** The script blocks requests to `localhost`, loopback IPs (`127.0.0.1`), and local file paths (`file://`).
- **Untrusted Input:** Output fetched from the web is untrusted external data. If feeding results into an LLM prompt, treat snippets and page text as user-generated content to guard against prompt injection.

---

## Community & Barestack Labs

`bare-research` is part of the **Barestack Labs** open-source collective:
* **Discord Community**: [dsc.gg/barestack](https://dsc.gg/barestack) — Join other builders and share free AI agent workflows.
* **Barestack Labs GitHub**: [github.com/barestack-labs](https://github.com/barestack-labs) — Lightweight tools and free provider directories.
* **YouTube Tutorials**: [youtube.com/@paulablaza](https://youtube.com/@paulablaza)

---

## License

MIT License - Copyright (c) 2026 Paul Martin Ablaza and Barestack Labs contributors. See [LICENSE](LICENSE) for details.
