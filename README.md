# AI Chat Universal Parser (ACUP) v1.0

> **Parse, standardize, and dashboard AI conversations from Kimi, Mistral, DeepSeek, Google AI Studio, and Gemini.**

---

## Table of Contents

1. [Overview](#overview)
2. [Supported Platforms & Export Methods](#supported-platforms--export-methods)
   - [Kimi (kimi.com / kimi.ai)](#kimi-kimicom--kimiai)
   - [Mistral (chat.mistral.ai)](#mistral-chatmistralai)
   - [DeepSeek (chat.deepseek.com)](#deepseek-chatdeepseekcom)
   - [Google AI Studio (aistudio.google.com)](#google-ai-studio-aistudiogooglecom)
   - [Gemini (gemini.google.com)](#gemini-geminigooglecom)
3. [Architecture](#architecture)
4. [Standard File Format](#standard-file-format)
5. [Layout Format (Markdown)](#layout-format-markdown)
6. [Installation & Usage](#installation--usage)
7. [Dashboard](#dashboard)
8. [Directory Structure](#directory-structure)
9. [Roadmap](#roadmap)

---

## Overview

ACUP is a forensic-grade parser designed to ingest chat exports from major AI web applications and normalize them into:

- **Standard JSON** — structured, queryable, machine-readable
- **Standard CSV** — flattened for spreadsheet analysis
- **Layout Markdown** — human-readable with explicit **Prompt** / **Response** separation
- **Interactive HTML Dashboard** — spreadsheet-like overview + per-platform breakdowns

### Why This Exists

AI chat platforms lock conversations in proprietary interfaces. None offer a universal export format. For researchers, developers, and forensic analysts who need to:

- Archive conversations with chain-of-custody integrity
- Cross-reference prompts across multiple AI platforms
- Build datasets for comparative analysis
- Maintain evidentiary records of AI interactions

…a unified parser is essential.

---

## Supported Platforms & Export Methods

### Kimi (kimi.com / kimi.ai)

| Method | Format | Reliability | Notes |
|--------|--------|-------------|-------|
| **Browser Extension** (YourAIScroll, AI Chat Exporter) | JSON / Markdown / HTML | ⭐⭐⭐⭐⭐ | Recommended. One-click full conversation export. Preserves code blocks and tables. |
| **Manual Copy-Paste** | Raw text | ⭐⭐⭐ | Lossy. Formatting degrades. Use as fallback only. |
| **Developer Tools** | Network intercept | ⭐⭐⭐⭐ | Advanced. Capture XHR responses from `kimi.com` API endpoints. Requires session auth. |
| **Official API Export** | ❌ Not available | — | Kimi does not provide a native bulk export or Takeout equivalent. |

**Recommended Workflow:**
1. Install [YourAIScroll](https://www.youraiscroll.com/) or [AI Chat Exporter](https://saveai.net/) extension
2. Open conversation on kimi.com
3. Click extension → Export as **JSON**
4. Save to `raw/kimi/`

---

### Mistral (chat.mistral.ai)

| Method | Format | Reliability | Notes |
|--------|--------|-------------|-------|
| **Browser Extension** (YourAIScroll, AI Chat Exporter) | JSON / Markdown | ⭐⭐⭐⭐⭐ | Recommended. Le Chat has no native export. |
| **Share Link** | Public URL | ⭐⭐⭐ | Generates `chat.mistral.ai/chat/...` link. Must be scraped or manually copied. |
| **Manual Copy-Paste** | Raw text | ⭐⭐⭐ | Lossy. Tables and code blocks may collapse. |
| **Official Export** | ❌ Not available | — | No GDPR Takeout or bulk download provided. |

**Recommended Workflow:**
1. Install multi-platform AI chat exporter extension
2. Export conversation as **JSON** or **Markdown**
3. Save to `raw/mistral/`

---

### DeepSeek (chat.deepseek.com)

| Method | Format | Reliability | Notes |
|--------|--------|-------------|-------|
| **Browser Extension** (DeepSeek Chat Exporter, YourAIScroll) | JSON / Markdown / CSV / PDF | ⭐⭐⭐⭐⭐ | Recommended. One-click export. |
| **GDPR Data Request** | JSON (raw) | ⭐⭐⭐⭐ | Email `service@deepseek.com` with account email. 30-day response time. Data stored in China. |
| **Print to PDF** | PDF | ⭐⭐ | Manual. Ctrl+P → Save as PDF. Formatting breaks on code blocks. |
| **Settings → Chat History** | ❌ View only | — | Can view and delete history. No download button. |

**Privacy Note:** DeepSeek stores data on servers in the PRC. For sensitive/acoustic forensics work, prefer browser extensions (local processing) over official data requests. citeweb_search:1#1

**Recommended Workflow:**
1. Install DeepSeek Chat Exporter or YourAIScroll
2. Export as **JSON** for parsing or **Markdown** for human review
3. Save to `raw/deepseek/`

---

### Google AI Studio (aistudio.google.com)

| Method | Format | Reliability | Notes |
|--------|--------|-------------|-------|
| **"Get Code" Button** | JSON (API-ready) | ⭐⭐⭐⭐⭐ | Cleanest programmatic format. Contains full `contents` array with `role`/`parts` structure. |
| **Google Drive Auto-Save** | JSON-like (no extension) | ⭐⭐⭐⭐ | Saved in Drive → `AI Studio` folder. Raw API format with metadata. Rename to `.json` to parse. |
| **Browser Extension** | Markdown / JSON | ⭐⭐⭐⭐ | Good for conversations where "Get code" is not used. |
| **Manual Copy** | Raw text | ⭐⭐ | AI Studio uses Angular virtual scroller; copy-paste misses off-screen content. |
| **Native Export Button** | ❌ Not available | — | No download button in UI. citeweb_search:1#2 |

**Recommended Workflow:**
1. In AI Studio conversation, click **Get code** → Copy JSON
2. Paste into `raw/aistudio/conversation_name.json`
3. OR: Access Drive → AI Studio folder → download auto-saved files → rename `.json`

**Drive File Format:**
```json
{
  "contents": [
    {"role": "user", "parts": [{"text": "prompt here"}]},
    {"role": "model", "parts": [{"text": "response here"}]}
  ],
  "model": "gemini-2.0-flash"
}
```

---

### Gemini (gemini.google.com)

| Method | Format | Reliability | Notes |
|--------|--------|-------------|-------|
| **Browser Extension** (Gemini Exporter, AI Chat Exporter) | JSON / Markdown / PDF / Word | ⭐⭐⭐⭐⭐ | Recommended for bulk export. Handles virtual scrolling. |
| **Google Takeout** (My Activity → Gemini Apps) | JSON | ⭐⭐⭐ | Official but unreliable. Must have "Gemini Apps Activity" enabled. Many users report missing option. citeweb_search:1#0 |
| **Per-Response Export** | Google Docs / Sheets | ⭐⭐⭐⭐ | Native. Exports **individual responses** only, not full threads. Good for specific answers. |
| **Share Link** | Public URL | ⭐⭐⭐ | `g.co/gemini/share/...`. Can be scraped. Not available for Workspace accounts. |
| **Gemini API** | JSON | ⭐⭐⭐⭐⭐ | If using API directly, history is in your infrastructure already. No export needed. |

**Recommended Workflow:**
1. For ongoing archiving: Use browser extension → Export as **JSON**
2. For one-time backup: Request Google Takeout → Deselect all → My Activity → Gemini Apps → Export
3. Save to `raw/gemini/`

**Takeout JSON Structure:**
```json
{
  "messages": [
    {"role": "user", "text": "..."},
    {"role": "model", "text": "..."}
  ],
  "title": "...",
  "createTime": "2026-05-29T09:00:00Z"
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     INPUT LAYER                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│
│  │  Kimi   │ │ Mistral │ │DeepSeek │ │AI Studio│ │ Gemini ││
│  │ .json   │ │ .json   │ │ .json   │ │ .json   │ │ .json  ││
│  │ .md     │ │ .md     │ │ .md     │ │ .md     │ │ .md    ││
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬────┘│
└───────┼───────────┼───────────┼───────────┼──────────┼────┘
        │           │           │           │          │
        └───────────┴───────────┴───────────┴──────────┘
                              │
                    ┌─────────▼──────────┐
                    │   AUTO-DETECT        │
                    │   (Platform Parser)  │
                    └─────────┬────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐   ┌────────▼────────┐   ┌──────▼──────┐
│   KimiParser │   │ MistralParser   │   │ DeepSeekParser│
│   (kimi)     │   │ (mistral)       │   │ (deepseek)    │
└──────────────┘   └─────────────────┘   └───────────────┘
┌──────────────┐   ┌─────────────────┐
│ AIStudioParser│   │  GeminiParser   │   │ MarkdownParser  │
│  (aistudio)   │   │   (gemini)      │   │  (fallback)     │
└──────────────┘   └─────────────────┘   └─────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  UNIFIED INTERNAL    │
                    │  Conversation +    │
                    │  Message dataclasses │
                    └─────────┬────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐   ┌────────▼────────┐   ┌──────▼──────┐
│  JSON Export │   │   CSV Export    │   │  Markdown   │
│  (standard)  │   │  (flattened)    │   │  (layout)   │
│              │   │                 │   │             │
│ conversations│   │  conversations  │   │  per-conv   │
│    .json     │   │     .csv        │   │    .md      │
└──────────────┘   └─────────────────┘   └─────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   DASHBOARD GEN    │
                    │   (HTML/JS)        │
                    │   dashboard.html   │
                    └────────────────────┘
```

### Parser Detection Strategy

Each parser implements `detect(raw_data)`:

1. **JSON input** → Check platform-specific keys (`kimi`, `mistral`, `deepseek`, `aistudio`, `gemini`)
2. **Text/Markdown input** → Regex match role prefixes (`**User**`, `**Assistant**`, `# Prompt`, etc.)
3. **AI Studio** → Detect `contents` array with `parts` objects
4. **Gemini** → Detect `model` role (mapped to `assistant`) and `user` role
5. **Fallback** → Generic Markdown parser attempts role extraction from common patterns

---

## Standard File Format

### JSON Schema (`conversations.json`)

```json
[
  {
    "conversation_id": "sha256_hash_16chars",
    "platform": "kimi|mistral|deepseek|aistudio|gemini",
    "title": "First 60 chars of first user message",
    "created_at": "2026-05-27T14:23:00Z",
    "updated_at": "2026-05-27T14:24:30Z",
    "message_count": 4,
    "user_message_count": 2,
    "assistant_message_count": 2,
    "word_count": 245,
    "messages": [
      {
        "role": "user",
        "content": "Analyse this acoustic harassment recording...",
        "timestamp": "2026-05-27T14:23:00Z",
        "model": "kimi-latest",
        "metadata": {}
      },
      {
        "role": "assistant",
        "content": "Based on the spectral analysis...",
        "timestamp": "2026-05-27T14:23:15Z",
        "model": "kimi-latest",
        "metadata": {}
      }
    ],
    "metadata": {
      "model": "kimi-latest",
      "source": "browser_extension"
    },
    "source_file": "kimi_export_2026-05-27.json"
  }
]
```

### CSV Schema (`conversations.csv`)

Flattened for spreadsheet analysis. One row per message:

| Column | Description |
|--------|-------------|
| `conversation_id` | Parent conversation hash |
| `platform` | Source platform |
| `title` | Conversation title |
| `conversation_created` | Conversation timestamp |
| `message_role` | `user` / `assistant` / `system` |
| `message_content` | Full message text |
| `message_timestamp` | Message timestamp |
| `message_model` | Model identifier |
| `source_file` | Original export filename |

---

## Layout Format (Markdown)

Each conversation exports to a separate Markdown file with **explicit Prompt/Response separation**:

```markdown
# Acoustic Forensics Analysis

**Platform:** kimi  
**Conversation ID:** kimi_abc123  
**Created:** 2026-05-27T14:23:00Z  
**Source:** kimi_export_2026-05-27.json  
**Messages:** 4  

---

## Prompt 1
**User** | 2026-05-27T14:23:00Z
*(Model context: kimi-latest)*

```
Analyse this acoustic harassment recording for spectral anomalies
```

## Response 1
**Assistant (kimi-latest)** | 2026-05-27T14:23:15Z

```
Based on the spectral analysis, I've identified several anomalies...
```

## Prompt 2
**User** | 2026-05-27T14:24:00Z
*(Model context: kimi-latest)*

```
Can you generate a Python script to detect these patterns automatically?
```

## Response 2
**Assistant (kimi-latest)** | 2026-05-27T14:24:30Z

```
import numpy as np
from scipy import signal
...
```

---

*End of conversation. Exported by ACUP v1.0.0*
```

**Design Rationale:**
- **Prompt** sections contain only user input (the "question" or "task")
- **Response** sections contain only AI output (the "answer" or "artifact")
- Code blocks preserve formatting for direct copy-paste into IDEs
- Timestamps maintain chronological/evidentiary order
- Model context aids reproducibility and version tracking

---

## Installation & Usage

### Requirements

- Python 3.9+
- No external dependencies (stdlib only)

### Quick Start

```bash
# 1. Place raw exports in platform subdirectories
mkdir -p raw/{kimi,mistral,deepseek,aistudio,gemini}

# 2. Run parser on directory
python ai_chat_parser.py raw/ --pattern "*.json" \
  --json-out conversations.json \
  --csv-out conversations.csv \
  --md-out markdown_layouts/

# 3. Generate dashboard
python generate_dashboard.py --input conversations.json --output dashboard.html

# 4. Open dashboard in browser
open dashboard.html
```

### Single File Parsing

```bash
python ai_chat_parser.py raw/kimi/export_001.json \
  --json-out out.json \
  --csv-out out.csv \
  --md-out ./layouts
```

### Programmatic Use

```python
from ai_chat_parser import parse_directory, export_json, export_csv, export_markdown_layout

conversations = parse_directory("./raw", "*.json")
export_json(conversations, "archive.json")
export_csv(conversations, "archive.csv")
export_markdown_layout(conversations, "./markdown_layouts")
```

---

## Dashboard

The generated `dashboard.html` provides:

### Global Overview
- **Stat cards**: Total conversations, messages, words, platforms
- **Master table**: All conversations with platform badges, message counts, word counts, dates
- **Real-time search**: Filter by title, platform, or content keywords

### Per-Platform Tables
- One card per detected platform (Kimi, Mistral, DeepSeek, AI Studio, Gemini)
- Conversation listing with title, message count, word count, creation date
- Responsive grid layout (2-3 columns on desktop, 1 on mobile)

### Screenshot Structure

```
┌────────────────────────────────────────────┐
│  🤖 AI Chat Universal Dashboard            │
│  5 Conversations | 22 Messages | 3,770 W  │
├────────────────────────────────────────────┤
│  [Search all conversations...      ]     │
├────────────────────────────────────────────┤
│  Platform | Title | Msgs | U/A | Words | Date │
│  ─────────────────────────────────────────  │
│  KIMI     | Acoustic Forensics | 4 | 2/2 | 245 │
│  DEEPSEEK | Side-Channel Att.. | 6 | 3/3 | 512 │
│  GEMINI   | Legal Framework.. | 3 | 1/2 |1890 │
│  ...                                       │
├────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐          │
│  │   KIMI      │  │  MISTRAL    │          │
│  │  1 convo    │  │  1 convo    │          │
│  │  4 msgs     │  │  5 msgs     │          │
│  │ [table]     │  │ [table]     │          │
│  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐  ┌─────────────┐          │
│  │  DEEPSEEK   │  │   GEMINI    │          │
│  │  1 convo    │  │  1 convo    │          │
│  │  6 msgs     │  │  3 msgs     │          │
│  │ [table]     │  │ [table]     │          │
│  └─────────────┘  └─────────────┘          │
└────────────────────────────────────────────┘
```

---

## Directory Structure

```
acup-project/
├── ai_chat_parser.py          # Core parser (stdlib only)
├── generate_dashboard.py      # HTML dashboard generator
├── sample_conversations.json  # Demo data (5 platforms)
├── dashboard.html             # Generated dashboard (from sample)
├── raw/                       # Your raw exports (create this)
│   ├── kimi/
│   ├── mistral/
│   ├── deepseek/
│   ├── aistudio/
│   └── gemini/
├── parsed/                    # Output directory (auto-created)
│   ├── conversations.json     # Standard JSON
│   ├── conversations.csv      # Standard CSV
│   ├── stats.json             # Aggregate statistics
│   └── markdown_layouts/      # Per-conversation Markdown
│       ├── kimi_Acoustic_F...abc123.md
│       ├── deepseek_Side-C...def456.md
│       └── ...
└── README.md                  # This file
```

---

## Roadmap

| Version | Feature | Priority |
|---------|---------|----------|
| v1.1 | **Browser automation scraper** (Selenium/Playwright) for platforms without exports | High |
| v1.2 | **Image attachment extraction** and base64 embedding in Markdown | Medium |
| v1.3 | **Diff view**: Compare same prompt across multiple platforms | Medium |
| v1.4 | **Notion/Obsidian sync** direct from parser | Low |
| v1.5 | **Cryptographic verification** (SHA-256 per message) for chain-of-custody | High |
| v2.0 | **Streamlit dashboard** as alternative to static HTML | Medium |

---

## License

MIT License — Free to use, modify, and distribute. Your conversations belong to you.

---

*Generated for forensic-grade AI chat archival and cross-platform analysis.*
