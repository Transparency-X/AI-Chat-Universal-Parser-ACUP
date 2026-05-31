# AI Chat Universal Parser — Browser Scraper v1.1

> **Forensic-grade browser automation for platforms without native export APIs.**

---

## What v1.1 Adds

v1.0 required you to manually export chats via browser extensions or Takeout. **v1.1 eliminates that dependency** by automating the browser itself — logging into each platform, navigating conversation history, and extracting messages directly from the DOM.

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **Playwright Engine** | Chromium-based automation with stealth headers |
| **Virtual Scroll Capture** | Handles Angular/React virtualized lists (AI Studio, Gemini) |
| **Content Deduplication** | SHA-256 hashing prevents double-capture during scroll |
| **Forensic Screenshots** | Per-conversation before/after captures for chain-of-custody |
| **Session Persistence** | Cookies & localStorage saved to `session.json` for re-runs |
| **Credential Support** | DeepSeek email/OTP; Google SSO handled via browser |
| **v1.0 Pipeline Integration** | Scraped output auto-feeds into JSON/CSV/Markdown/Dashboard |
| **Selector Config** | JSON override for DOM selectors when sites change |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER LAYER (Playwright)                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│
│  │  Kimi   │ │ Mistral │ │DeepSeek │ │AI Studio│ │ Gemini ││
│  │  SSO    │ │  OAuth  │ │Email/  │ │ Google  │ │ Google ││
│  │  OTP    │ │         │ │  OTP   │ │  SSO   │ │  SSO   ││
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬────┘│
└───────┼───────────┼───────────┼───────────┼──────────┼────┘
        │           │           │           │          │
        └───────────┴───────────┴───────────┴──────────┘
                              │
                    ┌─────────▼──────────┐
                    │   VIRTUAL SCROLL     │
                    │   CAPTURE ENGINE     │
                    │  (dedup + hash +     │
                    │   screenshot)        │
                    └─────────┬────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐   ┌────────▼────────┐   ┌──────▼──────┐
│  Scraped     │   │  v1.0-compatible │   │  Forensic   │
│  Raw JSON    │   │     JSON         │   │  Screenshots│
│  (internal)  │   │  (parser input)  │   │   + Logs    │
│              │   │                  │   │             │
│ scraped_raw  │   │ conversations    │   │  .png +     │
│    .json     │   │   _scraped.json  │   │  session    │
└──────────────┘   └─────────────────┘   └─────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   v1.0 PARSER        │
                    │   (ai_chat_parser.py)│
                    │   → JSON / CSV / MD  │
                    └────────────────────┘
```

---

## Installation

### Prerequisites

```bash
# 1. Python 3.9+
python --version

# 2. Install Playwright
pip install playwright

# 3. Install browser binaries (Chromium only)
playwright install chromium
```

### Project Structure

```
acup-v1.1/
├── ai_chat_parser.py          # v1.0 core parser (unchanged)
├── generate_dashboard.py      # v1.0 dashboard generator (unchanged)
├── browser_scraper.py         # v1.1 scraper engine (NEW)
├── run_scraper.py             # v1.1 CLI wrapper + pipeline (NEW)
├── credentials_template.json  # Credential config template (NEW)
├── scraper_config.json        # DOM selector overrides (NEW)
├── requirements.txt           # v1.1 deps (NEW)
├── scraped/                   # Output directory (auto-created)
│   ├── session.json           # Cookie/session persistence
│   ├── screenshots/           # Forensic PNG captures
│   ├── scraped_raw.json       # Internal scraper format
│   ├── conversations_scraped.json  # v1.0-compatible input
│   ├── conversations.json     # Parsed standard JSON
│   ├── conversations.csv      # Parsed CSV
│   ├── markdown_layouts/    # Parsed Markdown
│   ├── stats.json             # Aggregate stats
│   └── dashboard.html         # Generated dashboard
└── README.md                  # This file
```

---

## Usage

### 1. Interactive Scrape (Recommended First Run)

```bash
# Scrape Kimi and Gemini — browser window opens for manual login
python run_scraper.py --platforms kimi gemini
```

**What happens:**
1. Browser opens to `kimi.com`
2. You complete login (OTP/SSO) in the window
3. Scraper detects sidebar → auto-navigates conversation list
4. Virtual-scroll capture begins with progress logging
5. Screenshots saved to `scraped/screenshots/`
6. Session cookies saved to `scraped/session.json`
7. Repeats for `gemini.google.com`

### 2. Headless Re-Run (After Session Established)

```bash
# Re-run using saved session — no browser window
python run_scraper.py --platforms kimi gemini --headless --session scraped/session.json
```

> ⚠️ **Headless mode may trigger bot detection** on some platforms. Use `--headless` only after session is warm.

### 3. Full Pipeline (Scrape → Parse → Dashboard)

```bash
# Scrape all platforms, auto-run parser, generate dashboard
python run_scraper.py --platforms all --parse --dashboard --max 20
```

**Pipeline output:**
- `scraped/conversations.json` — standard v1.0 JSON
- `scraped/conversations.csv` — flattened spreadsheet
- `scraped/markdown_layouts/` — per-conversation Prompt/Response MD
- `scraped/dashboard.html` — interactive overview

### 4. DeepSeek with Credentials

```bash
# Create credentials file
cp credentials_template.json my_creds.json
# Edit my_creds.json with your DeepSeek email

