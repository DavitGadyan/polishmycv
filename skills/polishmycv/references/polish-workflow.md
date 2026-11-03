# polish — full workflow

The reader is a recruiter who spends ~7 seconds on the first pass and an ATS that counts
keyword hits. Both must find, in the first third of the page, the job's own words attached to
numbers. Everything below serves that.

## 0. Inputs and the output folder

```
K       = ~/.claude/skills/polishmycv/scripts
H       = $(python3 $K/home.py)                                 # repo with docs/ and output/
JD      = $ARGUMENTS after "polish" (text | file path | URL)   → save verbatim as $OUT/jd.txt
CV      = --cv <path> if given, else $H/docs/cv/base-cv.json
CAT     = $H/docs/portfolio-catalogue.json
OUT     = --out <dir> if given, else $H/output/<YYYY-MM-DD>-<company-slug>-<role-slug>/
```

- URL → fetch the page text (WebFetch, or the `firecrawl-scrape` skill for JS-heavy boards).
  If the result has no requirements section, ask David to paste the JD.
- `--cv` is a PDF → `pdftotext -layout <pdf> <OUT>/cv-source.txt`, then transcribe it into a
  `cv.json` with the same schema as `docs/cv/base-cv.json` (below). Keep every fact; do not
  polish yet.
- Catalogue `generated` older than 30 days, or missing → mention it and suggest
  `/polishmycv refresh`; continue with what is there.
- Company/role slugs: lowercase, hyphens, ≤ 30 chars each (e.g. `2026-09-20-meridian-health-senior-ml-engineer`).

## 1. Read the JD like the hiring manager wrote it

Write this down (it goes into `notes.md` later):

- **Role title & seniority** — the exact title is what the headline mirrors.
- **Industry / domain** — decides which project *industries* count as a bonus.
- **Must-haves** — hard skills and experience thresholds. Each one needs a bullet with evidence.
- **Nice-to-haves** — cover only if a chosen project happens to show them.
- **Responsibilities themes** — e.g. "own production LLM systems end to end" → pick projects
  where the catalogue `role` says sole/end-to-end.
- **Vocabulary** — the JD's spelling of tools and concepts (`PostgreSQL` vs `Postgres`,
  `LLM-powered`, `RAG`, `stakeholders`). Mirror it where it is true.
- **Soft signals** — "communicate trade-offs", "mentor", "work with clinicians" → pick
  projects whose text shows it (technical-lead role, documentation/replication packages,
  three consecutive contracts = client kept coming back).

## 2. Shortlist projects

