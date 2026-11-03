---
name: polishmycv
description: Tailor David Gadyan's CV to a specific job and keep his portfolio project catalogue fresh. Use `/polishmycv polish <job description | file | URL>` whenever David wants to apply for a role, tailor/adapt/customise/rewrite his CV or resume for a job, make it fit one page, make it more quantitative, or attach relevant portfolio projects to it — even if he just pastes a job post and says "make my CV fit this". Use `/polishmycv refresh` whenever he wants to update, sync, re-scrape or refresh the project catalogue / portfolio stats in docs/ from https://davidgadyan.com/ or re-download his original CV. Also trigger for "which of my projects fit this job", "update docs from my portfolio", or any CV/resume work for David.
---

# polishmycv

Two commands, one goal: a one-page CV that shows the *right* evidence for the job in front of it,
with every number traceable to David's portfolio site or his original CV.

```
/polishmycv polish <job description text | path/to/jd.txt | https://job-url>   [--cv <pdf|json>] [--out <dir>]
/polishmycv refresh
/polishmycv            → print the usage block at the bottom
```

`$ARGUMENTS` = everything after `/polishmycv`. The first word is the command. For `polish`, the
rest is the job: pasted text, a file path, or a URL (fetch it — WebFetch or `firecrawl-scrape`;
if the page is a JS app and comes back empty, ask David to paste the text).
No job given → ask for it; do not guess a role.

## Locations

The skill is installed globally (`~/.claude/skills/polishmycv` → symlink into the
`polishmycv` repo), so it can run from any directory. Two paths matter:

```
K = ~/.claude/skills/polishmycv/scripts          # the scripts (this skill's scripts/ dir)
H = $(python3 $K/home.py)                        # the data home = the repo with docs/ and output/
```
`home.py` resolves `$POLISHMYCV_HOME`, else the nearest parent of the cwd containing
`docs/portfolio-catalogue.json`, else the repo the skill is symlinked from. Run
`python3 $K/home.py --check` first; if it reports missing files, run `refresh` or ask David.

| Path (under `H`) | What | Written by |
|---|---|---|
| `docs/portfolio-catalogue.json` | 37+ portfolio projects, curated: summary, themes, skills, outcomes, ready `cv_bullet`, links; plus profile stats | `refresh` |
| `docs/portfolio-catalogue.md` | Same, human-readable, with indexes by theme / industry / skill | `refresh` (generated — never hand-edit) |
| `docs/cv/David_Gadyan_Resume.pdf` + `.txt` | The original CV as published on the site | `refresh` |
| `docs/cv/base-cv.json` | Structured transcription of that CV — the **default reference** `polish` starts from | hand-maintained; `refresh` flags it when the PDF changes |
| `docs/cv/headshot.png` | Photo extracted from the PDF, re-embedded in every tailored CV | `refresh` |
| `docs/site-index/` | Vector index of every live project (pages, chunks, embeddings, meta with count + slugs) | `site_index.py ensure` |
| `output/<date>-<company>-<role>/` | One folder per application: `jd.txt`, `cv.json`, the PDF, HTML, preview PNG, `notes.md` | `polish` |

Scripts (Python 3; `python3 $K/<name>.py --help` prints full usage):

| Script | Role |
|---|---|
| `home.py` | Print the data home (see above) |
| `fetch_portfolio.py` | Scrape the Hugo site (RSS + sitemap + every project page + home-page counters/testimonials) into raw JSON; also downloads the CV PDF |
| `diff_catalogue.py` | Raw scrape vs catalogue → which projects are new / changed / removed, with the raw records to curate |
| `build_catalogue.py` | Merge scrape + curated entries → rewrite both catalogue files, recompute indexes. Refuses to publish uncurated projects |
| `site_index.py` | `check` / `ensure`: compare the #portfolio count + sitemap slugs with `docs/site-index/`, re-scrape and re-embed all projects when they differ |
| `vector_rank.py` | **Primary ranking.** Embed project chunks + JD requirement lines (local `BAAI/bge-small-en-v1.5`) → semantic ranking with coverage/peak scores and the best project per requirement |
| `select_projects.py` | Secondary keyword ranking of catalogue projects (overlap, recency, has-numbers) and the JD terms with no evidence |
| `render_cv.py` | `cv.json` → HTML (template in `assets/`) → PDF via headless Chrome; `--fit` shrinks type within limits, reports pages, fill ratio, link count; `--png` preview |

