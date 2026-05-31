#!/usr/bin/env python3
"""
AI Chat Universal Parser (ACUP)
Parses exports from Kimi, Mistral, DeepSeek, Google AI Studio, and Gemini
into standardized JSON/CSV and structured Markdown layouts.

Platforms Supported:
  - kimi.com
  - chat.mistral.ai
  - chat.deepseek.com
  - aistudio.google.com
  - gemini.google.com

Author: AI Assistant
Version: 1.0.0
"""

import json
import csv
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import argparse


@dataclass
class Message:
    role: str          # "user" | "assistant" | "system"
    content: str
    timestamp: Optional[str] = None
    model: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Conversation:
    conversation_id: str
    platform: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: List[Message] = None
    metadata: Dict[str, Any] = None
    source_file: Optional[str] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.metadata is None:
            self.metadata = {}
        if not self.conversation_id:
            self.conversation_id = hashlib.sha256(
                f"{self.platform}:{self.title}:{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "platform": self.platform,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.messages),
            "user_message_count": sum(1 for m in self.messages if m.role == "user"),
            "assistant_message_count": sum(1 for m in self.messages if m.role == "assistant"),
            "word_count": sum(len(m.content.split()) for m in self.messages),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "model": m.model,
                    "metadata": m.metadata
                } for m in self.messages
            ],
            "metadata": self.metadata,
            "source_file": self.source_file
        }


class BaseParser:
    """Base class for all platform parsers."""
    PLATFORM = "unknown"

    def parse(self, raw_data: Any, source_file: str = "") -> Conversation:
        raise NotImplementedError

    def detect(self, raw_data: Any) -> bool:
        """Return True if this parser can handle the raw data."""
        raise NotImplementedError


class KimiParser(BaseParser):
    """
    Kimi (kimi.com / kimi.ai) Parser

    Native Export Formats:
      - Browser extension JSON/Markdown (recommended)
      - Manual copy-paste HTML
      - No official bulk export API

    Expected Input: JSON array or Markdown from extensions like YourAIScroll
    """
    PLATFORM = "kimi"

    def detect(self, raw_data: Any) -> bool:
        if isinstance(raw_data, dict):
            return any(k in raw_data for k in ["kimi", "moonshot", "moonshot_ai"])
        if isinstance(raw_data, list) and len(raw_data) > 0:
            first = raw_data[0]
            if isinstance(first, dict):
                return any(k in first for k in ["kimi", "moonshot"])
        text = str(raw_data)[:500].lower()
        return "kimi" in text and ("user" in text or "assistant" in text)

    def parse(self, raw_data: Any, source_file: str = "") -> Conversation:
        conv = Conversation(
            platform=self.PLATFORM,
            title="Kimi Conversation",
            source_file=source_file
        )

        if isinstance(raw_data, list):
            # Extension JSON format: [{role, content, timestamp}, ...]
            for item in raw_data:
                msg = Message(
                    role=item.get("role", "unknown"),
                    content=item.get("content", ""),
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "kimi-latest"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "content", "timestamp", "model"]}
                )
                conv.messages.append(msg)
            if conv.messages:
                conv.title = conv.messages[0].content[:60] + "..." if len(conv.messages[0].content) > 60 else conv.messages[0].content

        elif isinstance(raw_data, dict):
            # Nested format: {messages: [...], title: ...}
            messages = raw_data.get("messages", raw_data.get("history", []))
            conv.title = raw_data.get("title", raw_data.get("topic", "Kimi Conversation"))
            conv.created_at = raw_data.get("created_at", raw_data.get("timestamp"))
            for item in messages:
                msg = Message(
                    role=item.get("role", item.get("sender", "unknown")),
                    content=item.get("content", item.get("text", "")),
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "kimi-latest"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "content", "timestamp", "model"]}
                )
                conv.messages.append(msg)

        return conv


