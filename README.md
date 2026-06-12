# News Today

`news-today` is a Codex skill for building a daily topic-specific news digest from trusted sources only.

It is designed for English or Chinese digests and restricts unattended fetching to:

- official government, regulator, legislature, court, central bank, public-health, or multilateral feeds
- curated top newspaper feeds, such as The New York Times and other explicitly approved major outlets

The skill does not scrape arbitrary websites, social media, blogs, newsletters, or paywalled article bodies.

## Contents

- `SKILL.md`: skill instructions and operating rules
- `agents/openai.yaml`: Codex UI metadata
- `references/starter-config.md`: example `news-today.config.json`
- `scripts/news_today.py`: RSS/Atom fetch and state helper

## Basic Usage

Create a workspace config from `references/starter-config.md`, then run:

```bash
python scripts/news_today.py --config news-today.config.json fetch --include-seen
```

After Codex writes the Markdown digest, mark the run successful:

```bash
python scripts/news_today.py --config news-today.config.json mark-success \
  --data-file <JSON_PATH> \
  --digest-file <DIGEST_PATH> \
  --email-status <sent|failed|not-configured>
```

## Source Policy

Keep `allowed_source_types` limited to:

```json
["government", "top_newspaper"]
```

For `top_newspaper` feeds, the feed host must match `top_newspaper_domains` unless the source is explicitly reviewed and added.

## Language

Set `language` to:

- `en` for English
- `zh-CN` for Simplified Chinese

Chinese and English keywords can be mixed in `keyword_groups` and `topic_keyword_groups`.
