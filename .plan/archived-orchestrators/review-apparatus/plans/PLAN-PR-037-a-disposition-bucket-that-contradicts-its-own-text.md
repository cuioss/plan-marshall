# PLAN-PR-037: A disposition bucket that contradicts its own text, and the reviewer metric that believes it

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-063` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1–D5 are carried there as D7–D11 and D0 folds into that plan's merged D0
> gate. ⛔ **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of every
> deliverable body, and `PLAN-PR-063` points here rather than retyping it.

epic: review-apparatus
workstream: WS-03

> Staged plan spec, created 2026-08-23 from inbox message `truthful-signals-029`. The forwarding
> orchestrator explicitly labelled its claim **a lead, not a fact** and performed no verification.
> The mechanism below was re-derived first-party at HEAD `e8324d241` by this orchestrator; the
> **incidence** claim was not, and is carried as a lead throughout.

## Objective

A finding's disposition lives in two fields that nothing reconciles: the `resolution` bucket and the
`resolution_detail` text. A record can therefore say `accepted` in its bucket while its own text opens
*"Declined — the premise is factually wrong"*. The per-reviewer quality metrics are computed from the
bucket alone, so such a record makes `false_positives_count` under-report — and it under-reports as a
**confident zero**, which reads as "this reviewer filed no false positives" rather than "the bucket did
not agree with the text".

## Problem

**The mechanism is CONFIRMED first-party.** `resolve_finding`
(`manage-findings/scripts/_findings_core.py:440-484`) validates `resolution` against the closed
`RESOLUTIONS` enum and then writes `resolution_detail` as an **independent** field:

```python
if resolution not in RESOLUTIONS:
    return {'status': 'error', ...}
...
updates: dict[str, Any] = {'resolution': resolution}
if detail:
    updates['resolution_detail'] = detail
```

There is no comparison between the two, at this seam or at any other. The store accepts a record whose
bucket and text contradict each other, and no reader can see that it did.

**The consequence is CONFIRMED first-party.**
`finalize-step-review-retrospective/scripts/review_retrospective.py:299-302` derives the metric from
the bucket alone:

```python
if resolution in _POSITIVE_RESOLUTIONS:
    bucket['positives_count'] += 1
elif resolution in _FALSE_POSITIVE_RESOLUTIONS:
    bucket['false_positives_count'] += 1
