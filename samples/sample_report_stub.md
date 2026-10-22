# Evidence Desk report

**Question:** Should I bid on this n8n freelance job?

**Recommendation:** Lean NO / proceed with caution: the evidence surfaces more risks or costs than benefits.

**Confidence:** 0.92 (high) · mode: stub · model: deterministic-stub

## Why (claims → evidence)
- 1 quote(s) point to benefits or opportunities. [E2]
- 4 quote(s) point to risks, costs or requirements. [E4] [E5] [E6] [E7]
- Additional factual context relevant to the question. [E1] [E3]

## Why-graph (recommendation → claims → quotes → sources)

3 claim(s) rest on 7 cited quote(s) from 2 source(s).

```mermaid
flowchart LR
  R{{"Lean NO / proceed with caution: the evidence surfaces more risks or c… · conf 0.92"}}
  C1["C1: 1 quote(s) point to benefits or opportunities."]
  C2["C2: 4 quote(s) point to risks, costs or requirements."]
  C3["C3: Additional factual context relevant to the question."]
  E2("E2: “My hourly target is $25, so a $150 job of about 6 hours is…”")
  E4("E4: “I have no reviews on this platform yet, which is a risk for…”")
  E5("E5: “Requirements: must have prior n8n experience and provide tw…”")
  E6("E6: “Proposals so far: 35 to 50, which is competitive.”")
  E7("E7: “The client mentions previous freelancers failed to deliver…”")
  E1("E1: “Job: Build an n8n workflow that syncs Shopify orders to Goo…”")
  E3("E3: “I have built three n8n automation workflows, including a Sh…”")
  src_S2[("S2 · Pasted snippet 2: I have built three n8…")]
  src_S1[("S1 · Pasted snippet 1: Job: Build an n8n wor…")]
  R --> C1
  C1 -- supports --> E2
  R --> C2
  C2 -- cautions --> E4
  C2 -- cautions --> E5
  C2 -- cautions --> E6
  C2 -- cautions --> E7
  R --> C3
  C3 --> E1
  C3 --> E3
  E2 --> src_S2
  E4 --> src_S2
  E5 --> src_S1
  E6 --> src_S1
  E7 --> src_S1
  E1 --> src_S1
  E3 --> src_S2
  classDef claim fill:#1e2440,stroke:#7c9cff,color:#e8eaf6
  classDef ev fill:#14261f,stroke:#4cd39b,color:#e8eaf6
  classDef src fill:#262b45,stroke:#9aa0c3,color:#e8eaf6
  class C1 claim
  class C2 claim
  class C3 claim
  class E2 ev
  class E4 ev
  class E5 ev
  class E6 ev
  class E7 ev
  class E1 ev
  class E3 ev
  class src_S2 src
  class src_S1 src
```

## Evidence
- **[E1]** “Job: Build an n8n workflow that syncs Shopify orders to Google Sheets and sends a Slack alert.” — [Pasted snippet 1: Job: Build an n8n workflow that syncs Shopify orders to Google Sheets ](pasted:snippet-1) _(for: What are the key facts about: bid n8n freelance job?; score 2.25 · matched: job, n8n)_
- **[E2]** “My hourly target is $25, so a $150 job of about 6 hours is a good fit and profitable.” — [Pasted snippet 2: I have built three n8n automation workflows, including a Shopify order](pasted:snippet-2) _(for: What benefits or opportunities support: bid n8n freelance job?; score 2.3 · matched: job)_
- **[E3]** “I have built three n8n automation workflows, including a Shopify order notifier, and they are on GitHub.” — [Pasted snippet 2: I have built three n8n automation workflows, including a Shopify order](pasted:snippet-2) _(for: What benefits or opportunities support: bid n8n freelance job?; score 1.13 · matched: n8n)_
- **[E4]** “I have no reviews on this platform yet, which is a risk for winning competitive bids.” — [Pasted snippet 2: I have built three n8n automation workflows, including a Shopify order](pasted:snippet-2) _(for: What risks, costs or requirements count against: bid n8n freelance job?; score 4.56 · matched: bid)_
- **[E5]** “Requirements: must have prior n8n experience and provide two portfolio links.” — [Pasted snippet 1: Job: Build an n8n workflow that syncs Shopify orders to Google Sheets ](pasted:snippet-1) _(for: What risks, costs or requirements count against: bid n8n freelance job?; score 1.97 · matched: n8n)_
- **[E6]** “Proposals so far: 35 to 50, which is competitive.” — [Pasted snippet 1: Job: Build an n8n workflow that syncs Shopify orders to Google Sheets ](pasted:snippet-1) _(for: What risks, costs or requirements count against: bid n8n freelance job?; score 0.53 · matched: (risk/benefit cue))_
- **[E7]** “The client mentions previous freelancers failed to deliver on time, so the deadline is strict.” — [Pasted snippet 1: Job: Build an n8n workflow that syncs Shopify orders to Google Sheets ](pasted:snippet-1) _(for: What should be done next regarding: bid n8n freelance job?; score 2.07 · matched: freelan)_

## Open risks
- I have no reviews on this platform yet, which is a risk for winning competitive bids. [E4]
- Requirements: must have prior n8n experience and provide two portfolio links. [E5]
- Proposals so far: 35 to 50, which is competitive. [E6]
- The client mentions previous freelancers failed to deliver on time, so the deadline is strict. [E7]

## Next actions
1. Verify each cited quote against its source link.
2. Resolve or accept each listed risk before committing.
3. Re-run Evidence Desk with any new information.

## Explain-why trace
1. **plan** — Split the question into 4 sub-questions using deterministic template planner.
2. **retrieve** — Collected 2 usable source(s) out of 2 attempted.
3. **extract** — Ranked 8 candidate sentence(s) with BM25 + diversity; picked 7 verbatim quote(s) from 2 source(s), skipped 0 near-duplicate(s); 4/4 sub-questions have support.
4. **synthesize** — Drafted recommendation using deterministic polarity-weighted synthesizer.
5. **verify** — Checked citations: 3 claim(s) kept, 0 dropped for missing evidence; 7/7 quotes verified verbatim in source. Confidence 0.92 (high).
6. **conclude** — Final: Lean NO / proceed with caution: the evidence surfaces more risks or costs than benefits.

## Sources
- S1 (snippet, ok): [Pasted snippet 1: Job: Build an n8n workflow that syncs Shopify orders to Google Sheets ](pasted:snippet-1)
- S2 (snippet, ok): [Pasted snippet 2: I have built three n8n automation workflows, including a Shopify order](pasted:snippet-2)
