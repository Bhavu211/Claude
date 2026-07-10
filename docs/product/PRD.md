# Product Requirements Document — AI Career Copilot

## Problem statement

Job seekers preparing a serious application do 6-8 hours of fragmented work per role: re-reading the JD for what actually matters, guessing what the company cares about, tailoring a resume without breaking ATS parsing, figuring out what they're weak on, building a story for interviews, and writing 4-5 pieces of outreach copy — each done from scratch, with no consistent quality bar, and no way to know if any of it is actually good until a recruiter responds (or doesn't).

Generic LLM chat ("help me with my resume") produces plausible-sounding output that is frequently wrong in ways the candidate can't detect: invented achievements, inflated scope, keyword-stuffed resumes that read as robotic to a human, interview answers built on facts not in the candidate's actual history. The failure mode isn't "unhelpful" — it's "confidently wrong in a way that damages the candidate's credibility in an interview."

## Target users

- **Primary:** job seekers actively applying to specific roles who want a complete, tailored application package (resume, gap analysis, interview prep, outreach) for a real JD and company — not generic advice.
- **Secondary:** career changers who need an honest, evidence-based read on where they actually stand against a role's requirements before investing months in upskilling.
- **Tertiary (this repo specifically):** AI/PM practitioners studying multi-agent system design — this project doubles as a reference implementation of a non-fabrication-disciplined, orchestrated agent pipeline.

## Goals

1. Produce application materials that are **evidence-traceable** — every claim resolves to something the candidate's actual resume states or a cited, real source, never an invention.
2. Cover the **full application lifecycle** in one system: understand the JD → assess fit → close gaps → tailor materials → prepare for interviews → decide whether to pursue the role at all.
3. Make the system's own outputs **checkable**, not just plausible — via a dedicated review layer (Critic Agent) and a go/no-go verdict (Supervisor Agent), not just "trust the model."

## Non-goals

- Not a job-search aggregator or application-submission bot — it doesn't find or apply to jobs.
- Not a general resume-formatting/design tool — it produces content, not typeset PDFs.
- Not a guarantee of interview success — it improves the inputs a candidate controls; it doesn't predict or influence recruiter decisions.

## Scope (current: v0.1)

18 agents across four categories (see `README.md` Architecture section and `docs/agents/*.md` for full detail):
- **Extraction** (12 agents): read the resume/JD and derive structured findings independently.
- **Research** (3 agents): ground claims about the real world — company, learning resources, salary — in live web search rather than parametric memory.
- **Synthesis** (2 agents): compose other agents' structured findings into new artifacts (portfolio projects, the final report).
- **Orchestration** (3 agents): Planner decides what to run, Critic reviews what ran, Supervisor renders the final go/no-go verdict.

Plus `pipeline.py`, the real end-to-end entry point wiring all 18 together in dependency order.

## Functional requirements

- FR1: Given a resume and JD, the system must produce a gap analysis, an ATS score, and at least one tailored resume version.
- FR2: Given a company name, the system must ground company-specific content (interview questions, application assets) in live-researched, cited facts — never invented details.
- FR3: Every agent's output must validate against a declared Pydantic schema — no free-text parsing between agents.
- FR4: The system must be able to state "insufficient evidence" or leave a field null rather than fabricate a plausible-sounding answer.
- FR5: A review layer must be able to catch and report internal inconsistencies (e.g. a stated total not matching its own line items) before a deliverable is considered ready.

## Non-functional requirements

- **Non-fabrication is the top-priority constraint** — every agent's system prompt encodes this explicitly; it is enforced structurally (schema fields for null/insufficient-evidence), not just requested in prose.
- **Cost/latency:** research-grounded agents (Company Intelligence, Learning & Certification, Career Strategy) are the dominant cost/time driver; Planner's execution-cost estimate should reflect this, not just agent count.
- **Determinism of structure, not content:** identical inputs won't produce identical text (LLM sampling), but must always produce schema-valid output.

## Success metrics

See `docs/product/ROADMAP.md` and `docs/evals/` (Phase 7 scaffold) for the concrete metrics this system should eventually be measured against: hallucination rate, hard-fact accuracy, completeness, cost per full run, and — once there are real users — time saved and outcome correlation (interview/offer rate vs. baseline).

## Open questions

- Should the system ever submit/send anything on the user's behalf (email, LinkedIn message), or should it always stop at "drafted, ready for the user to review and send"? Current design is strictly the latter.
- How should the system handle a JD that's clearly a bad match (e.g. the candidate is 5+ years underqualified)? Currently Recruiter Simulation and Career Strategy will say so honestly, but there's no explicit "should you even apply" gate before the full pipeline runs.
