---
name: seed-post-blsky
description: "Find the first-ever mention of any phrase on Bluesky — binary-chop archive search + growth timeline"
author: https://github.com/jbrck
license: MIT
platforms: [linux, macos]
card: card.png
prerequisites:
  commands: [python3]
  pip: [atproto]
---

# seed-post-blsky — Find the first mention of any phrase on Bluesky

Given any phrase, **seed-post-blsky** finds the earliest mention on Bluesky by searching the platform's full archive through the AT Protocol's public search API. Uses the same binary-chop date narrowing algorithm from the X version, adapted for Bluesky's API.

## How it works

Bluesky's public API (`app.bsky.feed.searchPosts`) supports `since` and `until` date parameters. seed-post-blsky uses this to:

1. **Probe existence** — is the phrase on Bluesky at all?
2. **Binary-chop years** — walk backward from the current year to find the earliest year with mentions
3. **Binary-chop months** — within that year, find the earliest month
4. **Binary-chop days** — within that month, find the earliest day
5. **Fetch and filter** — get all posts from that day, filter for exact substring matches, return the chronologically first
6. **Growth scan** (optional) — scan successive time windows to show mention-frequency growth

A full search runs in under 60 seconds for most phrases. No authentication needed.

## Key differences from the X version

| X version | Bluesky version |
|---|---|
| Requires Node.js + `@steipete/bird` npm CLI | Python only + `atproto` pip package |
| Cookie auth (expires, fragile) | Public API — zero auth |
| X launched 2006 — 18+ year archive | Bluesky launched Feb 2024 — ~2.5 year archive |
| API is undocumented internal GraphQL | API is documented AT Protocol stable endpoint (`api.bsky.app`) |
| `since:` and `until:` as query string operators | `since` and `until` as structured API parameters |

## Setup

### 1. Install the dependency

```bash
pip install atproto
```

That's it. No Node.js, no npm, no cookies.

### 2. Run it

```bash
python3 scripts/seed-post-blsky.py "bitcoin"
```

## Usage

```
python3 scripts/seed-post-blsky.py <phrase> [--graph] [--annual] [--shares N] [--json]

Arguments:
  phrase       The exact phrase to search for (case-insensitive)
  --graph, -g  Also run growth scan (mention frequency over time windows)
  --weekly     Weekly growth windows (7-day intervals)
  --daily      Daily growth windows (1-day intervals)
  --annual     Calendar-year growth windows (for long-running terms)
  --window     Growth window duration: '7d', '30d', '3m', '1y', etc.
  --shares N   Show first N early mentions after the seed post
  --from-user  Only posts from this user (from:user.bsky.social)
  --lang       Language filter: 'en', 'ja', 'es', etc. (lang:code)
  --domain     Only posts linking from this domain (domain:example.com)
  --filter     Raw Bluesky search operators to append to query
  --json, -j   Output raw JSON (machine-readable)
  --after      Only search after this date (YYYY-MM-DD, inclusive)
  --before     Only search before this date (YYYY-MM-DD, exclusive)
```

### Examples

#### Find the first mention

```bash
python3 scripts/seed-post-blsky.py "bitcoin"
```

Output:
```
╔══════════════════════════════════════════════════════╗
║  SEED POST FOUND                                    ║
╠══════════════════════════════════════════════════════╣
║  @bitcoiner.social                                  ║
║  2024-02-15T14:32:00.000Z                           ║
║  https://bsky.app/profile/bitcoiner.social/post/xxx ║
╠══════════════════════════════════════════════════════╣
║  Is anyone else watching the bitcoin chart today?   ║
╠══════════════════════════════════════════════════════╣
║  ❤️ 133  ↻ 44  💬 11  🦋 7                        ║
╚══════════════════════════════════════════════════════╝
```

#### Full search with growth timeline

```bash
python3 scripts/seed-post-blsky.py "bitcoin" --graph
```

Shows the OG post + a bar chart of mention activity across time windows.

#### Annual growth view

```bash
python3 scripts/seed-post-blsky.py "bitcoin" --graph --annual
```

#### Get raw JSON

```bash
python3 scripts/seed-post-blsky.py "bitcoin" --json
```

## Project structure

```
seed-post-blsky/
├── SKILL.md                     # This file — docs + skill definition
├── requirements.txt             # Python dependency: atproto
├── .env.example                 # Placeholder (no auth needed)
├── .gitignore
└── scripts/
    └── seed-post-blsky.py       # Main script — binary-chop + growth scan
```

## Algorithm details

### Binary-chop date narrowing

```
Broad existence probed in one query
    ↓
Year-level scan (current year → 2024, backward)
    ↓
Month-level scan within winning year
    ↓
Day-level binary chop within winning month
    ↓
Linear backward scan to confirm first day
    ↓
Fetch all posts from the confirmed day
    ↓
Filter for exact substring matches
    ↓
Sort by createdAt, return earliest
```

### Growth window schedule

```
Week 1:  D → D+7      (first 7 days)
Week 2:  D+7 → D+14   (days 8-14)
Remainder of Month 1:  D+14 → D+30
Month N:   30-day rolling windows until today
```

### Exact-match filtering

Bluesky's search tokenizes queries. The script filters results client-side with an exact substring check (`phrase.lower() in post['text'].lower()`) to ensure only true matches.

### Rate limiting

The script spaces queries 1.5 seconds apart to avoid triggering Bluesky's rate limits. A full search with growth scan makes ~30-50 API calls and takes 1-3 minutes. On rate limit, it backs off 30-60 seconds and retries up to 3 times.

## Limitations

- **Token-level search** — Bluesky's search matches tokens, not substrings. Client-side filtering catches most false positives.
- **Archive depth** — Bluesky launched publicly February 2024. The binary chop covers ~2.5 years of history, not 18+.
- **hitsTotal rounding** — Bluesky's `hitsTotal` field may be rounded or truncated for large result sets. Growth scan counts are directional, not exact.
- **Deleted/private posts** — Not indexed by Bluesky's search.
- **API limits** — Search returns max 100 posts per call. The growth scan's count per window is capped by sample size.
- **sortAt vs createdAt** — Bluesky's `since`/`until` filters use the `sortAt` timestamp (when indexed), not `createdAt` (when posted). Minor discrepancies are possible for early posts.

## Who this is for

**Marketers and brand managers** — track the first mention of your brand, product, or campaign on Bluesky.

**Crypto degens** — trace when a token, chain, or protocol first entered the conversation on Bluesky.

**PR and crisis teams** — pinpoint when a rumor or claim first appeared on Bluesky.

**Competitive intelligence** — find when a competitor first named a product category on the platform.

**Political researchers** — trace when a slogan, hashtag, or narrative first appeared.

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| "No mentions found" for a known phrase | Phrase is too new and hasn't been indexed | Wait a few hours or check manually |
| Script exits with rate limit error | Too many queries too fast | Wait 2 minutes and retry |
| Growth scan shows 0 for all windows | Phrase is too new or too rare | The script found results in existence check but couldn't find them with exact-match filter |
| `ImportError: No module named atproto` | Dependency not installed | Run `pip install atproto` |

## License

MIT.

## Related

Part of the `skills-for-bluesky` collection — standalone skills for Bluesky.
See parent repo: https://github.com/jbrck/skills-for-bluesky