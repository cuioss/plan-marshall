envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=landing
created=2026-07-27T19:53:11Z

## What landed

**PLAN-79 `terminal-title-channel-reconciliation`** — PR **#1023**, `fix(terminal-title): reconcile the channel set and machine-own every clear`.

Operator-directed fix-it-once on the terminal-title surface. Six deliverables, all shipped:

- **D1** — Recorded the Channel Delivery Contract in `manage-terminal-title/standards/terminal-title-architecture.md`: all four settled rulings with rationales, the general delivery obligation and its deferred-repaint consequence, the statusLine host fact recorded as explicitly deferred (not re-litigated), and both `current_phase='complete'` writers named. The settled host contract from the shipped PLAN-26 (`#964`) was reused, not re-derived.
- **D2** — Deliver the terminal state before releasing the binding (`platform-runtime`: `_claude_runtime_impl.py`, `session_binding.py`, `runtime_base.py`, `opencode_runtime.py`; contract docs; `manage-status/_cmd_lifecycle.py`).
- **D3** — Made machine-set title-token state machine-cleared **and owner-scoped** across `manage-status`, `platform-runtime`, `manage-locks`, `manage-terminal-title`.
- **D4** — Replaced silent no-op renders with explicit rendered state.
- **D5** — Pinned the observable invariants and retired the defect-pinning tests; every new invariant demonstrated RED against the pre-fix baseline before acceptance.
- **D6** — Converged the doc and config divergences (`claude_runtime.py`, architecture doc, SKILL.md, steward menu).

## Gate record

- `pre-push-quality-gate`: whole-tree verify green — plugin-doctor 0 issues, 15466 tests passed.
- `pre-submission-self-review`: clean, 250 candidates examined. **This verdict was wrong** — see the `self-review-clean-on-a-defect-carrying-diff` candidate-lesson.
- `ci-verify`: green at `1e049aef7`, 0 failing checks — but only after a red CI run on a marketplace-wide static-analysis rule that every module-scoped pre-push gate skips by design (see candidate-lesson `-002`, which carries the corrected framing).
- `automatic-review`: 2 comments; 3 actionable findings fixed in-run.
- `sonar-roundtrip`: 0 new-code issues.
- `review-retrospective`: **2 reviewers tracked against a ground truth of 3** — sourcery attribution gap flagged.

## Residue the epic should track

1. **Every pre-push gate is module-scoped, and module-scoped `quality-gate` skips the marketplace-wide sweep by design.** CI caught `no-historical-prose-in-skills`. `build.py:cmd_quality_gate` runs `doctor-marketplace.py quality-gate` **only when `module is None`** (its docstring says so); `pre-push-quality-gate` calls `quality-gate {bundle}` per bundle and `finalize-step-plugin-doctor` runs scoped to touched skills, so both take the skip path. Scoped-green / whole-tree-red for **static rules**, not tests. ⚠ **CORRECTION:** an earlier wording of this item called it a gap "no local gate covers" / "only CI evaluates" — **that is false.** The whole-tree form is runnable locally and was run locally to confirm the fix (`verify`, no module arg → `total_issues: 0`, 15466 passed). The gap is scope selection, not capability. See candidate-lesson `-002` for the corrected statement.
2. **Reviewer attribution is lossy** — feeds directly into the PLAN-80 (refusal/participation detectors) and PLAN-72 (PR-Agent erraticism) threads. Sourcery demonstrably reviewed yet no stored finding carries it as `bot_kind`.
3. **Check state carried no participation information in either direction on this single PR** — new first-party bidirectional evidence on one PR for the standing rule. Relevant to PLAN-80.
4. **The learned build-timeout estimator regressed the budget after a fast failure** (1617s -> 1007s while the suite was growing), then timed out a legitimate run. Tool-layer defect we own.
5. **D3 — the deliverable whose whole purpose was owner-scoped machine-clear — shipped an unscoped in-memory clear.** A fix for the vacuous-guard archetype introduced the archetype. Reinforces the archetype family (now includes a second self-inflicted instance after `#1013 _split_bundle_version` / PLAN-81).
6. **A reviewer-named call-site list was a sample, not an enumeration** (3 named, 14 real). The fix moved to the shared write seam.

No open blocking findings. Nothing deferred out of scope.
