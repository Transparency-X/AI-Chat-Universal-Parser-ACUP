#!/usr/bin/env python3
"""
AI Chat Universal Parser — Browser Scraper v1.1
Production-grade Playwright scraper for platforms without native export APIs.

Platforms:
  - kimi.com / kimi.ai
  - chat.mistral.ai
  - chat.deepseek.com
  - aistudio.google.com
  - gemini.google.com

Forensic Features:
  - SHA-256 content hashing per message
  - Timestamped screenshot capture
  - Session persistence (cookies/localStorage)
  - Incremental virtual-scroll capture
  - Chain-of-custody logging

Dependencies:
  pip install playwright
  playwright install chromium

Author: AI Assistant
Version: 1.1.0
"""

import asyncio
import json
import hashlib
import base64
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from abc import ABC, abstractmethod

try:
    from playwright.async_api import async_playwright, Page, BrowserContext, expect
except ImportError:
    raise ImportError(
        "Playwright not installed. Run:
"
        "  pip install playwright
"
        "  playwright install chromium"
    )


# ─────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────

@dataclass
class ScrapedMessage:
    role: str                      # "user" | "assistant" | "system"
    content: str
    timestamp: Optional[str] = None
    model: Optional[str] = None
    element_hash: Optional[str] = None   # SHA-256 of raw innerHTML
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "model": self.model,
            "element_hash": self.element_hash,
            "metadata": self.metadata
        }


@dataclass
class ScrapedConversation:
    platform: str
    title: str
    url: str
    scraped_at: str
    messages: List[ScrapedMessage] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "title": self.title,
            "url": self.url,
            "scraped_at": self.scraped_at,
            "message_count": len(self.messages),
            "user_message_count": sum(1 for m in self.messages if m.role == "user"),
            "assistant_message_count": sum(1 for m in self.messages if m.role == "assistant"),
            "word_count": sum(len(m.content.split()) for m in self.messages),
            "messages": [m.to_dict() for m in self.messages],
            "screenshots": self.screenshots,
            "metadata": self.metadata,
            "log": self.log
        }


# ─────────────────────────────────────────────────────────────
# BASE SCRAPER
# ─────────────────────────────────────────────────────────────

