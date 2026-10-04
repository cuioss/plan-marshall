# PLAN-PRQ-14: The findings producers do not say which gate caught it, and Sonar's severity is thrown away at the door

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

The D4a hand-back from `PLAN-PRQ-13`, which landed in `cuioss/plan-marshall-telemetry` on 2026-10-04
(commit `5546bde`). That plan built the four-axis quality ontology and the per-subject quality report, and
D4a was its explicit non-goal: classification happens on the READING side, and anything the **producers**
must change is handed back to this repository rather than reached across for. See
`landings/PLAN-PRQ-13.md`.

⭐ **The hand-back is evidence, not a wish list.** Each item below was found by running the new reports
against the real archived corpus and observing a field that could not be populated. The reports are already
built and already degrade honestly — this plan is what turns several `not_measured` fields into measured
ones for plans that run *after* it.

## Objective

**Three facts the quality ontology needs are not recorded by the producers that own them, so the reports
degrade to `not_measured` for every plan — correctly, and permanently until this lands.** Two mechanisms
file findings that carry no marker saying which gate caught them, and the third throws away the severity it
was given before it writes the record.

⛔ **The Sonar item is the one with a deadline, because it is lossy rather than merely absent.** Items 1
and 2 omit a marker that could in principle be back-derived; item 3 **destroys information at ingestion**,
so every day this does not land is another day of findings whose `critical`-versus-`major` distinction can
never be recovered for any corpus query.

## Deliverables

Five deliverables. D0 is a gate. D1–D3 are the required set; D4 and D5 are recommended by the hand-back and
are smaller.

**D0 — GATE: establish where each producer writes, and what the reading side already expects.** Read the
three producer call paths and `plan-marshall-telemetry`'s `scripts/ontology.py` — the consumer — and
publish, as a table, the field each item below will write and the field name the consumer already reads. ⛔
**The consumer is already built and its vocabulary is fixed**, so a producer writing a differently-named or
differently-valued field satisfies nothing. This gate exists because the two sides are in different
repositories and nothing mechanically joins them.

**D1 — `finalize-step-simplify` files its findings with a mechanism marker.** `OBSERVED` via the
hand-back: it files **none** today. A `simplify` mechanism exists in the ontology and can never be
populated. Give the step's findings a marker such as `source: finalize-step-simplify`, in whatever form D0
establishes the consumer reads.

**D2 — the security-audit findings carry the same marker.** `OBSERVED` via the hand-back: they are stored
as plain `bug` / `anti-pattern` records today, indistinguishable from any other producer's. A
`security-review` mechanism exists in the ontology and can never be populated.

**D3 — Sonar's original severity is preserved in an `upstream_severity` field.** ⛔ **The lossy one.**
`OBSERVED` by direct code read: `workflow-integration-sonar`'s `_map_severity` collapses `BLOCKER`,
`CRITICAL` and `MAJOR` **all into `error`**; `MINOR` → `warning`; `INFO` → `info`; an unknown severity is
written with no severity field at all. Keep the pre-collapse value alongside the mapped one.

⚠ **Do NOT widen `FINDING_SEVERITIES` to fix this.** The store's three-value vocabulary is consumed
throughout the tree; the fix is an additional field carrying provenance, not a vocabulary change with a
tree-wide blast radius. D0 confirms that reading.

⛔ **State plainly what this does NOT do**: it fixes findings filed from the day it lands. **Every
already-archived plan stays `not_measured` forever** — the information is gone, not merely unread. No
deliverable here may claim otherwise, and no back-fill is attempted from the mapped value, because
`error` → `major` would be a fabrication.

**D4 — RECOMMENDED: stop writing totals as `0` when nothing was counted.** The hand-back's own words. This
is the honest-zero rule applied to the finding producers themselves — the same defect `PLAN-PRQ-13`'s
self-review found and fixed on the reading side (`totals_tokens: 0` published as measured). ⚠ Scope this at
D0 against the actual producers rather than assuming it is one call site.

