import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from evidence_desk.agent import EvidenceDesk
from evidence_desk.config import Settings
from evidence_desk.llm import extract_json
from evidence_desk.report import to_markdown
from evidence_desk.retrieval import html_to_text, is_safe_url, FetchError

ROOT = Path(__file__).resolve().parent.parent
STUB = Settings(mode="stub", base_url="", api_key="", model="")
JOB = (ROOT / "samples" / "freelance_job.txt").read_text()
ME = (ROOT / "samples" / "my_profile.txt").read_text()
FAKE_HTML = ("<html><head><title>n8n docs</title><script>var x=1;</script></head><body>"
             "<p>n8n is a free and open workflow automation tool with strong community support.</p>"
             "<p>Self-hosting n8n requires a server and some maintenance risk.</p></body></html>")


def fake_getter(url):
    if "example.test" in url:
        return "text/html", FAKE_HTML
    raise FetchError("fetch failed: offline test")


def run(**kw):
    return EvidenceDesk(STUB, getter=fake_getter).run("Should I bid on this n8n freelance job?", **kw).to_dict()


class TestAgent(unittest.TestCase):
    def test_stub_plan_deterministic(self):
        d = EvidenceDesk(STUB)
        self.assertEqual(d.stub_plan("Should I bid?"), d.stub_plan("Should I bid?"))
        self.assertEqual(len(d.stub_plan("Should I bid on this job?")), 4)

    def test_full_run_has_cited_verbatim_evidence(self):
        r = run(snippets=[JOB, ME])
        self.assertEqual(r["mode"], "stub")
        self.assertTrue(r["evidence"])
        texts = {"S1": JOB.strip(), "S2": ME.strip()}
        for e in r["evidence"]:
            self.assertIn(e["quote"], texts[e["source_id"]])
            self.assertTrue(e["url"].startswith("pasted:"))
        ids = {e["id"] for e in r["evidence"]}
        for c in r["reasoning"]:
            self.assertTrue(set(c["evidence_ids"]) <= ids)
        self.assertGreater(r["confidence"], 0)
        self.assertTrue(r["risks"] and r["next_actions"])

    def test_trace_order(self):
        r = run(snippets=[JOB])
        self.assertEqual([t["stage"] for t in r["trace"]],
                         ["plan", "retrieve", "extract", "synthesize", "verify", "conclude"])
        self.assertEqual([t["n"] for t in r["trace"]], list(range(1, 7)))

    def test_deterministic_output(self):
        a, b = run(snippets=[JOB, ME]), run(snippets=[JOB, ME])
        strip = lambda r: {k: v for k, v in r.items() if k != "trace"}
        self.assertEqual(strip(a), strip(b))

    def test_url_source_and_failed_fetch(self):
        r = run(urls=["https://example.test/n8n", "https://unreachable.test/x"])
        st = {s["id"]: s["status"] for s in r["sources"]}
        self.assertEqual(st["U1"], "ok")
        self.assertNotEqual(st["U2"], "ok")
        self.assertTrue(any(e["source_id"] == "U1" for e in r["evidence"]))

    def test_no_input_low_confidence(self):
        r = run()
        self.assertEqual(r["confidence"], 0.0)
        self.assertIn("Insufficient", r["recommendation"])

    def test_hallucinated_citation_dropped(self):
        class FakeLLM:
            def chat_json(self, system, user, max_tokens=0):
                if "planner" in system:
                    return {"sub_questions": ["What does the job require?", "What are the risks?"]}
                return {"recommendation": "Bid.", "reasoning": [
                    {"claim": "real", "evidence_ids": ["E1"]}, {"claim": "fake", "evidence_ids": ["E999"]}],
                    "risks": ["r"], "next_actions": ["n"]}
        r = EvidenceDesk(STUB, getter=fake_getter, llm=FakeLLM()).run("Bid on n8n job?", [JOB]).to_dict()
        self.assertEqual([c["claim"] for c in r["reasoning"]], ["real"])
        verify = [t for t in r["trace"] if t["stage"] == "verify"][0]
        self.assertEqual(len(verify["detail"]["dropped_claims"]), 1)


class TestUtils(unittest.TestCase):
    def test_html_to_text(self):
        title, text = html_to_text(FAKE_HTML)
        self.assertEqual(title, "n8n docs")
        self.assertNotIn("var x", text)
        self.assertIn("workflow automation", text)

    def test_ssrf_guard(self):
        for u in ["http://127.0.0.1/", "http://localhost:8787/", "file:///etc/passwd", "http://10.0.0.1/", "ftp://x"]:
            self.assertFalse(is_safe_url(u), u)

    def test_extract_json(self):
        self.assertEqual(extract_json('<think>hmm {x}</think>```json\n{"a": 1}\n```'), {"a": 1})

    def test_markdown_report(self):
        md = to_markdown(run(snippets=[JOB, ME]))
        for h in ["# Evidence Desk report", "## Evidence", "## Explain-why trace", "## Open risks", "## Next actions"]:
            self.assertIn(h, md)
        self.assertIn("[E1]", md)


class TestServer(unittest.TestCase):
    def test_api_ask_and_index(self):
        from server import make_handler
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(STUB, getter=fake_getter))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            self.assertIn(b"Evidence", urllib.request.urlopen(base + "/").read())
            h = json.loads(urllib.request.urlopen(base + "/api/health").read())
            self.assertEqual(h["mode"], "stub")
            self.assertNotIn("api_key", h)
            req = urllib.request.Request(base + "/api/ask", data=json.dumps(
                {"question": "Should I bid?", "snippets": [JOB]}).encode(), headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req).read())
            self.assertIn("markdown", d)
            self.assertTrue(d["evidence"])
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
