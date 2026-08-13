# Run report — 350-change-type-is-one-word-for-two-different-scopes (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/change-type-scopes-j6mbc6    **PR:** TBD    **Outcome:** in progress

## Skills loaded

Loaded by reading the bundle source path (the `plan-marshall` plugin is not installed in this
cloud session; the file route always works):

- `plan-marshall:ref-code-quality` (+ `standards/code-organization.md`) — always.
- `pm-plugin-development:plugin-script-architecture` — always.
- `pm-dev-python:python-core` — Python production code surface.

Not separately loaded (their standards are consulted on demand): `pytest-testing`,
`plugin-architecture`. `persona-implementer` not loaded — this is a scoped fix, not a
green-field build.

## Deliverables

### D0 — GATE: derive both scopes and every producer/consumer (mutates nothing)

**Two scopes, both spelled `change_type`, confirmed by symbol:**

**Scope A — PLAN scope: the plan's settled classification.** Named `status.metadata.change_type`
(a single, plan-wide value).

- *Producers (write):* `manage-status:change-type-heuristic`
  (`_cmd_change_type_heuristic.py::cmd_change_type_heuristic`, writes `status['metadata']['change_type']`
  at line 230, phase-1-init Step 8a.5 / phase-3-outline Step 4, high-confidence non-ambiguous only,
  self-skips the persist in the ambiguous branch); manual
  `manage-status metadata --set --field change_type`; the LLM `detect-change-type` fallback in the
  ambiguous branch.
- *Consumers (read):* `manage-status:planning-lane` (`_cmd_planning_lane.py:785`
  `metadata.get('change_type')` → S3 deep-bias routing); `manage-status:classification-validate`
  (`_cmd_classification_validate.py:277` → feature-as-bug_fix gate); phase-6-finalize
  architecture-refresh. **NOT read by `compose` — this is the gap.**

**Scope B — DELIVERABLE scope: a deliverable's local kind.** Named per-deliverable `change_type` in
each solution-outline **Metadata:** block.

- *Producers (write):* phase-3-outline authors one `change_type` per deliverable; validated by
  `manage-solution-outline.py:201,206-217` against the canonical vocabulary; recipes supply
  `default_change_type` per deliverable (change-types.md:103).
- *Consumers (read):* **phase-4-plan Step 7b (SKILL.md:681)** — "use the **first deliverable's**
  `change_type` when the outline has more than one" — forwarded at SKILL.md:734 as
  `compose --change-type {change_type}`. **THE forwarding path, confirmed by symbol.**
  Also `phase-4-plan/standards/breaking-refactor-task-split.md:13,25` (a genuinely deliverable-scoped
  consumer — the deliverable's own kind decides breaking-test splits; correct usage, left alone).

**Scope C — the confusion site: the `compose --change-type` flag.** `argparse` line 2707
(`required=True`) → `args.change_type` in `cmd_compose`. **Sourced** as deliverable-scope (first
deliverable, via phase-4-plan); **used** as plan-scope — it drives the six-row `_decide` matrix
(line 1974), the `simplify_inactive` pre-filter (line 1874), and the whole plan's phase-5/phase-6
step selection. The code itself documents the first-deliverable-wins sourcing at lines 1879-1882.

**Which scope is accidental?** Not assumed — derived. The composer makes **plan-wide** decisions, so
it needs the **plan** scope. The settled classification (`status.metadata.change_type`) *is* the plan
scope and is authoritative (written at high confidence, read back correctly by finalize). The flag
receives the deliverable scope by accident of phase-4's first-deliverable-wins rule ⇒ **the
deliverable-sourced flag is the accidental narrowing; the plan scope is what the composer should
use.**

**Claim-label resolutions (each re-derived at HEAD):**

| Claim | Verdict | Artifact |
|---|---|---|
| Composition takes change type as a required caller-supplied flag and never reconciles it | **CONFIRMED** | `argparse:2707` `required=True`; `cmd_compose` reads `args.change_type` and validates only against `VALID_CHANGE_TYPES`; no read of `status.metadata.change_type` anywhere in the manifest scripts |
| The wrong value came from the first deliverable | **CONFIRMED by symbol** | phase-4-plan SKILL.md:681 "use the first deliverable's `change_type`" → :734 forward |
| The compose path still exists at HEAD | **CONFIRMED** | `cmd_compose` present; `--change-type` required |
| Nothing already reconciles the two (asserted absence) | **CONFIRMED absent** | compose reads `status.metadata` via `_read_execution_profile`, `_read_recipe_source`, `_read_task_queue_active`, `_read_merged_phase_6_step_map` — none reads `change_type` |
| A compose call used a deliverable's type while the settled type differed (originating run) | **NOT re-derivable** | first-party to another run's `.plan/` logs, absent from this clone — but the code-side premise above holds regardless |
| Five-instance corpus cluster is the same defect at population scale | **NOT re-derivable** | corpus not reachable from this clone |

The `.plan/`-only claims are cited, not merged, per the plan's Notes.

### D1 — reconciliation (see § below): in progress
### D2 — name the scopes apart (flag rename): in progress
### D3 — record which scope the narrowing used: in progress
### D4 — tests, each seen red first: in progress

## The ⚠ decision — should the flag remain caller-supplied?

**Decided explicitly: yes, the flag stays (renamed), and reconcile-and-refuse is implemented rather
than replaced by a pure store-read.** The ⭐ hint invites dropping the flag and having compose read
`status.metadata.change_type` itself (a "lost-update"→"server-authoritative" collapse). I considered
it and rejected it: a pure read cannot satisfy D1's *"the contradiction is refused and the message
names both"* (it would silently use the settled value and ignore the flag), cannot satisfy D4(a)'s
refusal test, and would regress D4(c) (a no-settled plan has no value to compose from once the flag is
gone). The lost-update concern is instead resolved by making the settled value **authoritative**: the
flag may only *agree* with it (else compose refuses), so a caller can no longer silently narrow the
plan. The flag remains the sole source only when no settled classification exists (the D4(c) path).

## Build gate

_pending_

## Findings

_pending — verification sub-agent, CI, PR review_

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
