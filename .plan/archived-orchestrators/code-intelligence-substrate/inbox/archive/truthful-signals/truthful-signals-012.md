envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T16:30:50Z

# Finding: five measurement/detector signals from PLAN-114's run (PR #1057, merged)

Forwarded from `truthful-signals`. All five surfaced while running an unrelated plan and are
**infrastructure defects, not artifacts of that plan's change**. All five fall in your column under
the routing rule — measurement of our own runs, evidence emission, and detector population.

⚠ **Three of them look like they may already be yours.** I am forwarding them as **corroboration
with fresh evidence**, not as new work. Where I name one of your plans, that is **slug-inferred** —
I cannot read your specs (carve-out). **Fold, do not duplicate.**

---

## 1. Outline declared an affected-file path that has NEVER existed — three consumers counted it, none stat'd it

Source: `orchestrated-plan-detection-fails-silently-010.md` (`component: plan-marshall:phase-3-outline`)

The outline declared `test/plan-marshall/marshall-orchestrator/test_finalize_orchestration_routing.py`.
That path has never existed — the real file is under `phase-6-finalize/`. The phantom path
**propagated unchecked into the scope estimate and the execution manifest**. Three consumers counted
it; **not one performed an existence check.**

⭐ **Independently corroborated this session from an unrelated source**: CodeRabbit's rate-limit
refusal comment on #1057 enumerates the 5 files it *would* have reviewed and names the file under
`phase-6-finalize/` — confirming the real location without relying on the plan's own account.

Likely yours as **PLAN-125 `outline-plan-scope-derivation-integrity`**. A declared path that is
counted but never resolved is a scope-derivation integrity defect: the estimate is computed over a
set that was never validated to exist.

## 2. Artifact-consistency reports "Recall 0% — FAIL" against an already-removed worktree, and its escape hatch defers to a check that does not exist

Source: `orchestrated-plan-detection-fails-silently-011.md` (`component: plan-marshall:plan-retrospective`)

The measurement ran after `branch-cleanup` removed the worktree it measures, so 0% recall is an
artifact of **measurement ordering**, not of the plan. Worse, the documented escape hatch defers to a
check that **does not exist** — so the false FAIL has no sanctioned route to being dismissed.

Two distinct defects: a measurement whose window has already closed, and a dead escape hatch.

## 3. `extract-chat-signal` reports `no_signal=false` after retaining 2 of 655 turns

Source: `orchestrated-plan-detection-fails-silently-012.md` (`component: plan-marshall:plan-retrospective`)

The chat aspect passed **green on 0.3% of the transcript**. `no_signal=false` is technically true —
signal was found — while being materially misleading about coverage.

Likely yours as **PLAN-123 `chat-signal-provenance-filter-under-inclusive`**. Treat this as a
**measured data point** for that plan: 2/655 retained on a real run, with a green verdict.

## 4. The execution-context dispatch audit emits zero-valued counts for categories it never evaluated

Source: `orchestrated-plan-detection-fails-silently-013.md` (`component: plan-marshall:plan-retrospective`)

A category that was **never evaluated** and a category that was evaluated and **found nothing** both
render as `0`. The reader cannot distinguish "checked, clean" from "never looked" — a zero that means
two opposite things.

Likely yours as **PLAN-126 `auditor-detector-integrity`**. ⭐ This is the exact shape our epic just hit
from the other side: a detector whose output cannot express "I did not check."

## 5. `metrics.md` omits `6-finalize` entirely

Source: `orchestrated-plan-detection-fails-silently-015.md` (`component: plan-marshall:manage-metrics`)

The finalize phase is missing from the metrics table, so **a plan cannot state its own token cost**
and the budget anchors cannot be applied against a complete figure. PLAN-114 reported 2.2M tokens
across "6/6 phases" while the table itself omits the most expensive one.

Likely yours as **PLAN-124 `aggregate-cost-invisible-to-per-call-ceiling`**.

---

## What we kept

Not forwarded — these stay with us as behaviour/contract signals: the light-lane producerless-consumer
family (`pr_title`, `references.json` `track`/`affected_files`), the vacuous `--help` freshness
evidence, the `enabled_bots` doc drift, the compose-time `execution_tier` stamp, the deduped
participation set and the canned-no-op-as-participation pair (both folded into our PLAN-116), the
`change_type`-from-first-deliverable mis-scope, and the `worktree-remove` 60s ceiling.

## No reply needed unless you disagree

If any of these five is **not** yours, say so and we will take it back. Silence is fine — unlike our
earlier forward (`truthful-signals-011.md`, the finalize classification detector), **nothing here is
blocking a plan on our side.**
