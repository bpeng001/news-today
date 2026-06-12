#!/usr/bin/env python3
"""Fetch daily trusted-source news candidates for Codex-authored digests.

This script intentionally does not call an LLM. It gathers open RSS/Atom
metadata and snippets, then writes a JSON payload for a Codex automation to
summarize.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


RECIPIENT_EMAIL = ""
LANGUAGE = "en"
TIMEZONE = ""
SCHEDULE_TIME = "09:00"
DEFAULT_OUTPUT_DIR = Path("news-today-digests")
DEFAULT_STATE_FILE = DEFAULT_OUTPUT_DIR / "state.json"

ALLOWED_SOURCE_TYPES = ["government", "top_newspaper"]
TOP_NEWSPAPER_DOMAINS = [
    "nytimes.com",
    "washingtonpost.com",
    "wsj.com",
    "ft.com",
    "theguardian.com",
    "economist.com",
    "reuters.com",
    "apnews.com",
    "scmp.com",
    "caixin.com",
    "news.cn",
    "xinhuanet.com",
    "people.com.cn",
]
SOURCES = [
    {
        "key": "white-house",
        "display": "The White House",
        "source_type": "government",
        "language": "en",
        "country": "US",
        "url": "https://www.whitehouse.gov/briefing-room/feed/",
    },
    {
        "key": "nytimes-world",
        "display": "The New York Times - World",
        "source_type": "top_newspaper",
        "language": "en",
        "country": "US",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    },
]
KEYWORD_GROUPS = [
    {
        "label": "AI policy",
        "terms": [
            "AI policy",
            "artificial intelligence policy",
            "AI regulation",
            "人工智能政策",
            "人工智能监管",
        ],
    }
]
TOPIC_KEYWORD_GROUPS: list[dict[str, Any]] = []
RELEVANT_ONLY = True
MINIMUM_RELEVANCE_SCORE = 2
REQUIRE_DIRECT_KEYWORD_MATCH = True
REQUIRE_RECENT_DATE = False

USER_AGENT_BASE = "CodexDailyNewsDigest/1.0"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def clean_text(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item)
    if not isinstance(value, str):
        return ""
    text = html.unescape(value)
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [clean_text(value) for value in values if clean_text(value)]


def read_config(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(path_value)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return read_json(path, {})


def int_setting(cli_value: int | None, config: dict[str, Any], key: str, default: int) -> int:
    if cli_value is not None:
        return cli_value
    value = config.get(key)
    if value is None:
        return default
    return int(value)


def float_setting(cli_value: float | None, config: dict[str, Any], key: str, default: float) -> float:
    if cli_value is not None:
        return cli_value
    value = config.get(key)
    if value is None:
        return default
    return float(value)


def configured_keyword_groups(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    groups: list[dict[str, Any]] = []
    for group in values:
        if not isinstance(group, dict):
            continue
        label = clean_text(group.get("label"))
        terms = clean_list(group.get("terms"))
        if label and terms:
            groups.append({"label": label, "terms": terms})
    return groups


def configured_topic_keyword_groups(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    groups: list[dict[str, Any]] = []
    for group in values:
        if not isinstance(group, dict):
            continue
        label = clean_text(group.get("label"))
        topic_label = clean_text(group.get("topic_label"))
        keyword_label = clean_text(group.get("keyword_label"))
        topic_terms = clean_list(group.get("topic_terms"))
        keyword_terms = clean_list(group.get("keyword_terms"))
        if label and topic_terms and keyword_terms:
            groups.append(
                {
                    "label": label,
                    "topic_label": topic_label,
                    "keyword_label": keyword_label,
                    "topic_terms": topic_terms,
                    "keyword_terms": keyword_terms,
                }
            )
    return groups


def configured_sources(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    sources: list[dict[str, Any]] = []
    for source in values:
        if not isinstance(source, dict):
            continue
        key = clean_text(source.get("key"))
        display = clean_text(source.get("display"))
        url = clean_text(source.get("url"))
        source_type = clean_text(source.get("source_type"))
        if not key or not display or not url or not source_type:
            continue
        sources.append(
            {
                "key": key,
                "display": display,
                "source_type": source_type,
                "language": clean_text(source.get("language")),
                "country": clean_text(source.get("country")),
                "url": url,
                "domain": clean_text(source.get("domain")),
            }
        )
    return sources


def apply_runtime_config(args: argparse.Namespace) -> None:
    config = read_config(getattr(args, "config", None))
    global RECIPIENT_EMAIL, LANGUAGE, TIMEZONE, SCHEDULE_TIME, SOURCES, KEYWORD_GROUPS
    global TOPIC_KEYWORD_GROUPS, ALLOWED_SOURCE_TYPES, TOP_NEWSPAPER_DOMAINS
    global RELEVANT_ONLY, MINIMUM_RELEVANCE_SCORE, REQUIRE_DIRECT_KEYWORD_MATCH, REQUIRE_RECENT_DATE

    RECIPIENT_EMAIL = clean_text(config.get("recipient_email"))
    LANGUAGE = clean_text(config.get("language")) or LANGUAGE
    TIMEZONE = clean_text(config.get("timezone")) or TIMEZONE
    SCHEDULE_TIME = clean_text(config.get("schedule_time")) or SCHEDULE_TIME

    allowed_types = clean_list(config.get("allowed_source_types"))
    if allowed_types:
        ALLOWED_SOURCE_TYPES = allowed_types
    domains = clean_list(config.get("top_newspaper_domains"))
    if domains:
        TOP_NEWSPAPER_DOMAINS = [domain.lower() for domain in domains]
    sources = configured_sources(config.get("sources"))
    if sources:
        SOURCES = sources
    keyword_groups = configured_keyword_groups(config.get("keyword_groups"))
    if keyword_groups:
        KEYWORD_GROUPS = keyword_groups
    TOPIC_KEYWORD_GROUPS = configured_topic_keyword_groups(config.get("topic_keyword_groups"))

    RELEVANT_ONLY = bool(config.get("relevant_only", RELEVANT_ONLY))
    MINIMUM_RELEVANCE_SCORE = int(config.get("minimum_relevance_score", MINIMUM_RELEVANCE_SCORE))
    REQUIRE_DIRECT_KEYWORD_MATCH = bool(config.get("require_direct_keyword_match", REQUIRE_DIRECT_KEYWORD_MATCH))
    REQUIRE_RECENT_DATE = bool(config.get("require_recent_date", REQUIRE_RECENT_DATE))

    if args.command == "fetch":
        output_dir = args.output_dir or clean_text(config.get("output_dir")) or str(DEFAULT_OUTPUT_DIR)
        args.output_dir = output_dir
        args.state_file = args.state_file or clean_text(config.get("state_file")) or str(Path(output_dir) / "state.json")
        args.lookback_hours = int_setting(args.lookback_hours, config, "lookback_hours", 36)
        args.max_items = int_setting(args.max_items, config, "max_items", 25)
        args.sleep = float_setting(args.sleep, config, "sleep", 0.25)
    elif args.command == "mark-success":
        args.state_file = args.state_file or clean_text(config.get("state_file")) or str(DEFAULT_STATE_FILE)


def user_agent() -> str:
    if RECIPIENT_EMAIL:
        return f"{USER_AGENT_BASE} (mailto:{RECIPIENT_EMAIL})"
    return USER_AGENT_BASE


def http_text(url: str, *, retries: int = 3, delay: float = 0.6) -> str:
    headers = {"User-Agent": user_agent(), "Accept": "application/rss+xml,application/atom+xml,text/xml,*/*"}
    last_error: str | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code} for {url}"
            if exc.code in {429, 500, 502, 503, 504} and attempt < retries:
                retry_after = exc.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after and retry_after.isdigit() else delay * attempt
                time.sleep(sleep_for)
                continue
            raise RuntimeError(last_error) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(delay * attempt)
                continue
            raise RuntimeError(last_error) from exc
    raise RuntimeError(last_error or f"Failed to fetch {url}")


def parse_date(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None:
        iso_text = text.replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(iso_text)
        except ValueError:
            return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).isoformat()


def date_in_window(value: str, window_from: dt.datetime, window_until: dt.datetime) -> bool:
    if not value:
        return not REQUIRE_RECENT_DATE
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return not REQUIRE_RECENT_DATE
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    parsed = parsed.astimezone(dt.timezone.utc)
    return window_from <= parsed <= window_until


def source_domain(source: dict[str, Any]) -> str:
    configured = clean_text(source.get("domain")).lower()
    if configured:
        return configured
    parsed = urllib.parse.urlparse(clean_text(source.get("url")))
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def domain_matches(host: str, allowed_domain: str) -> bool:
    host = host.lower()
    allowed_domain = allowed_domain.lower()
    return host == allowed_domain or host.endswith("." + allowed_domain)


def is_government_domain(host: str) -> bool:
    government_suffixes = (
        ".gov",
        ".mil",
        ".gov.cn",
        ".gov.uk",
        ".gov.au",
        ".gc.ca",
        ".gouv.fr",
        ".go.jp",
        ".gov.sg",
        ".europa.eu",
    )
    government_domains = {"canada.ca", "who.int", "un.org", "worldbank.org", "imf.org", "oecd.org"}
    return any(host.endswith(suffix) for suffix in government_suffixes) or any(
        domain_matches(host, domain) for domain in government_domains
    )


def source_allowed(source: dict[str, Any]) -> tuple[bool, str]:
    source_type = clean_text(source.get("source_type"))
    if source_type not in ALLOWED_SOURCE_TYPES:
        return False, f"source_type '{source_type}' is not allowed"
    host = source_domain(source)
    if source_type == "government" and not is_government_domain(host):
        return False, f"government source host '{host}' is not an approved government/multilateral domain"
    if source_type == "top_newspaper" and not any(domain_matches(host, domain) for domain in TOP_NEWSPAPER_DOMAINS):
        return False, f"top_newspaper source host '{host}' is not in top_newspaper_domains"
    return True, ""


def child_text(element: ET.Element, path: str, namespaces: dict[str, str] | None = None) -> str:
    found = element.find(path, namespaces or {})
    if found is None:
        return ""
    return clean_text("".join(found.itertext()))


def rss_items(root: ET.Element, source: dict[str, Any]) -> list[dict[str, Any]]:
    channel = root.find("channel")
    if channel is None:
        return []
    items: list[dict[str, Any]] = []
    for item in channel.findall("item"):
        categories = [clean_text("".join(category.itertext())) for category in item.findall("category")]
        content_encoded = child_text(item, "content:encoded", CONTENT_NS)
        summary = child_text(item, "description")
        link = child_text(item, "link")
        guid = child_text(item, "guid")
        items.append(
            {
                "title": child_text(item, "title"),
                "link": link,
                "guid": guid,
                "published_at": parse_date(child_text(item, "pubDate") or child_text(item, "dc:date", {"dc": "http://purl.org/dc/elements/1.1/"})),
                "summary": summary,
                "content_snippet": content_encoded[:1000] if content_encoded else "",
                "categories": [item for item in categories if item],
                "source": source,
            }
        )
    return items


def atom_link(entry: ET.Element) -> str:
    fallback = ""
    for link in entry.findall("atom:link", ATOM_NS):
        href = clean_text(link.attrib.get("href"))
        rel = clean_text(link.attrib.get("rel")) or "alternate"
        if not href:
            continue
        if rel == "alternate":
            return href
        fallback = fallback or href
    return fallback


def atom_items(root: ET.Element, source: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        categories = [clean_text(category.attrib.get("term") or category.attrib.get("label")) for category in entry.findall("atom:category", ATOM_NS)]
        summary = child_text(entry, "atom:summary", ATOM_NS)
        content = child_text(entry, "atom:content", ATOM_NS)
        items.append(
            {
                "title": child_text(entry, "atom:title", ATOM_NS),
                "link": atom_link(entry),
                "guid": child_text(entry, "atom:id", ATOM_NS),
                "published_at": parse_date(child_text(entry, "atom:published", ATOM_NS) or child_text(entry, "atom:updated", ATOM_NS)),
                "summary": summary,
                "content_snippet": content[:1000] if content else "",
                "categories": [item for item in categories if item],
                "source": source,
            }
        )
    return items


def parse_feed(xml_text: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    tag = root.tag.lower()
    if tag.endswith("rss") or tag == "rss":
        return rss_items(root, source)
    if tag.endswith("feed"):
        return atom_items(root, source)
    return []


def text_blob(item: dict[str, Any]) -> tuple[str, str, str]:
    title = clean_text(item.get("title"))
    summary = clean_text(item.get("summary"))
    content = clean_text(item.get("content_snippet"))
    categories = " ".join(clean_list(item.get("categories")))
    return title.lower(), f"{summary} {content}".lower(), categories.lower()


def term_score(term: str, title_l: str, summary_l: str, categories_l: str) -> int:
    term_l = term.lower()
    score = 0
    if term_l in title_l:
        score += 4
    if term_l in summary_l:
        score += 2
    if term_l in categories_l:
        score += 1
    return score


def keyword_hits(item: dict[str, Any]) -> tuple[list[str], list[str], int]:
    title_l, summary_l, categories_l = text_blob(item)
    groups: list[str] = []
    terms: list[str] = []
    score = 0
    for group in KEYWORD_GROUPS:
        group_hit = False
        for term in group["terms"]:
            value = term_score(term, title_l, summary_l, categories_l)
            if value:
                score += value
                group_hit = True
                terms.append(term)
        if group_hit:
            groups.append(group["label"])
    for group in TOPIC_KEYWORD_GROUPS:
        topic_score = sum(term_score(term, title_l, summary_l, categories_l) for term in group["topic_terms"])
        keyword_score = sum(term_score(term, title_l, summary_l, categories_l) for term in group["keyword_terms"])
        if topic_score and keyword_score:
            groups.append(group["label"])
            score += topic_score + keyword_score + 3
            terms.extend([term for term in group["topic_terms"] if term.lower() in f"{title_l} {summary_l} {categories_l}"])
            terms.extend([term for term in group["keyword_terms"] if term.lower() in f"{title_l} {summary_l} {categories_l}"])
    unique_terms = sorted(set(terms), key=str.lower)
    return sorted(set(groups), key=str.lower), unique_terms, score


def priority_for(score: int, summary: str) -> str:
    if score >= 7 and summary:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def item_key(item: dict[str, Any]) -> str:
    source = item.get("source") or {}
    raw = clean_text(item.get("guid")) or clean_text(item.get("link")) or f"{clean_text(source.get('key'))}:{clean_text(item.get('title'))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def passes_selection(item: dict[str, Any], window_from: dt.datetime, window_until: dt.datetime) -> bool:
    if not date_in_window(clean_text(item.get("published_at")), window_from, window_until):
        return False
    if not RELEVANT_ONLY:
        return True
    if REQUIRE_DIRECT_KEYWORD_MATCH and not item.get("matched_groups"):
        return False
    return int(item.get("relevance_score", 0)) >= MINIMUM_RELEVANCE_SCORE


def normalized_candidate(item: dict[str, Any], window_from: dt.datetime, window_until: dt.datetime) -> dict[str, Any]:
    source = item.get("source") or {}
    groups, terms, score = keyword_hits(item)
    summary = clean_text(item.get("summary"))
    content_snippet = clean_text(item.get("content_snippet"))
    candidate = {
        "key": item_key(item),
        "title": clean_text(item.get("title")),
        "source": clean_text(source.get("display")),
        "source_key": clean_text(source.get("key")),
        "source_type": clean_text(source.get("source_type")),
        "source_language": clean_text(source.get("language")),
        "source_country": clean_text(source.get("country")),
        "source_url": clean_text(source.get("url")),
        "link": clean_text(item.get("link")),
        "guid": clean_text(item.get("guid")),
        "published_at": clean_text(item.get("published_at")),
        "summary": summary,
        "content_snippet": content_snippet,
        "categories": clean_list(item.get("categories")),
        "matched_groups": groups,
        "matched_terms": terms,
        "relevance_score": score,
        "priority": priority_for(score, summary or content_snippet),
        "metadata_match_confidence": "direct" if groups else "none",
        "title_level_only": not bool(summary or content_snippet),
        "within_window": date_in_window(clean_text(item.get("published_at")), window_from, window_until),
    }
    return candidate


def fetch_candidates(args: argparse.Namespace) -> Path:
    now = utc_now()
    window_until = now
    window_from = now - dt.timedelta(hours=args.lookback_hours)
    output_dir = Path(args.output_dir)
    state_file = Path(args.state_file)
    state = read_json(state_file, {"seen": {}, "successful_runs": []})
    seen = set((state.get("seen") or {}).keys())

    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    skipped_sources: list[dict[str, str]] = []
    seen_this_run: set[str] = set()

    for source in SOURCES:
        allowed, reason = source_allowed(source)
        if not allowed:
            skipped_sources.append({"source": clean_text(source.get("display")), "reason": reason})
            continue
        try:
            xml_text = http_text(clean_text(source.get("url")))
            feed_items = parse_feed(xml_text, source)
        except (RuntimeError, ET.ParseError, ValueError) as exc:
            errors.append({"source": clean_text(source.get("display")), "url": clean_text(source.get("url")), "error": str(exc)})
            continue
        for raw_item in feed_items:
            candidate = normalized_candidate(raw_item, window_from, window_until)
            if not candidate["title"]:
                continue
            if candidate["key"] in seen_this_run:
                continue
            seen_this_run.add(candidate["key"])
            if not args.include_seen and candidate["key"] in seen:
                continue
            if passes_selection(candidate, window_from, window_until):
                candidates.append(candidate)
        if args.sleep:
            time.sleep(args.sleep)

    candidates.sort(key=lambda item: (item.get("published_at") or "", item.get("relevance_score") or 0), reverse=True)
    candidates = candidates[: args.max_items]

    payload = {
        "generated_at": now.isoformat(),
        "window": {
            "from": window_from.isoformat(),
            "until": window_until.isoformat(),
            "lookback_hours": args.lookback_hours,
        },
        "settings": {
            "recipient_email": RECIPIENT_EMAIL,
            "language": LANGUAGE,
            "timezone": TIMEZONE,
            "schedule_time": SCHEDULE_TIME,
            "allowed_source_types": ALLOWED_SOURCE_TYPES,
            "top_newspaper_domains": TOP_NEWSPAPER_DOMAINS,
            "relevant_only": RELEVANT_ONLY,
            "minimum_relevance_score": MINIMUM_RELEVANCE_SCORE,
            "require_direct_keyword_match": REQUIRE_DIRECT_KEYWORD_MATCH,
            "require_recent_date": REQUIRE_RECENT_DATE,
            "keyword_groups": KEYWORD_GROUPS,
            "topic_keyword_groups": TOPIC_KEYWORD_GROUPS,
        },
        "source_count": len(SOURCES),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "errors": errors,
        "skipped_sources": skipped_sources,
        "notes": [
            "Only open RSS/Atom metadata and snippets were fetched.",
            "No paywalled article body or login-protected content was read.",
            "Government and curated top-newspaper source policy was enforced before filtering.",
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"news-candidates-{now.strftime('%Y%m%d-%H%M%S')}.json"
    write_json(output_path, payload)
    print(output_path)
    return output_path


def mark_success(args: argparse.Namespace) -> None:
    state_file = Path(args.state_file)
    state = read_json(state_file, {"seen": {}, "successful_runs": []})
    data = read_json(Path(args.data_file), {})
    seen = state.setdefault("seen", {})
    now = utc_now().isoformat()
    for item in data.get("candidates", []):
        key = clean_text(item.get("key"))
        if not key:
            continue
        seen[key] = {
            "title": clean_text(item.get("title")),
            "source": clean_text(item.get("source")),
            "link": clean_text(item.get("link")),
            "first_seen_at": seen.get(key, {}).get("first_seen_at", now),
            "last_digest_file": args.digest_file,
        }
    state.setdefault("successful_runs", []).append(
        {
            "timestamp": now,
            "data_file": args.data_file,
            "digest_file": args.digest_file,
            "email_status": args.email_status,
            "candidate_count": len(data.get("candidates", [])),
        }
    )
    state["successful_runs"] = state["successful_runs"][-100:]
    write_json(state_file, state)
    print(state_file)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch trusted-source news candidates for a daily digest.")
    parser.add_argument("--config", help="Path to news-today.config.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch candidate news items and write JSON.")
    fetch.add_argument("--output-dir")
    fetch.add_argument("--state-file")
    fetch.add_argument("--lookback-hours", type=int)
    fetch.add_argument("--max-items", type=int)
    fetch.add_argument("--sleep", type=float)
    fetch.add_argument("--include-seen", action="store_true")

    success = subparsers.add_parser("mark-success", help="Update state after a digest is generated.")
    success.add_argument("--state-file")
    success.add_argument("--data-file", required=True)
    success.add_argument("--digest-file", required=True)
    success.add_argument("--email-status", choices=["sent", "failed", "not-configured"], required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply_runtime_config(args)
    if args.command == "fetch":
        fetch_candidates(args)
    elif args.command == "mark-success":
        mark_success(args)
    else:
        parser.error(f"Unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
