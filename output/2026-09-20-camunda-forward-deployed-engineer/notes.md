# Camunda — Forward Deployed Engineer, ProcessOS (first cohort)  (2026-09-20)

JD source: pasted from LinkedIn (saved in `jd.txt`, board UI text removed). Remote, #USEAST; US TTC $131k–$211k, elsewhere via Remote.com.

## What the role really asks for

An engineer who can walk into an enterprise customer, get an agentic workflow into production, prove it with numbers, document the playbook and leave the customer's team running it — while feeding fixes back into the product. Camunda/BPMN/Java knowledge is listed, but the "What you bring" section is weighted toward production AI experience, integration debugging, stakeholder communication and hand-off discipline.

## Requirement → evidence

| Requirement (JD wording) | Evidence on the CV | Status |
|---|---|---|
| Practical AI experience in production — context management, prompt engineering, agent testing, integration trade-offs | Virgil.ai (production agent, MCP tools, HIPAA); LangGraph review agent (user-defined checks replacing hard-coded prompts = context/prompt engineering; external API validation); S1mple.ai (custom tools + MCP); "prompt & few-shot engineering" in skills | strong (agent *testing* only implied — see gaps) |
| Production experience with agentic systems / AI-integrated workflows (nice-to-have) | Virgil.ai, S1mple.ai + lead-scoring engine, LangGraph agent, n8n workflow (open source line) | strong |
| Write a custom agent against a legacy/external API; debug integration failures | LangGraph agent (ABN/ACN external API); S1mple.ai MCP connectors into HubSpot/Monday/Zoho and four databases; Google Workspace APIs | strong |
| Hand off deliberately — leave the customer team trained and independent | Technical-lead engagement (mentored client's engineers; team ships and runs the app); real-estate platform handed over with full documentation and reproducible code; LangGraph replication package | strong |
| Stakeholder communication across engineering, architecture and business leadership | Scope bullet: works directly with CEOs, CPOs, CFOs, managing partners (15 named references on the portfolio); broker partner on Virgil.ai | strong |
| Customer-facing engineering / professional services (nice-to-have) | 8 years freelance consulting, 100+ clients, 50+ long-term; subheading "independent consultant, customer-facing delivery" | strong |
| Regulated industries — financial services, healthcare, insurance (nice-to-have) | Virgil.ai (health insurance, HIPAA); law-firm due diligence; EY Big-4 compliance; real-estate zoning/quota constraints | strong |
| Comfort with ambiguity; document what you learn | Sole-engineer roles; documentation/replication packages on three projects | partial (implied, not stated) |
| Enterprise production experience *inside a large organisation* | EY (Big-4) — but as a tax accountant, not shipping software; client work was for SMEs/startups plus SecondSight, Greenwich.HR | partial |
| Java services | — (Python/FastAPI stack) | gap |
| React interfaces | S1mple.ai React frontend, Next.js dashboard; skills line | strong |
| Camunda clusters, BPMN | — | gap (JD itself says "ability and/or willingness to use our product") |
| Distributed systems performance / fault tolerance | Kubernetes deployments (Virgil.ai, lead scoring); 24/7 cloud scrapers exist in the catalogue but were not included | partial |
| Contributions to a shared platform / open source (nice-to-have) | n8n AI-assistant workflow and AI video pipeline on GitHub (Additional Information) | partial — personal repos, not contributions to others' platforms |
| Occasional travel | not on the CV (a preference, not a fact I can source) | add to cover letter if true |

## Projects used (with links)

1. [AI Health care — Virgil.ai](https://davitgadyan.github.io/portfolio_app/portfolio/project-34/) — production agentic system in a regulated domain, MCP, Docker/Kubernetes on AWS, broker partner; "days → minutes".
2. [Gemini LangGraph LLM Agent](https://davitgadyan.github.io/portfolio_app/portfolio/project-28/) — multi-agent workflow, dynamic user-defined checks, external API integration, docs + replication package.
3. [S1mple.ai](https://davitgadyan.github.io/portfolio_app/portfolio/project-33/) + [AI Lead Scoring — S1mple.ai](https://davitgadyan.github.io/portfolio_app/portfolio/project-35/) (one bullet, two links) — agentic platform David created; custom tools, MCP connectors into CRMs and databases, React/Next.js, Kubernetes.
4. [Data Science Consulting & Review](https://davitgadyan.github.io/portfolio_app/portfolio/project-25/) — technical lead mentoring the client's team to production; the hand-off requirement.
5. [AI Real Estate Analysis Program](https://davitgadyan.github.io/portfolio_app/portfolio/project-30/) — end-to-end delivery with documentation and reproducible code for in-house operation; regulatory constraints embedded.
6. [AI Assistant n8n](https://davitgadyan.github.io/portfolio_app/portfolio/project-32/) — referenced in Additional Information as the open-source workflow.

Considered and dropped: Document OCR (healthcare, but not agentic); Crypto RAG (RAG less central here); Classification of Industry of Firm (QA process design and replication package — good "document what you learn" evidence if a swap is wanted).

## Changes vs base CV

- Headline → "Forward Deployed Engineer | Agentic AI Systems in Production | AI Consultant".
- 3-line summary framing every engagement as customer-facing scoping → production → hand-over.
- Upwork subheading → "AI Engineer / Data Scientist — independent consultant, customer-facing delivery".
- Upwork bullets: scope bullet with consolidated numbers and the executive-level stakeholders; five linked project bullets ordered production-AI → custom agent/API → platform+integrations → hand-off → end-to-end delivery.
- EY compressed to one line, framed around compliance and internal controls (governance signal).
- Skills regrouped: Agentic AI / Integration & apps / Delivery / Languages. Only evidenced tools; JD spelling. "HIPPA" → HIPAA; "SOC20" left out pending confirmation.
- Personal projects replaced by the open-source line (n8n workflow, video pipeline on GitHub).

## Gaps to prepare for (interview / cover letter)

- **Camunda / BPMN / Java**: none on the CV. Cover letter should say plainly that the stack is Python-first and point to how fast platform-specific tooling was picked up elsewhere (MCP, LangGraph, n8n all adopted into production within months of release). Consider doing the free Camunda 8 getting-started before interviews.
- **"Inside a large organisation"**: the honest framing is *for* large-organisation-grade constraints (HIPAA, legal due diligence, zoning regulation) as an external consultant, plus EY. Prepare the governance/resilience story around Virgil.ai.
- **Agent testing / evaluation**: no project text describes a formal eval harness. Prepare a concrete example (how the LangGraph checks were validated; QA reviews on the industry-classification project).
- **Open source "that others built on"**: the GitHub repos are David's own; be precise about that.
- **Travel**: not stated on the CV; state willingness in the application if true.
- Compensation note: outside US/UK/SG the offer comes via Remote.com with a per-country calculator after the first interview.

## Render

`David_Gadyan_CV_Camunda.pdf` — 1 page, 10pt, line-height 1.22, page fill 95%, 12 clickable links (4 contact + 6 project + 2 GitHub). Five render passes: 9.5pt → text tightened → 9.75pt → headline shortened, orphans cut → 10pt clean.
