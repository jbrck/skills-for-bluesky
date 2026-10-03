# skills-for-bluesky

A growing collection of standalone tools for mining Bluesky's archive via the AT Protocol public API.

No auth required. No Node.js. Just Python + `pip install atproto`.

## Skills

| Skill | What it does |
|-------|-------------|
| [seed-post-blsky](seed-post-blsky/) | Find the first-ever mention of any phrase on Bluesky — binary-chop archive search + growth timeline |

_More skills coming._

## Quick start

```shell
git clone https://github.com/jbrck/skills-for-bluesky.git
cd skills-for-bluesky/seed-post-blsky
pip install atproto
python3 scripts/seed-post-blsky.py "hermes agent"
```

## Requirements

- **Python >= 3.9**
- **pip install atproto** (single dependency)

No API keys. No cookies. No browser setup.

## Why Bluesky?

Bluesky's public API at `https://api.bsky.app` is a documented, stable AT Protocol endpoint that requires zero authentication for search queries. This makes it dramatically simpler to build tools against compared to X's undocumented internal GraphQL API with fragile cookie auth.

The tradeoff: Bluesky launched publicly in February 2024, so the archive is ~2.5 years deep instead of 18+. For most use cases — tracking brand mentions, product launches, or narrative origins — that's enough.

## Adding a skill

Skills live in their own directory under the repo root. Each needs:

- A `README.md` (what it does, how to use it)
- A `SKILL.md` (Hermes agent skill frontmatter)
- A `requirements.txt` (pip dependencies)
- A `.env.example` (environment template, even if unused)
- Scripts in `scripts/`

The root `README.md` skills table should be updated when a new skill is added.

## Porting from skills-for-x

Each skill in this repo is a port of the corresponding skill from [skills-for-x](https://github.com/jbrck/skills-for-x). The binary-chop algorithm is platform-agnostic and ports cleanly. The API surface is cleaner on Bluesky.

## License

Skills in this repo are individually licensed. Check each skill's `SKILL.md` for its license.

## Attribution

Built by [Justin Brock](https://github.com/jbrck). Not affiliated with Bluesky.