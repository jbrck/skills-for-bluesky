# seed-post-blsky

Find the first-ever mention of any phrase on Bluesky — binary-chop archive search + growth timeline + early mentions.

## Who this is for

**Marketers and brand managers** — track the first mention of your brand, product, or campaign on Bluesky. Useful for origin stories, PR timelines, and "we were here first" positioning.

**Crypto degens** — trace when a token, chain, or protocol first entered the conversation. ("hermes agent" is the built-in example.)

**Patent and trademark attorneys** — establish first-public-use dates on a growing public platform.

**PR and crisis teams** — pinpoint when a rumor, lie, or leaked claim first appeared. Tighter correction timelines, faster takedown requests.

**Competitive intelligence** — find when a competitor first named a product category. "We were talking about this before they were."

**Product managers** — locate the first user request for a feature. Hard data for roadmap justification.

**Political and election researchers** — trace when a slogan, hashtag, or narrative entered the Bluesky conversation.

**Disinformation researchers** — identify patient zero of a coordinated narrative on Bluesky.

## Quick start

```bash
pip install atproto
python3 scripts/seed-post-blsky.py "hermes agent"
```

No API keys. No cookies. No browser setup.

## Flags

| Flag | What it does |
|------|-------------|
| `--graph` / `-g` | Show growth timeline (mention frequency over time) |
| `--weekly` | Weekly growth windows (7-day intervals) |
| `--daily` | Daily growth windows (1-day intervals) |
| `--annual` | Calendar-year growth windows |
| `--window 30d` | Custom window size: `7d`, `30d`, `3m`, `1y` |
| `--shares N` | Show first N early mentions after the seed post |
| `--from-user handle` | Only posts from this user (from:handle) |
| `--lang code` | Language filter: `en`, `ja`, `es`, etc. |
| `--domain example.com` | Only posts linking from this domain |
| `--filter "ops"` | Raw Bluesky search operators to append |
| `--after 2024-06-01` | Only search after this date |
| `--before 2025-01-01` | Only search before this date |
| `--json` / `-j` | Raw JSON output (machine-readable) |

## Examples

### Find the first mention

```bash
python3 scripts/seed-post-blsky.py "hermes agent"
```

Output:
```
╔════════════════════════════════════════════╗
║  RESULTS SUMMARY                           ║
╠════════════════════════════════════════════╣
║  Term           hermes agent                   ║
║  First mention  2024-02-15 14:32:00           ║
║  OG author      @hermes.bsky.social            ║
║  Search range   2024-02-01 — 2026-12-31      ║
║  Total mentions 24058                            ║
╚════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════╗
║  SEED POST FOUND                                    ║
╠══════════════════════════════════════════════════════╣
║  @hermes.bsky.social (Hermes)                     ║
║  2024-02-15T14:32:00.000Z                           ║
║  https://bsky.app/profile/hermes.bsky.social/post/abc123 ║
╠══════════════════════════════════════════════════════╣
║  hermes agent is a new paradigm for personal       ║
║  AI that puts the user first                      ║
╠══════════════════════════════════════════════════════╣
║  ❤️ 42     ↻ 12     💬 3      🦋 8              ║
╚══════════════════════════════════════════════════════╝
```

### Growth timeline

```bash
python3 scripts/seed-post-blsky.py "hermes agent" --graph
```

Shows the OG post + a bar chart of mention activity across time windows with cumulative running total column. The RESULTS SUMMARY table also gains a peak period and peak count row.

### Weekly growth

```bash
python3 scripts/seed-post-blsky.py "hermes agent" --graph --weekly
```

### Filter by user

```bash
python3 scripts/seed-post-blsky.py "hermes agent" --from-user jay.bsky.team
```

### Filter by language

```bash
python3 scripts/seed-post-blsky.py "hermes agent" --lang en
```

### Raw JSON

```bash
python3 scripts/seed-post-blsky.py "hermes agent" --json
```

## Bluesky search operators

seed-post-blsky flags support Bluesky's built-in search operators under the hood. The phrase you pass is combined with filter flags to form the API query. Here's what's available:

### Basic

| Operator | What it does | Example |
|----------|-------------|---------|
| `"phrase"` | Exact phrase match | `"voting machines"` |
| `OR` | Logical OR | `bitcoin OR crypto` |
| `#tag` | Hashtag search | `#bitcoin` |

### Entity

| Operator | What it does | Example |
|----------|-------------|---------|
| `from:handle` | Posts from a user | `--from-user jay.bsky.team` |
| `lang:code` | Language filter (BCP 47) | `--lang en` |
| `domain:example.com` | Posts linking from a domain | `--domain npr.org` |
| `#tag` | Hashtag search | `--filter "#news"` |
| `@user.bsky.social` | Mention of a user | `--filter "@jay.bsky.team"` |

### Custom combos

Use `--filter` to pass raw operators not covered by flags:

```bash
# Language + hashtag
python3 scripts/seed-post-blsky.py "tariffs" --filter "lang:en #economy"

# Domain + mention
python3 scripts/seed-post-blsky.py "AI" --filter "domain:npr.org @mike.bluesky"
```

Notes:
- `since:` and `until:` are handled internally by `--after`/`--before` flags — don't put them in `--filter`
- The `from:` operator in `--from-user` is the same as writing `--filter "from:handle"` (but the flag is more convenient)
- Operators that require authentication (`from:me`, `mentions:me`) don't work on the public API

## Requirements

- **Python >= 3.9**
- **pip install atproto**

No API keys. No cookies. No browser.

## How it works

The script uses Bluesky's public search API (`app.bsky.feed.searchPosts`) which supports structured `since` and `until` date parameters. It binary-chops by year → month → day, filters exact matches client-side, and returns the chronologically first post. The growth scan probes time windows from the OG post date to today using `hitsTotal` for accurate counts. The early mentions scan finds who picked up the term in the week after the seed post.

Full search with growth scan runs in 1-3 minutes and makes ~30-50 API calls.

## License

MIT. Part of the [skills-for-bluesky](https://github.com/jbrck/skills-for-bluesky) collection.