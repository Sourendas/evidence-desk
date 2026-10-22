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
 3. extract     → verbatim sentences scored per sub-question (never paraphrased → checkable)
 4. synthesize  → recommendation + claims, each claim must cite evidence ids (E1, E2…)
 5. verify      → drops claims citing non-existent evidence, re-checks every quote is
                  verbatim in its source, computes confidence from coverage, source
                  diversity and citation rate
 6. conclude    → final answer + markdown report
```

Every stage writes a numbered `trace` step (with timing and details), shown in the UI's
**Explain-why trace** panel and in the exported report.

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
python -m unittest discover -s tests -t .
```

### LLM modes
- **Stub (default when no key):** fully deterministic, offline-friendly; used by tests and demos.
- **Live:** any OpenAI-compatible `/chat/completions` endpoint. Copy `.env.example` to `.env`
  (gitignored) or set env vars:
  `EVIDENCE_LLM_BASE_URL`, `EVIDENCE_LLM_API_KEY`, `EVIDENCE_LLM_MODEL` (also accepts `OPENAI_*` / `NEBIUS_*`).
  Force a mode with `EVIDENCE_MODE=stub|live`. If the LLM call fails, the agent falls back to the
  deterministic path and records the fallback in the trace. Keys are never printed or returned by the API.

## API
- `GET /api/health` → `{mode, model, key_present}`
- `POST /api/ask` `{question, snippets:[], urls:[], use_web:bool}` → result JSON (+ `markdown`)
- `POST /api/report` (result JSON) → markdown

## Sponsor integration (planned slot)
Zetaris (federated data access) and Meterless (usage metering) integration is a **planned slot**:
`retrieval.py` is structured so a Zetaris-backed source can be added next to snippets/URLs/Wikipedia,
and the LLM layer is the hook point for Meterless metering. Not yet integrated — no accounts were
created and nothing paid is used.

## Roadmap
- Sponsor source adapters (Zetaris) + metering (Meterless)
- Decision-graph view (claims ↔ evidence ↔ sources)
- More keyless sources; better extractive ranking (BM25)
- Contradiction detection between sources

## License
MIT
