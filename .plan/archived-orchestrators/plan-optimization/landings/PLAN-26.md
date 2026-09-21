# Landing Analysis: PLAN-26 — Terminal-Title Refresh Cadence

epic: plan-optimization
workstream: WS-10
pr: #964 (`920f98879`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against merge commit `920f98879` (20 files, +1466/-165). **4/4 shipped.**

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — give the title a footer-equivalent continuous cadence | shipped-**modified**, premise corrected | The spec's candidate mechanism — *can `statusLine` carry a `terminalSequence`?* — was **answered NO by the consult**. `statusLine` cannot carry OSC-0; that candidate is dead. The real gap was different and simpler: the render hook was **already** on Pre/PostToolUse but **matcher-scoped to `Bash`/`AskUserQuestion`**, so `Read`/`Edit`/`Write`/`Grep`/`Task` fired no render at all. Now matcher-less on PostToolUse (`claude_runtime.py` +147/-…) |
| D2 — stop the in-turn path silently no-opping without a tty | shipped, **collapsed into D1's mechanism** | `/dev/tty` demoted to a *labelled fallback* reporting `no_controlling_tty` / `dev_tty_fallback`; the drive seam surfaces non-delivery at **WARNING**, no longer DEBUG-swallowed (`_claude_runtime_impl.py` +100, `runtime_base.py` +51, `session_binding.py` +55/-…) |
| D3 — activation-gated title teardown on `/clear` and on archive | shipped-as-specified | `_cmd_lifecycle.py` (+14), `_status_core.py` (+146). `/clear` proved **hookable** via `SessionStart` + `source: "clear"`, so the D4a sub-branch stayed in scope and the split-trigger never fired |
| D4 — port the changed delivery contract into describe-side docs | shipped-as-specified | `terminal-title-architecture.md` (+108), `platform-runtime/standards/contract.md` (+77), `menu-terminal-title.md` (+22), `hook-authoring-guide.md` (+6), `platform-runtime/SKILL.md` (+7) |

**Root cause was correctly identified, mechanism was not.** The spec's diagnosis — a
delivery-cadence divergence between the continuously-polled footer and the hook-plus-`/dev/tty`
title — **held exactly**. But its *proposed fix route* (statusLine carrying a terminal sequence)
was falsified by the consult. The spec had explicitly flagged D1 as *needing a claude-code-guide
consult at outline*, and that instruction is what caught it. **Second consecutive landing where a
staged spec's mechanism was wrong while its symptom analysis was right** (cf. PLAN-24 #963) —
and the second where an explicit verify-before-implement instruction is what saved the plan.

**Size-guard prediction confirmed.** The spec anticipated that D1 and D4a could collapse into a
single consult; the consult settled *both* open host-contract questions at once and merged
D1+D2 into one mechanism. The staged 4-deliverable scoping held without a split.

**Self-validating, four times over.** The plan emitted its new observable-failure messages during
its own finalize — push-token, two phase transitions, and the archive teardown — all from the
no-controlling-tty context the spec named as root cause. Same self-validation pattern as PLAN-28.

## Metrics and Anomalies

- Tokens: 3.1M
- Duration: 2h57m worked
- Finalize: 20/20 steps; plugin-doctor clean (5 skills gated, 0 issues); self-review clean
  (**104 candidates** — the largest candidate set observed in this epic); `finalize-step-simplify`
  0 edits / 0 findings; CI **11/11 green**
- Deploy: 1105 files; 10 bundles synced, executor regenerated → **v0.1.1175**
- Lessons: 3 recorded
- Anomalies: see the manifest-ordering item under Follow-Ups — **worked around, not tripped over**

## Routing and Merge Behavior

- **Review**: 3 findings → **2 fixed, 1 declined**; 2 reviewers compared in the retrospective.
  Notably this is the **first landing in the recent run where the plan's own new guard code was
  NOT the defect site** — a counter-example to the `guards-are-highest-risk-artifact` watch
  (n=3). Worth recording: PLAN-26's new code is delivery/observability plumbing rather than a
  correctness guard, which may be the discriminating factor.
- **CI/merge**: 11/11 checks green, merged via queue, cleanup complete, `main` clean at
  `920f98879`.
- **Surface collisions**: none. Ran concurrently with PLAN-25/30/32 and the predicted
  disjointness held.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated (status `shipped`, pr `964`, landing `landings/PLAN-26.md`)
- [x] epic.md queue row reconciled from status.json
- [x] **PLAN-30's verification block RELEASED** — the `/dev/tty` silent-no-op defect that made
      PLAN-30's added push calls unobservable is now fixed. PLAN-30 (PR #967, in flight) can be
      verified end-to-end rather than by asserting invocations per verb doc
- [x] **PLAN-29 sequencing resolved** — it was ADJACENT-to-live-26 *if* its D1 picked the Runtime
      route. PLAN-26 has landed, so the adjacency is moot; PLAN-29 is unblocked either way
- [x] Watch `composed-manifest-snapshot` — **n=2 confirmed** (see Follow-Ups)
- [x] Watch `guards-are-highest-risk-artifact` — counter-example recorded, still n=3
- [x] Cross-epic finding routed to plan-server (see Follow-Ups)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **⚠ CROSS-EPIC — plan-server's last open thread observed itself, NEGATIVELY.** The
  orchestrator-tier coverage build ran **from the worktree, daemon up and registered, preflight
  returning `ready`** — and still executed **in-process with zero daemon audit records**. This is
  the worktree-container routing thread that epic has been unable to observe for days; it is now
  observed, and the answer is *broken*. **Key insight: preflight readiness is NOT evidence of
  routing.** Filed as lesson `2026-07-21-14-001`. Per that epic's own standing rule
  (*routing OK → close; broken → new plan*), **the thread needs a plan, not a close** — its
  queue is no longer drainable. Routed to plan-server via its work log; folding into its ledger
  needs an `analyze slug=plan-server` run.
- **`composed-manifest-snapshot` watch — n=2 confirmed, and handled better than PLAN-24's case.**
  `lessons-housekeeping` declares `order: 4` (pre-merge, `mutates_source: true`) but this plan's
  manifest scheduled it at **position 18 (post-merge)**, because the manifest was composed before
  #962 — the very PR that moved it into the settle band. The plan ran it **classify-only** as a
  deliberate workaround; it happened to have nothing to promote, so no harm. **This is the
  predicted behaviour, correctly handled.** PLAN-30 (composed pre-#962) may hit it too; PLAN-32
  (composed post-#962) is the control case and should NOT.
- **Verify-before-implement is now the epic's highest-value spec instruction — n=2 consecutive.**
  PLAN-24's *"do NOT fix on the hypothesis"* and PLAN-26's *"needs a claude-code-guide consult at
  outline"* each caught a wrong mechanism behind a right symptom. Candidate for promotion into
  standing guidance: **any spec whose mechanism is orchestrator-inferred rather than observed
  MUST carry an explicit verify-first instruction.**
- **Version debt worsened**: `marshal.json` 0.1.1163 vs installed **0.1.1175** — `/marshall-steward`
  + session restart owed. Executor has now regenerated three times today.
