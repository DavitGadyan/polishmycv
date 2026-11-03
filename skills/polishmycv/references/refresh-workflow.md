# refresh — full workflow

Goal: `docs/portfolio-catalogue.{json,md}` and `docs/cv/` reflect what is on
https://davidgadyan.com/ *today*, while the curated wording for unchanged
projects stays exactly as it was (so a CV polished last month and one polished today pull the
same bullet for the same project).

Work in the scratchpad directory for intermediate files; only the four `docs/` artefacts are
outputs. Set `S=<scratchpad>`, `K=~/.claude/skills/polishmycv/scripts` and `H=$(python3 $K/home.py)` below;
every `docs/…` path is relative to `H`.

## 1. Scrape

```
python3 $K/fetch_portfolio.py --out $S/raw.json --cv-out $S/cv.pdf
```

What it pulls (all deterministic, no summarising):
- `portfolio/index.xml` (RSS) and `sitemap.xml` for the project list; then probes
  `project-<max+1..max+5>` for live-but-unlisted pages (project-38 was one).
- Per project page: `h1` title, hero image, body → markdown (`body_markdown`), sidebar Date /
  Categories / Client / link rows (`links`), anchors in the body (`body_links`), any other
  sidebar row (`sidebar_other`), and `possible_duplicate_of` (pages sharing a hero image).
- Home page: `data-count` counters (projects, long-term clients, hours), JSON-LD person
  (job title, knowsAbout), testimonials (name, role, quote), services, self-rated skill
  percentages, About text, links (LinkedIn, GitHub, Calendly, CV PDF).

If it fails on the network, retry once; if the site structure changed (0 projects parsed,
or titles empty), stop and tell David — do not rebuild the catalogue from a broken scrape.

## 2. Diff

```
python3 $K/diff_catalogue.py --raw $S/raw.json --catalogue docs/portfolio-catalogue.json --out $S/refresh-diff.json
```

It prints `NEW n  CHANGED n  UNCHANGED n  COVERED n  REMOVED n` and one line per item.
Comparison ignores markup-only differences (bold, link syntax, list markers, embeds, entities,
URL host case), compares the site title against `site_title` (the curated `title` may fix a
typo), and only requires the site's *sidebar* links to be present (curated "Referenced" links
are extra). So on a quiet site the diff is empty; anything listed is a real change.

`$S/refresh-diff.json` holds the full raw record of every new/changed project under `raw`,
and for changed ones the current curated fields under `current`.

**Nothing new or changed?** Skip to step 4 — the build still refreshes profile counters,
testimonials and dates.

## 3. Curate the delta

Write `$S/refresh-curated.json` — a JSON list with one object per new/changed project id.
Field definitions and the fixed theme list are in `catalogue-schema.md`. Read the raw
`body_markdown`, `links`, `body_links`, `site_tags`, `client`, `date` before writing.

For a **new** project, fill every curated field:

| Field | How to write it |
|---|---|
| `title` | Only if the site heading has an obvious typo ("Gene rative AI") — otherwise omit and the site title is used |
| `summary` | One sentence, ≤ 30 words, what was built and for whom. No marketing adjectives |
| `themes` | 1–3 from the fixed list. Add a new theme only if none fits at all (and say so in the report) |
| `industries` | 1–2, reuse existing names where they fit (`Healthcare & insurance`, `SaaS`, …) |
| `domains` | 2–5 short capability tags (`RAG`, `Web scraping`, `Conversion tracking`) |
| `skills` | Concrete tools/techniques **named in the text**, in the text's spelling. Not "AI" |
| `role` | What David did: `Sole engineer — …`, `Technical lead for the client's team`, `Deployment engineer` |
| `outcomes` | 2–5 bullet facts. Numbers and before/afters verbatim from the text. Include honest limits the text states ("profitable at times, but fees …") |
| `cv_bullet` | One sentence, ≤ 45 words: verb + what/tech + the outcome with its number. It must stand alone on a CV |
| `links` | Optional extra `{"label","url"}` from `body_links` worth attaching (GitHub repo, live demo, paper, API docs). Label useful ones `Referenced`; skip generic links |
| `notes` | Optional: caveats, e.g. product rights, page typo |
| `also_published_as` | If `possible_duplicate_of` is non-empty: keep the **more complete** page as the entry and list the other page's URL here; add `{"id": "<other>", "drop": true}` as a separate object so the build skips it |

For a **changed** project, include only the fields that the change affects:
- `body` changed → re-read it; update `summary`, `outcomes`, `skills`, `cv_bullet` if the facts
  moved (a new metric, a new tool). Keep wording otherwise.
- `title` changed → check whether the curated `title` should follow.
- `links` / `date` / `client` / `image` / `site_tags` → nothing to do; the build takes them
  from the site automatically.

Style for `cv_bullet` (same as the polish formula): past tense, starts with the verb, names
the tools as the text names them, ends on the number. Compare with neighbours in the
catalogue so the register matches.

## 4. Build

```
python3 $K/build_catalogue.py --catalogue docs/portfolio-catalogue.json --raw $S/raw.json \
    --curated $S/refresh-curated.json \
    --out-json docs/portfolio-catalogue.json --out-md docs/portfolio-catalogue.md
```
(omit `--curated` when there was no delta).

- Exit 2 → it lists projects with no `cv_bullet`/`themes`. Curate them (step 3) and rerun.
  `--allow-uncurated` exists for emergencies only; it marks entries `needs_curation` and the
  markdown shouts about it.
- Projects gone from the site are dropped with a stderr note (`--keep-removed` to keep them).
- Profile: counters → `projects_delivered` / `long_term_clients` / `hours_worked`; JSON-LD job
  title → `headline`; testimonials → `testimonials` and `named_clients_and_references`;
  services merged (site wording wins); links updated. Curated profile fields (`positioning`,
  `education`, `credentials`, `core_stack`, `experience_years`) are kept — edit them directly in
  the JSON, or pass `--profile override.json`, then rebuild.
- Then run the diff again against the rebuilt catalogue: it must print `NEW 0  CHANGED 0`.
  Also run the build a second time on its own output if you changed the scripts — it must be
  a no-op apart from `generated`.

## 5. The original CV

```
shasum -a 256 $S/cv.pdf   # compare with docs/cv/base-cv.json → source_pdf_sha256
```
Different hash →
1. `cp $S/cv.pdf docs/cv/David_Gadyan_Resume.pdf` and `pdftotext -layout` it to
   `docs/cv/David_Gadyan_Resume.txt`.
2. `pdfimages -png docs/cv/David_Gadyan_Resume.pdf $S/img` → if a ~square image came out,
   copy it to `docs/cv/headshot.png`.
3. Re-transcribe `docs/cv/base-cv.json` from the new text (same schema; keep facts verbatim,
   fix nothing), set `source_pdf_sha256` to the new hash.
4. Render it once to confirm it still fits one page:
   `python3 $K/render_cv.py --cv docs/cv/base-cv.json --out $S/base-check.pdf --png`.

Same hash → say "original CV unchanged".

## 6. Report

- Counts: new / changed / removed, and the catalogue project count and `generated` date.
- For each new project: title, date, the `cv_bullet` you wrote, the portfolio link.
- Profile counters as now recorded (projects, long-term clients, hours) and the headline.
- Whether the CV PDF changed.
- `git status --short docs/` so David sees what to commit (do not commit unless asked).
