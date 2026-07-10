# Roadmap (portfolio view)

**Shipped:** all 18 agents, each independently verified; a real orchestration pipeline wiring them in dependency order; a governance layer (Planner/Critic/Supervisor) that plans, reviews, and renders a go/no-go verdict grounded in a shared agent registry; full documentation and a working end-to-end dry-run verified without needing a live API key.

**Next:** make it measurable and usable by someone who isn't reading Python — live validation against varied real inputs, a persisted run history, an evaluation harness that turns "this agent works" into an actual accuracy/hallucination-rate number, and a real UI over the existing pipeline.

**Later:** workflow automation, partial re-runs driven by Supervisor's own findings, and the product decisions (pricing, access model, outcome tracking) that turn this from a working system into an actual product.

Full detail: [`docs/product/ROADMAP.md`](../product/ROADMAP.md).
