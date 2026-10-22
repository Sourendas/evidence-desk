"""Markdown report export and the why-graph (recommendation → claims → verbatim quotes → sources)."""
from __future__ import annotations

import re


def _short(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def why_graph(r: dict) -> dict:
    """Build a 4-layer graph: recommendation → claims → cited evidence quotes → sources.

    Only evidence actually cited by a verified claim is drawn; uncited evidence is counted so the
    reader can see what the agent looked at but did not rely on.
    """
    ev = {e["id"]: e for e in r.get("evidence", [])}
    src = {s["id"]: s for s in r.get("sources", [])}
    nodes = [{"id": "R", "layer": 0, "kind": "recommendation", "label": r.get("recommendation", ""),
              "confidence": r.get("confidence"), "confidence_label": r.get("confidence_label")}]
    edges, seen_ev, seen_src = [], [], []
    for i, c in enumerate(r.get("reasoning", []), 1):
        cid = f"C{i}"
        nodes.append({"id": cid, "layer": 1, "kind": "claim", "label": c.get("claim", "")})
        edges.append({"from": "R", "to": cid})
        for eid in c.get("evidence_ids", []):
            if eid not in ev:
                continue
            edges.append({"from": cid, "to": eid, "polarity": ev[eid].get("polarity", 0)})
            if eid not in seen_ev:
                seen_ev.append(eid)
    for eid in seen_ev:
        e = ev[eid]
        nodes.append({"id": eid, "layer": 2, "kind": "evidence", "label": e["quote"],
                      "polarity": e.get("polarity", 0), "source_id": e["source_id"]})
        if e["source_id"] not in seen_src:
            seen_src.append(e["source_id"])
        edges.append({"from": eid, "to": "src:" + e["source_id"]})
    for sid in seen_src:
        s = src.get(sid, {"title": sid, "url": "", "kind": "?"})
        nodes.append({"id": "src:" + sid, "layer": 3, "kind": "source", "label": f"{sid} · {s.get('title', sid)}",
                      "url": s.get("url", ""), "source_kind": s.get("kind", "")})
    # dedupe edges, keep order
    out, seen = [], set()
    for e in edges:
        k = (e["from"], e["to"])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return {"nodes": nodes, "edges": out,
            "uncited_evidence": [i for i in ev if i not in seen_ev],
            "stats": {"claims": len(r.get("reasoning", [])), "cited_quotes": len(seen_ev),
                      "sources": len(seen_src)}}


def _mm(text: str, n: int) -> str:
    t = _short(text, n)
    for a, b in (('"', "#quot;"), ("<", "#lt;"), (">", "#gt;"), ("[", "("), ("]", ")"), ("|", "/")):
        t = t.replace(a, b)
    return t


def to_mermaid(r: dict, graph: dict | None = None) -> str:
    """Mermaid flowchart text for the why-graph (renders natively on GitHub)."""
    g = graph or why_graph(r)
    nid = lambda x: re.sub(r"[^A-Za-z0-9_]", "_", x)
    L = ["flowchart LR"]
    for n in g["nodes"]:
        k = n["kind"]
        if k == "recommendation":
            L.append(f'  {nid(n["id"])}{{{{"{_mm(n["label"], 70)} · conf {n.get("confidence")}"}}}}')
        elif k == "claim":
            L.append(f'  {nid(n["id"])}["{n["id"]}: {_mm(n["label"], 60)}"]')
        elif k == "evidence":
            L.append(f'  {nid(n["id"])}("{n["id"]}: “{_mm(n["label"], 60)}”")')
        else:
            L.append(f'  {nid(n["id"])}[("{_mm(n["label"], 45)}")]')
    for e in g["edges"]:
        arrow = "-- supports -->" if e.get("polarity", 0) > 0 else "-- cautions -->" if e.get("polarity", 0) < 0 else "-->"
        L.append(f'  {nid(e["from"])} {arrow} {nid(e["to"])}')
    L += ["  classDef claim fill:#1e2440,stroke:#7c9cff,color:#e8eaf6",
          "  classDef ev fill:#14261f,stroke:#4cd39b,color:#e8eaf6",
          "  classDef src fill:#262b45,stroke:#9aa0c3,color:#e8eaf6"]
    for n in g["nodes"]:
        cls = {"claim": "claim", "evidence": "ev", "source": "src"}.get(n["kind"])
        if cls:
            L.append(f"  class {nid(n['id'])} {cls}")
    return "\n".join(L)


def to_markdown(r: dict) -> str:
    L = [f"# Evidence Desk report", "", f"**Question:** {r['question']}", "",
         f"**Recommendation:** {r['recommendation']}", "",
         f"**Confidence:** {r['confidence']} ({r['confidence_label']}) · mode: {r['mode']} · model: {r['model']}", "",
         "## Why (claims → evidence)"]
    usage = next((t.get("detail", {}).get("usage") for t in r.get("trace", []) if t.get("stage") == "conclude"), None)
    if usage and usage.get("llm_calls"):
        L[-1:-1] = [f"**LLM usage (metered):** {usage['llm_calls']} call(s) · {usage['prompt_tokens']} prompt + "
                    f"{usage['completion_tokens']} completion tokens · {usage['llm_ms']} ms", ""]
    for c in r.get("reasoning", []):
        L.append(f"- {c['claim']} " + " ".join(f"[{i}]" for i in c["evidence_ids"]))
    g = why_graph(r)
    L += ["", "## Why-graph (recommendation → claims → quotes → sources)", "",
          f"{g['stats']['claims']} claim(s) rest on {g['stats']['cited_quotes']} cited quote(s) from "
          f"{g['stats']['sources']} source(s)"
          + (f"; uncited evidence: {', '.join(g['uncited_evidence'])}." if g["uncited_evidence"] else "."),
          "", "```mermaid", to_mermaid(r, g), "```"]
    L += ["", "## Evidence"]
    for e in r.get("evidence", []):
        why = f" · matched: {', '.join(e['matched_terms'])}" if e.get("matched_terms") else ""
        L.append(f"- **[{e['id']}]** “{e['quote']}” — [{e['source_title']}]({e['url']}) "
                 f"_(for: {e['sub_question']}; score {e.get('score')}{why})_")
    L += ["", "## Open risks"] + [f"- {x}" for x in r.get("risks", [])]
    L += ["", "## Next actions"] + [f"{i+1}. {x}" for i, x in enumerate(r.get("next_actions", []))]
    L += ["", "## Explain-why trace"]
    for t in r.get("trace", []):
        L.append(f"{t['n']}. **{t['stage']}** — {t['summary']}")
    L += ["", "## Sources"]
    for s in r.get("sources", []):
        L.append(f"- {s['id']} ({s['kind']}, {s['status']}): [{s['title']}]({s['url']})")
    return "\n".join(L) + "\n"