class MistralParser(BaseParser):
    """
    Mistral (chat.mistral.ai / Le Chat) Parser

    Native Export Formats:
      - Browser extension JSON/Markdown (recommended)
      - No official bulk export
      - Share links provide public URL but not structured data

    Expected Input: JSON from AI Chat Exporter or similar
    """
    PLATFORM = "mistral"

    def detect(self, raw_data: Any) -> bool:
        text = str(raw_data)[:500].lower()
        return "mistral" in text or "le chat" in text

    def parse(self, raw_data: Any, source_file: str = "") -> Conversation:
        conv = Conversation(
            platform=self.PLATFORM,
            title="Mistral Conversation",
            source_file=source_file
        )

        if isinstance(raw_data, list):
            for item in raw_data:
                role = item.get("role", item.get("sender", "unknown"))
                # Mistral sometimes uses "human" / "ai"
                if role in ["human", "Human"]:
                    role = "user"
                elif role in ["ai", "AI", "bot"]:
                    role = "assistant"
                msg = Message(
                    role=role,
                    content=item.get("content", item.get("text", "")),
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "mistral-large"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "content", "timestamp", "model"]}
                )
                conv.messages.append(msg)
        elif isinstance(raw_data, dict):
            messages = raw_data.get("messages", raw_data.get("history", []))
            conv.title = raw_data.get("title", "Mistral Conversation")
            for item in messages:
                role = item.get("role", item.get("sender", "unknown"))
                if role in ["human", "Human"]:
                    role = "user"
                elif role in ["ai", "AI"]:
                    role = "assistant"
                msg = Message(
                    role=role,
                    content=item.get("content", item.get("text", "")),
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "mistral-large"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "content", "timestamp", "model"]}
                )
                conv.messages.append(msg)

        if conv.messages:
            conv.title = conv.messages[0].content[:60] + "..." if len(conv.messages[0].content) > 60 else conv.messages[0].content
        return conv


class DeepSeekParser(BaseParser):
    """
    DeepSeek (chat.deepseek.com) Parser

    Native Export Formats:
      - Browser extension JSON/Markdown/CSV (recommended)
      - GDPR data request: email service@deepseek.com (30-day response)
      - No native one-click export
      - Print-to-PDF (manual, lossy)

    Expected Input: JSON from DeepSeek Chat Exporter or similar
    """
    PLATFORM = "deepseek"

    def detect(self, raw_data: Any) -> bool:
        text = str(raw_data)[:500].lower()
        return "deepseek" in text or "deep seek" in text

    def parse(self, raw_data: Any, source_file: str = "") -> Conversation:
        conv = Conversation(
            platform=self.PLATFORM,
            title="DeepSeek Conversation",
            source_file=source_file
        )

        if isinstance(raw_data, list):
            for item in raw_data:
                msg = Message(
                    role=item.get("role", "unknown"),
                    content=item.get("content", item.get("text", "")),
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "deepseek-chat"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "content", "timestamp", "model"]}
                )
                conv.messages.append(msg)
        elif isinstance(raw_data, dict):
            messages = raw_data.get("messages", raw_data.get("history", raw_data.get("chat_history", [])))
            conv.title = raw_data.get("title", raw_data.get("topic", "DeepSeek Conversation"))
            conv.created_at = raw_data.get("created_at", raw_data.get("timestamp"))
            for item in messages:
                msg = Message(
                    role=item.get("role", item.get("sender", "unknown")),
                    content=item.get("content", item.get("text", "")),
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "deepseek-chat"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "content", "timestamp", "model"]}
                )
                conv.messages.append(msg)

        if conv.messages:
            conv.title = conv.messages[0].content[:60] + "..." if len(conv.messages[0].content) > 60 else conv.messages[0].content
        return conv


