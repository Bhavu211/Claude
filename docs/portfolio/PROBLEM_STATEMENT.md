# Problem Statement

Serious job applications take 6-8 hours of fragmented, error-prone manual work: decoding what a JD actually screens for, researching a company beyond stale memory, honestly assessing fit, tailoring a resume without breaking ATS parsing, building interview answers, and drafting 4-6 pieces of outreach copy — each done from scratch, with no consistent quality bar.

Generic AI chat assistance makes this faster but not safer: it produces confident, plausible-sounding output that is frequently *wrong in ways the candidate can't detect* — invented metrics, inflated scope, keyword-stuffed text that reads as robotic, interview answers built on facts not in the candidate's real history. In an interview, a fabricated claim doesn't fail quietly — it fails in front of the person deciding whether to hire you.

**The core design bet of this project:** a job-application AI system's most important property isn't fluency, it's *evidence-traceability* — every claim it produces must resolve to something the candidate's actual resume states or a cited, real source, and the system must say "I don't have evidence for this" rather than invent something plausible. That constraint shaped every architectural decision in this system, from per-field null-ability to a dedicated review agent whose entire job is catching violations of it.

See `docs/product/PRD.md` for the full requirements this problem statement drives, and `docs/portfolio/ARCHITECTURE.md` for how the system is built to enforce it.
