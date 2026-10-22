import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from evidence_desk.agent import EvidenceDesk
from evidence_desk.config import Settings
from evidence_desk.llm import extract_json
from evidence_desk.report import to_markdown, to_mermaid, why_graph
from evidence_desk.retrieval import Source
from evidence_desk.sponsors import LocalMeter, ZetarisAdapter
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


class FixedPlan:
    """Fake LLM: fixed sub-questions, no synthesis (forces deterministic synthesizer)."""
    def __init__(self, subs):
        self.subs = subs

    def chat_json(self, system, user, max_tokens=0):
        if "planner" in system:
            return {"sub_questions": self.subs}
        return {}


class TestQuotePicking(unittest.TestCase):
    def desk(self, subs, **kw):
        return EvidenceDesk(STUB, getter=fake_getter, llm=FixedPlan(subs), **kw)

    def test_near_duplicates_skipped(self):
        a = "The n8n job budget is 150 dollars fixed price for the workflow build."
        b = "The n8n job budget is 150 dollars fixed price for this workflow build."
        c = "The n8n client has twelve past hires and a strong rating on the platform."
        r = self.desk(["What is the n8n job budget?"]).run("n8n job?", [a, b, c]).to_dict()
        quotes = [e["quote"] for e in r["evidence"]]
        self.assertEqual(len(quotes), len(set(quotes)))
        self.assertFalse(a in quotes and b in quotes, quotes)
        ext = [t for t in r["trace"] if t["stage"] == "extract"][0]["detail"]["ranking"]
        self.assertGreaterEqual(ext["near_duplicates_skipped"] + ext["already_used_skipped"], 1)

    def test_prefers_diverse_sources(self):
        s1 = ("Kafka retention can be configured per topic for streaming data. "
              "Kafka retention defaults to seven days for streaming topics. "
              "Kafka retention may also be limited by total bytes for streaming topics.")
        s2 = "Kafka retention settings for streaming topics are documented in the broker guide."
        r = self.desk(["How does Kafka retention work for streaming topics?"]).run("Kafka retention?", [s1, s2]).to_dict()
        srcs = {e["source_id"] for e in r["evidence"]}
        self.assertEqual(srcs, {"S1", "S2"})
        self.assertLessEqual(sum(1 for e in r["evidence"] if e["source_id"] == "S1"), 2)

    def test_relevance_ranking_and_matched_terms(self):
        text = ("The weather in the city was pleasant during the conference week. "
                "The conference registration fee is 200 dollars and is non-refundable. "
                "Lunch at the conference venue was served at noon.")
        r = self.desk(["What is the conference registration fee?"]).run("Attend the conference?", [text]).to_dict()
        top = r["evidence"][0]
        self.assertIn("registration fee", top["quote"])
        self.assertTrue({"registr", "fee"} <= set(top["matched_terms"]), top["matched_terms"])

    def test_risk_question_gets_risk_quote_without_topic_word(self):
        r = run(snippets=[JOB, ME])
        risk_sq = [s for s in r["sub_questions"] if "risk" in s.lower()][0]
        risk_ev = [e for e in r["evidence"] if e["sub_question"] == risk_sq]
        self.assertTrue(risk_ev and all(e["polarity"] <= 0 for e in risk_ev))
        self.assertEqual(len({e["sub_question"] for e in r["evidence"]}), len(r["sub_questions"]))

    def test_bibliography_lines_not_quoted(self):
        txt = ("n8n is a workflow automation tool used by many teams. Rapid Product Development with n8n (PDF). "
               "Birmingham, England: n8n Packt Publishing Ltd.")
        r = self.desk(["What is n8n?"]).run("n8n?", [txt]).to_dict()
        self.assertTrue(r["evidence"])
        for e in r["evidence"]:
            self.assertNotIn("(PDF)", e["quote"])
            self.assertNotIn("Publishing", e["quote"])


