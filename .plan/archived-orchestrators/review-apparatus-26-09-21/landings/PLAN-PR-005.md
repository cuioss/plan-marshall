# Landing: PLAN-PR-005 — Participation derived from a lossy view

epic: review-apparatus · workstream: WS-01 · shipped 2026-08-13
cloud run: `cloud-runs/110-participation-derived-from-a-lossy-view/`
PR #1219 (`38548923`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## What landed — a refuted premise, handled correctly then abandoned

The run's headline outcome is sound and independently reproducible: **both target defects were real
before #1141 and are genuinely absent at HEAD**, so the plan produced no production change. The D0
gate handled the refutation correctly. What shipped is one uncovered regression guard,
`test_a_deduped_comment_is_still_credited_as_participating` — the only test in three suites (178) that
catches a dedup coupling confined to the presence-credited bots.

**Deliverables: 4 — 0 done, 4 partial.** The *premise* was refuted, not the deliverables: D1 and D2
were both already satisfied at HEAD by #1141.

| D | Outcome | What is missing |
|---|---------|-----------------|
| D0 | met with gaps | `workflow-integration-github/SKILL.md:129`, which *defines* what `participated_bots[]` credits, is enumerated nowhere; the wait-completion predicate is classified nowhere. |
| D1 | partial | Monotonicity breaks on an unreadable head SHA; the ⭐ `auto_on_push`/`requires_explicit_trigger` record does not exist. |
| D2 | partial | The plan's own verbatim D2 defect — dedup keyed on `comment_id` alone — is **still live** at `github_pr.py:1102`. |
| D3 | partial | (c) confirmed only for the single-comment shape; the refusal fixture is bot-derived, not wording-derived, and passes over an empty pattern set. |

## ⛔ The run wrote "no follow-up owed" over three live defects

The report's residue reads "**None blocking** … No follow-up owed". Verification found three live
defects (G1, G2, G3) plus two unmet ⭐ obligations, **in the files the plan itself declared as its
expected surface**, one of them its own D2 defect statement verbatim and unchanged.

**Standing rule this produces: a refuted premise is not a clean surface.** After a refutation,
re-walk the declared surface; do not infer its health from the refutation.

## Report claims the verification found false

- "Per-bot trigger semantics are already registry data (`participation_requires_update`,
  `trigger_comment`, `rate_limit_class`)" — **false** as a discharge of the ⭐; none encodes the
  distinction, and `trigger_comment` is non-empty for all three bots so it discriminates nothing.
- "`_reviewed_at_merge_candidate` … a **pure SHA comparison** … identical however many times it is
  evaluated" — overstated; the first-observation arm returns `bool(merge_candidate_sha)`, so the
  verdict is also a function of whether the head read succeeded.
- D3(d) "consumer population ALREADY COVERED" by three named tests — all three derive the **bot**
  population, not the site population.
- Line-number drift: of every `path:line` citation in the report, exactly **two** still resolve.

## ⛔ A figure carried across months of landings, refuted

The plan claimed `participation_evidence(bot)[0]` is consumed by "seven registry-derived consumers".
Re-verified first-party: **exactly four `[0]` call sites, all under `test/`, zero production
readers.** Production reads LIST membership only, which is order-independent. The ordering hazard is
real but confined to test-fixture convention.

## Gaps: 10 — 8 full, 1 partial, 1 uncovered

- **full**: G1, G2, G3, G4, G5, G8, G9, G10
- **partial**: G7 (PLAN-PR-025 D5 takes the substantive half; the report-citation correction is
  explicitly out of scope there)
- **uncovered**: **G6** (correct the "None blocking / No follow-up owed" residue — same deliberate
  exclusion family as `010 G5`)

## Standing facts

- **A "population-derived" fixture over the wrong population is the vacuous guard wearing a badge.**
  `_refusal_body` uses `declared[0]` and falls back to a synthetic structural notice, so
  `test_every_registered_bots_refusal_is_detected` sweeps **bots**, exercises one wording each, and
  passes for pr-agent — which declares **zero** refusal patterns — by exercising a fallback. Name the
  axis a sweep ranges over, and publish its size.
