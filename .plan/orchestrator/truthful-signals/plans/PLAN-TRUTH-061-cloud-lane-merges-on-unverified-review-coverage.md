# PLAN-TRUTH-061: The Cloud Lane Merges on Unverified Review Coverage

epic: truthful-signals
workstream: WS-01

> Staged plan spec — the SOURCE RECORD for the cloud plan
> `doc/plans/truthful-signals/010-cloud-lane-merges-on-unverified-review-coverage.md`.
> The shared slug (`cloud-lane-merges-on-unverified-review-coverage`) is the entire mapping
> between the two, per `doc/plans/cloud-bridge.md` § Path 1 — strip the `010-` prefix and this
> spec's id resolves. Nothing else records the pairing, deliberately.
>
> ⛔ **AUTHORED OUT OF ORDER, 2026-08-08.** The cloud plan was written FIRST and this spec was
> back-filled after the run had already started. Path 1 requires the reverse. See § Provenance
> for what that cost and why the filename was NOT changed to match.

## Objective

The cloud lane's merge gate asks whether every PR comment was *handled*; it never asks whether a
reviewer *looked*. With no comments the condition is vacuously satisfied, so a PR that received no
review reads green. Make reviewer participation an explicit, per-reviewer, body-derived verdict, and
make a coverage shortfall an operator-visible disclosure at the merge gate. Resolve the contract's
own conflict between the push-after-every-commit durability rule and review/CI integrity, and make a
cloud run report its cost so the token corpus stops silently excluding the whole lane.

## Deliverables

Five, as authored in the cloud plan (D0 population + vacuity proof, D1 per-reviewer participation
record, D2 shortfall disclosure at the merge gate, D3 push-cadence resolution, D4 run-cost line).
The cloud plan carries the full "done when" conditions; they are not duplicated here — that file is
the executing artifact and this spec is the ledger's record of it.

⭐ **Split-guard verdict, made at staging per C1:** five deliverables, under the ~6 presumption, no
split. D0 is a gate that can STOP the plan (if the reviewer population is not derivable from
configuration, the run halts rather than shipping a hand-maintained list — the vacuous-guard
archetype this epic exists to close).

## Claim Labels

Carried across from the cloud plan unchanged — a premise does not become established by being
copied (Path 1 item 3).

- OBSERVED: the merge gate's three conditions test handled-ness, never participation — read at
  `.claude/skills/cloud-plan-lane/SKILL.md` § Step 8.
- OBSERVED: Step 7 item 2 already states "a green check is not evidence that a reviewer
  participated" — so D1/D2 extend an existing principle rather than introduce one.
- OBSERVED: the lane mandates a push after every commit — § Step 2 "The remote is the only durable
  storage" and § Step 4 "Commit and push".
- OBSERVED: on #1107 coverage was 1 of 3 — `cuioss-review-bot` reviewed, `coderabbitai` and
  `sourcery-ai` were both rate-limited. Read from the STORED COMMENT BODIES via
  `ci pr comments --pr-number 1107`, not from a check state or a summary.
- OBSERVED: the #1107 run report omits `sourcery-ai` entirely.
- OBSERVED (asserted absence, verified as an absence): the lane persists no metrics and its report
  template has no cost line — enumerated every section of the § Report template.
- HYPOTHESIS: the expected reviewer set is derivable from configuration rather than a hand-kept
  list — confirm/refute at `.coderabbit.yaml` / the review-bot workflow registration (D0,
  verify-at-outline). ⛔ Refutation STOPS the plan; it does not license a hand-maintained list.
- HYPOTHESIS: a cloud run's token figure can be made comparable to a `metrics.toon` total —
  settled by D4; if not, the report states the incomparability rather than implying parity.

## Expected Surface

- OBSERVED: `.claude/skills/cloud-plan-lane/SKILL.md` — Steps 2/4, 7, 8, and the § Report template.
- OBSERVED: `doc/plans/cloud-bridge.md` — § Path 3 Collect step 5.
- HYPOTHESIS: a reviewer-registration config file (D0 settles which).

**Disjointness:** the `cloud-plan-lane` project skill and the bridge doc. Disjoint from every plan
currently running — `PLAN-TRUTH-044` (`manage-lessons` + `manage-status`), `PLAN-TRUTH-060`
(`manage-build-server`), `PLAN-TRUTH-042` (`pm-dev-java`), `PLAN-TRUTH-011` (`manage-logging` +
`manage-providers`) — and from emitted `056` / `057` / `058`.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none currently in flight.
- Adjacent to: the `ci pr create` plan-less-PR gap (no `--plan-id`-free form, no `--description`),
  hit while collecting CIS-021 and recorded as an Open Defect lead. Same *family* — machinery that
  assumes a plan behind every PR — but a different surface (`tools-integration-ci`, not the cloud
  lane). Deliberately NOT folded here.

## Provenance — why this spec is back-filled

The cloud plan was authored directly at the operator's request ("a fix + learnings I can run
directly"), without first creating this spec or a queue row. Path 1 requires the orchestrator spec
to come first, with the cloud plan derived from it. The consequences, recorded rather than
smoothed over:

- For the interval between authoring and this back-fill, the work was **invisible to the ledger**:
  no queue row, so it consumed no slot, appeared in no `R` count, and would not have been seen by a
  `next`-verb disjointness check against any plan emitted in that window.
- Path 3 § Collect step 4 transitions "the orchestrator plan" to `shipped` at ingest. With no row,
  that step would have had nothing to transition and the landing would have been unrecordable
  through the sanctioned verb.

⛔ **The cloud plan's filename was deliberately NOT changed** to fix the ordering. It is already out
with a cloud session, and Path 1's fixed-once-handed-over rule is explicit: that session is bound to
its file path, so a rename mid-run breaks it. This spec instead adopts the cloud plan's existing
slug, which restores the mapping in both directions without touching the file that is in use.

## Hand-Off Command

⛔ **Not applicable — this plan does NOT run in the plan-marshall lifecycle.** It is executing in the
cloud lane from its own file. Do not emit a `/plan-marshall` command for it; doing so would start a
second, competing run against the same surface.

```text
Execute doc/plans/truthful-signals/010-cloud-lane-merges-on-unverified-review-coverage.md
```

## Write-Boundary

The cloud run writes only its own `doc/plans/truthful-signals/010-…/` directory and the repository
source its deliverables name. It creates and edits NO file under `.plan/local/orchestrator/` — the
lane cannot see that tree at all (it is git-ignored), which is why the landing is collected locally
by the orchestrator per `cloud-bridge.md` § Path 3.
