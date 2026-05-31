#!/usr/bin/env python3
"""
ACUP v1.1 — Browser Scraper Runner
Simplified wrapper with automatic v1.0 parser pipeline integration.

Usage:
  # Scrape Kimi and Gemini (interactive login)
  python run_scraper.py --platforms kimi gemini

  # Scrape all platforms headless with credentials
  python run_scraper.py --platforms all --headless --credentials creds.json

  # Limit to 10 conversations per platform, then auto-parse to CSV/Markdown
  python run_scraper.py --platforms deepseek mistral --max 10 --parse
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from browser_scraper import ScraperRunner, SCRAPER_MAP


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ACUP v1.1 Browser Scraper + Parser Pipeline")
    parser.add_argument("--platforms", nargs="+", required=True,
                        choices=["kimi", "mistral", "deepseek", "aistudio", "gemini", "all"],
                        help="Platforms to scrape")
    parser.add_argument("--output", default="./scraped", help="Scraper output directory")
    parser.add_argument("--headless", action="store_true",
                        help="Headless mode (may trigger bot detection on some platforms)")
    parser.add_argument("--max", type=int, dest="max_conversations", default=None,
                        help="Max conversations per platform")
    parser.add_argument("--session", default=None,
                        help="Path to session JSON for cookie persistence")
    parser.add_argument("--credentials", default=None,
                        help="JSON file with credentials per platform")
    parser.add_argument("--parse", action="store_true",
                        help="Auto-run v1.0 parser on scraped output to generate CSV/Markdown/Dashboard")
    parser.add_argument("--dashboard", action="store_true",
                        help="Auto-generate HTML dashboard after parsing")
    args = parser.parse_args()

    platforms = list(SCRAPER_MAP.keys()) if "all" in args.platforms else args.platforms

    credentials = {}
    if args.credentials:
        creds_path = Path(args.credentials)
        if creds_path.exists():
            credentials = json.loads(creds_path.read_text(encoding="utf-8"))
            print(f"[INFO] Loaded credentials from {creds_path}")
        else:
            print(f"[WARN] Credentials file not found: {creds_path}")

    print("=" * 60)
    print("ACUP v1.1 Browser Scraper")
    print(f"Platforms: {', '.join(platforms)}")
    print(f"Output: {args.output}")
    print(f"Headless: {args.headless}")
    print(f"Max conversations: {args.max_conversations or 'unlimited'}")
    print(f"Auto-parse: {args.parse}")
    print(f"Auto-dashboard: {args.dashboard}")
    print("=" * 60)

    runner = ScraperRunner(
        platforms=platforms,
        output_dir=args.output,
        headless=args.headless,
        credentials=credentials,
        max_conversations=args.max_conversations,
        session_file=args.session
    )

    results = asyncio.run(runner.run())

    if not results:
        print("[WARN] No conversations scraped. Exiting.")
        sys.exit(1)

    print(f"\n[SUCCESS] Scraped {len(results)} conversations.")

    # Auto-parse pipeline
    if args.parse:
        print("\n[PIPELINE] Running v1.0 parser on scraped data...")
        scraped_json = Path(args.output) / "conversations_scraped.json"
        if scraped_json.exists():
            cmd = [
                sys.executable, "ai_chat_parser.py",
                str(scraped_json),
                "--json-out", str(Path(args.output) / "conversations.json"),
                "--csv-out", str(Path(args.output) / "conversations.csv"),
                "--md-out", str(Path(args.output) / "markdown_layouts"),
                "--stats-out", str(Path(args.output) / "stats.json")
            ]
            subprocess.run(cmd, check=False)
            print("[PIPELINE] Parser complete.")

        if args.dashboard:
            print("[PIPELINE] Generating dashboard...")
            cmd = [
                sys.executable, "generate_dashboard.py",
                "--input", str(Path(args.output) / "conversations.json"),
                "--output", str(Path(args.output) / "dashboard.html")
            ]
            subprocess.run(cmd, check=False)
            print(f"[PIPELINE] Dashboard: {Path(args.output) / 'dashboard.html'}")

    print("\n[COMPLETE] v1.1 pipeline finished.")
    print(f"Files in: {args.output}")


if __name__ == "__main__":
    main()
