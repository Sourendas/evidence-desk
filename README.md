# Evidence Desk — the agent that can explain why

> Open Agent Hackathon 2026 · **Track 02 — The Agent That Can Explain Why**

Evidence Desk answers a hard decision question ("Should I bid on this freelance job?",
"Which contest fits this product?") by pulling fragmented public sources, extracting
**verbatim, cited evidence**, and returning a recommendation with a confidence score,
open risks, next actions and an ordered **explain-why trace** a judge can follow step by step.

## How it works

```
question + pasted snippets + URLs
        │
 1. plan        → 3–5 sub-questions (LLM, or deterministic template planner)
 2. retrieve    → pasted snippets, pasted URLs over HTTP, optional keyless Wikipedia search
 3. extract     → verbatim sentences ranked per sub-question with BM25 + polarity cues,
                  then a diversity-aware pick (no near-duplicates, spread across sources)
 4. synthesize  → recommendation + claims, each claim must cite evidence ids (E1, E2…)
 5. verify      → drops claims citing non-existent evidence, re-checks every quote is
                  verbatim in its source, computes confidence from coverage, source
                  diversity and citation rate
 6. conclude    → final answer + markdown report
```

Every stage writes a numbered `trace` step (with timing and details), shown in the UI's
**Explain-why trace** panel and in the exported report.

### Why-graph
The answer is also drawn as a 4-column graph: **recommendation → claims → verbatim quotes → sources**.
- **Web UI:** pure inline SVG (no libraries). Edges are green (supports), red (cautions) or grey
  (context). Hover any node to highlight only the path through it; click a quote to jump to it,
  click a source to open it. Evidence the agent read but no claim relied on is listed as *uncited*.
- **Markdown export / API:** the same graph as a ```` ```mermaid ```` flowchart (renders natively on
  GitHub), plus `why_graph` (nodes/edges JSON) and `mermaid` fields in `POST /api/ask`.

### Quote picking (extract step)
- **Relevance:** BM25 over all candidate sentences; sub-question terms weigh 1.0, terms only in the
  main question 0.5; a tiny deterministic stemmer matches *freelancers/freelance*, *required/requirements*.
  Planner filler words ("key facts", "regarding"…) are ignored.
- **Polarity:** risk sub-questions boost sentences with risk/cost cues (and can pick a cue-only
  sentence at half weight); benefit sub-questions the reverse; off-polarity quotes are down-weighted.
- **No duplicates:** a sentence is used once; near-duplicates (token Jaccard ≥ 0.6) are skipped.
- **Diverse sources:** each pick decays the score of further quotes from the same source (×0.7),
  max 2 quotes per source per sub-question.
- **Fair coverage:** sub-questions pick round-robin (risk/benefit first), so one generic
  sub-question can't drain a small pool.
- Bibliography/citation lines ("(PDF)", ISBN, publisher lines) and fragments are never quoted.
- Each quote carries its `score` and `matched_terms`, and the extract trace step reports
  candidates ranked, duplicates skipped and distinct sources — so the *selection* is explainable too.

Design choices that make "why" trustworthy:
- **Quotes are extracted, not generated.** The LLM only reasons over numbered evidence; it
  cannot introduce new quotes.
- **Citation verifier.** Hallucinated evidence ids are dropped and penalise confidence (logged in the trace).
- **Transparent confidence.** Coverage × diversity × citation rate, all shown in the verify step.
- **Safe fetching.** Only public http(s) URLs; private/loopback hosts are blocked (SSRF guard); size and time limits.

## Run (zero cost, Python 3.10+, stdlib only)

```bash
cd app
python server.py            # http://127.0.0.1:8787  (click "Load sample" → "Investigate")
python cli.py "Should I bid on this n8n freelance job?" \
  --snippet-file samples/freelance_job.txt --snippet-file samples/my_profile.txt \
  --url https://en.wikipedia.org/wiki/N8n --md report.md
