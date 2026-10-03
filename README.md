# skills-for-bluesky

Standalone tools for mining Bluesky's archive via the AT Protocol public API.

No auth required. No Node.js. Just Python + `pip install atproto`.

## Skills

| Skill | What it does |
|-------|-------------|
| [seed-post-blsky](seed-post-blsky/) | Find the first-ever mention of any phrase on Bluesky — binary-chop archive search + growth timeline |

## Who this is for

**Marketers and brand managers** — track the first mention of your brand, product, or campaign on Bluesky. Useful for origin stories, PR timelines, and "we were here first" positioning.

**Crypto degens** — trace when a token, chain, or protocol first entered the conversation on Bluesky. ("charlie kirk" is the built-in example.)

**Patent and trademark attorneys** — establish first-public-use dates on a growing public platform.

**PR and crisis teams** — pinpoint when a rumor, lie, or leaked claim first appeared on Bluesky. Tighter correction timelines, faster takedown requests.

**Competitive intelligence** — find when a competitor first named a product category on Bluesky.

**Product managers** — locate the first user request for a feature. Hard data for roadmap justification.

**Political and election researchers** — trace when a slogan, hashtag, or narrative entered the Bluesky conversation.

**Disinformation researchers** — identify patient zero of a coordinated narrative on Bluesky.

## Requirements

- **Python >= 3.9**
- **pip install atproto** (single dependency)

No API keys. No cookies. No browser setup.

## Why Bluesky?

Bluesky's public API at `https://api.bsky.app` is a documented, stable AT Protocol endpoint that requires zero authentication for search queries. This makes it dramatically simpler to build tools against compared to X's undocumented internal GraphQL API with fragile cookie auth.

The tradeoff: Bluesky launched publicly in February 2024, so the archive is ~2.5 years deep instead of 18+. For most use cases — tracking brand mentions, product launches, or narrative origins — that's enough.

## Porting from skills-for-x

Each skill in this repo is a port of the corresponding skill from [skills-for-x](https://github.com/jbrck/skills-for-x). The binary-chop algorithm is platform-agnostic and ports cleanly. The API surface is cleaner on Bluesky.

## License

Skills in this repo are individually licensed. Check each skill's `SKILL.md` for its license.

## Attribution

Built by [Justin Brock](https://github.com/jbrck). Not affiliated with Bluesky.