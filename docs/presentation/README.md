# Business Presentation

A screenshot-driven walkthrough of the Career Copilot dashboard, written for
a business/PM audience rather than an engineering one — the problem, the
18-agent pipeline, a step-by-step tour of a real run, and the roadmap.

- `career-copilot-presentation.html` — self-contained (screenshots embedded
  as base64), open directly in a browser. Light/dark theme aware.
- `career-copilot-presentation.pdf` — print-paginated export of the same
  deck, ready to share or attach as-is.
- `career-copilot-demo.mp4` — a 2:16 narrated screen recording of the real
  dashboard: uploading a resume/JD, running the live 18-agent pipeline,
  watching the execution graph update in real time, then a tour of every
  history/analytics page. Includes an on-screen pointer highlighting each
  interaction and a synced voiceover.
- `voiceover_script.md` — the timestamped narration script the video's
  audio was generated from, in case you want to re-record it with a
  different (higher-quality/human) voice — the video's narration track was
  synthesized with a local offline TTS engine, since this build environment
  has no route to cloud TTS services; swap in your own recording of this
  script for a more natural voice.

All of the above were generated from the actual running dashboard (see
`../../dashboard/`) — no mockups.
