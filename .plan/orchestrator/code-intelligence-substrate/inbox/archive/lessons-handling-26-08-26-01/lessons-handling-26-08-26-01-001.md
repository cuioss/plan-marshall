envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=code-intelligence-substrate
kind=finding
created=2026-08-26T21:14:05Z

# The run's own measurement is unrecoverable — seven mechanisms

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule: these are measurement-substrate lessons, and measurement is this
epic's blocking dependency.

**Cluster:** 7 lessons. **Suggested fold target:** yours to decide — `PLAN-CIS-013` /
`-014` / `-022` held the cost-measurement surface at the last drain.

## Why this routes here rather than to `truthful-signals`

Every member is a reason the **cost of a run cannot be measured**, not a reason a signal
lies. The token-reduction roadmap is blocked on measurement it cannot currently take, and
these seven are the named mechanisms.

## The headline

⛔ **`2026-08-26-05-002`: a run cost 3,547,890 dispatched tokens and left NO cost figure at
all.** Both independent measurement paths were empty:

- **Per-dispatch.** All 11 dispatch-boundary rows carry `unmeasured` in all four
  context-load columns (`input`, `output`, `cache_read`, `cache_creation`).
  `measured_rows: 0` of `total_rows: 11`. The mechanism worked exactly as designed — it
  reported honestly that nothing was measured. **What is absent is any call site that
  supplies the values.**
- **Per-phase.** `manage-metrics enrich` never ran; `totals_billing_weighted_total: 0` with
  `population_count: 0`, and `metrics.md` renders `-` in `Billing (cost)` for all six phases.

⭐ The lesson names the consequence for this epic directly: *"the plan contributes zero rows
to the per-dispatch context-load corpus — the substrate for any position-cost or
context-growth analysis."* ⚠ And it restates the caveat that matters most here: since
`cache_read` is typically the large majority of billing weight, **the dispatched-token figure
is not a proxy for cost** — it answers a different question.

## The other six

| Lesson | Mechanism |
|--------|-----------|
| `2026-08-25-09-007` | **Six ledgers, no two agreeing, none reaching the truth.** `pre-submission-self-review` fired 7 times; the ledgers say 2, 2, 5, 5, 6, and 5-aggregated-into-2. The **only** artefact stating the true count is free text. The token consequence is measurable: accumulator 3,072,074 over 15 samples vs boundary ledger and execution_log both 2,808,583 over 14 — a **263,491-token gap that is one entire dispatched step**, discoverable only by summing 14 rows by hand. |
| `2026-08-25-09-006` | `record-dispatch-boundary` stamps `now()` and declares no `--terminated-at` and no backfill marker. **A truthful reconstruction is not expressible in the schema**, and the reconstruction that IS expressible silently corrupts the one field every correlator keys on. Four rows describing dispatches that ended between 19:47 and 22:09 carry timestamps spanning 5 seconds. |
| `2026-08-25-09-005` | The finalize **retry path** re-dispatches a `failed` step without re-entering the `effort resolve-target` seam the `[DISPATCH]` emission rides. Rounds 3-7 — five envelopes, ~1.2M tokens — left **no dispatch evidence whatsoever**. ⛔ And the audit built to catch it pairs a *resolve* against a *dispatch*, so with neither record present the pairing finds nothing unmatched. |
| `2026-08-25-09-010` | `manage-findings qgate add` **already declares `--iteration N`**; the self-review workflow never passes it. 15 findings, none carrying an iteration, five timestamp clusters for seven rounds — rounds 3, 4 and 6 cannot be separated at all. ⭐ This is free: the parameter exists and the round number is in hand at the call site. The payoff is a **stopping rule that can be evaluated instead of argued**. |
| `2026-08-08-20-004` | `record-metrics` is ordered **after** `plan-retrospective`, so the efficiency aspect reads a `metrics.md` carrying a literal `Partial: unrecorded phases — 6-finalize` banner. Structurally blind to a phase it can never see, on every plan, by construction. On the observed run the missing phase was the **largest**: reconstructing it gives 1,965,501 tokens against a published total of 3,339,873 — the true figure is **~1.66x the published one**, and that is still a lower bound. |
| `2026-08-25-09-014` | `compile-report` auto-deletes the fragment bundle on `status: success` — but `success` is also the status returned when sections did not render for a reason the caller is **told to investigate**. Acting on its own warning cost **nineteen tool calls** to add one fragment. |

## The convergent rule

Every member is one instance of: **a per-firing ledger that does not publish its
denominator is a floor, and nothing says so.** `2026-08-25-09-007` states the remedy
directly — a reconciliation verb reporting accumulator samples vs boundary rows vs
execution_log rows vs `firing_count`, with an explicit `unreconciled` verdict, and
`metrics.md` carrying that verdict rather than only the accumulator figure.

⚠ **Three of the seven are ordering defects**, and `2026-08-25-09-014` notes it: *"the
retrospective is scheduled after three producers whose output it needs."* If you fold these,
the ordering sub-set may be one cheap change rather than three.

## Claim labels

- **OBSERVED** — every figure above is a filing plan's own measurement of its own run,
  quoted from the lesson body: the 11 unmeasured rows, the six disagreeing ledgers, the
  263,491-token gap, the 1.66x understatement, the nineteen-call rebuild.
- **HYPOTHESIS** — that populating the four context-load columns at the dispatcher is
  sufficient to make the per-dispatch corpus usable. The lesson proposes it (*"the dispatcher
  already parses the returned `<usage>` envelope … forward it"*) and it has not been built.
  Confirm/refute at the dispatch site that parses the `<usage>` envelope. Verify-at-outline.
- **HYPOTHESIS** — that the three ordering defects share one fix. This router's inference
  from their co-location, not a lesson's claim. Confirm/refute at
  `phase-6-finalize` § the `phase_6.steps` order band. Verify-at-outline.

⛔ Figures are the filing plans' own and were NOT re-derived here.
