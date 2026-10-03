#!/usr/bin/env python3
"""
seed-post-blsky.py — Find the first mention of a phrase on Bluesky.

Uses the AT Protocol public API (no auth needed) to search Bluesky's
full post archive. Binary-chops date ranges to pinpoint the earliest
mention, then scans growth in successive time windows.

Usage:
  python seed-post-blsky.py "bitcoin"
  python seed-post-blsky.py "bitcoin" --graph
  python seed-post-blsky.py "bitcoin" --json

Requires:
  pip install atproto

License: MIT
"""

import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path

from atproto import Client


# ── Constants ──────────────────────────────────────────────────────────

BSKY_LAUNCH_DATE = datetime.date(2024, 2, 1)
PUBLIC_API_URL = "https://api.bsky.app"

SEARCH_LIMIT_SMALL = 1
SEARCH_LIMIT_MED = 30
SEARCH_LIMIT_MAX = 100

QUERY_DELAY = 1.5
RATE_LIMIT_RETRY = 30


# ── Client ─────────────────────────────────────────────────────────────

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(base_url=PUBLIC_API_URL)
    return _client


# ── Date helpers ────────────────────────────────────────────────────────

def today_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def fmt_date(dt: datetime.date | datetime.datetime) -> str:
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")


def fmt_dt_iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ymd(date_str: str) -> tuple:
    """Parse YYYY-MM-DD into (year, month, day)."""
    parts = date_str.split("-")
    return int(parts[0]), int(parts[1]), int(parts[2])


def parse_window_duration(dur_str: str) -> int | None:
    m = re.match(r"^(\d+)([dmy])$", dur_str.strip().lower())
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2)
    if unit == "d":
        return val
    elif unit == "m":
        return val * 30
    elif unit == "y":
        return val * 365


# ── Bluesky search wrapper ─────────────────────────────────────────────