Requirements: Python 3.10+ with `requests beautifulsoup4 lxml jinja2 markupsafe pypdf`
(`pip install -r $K/../requirements.txt`), Google Chrome (or `playwright` + chromium), and
poppler (`brew install poppler`) for `pdftotext` / `pdftoppm` / `pdfimages`.

## Ground rules (both commands)

1. **Every number is sourced.** Stats come from the catalogue profile (8 years, 190+ projects,
   50+ long-term clients, 8,700+ hours, Expert-Vetted top 1%, 100+ Upwork clients) or the base CV
   ($500k+ earnings, Toptal), and project metrics come from that project's `outcomes` /
   `source_text` (e.g. 84% R², 0/3 → 3/3 enquiry routes, underwriting days → minutes, <5s OCR).
   If a project has no metric, quantify its *scope* from the text (data sources, contracts,
   formats, jurisdictions, platforms) or leave it qualitative. Never invent a percentage — a
   recruiter who asks "how did you measure that?" must get a real answer.
2. **One page, Letter, 9–10.5pt.** Cut content before shrinking type; `render_cv.py --fit` stops
   at `--min-font 9` and returns exit 2 so you trim rather than squeeze.
3. **Projects carry links.** Each project bullet links its title to the portfolio page so the
   reader can verify it in one click (Chrome keeps the links clickable in the PDF).
4. **Site facts win, curation persists.** `refresh` overwrites dates, titles, tags, links, body
   text from the site, but keeps the curated summaries/bullets for unchanged projects so wording
   does not churn between refreshes.
5. Don't commit or push unless asked; report file paths at the end.

## polish — the short version

Read `references/polish-workflow.md` (next to this file) before doing this the first time in a
session; it has the bullet formula, the selection rules and the fit loop in detail. Outline:

0. **Always first: sync the portfolio index.** `python3 $K/site_index.py ensure`. This reads the
   project count on https://davidgadyan.com/#portfolio and the sitemap's project slugs, compares
   them with `$H/docs/site-index/meta.json`, and re-scrapes and re-embeds every project only if
   something changed. Report any NEW or REMOVED projects to David. A new project is a candidate for
   this CV, so it must take part in step 3.
1. Create `$H/output/<YYYY-MM-DD>-<company-slug>-<role-slug>/`, save the JD as `jd.txt`.
   Load `$H/docs/cv/base-cv.json` (or the `--cv` file — a PDF gets `pdftotext -layout` and a
   transcription into the same schema first).
2. Analyse the JD: role title, seniority, industry, must-haves, nice-to-haves, exact vocabulary.
3. **Vector-rank the indexed projects** (primary). Write one English requirement per line to
   `jd_en.txt` (translate a non-English JD; the model is English-only), then run
   `python3 $K/vector_rank.py --index $H/docs/site-index --jd jd_en.txt --top 20 --json ranking_vector.json`.
   `select_projects.py` (keyword, catalogue) is a secondary check only. Choose 3–6 projects from the
   vector top ranks that cover the must-haves. For data science / ML / analytics roles, lead with
   data science and ML projects, never with AI Marketing (GA4/SEO) work (David, 2026-11-03).
   Link only to the site's slug URLs (`https://davidgadyan.com/portfolio/<slug>/`), and read each
   chosen project's full `text` in `docs/site-index/projects.json` for facts and numbers.
