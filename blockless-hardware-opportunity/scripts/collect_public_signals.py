#!/usr/bin/env python3
"""Respectfully collect public, traceable early-signal records for a hardware idea."""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from re import sub

USER_AGENT = "BlocklessOpportunityResearch/0.1 (public research; contact: research@block-less.com)"


def get_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def clean(value: object) -> str:
    return sub(r"\s+", " ", sub(r"<[^>]+>", " ", unescape(str(value or "")))).strip()


def record(source: str, community: str, query: str, title: str, body: str, url: str, published: str = "") -> dict[str, str]:
    return {"source": source, "community": community, "query": query, "title": clean(title), "body": clean(body)[:1200], "url": url, "published_at": published or "", "fetched_at": datetime.now(timezone.utc).isoformat()}


def hn(query: str, limit: int) -> list[dict[str, str]]:
    url = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": limit})
    data = get_json(url)
    return [record("hackernews", "Hacker News", query, item.get("title"), item.get("story_text"), item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID')}", item.get("created_at")) for item in data.get("hits", [])]


def github(query: str, limit: int) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    encoded = urllib.parse.urlencode({"q": f'"{query}" in:title,body', "sort": "updated", "order": "desc", "per_page": min(limit, 100)})
    for item in get_json("https://api.github.com/search/issues?" + encoded).get("items", []):
        if item.get("pull_request"):
            continue
        results.append(record("github", "GitHub Issues", query, item.get("title"), item.get("body"), item.get("html_url"), item.get("created_at")))
    return results


def reddit(query: str, limit: int) -> list[dict[str, str]]:
    encoded = urllib.parse.urlencode({"q": query, "sort": "new", "limit": min(limit, 100), "raw_json": 1})
    data = get_json("https://www.reddit.com/search.json?" + encoded)
    rows = []
    for child in data.get("data", {}).get("children", []):
        item = child.get("data", {})
        rows.append(record("reddit", f"r/{item.get('subreddit', 'unknown')}", query, item.get("title"), item.get("selftext"), "https://www.reddit.com" + item.get("permalink", ""), str(item.get("created_utc", ""))))
    return rows


def seed_page(url: str, query: str) -> dict[str, str] | None:
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    robots = urllib.robotparser.RobotFileParser()
    try:
        robots.set_url(robots_url)
        robots.read()
        if not robots.can_fetch(USER_AGENT, url):
            return None
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
        title = clean(next(iter(__import__("re").findall(r"<title[^>]*>(.*?)</title>", html, flags=__import__("re").I | __import__("re").S)), ""))
        return record("seed_page", parsed.netloc, query, title, html, url)
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", required=True, help="Comma-separated English keyword phrases")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--per-source", type=int, default=100)
    parser.add_argument("--seed-url", action="append", default=[])
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    args = parser.parse_args()
    queries = [part.strip() for part in args.queries.split(",") if part.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path, log_path = args.output_dir / "raw-signals.jsonl", args.output_dir / "collection-log.json"
    logs, rows = [], []
    for query in queries:
        for source, func in [("github", github), ("hackernews", hn), ("reddit", reddit)]:
            try:
                found = func(query, args.per_source)
                rows.extend(found)
                logs.append({"source": source, "query": query, "status": "ok", "count": len(found)})
            except Exception as error:
                logs.append({"source": source, "query": query, "status": "error", "error": str(error)[:300]})
            time.sleep(args.pause_seconds)
    for url in args.seed_url:
        result = seed_page(url, queries[0] if queries else "")
        logs.append({"source": "seed_page", "url": url, "status": "ok" if result else "skipped_or_error", "count": 1 if result else 0})
        if result:
            rows.append(result)
        time.sleep(args.pause_seconds)
    with raw_path.open("w", encoding="utf-8") as target:
        for row in rows:
            target.write(json.dumps(row, ensure_ascii=False) + "\n")
    log_path.write_text(json.dumps({"queries": queries, "results": logs, "records": len(rows)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} records to {raw_path}")


if __name__ == "__main__":
    main()