class AIStudioParser(BaseParser):
    """
    Google AI Studio (aistudio.google.com) Parser

    Native Export Formats:
      - Google Drive auto-save: JSON-like files in "AI Studio" folder (no extension, raw API format)
      - "Get code" button: API-ready JSON (cleanest programmatic format)
      - Browser extension Markdown/JSON
      - No native export/download button in UI

    Expected Input: JSON from Drive export or "Get code" feature
    """
    PLATFORM = "aistudio"

    def detect(self, raw_data: Any) -> bool:
        text = str(raw_data)[:500].lower()
        return any(x in text for x in ["ai studio", "aistudio", "gemini-", "google ai studio"])

    def parse(self, raw_data: Any, source_file: str = "") -> Conversation:
        conv = Conversation(
            platform=self.PLATFORM,
            title="AI Studio Conversation",
            source_file=source_file
        )

        if isinstance(raw_data, dict):
            # "Get code" format: {contents: [{role: "user", parts: [{text: "..."}]}, ...]}
            contents = raw_data.get("contents", raw_data.get("messages", []))
            conv.title = raw_data.get("title", raw_data.get("displayName", "AI Studio Conversation"))
            conv.created_at = raw_data.get("createTime", raw_data.get("timestamp"))

            for item in contents:
                role = item.get("role", "unknown")
                # Extract text from parts array
                parts = item.get("parts", [])
                content_text = ""
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict) and "text" in part:
                            content_text += part["text"]
                        elif isinstance(part, str):
                            content_text += part
                elif isinstance(parts, str):
                    content_text = parts
                else:
                    content_text = str(parts)

                # Fallback if no parts structure
                if not content_text and "content" in item:
                    content_text = item["content"]
                if not content_text and "text" in item:
                    content_text = item["text"]

                msg = Message(
                    role=role,
                    content=content_text,
                    timestamp=conv.created_at,
                    model=raw_data.get("model", raw_data.get("modelId", "gemini-pro")),
                    metadata={k: v for k, v in item.items() if k not in ["role", "parts", "content", "text"]}
                )
                conv.messages.append(msg)

        elif isinstance(raw_data, list):
            # Direct array of turns
            for item in raw_data:
                role = item.get("role", "unknown")
                parts = item.get("parts", [])
                content_text = ""
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict) and "text" in part:
                            content_text += part["text"]
                        elif isinstance(part, str):
                            content_text += part
                elif isinstance(parts, str):
                    content_text = parts
                else:
                    content_text = item.get("content", item.get("text", ""))

                msg = Message(
                    role=role,
                    content=content_text,
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "gemini-pro"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "parts", "content", "text", "timestamp", "model"]}
                )
                conv.messages.append(msg)

        if conv.messages:
            conv.title = conv.messages[0].content[:60] + "..." if len(conv.messages[0].content) > 60 else conv.messages[0].content
        return conv


class GeminiParser(BaseParser):
    """
    Gemini (gemini.google.com) Parser

    Native Export Formats:
      - Google Takeout (My Activity -> Gemini Apps): JSON (unreliable, activity-dependent)
      - Per-response export to Google Docs/Sheets (individual responses only)
      - Share links: g.co/gemini/share/... (public URL, needs scraping)
      - Browser extension JSON/Markdown/PDF (recommended for bulk)
      - GDPR request via Google Takeout

    Expected Input: JSON from Takeout or browser extension
    """
    PLATFORM = "gemini"

    def detect(self, raw_data: Any) -> bool:
        text = str(raw_data)[:500].lower()
        return "gemini" in text and ("user" in text or "assistant" in text or "model" in text)

    def parse(self, raw_data: Any, source_file: str = "") -> Conversation:
        conv = Conversation(
            platform=self.PLATFORM,
            title="Gemini Conversation",
            source_file=source_file
        )

        if isinstance(raw_data, dict):
            # Takeout format or extension format
            messages = raw_data.get("messages", raw_data.get("history", []))
            conv.title = raw_data.get("title", raw_data.get("topic", "Gemini Conversation"))
            conv.created_at = raw_data.get("created_at", raw_data.get("timestamp"))

            for item in messages:
                role = item.get("role", item.get("sender", "unknown"))
                # Gemini sometimes uses "user" / "model"
                if role == "model":
                    role = "assistant"

                content = item.get("content", item.get("text", ""))
                # Handle Gemini's multi-part content
                if not content and "parts" in item:
                    parts = item["parts"]
                    if isinstance(parts, list):
                        content = "\n".join(p.get("text", str(p)) for p in parts if isinstance(p, dict))
                    elif isinstance(parts, dict):
                        content = parts.get("text", str(parts))

                msg = Message(
                    role=role,
                    content=content,
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "gemini-1.5-pro"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "content", "text", "timestamp", "model", "parts"]}
                )
                conv.messages.append(msg)

        elif isinstance(raw_data, list):
            for item in raw_data:
                role = item.get("role", item.get("sender", "unknown"))
                if role == "model":
                    role = "assistant"
                content = item.get("content", item.get("text", ""))
                if not content and "parts" in item:
                    parts = item["parts"]
                    if isinstance(parts, list):
                        content = "\n".join(p.get("text", str(p)) for p in parts if isinstance(p, dict))
                msg = Message(
                    role=role,
                    content=content,
                    timestamp=item.get("timestamp"),
                    model=item.get("model", "gemini-1.5-pro"),
                    metadata={k: v for k, v in item.items() if k not in ["role", "content", "text", "timestamp", "model", "parts"]}
                )
                conv.messages.append(msg)

        if conv.messages:
            conv.title = conv.messages[0].content[:60] + "..." if len(conv.messages[0].content) > 60 else conv.messages[0].content
        return conv


