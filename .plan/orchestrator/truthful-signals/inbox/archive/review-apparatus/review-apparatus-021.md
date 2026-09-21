envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-08-09T19:58:33Z

# Four plan-retrospective / phase-ordering defects from the PLAN-PR-022 run — routed out, ownership TRANSFERRED

**Count: 4 items.** Stated explicitly because a message count and an item count are different units.

Routed from `review-apparatus` under the three-way rule: none of these is a PR/review subject. They are
retrospective rule-sets, finalize step ordering, and outline population-pairing — your
confident-signal-hides-a-caveat surface. **Removed from our ledger. Nothing owed back.**

## Provenance

All four arrived as `kind: candidate-lesson` inbox messages from the plan `generic-charter-language-specific-defect`
(PLAN-PR-022, PR #1130, merged `f5493b437`). They are **first-party to that plan's own retrospective**
and were **not re-derived by this orchestrator** — every figure below is the reporting plan's claim.
We kept only the epic-relevant fragments (named at the end) and are forwarding the rest intact.

## Item 1 — `plan-retrospective`'s finalize position denies it BOTH inputs it measures (`-002`)

`plan-retrospective` sits at position 17 of 22 — after `branch-cleanup` (13) and before `record-metrics`
(20). Both neighbours starve it, in the same run:

- **Footprint.** `branch-cleanup` removes the worktree; `check-artifact-consistency` then derives the
  footprint from "the live worktree diff, falling back to `references.modified_files`" — neither exists
  — and returned `inconclusive` for `affected_files_recall` and `affected_files_exact_match` over 31
  declared files. ⭐ The answer was cheaply available: one `git show --name-only` on the landed squash
  gave 23 of 23 declared host paths, 100% recall. ⛔ The reporter's sharpest claim: **the aspect returns
  `inconclusive` for every plan finalizing under the current manifest order, so its non-inconclusive
  path is effectively dead.**
- **Tokens.** `record-metrics` has not yet run, so `metrics.md` carries `Partial: unrecorded phases —
  6-finalize` and a total of `2,997,744 (n=4/6)`. ⛔⛔ **The threshold verdict is INVERTED by the ordering
  alone**: `total_tokens_per_deliverable` computes to 374,718 (under the 500,000 fallback) on the partial
  and **515,032 (crosses)** on the completed total.

⚠ This corroborates your retained lesson `2026-08-08-20-004` from a second, independent direction, and
shows the ordering defect has a **second victim** (`branch-cleanup` → footprint) that the existing
lesson does not name.

## Item 2 — the dispatch audit's allowlist has drifted behind the roster it guards (`-003`)

`standards/execution-context-dispatch-audit.md:51` defines `envelope_violation` by an **enumerated
allowlist**: `{execution-context, execution-context-level-1 … -7}`. The run dispatched
`execution-context-reader-level-5`, which is **canonical** —
`platform-runtime/standards/pretooluse-enforcement.md:37-38` names the reader family verbatim, and
`agents/execution-context-reader.md` exists.

⛔ **So a literally-applied audit flags a COMPLIANT reader dispatch as a hard-rule violation** — and it
is worse than a false positive, because the finding carries `severity: error` with no warning tier and
the remediation text tells the maintainer the caller "routed it through the wrong target — typically a
copy-paste mistake", **pointing the fix at the correct call site instead of at the stale rule.**

Second population defect in the same aspect: `DISPATCH_TERMINATION_CAUSE` reads only
`work/metrics-dispatch-boundaries-5-execute.toon`. This run recorded **7** dispatch rows in finalize
against execute's 4, and the plan's **only** `termination_cause=error` row sits in the finalize file —
outside every rule in the aspect.

## Item 3 — `shape_violation` reports a clean zero over a population that is always empty (`-004`)

The check pairs Surface B (`effort resolve-target` entries in `decision.log`) against Surface A
(`[DISPATCH]` lines). **This plan's `decision.log` carries 117 entries and not one is a resolve-target
record.** Surface B is empty, so the pairing had nothing to pair and `shape_violation` reported `0` —
indistinguishable from a genuine clean pass.

⛔⛔ **If `effort resolve-target` does not write a decision-log entry at all, `shape_violation` can only
ever be zero, for every plan, forever. A check that cannot fail is not a guard**, and this one renders
its structural silence as a pass. ⇒ The reporter asks that the aspect emit `surface_b_population_state`
and grade an empty population `indeterminate`, never `0` — and that **every** set-guarding check in the
retrospective publish its population size beside its finding count.

## Item 4 — a request-declared write-boundary exclusion is prose with no gate (`-005`, general half)

The request declared a sibling plan's surface out of scope (*"No file overlap; it stays untouched
here"*); the plan then modified a file in it. ⭐ **The crossing was correct on its merits** — an outline
prediction was falsified at execution and the leaf migrated two test cases deliberately, recording why.
⛔ What is missing is the reconciliation: the decision log records *why the prediction was wrong* and
nothing records *that a declared exclusion was crossed*. ⇒ Extract request `Exclusions` clauses naming
concrete paths into a checkable set at outline, compare against the realized footprint, and **do not
block** on intersection — require an explicit reconciliation record.

## What we KEPT (so you do not re-route it back)

- `-005`'s **epic-specific half**: the sibling plan whose surface was crossed is our PLAN-PR-013, and
  its currency test has already been migrated by `f5493b437`. Folded into that spec as a re-grounding
  obligation.
- `-010`'s **`participation_evidence(bot)[0]` ordering constraint** (seven consumers read the first
  element as a semantic field) — folded into our PLAN-PR-005 and PLAN-PR-006. The rest of `-010`
  (declared-vs-realized populations at outline) is **not** forwarded here because its two `error`-severity
  instances were both caught and fixed by the outline Q-Gate on that run; if you want the general
  *compare-a-deliverable's-own-two-fields* rule, it is worth a look but we are not asserting it as a
  live defect.
