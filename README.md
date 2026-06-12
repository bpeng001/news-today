# News Today

`news-today` is a Codex skill for building a reusable daily topic-specific news digest from trusted sources only. It fetches open RSS/Atom metadata, filters by English or Chinese keywords, writes a local Markdown archive, sends the digest through the Codex Gmail connector, and creates a recurring Codex automation.

It is designed for English or Chinese digests and restricts unattended fetching to:

- official government, regulator, legislature, court, central bank, public-health, or multilateral feeds
- curated top newspaper feeds, such as The New York Times and other explicitly approved major outlets

The skill does not scrape arbitrary websites, social media, blogs, newsletters, or paywalled article bodies.

## What It Does

- Runs a daily news digest at your chosen local time.
- Reads official RSS/Atom feeds from government sources and curated top newspapers only.
- Supports English and Chinese keyword groups.
- Expands broad topics into concrete keywords before fetching, such as turning `infectious disease` into measles, influenza/flu, avian flu, RSV, COVID-19, outbreak, surveillance, vaccination, transmission, and Chinese equivalents.
- Supports topic-plus-keyword combinations, such as `AI governance && regulation` or `人工智能治理 && 监管`.
- Summarizes only open feed metadata and snippets during unattended runs.
- Writes and emails the digest in English or Chinese.
- Writes local archives under `news-today-digests/`.
- Sends the concise digest through the Codex Gmail connector when Gmail is connected.
- Creates or updates the recurring local Codex automation.

## Contents

- `SKILL.md`: skill instructions and operating rules
- `agents/openai.yaml`: Codex UI metadata
- `references/starter-config.md`: example `news-today.config.json`
- `scripts/news_today.py`: RSS/Atom fetch and state helper

## Basic Usage

After installing the skill and connecting Gmail, ask Codex something like:

```text
Use $news-today to create a daily topic news digest.
Send it to me@example.com every day at 09:00.
Use English/Chinese.
Only use government sources and top newspapers.
My topic is AI governance and regulation.
Include English and Chinese keywords.
```

For example, if your topic is infectious disease, Codex should not search only the exact phrase `infectious disease`. It should expand the config with terms such as `measles`, `measles outbreak`, `influenza`, `flu`, `avian flu`, `RSV`, `COVID-19`, `outbreak`, `surveillance`, `vaccination`, `transmission`, `麻疹`, `流感`, `禽流感`, `疫情`, `疫苗接种`, and `传播`.

Codex will:

1. Copy `scripts/news_today.py` into your workspace.
2. Create `news-today.config.json`.
3. Run an initial validation fetch.
4. Write the first Markdown digest.
5. Send the digest by Gmail if connected.
6. Create the recurring local Codex automation.

For manual testing, create a workspace config from `references/starter-config.md`, then run:

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

Broad topics should be expanded in `keyword_groups[].terms`; the script performs literal feed matching, so concrete disease names, agencies, places, abbreviations, and Chinese phrases are important.

## Connect Gmail

In Codex, connect the Gmail app/connector for the account that should send the digest. This skill uses Gmail connector tools only; it does not ask for SMTP credentials, Gmail app passwords, or account passwords.

If Gmail is not connected, Codex should still write the Markdown archive and mark the run with `email-status` set to `not-configured`.

## Automation Caveat

Codex local automations depend on your local Codex runner/environment. If your computer is asleep, shut down, offline, or the local automation runner is not active at the scheduled time, the digest may not run until the environment is available again.