class MarkdownParser(BaseParser):
    """
    Generic Markdown parser for manual copy-paste or extension exports.
    Handles common patterns like:
      **User**: ... / **Assistant**: ...
      ### Prompt / ### Response
      > User: ...
    """
    PLATFORM = "markdown_generic"

    def detect(self, raw_data: Any) -> bool:
        if not isinstance(raw_data, str):
            return False
        text = raw_data[:1000].lower()
        patterns = [
            r"\*\*user\*\*", r"\*\*assistant\*\*", r"\*\*you\*\*", r"\*\*ai\*\*",
            r"#\s*prompt", r"#\s*response", r"#\s*user", r"#\s*assistant",
            r">\s*user:", r">\s*assistant:", r"---\n\*\*",
        ]
        return any(re.search(p, text) for p in patterns)

    def parse(self, raw_data: str, source_file: str = "") -> Conversation:
        conv = Conversation(
            platform="unknown",
            title="Parsed Markdown Conversation",
            source_file=source_file
        )

        # Try to detect platform from content
        text_lower = raw_data.lower()
        if "kimi" in text_lower:
            conv.platform = "kimi"
        elif "mistral" in text_lower or "le chat" in text_lower:
            conv.platform = "mistral"
        elif "deepseek" in text_lower:
            conv.platform = "deepseek"
        elif "ai studio" in text_lower or "aistudio" in text_lower:
            conv.platform = "aistudio"
        elif "gemini" in text_lower:
            conv.platform = "gemini"

        # Split by common delimiters
        # Pattern 1: **User**: ...  **Assistant**: ...
        user_pattern = re.compile(r"(?:\*\*|#{1,3}\s*|>\s*)?(?:User|You|Human|Prompt)\s*(?:\*\*|\:|)\s*(.*?)(?=(?:\*\*|#{1,3}\s*|>\s*)?(?:Assistant|AI|Model|Response)\s*(?:\*\*|\:|)|$)", re.IGNORECASE | re.DOTALL)
        assistant_pattern = re.compile(r"(?:\*\*|#{1,3}\s*|>\s*)?(?:Assistant|AI|Model|Response|Kimi|Mistral|DeepSeek|Gemini)\s*(?:\*\*|\:|)\s*(.*?)(?=(?:\*\*|#{1,3}\s*|>\s*)?(?:User|You|Human|Prompt)\s*(?:\*\*|\:|)|$)", re.IGNORECASE | re.DOTALL)

        # Simple line-based heuristic
        lines = raw_data.split("\n")
        current_role = None
        current_content = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Detect role
            is_user = any(line_stripped.lower().startswith(p) for p in [
                "**user", "# user", "# prompt", "> user:", "you:", "human:", "user:"
            ]) or re.match(r"^\*\*User\*\*", line_stripped)
            is_assistant = any(line_stripped.lower().startswith(p) for p in [
                "**assistant", "# assistant", "# response", "> assistant:", 
                "ai:", "assistant:", "model:", "kimi:", "mistral:", "deepseek:", "gemini:"
            ]) or re.match(r"^\*\*Assistant\*\*", line_stripped)

            if is_user or is_assistant:
                if current_role and current_content:
                    conv.messages.append(Message(
                        role=current_role,
                        content="\n".join(current_content).strip()
                    ))
                current_role = "user" if is_user else "assistant"
                current_content = []
                # Remove role prefix from line
                for prefix in ["**User**", "**Assistant**", "# User", "# Assistant", 
                               "# Prompt", "# Response", "> User:", "> Assistant:",
                               "User:", "Assistant:", "AI:", "Model:", "Kimi:", "Mistral:", "DeepSeek:", "Gemini:"]:
                    if line_stripped.startswith(prefix):
                        line = line[len(prefix):].strip()
                        break
                if line:
                    current_content.append(line)
            elif current_role:
                current_content.append(line)

        if current_role and current_content:
            conv.messages.append(Message(
                role=current_role,
                content="\n".join(current_content).strip()
            ))

        if conv.messages:
            conv.title = conv.messages[0].content[:60] + "..." if len(conv.messages[0].content) > 60 else conv.messages[0].content
        return conv


