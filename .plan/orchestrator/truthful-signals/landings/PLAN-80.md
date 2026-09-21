# Landing Analysis: PLAN-80 — Refusal Recognizer Generalizes Phrasing, Not Failure Mode

epic: truthful-signals
workstream: WS-01
pr: 1021

> Landing record for one shipped plan. Claims below were verified against ground truth before
> recording — the operator's narrative is a lead, not a fact.

## Deliverable Fidelity vs Spec

Merge CONFIRMED first-party: `origin/main` head is `bd8ce3c3f` —
`fix(automatic-review): recognize bot refusals via registry data (#1021)`. The spec staged three
deliverable *themes* (D1 registry-vs-regex layer, D2 detector correction, D3 tests); the plan shipped
3/3 with the layer boundary settled as the spec's D1 required.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — collapse the CodeRabbit island onto the shared recognizer; file both bots' OBSERVED refusal markers as registry data | ⛔ **CORRECTED 2026-07-28 → shipped-PARTIALLY** (was recorded shipped-as-specified) | **What landed, verified:** the layer question is settled as the spec posed it — a registered bot's observed refusal text is **registry data** (`coderabbit.md:30` carries `"Review limit reached"`, the live phrasing), and the generic recognizer at `_github_pr.py:74-95` is genuinely bot-agnostic with a verb set including "reached". **What did NOT land: the CodeRabbit island survives.** At HEAD, after #1021: `_CODERABBIT_BOT_LOGINS` hardcoded at `_github_pr.py:42`, `_detect_coderabbit_rate_limited` at `:45`, still called at `:630` — and it is what produces the `rate_limited` discriminator. A stale code comment at `:78-79` still describes *"CodeRabbit's `## Rate limit exceeded` callout"*, a phrasing that does not exist (live text is `## Review limit reached`). **Functional consequence:** a rate-limited Sourcery / PR-Agent / future bot yields `rate_limited: false`, so any rate-window strategy built on that flag inherits a single-bot blind spot. Routed to **PLAN-71 § 0c** |
| D2 — regression tests pinning both refusal notices through the pre-filter | shipped-as-specified | Merged as deliverable 2 |
| D3 — stop both `await_fresh_review` discriminators counting a refusal as a response | **shipped-WIDENED after Q-Gate refutation** | Projection gains `body`; `_match_review` takes `bot_kind`. See the Verify-First note below — this is the significant deviation |
| (spec caution) D2 MUST NOT invent marker strings for unobserved modes | **honoured** | Both filed markers are OBSERVED refusal text, not invented for unobserved modes |
| (spec caution) D1 MUST verify whether #1016's noise-filtering of two real comments was correct | ⚠ **NOT reported either way** — see Follow-Ups |

## ⭐ The Verify-First Contract Did Its Job — record this as a positive instance

**The Q-Gate REFUTED D3 as originally scoped, and the refutation was correct.** The outline's fix
targeted `_match_bot_comment`, but the Sourcery refusal arrives as a **review**, and the review path
resolves first with **no body projected** — so the fix could never have fired for the very case it
cited. Confirmed first-party, escalated, and D3 was widened to project `body` and guard both paths.

Without that catch the plan would have shipped a **green, plausible, non-functioning fix** — which is
this epic's flagship archetype, and it would have shipped *inside the plan built to close an instance
of it*. The epic has repeatedly recorded the verify-first contract catching bad premises; this is the
sharpest instance so far, because the refuted premise was one the orchestrator itself had sharpened.

## Metrics and Anomalies

- Tokens: 2.9M
- Duration: 3h00m worked / 7h30m wall
- Finalize: 20/20 steps; plugin-doctor 30 rules 0 issues; `pre-submission-review` found and FIXED 1
  `contract_drift`; simplify collapsed 1 duplication and re-verified
- Anomalies: **`worktree remove` timed out mid-delete.** The executor restored the four already-deleted
  files so the documented non-force path could succeed rather than reaching for `--force`. Correct
  call — `--force` would have masked a timeout as a clean removal.
- Release: v0.1.1231, 10 bundles, executor regenerated

