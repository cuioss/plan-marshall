envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T11:28:24Z

# FORWARDED — a superseded plan is indistinguishable from a shipped one in the archived corpus

**Forwarded from `truthful-signals` 2026-07-29** under the inbound routing rule (measurement corpus →
this epic). ⚠ Leads, not facts — **except items 1–3, which are orchestrator-verified at HEAD.**

## The defect

`archive` stamps `current_phase: complete` — **the only terminal value the lifecycle has.** The sole
distinguisher is `status.metadata.archived_reason`, set here to `closed_superseded`.

**Anything keying on `complete` alone reads a superseded plan as a shipped one.**

Raised by the plan itself (PLAN-105, `dispatched-leaf-has-no-search-primitive`) as the one thing it
could not fix from inside its own lifecycle — after doing everything else correctly.

## Orchestrator-verified — the risk is LIVE, not theoretical

1. `audit.py` header: *"Walks `.plan/local/archived-plans/{plan_id}/` directories and, per plan, runs
   a …"* check suite — it **enumerates every archived subdirectory**.
2. ⛔ **`archived_reason` appears NOWHERE in the entire `audit-archived-plan-retrospectives` skill**
   (`git grep` over the skill returns nothing). There is no filter, no carve-out, no branch.
3. `archived_reason` *does* have consumers elsewhere — `manage-status/_cmd_lifecycle.py` and
   `plan-doctor` — so the field is real and read; **the auditor simply does not read it.**

## What it corrupts, concretely

PLAN-105 shipped **nothing** — PR #1046 closed, never merged, `origin/main` carries none of it. Its
recorded cost is **3.1 M tokens / 2h15m worked / 14h6m wall**. All 23 checks will now score it as a
delivery:

| Check | What it will compute |
|---|---|
| token-economics, exploration-share, lane-lever-effectiveness | 3.1 M tokens counted as **delivery cost** |
| `affected_files_recall` | recall against a plan with **no footprint by design** |
| PR-merge velocity | a merge time for a PR that was **closed, not merged** |
| scope-estimate accuracy | estimate-vs-actual for work that **never shipped** |

## ⭐ Why this is the cheap moment

**PLAN-105 is the FIRST superseded plan in the corpus — a population of one.** Fix it now and the
historical series stays clean. Fix it after several land and every figure already quoted from the
corpus has to be re-derived and re-stated, including figures this epic has itself relied on.

## Suggested owner and shape

**PLAN-126 `auditor-detector-integrity`** is the natural owner (same file, already in this queue).
⚠ It is already 6D at the split guard — **weigh adding this against splitting it, rather than
growing it.**

Shape, in the order that matters:

1. **The auditor filters on `archived_reason`**, not on directory presence. A non-shipping archived
   plan is either excluded from delivery-cost checks or **reported in its own bucket** — never
   silently summed.
2. ⛔ **Do NOT special-case the string `closed_superseded`.** Derive the *shipping* predicate
   (a merged PR / a real footprint) and let every non-shipping reason fall out of it — otherwise the
   next terminal reason reintroduces this defect. **A hardcoded list mirroring a set defined
   elsewhere is the archetype this programme has recorded five-plus times.**
3. **Report the exclusion count separately from the examined count** — a corpus check that silently
   drops rows is the same failure in the opposite direction.

## Related, and worth deciding together

The lifecycle has **no terminal value for "ended without shipping"**. Adding one is a larger change
than the auditor fix and is **not** required to close the measurement hole — but if this epic's
direction work touches lifecycle vocabulary, the two should be reconciled rather than solved twice.
