envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=candidate-lesson
created=2026-09-19T14:27:40Z

title=Owed hint: suppress stale CI-timeout findings once the terminal verdict is green
component=plan-marshall:phase-6-finalize
category=improvement

Owed `architecture enrich` call (filed post-merge, do not run enrich here):

- target: --module plan-marshall
- verb: best-practice
- hint: "prefer to suppress [ci_timeout] findings in plan-marshall finalize runs because a wait-deadline timeout is a wait artifact, not a defect verdict — re-read the terminal CI state and suppress when green"

Evidence: plan phase-gates suppressed 2 identical [ci_timeout] findings (64c43e, 623d73) after the terminal precondition showed verify green; recurrence 2/2 cleared preference_min_recurrence=2.
