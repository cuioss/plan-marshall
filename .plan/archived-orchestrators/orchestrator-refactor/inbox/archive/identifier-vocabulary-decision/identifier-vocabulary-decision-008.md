envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:31:03Z

component=plan-marshall:phase-2-refine
category=improvement
bundle=plan-marshall

# Orchestrator-authored staged specs systematically trip the suspicious-perfect-confidence check

Source signal: Q-Gate finding `c3cf74` (phase `2-refine`, source `qgate`, type `triage`,
resolved `taken_into_account`) on plan `identifier-vocabulary-decision` (epic
`orchestrator-refactor`, PR #1543).

All six weighted refine dimensions (correctness, completeness, consistency,
non-duplication, ambiguity, module_mapping) scored 100, which the refine Q-Gate flags
as suspicious by default. The flag was accepted rather than acted on, and the recorded
rationale is the generalizable part:

- The request was an **orchestrator-authored staged plan spec**, explicitly marked
  SELF-SUFFICIENT, with OBSERVED/HYPOTHESIS claim labeling and verify-first clauses.
- Step 3b source-premise verification independently checked 5 load-bearing OBSERVED
  claims against the live codebase and found 0 invalid.
- One HYPOTHESIS-labeled claim was *refined* (not invalidated), and a genuine
  cross-section ambiguity was found and resolved rather than silently scored down.

## Why this is a candidate rather than a one-off

The suspicious-perfect-score heuristic reads a 100% aggregate as evidence the scorer
was not discriminating. For a spec that an orchestrator already pre-verified and
labeled by claim status, 100% is the **expected** score, not a suspicious one — the
verification the heuristic wants already happened upstream, one layer out. If that
holds across the epic's other staged plans, the check fires as routine noise on every
orchestrated run, and routine noise is how a check stops being read.

The orchestrator is the right judge here because the population that decides it is
cross-plan: whether sibling plans in `orchestrator-refactor` (and in other epics that
stage specs the same way) also scored 100 and also resolved the flag as
`taken_into_account`.

## What would settle it

Derive, do not assume: count the `2-refine` Q-Gate findings with this title across the
epic's landed plans and partition by resolution. A high `taken_into_account` rate is
evidence the heuristic needs an orchestrated-spec-aware arm (e.g. reading the
`source_id` / staged-spec provenance, or the presence of Step 3b verification results,
before calling a perfect score suspicious). A mixed rate is evidence the check is doing
its job and this run was simply a clean one.

⛔ Do not read this single observation as the population — n=1 here by construction.