python -m unittest discover -s tests -t .   # 23 tests, no network/key needed
```

### LLM modes
- **Stub (default when no key):** fully deterministic, offline-friendly; used by tests and demos.
- **Live:** any OpenAI-compatible `/chat/completions` endpoint. Copy `.env.example` to `.env`
  (gitignored) or set env vars:
  `EVIDENCE_LLM_BASE_URL`, `EVIDENCE_LLM_API_KEY`, `EVIDENCE_LLM_MODEL` (also accepts `OPENAI_*` / `NEBIUS_*`).
  Force a mode with `EVIDENCE_MODE=stub|live`. If the LLM call fails, the agent falls back to the
  deterministic path and records the fallback in the trace. Keys are never printed or returned by the API.

## API
- `GET /api/health` → `{mode, model, key_present, sponsors}`
- `POST /api/ask` `{question, snippets:[], urls:[], use_web:bool}` → result JSON (+ `why_graph`, `mermaid`, `markdown`)
- `POST /api/report` (result JSON) → markdown

## Demo video & submission
- **Watch:** https://vimeo.com/1239163509 (2:53)  ·  **Slide deck:** [`docs/evidence_desk_deck.pdf`](docs/evidence_desk_deck.pdf)
- **Demo (2:53, voiceover):** real headless-Chrome screenshots of one live run with NVIDIA Nemotron 3 Nano
  on Nebius Token Factory, narrated with free edge-tts. Narration script and timings:
  [`demo/NARRATION.md`](demo/NARRATION.md). Rebuild with `demo/capture.py` (server running),
  `demo/slides.py`, `demo/build.py` (needs Playwright + Chrome, ffmpeg, edge-tts).
- **Track 02 submission copy:** [`docs/DEVPOST.md`](docs/DEVPOST.md).
- Latest live sample report (same run as the video): [`samples/sample_report_live.md`](samples/sample_report_live.md).

## Sponsor tech: Meterless, Zetaris, NVIDIA, Cursor (honest status)

| Sponsor | Status | Where |
|---|---|---|
| **Meterless** | **Integrated** (open-source H-MEM engine, no key, zero cost) | `meterless/bridge.ts`, `MeterlessMemory` in `evidence_desk/sponsors.py`, `memory` + `remember` trace steps |
| **Zetaris** | **Not integrated** — adapter slot only, no calls made | `ZetarisAdapter` in `evidence_desk/sponsors.py` |
| **NVIDIA** | Integrated — Nemotron 3 Nano 30B-A3B is the live model | `evidence_desk/llm.py` via Nebius Token Factory |
| **Cursor** | Used to build the project | — |

**Meterless H-MEM case memory.** Evidence Desk remembers what it has already *verified*:
- After **verify**, the decision and each kept claim (with its verbatim-verified quote and source) are
  stored via H-MEM's `MemoryStoreService`; every write lands in H-MEM's append-only `TrustLedger`.
- At the start of the next investigation, a **memory** step queries H-MEM's `MemoryRetrievalService`
  and lists ranked prior findings (memory ids, relevance, ledger entries) in the explain-why trace.
- Recalled memories are **context only**: they are never cited as evidence, so the "every claim
  traces to a verbatim quote in this run's sources" guarantee is unchanged.
- The engine is TypeScript; Python talks to it with one JSON request per call over stdin/stdout.
  If Node or the engine is missing, the steps are simply skipped and the agent still works.

Setup (Node 18+):
```bash
cd app/meterless && npm install && npm run setup   # vendors github.com/Meterless/Meterless engines/hmem/reference into vendor/ (gitignored)
```
State lives in `app/.evidence-memory/` (gitignored; override with `EVIDENCE_MEMORY_DIR`). Disable with `EVIDENCE_MEMORY=off`.
`tests/test_agent.py::TestMeterlessMemory` does a real remember → recall round trip when the engine is vendored.

**Zetaris (not integrated).** Hackathon accounts need either your own AWS account linked to create a
cluster, or a local Docker install (~16 GB RAM). Neither fit this zero-cost, no-card build, so no
Zetaris code runs. `ZetarisAdapter` marks the integration point: any object with
`name` + `search(question, limit) -> [Source]` passed as `EvidenceDesk(source_adapters=[...])` has its
sources run through the same extract → verify pipeline (ids `Z1`, `Z2`…).

**Usage meter.** `LocalMeter` records per-LLM-call tokens and latency (never the key) for the conclude
step. (`MeterlessMeter` is a legacy name for that same local meter; nothing is sent anywhere.)

## Dependencies
- Core agent, server, CLI, tests: Python 3.10+ standard library only.
- Optional live LLM: any OpenAI-compatible endpoint key (free Nebius credits were used).
- Optional Meterless memory: Node 18+, `tsx` (installed by `npm install`), H-MEM reference (Apache-2.0).
- Demo rebuild only: Playwright + Chrome, ffmpeg, edge-tts.

## Roadmap
- Zetaris adapter once a free runtime is available; H-MEM feedback + sleep-cycle consolidation
- More keyless sources; contradiction detection between sources
- Per-claim confidence in the why-graph

## License
MIT