def search_posts(
    phrase: str,
    since_dt: datetime.datetime | None = None,
    until_dt: datetime.datetime | None = None,
    limit: int = SEARCH_LIMIT_SMALL,
    filters: str = "",
) -> tuple[list, int | None]:
    """Search Bluesky. Returns (serialized_posts, hits_total)."""
    client = get_client()
    time.sleep(QUERY_DELAY)

    q = phrase
    if filters:
        q = f"{phrase} {filters}"

    params = {
        "q": q,
        "sort": "latest",
        "limit": min(limit, SEARCH_LIMIT_MAX),
    }

    if since_dt:
        params["since"] = fmt_dt_iso(since_dt)
    if until_dt:
        params["until"] = fmt_dt_iso(until_dt)

    for attempt in range(3):
        try:
            resp = client.app.bsky.feed.search_posts(params)
        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str or "429" in err_str or "too many" in err_str:
                wait = RATE_LIMIT_RETRY * (attempt + 1)
                print(f"  [rate limited — retrying in {wait}s]", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  [error: {e}]", file=sys.stderr)
            return [], None

        posts = resp.posts if resp and hasattr(resp, "posts") else []
        hits_total = (
            resp.hits_total
            if resp and hasattr(resp, "hits_total")
            else None
        )
        serialized = [_serialize_post(p) for p in (posts or [])]
        return serialized, hits_total

    print("  [gave up after 3 retries]", file=sys.stderr)
    return [], None


def _serialize_post(post) -> dict:
    """Convert a postView model object to a clean dict.
    
    The atproto Python SDK converts camelCase fields to snake_case
    (e.g. likeCount → like_count). Handles both conventions.
    """
    result = {}
    result["uri"] = getattr(post, "uri", "")

    author = getattr(post, "author", None)
    if author:
        result["author"] = {
            "did": getattr(author, "did", ""),
            "handle": getattr(author, "handle", ""),
            "displayName": (
                getattr(author, "display_name", None)
                or getattr(author, "displayName", None)
            ),
            "avatar": getattr(author, "avatar", None),
        }
    else:
        result["author"] = {
            "did": "", "handle": "", "displayName": None, "avatar": None,
        }

    record = getattr(post, "record", None)
    if record:
        if hasattr(record, "__dict__") or hasattr(record, "model_fields"):
            result["text"] = getattr(record, "text", str(record))
            result["createdAt"] = (
                getattr(record, "created_at", None)
                or getattr(record, "createdAt", None)
                or getattr(post, "indexed_at", "")
                or getattr(post, "indexedAt", "")
            )
        else:
            result["text"] = str(record)
            result["createdAt"] = (
                getattr(post, "indexed_at", None)
                or getattr(post, "indexedAt", "")
            )
    else:
        result["text"] = ""
        result["createdAt"] = (
            getattr(post, "indexed_at", None)
            or getattr(post, "indexedAt", "")
        )

    result["replyCount"] = getattr(post, "reply_count", 0) or 0
    result["repostCount"] = getattr(post, "repost_count", 0) or 0
    result["likeCount"] = getattr(post, "like_count", 0) or 0
    result["quoteCount"] = getattr(post, "quote_count", 0) or 0
    result["indexedAt"] = (
        getattr(post, "indexed_at", None)
        or getattr(post, "indexedAt", "")
    )

    uri = result.get("uri", "")
    if uri and ":" in uri:
        parts = uri.split("/")
        did = parts[2] if len(parts) > 2 else ""
        rkey = parts[-1] if len(parts) > 1 else ""
        handle = result.get("author", {}).get("handle", did)
        result["webUrl"] = f"https://bsky.app/profile/{handle}/post/{rkey}"

    return result


def exact_match(phrase: str, post: dict) -> bool:
    return phrase.lower() in post.get("text", "").lower()


# ── Core: Binary-chop date search ──────────────────────────────────────

def probe_range(
    phrase: str,
    since_dt: datetime.datetime,
    until_dt: datetime.datetime | None,
    filters: str = "",
) -> int:
    posts, hits_total = search_posts(
        phrase, since_dt=since_dt, until_dt=until_dt, limit=SEARCH_LIMIT_SMALL,
        filters=filters,
    )
    if hits_total is not None:
        return hits_total
    return len(posts)


def find_earliest_year(phrase: str, start_year: int, end_year: int, filters: str = "") -> int:
    earliest = end_year
    for year in range(end_year, start_year - 1, -1):
        print(f"  Checking {year}... ", end="", file=sys.stderr, flush=True)
        since_dt = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
        until_dt = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        count = probe_range(phrase, since_dt, until_dt, filters=filters)
        print(f"({'✅' if count > 0 else '❌'}) ({count})", file=sys.stderr)
        if count > 0:
            earliest = year
        elif year < end_year:
            return year + 1
    return earliest


def find_earliest_month(phrase: str, year: int, filters: str = "") -> int:
    for month in range(1, 13):
        next_m = month + 1
        until_y, until_m = (year + 1, 1) if next_m > 12 else (year, next_m)
        print(f"  Checking {year}-{month:02d}... ", end="", file=sys.stderr, flush=True)
        since_dt = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
        until_dt = datetime.datetime(until_y, until_m, 1, tzinfo=datetime.timezone.utc)
        count = probe_range(phrase, since_dt, until_dt, filters=filters)
        print(f"({'✅' if count > 0 else '❌'}) ({count})", file=sys.stderr)
        if count > 0:
            return month
    return 1


def find_earliest_day(phrase: str, year: int, month: int, filters: str = "") -> int:
    if month == 12:
        days_in_month = 31
    else:
        next_m_date = datetime.date(year, month + 1, 1)
        days_in_month = (next_m_date - datetime.timedelta(days=1)).day

    print(f"  Scanning {year}-{month:02d} day by day...", file=sys.stderr, flush=True)
    for day in range(1, days_in_month + 1):
        day_end = day + 1
        if day_end <= days_in_month:
            ck_y, ck_m, ck_d = year, month, day_end
        elif month == 12:
            ck_y, ck_m, ck_d = year + 1, 1, 1
        else:
            ck_y, ck_m, ck_d = year, month + 1, 1

        since_dt = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)
        until_dt = datetime.datetime(ck_y, ck_m, ck_d, tzinfo=datetime.timezone.utc)
        count = probe_range(phrase, since_dt, until_dt, filters=filters)
        if count > 0:
            print(f"  > Earliest day: {year}-{month:02d}-{day:02d}", file=sys.stderr)
            return day
    return days_in_month


def fetch_day_posts(phrase: str, year: int, month: int, day: int, filters: str = "") -> list:
    since_dt = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)
    until_dt = since_dt + datetime.timedelta(days=1)
    posts, _hits = search_posts(
        phrase, since_dt=since_dt, until_dt=until_dt, limit=SEARCH_LIMIT_MAX,
        filters=filters,
    )
    return posts or []


