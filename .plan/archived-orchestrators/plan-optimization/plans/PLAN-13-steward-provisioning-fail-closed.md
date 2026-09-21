# PLAN-13: steward-provisioning-fail-closed

epic: plan-optimization
workstream: WS-03

> Staged plan spec — the SYSTEMIC follow-up to WS-03's three point-fixes (PLAN-07/08/09). Promoted
> from the META-PATTERN watch after all three landed. Builds on ADR-009 (fail-closed principle,
> shipped with PLAN-08 #934). Re-ground citations at outline.

## Objective

Encode a systemic "provisioning writes must fail closed / must never silently succeed" invariant
across the steward/manage-config provisioning surface, and sweep for other sites of the same class —
rather than leaving the three shipped point-fixes as the whole answer. The class (all consumer-
surfaced, cui-open-rewrite): `project set` returned green on a wrong write (PLAN-07); a blanked
version stamp made staleness vacuously `fresh` (PLAN-08); a merge queue was enabled without its CI
(PLAN-09). #927 fixed the SAME class *inside finalize* ("green when CI disagrees"). ADR-009 named the
principle; this plan operationalizes it as an invariant + an audit sweep.

## Deliverables

> **Folded in 2026-07-19, operator-directed.** D1/D2 are two consumer-surfaced (API-Sheriff) CONCRETE,
> VERIFIED instances of this plan's fail-silent-fresh class — D1 is the "highest-value boundary" the split
> guard names. Fix them first (with regression tests), THEN sweep (D3) + encode the invariant (D4). D5 is
> the separately-folded single-command-upgrade reload-directive seam (feasibility CONFIRMED) — adjacent
> upgrade-surface work, cleanly separable if scope balloons (see Size / split guard).

### D1 — manifest resolver: highest-version-wins, not first-hit-wins (fail-silent-fresh root)

`find_installed_manifest_path()` (`generate_executor.py:1156-1159`) returns the FIRST existing candidate;
candidate 3 (cache root `base_path/dist-manifest.json`, line 1127) precedes candidate 4 (marketplace clone
root, line 1152) with no version/recency comparison. A leftover cache-root `dist-manifest.json` (e.g.
0.1.1144) permanently shadows the authoritative clone-root manifest (0.1.1152) → the whole staleness chain
(resolver→executor stamp→`provisioned_version`→preflight) reads one poisoned source and self-consistently
reports `fresh`, silently missing the next `executor_changed_at_version` / `config_changed_at_version` bump.
**This is a PLAN-08 #934 residual** (it added candidate 4 but AFTER candidate 3). **Fix:** collect ALL
existing candidates and pick the highest `version` (parse-and-compare). **Acceptance:** with both a
cache-root and a clone-root manifest present at differing versions, the NEWER is resolved; fail-closed
(`unknown`) still holds when none is resolvable. Regression test with two manifests at differing versions.

### D2 — prune superseded version dirs on regen (executor_action: regenerated-every-run)

`preflight` reports `executor_action: regenerated` on EVERY run because regen does not prune superseded
version dirs (observed: `cache/plan-marshall/plan-marshall/{0.1.1131,1137,1144,1152}`), so the
multi-version-pollution trigger survives its own remedy and the signal never clears. **Fix (confirm shape
at outline):** either prune superseded version dirs on regen, or make the pollution check advisory-once
rather than regenerate-every-time. Coordinate with the plugin-cache orphan-GC surface (7-day orphan GC
exists but does not prune version dirs on regen). **Acceptance:** a second consecutive regen does not
report `regenerated` when nothing changed. Regression test.

### D3 — audit sweep of the provisioning surface for silent-success / vacuous-default sites

Enumerate (do not sample) the manage-config / marshall-steward / executor-provisioning write + status
paths for the two failure shapes: (a) an unknown/invalid write that returns `status: success`; (b) a
missing/degraded input that yields a vacuously-safe verdict (e.g. `fresh`/`ok`) instead of failing
closed. **Acceptance:** a written enumeration of every such site with a fix-or-justify disposition.

### D4 — encode the fail-closed invariant (not just per-site patches)

Where the sweep finds a shared boundary, encode the invariant once (a validated-write / fail-closed
helper or a plugin-doctor-style structural check) so NEW provisioning writes can't regress into
silent success. Tie to ADR-009. **Acceptance:** a new silent-success / vacuous-default write is
caught structurally (test or lint), not only by a reviewer.

### D5 — single-command upgrade: harness-agnostic reload directive (runtime seam)

`/marshall-steward upgrade` regenerates the executor/agents but they are **session-pinned at session
start** (`upgrade-flow.md:152`), so today the flow tells the operator to restart the whole session.
Feasibility CONFIRMED 2026-07-19: Claude Code supports an in-session reload via **`/reload-plugins`**
(reloads plugins/skills/agents/hooks; only *monitors* need a full restart, and plan-marshall uses none),
so a regenerated executor/agent set can be picked up live WITHOUT a full restart. **Hard constraint:**
`/reload-plugins` is a harness-level user-typed slash command — a script/executor CANNOT invoke it, so
zero-touch is impossible in any harness; the achievable shape is "upgrade does all work, then emits the
harness-resolved reload directive." **This MUST land in the runtime, not Claude-only** (plan-marshall is
used from other harnesses): add a `platform-runtime` operation (e.g. `session reload-directive`) that
resolves the correct action per `runtime.target` — Claude → run `/reload-plugins`; OpenCode / other →
their equivalent or a restart no-op via the standard no-op contract — and adapt the steward `upgrade`
interface + the "Session Restart Required After Executor / Agent Changes" SKILL section to emit that
resolved directive instead of the blanket restart. **Acceptance:** after a `consumer` upgrade regen, the
flow surfaces the target-resolved reload directive (Claude: `/reload-plugins`); OpenCode returns a no-op/
restart directive; the seam is config-driven (`runtime.target`), not hard-coded to Claude. Test the
resolver per target. **Confirm the exact seam name + monitor-caveat wording at outline.**

