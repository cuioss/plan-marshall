> ⛔ **MERGED OUT 2026-09-18 (cleanup A5) — this spec is RETIRED and must not be launched.**
> Its substance now lives in **PLAN-TRUTH-162** as D3/D4: argparse rejections recur; the canonical hint is not uniform — both are a documented invocation the enforced surface rejects, and both sweep one documentation corpus.
> The deliverables were carried, not summarised, and this spec's own gate collapsed into the
> receiving spec's D0 rather than being duplicated. This file stays on disk unchanged below the
> line — a superseded spec is never deleted. Its queue row is `parked`, because
> `queue --transition` cannot write `superseded` (see PLAN-TRUTH-143 D9).

# PLAN-TRUTH-159: A documented finalize-step command is one this repo's own hook denies, and the documented recovery is a dead end

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-14 from a cross-epic transfer (`review-apparatus-039.md`), observed first-party during
`plan-pr-046`'s finalize (PR #1477, merged `77cb2e251`). Routed here per the standing three-way rule: not
PR/review subject matter — a workflow-doc-versus-enforcement divergence, this epic's theme.

## Objective

**`project:finalize-step-deploy-target` documents `./pw generate-claude` as its Step 1 — a command this
repository's own PreToolUse hook rule R4 unconditionally denies (any Bash call whose first token is
`./pw`) — and the redirect R4 itself offers is a dead end: `architecture resolve --command
generate-claude` returns `Command not found`, because a generator alias is not a canonical build
command.**

The documented command cannot be run, and the documented recovery cannot be reached. The step completed
on PR #1477 only by routing through the build executor instead — the working invocation is the
undocumented one. This is a workflow doc prescribing an invocation the enforced surface rejects, the same
class `PLAN-PR-017` (shipped, review-apparatus) settled once already: correct the doc to match the
enforced surface, never widen the enforcement to match a stale doc.

**The operator decision, already taken 2026-09-13 and binding on this plan's scope.** The skill adopts the
executor invocation as its documented Step 1. R4 stays intact and gains no carve-out — a carve-out would
widen an unconditional deny rule whose whole value is being unconditional, and every future generator
alias would inherit the exemption silently. `architecture resolve` is NOT taught the `./pw` alias — that
would be a resolver-contract change (generator aliases becoming canonical build commands), a larger
decision than this defect warrants.

## Deliverables

Three deliverables. D0 is a gate.

**D0 — GATE: derive the population of every other documented `./pw`-prefixed invocation across the
project-local `.claude/skills/` surface.** This instance was found only because a run happened to hit it —
a single-site fix over an underived population is the archetype this project keeps re-finding. Publish the
population and its size before fixing any one site.

**D1 — `project:finalize-step-deploy-target`'s Step 1 states the build-executor invocation that actually
runs**, matching the operator's binding decision above.

**D2 — Correct every other member of D0's population**, and add a check that keeps it true: a lint-time
detector that flags a documented Bash invocation an installed hook rule would deny, so the next instance
is caught before a run hits it rather than after.

## Claim Labels

- OBSERVED: `project:finalize-step-deploy-target` documents `./pw generate-claude` as its Step 1 (per the
  source transfer, first-party on PR #1477's finalize). ⛔ Not independently re-read against this repo's
  skill file at staging time — re-verify at outline (verify-at-outline).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: finalize-step-deploy-target/SKILL.md line 83 still documents ./pw generate-claude as Step 1 at current HEAD, re-read in full
- OBSERVED: this repository's PreToolUse hook rule R4 denies any Bash call whose first token is `./pw`
  (per the source transfer). Re-verify against the live hook config at outline (verify-at-outline).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: platform-runtime/standards/pretooluse-enforcement.md line 59 confirms R4 denies any Bash call invoking ./pw or a bare mvn/npm/gradle, redirecting to architecture resolve
- OBSERVED: `architecture resolve --command generate-claude` returns `Command not found` (per the source
  transfer, first-party). Re-verify at outline (verify-at-outline).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: Live-ran architecture resolve --command generate-claude at cleanup: returns status error, message 'Command not found', available[6] lists clean/compile/quality-gate/verify/module-tests/coverage -- generate-claude is absent, redirect confirmed a dead end
- ⚠ HYPOTHESIS: the `./pw`-prefixed-invocation population across `.claude/skills/` is non-trivial and
  underived. ⛔ Explicitly flagged by the source transfer as "NOT enumerated at HEAD in this checkout... the
  count is unknown, not zero." D0 owns the derivation (verify-at-outline).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: Shallow grep at cleanup: 4 distinct files under .claude/skills/ reference a './pw ' invocation, confirming the population is non-trivial (not zero, not one); exact classification per-instance remains D0's job, not re-derived here

## Expected Surface

- OBSERVED: `.claude/skills/finalize-step-deploy-target/SKILL.md` — the documented Step 1 (D1)
- HYPOTHESIS: `.claude/skills/**` — the D0 population sweep target and D2's correction sites
  (verify-at-outline)
- HYPOTHESIS: the PreToolUse hook rule R4's own config/implementation, for the D2 lint-time check
  (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/**` — coverage for the new lint-time check (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the
  harness-blocked `sleep` pacing (folded 2026-09-15 (c))

## Dependencies and Sequencing

- Depends on: none.
- Same archetype as the shipped `PLAN-PR-017` (review-apparatus) — "a workflow doc prescribes a flag no
  script declares" — but a different repository surface (project-local `.claude/skills/`, not a
  marketplace bundle). Not merged; no shared code.
- plan-truth-148 and plan-truth-157 were running when this plan was staged and were NOT re-scoped.

## ⭐ FOLDED 2026-09-15 (c) — THE SAME CLASS IN A MARKETPLACE BUNDLE, DENIED BY THE HARNESS RATHER THAN A HOOK

Forwarded from `api-sheriff-deployment-configurability-016.md` § `-011` (API-Sheriff PR #305). Expected
Surface extended in the same act (`branch-cleanup.md`, above). ⚠ This widens D0's population beyond
`.claude/skills/` and beyond hook-rule denial; the operator decision above (no R4 carve-out, doc follows the
enforced surface) is unaffected and applies unchanged.

Re-grounded at `7a028157e`: `phase-6-finalize/standards/branch-cleanup.md` line 600 prescribes pacing the
merge-lock re-poll with "a single standalone `sleep {interval}` Bash call". The Claude Code harness blocks
a foreground `sleep`, so the documented pacing cannot run as written and the consuming orchestrator
improvised the wait. Same shape as D1: a documented invocation the runtime refuses. A second known member
of the widened population is `architecture-refresh.md` § 2b's `rm -rf`, owned by `PLAN-TRUTH-166` D4 (not
re-owned here). D0 therefore derives documented Bash invocations the runtime would refuse — hook rule OR
harness — across `.claude/skills/` and the marketplace `phase-6-finalize` workflows, and D2's lint-time check
covers both refusal sources. Remedy direction for the `sleep` site: a script-side bounded poll (a
`--wait-seconds`-style option on the lock query), per `plan-marshall/standards/waiting.md`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-159-a-documented-finalize-step-command-this-repos-own-hook-denies.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
