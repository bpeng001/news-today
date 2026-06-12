# Starter Configuration

Use this as the default shape for `news-today.config.json`. Replace user-specific values before running.

```json
{
  "recipient_email": "user@example.com",
  "language": "en",
  "timezone": "America/New_York",
  "schedule_time": "09:00",
  "output_dir": "news-today-digests",
  "lookback_hours": 36,
  "max_items": 25,
  "relevant_only": true,
  "minimum_relevance_score": 2,
  "require_direct_keyword_match": true,
  "require_recent_date": false,
  "allowed_source_types": [
    "government",
    "top_newspaper"
  ],
  "top_newspaper_domains": [
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
    "people.com.cn"
  ],
  "sources": [
    {
      "key": "white-house",
      "display": "The White House",
      "source_type": "government",
      "language": "en",
      "country": "US",
      "url": "https://www.whitehouse.gov/briefing-room/feed/"
    },
    {
      "key": "hhs-news",
      "display": "U.S. Department of Health and Human Services",
      "source_type": "government",
      "language": "en",
      "country": "US",
      "url": "https://www.hhs.gov/rss/news.xml"
    },
    {
      "key": "nytimes-world",
      "display": "The New York Times - World",
      "source_type": "top_newspaper",
      "language": "en",
      "country": "US",
      "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
    },
    {
      "key": "nytimes-us",
      "display": "The New York Times - U.S.",
      "source_type": "top_newspaper",
      "language": "en",
      "country": "US",
      "url": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml"
    },
    {
      "key": "xinhua-world",
      "display": "Xinhua - World",
      "source_type": "top_newspaper",
      "language": "en",
      "country": "CN",
      "url": "https://english.news.cn/rss/world.xml"
    }
  ],
  "topic_keyword_groups": [
    {
      "label": "AI governance + regulation",
      "topic_label": "AI governance",
      "topic_terms": [
        "AI governance",
        "artificial intelligence governance",
        "人工智能治理"
      ],
      "keyword_label": "regulation",
      "keyword_terms": [
        "regulation",
        "regulatory",
        "监管",
        "法规"
      ]
    }
  ],
  "keyword_groups": [
    {
      "label": "AI policy",
      "terms": [
        "AI policy",
        "artificial intelligence policy",
        "AI regulation",
        "人工智能政策",
        "人工智能监管"
      ]
    },
    {
      "label": "public health policy",
      "terms": [
        "public health policy",
        "health regulation",
        "disease control",
        "公共卫生政策",
        "疾病防控"
      ]
    },
    {
      "label": "infectious disease",
      "terms": [
        "infectious disease",
        "communicable disease",
        "disease outbreak",
        "outbreak",
        "epidemic",
        "surveillance",
        "case count",
        "vaccination",
        "vaccine coverage",
        "transmission",
        "measles",
        "measles outbreak",
        "influenza",
        "flu",
        "seasonal flu",
        "avian flu",
        "H5N1",
        "RSV",
        "respiratory syncytial virus",
        "COVID-19",
        "SARS-CoV-2",
        "传染病",
        "感染性疾病",
        "疫情",
        "暴发",
        "流行病",
        "疾病监测",
        "病例",
        "疫苗接种",
        "疫苗覆盖率",
        "传播",
        "麻疹",
        "麻疹疫情",
        "流感",
        "季节性流感",
        "禽流感",
        "呼吸道合胞病毒",
        "新冠"
      ]
    }
  ]
}
```

Notes:

- `recipient_email`, `timezone`, and `schedule_time` are used by Codex when it sends the Gmail digest and creates the recurring automation.
- Keep `allowed_source_types` limited to `government` and `top_newspaper`.
- Use `sources[]` for official RSS/Atom feeds only. Verify feed URLs during setup; feeds change more often than source names.
- Government sources should be official agency, regulator, court, legislature, central bank, public-health, or multilateral feeds.
- Top-newspaper sources should be curated and must either match `top_newspaper_domains` or be explicitly added after the user approves the source.
- Set `language` to `en` for English or `zh-CN` for Simplified Chinese. When `zh-CN` is used, write the Markdown archive and email body in Chinese while preserving source metadata such as titles, source names, and URLs.
- Use English and Chinese terms together when the topic crosses languages. Literal Chinese phrases work better than broad single characters.
- Expand broad topics into concrete entities and subtopics before the first fetch. For example, `infectious disease` should include terms for measles, influenza/flu, avian flu, RSV, COVID-19, outbreaks, surveillance, vaccination, transmission, and Chinese equivalents.
- Keep `lookback_hours` wider than 24 when feeds publish across time zones.
- The fetch script does not send Gmail or create automations itself. Codex should use the Gmail connector and `automation_update` after the validation fetch and Markdown archive are complete.
