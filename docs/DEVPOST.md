# Evidence Desk — submission copy (Open Agent Hackathon 2026 · Track 02)

> Paste into HackOS / Devpost. Track: **Track 02 — The Agent That Can Explain Why**.
> Repo: https://github.com/Sourendas/evidence-desk (MIT) · Video: upload `demo/evidence_desk_demo_voice.mp4` (2:53, voiceover) to YouTube and paste the link · Cover: `cover.png` (1500×1000)

## Title
Evidence Desk

## Tagline (short)
The agent that can explain why: every claim in its answer traces back to a verbatim, verified quote.

## Inspiration / Problem
AI answers sound confident, but you can't check them. Citations get invented, quotes get paraphrased into things nobody said, and the reasoning is hidden, so you can't tell which fact actually drove the answer. That's fine for trivia and useless for real decisions. Indie freelancers and small teams make these calls every day: *Should I bid on this job? Is this contest worth entering? Does this vendor fit?* They need an answer **and** a "why" they can audit in a minute.

## What it does
You ask a decision question and give it material: pasted text (a job post, your profile, a pricing page), public URLs, and optionally a keyless Wikipedia search. Evidence Desk then:

1. **Plans** the question into 3–5 sub-questions (risks, benefits, requirements…).
2. **Retrieves** every source (with an SSRF guard, size and time limits).
3. **Extracts** verbatim sentences only. Quotes are ranked with BM25 + risk/benefit polarity cues, near-duplicates are skipped and sources are kept diverse. Each quote carries its score and matched terms, so even the *choice* of evidence is explainable.
4. **Synthesizes** a recommendation where every claim must cite evidence ids (E1, E2…). The LLM reasons over numbered evidence and cannot add new quotes.
5. **Verifies.** Claims citing evidence that doesn't exist are dropped, every quote is re-checked word for word against its source, and confidence is computed transparently from coverage × source diversity × citation rate.
6. **Concludes** with the recommendation, confidence, open risks, next actions and a markdown report.

The "why" is shown three ways:
- **Why-graph** (inline SVG): recommendation → claims → verbatim quotes → sources. Green edges support, red edges caution. Hover a node to light up only its path; click a quote to jump to it. Evidence the agent read but didn't rely on is listed as *uncited*.
- **Explain-why trace:** a numbered, timed log of all six steps, each with expandable details (e.g. verify shows coverage, diversity, cited fraction and dropped claims).
- **Markdown export:** the full report with the why-graph as a Mermaid diagram (renders natively on GitHub).

In the demo's live run (NVIDIA Nemotron 3 Nano) on a real-looking n8n freelance job: 5 sub-questions, 41 candidate sentences ranked, 15 verbatim quotes from 3 sources, 7/7 claims kept, 15/15 quotes verified, confidence 0.89 (high), about 13 s end to end.

## How we built it
- **Agent:** plain Python 3 standard library, no framework, no paid services. Six explicit stages (plan → retrieve → extract → synthesize → verify → conclude), and each one writes a trace step.
- **Model (sponsor tech: NVIDIA):** **NVIDIA Nemotron 3 Nano 30B-A3B** (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`), an open NVIDIA model, called through **Nebius Token Factory**'s OpenAI-compatible `/chat/completions` API for planning and synthesis. Any OpenAI-compatible endpoint works via env vars. The key lives in a gitignored env file and is never printed or returned by the API.
- **Deterministic stub mode:** with no key, a template planner and an extractive synthesizer keep the app fully usable offline. If a live LLM call fails, the agent falls back automatically and records that in the trace.
- **Retrieval & ranking:** stdlib HTML-to-text, BM25 with a tiny stemmer, polarity cues, Jaccard near-duplicate filter, same-source decay, round-robin across sub-questions, and a filter that keeps bibliography lines out of quotes.
- **UI:** one static HTML page with a hand-rolled SVG why-graph (no JS libraries). Also available as a CLI and a JSON API (`POST /api/ask` returns `why_graph`, `mermaid` and `markdown`).
- **Sponsor slots (honest status):** `evidence_desk/sponsors.py` defines a **Zetaris** source-adapter slot and a **Meterless** usage-meter slot. Any adapter's sources go through the same extract → verify pipeline. Both are **not connected yet**: no sponsor API calls are made today. A local meter records per-LLM-call usage and latency in the conclude step.
- **Tests:** 22 unit tests (stub mode, no network, no key) cover quote ranking, duplicate and diversity rules, the hallucinated-citation drop, the verbatim check, the why-graph and Mermaid escaping, the SSRF guard, the server API and the sponsor slots.

## Challenges we ran into
- **Quotes that are actually relevant.** Plain keyword overlap picked bibliography lines and repeated the same sentence for every sub-question. BM25 + polarity cues + duplicate and diversity rules fixed it, and we expose each score so the ranking itself can be audited.
- **Keeping the LLM honest.** Models love to "improve" quotes. We split the work: quotes are extracted by code, the LLM only cites ids, and a verifier drops anything that doesn't match.
- **Making "why" readable.** A long trace is accurate but hard to scan. The 4-column why-graph with path highlighting lets a judge follow one claim to its source in seconds.
- **Zero budget.** No paid APIs or hosting. Everything runs locally on the standard library, with a deterministic offline mode.

## Accomplishments we're proud of
- Every claim in the final answer is tied to a quote that is checked word for word against its source, and that's enforced by code, not by a prompt.
- Confidence is a transparent formula shown in the trace, not a vibe.
- Small, dependency-free codebase you can run in one command.

## What we learned
Explainability is mostly plumbing: stable evidence ids, extract-don't-generate, and a verifier that is allowed to say no. Once those exist, the graph and the trace are just two views of the same data.

## What's next
- Connect the Zetaris source adapter and the Meterless meter through their official APIs (the slots and tests are already in place).
- A "disagreeing evidence" view that shows the strongest quote against the recommendation.
- Saved investigations and side-by-side comparison of two options (e.g. two contests).
- Hosted demo + browser extension: "Explain why" on any job or contest page.

## Built with
python · nvidia-nemotron · nebius-token-factory · openai-compatible-api · bm25 · svg · mermaid · html · javascript

## Try it out
- Code: https://github.com/Sourendas/evidence-desk
- Run locally: `cd app && python server.py` → http://127.0.0.1:8787 → **Load sample** → **Investigate** (works without a key in stub mode; set `EVIDENCE_LLM_*` for live Nemotron).
- Tests: `python -m unittest discover -s tests -t .`

## Demo video narration
See `demo/NARRATION.md` (2:53, edge-tts voiceover over real screenshots of a live Nemotron run).
