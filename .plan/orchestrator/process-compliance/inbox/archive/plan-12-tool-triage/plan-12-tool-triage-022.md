envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:58Z

# The finalize loop-back ceiling has no documented operator override path

**Observed (plan-12-tool-triage, finalize):** loop-back iteration 5/5 was spent on a pre-submission-self-review round; the fix it drove (9009e676d) was itself flagged by the next round (finding 41d544, a wording ambiguity authored by that fix). phase-6-finalize SKILL item 7b refused iteration 6 and STOPped with the documented "Stopped one round short … re-run finalize when you are ready to give it another round" display.

**The gap:** the display invites a re-run, but the count is persisted in `status.metadata.loop_back_iteration` precisely so a re-run does NOT reset it — a re-run hits the identical refusal. No document names what an operator who WANTS another round does: raise `phase-6-finalize.max_iterations` (a project-wide `marshal.json` knob, not plan-scoped), hand-edit the persisted counter, or something else. The operator answered "make a final round and continue"; the orchestrator logged a WARNING operator-override decision and set `loop_back_iteration=6` via `manage-status metadata --set` — an improvised path with no contract behind it.

**Also observed:** the self-review fixes of loop-back 5 re-seeded the loop exactly as § "Round-loop termination" predicts (a fix's authored prose becomes the next round's finding), and each fix commit re-fired lessons-housekeeping, simplify and plugin-doctor at full cost because none declares `verdict_inputs` (see the staged loopback-refire-cascade finding).

**Suggested fix:** give 7b's STOP display an explicit, plan-scoped, logged operator override (e.g. a `manage-status` verb granting N extra rounds with a reason), and make the display name it instead of implying a plain re-run helps.
