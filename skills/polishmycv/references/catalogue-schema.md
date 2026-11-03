# docs/portfolio-catalogue.json — schema (catalogue_version 1.1)

```
{
  "catalogue_version": "1.1",
  "generated": "YYYY-MM-DD",                 // set by build_catalogue.py
  "source": "https://davidgadyan.com/ (site content extracted from the published pages)",
  "purpose": "…",
  "profile": { … },                          // see below
  "counts": {"projects": 37, "needs_curation": 0},
  "themes": ["…"],                           // sorted union of project themes
  "index_by_theme":    {"<theme>": ["project-35", …]},     // ordered by count desc, then name
  "index_by_industry": {"<industry>": [ids]},
  "index_by_domain":   {"<domain>": [ids]},
  "index_by_skill":    {"<skill>": [ids]},   // every skill; the .md lists only those with >1 project
  "projects": [ … ]                          // newest first (date desc, then id number desc)
}
```

## Project entry

| Field | Source | Meaning |
|---|---|---|
| `id` | site | `project-<n>` from the URL |
| `title` | curated | Display title. Defaults to the site heading; override only to fix a typo |
| `site_title` | site | The literal `<h1>` on the page (what the diff compares against) |
| `date` | site | ISO date from the sidebar (falls back to the RSS pubDate) |
| `url` | site | Portfolio page, host lower-cased |
| `client` | site | Sidebar "Client" row, or null |
| `listed` | site | false for pages that are live but absent from the feed/sitemap |
| `summary` | curated | One sentence, ≤ 30 words |
| `themes` | curated | 1–3 from the fixed list below |
| `industries` | curated | 1–2 |
| `domains` | curated | 2–5 capability tags |
| `skills` | curated | Concrete tools/techniques named in the text |
| `site_tags` | site | Sidebar "Categories" |
| `role` | curated | What David did |
| `outcomes` | curated | 2–5 factual bullets; numbers verbatim |
| `cv_bullet` | curated | One CV-ready sentence, ≤ 45 words |
| `links` | site + curated | Sidebar link rows (label/url) first, then curated extras |
| `notes` | site + curated | Odd sidebar rows and any caveats |
| `image` | site | Hero image URL |
| `source_text` | site | Page body as markdown — the evidence for every number |
| `also_published_as` | curated | URLs of duplicate pages folded into this entry |
| `needs_curation` | build | Present (true) only when built with `--allow-uncurated` |

## Fixed theme list

```
Agentic AI & LLM systems
Classical ML & predictive modelling
Computer vision
Data apps, dashboards & visualisation
Data engineering & web scraping
LLM fine-tuning & generative content
MLOps, cloud & deployment
Marketing analytics & growth
NLP & text analytics
Quantitative finance & trading
RAG & document intelligence
Recommender systems & matching
```

Industries in use: Marketing / B2B services · B2B / SME services · Finance & capital markets ·
Healthcare & insurance · Research & public sector · SaaS · Automotive · Consumer & leisure ·
Crypto & blockchain · E-commerce & retail · HR & recruitment · Legal & compliance ·
Real estate & construction · Advertising · B2B data / lead generation · Consumer mobile ·
Content & publishing · IoT & edge · Media & reporting · Productivity · Social media.
Reuse these names before inventing a new one.

## Profile

| Field | Source |
|---|---|
| `name`, `headline` | site JSON-LD (`jobTitle`) |
| `positioning`, `experience_years`, `location`, `education`, `previously`, `credentials`, `core_stack` | curated — edit in the JSON directly |
| `projects_delivered`, `long_term_clients`, `hours_worked` | site counters (`data-count`), rendered as "190+", "50+", "8,700+" |
| `services` | site service cards + curated extras |
| `knows_about`, `about_text`, `self_rated_skills_pct` | site |
| `testimonials` (name, role, quote) and `named_clients_and_references` | site testimonial carousel |
| `links` | site (portfolio, all_projects, cv_pdf, linkedin, github, book_a_call) |

## Curated-entry file for `build_catalogue.py --curated`

A JSON list. Each object has `id` plus any curated fields to set; `"drop": true` excludes a page.

```json
[
  {
    "id": "project-39",
    "summary": "…",
    "themes": ["Agentic AI & LLM systems"],
    "industries": ["SaaS"],
    "domains": ["Agents", "MCP"],
    "skills": ["LangGraph", "FastAPI", "PostgreSQL"],
    "role": "Sole engineer — design, build, deployment",
    "outcomes": ["…", "…"],
    "cv_bullet": "Built … cutting … from 3 days to 20 minutes.",
    "links": [{"label": "Referenced", "url": "https://github.com/…"}],
    "notes": [],
    "also_published_as": ["https://davidgadyan.com/portfolio/<duplicate-slug>/"]
  },
  {"id": "project-40", "drop": true}
]
```
