# PLAN-PR-063: The finalize record, and the disposition it carries

epic: review-apparatus
workstream: WS-03

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-072 (D0/D7/D11 — the store and its dispositions), PLAN-PR-074 (D2/D5/D6/D13 — the dispatcher and the finalize record), PLAN-PR-075 (D1/D3/D4 — the telemetry channels), PLAN-PR-076 (D8/D10 — what the retrospective can establish), PLAN-PR-071 (D9 — is_status_summary, an automatic-review symbol).
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **absorbs `PLAN-PR-050` and `PLAN-PR-037` whole**, under the operator's 2026-09-12
> decision to raise the split guard to **12 deliverables** and group staged work by shared target
> surface.
>
> ⛔ **Every deliverable body below lives in its SOURCE spec and is NOT restated here.** The sources
> are retired from the queue but remain the authoritative text. Follow the pointer; do not retype.

## Objective

Make the finalize phase's record of a review readable back as what actually happened — which head was
examined, whether findings came back, whether verification ran — and make each finding's recorded
disposition agree with its own text.

## Why these were grouped

Derived from `corpus surfaces`: both declare `_findings_core.py` and the review-retrospective surface,
and both are about the same artifact class — **the record a later reader consults instead of the run**.
`PLAN-PR-050` fixes whether the step record can be read back at all; `PLAN-PR-037` fixes whether a
record that IS read back means what it says. ⛔ A readable record carrying a `resolution` bucket that
contradicts its own `resolution_detail` is a worse outcome than an unreadable one, because it is
trusted.

## Deliverables

**D0 — GATE, mutates nothing.** The merged gate. From `PLAN-PR-050` D0: re-ground all three claims at
HEAD and record, per claim, the file and symbol that settles it. From `PLAN-PR-037` D0: establish which
of the two explanations for the bucket/detail contradiction holds, and publish the population. **HALT
and report** if either no longer reproduces.

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | Make a step record self-validating about its head | `PLAN-PR-050` § D1 |
| D2 | Stamp `returned_with_findings` at the finalize dispatch boundary | `PLAN-PR-050` § D2 |
| D3 | Three channels go dark over `6-finalize`, and a green completeness flag does not cover it | `PLAN-PR-050` § D2a |
| D4 | Resolve the `VERIFY` channel one way | `PLAN-PR-050` § D3 |
| D5 | Retire the duplicate retrospective step record | `PLAN-PR-050` § D4 |
| D6 | The post-run dirty-path guard must attribute by AUTHORSHIP | `PLAN-PR-050` § D5 |
| D7 | Make the bucket/detail contradiction mechanically detectable | `PLAN-PR-037` § D1 |
| D8 | Make the metric state what it can and cannot establish | `PLAN-PR-037` § D2 |
| D9 | Pin both — **and the carve-out that cannot fire on the real record shape** (`raw_input.body` quarantine; the passing fixture is what hid it) | `PLAN-PR-037` §§ D3 + D3a |
| D10 | Make the actionable classifier reviewer-aware for `issue_comment` | `PLAN-PR-037` § D4 |
| D11 | Accept a reviewer's INTENT, verify its DETAIL | `PLAN-PR-037` § D5 |

**D13 — A triage decision needs a representation the pipeline can protect (lesson `2026-09-04-08-015`,
absorbed 2026-09-18).** A remedy whose whole artifact is a sentence in a document is deleted by a later,
entirely correct accuracy pass, and nothing notices that a decision was voided: Q-Gate `c4e309` removed
the sentence step 1 had added, and CodeRabbit `1002a8` then reopened the same finding. *Done when:* a
triage disposition whose remedy is documentary records a commitment naming the file, the claim and the
finding it discharges, and a later edit that removes the claim surfaces the commitment rather than
silently voiding it. ⭐ In-epic by provenance — carried out of this epic's own inbox
(`review-packs-become-published-artifacts-014.md`).

**D8 amendment 2026-09-18 (lesson `2026-09-05-07-001`).** The `rejected` bucket does two jobs —
**administrative** rejection (out of scope, duplicate, not-for-this-PR) and a **refuted premise** (the
reviewer was wrong) — so `false_positives_count` over-reported by 4 and under-reported by 3 on one run,
in opposite directions at once, which no scaling can correct. D8's disclosure of a contradicting record
does not reach this axis (`grep -rn "administrative" plans/ epic.md findings/` → 0). ⇒ D8 additionally
separates the two at triage time, or excludes administrative dispositions from the metric's
denominator and says so.

Thirteen deliverables. The 12 ceiling is a guideline (operator ruling 2026-09-15); D13 is the same
disposition record the other twelve read and write. ⛔ **Absorb no fourteenth.**

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-logging/standards/log-format.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/post-run-review.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md`
- OBSERVED: `test/plan-marshall/manage-findings/`
- OBSERVED: `test/plan-marshall/manage-status/`
- OBSERVED: `test/plan-marshall/manage-logging/`
- OBSERVED: `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py`
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_store_resolve.py`

## Claim Labels

- OBSERVED: this plan's claim set is exactly the union of `PLAN-PR-050` § Claim Labels and
  `PLAN-PR-037` § Claim Labels, carried unchanged with their labels. Confirm/refute at those two
  sections — they are the authoritative record and this plan re-states none of them.
- OBSERVED: both sources declare `_findings_core.py` and the review-retrospective surface, and both
  govern the record a later reader consults instead of the run. Confirm/refute at `corpus surfaces`
  over the retired source rows.
- HYPOTHESIS: the bucket/detail contradiction and the step-record readback are independent defects that
  share only their storage — confirm/refute at D0 (verify-at-outline). If one causes the other, D0 says
  so and the roster is re-ordered rather than shipped as two unrelated halves.

## Dependencies and Sequencing

- ⛔ **Overlaps `PLAN-PR-061` and `PLAN-PR-062`** on the retrospective and `_findings_core.py` —
  sequence, never pair.
- ⭐ **Internal order: D0 → D7/D8/D9 (make the record honest) → D1–D6 (make it readable) → D10/D11.**
- Supersedes: `PLAN-PR-050`, `PLAN-PR-037`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-063-the-finalize-record-and-the-disposition-it-carries.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