# ── Growth scan ────────────────────────────────────────────────────────

def build_windows(
    first_date: datetime.datetime,
    window_days: int | None = None,
    annual: bool = False,
    weekly: bool = False,
    daily: bool = False,
) -> list:
    today = today_utc()

    if annual:
        windows = []
        now_year = today.year
        for year in range(first_date.year, now_year + 1):
            jan1 = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
            dec31 = datetime.datetime(
                year, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc
            )
            since = first_date if year == first_date.year else jan1
            until = today if year == now_year else dec31
            windows.append((str(year), since, until))
        return windows

    if window_days is not None:
        windows = []
        cur = first_date
        idx = 1
        while cur < today:
            nxt = min(cur + datetime.timedelta(days=window_days), today)
            windows.append((f"Window {idx}", cur, nxt))
            cur = nxt
            idx += 1
        return windows

    if daily:
        windows = []
        cur = first_date
        idx = 1
        one_day = datetime.timedelta(days=1)
        while cur < today:
            nxt = min(cur + one_day, today)
            windows.append((f"Day {idx}", cur, nxt))
            cur = nxt
            idx += 1
        return windows

    if weekly:
        windows = []
        cur = first_date
        idx = 1
        seven_days = datetime.timedelta(days=7)
        while cur < today:
            nxt = min(cur + seven_days, today)
            windows.append((f"Week {idx}", cur, nxt))
            cur = nxt
            idx += 1
        return windows

    windows = []
    w1_end = min(first_date + datetime.timedelta(days=7), today)
    w2_end = min(first_date + datetime.timedelta(days=14), today)
    m1_end = min(first_date + datetime.timedelta(days=30), today)
    windows.append(("Week 1 (first 7 days)", first_date, w1_end))
    windows.append(("Week 2", w1_end, w2_end))
    windows.append(("Remainder of Month 1", w2_end, m1_end))

    ws = m1_end
    month_num = 2
    while ws < today:
        we = min(ws + datetime.timedelta(days=30), today)
        windows.append((f"Month {month_num}", ws, we))
        ws = we
        month_num += 1
    return windows


def fmt_date_range(since_dt: datetime.datetime, until_dt: datetime.datetime) -> str:
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    if since_dt.year == until_dt.year and since_dt.month == until_dt.month:
        return f"{months[since_dt.month]} {since_dt.day}-{until_dt.day}"
    elif since_dt.year == until_dt.year:
        return (
            f"{months[since_dt.month]} {since_dt.day}"
            f" - {months[until_dt.month]} {until_dt.day}"
        )
    else:
        return (
            f"{months[since_dt.month]} {since_dt.day} {since_dt.year}"
            f" - {months[until_dt.month]} {until_dt.day}"
        )


def scan_growth(
    phrase: str,
    first_date: datetime.datetime,
    window_days: int | None = None,
    annual: bool = False,
    weekly: bool = False,
    daily: bool = False,
    filters: str = "",
) -> list:
    windows = build_windows(first_date, window_days=window_days, annual=annual,
                            weekly=weekly, daily=daily)
    results = []
    for label, since_dt, until_dt in windows:
        print(f"  {label}... ", end="", file=sys.stderr, flush=True)
        posts, hits_total = search_posts(
            phrase, since_dt=since_dt, until_dt=until_dt, limit=SEARCH_LIMIT_MED,
            filters=filters,
        )
        count = hits_total or len(posts)
        print(f"{count} posts", file=sys.stderr)
        results.append({
            "label": label,
            "since": fmt_date(since_dt),
            "until": fmt_date(until_dt),
            "count": count,
            "date_range": fmt_date_range(since_dt, until_dt),
        })
    return results


# ── Output formatting ──────────────────────────────────────────────────

