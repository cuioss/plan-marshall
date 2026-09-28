envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-28T05:25:31Z

# phase-3-outline leaf self-transitions before the orchestrator's gates run

## Observed

The first phase-3-outline dispatch of plan-12-tool-triage returned `status: success` carrying an
`outline_prompt` with 3 operator questions AND `qgate_validation_required: true`, and reported that it had
already moved the plan to `4-plan`.

`plan-marshall/workflow/planning-outline.md` puts the `3-outline` transition in the ORCHESTRATOR's Step 2c,
AFTER (a) the batched `outline_prompt` operator question plus at most one re-dispatch, (b) the sibling
q-gate-validation dispatch, (c) the Step 2b auto-loop, and (d) the post-outline clean-main assertion. A leaf
that transitions itself closes the phase while every one of those gates is still open:

- the documented re-dispatch now re-enters phase-3-outline on a plan whose status says `4-plan`;
- the orchestrator's own `manage-status transition --completed 3-outline` in Step 2c becomes a no-op, the
  same half-stamped boundary shape the plan-marshall SKILL resume reconciliation exists to repair;
- a violated clean-main assertion can no longer "refuse to advance" — the status already advanced.

The phase-2-refine leaf in the same run did the same (transitioned `2-refine` and captured its handshake
itself), so the orchestrator-side transition/capture in `planning.md` duplicates leaf work there as well.

The phase-4-plan leaf did it a third time: it returned `qgate_validation_required: true` (and itself said
"the orchestrator must dispatch q-gate-validation after this return") yet reported "Phase transitioned
4-plan → 5-execute cleanly" — before the sibling q-gate, the metrics boundary, the handshake capture and the
post-plan clean-main assertion that `planning-outline.md` Step 4/4b place ahead of that transition.

Compounding observation: the same phase-4-plan leaf read the transition's `mailbox.probe: not_orchestrated`
as "expected for a standalone plan" — the false-negative probe (inbox finding plan-12-tool-triage-001,
lesson 2026-09-27-07-001) actively misinforms leaves about the plan's own epic membership, and they
rationalise it instead of flagging it.

Consequence observed: after the 4-plan q-gate the operator chose to fix both open findings and re-plan.
`planning-outline.md` offers no documented path for that once status reads `5-execute` — Step 3c's
"re-dispatch phase-3-outline, loop to 3a" presumes the plan is still in `3-outline`, and the phase-4
`until_clean` loop only re-dispatches phase-4-plan. The orchestrator had to re-dispatch phase-3-outline
against a `5-execute` status with an explicit "do not transition" instruction — improvisation the leaf
self-transition forced.

## Suggested fix

Pick one owner per phase transition. Either the leaf never transitions when it returns a
prompt-required envelope or `qgate_validation_required: true`, or the orchestrator docs drop their
transition calls and gate the leaf instead. Add a return-shape assertion: `outline_prompt` present ⇒ the
status must still read `3-outline`.
