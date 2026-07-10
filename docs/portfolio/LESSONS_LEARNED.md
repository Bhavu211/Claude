# Lessons Learned

Concrete, specific things this build actually surfaced — not generic platitudes.

## A critic agent that never finds anything wrong isn't doing its job

Critic Agent's first real review pass came back almost entirely clean — 14 of 15 agents approved or approved-with-minor-notes. That's a red flag for a review agent, not a green light: a critic that always says "looks good" is indistinguishable from one that isn't actually checking. The fix wasn't to force it to find more issues artificially — it was to give it a concrete, mechanical task it couldn't fake: *recompute every stated total against the numbers it's supposedly summarizing.* That's what actually caught the one real bug in this project (Learning & Certification's total didn't match the sum of its own line items) — not a vaguer instruction like "review for quality." Specific, checkable tasks catch real bugs; vague quality instructions produce vague, rubber-stamp reviews.

## "Insufficient evidence" has to be a first-class schema value, not a prompt suggestion

Early in this project, non-fabrication was enforced entirely through system-prompt instructions ("never invent facts"). That's necessary but not sufficient — a model under instruction to "be helpful" will still often fill a gap with something plausible rather than leave it empty, because empty *feels* unhelpful. The fix that actually held under review was structural: giving fields explicit null-ability and bracketed-placeholder conventions (`[Recruiter Name]`) as part of the schema itself, so "I don't have this" has a designated, expected place to go instead of competing with "make something up" as an implicit default.

## A shared registry beats trusting an agent's self-description

Planner, Critic, and Supervisor all need to reason about what agents exist and how they depend on each other. The tempting shortcut is to just describe the other agents in each orchestrator's system prompt — but that drifts the moment an agent's actual required fields change and nobody updates three separate prompt descriptions. Building `AGENT_REGISTRY` as one shared, machine-readable source of truth (and grounding every orchestration agent's prompt in it directly, then programmatically checking every `agent_id` reference against it) made an entire class of hallucination — inventing an agent, or a dependency, that doesn't exist — structurally impossible rather than just less likely.

## Two-phase research beats one-phase "just use web search and format it"

Company Intelligence, Learning & Certification, and Career Strategy all need real, current facts. Combining "search the web" and "format the answer" into one model call sounds efficient, but it conflates two different failure modes: getting the facts wrong, and getting the JSON structure wrong. Splitting into a research call (search-enabled, free-text) and a separate structuring call (no search, schema-forced) meant each phase could be checked independently — and made it obvious, when reviewing output, whether a problem was a research gap or a formatting gap.

## GitHub App "authorized" and "installed" are not the same thing, and the error message doesn't say so

Most of a full session was spent diagnosing a persistent `403 Resource not accessible by integration` error. The actual cause — visible only by checking GitHub's own **Installed GitHub Apps** vs. **Authorized GitHub Apps** tabs separately — was that the app had been OAuth-authorized (identity verification only) but never actually *installed* with repository permissions. GitHub's error message gives no hint of this distinction; diagnosing it required systematically ruling out the more common causes (git credentials, signing keys, token scope) before checking the one place that showed the real gap. Lesson: when a permission error persists across multiple independent code paths (both `git push` and a separate API integration failed identically), the shared root cause is almost always upstream of both — in this case, an installation step neither path could see or fix from the client side.

## Verification-by-recomputation is worth the extra step

Every numeric claim in this system's sample outputs — ATS score arithmetic, gap-analysis row counts, skill-evidence confidence distributions, placeholder counts, character limits — was independently recomputed with a script against the underlying JSON, not just asserted in prose. This caught the Learning & Certification bug and confirmed everything else was actually correct, not just plausible-looking. It's more work than "eyeball the output and it looks right," and it's the difference between a verified system and one that merely appears verified.
