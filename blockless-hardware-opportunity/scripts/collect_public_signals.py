#!/usr/bin/env python3
"""Respectfully collect public, traceable early-signal records for a hardware idea."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from re import sub

USER_AGENT = "BlocklessOpportunityResearch/0.1 (public research; contact: research@block-less.com)"


def get_json(url: str) -> object:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    # Unauthenticated GitHub search allows 10 requests/minute; a token allows 30.
    if url.startswith("https://api.github.com/") and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def clean(value: object) -> str:
    return sub(r"\s+", " ", sub(r"<[^>]+>", " ", unescape(str(value or "")))).strip()


def record(source: str, community: str, query: str, title: str, body: str, url: str, published: str = "", query_variant: str = "") -> dict[str, str]:
    return {"source": source, "community": community, "query": query, "query_variant": query_variant or query, "title": clean(title), "body": clean(body)[:1200], "url": url, "published_at": published or "", "fetched_at": datetime.now(timezone.utc).isoformat()}


STOP_WORDS = {"a", "an", "and", "app", "for", "in", "of", "on", "the", "through", "to", "with", "without"}


def query_variants(query: str) -> list[str]:
    """Always search the full task phrase; for long phrases also search the last two bigrams."""
    words = [word.lower() for word in re.findall(r"[a-zA-Z0-9]+", query) if word.lower() not in STOP_WORDS]
    variants = [query]
    if len(words) > 3:
        pairs = [" ".join(words[index:index + 2]) for index in range(len(words) - 1)]
        variants.extend(pairs[-2:])
    return list(dict.fromkeys(variant for variant in variants if variant.strip()))


def hn(query: str, limit: int, parent_query: str | None = None) -> list[dict[str, str]]:
    """Collect both posts and replies: consumer language is often in replies."""
    url = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode({"query": query, "tags": "(story,comment)", "hitsPerPage": limit})
    data = get_json(url)
    return [record("hackernews", "Hacker News", parent_query or query, item.get("title") or item.get("story_title"), item.get("comment_text") or item.get("story_text"), f"https://news.ycombinator.com/item?id={item.get('objectID')}", item.get("created_at"), query) for item in data.get("hits", [])]


def github(query: str, limit: int, parent_query: str | None = None) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    encoded = urllib.parse.urlencode({"q": f'"{query}" in:title,body', "sort": "updated", "order": "desc", "per_page": min(limit, 100)})
    for item in get_json("https://api.github.com/search/issues?" + encoded).get("items", []):
        if item.get("pull_request"):
            continue
        results.append(record("github", "GitHub Issues", parent_query or query, item.get("title"), item.get("body"), item.get("html_url"), item.get("created_at"), query))
    return results


def reddit(query: str, limit: int, parent_query: str | None = None) -> list[dict[str, str]]:
    encoded = urllib.parse.urlencode({"q": query, "sort": "new", "limit": min(limit, 100), "raw_json": 1})
    data = get_json("https://www.reddit.com/search.json?" + encoded)
    rows = []
    for child in data.get("data", {}).get("children", []):
        item = child.get("data", {})
        rows.append(record("reddit", f"r/{item.get('subreddit', 'unknown')}", parent_query or query, item.get("title"), item.get("selftext"), "https://www.reddit.com" + item.get("permalink", ""), str(item.get("created_utc", "")), query))
    return rows


DEFAULT_STACKEXCHANGE_SITES = "electronics,diy,superuser,parenting,workplace,psychology"
STACKEXCHANGE_SITES: list[str] = DEFAULT_STACKEXCHANGE_SITES.split(",")


def stackexchange(query: str, limit: int, parent_query: str | None = None) -> list[dict[str, str]]:
    """Query public Q&A communities outside Reddit; no account or login required."""
    results: list[dict[str, str]] = []
    for site in STACKEXCHANGE_SITES:
        params = {"site": site, "q": query, "pagesize": min(limit, 100), "order": "desc", "sort": "activity", "filter": "withbody"}
        data = get_json("https://api.stackexchange.com/2.3/search/advanced?" + urllib.parse.urlencode(params))
        for item in data.get("items", []):
            results.append(record("stackexchange", f"{site}.stackexchange", parent_query or query, item.get("title"), item.get("body"), item.get("link"), str(item.get("creation_date", "")), query))
    return results


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
    parser.add_argument("--include-reddit", action="store_true", help="Supplement non-Reddit sources with Reddit when its public endpoint is reachable")
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum concurrent public requests")
    parser.add_argument("--stackexchange-sites", default=DEFAULT_STACKEXCHANGE_SITES, help="Comma-separated Stack Exchange site slugs; pick the communities where this idea's users actually ask")
    args = parser.parse_args()
    STACKEXCHANGE_SITES[:] = [part.strip() for part in args.stackexchange_sites.split(",") if part.strip()]
    queries = [part.strip() for part in args.queries.split(",") if part.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path, log_path = args.output_dir / "raw-signals.jsonl", args.output_dir / "collection-log.json"
    logs, rows = [], []
    # Reddit is supplementary only: its unauthenticated endpoint is often blocked.
    # The required primary evidence comes from the non-Reddit public sources below.
    sources = [("github", github), ("hackernews", hn), ("stackexchange", stackexchange)]
    if args.include_reddit:
        sources.append(("reddit", reddit))

    def collect_one(source: str, func, query: str, variant: str):
        try:
            found = func(variant, args.per_source, query)
            return {"source": source, "query": query, "query_variant": variant, "status": "ok", "count": len(found)}, found
        except Exception as error:
            return {"source": source, "query": query, "query_variant": variant, "status": "error", "error": str(error)[:300]}, []
        finally:
            time.sleep(args.pause_seconds)

    jobs = [(source, func, query, variant) for query in queries for variant in query_variants(query) for source, func in sources]
    with ThreadPoolExecutor(max_workers=max(1, min(args.max_workers, 4))) as pool:
        futures = [pool.submit(collect_one, *job) for job in jobs]
        for future in as_completed(futures):
            log, found = future.result()
            logs.append(log)
            rows.extend(found)
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
