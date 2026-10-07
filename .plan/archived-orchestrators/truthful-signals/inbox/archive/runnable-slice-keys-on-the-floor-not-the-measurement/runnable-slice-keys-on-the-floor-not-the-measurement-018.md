envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T06:12:48Z

component=finalize-step-plugin-doctor
category=anti-pattern
created=2026-07-29

# A step's structural caveat stayed in the work log and never reached its outcome

`project:finalize-step-plugin-doctor` recorded
`outcome: done`, `display_detail: "plugin-doctor clean: 7 skills gated"`.

Its own work log, one minute earlier, carries a WARNING that says the check was
structurally incapable of seeing a whole class of defect:

> scoped plugin-doctor cannot detect cross-skill divergence. Scoped mode gated
> skill-local rules over 7 skill dirs only, and cross-skill rules whose
> counterpart lives outside the scoped paths were NOT evaluated. A cross-skill
> invariant broken by this change would surface first at whole-tree CI (#915
> class).

The step knew its own coverage was partial, said so precisely, and then published
an unqualified "clean". Everything downstream that reads step outcomes rather
than work logs — the finalize gate, the PR body, this retrospective's own
step-level view, a human skimming `status.json` — sees a clean verdict with the
scope qualifier stripped off.

This is the epic's theme at its most ordinary: no component malfunctioned, no
error was swallowed. The caveat was simply written to a channel nobody reads at
decision time while the confident half went to the channel everybody reads.

## Impact

When a check runs in a reduced-scope mode, the scope qualifier belongs IN the
outcome, not merely in the log — e.g. `"clean (scoped: 7 skills, cross-skill
rules not evaluated)"` rather than `"clean: 7 skills gated"`. General rule: if a
step emits a WARNING about its own coverage, that warning must be reflected in
the step's `display_detail`/outcome, because a caveat that does not travel with
the verdict does not exist for any consumer of the verdict.
