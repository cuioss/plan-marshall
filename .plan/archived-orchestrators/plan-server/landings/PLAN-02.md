# Landing Analysis: PLAN-02 — marshalld registration scope population

epic: plan-server
workstream: WS-01
pr: #941 (squash-merged to main, 2026-07-19)

> Landing record for one shipped plan. Lives at `landings/PLAN-02.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

## Ground-truth verification

- PR #941 merged: **corroborated** — `origin/main` carries `245ca426f fix(build-server): populate marshalld registration scope defaults with re-register repair path and positive-routing coverage (#941)` (single squash commit).
- Changed surface matches spec: **corroborated** — `git show --stat` on the merge commit touches `manage-build-server/scripts/manage_build_server.py` (register path), `script-shared/scripts/build/_build_execute_factory.py` (routing-side / `routable_notations()` source-of-truth), `manage-build-server/SKILL.md` (docs), plus two new tests `test_register_defaults.py` and `test_acceptance_positive_routing.py`.
- Archived plan present: **corroborated** — `.plan/local/archived-plans/2026-07-19-marshalld-registration-scope-population/`.
- Registry STILL inert: **corroborated** — `~/.plan-marshall/marshalld/registry.json` for `/Users/oliver/git/plan-marshall` still has `worktree_containers: []`, `notation_allowlist: []`, `updated_at` unchanged `2026-07-18T21:45:41Z`. The plan ships the CODE; the machine-global registry repair is an operator re-register (the anti-laundering wall keeps `register` out of agent contexts) — consistent with the landing's own "operator action still owed" note.
- Deliverable-level fidelity below combines the operator's trusted landing narrative with the verified PR diff/stat; the gemini isinstance catch is a bot claim (untrusted lead) but corroborated by the merged diff touching `_effective_scope_value`.

## Deliverable Fidelity vs Spec

Spec: `plans/PLAN-02-registration-scope-population.md` (4 deliverables; D1 root-cause is investigative and folds into the D2 implementation, D3 repair is realized as the idempotent re-register path).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 Root-cause the empty-scope registration | shipped-as-specified | root cause found: `run_register` passed `args.container or []` / `args.notation or []` verbatim and there were no discoverable `--container`/`--notation` flags ⇒ every registration empty-scope; daemon verifier then refused every submit (`not_registered`/`exec_path_escape`) — confirmed LIVE this run (a real submit for module-tests returned `refused: not_registered`) |
| D2 Populate the two fields at registration | shipped-as-specified | `_default_notation_allowlist()` derives from a new public `routable_notations()` accessor on `_build_execute_factory` (single source of truth shared with the D5 routing map — no drift); `_default_worktree_containers(root) = [{root}/.plan/local/worktrees]`; precedence explicit CLI > existing non-empty stored > computed default |
| D3 Repair the existing inert registration | shipped-as-specified (code) / **operator action owed (machine state)** | re-register is the idempotent backfill/repair path — no hand-editing `registry.json`; BUT the live meta-project entry is NOT yet repaired (register is operator-run only) |
| D4 Positive-routing acceptance test | **shipped-modified** | outline (operator-approved) substituted a deterministic `verify_submit`-boundary assertion (registered-via-defaults ⇒ accepted; empty-scope ⇒ refused) for the spec's live end-to-end "job-logs non-empty, routed TOON matches inline" — a live daemon run isn't CI-safe |
| _effective_scope_value isinstance guard (TASK-5) | added-unplanned | gemini PR-bot caught a real defect: a corrupted non-list stored field (a string would split per-character); now isinstance-guarded. Loop-back: gemini finding → TASK-5 → full re-verify + CI → clean |

Verdict: **3/3 spec deliverables shipped** (D4 shipped-modified with recorded rationale; D1+D3's investigative/repair legs folded into the implementation), plus 1 unplanned gemini-caught fix. No deliverable dropped. **Residual gap: the spec's live end-to-end routing proof was substituted by a boundary assertion** — the worktree-container live-routing watch stays ACTIVE.

## Metrics and Anomalies

- Tokens: 2.1M total across the plan.
- Duration: 4h12m worked.
- Anomalies: one review loop-back (gemini isinstance defect → TASK-5 → re-verify). Whole-tree module-tests/coverage builds were repeatedly harness-reaped (0-byte, no ledger row) and skipped per prior operator approval, relying on per-task quality-gate (green) + CI verify/verify (green twice) — the exact work-preservation pain this epic exists to remove, still blocked by the inert registration this plan fixes at the code level.

## Routing and Merge Behavior

- Review: gemini PR bot active (despite epic-wide sunset it still posted a VALID finding — matches the standing "a pruned gemini can still post a real finding" rule); its isinstance catch was accepted and fixed via TASK-5. 21/21 finalize steps green.
- CI/merge: squash-merged via merge queue; CI verify/verify green twice (once pre-loop-back, once post-TASK-5). No rebase conflict reported. #942 (a plan-optimization plan) landed immediately after on main — disjoint surface, no collision.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-02 → status `shipped`, pr `#941`, landing `landings/PLAN-02.md`
- [x] epic.md Ordered Queue row reconciled from status.json
- [x] Open Defect (marshalld registered but inert) → **code-resolved by #941, but kept OPEN as an operator-action item** (live registry still empty; re-register owed)
- [x] Watch (worktree-container routing UNPROVEN) → **kept ACTIVE** — D4 substituted a boundary assertion for the live job-logs run, so live worktree routing is still unproven
- [x] resume_anchor updated → operator re-register, then PLAN-03
- [x] START-HERE block regenerated

## Follow-Ups

- **⚠ Operator must re-run `python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server register`** to repair the live inert entry — until then the meta-project daemon stays inert and every build still runs inline. Recorded as an Open Defect (operator-action leg) in `epic.md`.
- **Live end-to-end routing proof still owed** — D4's boundary assertion does NOT prove a real worktree build lands in `~/.plan-marshall/marshalld/job-logs/`. Kept as the ACTIVE worktree-container watch; verifiable manually after the operator re-registers (run a worktree build, confirm `job-logs/` non-empty). Feeds PLAN-03 (which adds captured-level fallback/refusal logging that would make this observable).
- **marshal.json provisioning stamp flagged stale** (advisory, surfaced at plan start) → run `/marshall-steward` when convenient. Not orchestrator work; operator note.
- Lesson capture ran in finalize (gemini isinstance / boundary-vs-e2e substitution) → global lessons store; no orchestrator action.
