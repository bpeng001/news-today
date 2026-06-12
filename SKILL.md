---
name: news-today
description: Create, update, run, or troubleshoot a reusable daily news digest for specific topics that fetches open RSS/Atom metadata from government sources and curated top newspapers only, filters by English or Chinese topic keywords, archives Markdown digests, and sends daily Gmail summaries in English or Chinese. Use when the user asks for scheduled government/top-newspaper news monitoring, daily topic news alerts, English/Chinese news digests, policy or current-affairs news summaries, or automated Gmail news updates.
---

# News Today

## Overview

Use this skill to build a user's daily topic-specific news digest from trusted open feeds. The bundled script gathers RSS/Atom metadata and summaries only; Codex writes the analysis, saves the archive, sends email through Gmail when connected, and creates or updates the recurring automation.

Do not scrape arbitrary websites, social media, blogs, newsletters, or search-result pages during unattended runs. Do not bypass paywalls or auto-login to newspaper sites. Full-article follow-up is a separate explicit task using open pages, user-supplied PDFs, or an active browser session the user already opened.

## Core Workflow

1. Confirm or infer settings:
   - Recipient email.
   - Digest language. If the user says "Use Chinese", set `language` to `zh-CN` and write the Markdown archive and email body in Chinese.
   - Timezone and daily schedule.
   - Workspace path and Python command.
   - Topic scope, with English and/or Chinese keyword groups.
   - Source policy: only `government` and `top_newspaper` source types.
   - Approved feed list. Prefer official RSS/Atom feeds from government agencies and curated top newspapers.
2. Copy `scripts/news_today.py` into the user's workspace.
3. Create `news-today.config.json` in the workspace. Use `references/starter-config.md` as the starting point and replace the example user values.
4. Run a validation fetch:
   ```bash
   python scripts/news_today.py --config news-today.config.json fetch --include-seen
   ```
5. Read the printed JSON path and write the Markdown archive to `news-today-digests/YYYY-MM-DD.md`.
6. If records have only a title and no feed summary, keep them title-level and state that no article body was read.
7. Send email through Gmail when available. If Gmail is unavailable, do not ask for SMTP credentials; record `not-configured`.
8. Mark success only after the Markdown archive exists:
   ```bash
   python scripts/news_today.py --config news-today.config.json mark-success --data-file <JSON_PATH> --digest-file <DIGEST_PATH> --email-status <sent|failed|not-configured>
   ```
9. Create or update a Codex cron automation at the user's local time.

## Source Rules

Use strict source admission:

- `government`: official government department, agency, regulator, legislature, court, central bank, public-health authority, or multilateral organization feed.
- `top_newspaper`: curated major newspaper or equivalent high-reputation newsroom feed, such as The New York Times or other user-approved top papers.

Reject or remove:

- Blogs, Substack/newsletters, corporate marketing pages, social media, forums, YouTube channels, unknown local outlets, SEO aggregators, and search pages.
- Newspaper-like sources that are not in `top_newspaper_domains` or explicitly approved in `sources[]`.
- Items that only match because the feed name is broad but the item title/summary/categories do not support the user's topic.

The script enforces allowed source types and top-newspaper domains. Codex should keep the digest even stricter during final selection.

## Search Rules

Use two complementary filter modes:

- **Standalone topic keywords**: Match every term in `keyword_groups[].terms` against item title, feed summary/content, and categories.
- **Topic-plus-keyword combinations**: For each `topic_keyword_groups[]`, keep an item only when metadata visibly contains evidence for both the topic side and the keyword side.

English and Chinese terms can coexist in the same config. For Chinese, include concrete phrases and entity names because unattended feed matching uses literal substring checks rather than semantic search.

Example:

```json
{
  "label": "AI governance + regulation",
  "topic_label": "AI governance",
  "topic_terms": ["AI governance", "artificial intelligence governance", "人工智能治理"],
  "keyword_label": "regulation",
  "keyword_terms": ["regulation", "regulatory", "监管", "法规"]
}
```

## Selection Rules

Treat matching as inclusive during fetch, but strict during final selection.

Include a news item in the main digest only when it passes the configured policy:

- Source type is `government` or `top_newspaper`.
- `top_newspaper` sources match `top_newspaper_domains` unless explicitly configured and justified.
- `relevant_only`: remove weak, query-only, source-only, and off-topic records.
- `require_direct_keyword_match`: require title, summary, content snippet, or categories to show topic evidence.
- `minimum_relevance_score`: enforce the configured score threshold.
- `require_recent_date`: prefer items with a parsed feed date inside the configured lookback window.

If no items pass, still write and send a concise no-results digest. Do not relax the filters silently.

## Summary Rules

Use only feed metadata: title, source, source type, date, link, summary/content snippet, categories, matched keywords, and open feed metadata in the JSON. Do not infer facts from the headline alone.

Write the digest and Gmail body in the configured language:

- `en`: English.
- `zh-CN`, `zh`, or "Chinese": Simplified Chinese.

When writing in Chinese, translate interpretation fields, section headings, relevance assessment, and next actions into Chinese. Keep source names, article titles, URLs, and exact quoted metadata unchanged unless a conventional Chinese name is obvious.

For each included item, report:

- Title.
- Source, source type, date, and link.
- Matched keyword group or topic-keyword group.
- Priority and relevance.
- What happened, why it matters for the user's topic, confidence/limitations, and suggested follow-up.

For title-only records, do not infer what happened or why it matters. State: `No feed summary/full text was available; this is a title-level judgment only.`

Mention source fetch errors in the digest and summarize any successfully fetched results.

## Automation Prompt Requirements

The automation prompt must include:

- Exact workspace path and Python command.
- Exact config path.
- Exact fetch command using `--config`.
- Recipient email, language, schedule time, timezone, and output directory.
- Explicit instruction to write the Markdown archive and Gmail email body in the configured language, including Chinese when requested.
- Original user topic and keywords, and a note that expanded terms live in `keyword_groups`.
- Approved source policy: government and curated top newspapers only.
- Topic-keyword combination instructions when `topic_keyword_groups` is configured.
- Instruction to summarize open feed metadata/snippets only.
- Instruction to use Gmail connector if available.
- Instruction to call `mark-success` with `sent`, `failed`, or `not-configured`.
- Warning that local Codex automations may not run if the computer is asleep or the local runner is not active.

For daily 09:00:

```text
FREQ=DAILY;BYHOUR=9;BYMINUTE=0;BYSECOND=0
```

## Full-Article Follow-Up

When the user asks to read full articles:

- Do not ask for passwords.
- Use only open-access pages, the current active browser/session, or files supplied by the user.
- Process only the explicit batch/list requested by the user.
- Save summaries to `news-today-digests/fulltext-summaries/YYYY-MM-DD-fulltext.md`.
- Do not create unattended newspaper-download or paywall-bypass automation.

## Resources

- `scripts/news_today.py`: deterministic fetch/state script for trusted RSS/Atom feeds.
- `references/starter-config.md`: reusable starter config with government/top-newspaper source policy, English/Chinese keyword examples, and source examples.