def format_og_post(post: dict) -> str:
    author = post.get("author", {})
    handle = author.get("handle", "?")
    display_name = author.get("displayName", "")
    text = post.get("text", "")
    created_at = post.get("createdAt", "?")
    web_url = post.get("webUrl", "")
    likes = post.get("likeCount", 0)
    rts = post.get("repostCount", 0)
    replies = post.get("replyCount", 0)
    quotes = post.get("quoteCount", 0)

    words = text.split()
    wrapped = []
    line = ""
    for w in words:
        if len(line) + len(w) + 1 > 50:
            wrapped.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        wrapped.append(line)

    card = []
    card.append("╔══════════════════════════════════════════════════════╗")
    card.append("║  SEED POST FOUND                                    ║")
    card.append("╠══════════════════════════════════════════════════════╣")
    name_part = f"@{handle} ({display_name})" if display_name else f"@{handle}"
    card.append(f"║  {name_part:<48s} ║")
    card.append(f"║  {created_at:<46s} ║")
    card.append(f"║  {web_url:<48s} ║")
    card.append("╠══════════════════════════════════════════════════════╣")
    for line_text in wrapped:
        card.append(f"║  {line_text:<48s} ║")
    card.append("╠══════════════════════════════════════════════════════╣")
    card.append(
        f"║  ❤️ {likes:<5d}  ↻ {rts:<5d}  💬 {replies:<5d}  🦋 {quotes:<5d}    ║"
    )
    card.append("╚══════════════════════════════════════════════════════╝")
    return "\n".join(card)


def format_growth(windows: list) -> str:
    if not windows:
        return ""

    max_count = max(w["count"] for w in windows)
    bar_width = 30
    scale = bar_width / max_count if max_count > 0 else 1

    cumulative = 0
    lines = [
        "╔══════════════════════════════════════════════════════╗",
        "║  GROWTH TIMELINE     mentions over time              ║",
        "╠════╦══════════════════╦═══════╦═══════════╦═══════════════════════╣",
    ]

    display = []
    i = 0
    while i < len(windows):
        w = windows[i]
        count = w["count"]
        run = 1
        while i + run < len(windows) and windows[i + run]["count"] == count:
            run += 1
        if run >= 3:
            first = windows[i]
            last = windows[i + run - 1]
            collapsed = f"{first['label']}+"
            dr = first.get("date_range", "").split(" - ")[0].split(" ")[-1] + " onward"
            display.append({"label": collapsed, "count": count,
                            "date_range": dr, "collapsed": run})
            i += run
        else:
            display.append(w)
            i += 1

    for d in display:
        count = d["count"]
        cumulative += count
        bar_len = int(count * scale) if count > 0 else 0
        bar = "█" * min(bar_len, bar_width)
        lbl = d["label"]
        dr = d.get("date_range", "")
        lines.append(f"║ {lbl:>5s} ║ {dr:28s} ║ {count:5d} ║ {cumulative:7d} ║ {bar:{bar_width}s} ║")

    collapsed_total = sum(d.get("collapsed", 0) for d in display if d.get("collapsed"))
    if collapsed_total:
        last_count = display[-1]["count"] if display else 0
        collapsed_rows = sum(1 for d in display if d.get("collapsed"))
        unit = "rows" if collapsed_rows > 1 else "row"
        lines.append("╠════╧══════════════════╧═══════╧═══════════════════╣")
        lines.append(
            f"║ {collapsed_total} @ {last_count}+ posts"
            f" — {collapsed_rows} {unit} collapsed{' ║' if collapsed_rows > 1 else '    ║'}"
        )

    lines.append("╚══════════════════════════════════════════════════════╝")
    return "\n".join(lines)


def fetch_early_shares(
    phrase: str,
    seed_created_at: str,
    seed_uri: str,
    max_shares: int = 5,
    filters: str = "",
) -> list:
    """Fetch the first posts after the seed post that mention the phrase."""
    seed_dt = datetime.datetime.fromisoformat(
        seed_created_at.replace("Z", "+00:00")
    )
    day_after = seed_dt + datetime.timedelta(days=1)
    week_later = seed_dt + datetime.timedelta(days=7)

    posts, _hits = search_posts(
        phrase, since_dt=day_after, until_dt=week_later, limit=SEARCH_LIMIT_MED,
        filters=filters,
    )
    if not posts:
        return []

    early = []
    seen_uris = {seed_uri}
    for p in posts:
        uri = p.get("uri", "")
        if uri and uri not in seen_uris and exact_match(phrase, p):
            early.append(p)
            seen_uris.add(uri)
        if len(early) >= max_shares:
            break
    return early


