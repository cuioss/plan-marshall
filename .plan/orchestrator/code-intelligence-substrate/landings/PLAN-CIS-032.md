# Landing Analysis: PLAN-CIS-032 — Executor Rejects Invalid Invocations Before Spawn

epic: code-intelligence-substrate
workstream: WS-01
pr: 1127 — https://github.com/cuioss/plan-marshall/pull/1127

> Landing record. Corroborated first-party before any transition: `ci pr view --pr-number 1127`
> → `state: merged`, head `feature/executor-rejects-invalid-invocations-before-spawn`;
> `git log origin/main` → `415dcf139`. **And the objective was PROBED LIVE, not read from the
> report** — see § The probe below.

## ⭐⭐ The probe — the guard is live, and it is on the right stream

The epic's standing rule is *probe the objective live, never accept a plan's own success report*.
Run from the main checkout after the merge:

```text
manage-tasks nuke  →  status: error / error: invalid_invocation / reason: unknown_verb
                      rejected: nuke
                      accepted: add-step, batch-add, … update-step   (21 verbs)
```

⭐ **And the claim that most needed checking was the STREAM, because that was the founding defect**
— *"a shape a caller that parses stdout reads as empty rather than as a correction"*. Re-run with
`2>/dev/null`, the TOON **still appears** ⇒ **the corrective is on stdout, not stderr.** The exit
code stays `2`, which is correct: it is an error, and it is now a *legible* one.

⇒ Both halves of the deliverable verified independently of the plan's own account.

## Deliverable Fidelity vs Spec

26 files, +7789 / −1070, 19 commits.

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — repair the script-failure analyzer's `work.log` regex | shipped | in-radius correction |
| D2 — one alias-aware help-derived accept-set shared by both guards | shipped | new `script-shared/scripts/argparse_surface.py` (1357 lines); `_analyze_manage_invocation.py` shrank ~700 lines; `_analyze_argument_naming.py` rewritten |
| D3 — embed per-notation `SCRIPT_SURFACES` in the generated executor | shipped | 106 surfaces over 148 scripts |
| D4 — reject invalid dispatch pre-spawn with a TOON corrective | shipped-and-probed | § The probe |
| D5 — document the contract and its non-self-exercisability boundary | shipped-modified | the boundary claim was **partly refuted in flight** — see below |

⭐ **The architectural win is that the edit-time rule and the dispatch-time rejection now read one
definition and cannot disagree about what a script accepts.** `script-call-drift` deliberately
keeps an independent probe, and `rule-catalog.md` now says so — a recorded exception rather than
an accident.

## ⭐⭐⭐ The result that bears on the epic's METHOD, not just this plan

**The plan predicted its own guard would be inert until a post-merge regeneration and therefore
not self-exercisable. That premise was partly refuted in flight** (decision.log `e4341f`):
phase-5 generates a **worktree-bound** executor, so regenerating it inside the run exercised the
guard end-to-end against 148 real notations. ⇒ **The non-exercisability boundary is
main-checkout-and-cache-scoped, not absolute.**

That mattered concretely. **Four false-rejection defects in the shipped guard were found ONLY by
probing it live, and none by the test suite** — `--help` refused on every script; a leading
top-level flag desynchronising the parser walk; short `-h` still refused after the `--help` fix
(*"zero hits for the token across the test tree"*); and an `unknown_flag` corrective advertising a
set that **contradicted its sibling corrective** on the same node.

⛔ **One shape produced all four, and the plan states it exactly**: *"it still shipped past a green
synthetic suite, because every fixture surface happened to declare at least one flag."* A
hand-written fixture is built to look *representative*, therefore populated — which makes the
entire class *"the derivation strips / omits / mis-attributes attribute X"* **structurally
invisible**, because X is only absent on a surface nobody would hand-write. → **PLAN-CIS-045**.

⭐ Worth recording the asymmetry: **the repair half worked every time.** Each of the four fixes
shipped with fail-first proof and matched negative controls (`6d981f` added three positive plus
three matched negative controls so the fix could not read as disabling validation; `cdbb40` added
an omission control and a required-subset-of-declared non-contradiction invariant).
**The gap is detection, not remediation.**

## Metrics and Anomalies

- 23h34m wall / 11h4m worked / **9.2M tokens**; 18 tasks, 22 finalize steps, 2 loop-backs.
- `pre-submission-self-review`: **six rounds, 1,008,012 tokens ≈ 60% of all 6-finalize spend** —
  the same proportion `PLAN-CIS-031` measured before its delta-scoping landed, on a plan that ran
  **after** it. ⚠ **Do not read that as CIS-031 having failed**: this plan's rounds were
  loop-back-driven with a self-seeding doc-claim half, which is a different mechanism from the
  unscoped re-sweep CIS-031 fixed. **The comparison is a lead for `PLAN-CIS-040` D1, not a result.**
