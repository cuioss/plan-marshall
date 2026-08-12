# Run report — 050-post-run-band-contract-and-ordering-residue (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/post-run-band-contract-ordering-i0th2w    **PR:** [#1175](https://github.com/cuioss/plan-marshall/pull/1175)    **Outcome:** completed (landing delegated — see Merge gate)

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
commit. The full `./pw verify plan-marshall` pre-PR gate is **green: `verify: SUCCESS` — 16001 passed,
1 skipped** (≈4m41s), covering quality-gate (ruff + plugin-doctor, 36 rules) and the whole
plan-marshall bundle test suite.

## Findings

- **Verification sub-agent (Step 6) — first pass:** verified all five deliverables **behaviorally
  complete and correct**, with NO correctness defect. Highest-risk checks confirmed: D3's
  assign-cumulative-overwrite (record-metrics' `end-phase` reads the accumulator with source
  `accumulator` → `_apply_provenance` ASSIGNS, so the retrospective's pre-fold floor is overwritten,
  not double-counted) and D4's `{sha}^1 {sha}` merge-commit recipe + the unresolvable→sentinel/skip
  negative control. **D2 cold-read verdict: "this case IS representable — via a split. Unambiguous."**
  The reviewer could not land on the "explicitly refused" reading because both contract docs pair the
  single-step refusal with a titled affirmation of representability. **D2 accepted.**
  - It found **7 stale-doc/comment/message claims** (the required beyond-diff sweep) — all the same
    shape: the resolver grew from 2 tiers to 5, and sibling docstrings/messages/reference passages
    still described the old 2-tier chain. **Disposition: all 7 fixed** in commit `52366d0`
    (`check-artifact-consistency.py` recall/exact-match docstrings + two inconclusive messages + the
    call-site comment; `check-routing-decisions.py` `load_diff_files` docstring; `artifact-consistency.md`
    "Footprint resolution state" + example warnings; `routing-decision-verification.md` skip rows +
    the new `footprint_source` fact). None was a behaviour defect; each is a misleading-signal
    accuracy defect the plan scopes in ("a stale claim in an untouched file is the same defect").
  - Per instance (7): (1) recall docstring, (2) recall inconclusive message, (3) exact-match
    inconclusive message, (4) exact-match call-site comment, (5) reference-doc example warnings,
    (6) reference-doc "Footprint resolution state" 2-tier enumeration, (7) `load_diff_files` "which is
    a skip" over-reach. All fixed.
