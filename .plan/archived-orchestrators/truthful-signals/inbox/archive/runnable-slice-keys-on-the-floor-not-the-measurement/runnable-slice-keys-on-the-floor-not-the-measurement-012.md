envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T06:10:31Z

component=phase-6-finalize
category=bug
created=2026-07-29

# An instant timeout verdict that names nothing failing is not a timeout

After the force-push, `ci_complete_precondition resolve` returned
`ci_final_status: timeout` with `wait_outcome: completed` and an EMPTY
`failing_checks[]` — twice, at 05:23:48Z (0.72s) and 05:24:15Z (0.75s), against
a 540s wait budget. The same script consumed a genuine 561.23s budget earlier in
the run (22:23:36Z), so the sub-second path is not how the verb normally behaves.
Direct `ci checks status` polling showed checks progressing normally throughout,
and a separate Monitor later confirmed the rebased HEAD reached
`CI_TERMINAL: success failing=[]`.

A verdict of `timeout` delivered in under a second, reporting nothing failing, is
untruthful in the strongest available sense: it asserts budget exhaustion that
demonstrably did not occur. A consumer trusting it is stranded — it cannot retry
(the budget is nominally spent), cannot fix (nothing is named failing), and
cannot proceed (the status is not success).

## Impact

A wait-with-budget verb must not be able to return its exhaustion verdict without
having consumed the budget. Three separable rules: (1) `timeout` requires elapsed
time within tolerance of the budget, otherwise the outcome is a different state
(`not_started`, `no_checks_registered`, `unknown`); (2) `wait_outcome: completed`
paired with a non-success `ci_final_status` and an empty `failing_checks[]` is a
self-contradictory tuple that should be rejected at emit time, not at read time;
(3) the fast path here correlates with a freshly force-pushed HEAD whose check
runs were not yet registered — "no checks exist yet" must be its own state, never
collapsed into `timeout`.