- Q-Gate 6-finalize: 13 findings, **all resolved `fixed`, 0 pending** — ⭐ the contrast with
  #1126's 19-pending is itself evidence for `PLAN-CIS-044`.
- `affected_files`: declared **17**, realized **26**, **recall 58% / precision 88%** — computed by
  hand from the merge SHA because both retrospective checks returned `inconclusive`. ⛔ **Two of
  the 11 undeclared files were the subject of three review findings**, i.e. the under-declaration
  under-scoped a remediation sweep that CodeRabbit then caught. **Sixth sighting.**

## Routing and Merge Behavior

- ⛔⛔ **The required bot carried no information.** `pr-agent`, the **sole REQUIRED** bot, resolved
  `participated_but_empty` on **all three passes**. Every one of the 15 actionable findings came
  from **optional** CodeRabbit. `sourcery` resolved `hard_quota` on all three — deterministic by
  diff size and **will recur on every comparable PR**. ⇒ **A green required-bot signal at the
  merge gate carried no evidence that the diff was substantively reviewed.** → routed to
  `review-apparatus`.
- ⚠ **14 of 60 GitHub comment threads remain unresolved while our store shows 0 pending.** That is
  thread-resolution state rather than undispositioned work — but **a barrier reading only our own
  store cannot see the difference**, which is the confident-signal theme on the review surface.
- Merge: squash via merge queue at `415dcf139`. Two upstream commits rebased in cleanly.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = `1127`; `landing` = `landings/PLAN-CIS-032.md`;
      `plan_marshall_plan_id` was already stamped `executor-rejects-invalid-invocations-before-spawn`
- [x] epic.md queue reconciled; **R = 0, two slots open** — ⛔ **operator hold: NO EMIT**
- [x] Inbox drained 9/9
- [x] New spec staged: **PLAN-CIS-045** (messages 001 + 007)
- [x] Open Defects added: the fail-open regeneration; the required-bot-empty gate
- [x] resume_anchor updated; START-HERE regenerated

## ⛔ Three operator judgement calls, all recorded as SOUND

1. **Self-review closed on a recorded WARNING deviation rather than a clean pass.** Six rounds; the
   behavioural half converged (rounds 4–5 found real shipped-code defects, round 6 found none) while
   the doc-claim half **self-seeded** — each correction authored new prose for the next round to
   audit. ⭐ **Recorded as a deviation rather than hidden behind a green `done`**, which is the
   epic's own thesis applied by the operator to their own report. ⚠ This is the same self-seeding
   mechanism `PLAN-CIS-031`'s landing recorded (correction breeds the next instance) — **second
   sighting, and it is now a pattern rather than an anecdote.** → folded to `PLAN-CIS-043`.
2. **`worktree-remove` needed `--force` after its first attempt timed out mid-deletion.** Verified
   before forcing: main carried the merge, plan state was already moved back, and the only diffs
   were the interrupted removal's own deletions. **Correct order — verify, then force.**
3. **The on-main executor regeneration reported success over a surfaces-less executor.** Recovered
   by running the merged-source generator directly. → **PLAN-CIS-045** D1.

## Follow-Ups

1. ⛔⛔ **`generate_executor` is FAIL-OPEN at the last gate** — it treats *derived nothing* and
   *derived everything* as the same outcome, and the only observable distinguishing them is the
   **absence** of a surface-stats line, which nothing consumes. The shipped guard was **not live on
   main** despite a green sync and a green regen. ⭐ **Directly relevant to the epic's standing
   pin-check rule: this is a SECOND, independent way the on-main executor can silently disagree
   with merged source** — the first being the plugin-registry pin inversion. → **PLAN-CIS-045** D1.
2. `[DISPATCH]` not emitted on loop-back re-fires — **4 of 13 dispatches unlogged (31%)**.
   **SECOND SIGHTING** (first was #1126, 6:1). → folded to `PLAN-CIS-011` as a recurrence.
3. Footprint recovery from the merge SHA — **SECOND SIGHTING**, now with recall/precision figures.
   → folded to `PLAN-CIS-034` D4.
4. `plan-retrospective` Step 3 rows should name the canonical aspect key. → folded to `PLAN-CIS-020`.
5. A review bot re-litigates decisions the plan already settled, because the rationale lives in the
   finding store where the bot cannot read it. Carries an **owed architecture hint**;
   ⛔ **NOT executed here** — `architecture enrich` post-merge writes tracked source onto main with
   no push path. Recorded as a Watch for a plan to land properly.