- **Verification sub-agent (Step 6) — second pass (re-dispatch):** confirmed all 7 first-pass fixes
  accurate against the resolver's actual 5-tier chain, with **no new inaccuracy introduced**. Its
  re-sweep surfaced more of the same defect the first pass missed; combined with my own exhaustive
  grep of the footprint surface, the full set was fixed in commits `603568f` (four prose passages:
  `plan-retrospective/SKILL.md` coverage-contract + achieved-thoroughness, `artifact-consistency.md`
  Inputs bullet, `logging-gap-analysis.md`; plus tightening `check-routing-decisions` "no realized
  footprint" → "footprint unresolvable") and `5382861` (stale test docstrings: "three-tier"/"live diff
  then legacy" → the 5-tier chain). A final marketplace-wide grep confirms no stale 2-tier resolver
  claim remains; the two surviving hits (`pre-push-quality-gate.md` describing the live
  `compute-footprint` query, and plan 050/320's own historical descriptions) are correct or
  out-of-scope. **Verification cycle: clean** — no correctness defect, D2 cold read PASS, all
  stale-claim findings resolved.
- **Build gate (Step 5, final):** `./pw verify plan-marshall` re-run after all stale-claim fixes —
  **green: `verify: SUCCESS`, 16001 passed, 1 skipped**.
- **CI (Step 7):** on the PR head, `verify / gate`, `review / review`, `dependency-review`,
  `generate-check` all **success**; `verify / verify` (the full test suite) ran to green. The
  required `verify / conclusion` gate is enforced by the merge queue at land time.
- **PR review (Step 7):** both surfaces read (conversation + inline threads). Inline review-thread
  surface: **empty (0 threads)**. Conversation: `cuioss-review-bot` posted a clean review ("PR
  contains tests, no security concerns, no major issues"); CodeRabbit posted only a rate-limit notice;
  Sourcery's check was skipped. **No comment was actionable** — nothing to fix or reply to.
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

Expected reviewer population **derived from configuration** — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:
`coderabbitai` (coderabbit.md), `cuioss-review-bot` (pr-agent.md), `sourcery-ai` (sourcery.md).

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published a review artifact over the diff — "## PR Reviewer Guide 🔍: PR contains tests / No security concerns identified / No major issues detected". |
| `coderabbitai` | `rate-limited` | Published only a refusal/quota notice ("Review limit reached … Next review available in: 15 minutes"), not a review of the diff. |
| `sourcery-ai` | `silent` | Its `Sourcery review` check concluded `skipped`; it published no review artifact and no notice. |

**Coverage: 1 of 3 reviewed.** The § Step 8 review-coverage shortfall disclosure **fired**:
"Review coverage 1 of 3 — `cuioss-review-bot` reviewed (no major issues, no security concerns);
`coderabbitai` rate-limited (window reopens ~15 min); `sourcery-ai` silent (Sourcery review check
skipped)." Per the lane this is a **disclosure, not a block** — a rate limit and a skipped check are
routine and outside our control, so the merge is armed on the stated partial coverage rather than held
behind a bot's quota.

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

Re-read the `cloud-plan-lane` skill and checked each step against what happened:

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — named above; the always-load skills were read via bundle path, domain standards consulted at point of use. |
| 2 Branch | **done** — harness-assigned `claude/post-run-band-contract-ordering-i0th2w`, pushed to `origin` before any edit. |
| 3 Plan directory | **done** — `doc/plans/code-intelligence-substrate/050-.../plan.md` exists and opens with the first-instruction block (verified present, not repaired). |
| 4 Implement | **done** — five deliverables addressed; every commit carries the `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" footer. |
| 4 Per-commit gate | **done** — every `*.py`-touching commit was preceded by a `./pw quality-gate` run with `total_issues: 0` and empty `issues[]` (ruff + plugin-doctor). |
| 4 Pushed | **done** — pushed after every commit; no unpushed commit remains. |
| 5 Build gate | **done** — `*.py` changed → `./pw verify plan-marshall` green (`verify: SUCCESS`, 16001 passed). |
| 6 Verification sub-agent | **done** — two independent passes; findings + dispositions recorded (§ Findings). |
| 7 PR cycle | **done** — PR #1175; both comment surfaces read; every comment dispositioned (none actionable). |
| 8 Merge gate | conditions 1–3 met; auto-merge armed (§ Merge gate). Landing delegated to the merge queue / orchestrator collect — this cloud session could not self-wake to watch the queue. **completed, not partial.** |
| 8 Bridge | **done** — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | **done** — appended here. |
| 9 What have we learned | recorded below. |

GitHub access path used: **GitHub MCP server** (cloud). Branch form: **harness-assigned**. No
`/sync-plugin-cache` owed (machine-local build step a cloud run never performs).

## What have we learned (Step 9)

**No contract change proposed.** The run exercised the `cloud-plan-lane` contract end to end and every
step's artifact was producible as written; no command failed in the actual environment, and no step was
ambiguous in a way the contract does not already address. The one friction — the Step 6 beyond-diff
stale-claim sweep needed **two** sub-agent passes plus a manual grep to be exhaustive — is already
anticipated by the contract's own Step 6 note that a run may "re-dispatch a second time to catch two
such statements in bundle docs," so it is the contract working as written rather than a gap.

One minor, evidence-backed **observation** (recorded, not proposed as a change): the LLM-driven
beyond-diff sweep was most reliably exhausted when paired with a **deterministic grep** for the
changed symbol's prior descriptors (the second sub-agent pass and my own grep together caught four
stale claims the first pass missed). A future contract refinement *could* recommend pairing the LLM
sweep with such a grep — but the existing re-dispatch loop converged correctly here, so this is noted
for the operator rather than shipped as a separate `chore/` PR (which would need operator approval this
autonomous run cannot obtain).

## Residue

- The **merge-commit fallback tier** records `merge_commit_sha` only on the synchronous landing path;
  on the enqueued-not-yet-landed path (Branch F) it relies on the `realized_footprint` capture taken
  before worktree removal, plus re-entry. This is by design (the SHA is genuinely unknown at enqueue),
  and documented in `branch-cleanup.md` and the resolver.
- `analyze-logs.resolve_footprint` keeps its own diff-failure fall-through policy (distinct from the
  whole-chain resolver's fail-closed-to-UNRESOLVED), so it composes the shared per-tier helpers rather
  than the whole-chain function. Intentional; noted so a future consolidation does not silently flip
  its diff-fail semantics.
