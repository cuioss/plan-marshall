# Landing Analysis: PLAN-31 — Orchestrator Dispatch Ruleset

epic: plan-optimization
workstream: WS-10
pr: #968 (`dc919162f`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against merge commit `dc919162f` (6 files, +41/-5). **4/4 shipped.** A notably small
diff for a design-first plan — the value is in the decisions, not the volume.

| Deliverable (as executed) | Verdict | Evidence |
|---|---|---|
| D1 — state the Dispatch Decision Rule once in the standard | shipped-as-specified | `orchestration-model.md` (+27/-1) — a new `## Dispatch Decision Rule` section |
| D2 — apply to `analyze` with the reader-vs-Bash composition | shipped-**modified**, better than specified | `workflow/analyze.md` (+6) — see below |
| D3 — apply to `decompose`'s dispatchable/inline-only seam | shipped-as-specified | `workflow/decompose.md` (+5) |
| D4 — point the two orchestrator entry surfaces at the boundary | shipped-as-specified | `marshall-orchestrator/SKILL.md` (+1), `persona-marshall-orchestrator/SKILL.md` (+5/-2), `agent-behavior-rules.md` (-2) |

**All three orchestrator carries were honoured** — worth recording, since they were the
orchestrator's main contribution to this plan:

1. **Re-grounding done properly.** All three targets re-read at HEAD `f22d9c20f`, and — the part
   that matters — **the zero-hits premise was re-verified by direct read, not inference.**
2. **Both hard blockers re-verified TRUE**: `execution-context-reader` declares no Bash;
   `execution-context` explicitly states `AskUserQuestion` is not declared.
3. **The `#967` template was mirrored** — the rule is stated once as a named section in the
   standard, exactly the shape the Terminal-Title Repaint Contract established.

## ⚠ The spec's guessed mechanism was WRONG — and the plan found better

The staged spec proposed a **three-stage pipeline** for D2 (reader extracts candidate struct →
`validate_struct` → Bash-capable verification) to work around the reader-has-no-Bash mismatch.

The plan **dissolved the mismatch instead of engineering around it**, by splitting on
**provenance** rather than on tool surface:

- the orchestrator runs the `ci`/`git` fetch **inline**, so Bash never leaves it;
- **first-party ground truth** dispatches straight to `execution-context`;
- parsing the **operator's own paste** stays inline — dispatching it would be *containment
  theatre*, since the operator's narrative is trusted input by the standard's own posture.

This is strictly better than the spec: no new pipeline, no `validate_struct` hop on trusted
input, and the trust boundary lands where the standard already draws it. **The orchestrator's
inferred mechanism was again wrong** — but this time the spec's own verify-first framing gave
the plan room to replace it rather than implement it.

**Two spec errors the plan corrected:**

- `analyze.md` step numbers in the spec were **stale** — ground-truth verification is Step 2 and
  mid-flight observation is Step 5, not as the spec cited.
- The PLAN-30 sequencing caveat was **moot** — PLAN-30 had already landed as #967. The
  orchestrator carried a stale blocker into the emit.

## Metrics and Anomalies

- Tokens: **2.3M** · Duration: **1h35m**
- Finalize: 21/21; plugin-doctor clean (2 skills gated, **+1 by hand**); self-review clean
  (26 candidates); `finalize-step-simplify` 0 edits; CI green (11 checks, 0 failing)
- Deploy: 1108 files → **0.1.1179**; 10 bundles synced, executor regenerated
- Lessons: 1 new + **2 recurrences merged**

## Routing and Merge Behavior

- **Review**: 3 comments → 2 fixed via loop-back; 1 reviewer, 3 actionable, 2 fixed.
- **⚠ CodeRabbit caught a defect the plan's own Q-Gate had already "fixed".** The canonical
  dispatch form was wrong **three times**: outline draft → Q-Gate fix (`eba657`) → CodeRabbit
  (`skills[0]: []`). Root cause as merged into `2026-07-18-14-001`: **the Q-Gate fix was
  hand-patched against the reviewer's comment instead of re-derived from the owning contract
  doc**, so the rest of the block kept its unverified provenance. This is a sharper statement
  than the original lesson and generalizes well beyond dispatch forms — *fixing the reported
  instance does not re-validate its neighbours.*
- **CI/merge**: merged via queue, cleanup complete, `main` at `dc919162f`.
- **Surface collisions**: none. Ran concurrently with PLAN-29 and PLAN-32.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated (status `shipped`, pr `968`, landing `landings/PLAN-31.md`)
- [x] epic.md queue row reconciled
- [x] `verify-before-implement` — **stays n=2**; both blockers held, so no new falsification.
      Recorded as a *positive* datapoint (below)
- [x] Two new defects opened as follow-ups (below)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **⚠ NEW DEFECT — docs-only plans structurally deadlock the pre-push freshness gate.**
  `build-decision` rules the build `not_necessary` (no `build_map` glob matches markdown), so
  **no `kind=build` entry can ever stamp the worktree sha** — yet `pre-commit-verify-freshness`
  fails closed demanding exactly that stamp. **Contradictory premises: no legal path through
  finalize for a docs-only plan.** Hit **twice this run**, each time costing a ~200s whole-tree
  pytest run purely to stamp a ledger for markdown edits. The plan resolved both **honestly with
  a real build rather than `--force`** — the right call, and the reason the contradiction is now
  documented rather than papered over. Merged as a recurrence into `2026-06-20-16-002`, upgraded
  from *"wasteful"* to *"contradictory premises"*. **This epic ships docs-only plans constantly**
  (PLAN-30, PLAN-31, and PLAN-29's likely shape) — high-value, plan-worthy. **Not staged —
  draining.**
- **⚠ NEW DEFECT — `ci_complete_precondition`'s inner 600s timeout equals the harness Bash
  ceiling**, so it **always loses the race** and gets backgrounded with zero output (lesson
  `2026-07-21-21-001`). Worked around by resolving CI state directly via `ci checks status`.
  **This is the same defect class as PLAN-32's bound inversion** — an inner bound that can never
  fire because it is not strictly less than the outer one. PLAN-32 D2 orders bounds
  `inner < outer` with a re-inversion guard; **check at PLAN-32's landing whether that guard
  generalizes to this instance**, and stage a follow-up only if it does not. Do NOT inject scope
  into PLAN-32 while it is live.
- **Positive datapoint for verify-first.** Both PLAN-31 blockers were re-verified **true** — so
  the instruction did not catch a falsification this time. That is not a wasted instruction: it
  converted two orchestrator assumptions into verified facts at negligible cost, and the plan
  then confidently built on them. **The instruction earns its place on confirmations too**, not
  only on the n=2 catches.