Primary: semantic vector ranking over the **live** site (https://davidgadyan.com/).

```
python3 $K/site_index.py ensure      # 1. reindex only if the #portfolio count or sitemap slugs changed
# 2. jd_en.txt = one English requirement per line (translate French/Spanish JDs; the model is English-only)
python3 $K/vector_rank.py --index $H/docs/site-index --jd <OUT>/jd_en.txt --top 20 --json <OUT>/ranking_vector.json
# 3. secondary keyword check
python3 $K/select_projects.py --jd <OUT>/jd.txt --top 12 --json <OUT>/ranking.json
```

Pick from the vector top ranks. For data science / ML / analytics roles, lead with data science
and ML projects, not AI Marketing (GA4/SEO) work (David, 2026-11-03). Links must be the site's slug
URLs. In the keyword output, the "NO project evidence" list is what you must not claim. Then choose **3–6 projects** (4–5 is the usual sweet spot for one page):

1. Cover every must-have that David has evidence for; one strong project per must-have beats
   three weak ones.
2. Prefer projects with numbers in `outcomes` (marked `#` in the ranking).
3. Prefer recent (2024+) over old, unless an old one is the only evidence for a must-have.
4. Diversity: don't spend three bullets on the same theme; industry match is a tie-breaker,
   not a requirement.
5. Read the chosen project pages in full (scraped `text`, or catalogue `outcomes`/`source_text`):
   the numbers and the exact tools live there.

## 3. Write `cv.json`

Schema (same as `docs/cv/base-cv.json`; strings accept `**bold**`, `*italic*`, `[text](url)`, `\n`):

```json
{
  "name": "David Gadyan",
  "headline": "…",                       // one line, bold
  "photo": "docs/cv/headshot.png",
  "contact": [{"label": "Email", "text": "…", "url": "mailto:…"}, …],
  "summary": "…" | null,                  // 2 lines max, optional
  "sections": [
    {"title": "Professional Experience", "entries": [
       {"heading": "Upwork (Freelancer)", "subheading": "…", "right": "Yerevan, Armenia",
        "right_sub": "01/2018 – Present", "bullets": ["…"], "paragraph": null, "italic": false}]},
    {"title": "Education", "entries": [ … {"paragraph": "line one\nline two"} ]},
    {"title": "Languages & Technical Skills", "lines": [{"label": "…", "text": "…"}]},
    {"title": "Additional Information & Personal Projects", "italic": true, "bullets": ["…"]}
  ],
  "style": {"font_size_pt": 10, "line_height": 1.25, "margin_in": 0.5}
}
```

Section by section:

**Headline.** `<JD title> | <2–3 true descriptors>` — e.g.
`Senior Machine Learning Engineer | LLM & Agentic Systems | MLOps on AWS/Kubernetes`. ≤ 90 chars.
Keep the original's flavour (it listed roles separated by `|`), just lead with the job's title.

**Contact.** Keep all four lines from the base CV. Add the portfolio's "All projects" link
only if there is spare room.

**Summary (recommended, 2 lines).** Who + tenure + two or three proof points that answer the
must-haves, each with a number, in JD vocabulary. Example for an LLM/healthcare role:
> Data scientist and AI engineer with 8 years, 180+ delivered projects and 50+ long-term clients
> (Upwork Expert-Vetted, top 1%). Ships production LLM systems — RAG, LangChain/LangGraph agents,
> MCP tool use — on AWS/Kubernetes, incl. a HIPAA-compliant underwriting assistant that cut
> turnaround from days to minutes.

**Professional Experience → Upwork entry.**
- `subheading`: the role name the JD would search for, kept true:
  `Data Scientist / ML Engineer (freelance consultant)`.
- Bullet 1 = scope: `8 years, 180+ projects for 100+ clients worldwide (50+ long-term);
  Upwork Expert-Vetted (top 1%), $500k+ earned, 8,700+ hours.`
- Then one bullet per chosen project, **ordered by relevance to the must-haves**, not by date:

  ```
  **[Project title](portfolio url)** — <verb> <what you built, naming the JD's tools> <, so/which> <outcome with the number>.
  ```
  Examples (all numbers from the catalogue):
  - `**[Virgil.ai — AI health-insurance assistant](https://davidgadyan.com/portfolio/virgil-ai-health-insurance-agent/)** — Built the agentic backend (LangChain + FastAPI + GPT, MCP tools, Docker/Kubernetes on AWS) that automates plan selection, medication-coverage lookup and underwriting under HIPAA controls, cutting underwriting from days to minutes.`
  - `**[Document OCR & data extraction](https://davidgadyan.com/portfolio/document-ocr-extraction-api/)** — Replaced manual entry of driver licences and insurance cards at a healthcare booking platform with an AWS Textract + regex REST API after benchmarking YOLO/NLP alternatives; per-image latency ~10 s → under 5 s.`
  - `**[Crypto regulation RAG assistant](https://davidgadyan.com/portfolio/crypto-regulation-rag-chatbot/)** — Shipped a LangChain + GPT-4 + Pinecone RAG chatbot over multi-jurisdiction regulation with OCR ingestion of scanned PDFs, sub-second retrieval and inline citations, delivered with Docker config and deployment scripts.`

  Rules for these bullets:
  - Start with the linked bold title, then a past-tense verb (Built, Shipped, Architected,
    Productionised, Led, Cut, Automated). No "I", no "responsible for".
  - Use the JD's exact tool names when the project genuinely used them; don't add tools the
    project did not use just because the JD lists them.
  - End on the number or the concrete before/after. If the catalogue has none, quantify scope
    (`3 consecutive contracts`, `millions of Indeed pages`, `hundreds of lot-and-style
    scenarios`, `4 ingestion formats`) — those are also in the text.
  - ≤ 2 rendered lines (≈ 230 characters at 10pt). Cut adjectives before cutting facts.
  - Keep `~` / "around" where the source hedges (e.g. "~84% R²").

**Professional Experience → Ernst & Young.** Keep it — a Big-4 stint reads as rigour and it
closes the timeline. One or two bullets, e.g. `Tax compliance and internal-control reviews for
clients with ~$10M turnover; 3+ concurrent engagements.` Drop to one line if space is tight;
drop it entirely only if the JD is unrelated to finance *and* the page will not fit.

**Education.** Both degrees. "Relevant courses" may be reordered to lead with the JD's topics
but only from what the base CV lists (Computational Machine Learning, Data Visualization,
Deep Learning) — do not add courses.

**Languages & Technical Skills.** Keep the languages line. Replace the single technical-skills
line with 3–4 labelled lines that mirror the JD's own grouping, listing only tools evidenced in
the catalogue or base CV, must-haves first, JD spelling:
```
LLM & agents: LangChain, LangGraph, RAG (Pinecone), MCP, OpenAI/Gemini/Claude APIs, n8n, HuggingFace fine-tuning (Mistral 7B)
ML & CV: XGBoost, scikit-learn, BERT, LSTM, U-Net, YOLO, Stable Diffusion, PCA/clustering
Data & infra: Python, SQL (PostgreSQL, MySQL, BigQuery), FastAPI, Docker, Kubernetes, AWS, GCP
Compliance: HIPAA-controlled data handling, GDPR
```
(the base CV wrote "HIPPA" and "SOC20" — correct the spelling to HIPAA; only keep SOC 2 if David
confirms it, otherwise leave it out.)

**Additional Information & Personal Projects.** Keep the Expert-Vetted/Toptal line. Keep the
crypto trading strategy only for quant/finance roles and ImprovTalk only for mobile/consumer
roles; otherwise this section is the first thing to drop for space.

**What never changes:** name, contact details, employers, dates, degrees. Tailoring is about
selection and wording, not biography.

## 4. Render, fit, look

```
python3 $K/render_cv.py --cv <OUT>/cv.json \
    --out "<OUT>/David_Gadyan_CV_<Company>.pdf" --fit --png
```

- Exit 2 (does not fit at 9pt): trim in this order — personal projects → EY to one line →
  shorten the two longest project bullets → drop the least relevant project → drop the summary.
  Re-run. Never go below 9pt; a cramped page reads worse than one fewer bullet.
- `last_page_fill` < 0.85: there is room — add the summary back, or one more project bullet, or
  a nice-to-have skill line. 0.88–0.99 is the target.
- `links_in_pdf` should equal contact links + project links; if it is lower, a `[title](url)`
  is malformed (no spaces inside the parentheses, `https://` prefix).
- Then **Read the `.preview.png`** and check: headline on one line, right column (location /
  dates) aligned, no bullet ending with a lone word on its own line, photo present, section
  rules unbroken. Fix in `cv.json` and re-render; two or three passes is normal.

## 5. notes.md

```markdown
# <Company> — <Role>  (<date>)
JD source: <url or "pasted">

## Requirement → evidence
| Requirement (JD wording) | Evidence on the CV | Status |
|---|---|---|
| LangChain/LangGraph in production | Virgil.ai, Gemini LangGraph agent bullets | strong |
| pgvector | — (Pinecone used instead) | partial |
| SageMaker | — | gap |

## Projects used (with links)  · why each one
## Changes vs base CV  · headline, summary added, bullets replaced, skills regrouped, dropped X
## Gaps to prepare for  · honest list for the interview
```

## 6. Report to David

Paths (PDF, preview, notes), the 3–6 projects chosen and why, the keyword gaps, and one
question if a claim needs his confirmation (e.g. SOC 2, a client name that may be under NDA).
Offer to swap projects or change the emphasis — that is a one-line edit to `cv.json` and a
re-render.