4. Write `cv.json`: headline mirrors the JD title; 2-line summary with the top proof points;
   Upwork entry = one scope bullet (big numbers) + one bullet per chosen project
   (`**[Title](url)** — verb + what/tech in JD vocabulary + outcome with number`); EY kept short;
   skills regrouped in JD categories using only evidenced tools; personal projects only if relevant.
5. `python3 $K/render_cv.py --cv cv.json --out <dir>/David_Gadyan_CV_<Company>.pdf --fit --png`.
   Exit 2 → trim and re-run. Aim for `last_page_fill` 0.88–0.99. Then Read the preview PNG and fix
   anything that looks off (orphan words, misaligned right column, an over-long headline).
6. Write `notes.md` (requirement → evidence → strong/partial/gap; projects used with links;
   what changed vs the base CV; honest gaps to prepare for). Report paths + gaps to David.

## polish for an Upwork proposal (no contact details) — David, 2026-10-23

When the CV goes on an Upwork proposal (the job is an upwork.com link, or David says Upwork / "attach to
the proposal"), Upwork forbids contact details before a contract. Reference version:
https://davitgadyan.github.io/portfolio_app_upwork/CV_David_Gadyan_no_contact.pdf. Same steps as above, plus:

- `cv.json` `contact` is `[]`: no email, phone, LinkedIn, Upwork URL or personal-site link.
- Project title links point to `https://davitgadyan.github.io/portfolio_app_upwork/...` (the Upwork copy of
  the site), never `davidgadyan.com` (the main site shows the phone and LinkedIn). If unsure, drop the link.
- Name the file `CV_David_Gadyan_no_contact_<Company>.pdf`.
- Before handing it over: `pdftotext <pdf> - | grep -inE '@|\+?[0-9][0-9 ()-]{7,}|linkedin|wa\.me|t\.me|davidgadyan\.com'`
  must print nothing.
- David uploads it in Up Assistant (proposal → Files → Upload, then tick "When a post asks for a CV" for the
  default one). Up Assistant attaches the ticked CV by itself when a post asks for a CV, and blocks submitting
  a proposal on such a post without one.

## refresh — the short version

Read `references/refresh-workflow.md` for the curation rules and `references/catalogue-schema.md`
for the field definitions. Use the scratchpad for intermediates (`S`). Outline:

1. `python3 $K/fetch_portfolio.py --out $S/raw.json --cv-out $S/cv.pdf`
2. `python3 $K/diff_catalogue.py --raw $S/raw.json --catalogue $H/docs/portfolio-catalogue.json --out $S/refresh-diff.json`
3. For each **new** or **changed** project in the diff, write a curated entry (summary, themes
   from the fixed list, industries, domains, skills, role, outcomes with numbers verbatim,
   `cv_bullet`) into `$S/refresh-curated.json`. Duplicates (same hero image / body):
   keep the more complete page, fold the other URL into `also_published_as`.
4. `python3 $K/build_catalogue.py --catalogue $H/docs/portfolio-catalogue.json --raw $S/raw.json --curated $S/refresh-curated.json --out-json $H/docs/portfolio-catalogue.json --out-md $H/docs/portfolio-catalogue.md`
   (exit 2 lists projects still lacking curation — curate them, rerun). Run the diff again: it
   should now be clean.
5. If the downloaded CV's sha256 differs from `base-cv.json.source_pdf_sha256`: copy the PDF and
   its `pdftotext -layout` text into `$H/docs/cv/`, re-extract the headshot (`pdfimages -png`),
   re-transcribe `base-cv.json`, update the hash.
6. Report: new/changed/removed projects, the profile counters, and the catalogue date.

## Usage (print when called with no command)

```
/polishmycv polish <job description | file | URL> [--cv <pdf|json>] [--out <dir>]
    Tailor the CV to the job: relevant projects + numbers, one page, PDF in output/.
/polishmycv refresh
    Re-scrape https://davidgadyan.com/ into docs/ (catalogue + original CV).
```
