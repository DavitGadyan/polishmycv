# polishmycv

A Claude Code skill that tailors David Gadyan's CV to a specific job — the right portfolio
projects, quantified bullets, one page, clickable links — and keeps the project catalogue it
draws from in sync with [davitgadyan.github.io/portfolio_app](https://davitgadyan.github.io/portfolio_app/).

```
/polishmycv polish <job description | path/to/jd.txt | https://job-url>   [--cv <pdf|json>] [--out <dir>]
/polishmycv refresh
```

| Command | What it does |
|---|---|
| `polish` | Reads the job post, ranks the 37+ catalogued projects against it, picks the 3–6 that prove the must-haves, rewrites the CV around them (every number sourced from the portfolio or the original CV), renders a one-page PDF with the headshot and links, and writes a `notes.md` with requirement → evidence → gaps. Output lands in `output/<date>-<company>-<role>/`. |
| `refresh` | Scrapes the portfolio site (RSS + sitemap + every project page + home-page counters and testimonials), diffs it against `docs/portfolio-catalogue.json`, has Claude curate only the new/changed projects (summary, themes, outcomes, CV bullet), rebuilds both catalogue files and re-downloads the original CV PDF. Unchanged projects keep their curated wording. |

## Installation

The skill source lives in this repo at `skills/polishmycv/`. Install it **globally** (available in
every Claude Code session on the machine) by symlinking it into `~/.claude/skills/` — a symlink,
so `git pull` in this repo updates the installed skill:

```bash
git clone https://github.com/DavitGadyan/polishmycv.git ~/Desktop/Github/polishmycv   # or wherever you keep it
cd ~/Desktop/Github/polishmycv

mkdir -p ~/.claude/skills
ln -sfn "$(pwd)/skills/polishmycv" ~/.claude/skills/polishmycv

pip install -r skills/polishmycv/requirements.txt      # requests, beautifulsoup4, lxml, jinja2, markupsafe, pypdf
brew install poppler                                   # pdftotext / pdftoppm / pdfimages (macOS; apt: poppler-utils)
```

Google Chrome renders the PDF (headless, already installed on most Macs). Without Chrome,
`pip install playwright && playwright install chromium` gives the renderer a fallback.

Verify: start a new Claude Code session anywhere and type `/polishmycv` — it prints the usage.
`python3 ~/.claude/skills/polishmycv/scripts/home.py --check` confirms the skill can find this
repo's `docs/` (it resolves `$POLISHMYCV_HOME`, then the nearest parent of the cwd containing
`docs/portfolio-catalogue.json`, then the repo the symlink points into).

Prefer a project-only install? Copy or symlink the same folder to `<repo>/.claude/skills/polishmycv`
instead; it then only loads inside that repo.

Prefer a copy over a symlink? `cp -R skills/polishmycv ~/.claude/skills/polishmycv` works too, and
`POLISHMYCV_HOME=/path/to/this/repo` in your shell profile tells it where `docs/` is.

## Repository layout

```
docs/
  portfolio-catalogue.json    curated catalogue of portfolio projects + profile stats (source of truth for polish)
  portfolio-catalogue.md      the same, readable, with indexes by theme / industry / skill  (generated)
  cv/
    David_Gadyan_Resume4.pdf  original CV as published on the site (+ .txt extraction)
    base-cv.json              structured transcription of it — the default reference polish starts from
    headshot.png              photo extracted from the PDF, embedded in every tailored CV
output/
  <date>-<company>-<role>/    one folder per application: jd.txt, cv.json, PDF, HTML, preview PNG, notes.md
skills/polishmycv/
  SKILL.md                    the skill (what Claude reads)
  references/                 polish-workflow.md · refresh-workflow.md · catalogue-schema.md
  scripts/                    fetch_portfolio · diff_catalogue · build_catalogue · select_projects · render_cv · home
  assets/cv-template.html     HTML/CSS template that mirrors the original CV layout
  requirements.txt
```

## How a tailored CV is built

1. The JD is saved verbatim; role, must-haves, nice-to-haves and vocabulary are extracted.
2. `select_projects.py` scores every catalogue project (keyword overlap weighted by field, recency,
   whether outcomes already carry numbers) and prints the JD terms that have **no** evidence — those
   are never claimed.
3. Claude writes `cv.json`: headline mirrors the JD title, a two-line summary, one scope bullet with
   the platform stats (8 years, 180+ projects, 50+ long-term clients, top 1%, 8,700+ hours), one
   linked bullet per chosen project (`**[Title](portfolio url)** — verb + what/tech + outcome with
   number`), skills regrouped in the JD's categories using only evidenced tools.
4. `render_cv.py --fit --png` renders HTML → PDF in headless Chrome, shrinks type only between
   10pt and 9pt, and fails loudly if the content still doesn't fit — content is cut, not squeezed.
   The preview PNG is checked for wrapped headlines and orphan lines.
5. `notes.md` records requirement → evidence → status and the honest gaps to prepare for.

## Rules the skill follows

- Every number traces to the portfolio catalogue (`outcomes` / `source_text` / profile counters) or
  the original CV. No invented percentages.
- One page, Letter, Arial 9–10.5pt, headshot top-right — the original CV's layout.
- Names, employers, dates and degrees never change; tailoring is selection and wording.
- `refresh` never publishes an uncurated project (`build_catalogue.py` exits 2 until every live
  project has a summary, themes and a CV bullet), and it never rewrites curated text for projects
  whose page did not change.