## Routing and Merge Behavior

- Review: **3/3 bots responded, 1 comment**, triaged as accepted-false-positive and answered
  on-thread. ⭐ Notable against this epic's standing warning that bot participation cannot be read
  from check states: this run had all three participating with real comment evidence.
- CI/merge: all checks green; merged via merge queue; branch + worktree removed; working tree clean.
- **Operator self-correction recorded:** an earlier reading of `autoMergeRequest: null` as "not
  enqueued" was WRONG — the PR was queued at position 1 the whole time. Worth carrying: `null` there
  is not evidence of absence from the queue.
- Surface collisions: none. PLAN-80's `workflow-integration-github` / `automatic-review` surface stayed
  disjoint from the five plans running concurrently, as staged.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-80 --status shipped`
- [x] row `pr` stamped `1021` — `orchestrator queue --set-row PLAN-80 --field pr --value 1021`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-80 --field landing --value landings/PLAN-80.md`
- [x] epic.md queue reconciled from status.json; PLAN-80 mirror row marked shipped
- [x] **Watch RETIRED** — the "refusal detectors are stale and neither is a superset" watch is closed by
      this landing
- [x] **Follow-ups routed** (below) — no new plan created; both halves already had staged homes
- [x] resume_anchor updated
- [x] START-HERE block regenerated
- [ ] row `plan_marshall_plan_id` — NOT stamped; the plan id was not reported in the landing narrative
      and is not recoverable from the PR alone. The archived plan dir is
      `.plan/local/archived-plans/2026-07-27-refusal-…` (truncated in the report). **Left empty
      deliberately rather than guessed** — a fabricated id is worse than an absent one, and the
      START-HERE gap marker only checks `pr`/`landing`, both of which are stamped.

## Follow-Ups

Three items surfaced. ⚠ **The operator suggested item 2 below was "worth its own plan" — it is NOT
staged as one, because both of its halves already have staged homes.** Creating a third plan would
have duplicated scope across three specs.

1. **"Closed consumer set" was not closed, and it told phase-5 not to re-check** → **folded into
   PLAN-61** (`outline-plan-scope-derivation-integrity`), whose objective is precisely that
   consumed fields be *derived, not asserted* and completeness checks be *closure-based*. The outline
   verified `test_re_review_strategy.py` had no dict-equality assertions but never looked at
   `test_github_ops.py`, which had two; both broke on the new `body` key and surfaced only in the
   whole-tree run. **Sixth recurrence of the archetype.**
2. **Push freshness gate passes on evidence that does not support it** → split across the two staged
   plans that already own the two halves:
   - **Consumer half → PLAN-82** (`freshness-gate-cannot-distinguish-test-authored-evidence`). The gate
     returned `fresh` by matching an **npm `--help` invocation recorded as a successful `kind=build`,
     in a repo with no npm build**. This is a *second independent instance* of PLAN-82's founding
     defect — which was ALSO an unrelated `plan-marshall:build-npm` notation. Same gate, same bundle,
     different plan. n=2.
   - **Producer half → PLAN-59 D1/D2.** `parse --log` (a pure log reader) is recorded as a `kind=build`,
     which is the *same defect* as PLAN-59's already-open lesson `2026-07-22-16-003` (`kind=build`
     stamp keyed on the `bundle:skill` prefix with **no subcommand discriminator**, so a query verb
     writes a `status=success` build row). A `--help` invocation and a log reader are both exactly that.
     **This is corroborating evidence that PLAN-59 D2's discriminator is the right fix, and it widens
     the known blast radius from `resolve-test-scope` to at least three verbs.**
   - **Also carried to PLAN-59:** timed-out builds carry `exit_code: 0` — previously observed at the
     PLAN-55 landing, now independently re-confirmed. Two sightings, same falsehood.
3. **PLAN-80's own D1 caution went unreported.** The spec required D1 to VERIFY whether #1016's
   noise-filtering of two real comments was CORRECT. The landing narrative does not say either way.
   Recorded as an **open watch**, not assumed discharged — a silent pass on an explicitly-required
   verification is exactly the shape this epic exists to catch.