# Registry of all parsers
PARSERS = [
    KimiParser(),
    MistralParser(),
    DeepSeekParser(),
    AIStudioParser(),
    GeminiParser(),
    MarkdownParser(),
]


def auto_detect_parser(raw_data: Any) -> Optional[BaseParser]:
    """Automatically detect the correct parser for raw data."""
    for parser in PARSERS:
        if parser.detect(raw_data):
            return parser
    return None


def parse_file(file_path: str) -> Conversation:
    """Parse a single file and return a Conversation object."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = path.read_text(encoding="utf-8")

    # Try JSON first
    raw_data = None
    try:
        raw_data = json.loads(content)
    except json.JSONDecodeError:
        pass

    # If not JSON, use raw text for markdown parser
    if raw_data is None:
        raw_data = content

    parser = auto_detect_parser(raw_data)
    if parser is None:
        raise ValueError(f"Could not detect parser for file: {file_path}")

    return parser.parse(raw_data, source_file=str(path))


def parse_directory(directory: str, pattern: str = "*") -> List[Conversation]:
    """Parse all matching files in a directory."""
    path = Path(directory)
    conversations = []
    for file_path in path.glob(pattern):
        if file_path.is_file():
            try:
                conv = parse_file(str(file_path))
                conversations.append(conv)
                print(f"[OK] {file_path.name} -> {conv.platform} ({len(conv.messages)} messages)")
            except Exception as e:
                print(f"[ERR] {file_path.name}: {e}")
    return conversations


def export_json(conversations: List[Conversation], output_path: str):
    """Export conversations to standard JSON format."""
    data = [conv.to_dict() for conv in conversations]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Exported JSON: {output_path}")


def export_csv(conversations: List[Conversation], output_path: str):
    """Export conversations to flattened CSV format."""
    rows = []
    for conv in conversations:
        for msg in conv.messages:
            rows.append({
                "conversation_id": conv.conversation_id,
                "platform": conv.platform,
                "title": conv.title,
                "conversation_created": conv.created_at,
                "message_role": msg.role,
                "message_content": msg.content,
                "message_timestamp": msg.timestamp,
                "message_model": msg.model,
                "source_file": conv.source_file
            })

    if not rows:
        print("No data to export to CSV.")
        return

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported CSV: {output_path}")


def export_markdown_layout(conversations: List[Conversation], output_dir: str):
    """
    Export each conversation to a structured Markdown layout file.
    Separates prompts (user) and responses (assistant) into distinct sections.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for conv in conversations:
        safe_title = re.sub(r"[^\w\s-]", "", conv.title)[:50].strip().replace(" ", "_")
        filename = f"{conv.platform}_{safe_title}_{conv.conversation_id[:8]}.md"
        filepath = out_path / filename

        lines = [
            f"# {conv.title}",
            f"",
            f"**Platform:** {conv.platform}  ",
            f"**Conversation ID:** {conv.conversation_id}  ",
            f"**Created:** {conv.created_at or 'Unknown'}  ",
            f"**Source:** {conv.source_file or 'Unknown'}  ",
            f"**Messages:** {len(conv.messages)}  ",
            f"",
            "---",
            f"",
        ]

        turn_number = 1
        for i, msg in enumerate(conv.messages):
            if msg.role == "user":
                lines.append(f"## Prompt {turn_number}")
                lines.append(f"**User** | {msg.timestamp or 'Unknown timestamp'}")
                if msg.model:
                    lines.append(f"*(Model context: {msg.model})*")
                lines.append(f"")
                lines.append(f"```")
                lines.append(msg.content)
                lines.append(f"```")
                lines.append(f"")
            elif msg.role == "assistant":
                lines.append(f"## Response {turn_number}")
                lines.append(f"**Assistant ({msg.model or 'AI'})** | {msg.timestamp or 'Unknown timestamp'}")
                lines.append(f"")
                lines.append(f"```")
                lines.append(msg.content)
                lines.append(f"```")
                lines.append(f"")
                turn_number += 1
            else:
                lines.append(f"## Message {i+1} ({msg.role})")
                lines.append(f"**{msg.role}** | {msg.timestamp or 'Unknown'}")
                lines.append(f"")
                lines.append(f"```")
                lines.append(msg.content)
                lines.append(f"```")
                lines.append(f"")

        lines.append("---")
        lines.append(f"")
        lines.append(f"*End of conversation. Exported by ACUP v1.0.0*")

        filepath.write_text("\n".join(lines), encoding="utf-8")
        print(f"Exported Markdown: {filepath}")