```

A declined finding bucketed `accepted` is counted as a positive and never as a false positive. The
metric is not wrong about its own inputs — it is exactly as reliable as a field nothing reconciles.

**The incidence is a LEAD, not a fact.** The forwarded report describes two records
(`008663`, `99e8ec`) whose text opened "Declined —" against an `accepted` bucket, and a CodeRabbit
`false_positives_count` reading `0` where the store supported `2`. ⛔ Those ids belong to a
machine-local plan archive on a **different machine** and are not resolvable from a clone. Treat the
two-record figure as unverified provenance. The run in question shipped as
**PR cuioss/plan-marshall#1330**, landed `92d61b521`, and recorded the correction under
"§ 5 Corrections to the record" — **not** as one of its ten lessons, so it carries no lesson id and had
no owner anywhere until this spec.

## ⭐ FOLDED IN 2026-08-27 — one triage rule, closed from three sides (3 lessons)

From inbox `lessons-handling-26-08-26-01-003.md`, which left the fold target to the orchestrator. It
lands here because this plan owns the disposition surface. All three lessons are already in the global
corpus; two of them (`09-016`, `09-017`) reached this epic once before as `truthful-signals`
delegations and were promoted at the 2026-08-25 drain. This fold allocates nothing new.

| Side | Lesson | The rule |
|---|---|---|
| **Rejecting** | `2026-08-25-09-016` | A rejection re-checked against the **prior verdict** rather than the code is vacuous authority |
| **Accepting** | `2026-08-25-09-017` | A disposition that **ACTS** on a finding must cite the same file:line evidence a rejection must |
| **Softening** | `2026-08-09-22-002` | A review may **raise** a severity by reasoning; it may not **lower** one without executing the code |

⭐ **The three are one rule, and the asymmetry is the finding.** Triage discipline is written almost
entirely around *rejecting* — a rejection must cite evidence and survive a re-trace. **Accepting and
softening carry no equivalent obligation**, because both feel like the safe direction. Neither is:
an accepted-but-unverified finding writes a change into the tree on the reviewer's premises, and the
pipeline then scores it `fixed` — **the highest-scoring outcome is the least-verified one**, which is
this plan's own subject one level up. ⇒ Make the evidence obligation **symmetric across all three
dispositions**, not heavier on any.

**D0 — GATE, mutates nothing: establish which of the two explanations holds, and publish the
population.** The forwarding orchestrator named two: an agent-side judgement slip on two records, or a
store that permits the contradiction. The second is already confirmed above — so D0's real question is
the **incidence**: over every findings store reachable from this machine, how many records carry a
`resolution_detail` opening with a declining word against a non-`rejected` bucket? **Publish the count
beside the number of records scanned and the number of stores reached.** ⛔ A zero here means "none in
the reachable stores", never "none exist" — the originating archive is on another machine, and the
report must say so.

**D1 — Make the contradiction mechanically detectable.** A `resolution_detail` opening with a declining
token (`Declined`, `Rejected`, and whatever else D0's sweep actually finds — derived, not guessed)
against a bucket outside the rejecting set is a defect. Detect it at the seam that writes it.
⛔ **Do not silently coerce the bucket from the text** — the text is prose written by an agent and the
bucket is the machine-readable decision; inferring one from the other replaces a visible contradiction
with an invisible one. Refuse the write, or record the contradiction on the record, and say which.

**D2 — Make the metric state what it can and cannot establish.** `false_positives_count` is exactly as
reliable as the bucket. Where the store holds a contradicting record for a reviewer, the per-reviewer
row must say so rather than publishing a clean integer. A confident zero over an unreconciled field is
the archetype this epic exists to remove.

**D3 — Pin both.** A test writing a record whose detail opens "Declined" against an `accepted` bucket,
asserting D1's chosen behaviour; and a test asserting the metric row discloses rather than reports a
bare count when such a record is present. The declining-token set must be **derived from D0's sweep**,
not hand-listed — a hand-listed token set is complete only over the tokens.

## ⛔⛔ FOLDED IN 2026-08-30 — the actionable classifier scores an entire reviewer zero BY CONSTRUCTION

Same module, same archetype as this spec's subject: a bucket whose rule contradicts what the field
is read to mean. **Verified first-party at HEAD `a1cae6102`.**

`_is_actionable` (`review_retrospective.py`:177-191) classifies **by kind alone**:

```text
inline        -> True
review_body   -> not _is_status_summary(record)   # registry-driven, REVIEWER-AWARE
issue_comment -> False                            # unconditional, NO content inspection
unknown       -> False
```

The docstring justifies the third line as *"meta (walkthrough/poem)"* — a **CodeRabbit-shaped
rationale applied to every reviewer**. ⛔ **`pr-agent` posts ONLY `issue_comment`s**, so its
`actionable_count` is **structurally 0 no matter what the body contains**.

⭐ **Note the asymmetry, because it is the fix's shape:** `review_body` already gets a
registry-driven, per-reviewer refinement via `_is_status_summary`. `issue_comment` gets a flat
constant. The seam for a per-reviewer rule therefore **already exists** — this is an extension of a
shipped pattern, not new plumbing.

**What it cost, measured:** the 2026-08-30 six-repo corpus pass found pr-agent produced exactly two
substantive reviews, one of them a **security** defect (cui-http #162, a fail-open in the RFC 7239
`Forwarded` parser). **Both would score `actionable_count: 0` in our own retrospective.**

⛔⛔ **The consequence is larger than wrong counts: every historical "pr-agent actionable_count: 0"
reading was UNINFORMATIVE.** It was zero by construction, not by measurement — so the epic never had
evidence pr-agent produced nothing, only an instrument that could not say. The corpus pass, reading
at source, is the first measurement that could. ⛔ **Do not cite any pre-2026-08-30
`actionable_count` for pr-agent as evidence of anything.**

### D3a — The carve-out cannot fire on the REAL record shape, and a fixture hid it

⛔⛔ **Folded 2026-09-13 from `truthful-signals-057`, first-party on PLAN-TRUTH-127 / PR #1483.**
`review_retrospective._is_status_summary` delegates to `review_gate_delta.is_status_summary`, which
matches the registry's `review_body_summary_patterns` against `_BODY_FIELDS = ('body', 'message')`.
⛔ **Every `pr-comment` record in that plan's store carries the comment text ONLY under the quarantined
`raw_input.body`** — no top-level `body` was ever promoted. With nothing to match, both of CodeRabbit's
*"Actionable comments posted: N"* `review_body` records were classified **actionable** rather than meta.

⭐ **On #1483 it landed on the correct side BY ACCIDENT** (both bodies also carried a real finding), so
the defect produced a right answer by a wrong mechanism — and on a PR whose status summary is purely a
summary, the same path inflates `actionable_count` by one **per review round**.

⛔ **The test that should have caught it is the reason it survived**: the existing coverage is a
hand-constructed fixture that happens to carry a top-level `body`. *Done when:* either the ingest path
promotes a top-level `body` or `_BODY_FIELDS` reaches `raw_input.body`, AND a positive test is built
**from a REAL stored record** rather than a fixture. ⚠ This composes with D1's contradiction detection:
a record whose text the classifier cannot reach is one the bucket/detail comparison cannot read either.

### D4 — Make the actionable classifier reviewer-aware for `issue_comment`

⭐ **A SECOND instance, folded 2026-09-13 from `truthful-signals-057` item 2** (same run, PR #1483): a
**round-2 Medium** finding was scored **meta** *solely because it arrived as a comment reply rather than
an inline note* — the classifier keys on the arrival shape, not on the content. That is this
deliverable's premise reaching a second shape, so it widens D4 rather than adding a deliverable: the
reviewer-awareness this deliverable adds for `issue_comment` must cover the **reply** shape too, and a
test must pin a substantive reply as actionable.

- Give `issue_comment` the same registry-driven treatment `review_body` has: a reviewer whose
  publish shape IS the `issue_comment` (pr-agent) must have its guide bodies classified on
  **content**, not on kind. Reuse the `_is_status_summary` seam rather than adding a parallel one.
- ⛔ **Derive the affected reviewer set from the registry**, never hand-list it — a hand-listed set
  is complete only over the names someone remembered, which is this epic's standing archetype.
- ⛔ **A canned-empty pr-agent guide must still classify as meta.** The fix must separate *"posted an
  empty table"* from *"posted a finding"*, not reclassify all 44 guides as actionable — that would
  replace an under-count with an over-count and manufacture a yield that does not exist.

*Done when:* a pr-agent guide carrying a real finding scores `actionable_count >= 1`, pinned by a
test using the cui-http #162 body shape; a canned-empty guide still scores 0, pinned as a **matched
negative control**; and the reviewer set the rule applies to is derived from the registry with its
population published.

### D5 — Accept a reviewer's INTENT, verify its DETAIL

⭐ **Folded from `truthful-signals-053.md` item 2 on 2026-09-08** (their `-021`). A **triage posture**,
not a defect — and it belongs here because this spec already owns the disposition vocabulary.

A reviewer's finding may be **right about the problem and wrong about the specifics**. Treating those
as one verdict **discards real signal**: the finding is rejected on its detail, and the problem it
named goes unrecorded.

⭐⭐ **We hold the matching first-party instance**: a CodeRabbit finding on one of this epic's plans
**whose stated line was wrong and whose subject was real.** ⇒ The posture is corroborated here, not
merely relayed.

*Done when:* the disposition vocabulary can express *subject accepted, detail corrected* as a single
recorded outcome — distinct from both `accepted` and from a rejection — and a triage that rejects a
finding on its detail alone records what it did with the subject. ⛔ A bucket that cannot say
"right problem, wrong line" forces a reviewer's real signal into a false-positive count, which is
exactly the metric D2 is already making honest.

## Claim Labels

- OBSERVED (added 2026-08-30, verified first-party at HEAD `a1cae6102`): `_is_actionable` returns
  `False` for `issue_comment` unconditionally with no content inspection, while `review_body` gets a
  registry-driven per-reviewer test — `review_retrospective.py`:177-191. Since pr-agent posts only
  `issue_comment`s, its `actionable_count` is structurally 0. ⛔ Re-read the function at run time;
  line numbers drift.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD (was 19453cb). Two-window read: over 19453cb..HEAD the 6 declared paths give 5 hits (_findings_core.py, jsonl-format.md, review_retrospective.py, test_findings_store_resolve.py, test_review_retrospective.py), but over 7a028157e..HEAD the intersection is EMPTY - every hit predates the corpus-wide baseline. The tail since 7a028157e is UNDISTURBED. Light method on the pre-7a028157e portion: not re-audited line by line this pass.
- OBSERVED: `resolve_finding` validates `resolution` against `RESOLUTIONS` and writes
  `resolution_detail` independently, with no comparison between them —
  `_findings_core.py:456-464`, read at `e8324d241`.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Same two-window read, baseline 26645688b..HEAD: 5 declared hits in the head of the window, zero in the 7a028157e..HEAD tail. The findings store and the retrospective have not moved since the corpus baseline, so no premise of this spec was disturbed in this pass window.
- OBSERVED: `false_positives_count` is incremented solely from
  `resolution in _FALSE_POSITIVE_RESOLUTIONS` — `review_retrospective.py:301-302`.
- HYPOTHESIS (forwarded, **unverified by this orchestrator**): two such records existed in the
  originating store and CodeRabbit's `false_positives_count` read `0` against a supported `2`.
  Confirm/refute at D0 over the reachable stores — and record `unverifiable` if the reachable
  population is empty, rather than reporting a clean zero (verify-at-outline).
- HYPOTHESIS: `Declined` and `Rejected` are the only declining openers in use — confirm/refute by D0's
  sweep (verify-at-outline). **Expect a larger set; treat that as the expected outcome, not drift.**
- Verify-first clause: the forwarding epic's standing ruling applies to every figure derived here —
  **derive it after the review cycle closes, and publish the population beside it.**

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
  — `resolve_finding`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
  — the resolution-bucket counters
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md` — the `reviewers[]` row shape
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_store_resolve.py`
- OBSERVED: `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md` —
  only if D1's chosen behaviour changes the documented record contract (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. **Emittable once its sequencing constraint below is respected.**
- ⛔ **MUST NOT run concurrently with PLAN-PR-026 or PLAN-PR-030** — both write
  `review_retrospective.py` and its SKILL.md, and PLAN-PR-030 D3 additionally narrows
  `test_counting_rule_parity.py`, which pins the predicate delegation this plan's metric sits behind.
- ⛔ **MUST NOT run concurrently with PLAN-PR-029** — that plan writes `_findings_core.py`'s
  `resolve_finding` neighbourhood (the transmission marker cleared inside the same function).
- Adjacent to: PLAN-PR-035, which measures answers that never went out. Different failure (a
  disposition that was transmitted but mis-bucketed), same record. Neither subsumes the other.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-037-a-disposition-bucket-that-contradicts-its-own-text.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
