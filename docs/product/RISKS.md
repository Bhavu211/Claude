# Risks — AI Career Copilot

## Fabrication risk (highest priority)

**Risk:** an agent invents a fact — a metric, a project, a credential, a source — that the candidate then unknowingly repeats in an interview and gets caught on.

**Mitigation in place:** every agent's system prompt explicitly forbids fabrication and requires null/"insufficient evidence" over invention; Critic Agent specifically checks for this across all 15 reviewed outputs; Interview Coach Agent — the highest-stakes agent for this risk — returns `star_answer: null` rather than a fabricated story when the resume has no supporting evidence.

**Residual risk:** this is a prompted behavior, not a hard technical guarantee. An eval harness that specifically measures hallucination rate against known ground truth (Phase 7) is needed before this can be called "solved" rather than "well-mitigated."

## Stale or wrong real-world facts

**Risk:** company details, salary data, or learning resources are outdated or simply wrong, and presented with false confidence.

**Mitigation in place:** research-grounded agents (Company Intelligence, Learning & Certification, Career Strategy) use live web search rather than parametric memory, and explicitly separate sourced claims from unverified/assumed ones.

**Residual risk:** web search quality varies by how well-indexed the target company/topic is; thin coverage degrades silently unless `research_confidence` is read carefully.

## Over-reliance / authenticity risk

**Risk:** a candidate presents AI-assisted materials as entirely their own unaided work, or loses the ability to speak to their own resume in an interview because they didn't actually internalize what was written for them.

**Mitigation:** none currently built into the system — this is a user-behavior risk, not a system-output risk, and is out of this system's control. Worth stating explicitly rather than ignoring.

## Cost risk

**Risk:** a full 18-agent pipeline run, especially with 3 web-search-grounded agents, has real, non-trivial API cost. Uncontrolled use (e.g. re-running for every minor JD variation) could get expensive fast.

**Mitigation in place:** Planner Agent estimates execution cost/complexity upfront and can skip agents not relevant to the user's stated intent.

**Residual risk:** no hard budget cap or cost-tracking exists yet (planned for Phase 7/v0.2).

## Single point of failure in orchestration

**Risk:** Planner Agent's plan is grounded in `AGENT_REGISTRY`, but if the registry ever drifts from what agents actually require (e.g. someone changes an agent's required fields without updating the registry), Planner's plan would be silently wrong.

**Mitigation in place:** registry entries are written to match each agent's actual Pydantic input model; Critic/Supervisor cross-check `agent_id` references against the registry.

**Residual risk:** there's no automated test that fails CI if an agent's real input model and its registry entry diverge — this should be a Phase 1/CI addition.

## Ethical/legal risk in generated content

**Risk:** application assets (cover letters, outreach) or resume rewrites could cross from "reframing real experience persuasively" into "misrepresenting experience," especially in verb-choice decisions (e.g. "Managed" → "Owned").

**Mitigation in place:** Resume Rewrite Agent's system prompt constrains it to fact-preserving rewrites; Critic Agent specifically reviews for scope-inflation language.

**Residual risk:** this is a judgment call at the margin, and the system currently makes that call unilaterally rather than flagging borderline word choices for the candidate to confirm.

## Competitive/commoditization risk

**Risk:** general-purpose AI assistants (ChatGPT, Claude.ai directly) can approximate parts of this system's output with a well-crafted single prompt, eroding the case for a dedicated multi-agent product.

**Mitigation/differentiation:** see `docs/product/COMPETITIVE_ANALYSIS.md` — the actual differentiation is the orchestration/governance layer (Planner/Critic/Supervisor) and evidence-traceability discipline, not any single agent's output in isolation.
