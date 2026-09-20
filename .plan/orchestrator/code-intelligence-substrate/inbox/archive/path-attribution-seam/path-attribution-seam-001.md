envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=landing
created=2026-08-01T18:31:53Z

## What landed

**PLAN-CIS-023: Path-attribution seam — core owns the merge, bundles claim their paths**

PR: [#1072](https://github.com/cuioss/plan-marshall/pull/1072) — `feat(extension-api): add path-attribution seam for which-module claims`
Branch: `feature/path-attribution-seam`
Worktree SHA at finalize: `183db4b93d0ec3a94d71b73a979b0360142bbefa`

Replaced the hardcoded single-entry `_PROJECT_LOCAL_PREFIX_MAP` tuple in `manage-architecture`'s `_architecture_core.py` with a bundle-contributed path-attribution extension point modelled on the shipped `ext-point-derivation-resolver` contract (declaration, discovery, dispatch, null-on-absent).

Shipped shape:

- New extension point documented under `extension-api/standards/ext-point-path-attribution.md`, sibling to `ext-point-derivation-resolver.md`.
- Core retains the merge (longest-prefix wins), the provenance record (which bundle claimed the match), and the resolution order inside `cmd_which_module`'s four-step ladder. Bundles own only their individual path claims.
- A path claimed by two bundles is an ambiguous key: the merge emits no attribution and reports the collision rather than breaking the tie by iteration order.
- `_PROJECT_LOCAL_PREFIX_MAP` retired; its one confirmed entry (`.claude/skills` → `plan-marshall`) re-homed as a declared claim through the new seam without silently re-deciding the owner.
- Core's own claim (`.plan/**` → `plan-marshall`) registered through the same seam, closing the `module: null` answer that `.plan/execute-script.py` and every `.plan/` script path previously received.
- Fail-closed reporting for unclaimed residue, mirroring the `resolver_count: 0` vs `resolver_count: N, edges: []` distinction already established for edge derivation at Tier 1.
- `which-module` resolution-order documentation updated in `manage-architecture`; attribution model updated in `doc/concepts/code-intelligence.adoc`.
- Tests added/updated under `test/plan-marshall/manage-architecture/`.

## Gate outcomes

All finalize gates green at `9f17cafa59eb7548c1951f237989bc6d45584766`: quality-gate + test-compile + verify, plugin-doctor (4 skills gated), pre-submission self-review (115 candidates examined, no check matched), ci-verify all checks green.

## Residue the epic should track

1. **The two outline-time HYPOTHESIS items were both resolved in-plan** — (a) the ambiguous-identity-key obligation from `ext-point-derivation-resolver` did transfer to a path-to-module function, and (b) the `which-module`-returns-null consumer population was enumerated rather than sampled. Neither remains open.

2. **Explicitly deferred, still owed** — whether `.claude/skills/**` should move from the `plan-marshall` module to `pm-plugin-development`. This plan deliberately re-homed the existing entry *without* re-deciding the owner; that decision belongs to **PLAN-CIS-025**.

3. **Gating relationship now discharged** — this plan gated PLAN-CIS-024 and PLAN-CIS-025. Both can now proceed without re-introducing a hardcoded map.

4. **A real defect reached the PR and was caught by the review bot, not by our own gates** — `merge_path_claims` iterated the claims collection outside the `try` that guards `claim_paths`, so a truthy non-iterable return blanked the whole ownership map. Fixed on-branch (TASK-012). See the accompanying candidate-lesson messages; the notable part is that pre-submission self-review examined 115 candidates and matched none of them against this defect.

5. **Signal-truthfulness discrepancy worth the epic's attention** — the `automatic-review` step recorded `0 comment(s) found` and `project:finalize-step-review-retrospective` recorded `1 true-positive comment (0 counted actionable)`, yet that comment drove a real code fix. Filed as a candidate-lesson; flagging here because it is the confident-signal-hides-a-caveat shape the sibling epic tracks and may belong to `review-apparatus` rather than here.
