# Landing Analysis: PLAN-TRUTH-101 — Documented invocations that cannot succeed as written

epic: truthful-signals
workstream: WS-01
plan: `documented-invocations-cannot-succeed-as-written`
pr: #1386 (merged)
landing commit: `71279cc024fdc256358e81df509a81c5b6770ec1`

## Ground-Truth Corroboration

Every claim below was settled first-party **before** any ledger write. Nothing is recorded on the
report's word alone.

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1386 merged | **corroborated** | `ci pr view --pr-number 1386` → `state: merged` |
| landing commit `71279cc0…` | **corroborated** | PR state's own `merge_commit_sha` = `71279cc024fdc256358e81df509a81c5b6770ec1`; `git log` shows `71279cc02` is the #1386 commit and is now the tip of `main` |
| landing message completeness | **corroborated** | `inbox landing-check` → `complete: true`, `missing_keys[0]` — every REQUIRED fact key supplied with a real value |
| `9f7923` — the issue-comment re-review path never verifies the head sha | **corroborated, and SHARPENED** | see below |
| "Nine findings were filed and deliberately not fixed" | ⛔ **contradicted** | see below |
| "`lessons-capture` 10 inbox messages" | **corroborated as a per-step count**, but it is not the population | see below |
| plugin-registry pin gap re-opened at `0.1.1588` | **unverifiable here** | operator-only surface; recorded as an OWED ACTION, not as a verified fact |

⭐ **The `merge_commit_sha` hazard R151 armed was checked and is clean.** The stamp was taken from PR
state, never from the landing message — R148's n=2 defect (a landing stamping another plan's commit)
appears only at N>1, and N>1 was live for this run. The two agree.

### ⭐⭐ `9f7923` is corroborated and the mechanism is sharper than reported

The report says `head_sha_verified` is **hard-coded `false`** on the issue-comment path. Read at
source, `workflow-integration-github/scripts/github_re_review.py:394`:

```python
'head_sha_verified': matched_signal == 'review',
```

It is not a literal `False` — it is a **derived predicate the issue-comment path can never satisfy**.
The observable effect is identical, and the sharper statement is the one to carry: the field does not
report *"the head sha was not verified"*, it reports *"the signal was not a review"*, and those are
different facts wearing one name. ⛔ A fix that changed the literal would find nothing to change.

