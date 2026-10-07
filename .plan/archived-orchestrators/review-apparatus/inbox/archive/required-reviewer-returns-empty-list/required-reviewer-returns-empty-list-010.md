envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:43:19Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-09-05
bundle=plan-marshall

# The post-run-review dirty-path guard names the step that ran, not the step that wrote

## Context

This is the **only Q-Gate finding from this plan still `pending`** (`5ac74f`, filed
2026-09-05T16:35:04Z, and the newest of the twelve). Every other Q-Gate finding across
all five phases closed `fixed` or `taken_into_account`.

The `post_run_review` guard — item 5f sub-item (0), which observes the main checkout on
return and reports any dirty TRACKED path from a step declaring `mutates_source: false` —
fired against `plan-marshall:plan-retrospective`:

> Post-run-review step `plan-marshall:plan-retrospective` declares `mutates_source: false`
> but left dirty TRACKED paths (source, or tracked `.plan/` config/descriptors): `uv.lock`
> — the edit ran after the merge gate and has no push path; it is NOT committed and NOT
> blocking

The attribution is false. `uv.lock` was **already dirty before the retrospective was ever
dispatched**: the finding's own provenance note records it present in the `5-execute`
phase-handshake capture (`main_dirty_files[1]: uv.lock`). The retrospective did not author
it. The real cause is upstream and already known — PR #1417 raised the ruff specifier
without refreshing `uv.lock`, so every local build re-resolves and dirties the tree.

## Root cause

The guard is **per-step and attributes by observation, not by authorship**. It samples the
working tree once when a step returns and names whatever is dirty. It has no before/after
comparison, so it cannot distinguish:

- a path this step wrote (a genuine `mutates_source: false` violation), from
- a path that was already dirty when this step started (someone else's, or nobody's).

The consequence is a signal that is confidently specific and wrong in its most important
field — *which step misbehaved*. That is worse than a vaguer, correct signal, because the
named step is the one a reader will go and inspect, and it is innocent. Any long-lived
tree dirt makes **every** subsequent post-run-review step look like a violator, one after
another; the step named is simply whichever happened to run first after the dirt appeared.

This is the archetype the guard was built to prevent, inverted onto itself: the guard
exists so a `mutates_source: false` declaration is *checked rather than trusted*, and its
check is not sound enough to support the accusation it makes.

## Proposed action

1. **Capture the dirty-path set on step ENTRY as well as exit, and report the difference.**
   The violation is `dirty_on_exit - dirty_on_entry`. Paths already dirty on entry are
   pre-existing conditions and belong in a separate, non-accusatory field.
2. Keep reporting pre-existing dirt — it is genuinely useful — but under a name that
   asserts what was observed rather than who caused it (e.g. `pre_existing_dirty_paths`
   alongside `paths_this_step_dirtied`). The entry snapshot is what makes the two
   separable; without it, only one of the two claims is expressible and the guard is
   forced to make the wrong one.
3. Note that the finding text itself already did this reasoning by hand — a human-authored
   provenance paragraph reconstructed the truth from the `5-execute` handshake. That
   reconstruction is exactly what the guard should compute.
4. Separately: chase the upstream `uv.lock` / ruff-specifier drift from PR #1417, which is
   what keeps the tree permanently dirty and will keep this guard mis-firing until fixed.

## Note on scope

This candidate is about the guard's attribution logic, not about the retrospective step.
The sibling candidate 004 (finalize step re-firing cost) and this one both touch
`phase-6-finalize` but are independent defects; do not merge them.

## Evidence

- Q-Gate `6-finalize` `5ac74f` — anti-pattern, severity warning, **`resolution: pending`**, component `plan-marshall:phase-6-finalize`
- work log `2a634c` @ 2026-09-05T16:34:57Z — the WARNING as emitted
- `5ac74f` detail — "`uv.lock` was ALREADY dirty at this session's 5-execute phase_handshake capture (`main_dirty_files[1]: uv.lock`), before the retrospective was dispatched"
- `5ac74f` detail — "The guard is per-step and attributes by observation, not authorship"
- upstream: PR #1417 raised the ruff specifier without refreshing `uv.lock` (known defect `d2c000`)
