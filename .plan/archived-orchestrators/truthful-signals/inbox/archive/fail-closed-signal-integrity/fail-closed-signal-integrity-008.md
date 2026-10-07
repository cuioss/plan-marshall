envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T21:11:32Z

component=plan-marshall:phase-3-outline
category=improvement
bundle=plan-marshall

# A refuted request arm is a RESULT — verify each arm's premise before building its deliverable

Three of this plan's request arms were refuted on contact, and in each case the refutation
was cheap to establish and would have been cheaper still at outline time:

| Arm | Premise as written | Ground truth |
|-----|--------------------|--------------|
| D4 — leaf record-before-return invariant | Missing, needs authoring | **Already landed** in `agents.md`. The request arm was stale. |
| D4b — fail-closed on unmappable paths, example `.claude/skills/**` | The named example is fail-open | The **example** was already fail-closed. The **class** was real and was confirmed at three OTHER shapes. |
| Launch-abort pin | Launch abort is fail-open | Already fail-closed — a negative returncode already maps to `killed`. Reduced to a stub-binary pin. |

The failure mode is not "the request was wrong". It is that a request arm's premise was
carried into implementation as a given, and the plan's shape (one deliverable per arm) made
a refuted arm look like a gap in delivery rather than a finding.

Note the second row especially: **a wrong example does not refute the class.** Dropping D4b
because its literal example was already fail-closed would have discarded a real, live defect
class present at three other shapes.

## Impact

Refuted arms consumed real budget and, worse, risk being re-queued by the epic as
"unfinished" unless the refutation is recorded as an outcome. Recording them as results is
what stops the same arm from being staged again.

## Solution

- At outline time, verify the PREMISE of each arm against ground truth before sizing its
  deliverable. An arm whose premise is already satisfied is closed at outline, not carried
  into execution.
- When an arm's premise is refuted at its literal example, re-test the CLASS at other shapes
  before closing it — example-level refutation is not class-level refutation.
- Report refuted arms explicitly in the landing as results with their evidence, never as
  silently-absent deliverables.
