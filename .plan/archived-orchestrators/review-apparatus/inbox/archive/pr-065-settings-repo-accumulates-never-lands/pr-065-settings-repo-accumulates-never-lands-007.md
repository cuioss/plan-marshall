envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:21:41Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR 20264d (2026-09-13T22:01:10Z, 2026-09-14T19:00:58Z), cffb9b (22:01:17Z), 4256cb (22:01:24Z, 2026-09-14T06:10:10Z)

# The same invented verb was re-invented three times, hours apart, after the executor printed the registered set

Five argparse rejections against
`plan-marshall:manage-solution-outline:manage-solution-outline` in one run:

- `extract-deliverables` — an invented verb naming the GOAL. The executor answered
  with the registered set: `['exists', 'get-deliverable', 'get-field',
  'get-module-context', 'list-deliverables', 'read', 'resolve-path', 'update',
  'validate', 'write']`, and named `list-deliverables` as the canonical form.
  Re-invented at 2026-09-13T22:01 and again at 2026-09-14T19:00 — 21 hours and
  many envelopes apart.
- `get-deliverable` invoked with a flag outside its declared set
  `['deliverable-number', 'plan-id']`. Twice (22:01, 06:10).

## Why it matters to this epic

This is the verb-paraphrase signature (signature 1 in agent-behavior-rules), and
it recurred *after* a correction had already been printed into the run's own work
log. The correction is per-envelope and evaporates at the envelope boundary; the
next envelope re-derives the verb name from workflow prose and lands on the same
wrong word. The strength of the signal here is the interval: 21 hours and a
different phase, same invented token.

## Candidate rule

Where a workflow body instructs an agent to "extract the deliverables", name the
canonical verb inline in that same sentence. A goal-phrased instruction adjacent
to a verb-named script is the generator of this failure, and it recurs until the
instruction carries the verb.
