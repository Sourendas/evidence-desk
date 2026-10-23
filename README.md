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
python -m unittest discover -s tests -t .   # 22 stub-mode tests, no network/key needed
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
- **Demo (2:53, voiceover):** real headless-Chrome screenshots of one live run with NVIDIA Nemotron 3 Nano
  on Nebius Token Factory, narrated with free edge-tts. Narration script and timings:
  [`demo/NARRATION.md`](demo/NARRATION.md). Rebuild with `demo/capture.py` (server running),
  `demo/slides.py`, `demo/build.py` (needs Playwright + Chrome, ffmpeg, edge-tts).
- **Track 02 submission copy:** [`docs/DEVPOST.md`](docs/DEVPOST.md).
- Latest live sample report (same run as the video): [`samples/sample_report_live.md`](samples/sample_report_live.md).

## Sponsor integration (adapter slots)
`evidence_desk/sponsors.py` defines the integration points; nothing sponsor-side is called yet
(no accounts created, nothing paid):
- **Zetaris → `ZetarisAdapter` (evidence source).** Any object with `name` + `search(question, limit) -> [Source]`
  can be passed as `EvidenceDesk(source_adapters=[...])`; its sources go through the same
  extract → verify pipeline, so quotes are verbatim-checked and cited like any other source.
  The Zetaris adapter is off unless `ZETARIS_ENDPOINT` + `ZETARIS_TOKEN` are set, and the client
  itself is still a stub (records "skipped" in the retrieve trace step).
- **Meterless → `MeterlessMeter` (usage metering).** Every LLM call emits a usage event
  (model, prompt/completion tokens, latency — never the key) to a meter, plus one event per run.
  `LocalMeter` is always on and its totals appear in the conclude trace step and report; the
  Meterless meter is enabled by `METERLESS_API_KEY` but currently keeps events local only.

## Roadmap
- Real Zetaris + Meterless clients behind the existing slots (once sponsor access is available)
- More keyless sources; contradiction detection between sources
- Per-claim confidence in the why-graph

## License
MIT
