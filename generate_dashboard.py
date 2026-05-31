#!/usr/bin/env python3
"""
AI Chat Dashboard Generator
Generates an interactive HTML dashboard from ACUP parsed data.

Usage:
  python generate_dashboard.py --input conversations.json --output dashboard.html
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def generate_dashboard(data_path: str, output_path: str):
    with open(data_path, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    # Aggregate stats
    total_convs = len(conversations)
    total_msgs = sum(c["message_count"] for c in conversations)
    total_words = sum(c["word_count"] for c in conversations)

    platforms = {}
    for c in conversations:
        plat = c["platform"]
        if plat not in platforms:
            platforms[plat] = {"conversations": 0, "messages": 0, "words": 0, "items": []}
        platforms[plat]["conversations"] += 1
        platforms[plat]["messages"] += c["message_count"]
        platforms[plat]["words"] += c["word_count"]
        platforms[plat]["items"].append(c)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Chat Dashboard | ACUP v1.0</title>
<style>
  :root {{
    --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --muted: #94a3b8;
    --accent: #38bdf8; --accent2: #818cf8; --border: #334155;
    --user: #22c55e; --assistant: #f59e0b; --danger: #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
  header {{ margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }}
  header h1 {{ font-size: 1.8rem; color: var(--accent); }}
  header p {{ color: var(--muted); margin-top: 0.25rem; }}

  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .stat-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; text-align: center; }}
  .stat-card .value {{ font-size: 2rem; font-weight: 700; color: var(--accent); }}
  .stat-card .label {{ font-size: 0.875rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.25rem; }}

  .platform-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }}
  .platform-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }}
  .platform-header {{ padding: 1rem 1.5rem; background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #fff; }}
  .platform-header h2 {{ font-size: 1.25rem; }}
  .platform-header .meta {{ font-size: 0.875rem; opacity: 0.9; margin-top: 0.25rem; }}
  .platform-body {{ padding: 1rem; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
  th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
  td {{ color: var(--text); }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  .badge {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
  .badge-user {{ background: rgba(34,197,94,0.15); color: var(--user); }}
  .badge-assistant {{ background: rgba(245,158,11,0.15); color: var(--assistant); }}
  .badge-platform {{ background: rgba(56,189,248,0.15); color: var(--accent); }}

  .overview-table {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-bottom: 2rem; }}
  .overview-table h2 {{ padding: 1rem 1.5rem; font-size: 1.25rem; border-bottom: 1px solid var(--border); }}
  .overview-table .table-wrap {{ overflow-x: auto; }}

  .search-box {{ width: 100%; padding: 0.75rem 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 0.875rem; margin-bottom: 1rem; }}
  .search-box:focus {{ outline: none; border-color: var(--accent); }}

  .content-preview {{ max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--muted); }}

  footer {{ text-align: center; color: var(--muted); font-size: 0.875rem; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid var(--border); }}

  @media (max-width: 768px) {{
    .container {{ padding: 1rem; }}
    .platform-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🤖 AI Chat Universal Dashboard</h1>
    <p>Aggregated view across Kimi, Mistral, DeepSeek, AI Studio, and Gemini | Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
  </header>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="value">{total_convs}</div>
      <div class="label">Conversations</div>
    </div>
    <div class="stat-card">
      <div class="value">{total_msgs}</div>
      <div class="label">Total Messages</div>
    </div>
    <div class="stat-card">
      <div class="value">{total_words:,}</div>
      <div class="label">Total Words</div>
    </div>
    <div class="stat-card">
      <div class="value">{len(platforms)}</div>
      <div class="label">Platforms</div>
    </div>
  </div>

  <div class="overview-table">
    <h2>📊 Overview — All Conversations</h2>
    <div class="table-wrap">
      <input type="text" class="search-box" id="globalSearch" placeholder="Search conversations by title, platform, or content..." onkeyup="filterTables()">
      <table id="overviewTable">
        <thead>
          <tr>
            <th>Platform</th>
            <th>Title</th>
            <th>Messages</th>
            <th>User / Assistant</th>
            <th>Words</th>
            <th>Created</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
"""

    for c in conversations:
        html += f"""          <tr data-platform="{c['platform']}">
            <td><span class="badge badge-platform">{c['platform'].upper()}</span></td>
            <td>{c['title'][:60]}{'...' if len(c['title']) > 60 else ''}</td>
            <td>{c['message_count']}</td>
            <td><span class="badge badge-user">{c['user_message_count']}U</span> <span class="badge badge-assistant">{c['assistant_message_count']}A</span></td>
            <td>{c['word_count']:,}</td>
            <td>{c['created_at'] or 'N/A'}</td>
            <td class="content-preview">{c['source_file'] or 'N/A'}</td>
          </tr>
"""

    html += """        </tbody>
      </table>
    </div>
  </div>

  <div class="platform-grid">
"""

    for plat, data in sorted(platforms.items()):
        html += f"""    <div class="platform-card">
      <div class="platform-header">
        <h2>{plat.upper()}</h2>
        <div class="meta">{data['conversations']} conversations · {data['messages']} messages · {data['words']:,} words</div>
      </div>
      <div class="platform-body">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Msgs</th>
                <th>Words</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
"""
        for c in data["items"]:
            html += f"""              <tr>
                <td class="content-preview" title="{c['title']}">{c['title'][:40]}{'...' if len(c['title']) > 40 else ''}</td>
                <td>{c['message_count']}</td>
                <td>{c['word_count']:,}</td>
                <td>{c['created_at'] or 'N/A'}</td>
              </tr>
"""
        html += """            </tbody>
          </table>
        </div>
      </div>
    </div>
"""

    html += """  </div>

  <footer>
    <p>Generated by ACUP Dashboard Generator v1.0 | AI Chat Universal Parser</p>
  </footer>
</div>

<script>
function filterTables() {
  const query = document.getElementById('globalSearch').value.toLowerCase();
  const rows = document.querySelectorAll('#overviewTable tbody tr');
  rows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
}
</script>
</body>
</html>
"""

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="AI Chat Dashboard Generator")
    parser.add_argument("--input", default="conversations.json", help="Input JSON from ACUP")
    parser.add_argument("--output", default="dashboard.html", help="Output HTML file")
    args = parser.parse_args()
    generate_dashboard(args.input, args.output)


if __name__ == "__main__":
    main()
