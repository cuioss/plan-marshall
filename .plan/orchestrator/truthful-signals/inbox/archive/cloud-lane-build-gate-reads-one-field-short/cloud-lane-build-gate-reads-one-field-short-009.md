envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=finding
created=2026-08-23T22:12:42Z

# PLAN-TRUTH-075: three of four deliverables closed WITHOUT a code change — the evidence

The spec staged four deliverables. **Three closed on re-verification against HEAD**, with no edit
owed. This message is the durable record of *why*, so no later pass re-derives it.

The spec itself named D0 as the gate: *"⛔ This is the claim `review-apparatus` explicitly did NOT
establish and flagged as the discriminator."* It is now established.

## D0 — settled by CODE READ, not by a doc-text match

**The pyproject build wrapper structurally cannot emit `status: success` with a non-empty `errors[]`.**

Read `script-shared/scripts/build/_build_shared.py::cmd_run_common` and `_build_result.py`:
`errors[]` is populated at exactly one call site, reached only after `error_result(...)` has
unconditionally set `status: 'error'`. The success path never parses issues at all.

⇒ PLAN-TRUTH-075's Finding 1 is a **defence-in-depth gap, not a live false-green**. The severity
question the spec made D0 the gate for is answered: the weaker framing is correct.

## D1 — already satisfied at both cited sites

Both sites the spec cited already require `total_issues: 0` **and an empty `errors[]`** — the Step 4
per-commit gate and the Step 5 build gate. The spec's line numbers (`:278`, `:376-377`) had moved,
which is why the claim-labels flagged line numbers as the least durable part; the *content*
requirement is present at both.

Read with D0: the requirement is correct **and currently unreachable**, because the wrapper cannot
produce the combination it guards against.

## D2 — already shipped, and the chronology in the plan's own artifacts is BACKWARDS

The merge-queue / stale-base report vocabulary already exists, landed by `2cbcb1f30` (PR #1299) on
**2026-08-18** (verified with `git show -s --date=short`).

⛔ **Correction that must not be lost.** `solution_outline.md`'s "Closed on re-verification" table,
and both the phase-2-refine and phase-3-outline summaries, state that #1299 *predates this plan's
staging*. **That is false.** PLAN-TRUTH-075 was staged **2026-08-09** and executed **2026-08-23**, so
#1299 landed **nine days AFTER staging** and five days before execution.

The distinction changes the diagnosis entirely:

- *"Staging ingested a stale claim"* ⇒ a defect in the staging pipeline. **Wrong.**
- *"The spec was accurate when written, and its target was fixed by unrelated work while it waited
  14 days in the queue"* ⇒ **queue latency.** Correct.

## The epic-level implication

A staged spec must be **re-grounded against HEAD at execution start**. That is exactly what
phase-2-refine's source-premise verification did here, and it is the reason three of four
deliverables closed without an edit rather than being implemented against a phantom surface.

The cost of *not* doing it would have been three unnecessary edits to a file two other plans also
touch — including one (`PLAN-TRUTH-092`) that declares the same file in its Expected Surface.
