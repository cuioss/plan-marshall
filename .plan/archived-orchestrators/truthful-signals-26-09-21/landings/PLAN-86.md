# Landing: PLAN-86 — unchecked finding-persist loses the finding

plan: PLAN-86 · plan_id: `unchecked-finding-persist-loses-the-finding` · PR **#1038**
squash-merged: `25f6500a6` · 3/3 deliverables · 22/22 finalize steps

## Deliverable fidelity

3/3. Published the persist-outcome success-set and routed every caller through it; converged the
subprocess persist and gated the referral on a **store readback**; shipped a regression suite proving
a failed persist can never present as a clean pass. **The spec's explicit bias toward a structural fix
over a doc-contract one held** — a readback is machinery, not a reminder.

## ⭐ What the sweep actually found — the spec's premise was under-scoped

**The request's five-site list was a HYPOTHESIS. A population sweep found 10 production persist sites,
and TWO were 100% broken in production, not one:**

- `scope_creep_check._emit_finding` — a **vacuous `returncode == 0` guard** plus an argv that never
  validated.
- `_cmd_baseline_reconcile.py:461` — finding type **absent from `FINDING_TYPES`**.

**Both had silently dropped every finding since introduction.** This is the
named-sample-read-as-an-enumeration archetype confirmed once more, and it vindicates the spec's
instruction to derive the site set from the population rather than the request.

⚠ The second site is **PLAN-85's subject confirmed at a second location** — a closed enum with no
member matching caller intent. PLAN-85 should treat this as a second data point, not a duplicate.

⭐ **The sub-class nobody had named: all four producer-mismatch emitters were themselves unchecked
persists** — *the guards whose entire job is reporting that findings were lost were losing them.*
That is the flagship archetype folded onto itself, and it is the most valuable single finding of this
plan.

⭐ **The plan reproduced its own target defect, and pre-submission self-review caught it.**
`phase-4-plan` Step 8 parsed only `total_failed`/`ambiguous`, so a rejected persist was silently
dropped **at a call site this plan itself created**. Same archetype, one level up. **n+1 for
"a fix for the archetype introduced the archetype."**

## Review coverage — verified via `ci pr comments`

Six comments, four authors. **Better than #1037, but the completeness signal is still wrong:**

| Reviewer | Ground truth |
|---|---|
| **coderabbitai** | **Real review — *"Actionable comments posted: 3"*.** Also posted a *"Review limit reached"* notice on this PR. |
| **cuioss-review-bot** | *"No major issues detected"* — informational. |
| **sourcery-ai** | *"rate limit of 500000 diff characters"* — **refused. Third consecutive PR** (#1034, #1037, #1038). |
| cuioss-oliver | 2 triage replies. |

⚠ **The report's "3 bots confirmed by fetch" counts a REFUSING bot as confirmed.** The outcome was
benign here only because CodeRabbit genuinely reviewed and found 3 actionable items. **The
completeness predicate is unchanged and still wrong** — PLAN-92's subject, unaffected by this landing.
⚠ CodeRabbit hit its own limit on this PR too — **three consecutive PRs with a CodeRabbit cap event.**

## Decisions worth revisiting (the plan flagged these itself)

1. **Simplify not re-swept after the loop-back commit** — the step record **says so verbatim rather
   than claiming a clean sweep**. ✅ That is exactly the behaviour this epic exists to produce: a
   truthful partial signal beats a confident false one. Recorded as a positive instance.
2. **Preference-emitter skipped its one threshold-clearing pattern** because
   `(default, pr-comment, accepted) = 2` was composed of pr-agent's "no issues" report **plus our own
   triage reply echoed back — a fetch artifact, not an operator preference.** ⭐ **This is PLAN-92
   defect 6 manifesting in a THIRD consumer** (after the pre-merge barrier and `fetch_findings`): our
   own replies re-enter the system as external signal. The skip was correct.
3. **Three CodeRabbit suggestions declined**, each citing a settled outline/decision-log design.
   ⚠ The plan states plainly that **if those decisions were wrong, the declines inherit the error** —
   an honest dependency, carried rather than hidden.

## Latent, deliberately left

`conftest.load_script_module` **unconditionally overwrites `sys.modules[name]`**, so a monkeypatch can
**silently become a no-op rather than an error**. It caused one of this plan's two test failures.
**Blast radius spans the whole suite.** → routed to the test-hygiene family (**PLAN-82**).

## Cost

4M tokens / 3h25m worked / 5h12m wall. **The highest of the three landings today** (#1034 2.7M,
#1037 3.8M).

## Reconciliation

- Row → `shipped`, `pr=1038`, `landing=landings/PLAN-86.md`, plan id stamped.
- **PLAN-89 is unblocked** (`phase-5-execute` released).
- 12 inbox messages (1 landing + 11 candidate-lessons) await drain.
- Operator-owed: `marshal.json` stale (`provisioned_version 0.1.1240` vs installed `0.1.1246`) —
  advisory, run `/marshall-steward`; and a session restart, since the executor was regenerated but
  Claude Code pins the agent registry at startup.
