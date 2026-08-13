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

### D1 — Composition reconciles against the plan's settled classification — DONE

Commit `ba766bf`. New read-side helper `_read_settled_change_type(plan_id)`
(`_manifest_decide.py`, mirroring `_read_recipe_source` — best-effort degrade to `None` on a
missing/malformed `status.json`). In `cmd_compose` (`manage-execution-manifest.py`), after input
validation: `settled_change_type = _read_settled_change_type(plan_id)`; if present and it differs
from the supplied value, return `error: change_type_scope_conflict` whose message names **both**
values and **both** scopes, plus `settled_change_type` / `supplied_change_type` fields. No manifest
is written on refusal. Verified by reading the actual refusal message in the test output.

### D2 — Name the two scopes apart (flag rename) — DONE

Commit `ba766bf`. The compose flag `--change-type` → `--plan-change-type` (dest kept as `change_type`
to avoid churning 22 test-namespace files; the CLI spelling is genuinely renamed). Verified as a
**rename, not an alias**: `test_old_change_type_flag_is_rejected` confirms `--change-type` now exits
non-zero (argparse rejects it); `test_new_plan_change_type_flag_is_accepted` confirms the new
spelling. In `cmd_compose` the two scopes are distinct locals: `supplied_change_type` (the flag,
deliverable-scoped) vs `settled_change_type` (the plan-scoped read). Updated the SKILL.md canonical
block, command table, parameter list, and error table; `decision-rules.md` Inputs row + a new
"change_type scope reconciliation" section; and phase-4-plan Step 7b.

### D3 — The narrowing decision records which scope it used — DONE

Commit `ba766bf`. `effective_change_type` = settled-when-present else supplied — consumed by every
change-type-gated decision (`_decide`, `simplify_inactive`). The compose result carries
`change_type_scope` (`settled` | `supplied`), `effective_change_type`, `settled_change_type`,
`supplied_change_type`, and a `decision.log` line names the scope and value used.

### D4 — Tests, each verified to FAIL pre-fix — DONE

Commit `ba766bf`. New file `test_compose_change_type_reconciliation.py` (8 tests): (a) refusal
naming both; (b) matching pair passes, records `settled`; (c) **control** — no settled classification
still composes, records `supplied` (plus a status-without-change_type variant); (d) narrowing records
its scope + input; the reconciliation decision-log line; and the flag rename (new accepted, old
rejected). **Red-first confirmed**: with only the two source files stashed to pre-fix, all 8 failed
for the right reasons (no reconciliation → no refusal; no `change_type_scope` key; old flag still
required). After restore, all 8 pass.

### Post-implementation staleness sweep — DONE

Commit `c638b26`. The fix made the `security_class_inactive` gate's "no change_type leg" rationale
stale (it was justified by the old FIRST-DELIVERABLE-WINS forwarding). Refreshed the rationale in the
main-script comment, `_manifest_rules.py` docstring, `finalize-step-security-audit.md`, and two test
comments to the surviving reason: change_type — even reconciled to the settled classification — is
orthogonal to the security surface.

## The ⚠ decision (continued)

The full text of the "should the flag remain caller-supplied" decision is in the section above; the
resolution shipped as reconcile-and-refuse with the flag kept (renamed), plus phase-4 forwarding the
settled value so the guard fires only on a genuinely wrong caller.

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

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (the compose script, the decide
helper, the rules helper, and three test files changed), so the gate takes its full path. Ran the
full `./pw verify` (all three sub-steps) — **`=== verify: SUCCESS ===`**: mypy(production) clean
(398 files), ruff `All checks passed!`, SPDX passed, plugin-doctor `total_issues: 0` across all 36
rules (including `scan_manage_invocation`, `canonical-enum-choices-drift`, `broken-relative-link`,
`analyze_argument_naming`), mypy(test) clean (734 files), and module-tests **19613 passed, 14
skipped**. A follow-up `./pw quality-gate` after the staleness-fix commit was also clean.
`UV_HTTP_TIMEOUT=600` set on every `./pw` call. No `uv.lock` churn (staged paths explicitly).

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