def generate_stats(conversations: List[Conversation]) -> Dict[str, Any]:
    """Generate aggregate statistics across all conversations."""
    stats = {
        "total_conversations": len(conversations),
        "total_messages": sum(len(c.messages) for c in conversations),
        "total_words": sum(sum(len(m.content.split()) for m in c.messages) for c in conversations),
        "platforms": {},
        "date_range": {"earliest": None, "latest": None}
    }

    for conv in conversations:
        plat = conv.platform
        if plat not in stats["platforms"]:
            stats["platforms"][plat] = {
                "conversations": 0,
                "messages": 0,
                "words": 0,
                "user_messages": 0,
                "assistant_messages": 0
            }
        p = stats["platforms"][plat]
        p["conversations"] += 1
        p["messages"] += len(conv.messages)
        p["words"] += sum(len(m.content.split()) for m in conv.messages)
        p["user_messages"] += sum(1 for m in conv.messages if m.role == "user")
        p["assistant_messages"] += sum(1 for m in conv.messages if m.role == "assistant")

    return stats


def main():
    parser = argparse.ArgumentParser(description="AI Chat Universal Parser (ACUP)")
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("--pattern", default="*.json", help="File pattern for directory input")
    parser.add_argument("--json-out", default="conversations.json", help="JSON output path")
    parser.add_argument("--csv-out", default="conversations.csv", help="CSV output path")
    parser.add_argument("--md-out", default="./markdown_layouts", help="Markdown layout output directory")
    parser.add_argument("--stats-out", default="stats.json", help="Statistics JSON output")
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_dir():
        conversations = parse_directory(args.input, args.pattern)
    else:
        conversations = [parse_file(args.input)]

    if not conversations:
        print("No conversations parsed. Exiting.")
        return

    export_json(conversations, args.json_out)
    export_csv(conversations, args.csv_out)
    export_markdown_layout(conversations, args.md_out)

    stats = generate_stats(conversations)
    with open(args.stats_out, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"Exported stats: {args.stats_out}")

    print(f"\nSummary: {len(conversations)} conversations, {stats['total_messages']} messages, {stats['total_words']} words")


if __name__ == "__main__":
    main()