**D5 — RECOMMENDED: compute the per-deliverable fingerprints in a script.** `OBSERVED` via the hand-back:
only *"no change"* can currently be proven, and only for **39 of the 55** plans that have fingerprints. A
script-computed fingerprint makes post-planning changes to the deliverable list measurable — which is what
the ontology's **scope-stability axis** (`specification_changes`) needs to move off `not_measured`. ⚠ The
39/55 figure is the hand-back's; D0 re-derives it rather than restating it.

## Claim Labels

- ⛔ OBSERVED: `workflow-integration-sonar`'s `_map_severity` maps `BLOCKER` / `CRITICAL` / `MAJOR` → `error`, `MINOR` → `warning`, `INFO` → `info`, and an unknown severity to no field — read directly at `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py`.
- OBSERVED: `FINDING_SEVERITIES` is `('error', 'warning', 'info')` in `tools-file-ops/scripts/constants.py`, aliased as `SEVERITIES` in `manage-findings/scripts/_findings_core.py`.
- OBSERVED: the consuming ontology exists and is already landed — `plan-marshall-telemetry` commit `5546bde`, `scripts/ontology.py`, eight mechanisms with bot identity as a field.
- ⚠ HYPOTHESIS: `finalize-step-simplify` files no findings at all today, rather than filing them untagged — reported by the hand-back and NOT independently verified here. Confirm/refute at `phase-6-finalize`'s simplify step and its findings calls; the two cases need different fixes, since an untagged filing needs a marker and a non-filing needs a filing path (verify-at-outline, D0 owns it).
- ⚠ HYPOTHESIS: the security-audit findings are filed as plain `bug` / `anti-pattern` with no producer marker — same provenance, same caveat; confirm at `finalize-step-security-audit`'s findings calls (verify-at-outline, D0 owns it).
- ⚠ HYPOTHESIS: the `39 of 55` fingerprint figure. It is the hand-back's count over the archived corpus and is not re-derived here (verify-at-outline, D5).
- ⚠ HYPOTHESIS: an additional `upstream_severity` field is additive for every current consumer of a finding record — confirm by enumerating the readers before writing it (verify-at-outline, D0).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py` — D3 (the `_map_severity` call site)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/` — D0, D3, D4 (the record writer and its field set)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — D1, D2 (the simplify and security-audit steps' findings calls)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — D3, ONLY if D0 shows the new field needs a declared vocabulary there rather than being free-form (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/` — D5, only if the fingerprint producer lives there (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-findings/` — D0's and D3's controls
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — D1's and D2's controls

## Dependencies and Sequencing

- **Depends on: `PLAN-PRQ-13` — SATISFIED.** It landed 2026-10-04 and built the consumer this plan feeds.
- ⛔ **The consumer is in ANOTHER REPOSITORY and nothing joins the two mechanically.** A field renamed here
  silently breaks `plan-marshall-telemetry`'s `ontology.py`, and no gate in either repo will say so. D0
  reads the consumer first for exactly this reason, and the landing report names the field it wrote.
- ⚠ **Overlaps `manage-findings` with many staged specs across sibling ledgers** — `review-apparatus`
  (`PLAN-PR-072` and others), `truthful-signals` (`PLAN-TRUTH-146`, `-178`) and this epic's own `parked`
  `PLAN-PRQ-01`. `PLAN-TRUTH-146` is the findings-ledger-vocabulary plan and is **`parked`**, so the
  vocabulary work it owned will not land there; this plan deliberately does **not** pick it up — it adds
  one provenance field and changes no vocabulary. Re-check the live plan set at outline.
- **Does not block anything.** The reports already degrade honestly without it; this plan only moves fields
  from `not_measured` to measured for future plans.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-14-findings-producers-tag-their-mechanism-and-keep-upstream-severity.md"
```

## Write-Boundary

The plan implementing this spec touches only this repository's own source and tests. ⛔ It does **not** edit
`plan-marshall-telemetry` — that repo's ontology is the consumer and is already landed; if a field name
must change, the plan reports it and the orchestrator stages the consumer-side follow-up. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message, and reports its
outcome through its PR and that message. See
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
