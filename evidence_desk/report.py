"""Markdown report export."""
from __future__ import annotations


def to_markdown(r: dict) -> str:
    ev = {e["id"]: e for e in r.get("evidence", [])}
    L = [f"# Evidence Desk report", "", f"**Question:** {r['question']}", "",
         f"**Recommendation:** {r['recommendation']}", "",
         f"**Confidence:** {r['confidence']} ({r['confidence_label']}) · mode: {r['mode']} · model: {r['model']}", "",
         "## Why (claims → evidence)"]
    for c in r.get("reasoning", []):
        L.append(f"- {c['claim']} " + " ".join(f"[{i}]" for i in c["evidence_ids"]))
    L += ["", "## Evidence"]
    for e in r.get("evidence", []):
        L.append(f"- **[{e['id']}]** “{e['quote']}” — [{e['source_title']}]({e['url']}) _(for: {e['sub_question']})_")
    L += ["", "## Open risks"] + [f"- {x}" for x in r.get("risks", [])]
    L += ["", "## Next actions"] + [f"{i+1}. {x}" for i, x in enumerate(r.get("next_actions", []))]
    L += ["", "## Explain-why trace"]
    for t in r.get("trace", []):
        L.append(f"{t['n']}. **{t['stage']}** — {t['summary']}")
    L += ["", "## Sources"]
    for s in r.get("sources", []):
        L.append(f"- {s['id']} ({s['kind']}, {s['status']}): [{s['title']}]({s['url']})")
    return "\n".join(L) + "\n"
