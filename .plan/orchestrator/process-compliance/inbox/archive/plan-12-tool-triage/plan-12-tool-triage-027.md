envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:44:00Z

# pre-push-quality-gate's builds can never satisfy the push freshness gate's scope cross-check

**Observed (plan-12-tool-triage, finalize, HEAD ca30cbed9):** `default:pre-push-quality-gate` ran every arm exactly as its doc prescribes and all four returned `status: success` — per-bundle `quality-gate plan-marshall`, whole-tree `quality-gate`, whole-tree `test-compile` (module-scoped fallback widened), whole-tree `module-tests` (28166 tests). The very next step, `default:push`, ran `pre-commit-verify-freshness` and refused with `status: stale, reason: build_scope_narrow`; `row_scopes` rated every one of the eight rows `canonical_performs_too_few_analyses`.

**Why it is structural, not incidental:** the scope cross-check (`manage-tasks/SKILL.md` § "The scope cross-check") admits only a *single row* whose canonical performs every required analysis. For a footprint containing a `.py` path the requirement is `compile + lint + test`; each pre-push arm is a separate build row covering a subset (`quality-gate` = compile+lint, `module-tests` = test). No arm the gate runs is `verify`, so no row it writes can ever be `covered`. The push doc's § "Settle-band position" asserts the opposite — that the freshness precondition "permits on a `kind=build` ledger entry carrying the current worktree SHA, which only this gate's just-completed builds can have written" — and that assertion is false for every `.py` footprint.

**Consequence:** every finalize that touches Python halts at push with a refusal, and the only remedy (the reason table's "re-run a build whose canonical and scope cover this change") is an extra whole-tree `verify` that no finalize step prescribes — ~12+ minutes duplicating what the gate just proved, and it exceeds the Bash ceiling so it is moved to background. The orchestrator has to improvise the recovery; the documented halt path records `outcome=failed` and names no step that runs the remedy. This is the same defect memory recorded for PLAN-PR-044 (`freshness: build_scope_narrow`; only `verify` covers compile+lint+test).

**Recurrence at phase-5 Step 12a (same run, loop-back re-entry):** Step 11c ran its documented "one `verify` per affected bundle" — `verify plan-marshall` and `verify pm-plugin-development`, both green — and the Step 12a freshness gate then refused `build_scope_narrow` with `verify {bundle}: scope_narrower_than_change` on both rows. So phase-5's own documented exit gate (11c) also cannot produce the evidence its own transition gate (12a) demands for a multi-bundle footprint; the only admissible row is a whole-tree `verify`, which no phase-5 step prescribes.

**Also observed:** every build invoked by the pre-push gate reported `[BUILD-SERVER] ... plan=NO_PLAN` — the architecture-resolved executables carry no `--plan-id`, so the daemon attributes the plan's own gate builds to no plan.

**Suggested fix directions (for triage, not prescribed):** either (a) the freshness scope cross-check accepts a *set* of rows against the same worktree sha whose union of analyses covers the requirement, or (b) the pre-push gate runs `verify` as its whole-tree arm instead of the separate quality-gate/test-compile/module-tests trio, or (c) push.md documents the verify re-run as a named recovery step rather than leaving it to improvisation.
