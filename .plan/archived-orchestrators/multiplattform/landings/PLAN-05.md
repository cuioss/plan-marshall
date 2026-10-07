# Landing Analysis: PLAN-05 — Structural directive coverage

epic: multiplattform
workstream: WS-02
pr: [#1379](https://github.com/cuioss/plan-marshall/pull/1379) — merged as `30cd8aaf8442229032eb2bcb5b304283fb50072c`

> Landing record for one shipped plan. **The first landing in this epic DRAINED from the inbox rather
> than reconstructed from an operator paste** — the Step 10 channel added to the RUNBOOK worked
> end-to-end on its first run. Facts below were corroborated against the merged diff and PR state; the
> inbox message was treated as a lead, not a fact, exactly as a paste is.

## Deliverable Fidelity vs Spec

`deliverables_total=4`, `deliverables_done=4` — corroborated deliverable by deliverable against the diff:

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — `Read:` directive into `STRUCTURAL_VOCABULARY`, fail-closed | shipped-as-specified | `body_transform_engine.py` +104, `opencode/mapping.json` +4, `opencode/transforms.md` +57, with `test_body_transforms.py` +214 and `test_config_files.py` +9 |
| **D2** — `manage-maven-profiles/SKILL.md` normative tool invocation | shipped-as-specified | that file, +21/−… |
| **D3** — the seven `ext-triage-*/standards/pr-comment-disposition.md` files | shipped-as-specified | **exactly 7** such files in the diff, matching the spec's enumeration (six domain bundles plus the single `pm-plugin-development` one) |
| **D4** — §M2-named bundle files across bundles | shipped-as-specified | `pm-dev-java-cui` README + `recipe-cui-logging-enforce`, `pytest-testing/standards/testing-pytest.md`, and the `pm-documents` `ref-asciidoc` / `ref-documentation` / `ref-svg-diagrams` surfaces |

**25 files, +435/−125.** The title — *"register read_directive and name acts, not host tools"* — states the mechanism precisely: the directive becomes a registered act rather than a host-tool reference.

### The load-bearing carve-out held

PLAN-05's spec carried the epic's most explicitly-flagged partition hazard: `pm-plugin-development/skills/ext-triage-plugin/standards/pr-comment-disposition.md` belongs to PLAN-05, carved out of PLAN-06's `pm-plugin-development/**`, and ⛔ *"everything else under `pm-plugin-development/**` is PLAN-06's and must not be touched here."*

**Verified: the only file touched under `pm-plugin-development/` is that one carved-out file.** PLAN-06's surface is untouched, so the partition survives and PLAN-06 remains stageable against an unmodified tree.

## Metrics and Anomalies

- **Tokens: `unknown`** — see the landing-completeness section below. Not estimated.
- **Branch form `feature/050-structural-directive-coverage`** — the first branch in this lane to carry the `{NNN}-` prefix.
- **Reviewers:** CodeRabbit, cuioss-review-bot, and Sourcery (round-2 **Approved**) — full 3-of-3 participation, notable given the reviewer policy now makes only CodeRabbit required.
- **Contract observations recorded, not actioned:** the run surfaced a stale argparse cache and executor-pin observation; the operator chose record-only with no follow-up PR. Correct disposition — neither is this plan's surface.

## Landing Completeness — the channel worked, and reported honestly

`inbox landing-check` → **`complete: false`, `missing_keys: [total_tokens]`**. Every other required key was supplied with a real value:

```text
schema=landing-facts/1        plan_id=structural-directive-coverage    epic=multiplattform
pr=#1379                      merge_state=merged
deliverables_total=4          deliverables_done=4                      total_tokens=unknown
steps=step-4-implement:done,step-5-build-gate:done,step-6-verifier:clear,
      step-7-pr:done,step-8-merge:done,step-9-self-check:done
```

⚠️ **This is the predicted outcome, not a defect.** The required-key set is plan-marshall's, and `total_tokens` originates in its `record-metrics` finalize step, for which this lane has no analogue. The run wrote `unknown` — the could-not-read class — rather than `n/a`, which would have laundered an unread value into an asserted absence. That is precisely the false-completeness defect the two-class split exists to prevent, and the run got it right. Recorded as residue; it blocks nothing, and the merge had already landed.

**The `steps` value parses correctly under the last-colon rule** — every element here carries a single colon, so this run does not discriminate between the two split directions; a namespaced step id would. The rule was applied, not assumed.

## Reconciliation Actions

- [x] inbox message drained: `structural-directive-coverage-001.md` — enumerated, completeness-checked, reconciled, archived
- [x] row `status` → `landed`; `pr` `#1379`; `landing` `landings/PLAN-05.md`; `plan_marshall_plan_id` `n/a`
- [x] carve-out verified intact — PLAN-06's surface untouched
- [x] epic.md reconciled; both generated blocks regenerated; `resume_anchor` updated

## Follow-Ups

- ⛔ **A defect in the Step 10 instruction I wrote was found and fixed by the operator — record it, do not re-introduce it.** My Step 10 specified `--sender-id {NNN}-{plan-name}`. The write verb validates that id through `validate_plan_id`, whose pattern is `^[a-z][a-z0-9-]*$` (verified at `input_validation.py:61`), so a digit-prefixed directory name like `050-structural-directive-coverage` is **rejected outright**. The corrected rule — now at `RUNBOOK.md:735` — uses the plan's orchestrator **slug** alone, which passes the validator and maps to the `slug` field of the plan's `status.json` row, so attributability is preserved rather than traded away. **Root cause of my error:** I validated the write verb's *flags* against a live `--help` but never validated the *value shape* I was prescribing for one of them.
- ✅ **The inbox landing channel is proven end-to-end.** First run: message written, enumerated `valid`/`live`, completeness-checked, reconciled and archived. Future landings should be drained with `analyze` and no paste. ⚠️ The operator's narrative report stays valuable — the payload spec names two finding classes (a contradicted merge claim, a bot withdrawal) as irreducibly narrative, so the manual channel is a complement, not a redundancy.
- **`total_tokens` will read `unknown` on every OpenCode landing until this lane grows a token-total source.** Expect a standing `complete: false` on that one key. If that noise ever outweighs the signal, the options are to supply a real total from the session or to argue the key down from required — the latter changes a shared contract and would need its own plan.
