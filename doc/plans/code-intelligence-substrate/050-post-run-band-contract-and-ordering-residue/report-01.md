# Run report — 050-post-run-band-contract-and-ordering-residue (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/post-run-band-contract-ordering-i0th2w    **PR:** _pending_    **Outcome:** completed (landing delegated — see Merge gate)

## Skills loaded

- `cloud-plan-lane` (`.claude/skills/cloud-plan-lane/SKILL.md`) — the working contract, loaded first.
- `plan-marshall:ref-code-quality` — read via bundle path.
- `pm-plugin-development:plugin-script-architecture` — read via bundle path.

The plan touches Python scripts, skill docs, and extension-api contract docs; the domain
standards (`persona-implementer`, `python-core`, `pytest-testing`, `plugin-architecture`,
`ref-asciidoc`) were consulted **at the point of use** by reading the surface directly rather than
pre-loading, which is equivalent for a single interactive session and avoided loading skills the
work did not need.

Branch form: **harness-assigned** `claude/post-run-band-contract-ordering-i0th2w` (kept as-is per the
lane contract). GitHub access path: **GitHub MCP server** (cloud). No `/sync-plugin-cache` owed (a
cloud run neither performs nor owes it).

## Deliverables

### D1 — derive producer→consumer edges; publish cardinality; state coverage floor (GATE, mutates nothing)

- **Commit** `5e589b4` — new `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py`.
- Derives the gate-relative producer→consumer ordering-edge set from the declared frontmatter
  markers (not enumerated): `mutates_source: true` ⇒ a `step → gate` edge; `post_run_review: true`
  ⇒ a `gate → step` edge. Asserts every derived edge is order-satisfied (the GATE), pins the
  cardinality to its own derivation (no literal), and asserts coverage is a strict FLOOR.
- **Published cardinality (derived from discovery in the clone):** **13 edges** — 7 before-gate
  (`mutates_source`: `finalize-step-sync-baseline` 3, `lessons-housekeeping` 4, `finalize-step-simplify`
  8, `finalize-step-security-audit` 9, `era-stamp-fill` 21, `automatic-review` 30, `sonar-roundtrip`
  40) and 6 after-gate (`post_run_review`: `review-retrospective` 990, `lessons-capture` 991,
  `preference-emitter` 992, `plan-retrospective` 995, `record-metrics` 998, `print-phase-breakdown`
  999). Merge gate `default:branch-cleanup` at order 70.
- **Coverage stated as a FLOOR:** 13 of 24 finalize steps (≈54%) carry an edge-bearing marker. The
  **consumer side** of an artifact-level *data* edge — WHICH artifact a step reads — has **no**
  frontmatter marker at all, so R1/R2-type data edges are **below this floor** and invisible to any
  frontmatter derivation. A dedicated test pins that the consumer-side vocabulary is empty, so the
  floor is honest rather than asserted-as-a-count. **Verification state:** all 6 tests pass.

### D2 — settle the band contract for a step needing post-merge evidence AND source mutation