⭐⭐⭐ **This is the SECOND first-party observation of this exact mechanism today, from a DIFFERENT
repository.** Inbox message `deployment-and-refresh-gaps-004.md` — relayed from **Token-Sheriff**,
plan `outbound-hostname-verification-core` (PR #689) — recorded pr-agent republishing by **editing its
existing comment in place**, producing no new comment for the classifier to match and resolving
`head_sha_verified=false, matched_signal=issue_comment` → `declined`. That message was transferred to
`review-apparatus` earlier today as `truthful-signals-043.md` § 2. **Two independent observations, two
repositories, one mechanism, one day.** The corroboration is now first-party at source and no longer
rests on either report.

⛔ **Both runs record the same near-miss for the same reason:** the false negative did not block only
because another signal outranked it. **The documented remedy for `declined` is to ask the operator to
merge unreviewed**, and pr-agent is this project's only REQUIRED bot.

### ⛔ The findings count is nine; the enumeration is eight

The report's prose says *"Nine findings were filed and deliberately not fixed"* and then names **eight**
ids: `d6bf20`, `f3d2df`, `50bab4`, `7d3960`, `7bf19d` (→ truthful-signals) and `9f7923`, `65f631`,
`7dfe44` (→ review-apparatus). **The landing message's own residue section enumerates the same eight**,
so the machine record and the id list agree with each other and only the word *nine* disagrees.

The likely ninth referent is `c128cb`, which `f3d2df`'s own text names — *"This plan's own finding
`c128cb` landed in exactly that cell"* — but `c128cb` is described as **acted upon**, not deferred, so
it does not belong to a count of findings *deliberately not fixed*.

⛔ **Recorded as a divergence, not resolved by inference.** Either the count is off by one or a ninth
deferred finding exists that the payload omits, and this epic's own rule forbids picking between those
from a restated total. ⭐ It is this epic's archetype in miniature: **a count published beside an
enumeration that does not support it**, in a report whose subject is exactly that class of defect.
Two candidate homes already exist — `PLAN-TRUTH-117` (restated counts and underived completeness
claims) and `PLAN-TRUTH-110` (a plan decides what the epic learns and nothing audits that decision).

### ⚠ "10 inbox messages" is a per-step count, not the population

`lessons-capture` reported **10** messages and `plan-retrospective` reported **8 candidate-lessons**.
The inbox holds **19**: 18 candidate-lessons (`-001`…`-018`) plus the landing (`-019`), written in two
bursts — `-001`…`-008` at 18:49 (the retrospective's) and `-009`…`-018` at 18:59–19:00 (lessons-capture's).

⭐ **Both step figures are individually correct and neither is the total.** Read as a headline, "10
inbox messages → truthful-signals" understates the drain's work by 8. The per-step counts are right;
the risk is entirely in reading one as the population.

## Deliverable Fidelity vs Spec

**4/4 shipped, and the approach on D2 is better than the spec's.** The stdin TOON parser was closed by
**DELEGATING to the canonical `toon_parser`** rather than widening a second hand-rolled reader — the
one-reader discipline this marketplace enforces for `## Expected Surface` applied to a second format.
D3's site list was **derived from source at execute time rather than restated as a literal list**,
which is the same discipline again and exactly what `PLAN-TRUTH-117` asks of every count.

⭐ D1 ("enumerate and check every documented invocation in scope") is a population-derivation gate, and
D4 is a **population-derived contract test** — so the plan both derived its scope and left behind the
mechanism that keeps it derived. That is the shape this epic wants from every plan.

## Metrics and Anomalies

| Figure | Value |
|---|---|
| total tokens | **6,377,728** against a **2.0M** anchor for `multi_module + bug_fix` — **2.9×** |
| billing-weighted | 40,734,118 |
| `6-finalize` alone | **3,543,944** — 55.6% of the plan |
| largest single contributor | `pre-submission-self-review` — **~738k**, 5 firings, **3 terminating in `error`** |
| wall / worked | 28h02m / 5h20m |

⛔⛔ **`pre-submission-self-review` is now the named lever in two consecutive landings.** PLAN-TRUTH-102
recorded it at **1,850,232 tokens = 50.6%** of that plan with 13 defects that never reached the PR;
this run records ~738k with **3 of 5 firings terminating in `error`**. ⭐ The two runs fail
*differently* — 102's cost was residue-chasing across symmetric documents (folded into `PLAN-TRUTH-108`
today), this run's is **error-terminated firings**, which buy nothing at all. Lesson
`2026-08-27-16-002` already records *"cap or triage error-terminated finalize dispatches — 34% of
finalize spend bought zero detection"*. ⇒ **Three independent observations of one step, and token
reduction is the operator's stated priority 1.**

⚠ **Two self-caught omissions the run corrected mid-flight, and the correction was the right one:**
`branch-cleanup` and `record-metrics` had recorded no typed facts, which would have degraded
`merge_state` to `unknown` in this landing. They were re-stamped with `--no-completion-log` so the
completion line stayed emitted exactly once. ⭐ **That is why `landing-check` returns `complete: true`
here** — and under the landing-payload contract a `merge_state=unknown` landing is INCOMPLETE, because
the drain must not reconcile against a failed read. The correction converted an incomplete landing into
a complete one before it was sent.

## Routing and Merge Behavior

Squash-merged through the platform merge queue; `upstream_commit_count: 6`. Branch cleaned up,
worktree removed, working tree clean. 23/23 finalize steps `done` — the landing-facts `steps` list was
parsed with a **last-colon split**, so namespaced ids (`project:finalize-step-plugin-doctor:done`,
`plan-marshall:plan-retrospective:done`) resolve to the step, not to the bare namespace.

⛔ **Two run-shape observations that are defects in the machinery, not in this plan** — both are carried
below as epic-level items rather than as plan residue:

1. **The `5-execute → 6-finalize` boundary was crossed with the phase's declared verification never
   having run.** The manifest declared **3** `verification_steps` and the execution log holds **zero**
   `record-step` rows for `5-execute`. ⭐⭐ **The gap closed only because a later loop-back re-fired
   `pre-push-quality-gate` against the newer HEAD — i.e. by luck.** Absent the loop-back this ships
   unverified **with nothing reporting it**.
2. **`metrics.toon` still reports `re_entered_phases: []`** after a completed
   `6-finalize → 5-execute → 6-finalize` loop-back carrying `loop_back_iteration: 1`. A re-entry that
   happened and a re-entry that did not are byte-identical in that field.

## Reconciliation Actions

- `PLAN-TRUTH-101` transitioned `launched` → `shipped`.
- Row stamped: `pr = 1386`, `landing = landings/PLAN-TRUTH-101.md`. `plan_marshall_plan_id` was already
  stamped at launch (R151) and was not rewritten.
- Landing message `documented-invocations-cannot-succeed-as-written-019.md` archived on consume.
- Slot freed: R drops 2 → 1 against `parallelization_scope = 3`.
- ⛔ The 18 queued candidate-lessons (`-001`…`-018`) are **NOT** dispositioned by this landing analysis.
  They are a drain, not a landing, and folding them in silently would be scope creep.

## Follow-Ups

- **`9f7923` / `65f631` / `7dfe44` → `review-apparatus`.** `9f7923` is now double-corroborated and its
  mechanism is sharpened above; it strengthens `truthful-signals-043.md` § 2 and bears directly on
  `PLAN-PR-046`. `65f631` reports the pr-agent registry doc and observed behaviour disagreeing **in
  both directions** — taken with `9f7923` the declared publish shape is wrong twice over.
- **`7bf19d` is live against a CLAUDE.md that was edited today.** It reports `generate.py`'s docstring
  and `marketplace/targets/README.md` asserting *"always invoked through the `./pw` wrapper"* and that a
  bare `python3` cannot import PyYAML — both false of this repository's own CI, which invokes the bare
  form after installing the dependency. ⚠ CLAUDE.md now carries an adjacent-but-not-identical claim
  (`uv` is not on `PATH`, so a bare `uv run …` fails outside the wrapper). **Settle the two together;
  do not assume the new wording inherits the refutation, and do not assume it escapes it.**
- **`d6bf20`** (`toon_parser` CSV/TSV round trip loses a tab-bearing value) belongs with
  `PLAN-TRUTH-125` — *one format, several implementations that disagree, and no test compares them* —
  whose declared surface already names `ref-toon-format/scripts/toon_parser.py`. ⭐ Provenance was
  established at source in both directions and the defect is **pre-existing, not introduced here**.
- **`50bab4`** (`prune-local-and-remote-ref` hard-fails on an already-deleted local branch and aborts
  before the remote prune it exists to perform) is an asymmetry defect: the remote half has a tolerant
  guard, the local half does not. Worst exactly on the merge-queue path.
- **`7d3960`** (`manage-metrics enrich` takes ONE `--session-id` while `session_ids` is a list; this
  plan spanned two sessions and only the last was walked, **with nothing in the return saying so**) is
  this epic's canonical shape and belongs with `PLAN-TRUTH-127` / `PLAN-TRUTH-121`.
- **`f3d2df`** (`triage.md` Step 6 justifies a guard via signal 1 alone while signal 3 can fire on the
  same cell) — the plan's own finding `c128cb` landed in exactly that cell, which is a worked
  counter-example rather than an inference.
- ⛔ **OWED, operator-only: the plugin-registry pin gap re-opened at `0.1.1588`** (18 entries, 10 dirs)
  after this run's cache sync. Repair is `python3 .plan/temp/repair-plugin-pin.py --target 0.1.1588`,
  and a **full restart** is required to re-seat skill bodies. ⚠ Per R158: there is **no `--apply` flag**
  (writing is the default, `--dry-run` is the opt-out), and after the repair **delete
  `*/0.1.1588/.orphaned_at`** — the foreign GC marks the freshly-synced version within minutes.
