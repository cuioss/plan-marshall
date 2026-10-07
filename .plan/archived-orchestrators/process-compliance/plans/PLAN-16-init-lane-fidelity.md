# PLAN-16: Init-lane fidelity defects

> ✅ **Staged 2026-09-27 under explicit operator directive ("issues about current problems are to be fixed, not
> relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-16-init-lane-fidelity.md` and is queued in the epic's `queue/` row
> files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Close five defects that the PLAN-12 and PLAN-13 runs hit at plan init, each of which makes
phase-1-init either tell the operator something false or force a rule deviation: the posture
dialogue's static prose contradicts the lane data it is choosing between, the per-step lane
report omits a step, `session_ids` is never captured for a plan created inside a running
session, the scope-estimate heuristic counts provenance citations as change surface, and
domain detection matches the epic slug instead of the work. A fifth, rule-side defect: the
hard rules mandate `Grep`/`Glob` as the fallback while the session may not expose them.

## Deliverables

1. **Posture dialogue from data, lane report complete.** phase-1-init Step 8d option
   descriptions are rendered from `manage-execution-manifest lanes preview`'s kept/dropped
   diff instead of static prose (today "full" claims to add the written look-back, but
   `plan-marshall:plan-retrospective` is in all three postures; what full actually adds is
   `finalize-step-security-audit`, `sonar-roundtrip`, `adr-propose`, `lessons-capture`).
   `lane_report[]` enumerates every step that appears in ANY posture — today
   `lane_report_count: 25` vs `full.phase_6_steps_count: 26`, missing
   `plan-marshall:plan-retrospective`. Regression test: `lane_report` population equals the
   union of all posture step lists.
2. **`session_ids` captured at plan creation.** The `SessionStart` hook fires before a
   mid-session plan exists, so the documented "normal" append never happens for the ordinary
   `/plan-marshall task=...` flow (Step 8a gets `not_found` every time). Call the
   platform-runtime `session capture` operation explicitly once `status.json` exists
   (phase-1-init Step 3a or `manage-status create`), keep Step 8a as the verification, and
   correct the plan-marshall SKILL § Session ID Resolver prose to describe the path that runs.
3. **Scope estimate excludes provenance.** `scope-estimate-heuristic` must not count the
   ingested spec's own path (counted twice today, full and `plans/`-relative), cited inbox
   evidence files, or absolute paths into another repository as change surface. PLAN-13 was
   banded `multi_module` on 10 paths of which 3–4 were provenance, firing
   `S2:scope_estimate`. Every file-pointer plan is inflated this way.
4. **Domain detection ignores provenance tokens.** `domain-detect` returned
   `unambiguous_narrative_match` on the alias `compliance`, sourced from the epic slug in the
   spec header, and silently dropped `python` (named by `.py` surfaces and pytest tests) into
   `additional_candidates`. Header/provenance tokens must not count as narrative evidence, and
   a candidate backed by named file surfaces must not be dropped without a prompt.
5. **Named fallback that exists.** CLAUDE.md "No shell file operations" / "Structured queries
   first" and persona `agent-behavior-rules.md` Principle 4 name `Grep`/`Glob` as the
   fallback; sessions exist where neither tool is exposed and the harness itself steers to
   Bash `grep`. The rules must name the sanctioned substitute when the named tool is absent
   (e.g. `Read` with offset on an already-identified file, or a line-level
   `architecture search` mode) so no compliant path is missing.

**Folded 2026-09-29.** The PLAN-12 run corrects its own earlier report behind D2. At finalize,
`manage-status metadata --get --field session_ids` returned the session id with `resolved_from: current`,
and `manage-metrics enrich` succeeded. The id was therefore captured, but late: not at init, where Step 8a
read `not_found`. D2 stands. Re-grounding at `c56710b` found no create-time capture in Step 3a or
`cmd_create`. The fix is to capture at creation, not to add capture where none exists.

## Claim Labels

- OBSERVED: posture prose vs lanes preview mismatch and 25 vs 26 lane_report gap — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-004.md` and `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-001.md` § 5 (two independent runs)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: phase-1-init SKILL.md:952 static 'written look back' prose; manage-execution-manifest.py :1852-1871 / :1545 lane_report drop holds
- OBSERVED: `session_ids` `not_found` at Step 8a for a mid-session plan — cited at `plan-12-tool-triage-005.md` and `plan-13-finalize-mechanism-defects-001.md` § 6 (two independent runs)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: SKILL.md:818 Step 8a credits the SessionStart hook; Step 3a :251-281 and cmd_create _cmd_lifecycle.py:624-708 make no session capture
- OBSERVED: scope-estimate counted provenance paths — cited at `plan-13-finalize-mechanism-defects-001.md` § 3
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _cmd_planning_lane.py :268-279 _distinct_paths counts citations; :323-367 reads whole body incl. header
- OBSERVED: domain-detect matched the epic slug alias — cited at `plan-13-finalize-mechanism-defects-001.md` § 4
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _cmd_domain_detect.py:387-395 and _plan_parsing.py parse_document_sections :79-83 unchanged
- OBSERVED: `Grep`/`Glob` absent from the tool list while the rules name them — cited at `plan-12-tool-triage-003.md`; corroborated by the orchestrator's own 2026-09-27 drain session, which also had neither tool
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: agent-behavior-rules.md:167-186 Principle 4 names only Glob/Grep, no substitute

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/` — Step 3a/8a/8d
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — `lanes preview` / `lane_report`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py` — scope-estimate-heuristic
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py` — narrative-match reason
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/SKILL.md` — § Session ID Resolver
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/` — Principle 4 fallback
- OBSERVED: `CLAUDE.md` — hard-rule fallback wording
- OBSERVED: `marketplace/bundles/plan-marshall/agents/execution-context.md` — § Runtime tool availability for dispatched leaves already states a fallback; D5 must agree (added cleanup 2026-09-29 at 56add3f — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md` — leaf fallback statement; D5 must agree (added cleanup 2026-09-29 at 56add3f — understated surface)
- OBSERVED: `test/plan-marshall/manage-execution-manifest/` — lane_report population test
- OBSERVED: `test/plan-marshall/manage-status/` — scope-estimate provenance test
- OBSERVED: `test/plan-marshall/manage-config/` — domain-detect provenance test
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — `cmd_create` create-time session capture (deliverable 2) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/` — `session capture` entry point (deliverable 2; NOT `session_binding.py`) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` — `parse_document_sections` truncation at the first ingested `## ` (deliverable 4) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-10 (shares `phase-1-init/` — sequence, do not parallelize); PLAN-14 (parked; shares `persona-plan-marshall-agent/`)
- Adjacent to: PLAN-13 (running; touches `platform-runtime/scripts/session_binding.py` — deliverable 2 must not edit that file)

## Folded inbox material (same act)

- `plan-12-tool-triage-003.md` (finding): Grep/Glob fallback — deliverable 5
- `plan-12-tool-triage-004.md` (finding): posture prose + lane_report — deliverable 1
- `plan-12-tool-triage-005.md` (finding): session_ids at init — deliverable 2
- `plan-13-finalize-mechanism-defects-001.md` items 3, 4, 5, 6 (finding): deliverables 3, 4, 1 (recurrence), 2 (recurrence)
- `plan-12-tool-triage-025.md` item 4 (finding, 2026-09-29): deliverable 2 (premise sharpened: late capture, not none)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-16-init-lane-fidelity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
