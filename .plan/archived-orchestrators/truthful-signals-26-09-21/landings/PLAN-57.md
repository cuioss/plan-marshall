# Landing Analysis: PLAN-57 — Lane-router scale-blind false negative

epic: truthful-signals
workstream: WS-01
pr: 1068 — merged as `7201f8d2d`

## Ground-truth corroboration

✅ **Verified independently of the report**: `git log origin/main` shows
`7201f8d2d fix(planning-lane): scale-truthful routing + auto->standard rename (#1068)`.
Finalize 25/25, `archive-plan` completed, worktree and branch removed.

⚠ Per-deliverable fidelity is the plan's own assertion — recorded as verification debt, consistent with
every landing in this epic.

## ⛔ THE HEADLINE IS NOT THE LANE FIX — a ReDoS shipped, and the gate that caught it is the gate the defect would have dropped

**CWE-1333 in shipped code.** `_PATH_RE` ran unbounded over the ingested `request.md` at `phase-1-init`:
**~3 s at 20 KB of adversarial input, 145 s at 10 MB.**

⭐⭐ **Found by the finalize security audit — the step the `minimal` posture would have dropped.** That is
this plan's own thesis demonstrated on itself: **a wrong narrow verdict is a security-gate suppression
path, not a cost optimisation.** The plan argued the abstract case and then produced the concrete one.

⚠ **This is now a chain of three, and the chain is the finding:**

| Plan | What it established |
|---|---|
| **PLAN-112** (#1055) | the ceremony pre-filter *could* drop the security audit |
| **PLAN-202** (#1066) | a scope gate *silently reversed an explicit operator override* |
| **PLAN-57** (#1068) | a wrong narrow verdict *would have suppressed a real CWE-1333* |

⇒ The lane/ceremony/scope-gate family is no longer a correctness-of-routing question. **It is the
project's principal security-gate suppression surface**, and should be ranked as one.

## ⭐ The plan reproduced its own defect three times, and only the third fix was structural

The gate **re-derived a subset of the sensor's rules and drifted** — first on `scan_incomplete`, then on
`fan_out_marker`. The first two fixes re-stated the rules; the third made the detector **call
`classify_scope_pure` and consume its band**, so gate and sensor are **one decision by construction**.

⭐ **That is the correct shape and worth generalising**: two components that must agree are made to agree
*by construction*, not by two authors keeping two copies in step. The first two attempts are what
"fixing the instance" looks like; the third is what fixing the defect looks like.

## ⭐ Five instances of one archetype — two of them created by the plan itself

`_GLOB_RE`'s `**` matching markdown bold; the `epic:` metadata key; the sweep harness vacuous in every
worktree; **an ad-hoc checker that reproduced the bug minutes after the author read the fix**; and the
unreachable safety net.

⭐ **The keeper rule, stated by the plan itself:** ***any path-part skip-list is guilty until shown to
scan.*** ⛔ And the fourth instance is the one to remember — **reproducing a bug minutes after reading its
fix** is the strongest evidence in this epic that archetype knowledge does not transfer by exposure.
**Vacuous/empty-match family: now n≈13 across the epic.**

## Four things the operator reported as true and unflattering — recorded, because they were volunteered

1. ⛔ **The required bot's review is ONE HEAD STALE** (finding `ea33a6`), accepted by the operator. ⭐ **And
   the refresh path does not exist**: `/review` got no response in 449 s, `ci pr ready` **returned
   `success` but was a no-op**, and the abstraction has `pr close` with **no `pr reopen`**. ⇒ Three
   independent recovery routes, none functional. **A `success` return from a no-op is the epic's theme in
   the CI abstraction itself.** ⇒ Routes to `review-apparatus`.
2. ✅ **`finalize-step-simplify` and `finalize-step-security-audit` were not re-fired after the loop-backs,
   and their stamps honestly name the OLDER trees they validated.** ⭐ **Credit this explicitly**: the
   operator declined to re-stamp them to look current. A stamp that names the tree it actually validated
   is exactly what this epic asks for, and it is the first time in the series a stale-but-honest stamp was
   preserved rather than refreshed.
3. ⛔ **`finalize-step-preference-emitter` was SKIPPED, not clean** — executor notation unresolvable, no
   aggregation ran — **and this plan had 12 FIX dispositions concentrated in two modules that plausibly
   crossed the promotion threshold.** ⇒ A skipped aggregation reported in the same shape as a clean one;
   the promotion that should have fired cannot be shown either way.
4. ⛔ **Three instrumentation defects, one of which indicts itself**: phase-6 carries **three disagreeing
   token totals (6× spread, no partial marker)**; the dispatch-boundary artifact captured **3 of 12**
   dispatches; and its **own coverage check reports 0% recall** because it derives the footprint from a
   worktree `branch-cleanup` deleted a step earlier — *"reporting 'I could not look' as 'I looked and
   found nothing,' for every orchestrated plan."*
   ⚠ **That third one is already an Open Defect here** (from #1065) — this is its **third independent
   observation**, which settles it as structural rather than incidental. The token-total spread is the
   **third** instance of the disagreeing-ledgers item already forwarded to `code-intelligence-substrate`.

## Review economics

CodeRabbit **12** actionable across three heads; pr-agent (required) **1** — ⭐ **but it corroborated
CodeRabbit independently, and that convergence is why the `fan_out_marker` gap was fixed rather than
triaged away.** Sourcery **refused all three heads on diff size, zero coverage.**

⭐ **The lesson is not "pr-agent underperformed."** A single corroborating finding from an independent
reviewer changed a disposition from *triage* to *fix*. **Convergence carried more value than volume**, and
a participation metric counting findings would have scored this backwards.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1068; `landing`; `plan_marshall_plan_id` — all four stamped
- [ ] **14 inbox messages** (1 landing + 13 candidate-lessons) — pending drain; **its finalize is quiet**
- [ ] post-merge PR revisit for #1068 — owed (ours)
- [ ] ⚠ **The two provider defects named in the report are ALREADY FORWARDED** — pr-agent's in-place edits
      defeating `comment_id` dedup (round-5 #2 → `truthful-signals-006`) and `post_responses`
      non-idempotency with 9 duplicate replies (round-6 #6 → `truthful-signals-007`). **Do not re-forward;
      record the recurrence on the existing items.**

## Parallelization Consequence

⭐ **PLAN-57 was the LAST running plan — the epic now has R = 0.** `manage-status` is free, which
**unblocks PLAN-TRUTH-003** (blocked ×2 on PLAN-57 and PLAN-202, both now shipped). Re-derive from the
spec at emit, not from this sentence.
