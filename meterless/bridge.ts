// Evidence Desk <-> Meterless H-MEM bridge (open-source engine, Apache-2.0, zero API keys).
// Reads one JSON request on stdin, writes one JSON reply on stdout.
//   {"op":"recall","question":"...","topN":3}
//   {"op":"remember","question":"...","recommendation":"...","confidence":0.8,
//    "findings":[{"claim":"...","quotes":["..."],"sources":["https://..."]}]}
//   {"op":"audit","id":"mem-1"}
// State persists in EVIDENCE_MEMORY_DIR (default ../.evidence-memory, gitignored).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const entry = path.join(here, "vendor", "hmem", "src", "index.ts");

async function main() {
  if (!fs.existsSync(entry)) {
    process.stdout.write(JSON.stringify({ ok: false, error: "H-MEM not vendored; run: cd meterless && npm install && npm run setup" }));
    return;
  }
  const { HMEM } = await import(pathToFileURL(entry).href);
  const req = JSON.parse(fs.readFileSync(0, "utf-8") || "{}");
  const dir = process.env.EVIDENCE_MEMORY_DIR || path.join(here, "..", ".evidence-memory");
  const hmem = new HMEM({ persistDir: dir });
  if (req.op === "recall") {
    // MemoryRetrievalService: hybrid ranking + trace.
    const r = hmem.query(String(req.question || ""), { topN: req.topN ?? 3, threshold: 0.1 });
    const memories = r.memories.map((m: any) => ({
      id: m.memory.id, relevance: Number(m.relevance.toFixed(3)), content: m.memory.content,
      source: m.memory.source, tags: m.memory.tags ?? [], confidence: m.memory.confidence,
      ledger: hmem.ledger.history(m.memory.id).length,
    }));
    process.stdout.write(JSON.stringify({ ok: true, engine: "meterless/h-mem", strategy: r.trace?.strategy, memories }));
  } else if (req.op === "remember") {
    // MemoryStoreService + TrustLedgerService: one record per verified finding.
    const ids: string[] = [];
    const conf = Math.max(0.1, Math.min(1, Number(req.confidence ?? 0.5)));
    const head = hmem.add({ content: `Decision on "${req.question}": ${req.recommendation}`, type: "general",
      source: "evidence-desk:conclude", confidence: conf, tags: ["decision"] });
    ids.push(head.id);
    for (const f of req.findings ?? []) {
      const q = (f.quotes ?? [])[0];
      const rec = hmem.add({ content: `${f.claim}${q ? ` — verified quote: "${q}"` : ""}`, type: "general",
        source: `evidence-desk:verified:${(f.sources ?? [])[0] ?? "pasted"}`, confidence: conf,
        tags: ["verified-finding"], derivedFrom: [head.id] });
      ids.push(rec.id);
    }
    process.stdout.write(JSON.stringify({ ok: true, engine: "meterless/h-mem", stored: ids }));
  } else if (req.op === "audit") {
    process.stdout.write(JSON.stringify({ ok: true, history: hmem.ledger.history(String(req.id)) }));
  } else {
    process.stdout.write(JSON.stringify({ ok: false, error: "unknown op" }));
  }
}
main().catch((e) => { process.stdout.write(JSON.stringify({ ok: false, error: String(e?.message ?? e) })); });
