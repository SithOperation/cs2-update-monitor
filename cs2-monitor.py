import feedparser
import json
import os
import requests
import time
from pathlib import Path
from datetime import datetime, timezone

STATE_FILE = Path("cs2_state.json")
DISCORD_LIMIT = 1900

DISCORD_WEBHOOK_URLS = [
    os.environ["DISCORD_WEBHOOK_URL_1"],
    os.environ["DISCORD_WEBHOOK_URL_2"],
]

FEEDS = [
    "https://store.steampowered.com/feeds/news/app/730/?cc=US&l=english",
    "https://steamdb.info/app/730/patchnotes/rss/",
]

KEYWORDS = [
    "update",
    "release notes",
    "patch",
    "fixed",
    "changed",
    "weapon",
    "map",
    "matchmaking",
    "premier",
    "vac",
    "anti-cheat",
    "sub-tick",
    "skins",
    "market",
    "case",
    "trade",
    "animation",
    "sound",
    "server",
]

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_links": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def send_discord_alert(message):
    for webhook_url in DISCORD_WEBHOOK_URLS:
        response = requests.post(
            webhook_url,
            json={"content": message[:DISCORD_LIMIT]},
            timeout=20
        )

        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 5)
            time.sleep(retry_after + 1)

            response = requests.post(
                webhook_url,
                json={"content": message[:DISCORD_LIMIT]},
                timeout=20
            )

        response.raise_for_status()
        time.sleep(2)

def matches_keywords(title, summary):
    text = f"{title} {summary}".lower()
    return [word for word in KEYWORDS if word.lower() in text]

def main():
    state = load_state()
    seen_links = set(state.get("seen_links", []))
    new_seen_links = set(seen_links)

    for feed_url in FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:10]:
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "")

            if not link or link in seen_links:
                continue

            matched = matches_keywords(title, summary)
            new_seen_links.add(link)

            if not matched:
                continue

            source = feed.feed.get("title", "CS2 Update Feed")

            send_discord_alert(
                f"🎮 **Counter-Strike 2 Update Alert**\n\n"
                f"Source: **{source}**\n"
                f"Matched: **{', '.join(matched[:6])}**\n"
                f"Title: **{title}**\n"
                f"{link}"
            )

    state["seen_links"] = list(new_seen_links)[-500:]
    state["last_checked"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

if __name__ == "__main__":
    main()
