# Self-Blocking Guards

## Pattern Statement

A **self-blocking guard** is the deadlock that arises whenever an enforcement
mechanism's own implementation lives inside the marketplace source tree the
mechanism is meant to police. Plans whose diff touches that implementation are
loaded, dispatched, and verified by the *broken* version of the guard — the
very plan that fixes the guard cannot reach finalize because the guard refuses
to let it through. This is the marketplace analogue of the classic compiler
bootstrap problem: the tool that compiles the next compiler is itself
compiled by the previous compiler, so a defect in the previous compiler can
prevent the fix from ever shipping.

The pattern is not specific to any single guard. It applies to every check
whose code path is reached by the same composer / executor / dispatcher that
also publishes the fix:

- Manifest composers that validate the manifest they are emitting.
- Phase 6 finalize steps that gate on rules whose implementations they ship.
- Plugin-doctor rules that scan the same skill directories that hold the
  rule implementations.
- Cache-sync logic that decides whether a sync is needed based on its own
  source files.

The risk surface is wide because the marketplace is intentionally
self-hosting — the workflow that authors marketplace components is itself a
marketplace component.

## Symptoms

The bot-enforcement guard surfaced two failure modes in close succession; both
are characteristic of self-blocking guards in general.

**Missing-prefix failure** — the guard inserts a remediation step into the
manifest using a name shape (`automated-review`) that is correct against the
boundary-normalized representation, but stale callers compared against the
project-prefixed shape (`default:automated-review`) and silently skipped the
remediation. The guard logs success while the manifest is still missing the
remediation entry, so the violation is invisible until finalize fails.

**Wrong-position failure** — the guard inserts the remediation step at a
positionally-incorrect index (e.g., at the end of the list or between two
plan-mutating steps). The step is present, the guard log says "remediated",
but `automated-review` runs after `archive-plan` has already moved the plan
directory or `branch-cleanup` has already deleted the branch. The bot review
either fails to find its inputs or runs against an artifact that no longer
matches the merged state.

Both failure modes share a structural feature: **the guard reports success
while the invariant it is supposed to enforce is still broken.** The plan that
fixes the guard cannot land because the broken guard either rejects it
outright or causes its own finalize phase to fail downstream.

## Mitigation A: Anchor-Relative Insertion Contracts (preferred)

The preferred mitigation is to make the guard *self-fixing*: the insertion
position is computed relative to a stable anchor in the manifest, plus an
exclusion zone of plan-mutating steps that must run after the inserted step.
A plan that edits the guard helper itself can still be finalized by the broken
helper, because the anchor + exclusion contract is robust to the most common
defects (wrong index, missing prefix, reordered candidate list).

The bot-enforcement guard implements this contract in
`scripts/manage-execution-manifest.py` at `_bot_enforcement_insert_index`
(see line 853 for the function definition; the resolution algorithm is
documented inline in the docstring). The function picks the insertion index
in three tiers:

1. Immediately after the stable anchor `create-pr` (its natural neighbour —
   review runs against the freshly-opened PR).
2. Else immediately before the first plan-mutating step in the exclusion
   zone (`archive-plan`, `record-metrics`, `branch-cleanup`,
   `plan-marshall:plan-retrospective`).
3. Else at the end of the list (no anchors found — degraded but safe).

The source file is the ground truth. Do not duplicate the algorithm here —
read the function and its docstring directly when reasoning about edge cases.

What makes this contract self-fixing:

- **Anchor stability**: `create-pr` is one of the oldest, most stable entries
  in `phase_6_candidates`. A plan that touches the guard does not also touch
  `create-pr` ordering, so the anchor still resolves correctly under the
  broken guard.
- **Exclusion zone as fallback**: even if the anchor is removed by an unusual
  plan, the exclusion zone keeps the inserted step ahead of every step that
  would invalidate it. The guard degrades gracefully rather than catastrophically.
- **Bare-name comparison**: the resolver compares against bare names so the
  prefix-shape mismatch (`default:` vs. bare) cannot silently disable the
  resolution.

Anchor-relative insertion is the first choice for any new guard. It moves
correctness from "the author remembered to update every callsite" to "the
manifest shape itself encodes the invariant".

## Mitigation B: Out-of-Band Override Flag (fallback)

Some guards genuinely cannot be made self-fixing — the invariant they enforce
is so coarse that no anchor is reliable, or the broken state is undetectable
from the manifest alone. For those cases the fallback is an **out-of-band
override flag**: a one-shot, plan-scoped, loudly-logged escape hatch that
disables the guard for exactly one plan to let the fix land.

Required properties:

- **One-shot**: the flag clears itself after a single plan finalize, so it
  cannot accumulate technical debt.
- **Plan-scoped**: the flag lives in the plan's config or work directory, not
  in user-global settings. A flag set by one plan must not affect any other
  plan.
- **Loudly logged**: every guard that observes the override emits a WARNING
  decision-log entry naming the plan, the guard, and the rationale recorded
  by the operator. Silent overrides defeat the purpose.

The bot-enforcement guard does NOT use this fallback — Mitigation A
(anchor-relative insertion) was sufficient to make the guard self-fixing.
Mitigation B is documented here so future guards that genuinely need it have
a canonical pattern to follow rather than each inventing an ad-hoc bypass.

When in doubt, choose Mitigation A. Reach for B only after demonstrating that
no stable anchor exists for the invariant in question.

## Cross-References

- `decision-rules.md` — Stacked Rule `bundle_self_modification`. The
  early-`sync-plugin-cache` insertion is the same meta-pattern applied to a
  different self-modification surface: the manifest composer detects that the
  plan's diff touches bundled agents/commands/skills and inserts an early
  sync to keep the in-flight finalize from dispatching stale cached
  definitions. Conceptually the same anchor-relative contract — the early
  sync is positioned relative to the first agent-dispatched step, with the
  exclusion zone implied by "must run before the first dispatch".
- Originating lessons:
  - `2026-04-28-09-002` — first-run bootstrap problem when a plan adds a
    finalize step that depends on a new helper script (superseded).
  - `2026-04-28-13-001` — manifest guard insertion must use prefixed step ID
    and correct ordinal position (superseded).
  - `2026-04-28-13-002` — consolidated bootstrap-deadlock postmortem (the
    canonical record that absorbed both predecessors).
