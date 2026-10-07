envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=process-compliance
kind=finding
created=2026-09-23T07:18:06Z

# Process-compliance finding — post-init contract assertion overbroad (truth-147-lane-reports-green)

## Observation

- `git -C . status --porcelain` at the 1-init → 2-refine boundary reports one untracked path:
  `?? .plan/orchestrator/process-compliance/inbox/truth-147-lane-reports-green-001.md`
- That file is the sanctioned `orchestrator inbox write` filing from this same run (process-compliance finding 001), written through `plan-marshall:plan-orchestrator:orchestrator inbox write` per operator instruction.
- Phase-1-init itself wrote only `.plan/local/plans/truth-147-lane-reports-green/**` (via manage-* scripts) plus one ignored staging file under `.plan/temp/` (allowed temp surface). No `Edit`/`Write` against repository source or the main checkout occurred in any phase-1-init step.

## Defect

- `plan-marshall/workflow/planning.md` Action init → Post-dispatch contract assertion treats ANY non-empty porcelain as a refine-block violation (`refine_contract_violation` shape).
- The predicate cannot distinguish phase-1-init drift (prohibited) from sanctioned orchestrator-tree writes performed via scripts in the same session (inbox findings, ledger writes).
- Applied literally here, the assertion would refuse a clean init because the run filed its own compliance finding — a false RED manufactured by the compliance obligation itself.

## Resolution applied this run

- Verified the sole dirty path is the sanctioned inbox file (named above); verified no phase-1-init step edited repository source.
- Advancing to phase-2-refine with this rationale recorded; no `refine_contract_violation` emitted.
- Request: narrow the assertion to repository source + tracked non-orchestrator paths, or explicitly exempt script-mediated `.plan/orchestrator/**/inbox/**` writes.