## Out of scope / do NOT expand
- Re-fixing PLAN-07/08/09's three specific sites (already shipped) — D3/D4 are the SWEEP + INVARIANT
  (D1/D2 are NEW verified sites, not re-fixes).
- Non-provisioning surfaces (finalize's own gate is #927's domain).
- D5 does NOT attempt to script-invoke `/reload-plugins` (impossible — harness-level user command); it
  RESOLVES + SURFACES the directive only.

## Absorbs
- Open Defect "stale cache-root dist-manifest.json shadows marketplace manifest" (API-Sheriff 2026-07-19,
  VERIFIED at `generate_executor.py:1156-1159`; PLAN-08 #934 residual) → D1.
- Watch "`executor_action: regenerated` on every run / multi-version-dir pollution not pruned"
  (API-Sheriff 2026-07-19) → D2.
- Feature request "single-command upgrade that also reloads the plugin, landing in the runtime seam"
  (operator 2026-07-19; feasibility CONFIRMED via Claude `/reload-plugins`) → D5.

## Size / split guard
Now **5 deliverables** (D1 resolver + D2 prune folded concrete sites; D3 sweep + D4 invariant systemic
layer; D5 upgrade reload-directive seam) — at the ~6 split presumption. **Operator-directed to keep
unsplit** (2026-07-19: chose fold over spawn for both the API-Sheriff sites AND the reload seam, keeping
the whole provisioning/upgrade surface in one plan) — this is the recorded rationale the split guard
requires for proceeding unsplit. The outline retains TWO natural split seams if it balloons: (a) D3's
sweep tail (keep D1/D2/D4/D5 + the highest-value sweep boundary, stage the long tail); and (b) D5, the
upgrade reload-directive seam, is cleanly separable (distinct `platform-runtime`/steward-upgrade surface)
and MAY be pulled into its own follow-up plan if the combined scope proves too large at outline. Record
any split as an epic decision.

## Expected Surface
- `tools-script-executor/scripts/generate_executor.py` — `find_installed_manifest_path` (D1 resolver
  ordering) + regen/preflight version-dir pruning (D2)
- `manage-config/scripts/_cmd_system_plan.py`, `_config_defaults.py`, `_cmd_sync_defaults.py`
- `marshall-steward` provisioning references + SKILL (D1-D4); `marshall-steward` upgrade-flow.md +
  "Session Restart Required" SKILL section (D5); ADR-009; plugin-cache orphan-GC surface (D2)
- `platform-runtime` — new `session reload-directive`-style operation + `standards/contract.md` schema +
  claude/opencode target impls with no-op fallback (D5)
- tests: two-manifest-differing-version resolver regression (D1); consecutive-regen-no-op (D2);
  structural check for the invariant (D4); per-target reload-directive resolver (D5)

## Dependencies and Sequencing
- Depends on: PLAN-07/08/09 (all shipped — precondition met).
- Overlaps with: in-flight PLAN-11 (`_manifest_*` / `_config_defaults` compose path) — adjacent;
  coordinate/rebase on `_config_defaults.py`. Mostly disjoint from PLAN-10/12/14/15/16.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-13-steward-provisioning-fail-closed.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-13.md is recorded}