class BaseScraper(ABC):
    PLATFORM: str = "unknown"
    BASE_URL: str = ""
    DEFAULT_SELECTORS: Dict[str, str] = {}

    def __init__(self, page: Page, config: Dict[str, Any], output_dir: Path):
        self.page = page
        self.config = config
        self.output_dir = output_dir
        self.selectors = {**self.DEFAULT_SELECTORS, **config.get("selectors", {})}
        self.log_entries: List[str] = []
        self.screenshots: List[str] = []
        self._msg_dedup: set = set()  # content hashes for deduplication

    async def _log(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        entry = f"[{ts}] {self.PLATFORM}: {msg}"
        self.log_entries.append(entry)
        print(entry)

    async def _screenshot(self, name: str) -> str:
        """Capture forensic screenshot. Returns file path."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        fname = f"{self.PLATFORM}_{name}_{ts}.png"
        path = self.output_dir / "screenshots" / fname
        path.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(path), full_page=("full" in name))
        self.screenshots.append(str(path))
        await self._log(f"Screenshot saved: {path}")
        return str(path)

    def _hash_content(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    async def _safe_query(self, selector: str, timeout: int = 5000) -> Optional[Any]:
        try:
            await expect(self.page.locator(selector).first).to_be_visible(timeout=timeout)
            return self.page.locator(selector)
        except Exception:
            return None

    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        """Override if platform requires explicit login flow."""
        await self._log("Login not required or using existing session.")
        return True

    @abstractmethod
    async def get_conversation_urls(self) -> List[str]:
        """Return list of conversation URLs to scrape."""
        pass

    @abstractmethod
    async def scrape_conversation(self, url: str) -> ScrapedConversation:
        """Scrape a single conversation and return structured data."""
        pass

    async def _scroll_virtual_list(
        self,
        container_selector: str,
        item_selector: str,
        extract_fn,
        max_scrolls: int = 200,
        scroll_step: int = 800
    ) -> List[Dict[str, Any]]:
        """
        Generic virtual-scroll capture.
        Scrolls to top, then increments down, extracting items via extract_fn.
        Deduplicates by content hash.
        """
        await self._log(f"Starting virtual scroll capture: {container_selector}")
        container = await self._safe_query(container_selector, timeout=10000)
        if not container:
            await self._log(f"ERROR: Container not found: {container_selector}")
            return []

        # Scroll to absolute top
        await self.page.evaluate(f"""
            const el = document.querySelector('{container_selector}');
            if (el) el.scrollTop = 0;
        """)
        await asyncio.sleep(0.5)

        captured = []
        last_height = -1
        stable_count = 0

        for i in range(max_scrolls):
            # Extract current viewport items
            items = await self.page.locator(item_selector).all()
            for item in items:
                try:
                    data = await extract_fn(item)
                    if data and data.get("content"):
                        h = self._hash_content(data["content"])
                        if h not in self._msg_dedup:
                            self._msg_dedup.add(h)
                            data["_hash"] = h
                            captured.append(data)
                except Exception as e:
                    await self._log(f"Extract error: {e}")

            # Scroll down
            await self.page.evaluate(f"""
                const el = document.querySelector('{container_selector}');
                if (el) el.scrollTop += {scroll_step};
            """)
            await asyncio.sleep(0.3)

            # Check for end of list
            height = await self.page.evaluate(f"""
                const el = document.querySelector('{container_selector}');
                return el ? el.scrollHeight : 0;
            """)
            scroll_top = await self.page.evaluate(f"""
                const el = document.querySelector('{container_selector}');
                return el ? el.scrollTop : 0;
            """)

            if height == last_height:
                stable_count += 1
                if stable_count >= 3:
                    await self._log("End of scroll detected.")
                    break
            else:
                stable_count = 0
            last_height = height

            if i % 20 == 0:
                await self._log(f"Scroll progress: {len(captured)} items, scrollTop={scroll_top}")

        await self._log(f"Virtual scroll complete: {len(captured)} unique items captured.")
        return captured

    async def run(self, credentials: Optional[Dict] = None, max_conversations: Optional[int] = None) -> List[ScrapedConversation]:
        await self._log("Starting scraper run.")
        await self.login(credentials)
        urls = await self.get_conversation_urls()
        await self._log(f"Discovered {len(urls)} conversations.")

        if max_conversations:
            urls = urls[:max_conversations]

        results = []
        for idx, url in enumerate(urls, 1):
            await self._log(f"[{idx}/{len(urls)}] Scraping: {url}")
            try:
                conv = await self.scrape_conversation(url)
                conv.log = self.log_entries.copy()
                conv.screenshots = self.screenshots.copy()
                results.append(conv)
                # Reset per-conversation state
                self._msg_dedup.clear()
                self.screenshots = []
            except Exception as e:
                await self._log(f"FAILED to scrape {url}: {e}")
                # Capture error screenshot
                try:
                    await self._screenshot(f"error_{idx}")
                except Exception:
                    pass

        await self._log(f"Run complete: {len(results)}/{len(urls)} conversations scraped.")
        return results


# ─────────────────────────────────────────────────────────────
# KIMI SCRAPER
# ─────────────────────────────────────────────────────────────

class KimiScraper(BaseScraper):
    PLATFORM = "kimi"
    BASE_URL = "https://kimi.com"
    DEFAULT_SELECTORS = {
        "sidebar": "aside, [class*='sidebar'], nav",
        "conversation_item": "[class*='conversation-item'], [class*='chat-item'], [class*='history-item']",
        "conversation_link": "a",
        "chat_container": "main, [class*='chat-content'], [class*='message-list']",
        "message_turn": "[class*='message'], [class*='chat-turn']",
        "user_indicator": "[class*='user'], [class*='right'], [class*='own']",
        "assistant_indicator": "[class*='assistant'], [class*='left'], [class*='ai'], [class*='kimi']",
        "message_content": "[class*='content'], [class*='text'], [class*='bubble']",
        "code_block": "pre code",
        "timestamp": "[class*='time'], [class*='date']",
        "model_label": "[class*='model'], [class*='version']"
    }

    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        await self.page.goto(self.BASE_URL, wait_until="networkidle")
        await self._screenshot("kimi_landing")
        # Check if already logged in (sidebar visible)
        sidebar = await self._safe_query(self.selectors["sidebar"], timeout=3000)
        if sidebar:
            await self._log("Already logged in (sidebar detected).")
            return True
        # If not, user must manually log in or provide credentials
        await self._log("Login required. Please complete login in the browser window.")
        await self.page.wait_for_selector(self.selectors["sidebar"], timeout=120000)
        await self._screenshot("kimi_logged_in")
        return True

    async def get_conversation_urls(self) -> List[str]:
        await self.page.goto(f"{self.BASE_URL}/chat", wait_until="networkidle")
        await asyncio.sleep(1.5)
        items = await self.page.locator(self.selectors["conversation_item"]).all()
        urls = []
        for item in items[:50]:  # Limit to recent 50
            try:
                link = item.locator(self.selectors["conversation_link"]).first
                href = await link.get_attribute("href")
                if href:
                    url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    urls.append(url)
            except Exception:
                continue
        await self._log(f"Found {len(urls)} conversation URLs.")
        return urls

    async def scrape_conversation(self, url: str) -> ScrapedConversation:
        await self.page.goto(url, wait_until="networkidle")
        await asyncio.sleep(1.5)
        await self._screenshot("kimi_convo_start")

        conv = ScrapedConversation(
            platform=self.PLATFORM,
            title="",
            url=url,
            scraped_at=datetime.now(timezone.utc).isoformat()
        )

        # Extract title from first user message or page title
        title = await self.page.title()
        conv.title = title.replace(" - Kimi", "").replace("Kimi", "").strip() or "Kimi Conversation"

        # Extract model info if visible
        model_text = ""
        model_el = await self._safe_query(self.selectors["model_label"], timeout=2000)
        if model_el:
            model_text = await model_el.first.inner_text() or ""

        async def extract_message(element) -> Optional[Dict[str, Any]]:
            html = await element.inner_html()
            text = await element.inner_text()
            if not text or len(text.strip()) < 2:
                return None
            # Determine role by class or position
            class_attr = await element.get_attribute("class") or ""
            is_user = any(k in class_attr.lower() for k in ["user", "right", "own", "human"])
            is_assistant = any(k in class_attr.lower() for k in ["assistant", "left", "ai", "kimi", "bot"])
            role = "user" if is_user else ("assistant" if is_assistant else "unknown")
            # Extract code blocks properly
            code_blocks = await element.locator(self.selectors["code_block"]).all_inner_texts()
            content = text
            if code_blocks:
                content = text  # Keep text; code is inside
            return {"role": role, "content": content, "html": html, "model": model_text}

        items = await self._scroll_virtual_list(
            container_selector=self.selectors["chat_container"],
            item_selector=self.selectors["message_turn"],
            extract_fn=extract_message,
            max_scrolls=150,
            scroll_step=600
        )

        for item in items:
            msg = ScrapedMessage(
                role=item["role"],
                content=item["content"],
                model=item.get("model") or "kimi-latest",
                element_hash=self._hash_content(item.get("html", ""))
            )
            conv.messages.append(msg)

        if conv.messages and not conv.title:
            conv.title = conv.messages[0].content[:60] + "..."
        await self._screenshot("kimi_convo_end_full", )
        return conv


# ─────────────────────────────────────────────────────────────
# MISTRAL SCRAPER
# ─────────────────────────────────────────────────────────────

class MistralScraper(BaseScraper):
    PLATFORM = "mistral"
    BASE_URL = "https://chat.mistral.ai"
    DEFAULT_SELECTORS = {
        "sidebar": "[class*='sidebar'], nav, aside",
        "conversation_item": "[class*='conversation'], [class*='chat-item'], [class*='thread']",
        "conversation_link": "a",
        "chat_container": "[class*='chat-content'], [class*='messages'], main",
        "message_turn": "[class*='message']",
        "user_indicator": "[class*='user'], [class*='human'], [class*='right']",
        "assistant_indicator": "[class*='assistant'], [class*='ai'], [class*='mistral'], [class*='left']",
        "message_content": "[class*='content'], [class*='text'], [class*='bubble']",
        "code_block": "pre code",
        "timestamp": "[class*='time']",
        "model_label": "[class*='model']"
    }

    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        await self.page.goto(self.BASE_URL, wait_until="networkidle")
        await self._screenshot("mistral_landing")
        sidebar = await self._safe_query(self.selectors["sidebar"], timeout=5000)
        if sidebar:
            await self._log("Already logged in.")
            return True
        await self._log("Please complete Mistral login in browser (OAuth/Google).")
        await self.page.wait_for_selector(self.selectors["sidebar"], timeout=120000)
        await self._screenshot("mistral_logged_in")
        return True

    async def get_conversation_urls(self) -> List[str]:
        await self.page.goto(self.BASE_URL, wait_until="networkidle")
        await asyncio.sleep(1.5)
        items = await self.page.locator(self.selectors["conversation_item"]).all()
        urls = []
        for item in items[:50]:
            try:
                href = await item.locator(self.selectors["conversation_link"]).first.get_attribute("href")
                if href:
                    url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    urls.append(url)
            except Exception:
                continue
        return urls

    async def scrape_conversation(self, url: str) -> ScrapedConversation:
        await self.page.goto(url, wait_until="networkidle")
        await asyncio.sleep(1.5)
        await self._screenshot("mistral_convo_start")

        conv = ScrapedConversation(
            platform=self.PLATFORM,
            title="",
            url=url,
            scraped_at=datetime.now(timezone.utc).isoformat()
        )
        title = await self.page.title()
        conv.title = title.replace(" - Le Chat", "").replace("Mistral", "").strip() or "Mistral Conversation"

        model_text = ""
        model_el = await self._safe_query(self.selectors["model_label"], timeout=2000)
        if model_el:
            model_text = await model_el.first.inner_text() or ""

        async def extract_message(element) -> Optional[Dict[str, Any]]:
            text = await element.inner_text()
            if not text or len(text.strip()) < 2:
                return None
            html = await element.inner_html()
            class_attr = await element.get_attribute("class") or ""
            is_user = any(k in class_attr.lower() for k in ["user", "human", "right", "own"])
            is_assistant = any(k in class_attr.lower() for k in ["assistant", "ai", "mistral", "left", "bot"])
            role = "user" if is_user else ("assistant" if is_assistant else "unknown")
            return {"role": role, "content": text, "html": html, "model": model_text or "mistral-large"}

        items = await self._scroll_virtual_list(
            container_selector=self.selectors["chat_container"],
            item_selector=self.selectors["message_turn"],
            extract_fn=extract_message,
            max_scrolls=150,
            scroll_step=600
        )

        for item in items:
            conv.messages.append(ScrapedMessage(
                role=item["role"],
                content=item["content"],
                model=item.get("model") or "mistral-large",
                element_hash=self._hash_content(item.get("html", ""))
            ))

        if conv.messages and not conv.title:
            conv.title = conv.messages[0].content[:60] + "..."
        return conv


# ─────────────────────────────────────────────────────────────
# DEEPSEEK SCRAPER
# ─────────────────────────────────────────────────────────────

class DeepSeekScraper(BaseScraper):
    PLATFORM = "deepseek"
    BASE_URL = "https://chat.deepseek.com"
    DEFAULT_SELECTORS = {
        "sidebar": "[class*='sidebar'], [class*='history'], nav",
        "conversation_item": "[class*='conversation'], [class*='session'], [class*='chat-item']",
        "conversation_link": "a, [class*='item']",
        "chat_container": "[class*='chat-content'], [class*='messages'], [class*='chat-layout']",
        "message_turn": "[class*='message'], [class*='turn']",
        "user_indicator": "[class*='user'], [class*='right'], [class*='human']",
        "assistant_indicator": "[class*='assistant'], [class*='left'], [class*='deepseek'], [class*='ai']",
        "message_content": "[class*='content'], [class*='text'], [class*='bubble'], [class*='markdown']",
        "code_block": "pre code",
        "timestamp": "[class*='time']",
        "model_label": "[class*='model']"
    }

    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        await self.page.goto(self.BASE_URL, wait_until="networkidle")
        await self._screenshot("deepseek_landing")
        # DeepSeek uses email/phone + code or password
        sidebar = await self._safe_query(self.selectors["sidebar"], timeout=5000)
        if sidebar:
            await self._log("Already logged in.")
            return True
        if credentials and credentials.get("email"):
            await self._log("Attempting credential login...")
            # Fill login form if present
            email_input = await self._safe_query("input[type='email'], input[placeholder*='email']", timeout=3000)
            if email_input:
                await email_input.first.fill(credentials["email"])
                if credentials.get("password"):
                    pwd_input = await self._safe_query("input[type='password']", timeout=3000)
                    if pwd_input:
                        await pwd_input.first.fill(credentials["password"])
                        await self.page.keyboard.press("Enter")
                else:
                    # OTP flow — wait for user
                    await self._log("OTP/verification code sent. Enter it in browser.")
                    await self.page.wait_for_selector(self.selectors["sidebar"], timeout=120000)
        else:
            await self._log("Please complete DeepSeek login in browser.")
            await self.page.wait_for_selector(self.selectors["sidebar"], timeout=120000)
        await self._screenshot("deepseek_logged_in")
        return True

    async def get_conversation_urls(self) -> List[str]:
        await self.page.goto(self.BASE_URL, wait_until="networkidle")
        await asyncio.sleep(1.5)
        items = await self.page.locator(self.selectors["conversation_item"]).all()
        urls = []
        for item in items[:50]:
            try:
                href = await item.get_attribute("href") or await item.locator("a").first.get_attribute("href")
                if href:
                    url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    urls.append(url)
            except Exception:
                continue
        return urls

    async def scrape_conversation(self, url: str) -> ScrapedConversation:
        await self.page.goto(url, wait_until="networkidle")
        await asyncio.sleep(1.5)
        await self._screenshot("deepseek_convo_start")

        conv = ScrapedConversation(
            platform=self.PLATFORM,
            title="",
            url=url,
            scraped_at=datetime.now(timezone.utc).isoformat()
        )
        title = await self.page.title()
        conv.title = title.replace(" - DeepSeek", "").replace("DeepSeek", "").strip() or "DeepSeek Conversation"

        model_text = ""
        model_el = await self._safe_query(self.selectors["model_label"], timeout=2000)
        if model_el:
            model_text = await model_el.first.inner_text() or ""

        async def extract_message(element) -> Optional[Dict[str, Any]]:
            text = await element.inner_text()
            if not text or len(text.strip()) < 2:
                return None
            html = await element.inner_html()
            class_attr = await element.get_attribute("class") or ""
            is_user = any(k in class_attr.lower() for k in ["user", "human", "right", "own"])
            is_assistant = any(k in class_attr.lower() for k in ["assistant", "ai", "deepseek", "left", "bot"])
            role = "user" if is_user else ("assistant" if is_assistant else "unknown")
            return {"role": role, "content": text, "html": html, "model": model_text or "deepseek-chat"}

        items = await self._scroll_virtual_list(
            container_selector=self.selectors["chat_container"],
            item_selector=self.selectors["message_turn"],
            extract_fn=extract_message,
            max_scrolls=150,
            scroll_step=600
        )

        for item in items:
            conv.messages.append(ScrapedMessage(
                role=item["role"],
                content=item["content"],
                model=item.get("model") or "deepseek-chat",
                element_hash=self._hash_content(item.get("html", ""))
            ))

        if conv.messages and not conv.title:
            conv.title = conv.messages[0].content[:60] + "..."
        return conv


# ─────────────────────────────────────────────────────────────
# GOOGLE AI STUDIO SCRAPER
# ─────────────────────────────────────────────────────────────

class AIStudioScraper(BaseScraper):
    PLATFORM = "aistudio"
    BASE_URL = "https://aistudio.google.com"
    DEFAULT_SELECTORS = {
        "chat_list": "[class*='chat-list'], [class*='history'], [class*='conversation-list']",
        "conversation_item": "[class*='chat-item'], [class*='conversation'], [role='listitem']",
        "conversation_link": "a",
        "chat_container": "[class*='chat-panel'], [class*='messages'], [class*='scroll-container']",
        "message_turn": "[class*='message'], [class*='turn']",
        "user_indicator": "[class*='user'], [class*='human']",
        "assistant_indicator": "[class*='model'], [class*='assistant'], [class*='gemini']",
        "message_content": "[class*='content'], [class*='text'], [class*='bubble']",
        "code_block": "pre code",
        "timestamp": "[class*='time']",
        "model_label": "[class*='model']"
    }

    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        await self.page.goto(self.BASE_URL, wait_until="networkidle")
        await self._screenshot("aistudio_landing")
        # AI Studio uses Google SSO
        chat_list = await self._safe_query(self.selectors["chat_list"], timeout=5000)
        if chat_list:
            await self._log("Already logged in (Google session).")
            return True
        await self._log("Please complete Google login in browser.")
        await self.page.wait_for_selector(self.selectors["chat_list"], timeout=120000)
        await self._screenshot("aistudio_logged_in")
        return True

    async def get_conversation_urls(self) -> List[str]:
        await self.page.goto(f"{self.BASE_URL}/chat", wait_until="networkidle")
        await asyncio.sleep(2)
        items = await self.page.locator(self.selectors["conversation_item"]).all()
        urls = []
        for item in items[:50]:
            try:
                href = await item.locator(self.selectors["conversation_link"]).first.get_attribute("href")
                if href:
                    url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    urls.append(url)
            except Exception:
                continue
        return urls

    async def scrape_conversation(self, url: str) -> ScrapedConversation:
        await self.page.goto(url, wait_until="networkidle")
        await asyncio.sleep(2)
        await self._screenshot("aistudio_convo_start")

        conv = ScrapedConversation(
            platform=self.PLATFORM,
            title="",
            url=url,
            scraped_at=datetime.now(timezone.utc).isoformat()
        )
        title = await self.page.title()
        conv.title = title.replace(" - AI Studio", "").replace("Google AI Studio", "").strip() or "AI Studio Conversation"

        model_text = ""
        model_el = await self._safe_query(self.selectors["model_label"], timeout=2000)
        if model_el:
            model_text = await model_el.first.inner_text() or ""

        async def extract_message(element) -> Optional[Dict[str, Any]]:
            text = await element.inner_text()
            if not text or len(text.strip()) < 2:
                return None
            html = await element.inner_html()
            class_attr = await element.get_attribute("class") or ""
            # AI Studio uses "user" and "model" roles
            is_user = any(k in class_attr.lower() for k in ["user", "human"])
            is_model = any(k in class_attr.lower() for k in ["model", "gemini", "assistant"])
            role = "user" if is_user else ("assistant" if is_model else "unknown")
            return {"role": role, "content": text, "html": html, "model": model_text or "gemini-pro"}

        items = await self._scroll_virtual_list(
            container_selector=self.selectors["chat_container"],
            item_selector=self.selectors["message_turn"],
            extract_fn=extract_message,
            max_scrolls=200,  # AI Studio virtual scroll is aggressive
            scroll_step=500
        )

        for item in items:
            conv.messages.append(ScrapedMessage(
                role=item["role"],
                content=item["content"],
                model=item.get("model") or "gemini-pro",
                element_hash=self._hash_content(item.get("html", ""))
            ))

        if conv.messages and not conv.title:
            conv.title = conv.messages[0].content[:60] + "..."
        return conv


# ─────────────────────────────────────────────────────────────
# GEMINI SCRAPER
# ─────────────────────────────────────────────────────────────

class GeminiScraper(BaseScraper):
    PLATFORM = "gemini"
    BASE_URL = "https://gemini.google.com"
    DEFAULT_SELECTORS = {
        "chat_list": "[class*='chat-list'], [class*='history'], nav",
        "conversation_item": "[class*='conversation'], [class*='chat-item'], [class*='thread']",
        "conversation_link": "a",
        "chat_container": "[class*='chat-content'], [class*='messages'], [class*='scroll-viewport']",
        "message_turn": "[class*='message'], [class*='turn']",
        "user_indicator": "[class*='user'], [class*='human']",
        "assistant_indicator": "[class*='model'], [class*='gemini'], [class*='assistant']",
        "message_content": "[class*='content'], [class*='text'], [class*='bubble']",
        "code_block": "pre code",
        "timestamp": "[class*='time']",
        "model_label": "[class*='model']"
    }

    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        await self.page.goto(self.BASE_URL, wait_until="networkidle")
        await self._screenshot("gemini_landing")
        chat_list = await self._safe_query(self.selectors["chat_list"], timeout=5000)
        if chat_list:
            await self._log("Already logged in (Google session).")
            return True
        await self._log("Please complete Google login in browser.")
        await self.page.wait_for_selector(self.selectors["chat_list"], timeout=120000)
        await self._screenshot("gemini_logged_in")
        return True

    async def get_conversation_urls(self) -> List[str]:
        await self.page.goto(f"{self.BASE_URL}/app", wait_until="networkidle")
        await asyncio.sleep(2)
        items = await self.page.locator(self.selectors["conversation_item"]).all()
        urls = []
        for item in items[:50]:
            try:
                href = await item.locator(self.selectors["conversation_link"]).first.get_attribute("href")
                if href:
                    url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    urls.append(url)
            except Exception:
                continue
        return urls

    async def scrape_conversation(self, url: str) -> ScrapedConversation:
        await self.page.goto(url, wait_until="networkidle")
        await asyncio.sleep(2)
        await self._screenshot("gemini_convo_start")

        conv = ScrapedConversation(
            platform=self.PLATFORM,
            title="",
            url=url,
            scraped_at=datetime.now(timezone.utc).isoformat()
        )
        title = await self.page.title()
        conv.title = title.replace(" - Gemini", "").replace("Gemini", "").strip() or "Gemini Conversation"

        model_text = ""
        model_el = await self._safe_query(self.selectors["model_label"], timeout=2000)
        if model_el:
            model_text = await model_el.first.inner_text() or ""

        async def extract_message(element) -> Optional[Dict[str, Any]]:
            text = await element.inner_text()
            if not text or len(text.strip()) < 2:
                return None
            html = await element.inner_html()
            class_attr = await element.get_attribute("class") or ""
            is_user = any(k in class_attr.lower() for k in ["user", "human"])
            is_model = any(k in class_attr.lower() for k in ["model", "gemini", "assistant"])
            role = "user" if is_user else ("assistant" if is_model else "unknown")
            return {"role": role, "content": text, "html": html, "model": model_text or "gemini-1.5-pro"}

        items = await self._scroll_virtual_list(
            container_selector=self.selectors["chat_container"],
            item_selector=self.selectors["message_turn"],
            extract_fn=extract_message,
            max_scrolls=200,
            scroll_step=500
        )

        for item in items:
            conv.messages.append(ScrapedMessage(
                role=item["role"],
                content=item["content"],
                model=item.get("model") or "gemini-1.5-pro",
                element_hash=self._hash_content(item.get("html", ""))
            ))

        if conv.messages and not conv.title:
            conv.title = conv.messages[0].content[:60] + "..."
        return conv


# ─────────────────────────────────────────────────────────────
# SCRAPER REGISTRY & RUNNER
# ─────────────────────────────────────────────────────────────

SCRAPER_MAP = {
    "kimi": KimiScraper,
    "mistral": MistralScraper,
    "deepseek": DeepSeekScraper,
    "aistudio": AIStudioScraper,
    "gemini": GeminiScraper,
}


class ScraperRunner:
    def __init__(
        self,
        platforms: List[str],
        output_dir: str = "./scraped",
        headless: bool = False,
        credentials: Optional[Dict[str, Dict[str, str]]] = None,
        max_conversations: Optional[int] = None,
        session_file: Optional[str] = None
    ):
        self.platforms = platforms
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.credentials = credentials or {}
        self.max_conversations = max_conversations
        self.session_file = Path(session_file) if session_file else self.output_dir / "session.json"
        self.all_results: List[ScrapedConversation] = []

    async def _save_session(self, context: BrowserContext) -> None:
        cookies = await context.cookies()
        storage = await context.storage_state()
        state = {
            "cookies": cookies,
            "storage": storage,
            "saved_at": datetime.now(timezone.utc).isoformat()
        }
        self.session_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"[SESSION] Saved to {self.session_file}")

    async def _load_session(self, context: BrowserContext) -> None:
        if self.session_file.exists():
            try:
                state = json.loads(self.session_file.read_text(encoding="utf-8"))
                await context.add_cookies(state.get("cookies", []))
                print(f"[SESSION] Loaded from {self.session_file}")
            except Exception as e:
                print(f"[SESSION] Load failed: {e}")

    async def run(self) -> List[ScrapedConversation]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            await self._load_session(context)

            for platform in self.platforms:
                scraper_cls = SCRAPER_MAP.get(platform)
                if not scraper_cls:
                    print(f"[WARN] Unknown platform: {platform}. Skipping.")
                    continue

                page = await context.new_page()
                config = self.credentials.get(platform, {})
                scraper = scraper_cls(page, config, self.output_dir)

                try:
                    results = await scraper.run(
                        credentials=config,
                        max_conversations=self.max_conversations
                    )
                    self.all_results.extend(results)
                except Exception as e:
                    print(f"[ERROR] Platform {platform} failed: {e}")
                finally:
                    await page.close()

            await self._save_session(context)
            await browser.close()

        # Save combined output
        await self._export()
        return self.all_results

    async def _export(self) -> None:
        # Save raw scraped JSON
        raw_path = self.output_dir / "scraped_raw.json"
        raw_path.write_text(
            json.dumps([r.to_dict() for r in self.all_results], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"[EXPORT] Raw scraped data: {raw_path}")

        # Save v1.0-compatible JSON for parser pipeline
        compatible = []
        for r in self.all_results:
            compatible.append({
                "conversation_id": hashlib.sha256(f"{r.platform}:{r.title}:{r.url}".encode()).hexdigest()[:16],
                "platform": r.platform,
                "title": r.title,
                "created_at": r.scraped_at,
                "message_count": len(r.messages),
                "user_message_count": sum(1 for m in r.messages if m.role == "user"),
                "assistant_message_count": sum(1 for m in r.messages if m.role == "assistant"),
                "word_count": sum(len(m.content.split()) for m in r.messages),
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp or r.scraped_at,
                        "model": m.model or "unknown",
                        "metadata": {**m.metadata, "element_hash": m.element_hash}
                    }
                    for m in r.messages
                ],
                "metadata": {
                    "scraped": True,
                    "source_url": r.url,
                    "screenshots": r.screenshots,
                    "scraper_log": r.log
                },
                "source_file": f"browser_scrape_{r.platform}_{r.scraped_at}"
            })

        compat_path = self.output_dir / "conversations_scraped.json"
        compat_path.write_text(json.dumps(compatible, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[EXPORT] v1.0-compatible JSON: {compat_path}")
        print(f"[EXPORT] Total conversations: {len(compatible)}")


# ─────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ACUP Browser Scraper v1.1")
    parser.add_argument("--platforms", nargs="+", required=True,
                        choices=["kimi", "mistral", "deepseek", "aistudio", "gemini", "all"],
                        help="Platforms to scrape")
    parser.add_argument("--output", default="./scraped", help="Output directory")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (may trigger bot detection)")
    parser.add_argument("--max-conversations", type=int, default=None, help="Limit per platform")
    parser.add_argument("--session", default=None, help="Path to session JSON file")
    parser.add_argument("--credentials", default=None, help="JSON file with credentials per platform")
    args = parser.parse_args()

    platforms = list(SCRAPER_MAP.keys()) if "all" in args.platforms else args.platforms

    credentials = {}
    if args.credentials:
        credentials = json.loads(Path(args.credentials).read_text(encoding="utf-8"))

    runner = ScraperRunner(
        platforms=platforms,
        output_dir=args.output,
        headless=args.headless,
        credentials=credentials,
        max_conversations=args.max_conversations,
        session_file=args.session
    )

    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