- **Commit** `3c8f400` — `phase-6-finalize/standards/source-edit-pushability.md` (new section "The
  both-sides need is representable — by a split") + a pointer in
  `extension-api/standards/ext-point-finalize-step.md`.
- **Chosen outcome:** the **split** (option 2 of the three). The contract now reads that the case IS
  **representable** — by splitting into a post-merge classify pass (`post_run_review: true`,
  `mutates_source: false`, records its verdict durably) and a settle-band apply pass
  (`mutates_source: true`, reads the verdict and makes the pushable edit). The seam is cross-run and
  the durable store is the only channel. Distinguished from the discover-after-merge follow-up-artifact
  rule. `lessons-housekeeping` is documented as the worked case that does NOT need a physical split
  (its report read is best-effort), so no step was physically split.
- Reasoning recorded **in the contract document**, not only here. **Verification state:** the cold
  read is delegated to the pre-PR sub-agent (§ Findings).

### D3 — the retrospective reads a closed accumulator

- **Commit** `d2dabf7` — `plan-retrospective/SKILL.md` (new Step 2.5) + a pinning test in
  `test/plan-marshall/manage-metrics/test_manage_metrics.py`.
- Root: the retrospective (order 995) reads per-phase tokens from `metrics.md` before
  `record-metrics` (998) folds the 6-finalize accumulator, and record-metrics cannot move earlier (it
  must fold the retrospective's own spend) — a genuine circular constraint. Fix: **close the
  accumulator, not the reader** — the retrospective now regenerates `metrics.md`
  (`manage-metrics generate`) before aspect 4 reads it, folding the durable accumulator FLOOR into
  the 6-finalize row **without** stamping an `end_time`. The phase reads non-zero while the partiality
  machinery still marks it partial until record-metrics' authoritative close (its accumulator read is
  assign-cumulative, so the final total overwrites the floor — no double-count). Live modes only.
- **Verification state:** the pinning test asserts fold + partiality-intact together on a real
  non-zero phase (`TestReconcileFloorKeepsPartiality`) — passes.

### D4 — capture the realized footprint while it is true

- **Commit** `a4b7f25` — `manage-references` (new `capture-footprint` verb + schema + docs), a shared
  `plan-retrospective/scripts/_footprint_resolver.py`, the two consumers delegate/reuse it,
  `check-routing-decisions` recovers via the resolver when `--diff-file` is absent, and
  `phase-6-finalize/standards/branch-cleanup.md` calls the capture before worktree removal and records
  `merge_commit_sha` after the base pull. Tests: `test_footprint_resolver.py`, capture tests in
  `test_manage_references_compute_footprint.py`, routing-decisions fallback tests.
- `capture-footprint` persists `references.realized_footprint` while the worktree still exists (the
  capture-while-true side effect); the resolver PREFERS it over any re-derivation. A merge-commit
  fallback tier (`git diff {sha}^1 {sha}` — exact for squash and true-merge, no sibling contamination,
  never `base..HEAD`) resolves post-merge from the recorded `merge_commit_sha`. One footprint
  resolution, two consumers (recall + mis-prune) recover together.
- **Verification state:** all new tests pass; existing resolver/routing/artifact tests updated and
  green. **Negative control** preserved: an unresolvable footprint yields the `FOOTPRINT_UNRESOLVED`
  sentinel / a skip, never a graded zero (`test_tier5_unresolvable_negative_control`,
  `test_mis_prune_skipped_when_footprint_unresolvable`).

### D5 — this change is NOT self-exercising; the observation point

- Discharged by this report section plus the derivation-level tests above.
- **What this run's own execution CAN substantiate:** the derivation-level tests
  (`test_finalize_edge_ordering.py`, `TestReconcileFloorKeepsPartiality`, `test_footprint_resolver.py`,
  the capture and routing-decisions tests) run inside `./pw verify` and pass, so the *derivations*
  (edge ordering, accumulator fold-with-partiality, footprint tiers, capture side effect) are observed
  green from inside this run.
- **What it CANNOT substantiate:** an end-to-end finalize run exercising the NEW behaviour. This is a
  cloud-lane run (`doc/plans/`) that verifies and opens a PR; it does **not** execute the plan-marshall
  phase-6-finalize pipeline at all, so no real retrospective reads a reconciled `metrics.md` here and
  no real `branch-cleanup` captures a footprint here. And even under the plan-marshall lifecycle the
  plan's own manifest is frozen before finalize and executes the OLD order, with script-backed steps
  resolving from a cache synced later in the same run — so **a green finalize of this plan would not be
  evidence the fix works**. The evidence is the derivation-level tests, not this run's own pipeline.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (footprint resolver, capture
verb, check-* consumers, and several test files), so the Python build gate applies. Per-commit
`./pw quality-gate` was run green (`total_issues: 0`, empty `issues[]`) before each Python-touching
commit; the full `./pw verify plan-marshall` was run as the pre-PR gate — result recorded below once
it completes.

## Findings

- **Verification sub-agent (Step 6):** _pending dispatch_ — recorded per instance below.
- **CI / PR review (Step 7):** _pending_.
- **Self-caught during implementation (recorded per instance):**
  - _ruff unused-import_ — after delegating `check-artifact-consistency._resolve_footprint` to the
    shared resolver, `FOOTPRINT_UNRESOLVED` became an unused re-export. **Disposition: fixed** —
    dropped the import and pointed the four test references at the sentinel's canonical home
    (`_footprint_resolver`).
  - _regression: `test_check_artifact_consistency.py::TestResolveFootprintTiers` (×3)_ — the tier
    tests monkeypatched `resolve_live_worktree` on the check-artifact-consistency module, which now
    delegates. **Disposition: fixed** — retargeted the patch at the shared `_footprint_resolver`
    module the delegate actually calls.
  - _regression: `test_plan_retrospective_manifest.py::…::test_mis_prune_skipped_without_footprint`_ —
    the fixture's legacy `modified_files` key is now correctly recovered by the shared resolver, so the
    check re-evaluated instead of skipping. **Disposition: fixed (behaviour is correct)** — renamed to
    `test_mis_prune_skipped_when_footprint_unresolvable` and stripped the footprint keys so it pins the
    genuine unresolvable→skip negative control.

## Reviewer participation

_Pending PR — filled after the review cycle (§ Step 7). Expected reviewer population derived from the
`author_login` of each `automatic-review/standards/{bot_kind}.md` registry doc._

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| … | … | … |

## Cost

- **Tokens:** not available to the agent in this session (this single Claude Code cloud session's usage
  is not surfaced to the agent as a countable figure).
- **Wall-clock:** the run spans one interactive cloud session on 2026-08-11 (UTC); precise start/end
  timestamps are not available to the agent.
- **Population:** whatever the harness counts for this one interactive cloud session. ⛔ NOT comparable
  to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary that a single interactive session does not share. The
  figures cannot be made comparable, so none is presented as if it were.

## Contract check (Step 9)

_Completed at Step 8 condition 3 — see the final pre-merge commit._

## What have we learned (Step 9)

_Recorded at Step 9._

## Residue

- The **merge-commit fallback tier** records `merge_commit_sha` only on the synchronous landing path;
  on the enqueued-not-yet-landed path (Branch F) it relies on the `realized_footprint` capture taken
  before worktree removal, plus re-entry. This is by design (the SHA is genuinely unknown at enqueue),
  and documented in `branch-cleanup.md` and the resolver.
- `analyze-logs.resolve_footprint` keeps its own diff-failure fall-through policy (distinct from the
  whole-chain resolver's fail-closed-to-UNRESOLVED), so it composes the shared per-tier helpers rather
  than the whole-chain function. Intentional; noted so a future consolidation does not silently flip
  its diff-fail semantics.