def format_early_shares(shares: list) -> str:
    if not shares:
        return ""
    card = []
    card.append("╔══════════════════════════════════════════════════════╗")
    card.append("║  EARLY MENTIONS   who picked it up next                ║")
    card.append("╠══════════════════════════════════════════════════════╣")
    for i, t in enumerate(shares, 1):
        author = t.get("author", {})
        handle = author.get("handle", "?")
        text = t.get("text", "").replace("\n", " ")[:80]
        created = t.get("createdAt", "?")
        card.append(f"║  {i}. @{handle:<35s}           ║")
        card.append(f"║     {created:<44s} ║")
        words = text.split()
        line = ""
        for w in words:
            if len(line) + len(w) + 1 > 44:
                card.append(f"║     {line:<44s} ║")
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            card.append(f"║     {line:<44s} ║")
        if i < len(shares):
            card.append("╠══════════════════════════════════════════════════════╣")
    card.append("╚══════════════════════════════════════════════════════╝")
    return "\n".join(card)


# ── Main pipeline ──────────────────────────────────────────────────────

def find_seed_post(
    phrase: str,
    growth: bool = False,
    after_date: str | None = None,
    before_date: str | None = None,
    window_days: int | None = None,
    annual: bool = False,
    weekly: bool = False,
    daily: bool = False,
    shares_count: int = 0,
    filters: str = "",
) -> dict:
    """Full pipeline. Returns result dict."""
    print(f"🔎 Searching for first mention of \"{phrase}\" on Bluesky",
          file=sys.stderr)

    start_year = BSKY_LAUNCH_DATE.year
    end_year = today_utc().year
    if after_date:
        sy, _sm, _sd = parse_ymd(after_date)
        start_year = max(start_year, sy)
    if before_date:
        ey, _em, _ed = parse_ymd(before_date)
        end_year = min(end_year, ey)

    lo = after_date or f"{start_year}-01-01"
    hi = before_date or f"{end_year}-12-31"
    print(f"  Range: {lo} → {hi}", file=sys.stderr)

    if filters:
        print(f"  Filters: {filters}", file=sys.stderr)

    print("Phase 1: Existence check", file=sys.stderr)
    since_dt = (
        datetime.datetime(start_year, 1, 1, tzinfo=datetime.timezone.utc)
        if not after_date
        else datetime.datetime(*parse_ymd(after_date), tzinfo=datetime.timezone.utc)
    )
    until_dt = (
        datetime.datetime(end_year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        if not before_date
        else datetime.datetime(*parse_ymd(before_date), tzinfo=datetime.timezone.utc)
    )
    count = probe_range(phrase, since_dt, until_dt, filters=filters)
    if count == 0:
        print(
            f"\n  No mentions of \"{phrase}\" found in that range.\n",
            file=sys.stderr,
        )
        return {"found": False, "phrase": phrase}
    print(f"  ✅ Found — at least {count} result{'s' if count != 1 else ''}",
          file=sys.stderr)

    print("Phase 2: Binary-chop — earliest year", file=sys.stderr)
    year = find_earliest_year(phrase, start_year=start_year, end_year=end_year,
                               filters=filters)
    print(f"  → Earliest year: {year}", file=sys.stderr)

    print("Phase 3: Earliest month", file=sys.stderr)
    month = find_earliest_month(phrase, year, filters=filters)
    print(f"  → Earliest month: {year}-{month:02d}", file=sys.stderr)

    print("Phase 4: Earliest day", file=sys.stderr)
    day = find_earliest_day(phrase, year, month, filters=filters)
    print(f"  → Earliest day: {year}-{month:02d}-{day:02d}", file=sys.stderr)

    print("Phase 5: Finding the OG post", file=sys.stderr)
    posts = fetch_day_posts(phrase, year, month, day, filters=filters)
    if not posts:
        print("  No posts returned for that day.", file=sys.stderr)
        return {"found": False, "phrase": phrase, "reason": "no_posts_from_api"}

    exact = [p for p in posts if exact_match(phrase, p)]
    exact.sort(key=lambda p: p.get("createdAt", ""))
    if not exact:
        print("  No exact substring matches (token-level only).", file=sys.stderr)
        return {"found": False, "phrase": phrase, "reason": "token_match_only"}

    first_post = exact[0]
    print(
        f"  ✅ @{first_post.get('author',{}).get('handle','?')}"
        f" — {first_post.get('createdAt','?')}",
        file=sys.stderr,
    )

    growth_data = None
    if growth:
        print(file=sys.stderr)
        print("Phase 6: Growth scan", file=sys.stderr)
        first_date = datetime.datetime.fromisoformat(
            first_post["createdAt"].replace("Z", "+00:00")
        )
        growth_data = scan_growth(
            phrase, first_date, window_days=window_days, annual=annual,
            weekly=weekly, daily=daily, filters=filters,
        )

    shares_data = None
    if shares_count > 0:
        print(file=sys.stderr)
        print(f"Phase 7: Early mentions (first {shares_count})", file=sys.stderr)
        shares_data = fetch_early_shares(
            phrase, first_post["createdAt"], first_post.get("uri", ""),
            max_shares=shares_count, filters=filters,
        )
        print(
            f"  → Found {len(shares_data)} early mention"
            f"{'s' if len(shares_data)!=1 else ''}",
            file=sys.stderr,
        )

    return {
        "found": True,
        "phrase": phrase,
        "og_post": first_post,
        "growth": growth_data,
        "early_shares": shares_data,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Find the first mention of a phrase on Bluesky"
    )
    parser.add_argument("phrase", help="The exact phrase to search for")
    parser.add_argument("--graph", "-g", action="store_true",
                        help="Run growth scan (mention frequency over time windows)")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output results as JSON (machine-readable)")
    parser.add_argument("--after", metavar="YYYY-MM-DD",
                        help="Only search after this date (inclusive)")
    parser.add_argument("--before", metavar="YYYY-MM-DD",
                        help="Only search before this date (exclusive)")
    parser.add_argument("--window", metavar="DURATION",
                        help="Growth window duration: '7d', '30d', '3m', '1y' etc.")
    parser.add_argument("--annual", action="store_true",
                        help="Annual growth windows (calendar years from OG post)")
    parser.add_argument("--weekly", action="store_true",
                        help="Weekly growth windows (7-day intervals)")
    parser.add_argument("--daily", action="store_true",
                        help="Daily growth windows (1-day intervals)")
    parser.add_argument("--shares", type=int, default=0, metavar="N",
                        help="Show first N early shares/replies to the seed post")
    parser.add_argument("--from-user", metavar="HANDLE",
                        help="Only posts from this user (from:handle)")
    parser.add_argument("--lang", metavar="CODE",
                        help="Language filter: 'en', 'ja', 'es', etc. (lang:code)")
    parser.add_argument("--domain", metavar="DOMAIN",
                        help="Only posts linking from this domain (domain:example.com)")
    parser.add_argument("--filter", metavar="OPS",
                        help="Raw Bluesky search operators to append to query")

    args = parser.parse_args()
    phrase = args.phrase.strip()

    if len(phrase) < 2:
        print("error: phrase must be at least 2 characters", file=sys.stderr)
        sys.exit(1)

    for flag in ["after", "before"]:
        val = getattr(args, flag)
        if val and not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
            print(f"error: --{flag} must be YYYY-MM-DD format, got '{val}'",
                  file=sys.stderr)
            sys.exit(1)

    window_days = None
    if args.window:
        window_days = parse_window_duration(args.window)
        if window_days is None:
            print(
                f"error: --window must be like '30d', '3m', or '1y', got '{args.window}'",
                file=sys.stderr,
            )
            sys.exit(1)

    filters = ""
    filter_parts = []
    if args.from_user:
        filter_parts.append(f"from:{args.from_user}")
    if args.lang:
        filter_parts.append(f"lang:{args.lang}")
    if args.domain:
        filter_parts.append(f"domain:{args.domain}")
    if args.filter:
        filter_parts.append(args.filter)
    if filter_parts:
        filters = " ".join(filter_parts)

    result = find_seed_post(
        phrase,
        growth=args.graph,
        after_date=args.after,
        before_date=args.before,
        window_days=window_days,
        annual=args.annual,
        weekly=args.weekly,
        daily=args.daily,
        shares_count=args.shares,
        filters=filters,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    elif result.get("found"):
        print(format_og_post(result["og_post"]))
        if result.get("early_shares"):
            print(format_early_shares(result["early_shares"]))
        if result.get("growth"):
            print(format_growth(result["growth"]))
    else:
        print(f"\n  No seed post found for \"{args.phrase}\".\n")


if __name__ == "__main__":
    main()