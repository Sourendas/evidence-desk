"""Evidence Desk agent loop: plan -> retrieve -> extract -> synthesize -> verify.

Every step appends to an ordered "why trace" so a reader can follow exactly how the
conclusion was reached. Evidence quotes are always verbatim spans of fetched text
(extracted deterministically), so citations can be checked against their source.
"""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field

from .config import Settings, get_settings
from .llm import LLMError, OpenAICompatLLM
from .retrieval import Source, fetch_url, http_get, wikipedia_search

STOPWORDS = set(
    """a an the and or but if of to in on for with by at from is are was were be been being this that
    these those it its as do does did should would could can will i me my we our you your they them their
    what which who whom how why when where than then there here about into over under also just not no yes
    vs versus any some more most much many very so such""".split()
)
POSITIVE = {"free", "open", "eligible", "growing", "growth", "strong", "benefit", "benefits", "prize",
            "award", "support", "supports", "recommended", "popular", "fast", "cheap", "remote", "worldwide",
            "profitable", "demand", "simple", "easy", "success", "successful", "advantage", "opportunity"}
NEGATIVE = {"risk", "risks", "fee", "fees", "paid", "requires", "required", "limited", "restricted",
            "expensive", "decline", "declining", "ban", "banned", "fail", "failure", "scam", "card",
            "deadline", "ineligible", "costly", "difficult", "competition", "competitive", "unclear",
            "lawsuit", "warning", "penalty", "loss"}


@dataclass
class Evidence:
    id: str
    sub_question: str
    source_id: str
    source_title: str
    url: str
    quote: str
    score: float
    polarity: int  # +1 supports, -1 cautions, 0 neutral


@dataclass
class TraceStep:
    n: int
    stage: str
    summary: str
    detail: dict = field(default_factory=dict)
    ms: int = 0


@dataclass
class Result:
    question: str
    mode: str
    model: str
    sub_questions: list
    recommendation: str
    confidence: float
    confidence_label: str
    reasoning: list  # [{claim, evidence_ids}]
    evidence: list
    risks: list
    next_actions: list
    sources: list
    trace: list

    def to_dict(self) -> dict:
        return asdict(self)


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9][a-z0-9\-\+\.]*[a-z0-9]|[a-z0-9]", text.lower()) if t not in STOPWORDS]


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    out = []
    for p in parts:
        p = re.sub(r"\[\d+\]", "", p).strip()  # drop footnote markers like [12]
        if not 25 <= len(p) <= 400 or p[0] in "\"'^|*[":
            continue  # skip citation titles, table rows, bullets of link lists
        if re.match(r"(From Wikipedia|Jump to|Retrieved|Archived from|This article)", p):
            continue
        if sum(c.isalpha() for c in p) / len(p) < 0.6:
            continue
        out.append(p)
    return out


def label(conf: float) -> str:
    return "high" if conf >= 0.7 else "medium" if conf >= 0.45 else "low"


