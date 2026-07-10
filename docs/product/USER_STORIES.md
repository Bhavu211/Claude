# User Stories — AI Career Copilot

Grouped by the phase of a job search they serve. Each maps to one or more agents (see `docs/agents/`).

## Understand the opportunity

- As a job seeker, I want to know what a JD's boilerplate is hiding, so I don't waste effort on requirements that don't actually matter to the recruiter. → **JD Intelligence Agent**
- As a job seeker, I want current, real facts about a company (not stale training-data knowledge), so I don't say something wrong or outdated in an interview. → **Company Intelligence Agent**

## Assess my fit honestly

- As a job seeker, I want to know exactly which JD requirements I'm missing, and how severe each gap actually is, so I can prioritize what to fix. → **Gap Analysis Agent**
- As a job seeker, I want to know not just *whether* I have a skill but whether my resume *proves* it convincingly, so I know which bullets need to be stronger, not just which skills to add. → **Skill Evidence Agent**
- As a job seeker, I want an unflattering, realistic read of how a time-pressured recruiter would actually screen my resume, so I'm not blindsided by a rejection I could have seen coming. → **Recruiter Simulation Agent**

## Close the gaps

- As a job seeker with a skill gap I can't yet claim from work history, I want a specific, scoped project brief I can actually execute, not generic "build a portfolio" advice. → **Portfolio Recommendation Agent**
- As a job seeker, I want a sequenced learning plan with real, currently-existing courses (not invented ones) and an honest ROI read on whether a certification is worth it for me specifically. → **Learning & Certification Agent**

## Tailor my materials

- As a job seeker, I want my resume rewritten for ATS parsers without losing what makes it compelling to a human reader. → **ATS Optimization Agent** + **Resume Rewrite Agent**
- As a job seeker, I want a LinkedIn profile that plays to LinkedIn's own conventions, not just my resume pasted in verbatim. → **LinkedIn Optimization Agent**
- As a job seeker, I want a full set of application communications (cover letter, outreach, follow-up) drafted and factually consistent with my actual resume, so I'm not writing six documents from scratch per application. → **Application Assets Agent**

## Prepare for interviews

- As a job seeker, I want interview questions with answers grounded in my real history, and an honest "you don't have a story for this yet" when that's true, not a fabricated one I'd get caught on in a follow-up. → **Interview Coach Agent**

## Decide whether to pursue it

- As a job seeker, I want a realistic, currently-researched salary range and a role-fit read that accounts for everything the system has found about me, not a generic guess. → **Career Strategy Agent**
- As a job seeker, I want one consolidated report I can actually read end-to-end, not 14 separate JSON files I have to synthesize myself. → **Final Report Agent**

## Trust the system itself

- As a job seeker, I want to know the system checked its own work — not just that it produced plausible-sounding output — before I rely on it. → **Critic Agent**
- As a job seeker, I want a single clear signal for "is this package actually ready," not a pile of individual agent outputs I have to judge myself. → **Supervisor Agent**
- As a job seeker with limited time, I want the system to figure out what actually needs to run for my specific request, instead of always running everything. → **Planner Agent**