class TestWhyGraph(unittest.TestCase):
    def test_graph_layers_and_edges(self):
        r = run(snippets=[JOB, ME])
        g = why_graph(r)
        ids = {n["id"]: n for n in g["nodes"]}
        self.assertEqual(ids["R"]["layer"], 0)
        for e in g["edges"]:
            self.assertIn(e["from"], ids)
            self.assertIn(e["to"], ids)
            self.assertEqual(ids[e["to"]]["layer"], ids[e["from"]]["layer"] + 1)
        cited = {i for c in r["reasoning"] for i in c["evidence_ids"]}
        self.assertEqual({n["id"] for n in g["nodes"] if n["kind"] == "evidence"}, cited)
        self.assertEqual(set(g["uncited_evidence"]), {e["id"] for e in r["evidence"]} - cited)
        for n in g["nodes"]:
            if n["kind"] == "evidence":  # each quote links to its own source
                self.assertIn({"from": n["id"], "to": "src:" + n["source_id"]}, g["edges"])

    def test_mermaid_escaping_and_markdown(self):
        r = run(snippets=['The "n8n" job [urgent] pays well <fast> | remote and n8n experience is a benefit.', JOB])
        mm = to_mermaid(r)
        self.assertTrue(mm.startswith("flowchart LR"))
        body = "\n".join(l for l in mm.splitlines()[1:] if "[\"" in l or "(\"" in l)
        self.assertNotIn('"n8n"', body)
        self.assertNotIn("<fast>", body)
        md = to_markdown(r)
        self.assertIn("## Why-graph", md)
        self.assertIn("```mermaid\nflowchart LR", md)


class TestSponsorSlots(unittest.TestCase):
    def test_zetaris_off_by_default_and_noted(self):
        self.assertFalse(ZetarisAdapter(endpoint="", token="").enabled)
        r = EvidenceDesk(STUB, getter=fake_getter, source_adapters=[ZetarisAdapter(endpoint="", token="")]).run(
            "Bid?", [JOB]).to_dict()
        ret = [t for t in r["trace"] if t["stage"] == "retrieve"][0]["detail"]
        self.assertIn("skipped", ret["adapters"]["zetaris"])

    def test_custom_adapter_sources_are_cited(self):
        class Fake:
            name = "fake"
            def search(self, question, limit=3):
                return [Source("Z1", "zetaris", "Federated table: n8n jobs", "zetaris://demo/jobs",
                               "Federated data shows n8n freelance jobs grew strongly with strong demand this year.")]
        meter = LocalMeter()
        r = EvidenceDesk(STUB, getter=fake_getter, source_adapters=[Fake()], meter=meter).run(
            "Should I bid on this n8n freelance job?", [JOB]).to_dict()
        self.assertTrue(any(e["source_id"] == "Z1" for e in r["evidence"]))
        self.assertTrue(any(ev["type"] == "run" for ev in meter.events))


class TestLLMMetering(unittest.TestCase):
    def test_llm_call_metered_without_key(self):
        import io
        from unittest import mock
        from evidence_desk.llm import OpenAICompatLLM

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        body = json.dumps({"choices": [{"message": {"content": '{"ok": 1}'}, "finish_reason": "stop"}],
                           "usage": {"prompt_tokens": 11, "completion_tokens": 7}}).encode()
        meter = LocalMeter()
        llm = OpenAICompatLLM(Settings("live", "https://llm.invalid/v1", "sk-secret-test", "m"), meter=meter)
        with mock.patch("urllib.request.urlopen", return_value=Resp(body)):
            self.assertEqual(llm.chat_json("s", "u"), {"ok": 1})
        self.assertEqual(meter.summary()["prompt_tokens"], 11)
        self.assertEqual(meter.summary()["completion_tokens"], 7)
        self.assertNotIn("sk-secret-test", json.dumps(meter.events))


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
            self.assertTrue(d["why_graph"]["nodes"])
            self.assertTrue(d["mermaid"].startswith("flowchart LR"))
            self.assertIn("sponsors", h)
            self.assertTrue(d["evidence"])
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