class EvidenceDesk:
    def __init__(self, settings: Settings | None = None, getter=http_get, llm=None):
        self.settings = settings or get_settings()
        self.getter = getter
        if llm is not None:
            self.llm = llm
        elif self.settings.live:
            self.llm = OpenAICompatLLM(self.settings)
        else:
            self.llm = None
        self.trace: list[TraceStep] = []

    # ---- trace helper -------------------------------------------------
    def _log(self, stage: str, summary: str, t0: float, **detail) -> None:
        self.trace.append(TraceStep(len(self.trace) + 1, stage, summary, detail, int((time.time() - t0) * 1000)))

    # ---- 1. plan ------------------------------------------------------
    def stub_plan(self, question: str) -> list[str]:
        q = question.strip().rstrip("?")
        core = " ".join(tokens(q)[:8]) or q
        return [
            f"What are the key facts about: {core}?",
            f"What benefits or opportunities support: {core}?",
            f"What risks, costs or requirements count against: {core}?",
            f"What should be done next regarding: {core}?",
        ]

    def plan(self, question: str, n_snippets: int, n_urls: int) -> list[str]:
        t0 = time.time()
        subs, how = None, "deterministic template planner"
        if self.llm:
            try:
                data = self.llm.chat_json(
                    "You are a research planner. Break the user's decision question into 3-5 short, "
                    "independently answerable sub-questions covering facts, benefits, risks/costs, and next steps. "
                    'Reply ONLY with JSON: {"sub_questions": ["..."]}',
                    question,
                    max_tokens=2000,
                )
                subs = [s for s in data.get("sub_questions", []) if isinstance(s, str) and s.strip()][:5]
                how = f"LLM planner ({self.settings.model})"
            except (LLMError, AttributeError) as e:
                how = f"LLM planner failed ({e}); fell back to template planner"
        if not subs:
            subs = self.stub_plan(question)
        self._log("plan", f"Split the question into {len(subs)} sub-questions using {how}.", t0,
                  sub_questions=subs, inputs={"snippets": n_snippets, "urls": n_urls})
        return subs

    # ---- 2. retrieve --------------------------------------------------
    def retrieve(self, question: str, snippets: list[str], urls: list[str], use_web: bool) -> list[Source]:
        t0 = time.time()
        sources: list[Source] = []
        for i, s in enumerate([s for s in snippets if s and s.strip()]):
            first = s.strip().splitlines()[0][:70]
            sources.append(Source(f"S{i+1}", "snippet", f"Pasted snippet {i+1}: {first}", f"pasted:snippet-{i+1}", s.strip()))
        for i, u in enumerate([u.strip() for u in urls if u and u.strip()][:6]):
            sources.append(fetch_url(u, f"U{i+1}", getter=self.getter))
        if use_web:
            query = " ".join(tokens(question)[:6])
            sources.extend(wikipedia_search(query, limit=2, getter=self.getter))
        ok = [s for s in sources if s.status == "ok" and s.text]
        self._log("retrieve", f"Collected {len(ok)} usable source(s) out of {len(sources)} attempted.", t0,
                  sources=[{"id": s.id, "kind": s.kind, "title": s.title, "url": s.url, "status": s.status,
                            "chars": len(s.text)} for s in sources])
        return sources

    # ---- 3. extract ---------------------------------------------------
    def extract(self, question: str, subs: list[str], sources: list[Source], per_sub: int = 3) -> list[Evidence]:
        t0 = time.time()
        qtok = set(tokens(question))
        evidence: list[Evidence] = []
        seen: set[str] = set()
        for sq in subs:
            stok = set(tokens(sq)) | qtok
            is_risk = any(w in sq.lower() for w in ("risk", "cost", "against", "requirement", "downside"))
            is_benefit = any(w in sq.lower() for w in ("benefit", "opportunit", "support", "upside"))
            cands = []
            for src in sources:
                if src.status != "ok":
                    continue
                for sent in split_sentences(src.text):
                    st = tokens(sent)
                    if not st:
                        continue
                    sset = set(st)
                    overlap = len(stok & sset)
                    if overlap == 0:
                        continue  # must share at least one content word with the (sub-)question
                    pos, neg = len(sset & POSITIVE), len(sset & NEGATIVE)
                    score = overlap + (1.5 * neg if is_risk else 0) + (1.5 * pos if is_benefit else 0)
                    score += 0.5 if src.kind == "snippet" else 0  # user-provided context first
                    if score <= 0.5:
                        continue
                    pol = 1 if pos > neg else -1 if neg > pos else 0
                    cands.append((score, sent, src, pol))
            cands.sort(key=lambda c: (-c[0], c[2].id, c[1]))
            taken = 0
            for score, sent, src, pol in cands:
                if sent in seen:
                    continue
                seen.add(sent)
                evidence.append(Evidence(f"E{len(evidence)+1}", sq, src.id, src.title, src.url, sent,
                                         round(score, 2), pol))
                taken += 1
                if taken >= per_sub:
                    break
        covered = len({e.sub_question for e in evidence})
        self._log("extract", f"Extracted {len(evidence)} verbatim evidence quote(s); {covered}/{len(subs)} "
                  f"sub-questions have support.", t0,
                  per_sub_question={sq: [e.id for e in evidence if e.sub_question == sq] for sq in subs})
        return evidence

    # ---- 4. synthesize ------------------------------------------------
    def stub_synthesize(self, question: str, subs: list[str], ev: list[Evidence], sources: list[Source]) -> dict:
        pos = [e for e in ev if e.polarity > 0]
        neg = [e for e in ev if e.polarity < 0]
        if not ev:
            rec = "Insufficient evidence: add snippets or URLs before deciding."
        elif len(pos) > len(neg):
            rec = "Lean YES: the supporting evidence outweighs the cautions, but address the listed risks first."
        elif len(neg) > len(pos):
            rec = "Lean NO / proceed with caution: the evidence surfaces more risks or costs than benefits."
        else:
            rec = "Undecided: evidence is balanced; resolve the open risks below before committing."
        reasoning = []
        if pos:
            reasoning.append({"claim": f"{len(pos)} quote(s) point to benefits or opportunities.",
                              "evidence_ids": [e.id for e in pos[:4]]})
        if neg:
            reasoning.append({"claim": f"{len(neg)} quote(s) point to risks, costs or requirements.",
                              "evidence_ids": [e.id for e in neg[:4]]})
        neutral = [e for e in ev if e.polarity == 0]
        if neutral:
            reasoning.append({"claim": "Additional factual context relevant to the question.",
                              "evidence_ids": [e.id for e in neutral[:3]]})
        risks = [f"{e.quote} [{e.id}]" for e in neg[:4]]
        missing = [sq for sq in subs if not any(e.sub_question == sq for e in ev)]
        risks += [f"No evidence found for: {sq}" for sq in missing]
        actions = ["Verify each cited quote against its source link."]
        if missing:
            actions.append("Paste a source that answers the uncovered sub-question(s).")
        if neg:
            actions.append("Resolve or accept each listed risk before committing.")
        actions.append("Re-run Evidence Desk with any new information.")
        return {"recommendation": rec, "reasoning": reasoning, "risks": risks, "next_actions": actions}

    def synthesize(self, question: str, subs: list[str], ev: list[Evidence], sources: list[Source]) -> dict:
        t0 = time.time()
        out, how = None, "deterministic polarity-weighted synthesizer"
        if self.llm and ev:
            ev_txt = "\n".join(f"[{e.id}] ({e.source_title}) \"{e.quote}\"" for e in ev)
            try:
                data = self.llm.chat_json(
                    "You are a careful analyst. Using ONLY the numbered evidence, answer the decision question. "
                    "Every claim must cite evidence ids like E1. Do not invent facts. Reply ONLY with JSON: "
                    '{"recommendation": "one or two sentences", "reasoning": [{"claim": "...", "evidence_ids": ["E1"]}], '
                    '"risks": ["..."], "next_actions": ["..."]}',
                    f"Question: {question}\nSub-questions: {subs}\nEvidence:\n{ev_txt}",
                    max_tokens=4000,
                )
                if isinstance(data, dict) and data.get("recommendation"):
                    out, how = data, f"LLM synthesizer ({self.settings.model})"
            except (LLMError, AttributeError) as e:
                how = f"LLM synthesizer failed ({e}); fell back to deterministic synthesizer"
        if out is None:
            out = self.stub_synthesize(question, subs, ev, sources)
        self._log("synthesize", f"Drafted recommendation using {how}.", t0,
                  recommendation=out.get("recommendation"))
        return out

    # ---- 5. verify ----------------------------------------------------
    def verify(self, draft: dict, subs: list[str], ev: list[Evidence], sources: list[Source]) -> tuple[dict, float]:
        t0 = time.time()
        valid = {e.id for e in ev}
        kept, dropped = [], []
        for r in draft.get("reasoning", []) or []:
            if not isinstance(r, dict):
                continue
            ids = [i for i in r.get("evidence_ids", []) if i in valid]
            (kept if ids else dropped).append({"claim": str(r.get("claim", "")), "evidence_ids": ids})
        draft["reasoning"] = kept
        draft["risks"] = [str(x) for x in (draft.get("risks") or [])]
        draft["next_actions"] = [str(x) for x in (draft.get("next_actions") or [])]
        src_text = {s.id: s.text for s in sources}
        verbatim = sum(1 for e in ev if e.quote in src_text.get(e.source_id, ""))
        coverage = len({e.sub_question for e in ev}) / max(1, len(subs))
        diversity = min(1.0, len({e.source_id for e in ev}) / 3)
        cited = len({i for r in kept for i in r["evidence_ids"]}) / max(1, len(ev))
        conf = 0.0 if not ev else round(0.15 + 0.4 * coverage + 0.25 * diversity + 0.2 * cited, 2)
        if dropped:
            conf = round(max(0.0, conf - 0.1 * len(dropped)), 2)
        conf = min(conf, 0.95)
        self._log("verify", f"Checked citations: {len(kept)} claim(s) kept, {len(dropped)} dropped for missing "
                  f"evidence; {verbatim}/{len(ev)} quotes verified verbatim in source. Confidence {conf} "
                  f"({label(conf)}).", t0,
                  coverage=round(coverage, 2), source_diversity=round(diversity, 2),
                  cited_fraction=round(cited, 2), dropped_claims=dropped)
        return draft, conf

    # ---- run ----------------------------------------------------------
    def run(self, question: str, snippets: list[str] | None = None, urls: list[str] | None = None,
            use_web: bool = False) -> Result:
        self.trace = []
        snippets, urls = snippets or [], urls or []
        subs = self.plan(question, len(snippets), len(urls))
        sources = self.retrieve(question, snippets, urls, use_web)
        ev = self.extract(question, subs, sources)
        draft = self.synthesize(question, subs, ev, sources)
        final, conf = self.verify(draft, subs, ev, sources)
        t0 = time.time()
        self._log("conclude", f"Final: {final['recommendation']}", t0, confidence=conf)
        return Result(
            question=question,
            mode="live" if self.llm else "stub",
            model=self.settings.model if self.llm else "deterministic-stub",
            sub_questions=subs,
            recommendation=str(final["recommendation"]),
            confidence=conf,
            confidence_label=label(conf),
            reasoning=final["reasoning"],
            evidence=[asdict(e) for e in ev],
            risks=final["risks"],
            next_actions=final["next_actions"],
            sources=[{"id": s.id, "kind": s.kind, "title": s.title, "url": s.url, "status": s.status} for s in sources],
            trace=[asdict(t) for t in self.trace],
        )
