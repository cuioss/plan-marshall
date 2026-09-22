# Landing Analysis: PLAN-99 — Exploration share is unmeasured

epic: truthful-signals
workstream: WS-01
pr: 1043 — merged as `bef5b29df`, 2026-07-29 06:58:23 +0000

> Corroborated against `origin/main` and the PR comment stream before recording.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — GATE: settle hypotheses, classification, denominator | shipped-as-specified | gate mutated nothing; classification and denominator settled before instrumentation |
| D2 — per-phase exploration/work counters from the transcript engine | shipped-as-specified | `platform-runtime` + `manage-metrics` in the merged title |
| D3 — `exploration-share` cross-plan auditor check (the 23rd) | shipped-as-specified | **independently confirmed**: the `audit-archived-plan-retrospectives` skill description now enumerates **twenty-three** checks including *"exploration-share (measured share of tool-call spend that went to exploration rather than to work)"* |
| D4 — citations-only return standard + conformance detector | shipped-as-specified | standard + detector |
| D5 — acceptance read | shipped-**as not-yet-measurable**, recorded honestly | see below |

⭐ **D5 is the right outcome, not a shortfall.** The plan recorded the acceptance read as
**not-yet-measurable** rather than manufacturing a verdict from one run's data. That is precisely the
discipline this epic exists to enforce — a measurement-first plan declining to claim its own effect
until the baseline can support it.

## ⭐ The instrument measured itself

From the run's own `metrics.md`:

| Metric | This run | Corpus baseline |
|---|---|---|
| exploration payload-byte share | **83.4 %** | 76.84 % |
| exploration turn share | **21.3 %** | 16.90 % |

And **`unclassified` was 0 in every phase**, so the population-derived classifier's fail-open bucket
never had to fire. ⚠ **That is a genuine non-vacuity signal**: the classifier covered its whole
population on first contact, which is the positive-population property the epic keeps demanding of
detectors — here satisfied rather than merely claimed.

## Routing and Merge Behavior

- **Two finalize loop-backs. Four defects escaped local gates, each caught by a DIFFERENT gate** — a
  useful natural experiment in gate complementarity:

| Caught by | Defect |
|---|---|
| `module-tests` | over-strict exact-list-equals on orthogonal flags |
| **the plan's own new detector** | leftover restatement sentence |
| `pre-submission-self-review` | doc-contract divergence in the enrich field enumeration |
| **CI alone** | pollution-guard leak — passed locally **only because the worktree already held `audit-reports`** |
| **CodeRabbit** | the plan's 390-line insertion **split an existing test class, stranding 6 methods** |

⇒ **No single gate would have caught more than one of these.** The CI-only case is the sharpest: a
local pass that depended on pre-existing worktree state — the same "green for the wrong reason"
shape the epic tracks, here caught only because CI starts clean.

- ⭐ **Waiting on the rebase paid for itself.** CodeRabbit's rate-limit window reset, coverage went
  **1-of-3 → 2-of-3**, and its 7 inline findings produced four more fixes **including the real
  class-split defect**. ⚠ **This is the first landing where waiting out a refusal actually
  recovered a required reviewer** — and it stands against #1041, where an 8-hour wait recovered
  nothing. ⇒ **Both outcomes are now observed: a rate-limit window MAY reset within a run, or may
  not.** That strengthens lesson `2026-07-28-23-001` (an ETA is a lower bound, never a wait budget)
  rather than contradicting it — the recovery was opportunistic, not predictable.

### Post-merge PR revisit — clean

Merged 06:58:23Z, latest comment 06:42:36Z. **No post-merge arrivals.** Late-arrival recurrence
stays at **n=3**.

## Metrics

4h7m worked / 4.2M tokens, 21/21 finalize steps.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1043; `landing`; `plan_marshall_plan_id` — all four stamped
- [x] post-merge revisit performed — clean
- [x] the live `audit.py` cwd defect recorded as an Open Defect pending allocation
- [x] resume_anchor updated

## Follow-Ups — three open, none blocking

1. ⛔ **A LIVE PRODUCTION DEFECT.** `audit.py`'s `write_persisted_report` derives its path from
   `Path.cwd()` and **ignores `--plan-dir`**. TASK-11 fixed **only the test side**, so the production
   path is still wrong. Filed by the plan as a candidate-lesson; **the epic must allocate it.**
   ⚠ This is the *fix-the-calls-not-the-test* inversion — a test-side fix that leaves the defect live
   is indistinguishable from a fix at the reporting layer.
2. **The retrospective found four more defects**, two of which matter:
   - **`check-manifest-consistency` rule M3 is a VACUOUS GUARD** — `steps != ['module-tests']`
     against the composer's `['verify:module-tests']`, so **it cannot fire**. ⭐ **Occurrence 5+ of
     the vacuous-guard archetype.**
   - **A loop-back OVERWROTE 73 % of phase-5's token attribution**, because `end-phase` is
     **replace-not-accumulate**. ⚠ Directly corrupts the measurement corpus this very plan just
     instrumented — **route to `code-intelligence-substrate`** per the inbound routing rule.
3. **`marshal.json` still stale** — 0.1.1240 provisioned vs **0.1.1252** installed. Operator-owed
   `/marshall-steward`.

## Deviations — disclosed, not silent

Both logged by the plan as deliberate: a forced worktree removal **after verifying all 22 files were
in `bef5b29d`**, and a skipped redundant outline re-dispatch when all three operator answers matched
what was already persisted. ✅ **Recording a deviation as deliberate is the behaviour the epic
wants**; neither is a defect.
