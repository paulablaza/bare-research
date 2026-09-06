# bare-research

Free web search and page scraping for your AI coding agents.

If you use coding agents like Hermes Agent, Claude Code, or Antigravity, you already know what happens when you ask them to search the web or read documentation: they either hallucinate, or they ask you to buy expensive API subscriptions.

You do not need to pay for search. This tool connects your agent to free tiers from Tavily, Serper, and Firecrawl using plain Python with zero extra pip packages.

---

## Free plans comparison

None of these require a credit card to get started.

| Tool | Free allowance | Type | Best for |
| :--- | :--- | :--- | :--- |
| **Tavily** | 1,000 queries / month | Recurring monthly | Direct answers, summarized facts, instant context |
| **Serper** | 2,500 queries | One-time on signup | Raw Google search, official links, Reddit lookups |
| **Firecrawl** | 500 to 1,000 credits / month | Recurring monthly | Converting web pages and docs into clean Markdown |
| **Exa** | $10 credit / month (~1,000 queries) | Recurring monthly | Finding engineering blogs, papers, and GitHub repos |
| **You.com** | $100 trial credit | Trial on signup | Fast multi-source search index backup |
| **Agent Browser** | Unlimited | Optional local fallback | Looking at pages with heavy JavaScript or Cloudflare |

---

## Quick setup: Copy-pasteable .env

You can create a `.env` or `.env.bare-research` file in whatever folder your agent is working in. The script finds it automatically.

Here is the template you can copy-paste directly:

```env
TAVILY_API_KEY=
SERPER_API_KEY=
FIRECRAWL_API_KEY=
EXA_API_KEY=
YOU_API_KEY=
```

You do not need all of them to start. Even just pasting a free Tavily key is enough to get working web search.

---

## What each tool does

- **Tavily (Start with this):** Ask a question, get an actual answer plus links in one shot. You get 1,000 free searches every month without a credit card.
- **Serper:** Raw Google search. Good for finding official docs or reading Reddit discussions without cookies (just search `site:reddit.com/r/LocalLLaMA <topic>`). You get 2,500 free searches on signup without a card.
- **Firecrawl:** Paste a URL, get clean Markdown back. It strips ads, navigation bars, and cookie banners so your agent only reads the actual content. You get 500 to 1,000 free credits a month.
- **Agent Browser (Optional fallback):** If a website blocks normal scrapers with Cloudflare, you can use local Chrome to look at the page. We do not force this install. If you ever need it, just tell your agent "install agent-browser" or run `npm install -g agent-browser` yourself.

---

## Testing in your terminal

Search:
```bash
python research.py search "what is Hermes Agent Bot Mode"
```

Google / Reddit search:
```bash
python research.py search "site:reddit.com/r/LocalLLaMA DeepSeek R1" --provider serper
```

Scrape a URL:
```bash
python research.py scrape "https://github.com/NousResearch/hermes-agent"
```

Optional browser inspection (for Cloudflare pages):
```bash
python research.py scrape "https://protected-site.com" --provider browser
```

---

## Adding this to your agent

- **Hermes Agent:** Copy `bare-research` into `~/.hermes/skills/bare-research`. Hermes reads `SKILL.md` and uses it automatically.
- **Claude Code:** Reference `research.py` directly in your terminal or prompt instructions.
- **Antigravity / OpenCode:** Drop `bare-research` into your workspace `.agents/skills/` directory.

---

## Why this is built hands-off

1. **No surprise installs:** The script will never install packages behind your back. If you want browser fallback, you decide when to install it.
2. **No background browser popups:** The script never launches Chrome on its own during auto search or scrape. You have to pass `--provider browser` on purpose.
3. **Clean security audits:** Built with standard library Python (`urllib`, `json`, `argparse`). No `node_modules`, no `requirements.txt`. It passes audit tools like Socket, Snyk, and Gen Agent Trust Hub with zero alerts.

---

## How we can improve this skill (Roadmap)

Ideas to make this even better in future updates:

- **Local Markdown caching:** Save scraped web pages to a local `cache/` folder so if your agent reads the same documentation page 5 times, it uses 0 API credits.
- **Zero-key fallback (DuckDuckGo):** Add an automatic free fallback using public search when you do not have any API keys configured at all.
- **Multi-page doc scraper:** Give it a root documentation URL and let it scrape the top 3 sub-pages in one shot so your agent gets complete library context.
- **Academic paper search:** Plug in Semantic Scholar and arXiv free endpoints (100% free forever, no key required) for deep research mode.