python run_scraper.py --platforms deepseek --credentials my_creds.json
```

If password is provided, scraper attempts form fill. If empty, it waits for OTP entry in browser.

### 5. Per-Platform Scrape (Direct API)

```python
import asyncio
from browser_scraper import ScraperRunner

runner = ScraperRunner(
    platforms=["kimi", "deepseek"],
    output_dir="./forensic_archive",
    headless=False,
    max_conversations=10
)
results = asyncio.run(runner.run())

for conv in results:
    print(f"{conv.platform}: {conv.title} ({len(conv.messages)} messages)")
    print(f"  Screenshots: {conv.screenshots}")
    print(f"  Log entries: {len(conv.log)}")
```

---

## Platform-Specific Notes

### Kimi (kimi.com)
- **Auth:** Phone/email OTP (PRC-based). No password-only login.
- **Scraper behavior:** Opens `kimi.com/chat`, waits for sidebar. You enter OTP in browser.
- **Virtual scroll:** Moderate. Messages stay in DOM once loaded.
- **Selector stability:** Medium. Class names are hashed in production builds. Use `scraper_config.json` to update.

### Mistral (chat.mistral.ai)
- **Auth:** Google/Microsoft OAuth or email magic link.
- **Scraper behavior:** Opens chat.mistral.ai, waits for sidebar. Complete OAuth in browser.
- **Virtual scroll:** Light. Conversation list is short for most users.
- **Note:** Le Chat has no conversation history API at all — this scraper is the only automated method.

### DeepSeek (chat.deepseek.com)
- **Auth:** Email + password or email + OTP.
- **Scraper behavior:** Supports credential auto-fill for email/password. OTP requires manual entry.
- **Virtual scroll:** Moderate. Code blocks render lazily.
- **Privacy warning:** Scraping occurs client-side (your machine). No data sent to DeepSeek servers beyond normal chat usage.

### Google AI Studio (aistudio.google.com)
- **Auth:** Google SSO (same as Gmail).
- **Scraper behavior:** Opens aistudio.google.com/chat. If already logged into Google, proceeds automatically.
- **Virtual scroll:** **Aggressive.** Angular CDK virtual scroll unmounts off-screen messages. The scraper uses incremental 500px scroll steps with 300ms settle time to force re-mounting.
- **Known issue:** Very long conversations (>100 turns) may lose early turns due to virtual scroll buffer limits. Use "Get code" export for critical long threads.

### Gemini (gemini.google.com)
- **Auth:** Google SSO.
- **Scraper behavior:** Opens gemini.google.com/app. Auto-detects logged-in state.
- **Virtual scroll:** **Aggressive.** Similar to AI Studio. Uses 500px incremental scroll.
- **Limitation:** Workspace accounts may disable share links; scraper still works if you have access.

---

## Forensic Features

### Chain of Custody

Every scraped conversation includes:

```json
{
  "scraped_at": "2026-05-31T01:35:00+00:00",
  "url": "https://kimi.com/chat/abc123",
  "screenshots": [
    "scraped/screenshots/kimi_convo_start_20260531_013500.png",
    "scraped/screenshots/kimi_convo_end_full_20260531_013515.png"
  ],
  "messages": [
    {
      "role": "assistant",
      "content": "...",
      "element_hash": "a1b2c3d4e5f6...",
      "model": "kimi-latest"
    }
  ]
}
```

- `scraped_at` — ISO 8601 UTC timestamp
- `screenshots` — Before/after visual verification
- `element_hash` — SHA-256 of raw DOM innerHTML for tamper detection
- `url` — Source URL for reproducibility

### Session Persistence

`session.json` stores cookies and localStorage state:

```json
{
  "cookies": [...],
  "storage": { "origins": [...] },
  "saved_at": "2026-05-31T01:35:00+00:00"
}
```

This allows:
- Re-running scraper without re-authenticating
- Transferring session between machines (treat as sensitive — contains auth tokens)
- Scheduled/cron-based scraping

### Logging

Every scraper action is logged with UTC timestamps:

```
[2026-05-31T01:35:00+00:00] kimi: Starting scraper run.
[2026-05-31T01:35:02+00:00] kimi: Already logged in (sidebar detected).
[2026-05-31T01:35:05+00:00] kimi: Found 12 conversation URLs.
[2026-05-31T01:35:06+00:00] kimi: [1/12] Scraping: https://kimi.com/chat/abc123
[2026-05-31T01:35:08+00:00] kimi: Screenshot saved: scraped/screenshots/kimi_convo_start_...
[2026-05-31T01:35:15+00:00] kimi: Scroll progress: 8 items, scrollTop=800
[2026-05-31T01:35:22+00:00] kimi: Scroll progress: 14 items, scrollTop=1600
[2026-05-31T01:35:25+00:00] kimi: End of scroll detected.
[2026-05-31T01:35:25+00:00] kimi: Virtual scroll complete: 14 unique items captured.
```

---

## Configuration

### DOM Selector Overrides

When platforms update their UI, class names change. Update `scraper_config.json` without touching code:

```json
{
  "kimi": {
    "chat_container": "[class*='chat-layout']",
    "message_turn": "[class*='message-row']",
    "user_indicator": "[class*='user-bubble']",
    "assistant_indicator": "[class*='ai-bubble']"
  },
  "gemini": {
    "chat_container": "[class*='conversation-scroll']",
    "message_turn": "[class*='message-block']"
  }
}
```

Pass to scraper:
```python
from browser_scraper import ScraperRunner
runner = ScraperRunner(
    platforms=["kimi"],
    credentials={"kimi": {"selectors": {...}}}
)
```

### Rate Limiting & Delays

Built-in delays are conservative:
- Scroll step: 500–800px
- Settle time: 300ms per step
- Max scrolls: 150–200 per conversation

To go faster (risk of detection):
```python
# In browser_scraper.py, modify _scroll_virtual_list defaults
scroll_step=1200,  # faster
# Or reduce sleep in the loop
```

To go slower (safer for large accounts):
```python
scroll_step=300,   # slower, more granular
# Increase sleep
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Timeout waiting for sidebar` | Not logged in | Complete login in browser window; session will save |
| `0 items captured` | Selectors outdated | Update `scraper_config.json` with new class names from DevTools |
| `Missing early messages` | Virtual scroll buffer | Reduce `scroll_step` to 300; increase `max_scrolls` |
| `Bot detection / CAPTCHA` | Headless mode or fast scraping | Use `--headless=False`; increase delays; use residential IP |
| `Duplicate messages` | Deduplication hash collision | Rare. Check `element_hash` in output to verify |
| `Session expired` | Google/Kimi token timeout | Re-run without `--session` to re-authenticate |

### Updating Selectors Manually

1. Open platform in browser → DevTools → Inspect message element
2. Copy outer HTML of a user message and an assistant message
3. Note the `class` attribute (e.g., `class="message user-message"`)
4. Update `scraper_config.json`:
   ```json
   {"kimi": {"message_turn": ".message", "user_indicator": ".user-message"}}
   ```

---

## Security & Privacy

- **Local-only processing:** All scraping occurs in your Playwright browser on your machine. No data sent to third-party APIs.
- **Session file sensitivity:** `session.json` contains authentication cookies. Store with `chmod 600` and exclude from Git.
- **Screenshot storage:** PNGs contain conversation content. Encrypt at rest if handling sensitive data.
- **DeepSeek note:** Scraping does not trigger the GDPR data-request process. Data stays local.

---

## Roadmap Integration

v1.1 fulfills the **"Browser automation scraper"** milestone from the v1.0 roadmap.

| Version | Status | Feature |
|---------|--------|---------|
| v1.0 | ✅ Complete | Parser + Dashboard for manual exports |
| **v1.1** | ✅ **Complete** | **Browser automation scraper** |
| v1.2 | Planned | Image attachment extraction & base64 embedding |
| v1.3 | Planned | Cross-platform diff view (same prompt, different AIs) |
| v1.4 | Planned | Notion/Obsidian direct sync |
| v1.5 | Planned | Cryptographic verification (SHA-256 per message) |

> v1.1 already includes per-message `element_hash` (SHA-256 of DOM content), which is the foundation for v1.5's full chain-of-custody verification.

---

## License

MIT — Your data belongs to you. Scrape responsibly.

---

*Generated for forensic-grade AI chat archival and cross-platform analysis.*
