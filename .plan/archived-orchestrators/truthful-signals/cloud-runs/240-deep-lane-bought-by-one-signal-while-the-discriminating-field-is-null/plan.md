> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The deep lane is bought by one fired signal while the field that would have refuted it is null

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

The planning-lane router selected `planning_lane=deep` for a plan whose realized footprint was **9
files, +2,083 / −16**. The recorded decision was:

```text
Routed planning_lane=deep (predicate=signal_set, fired=['S7:risk_prose'], ceremony.deep_lane=auto,
  execution_profile=standard,
  signals={'plan_source': None, 'scope_estimate': 'single_module', 'change_type': None,
           'compatibility': None, 'request_concrete': True, 'risk_prose': True,
           'planning_lane_override': None})
```

## ⭐ The root cause is sharper than "the sensor read rhetoric as risk"

⛔ **`plan_source: None`.** That plan **was** launched from an orchestrator plan spec — which is exactly
what `plan_source` exists to record, and a detection verb already classifies that pointer. **The one
field that identifies orchestrator-spec provenance, and could therefore have discounted the prose
signal, was null.**

And it is not alone: **three of the seven signals are `None`**. The predicate is `signal_set` — deep if
**any** member fires — so:

> **deep was bought on 1 fired signal out of 4 that resolved at all, against a `scope_estimate` of
> `single_module` pointing the other way.**

⇒ ⛔ **Tuning the prose sensor is the WRONG fix and would leave the defect in place.** A `signal_set`
predicate over a mostly-null signal vector is **structurally biased toward firing**: every unresolved
field is a field that cannot vote against.

## ⛔⛔ Self-implicating: the authoring style of these very specs is the trigger

The prose-risk signal fired on a body that is an **orchestrator plan spec**, in which ⛔ / ⚠ / ⭐ markup
is a deliberate house convention for marking hard-won constraints — **including in this document you are
reading now.**

⇒ **Every plan this epic emits ingests such a spec.** The misfire is **structural, not occasional**.
⭐ **The sensor is measuring the author, not the change.**

⚠ **The tempting cheap fix — "write plainer specs" — is REJECTED.** The markup carries the anti-rework
record that keeps plans from re-deriving settled constraints; degrading it to placate a sensor trades a
real good for a measurement artifact. **The sensor must learn provenance.**

## Goal

The lane decision reports how much of its signal vector actually resolved, a prose-only signal cannot
carry the lane against a resolved contradicting signal, and an orchestrator-launched plan is identifiable
as one.

## Deliverables

1. **D0 — GATE: derive why `plan_source` is null for an orchestrator-launched plan.** Mutates nothing.
   The pointer exists in the request's `source_id`, and a detection verb already classifies it. **Find
   the break: never populated, populated too late for the route, or populated under a different key.**
   *Done when:* the break is located by symbol and named.
   ⛔ **Answer this before touching any sensor.** If the field simply arrives **late**, the fix is
   **ordering, not scoring** — and a scoring change would then be both unnecessary and wrong.
   ⛔ **Also derive whether `plan_source` is null for EVERY orchestrator-launched plan.** The known
   instance is **n=1**. ⭐ If it generalises, the blast radius is every plan this epic has emitted — which
   changes the priority, not merely the description.
2. **D1 — Make an unresolved signal visible in the decision.** Today the record reads as a positive
   finding; it is equally a report that **three inputs were unknown**.
   *Done when:* the route record states resolved-versus-null counts, so **a 1-of-4 decision cannot look
   like a 1-of-7 one**.
   ⭐ This deliverable stands on its own even if D0 refutes everything else: an unreadable confidence
   level is the epic's theme exactly.
3. **D2 — Require corroboration for prose-only routing.** The prose signal must not carry the lane alone
   when it **contradicts a resolved scope estimate**, or when the body is a spec-pointer ingestion.
   *Done when:* the chosen rule is implemented **and the rejected alternative is recorded**.
   ⛔ **Decide between corroboration and provenance-exemption, and record which was rejected and why.**
   They are **not the same fix**, and D0's answer should drive the choice.
   ⚠ **Verify-first:** this assumes the prose signal fires on **markup** rather than on semantic content.
   **Confirm by reading the sensor's implementing source** — if it scores semantics, exempting
   spec-pointer bodies is the wrong lever entirely.
4. **D3 — Tests, each verified to FAIL pre-fix.**
   - (a) Replay this exact signal vector → **not** `deep`.
   - (b) An orchestrator-spec-sourced request resolves `plan_source` **non-null**.
   - (c) A signal vector with several nulls is reported as **low-confidence**.
   - (d) ⛔ **A CONTROL assertion: a genuinely deep-warranting vector still routes `deep`.**
   *Done when:* all four pass, each seen red first.
   ⛔ **(d) is not optional. A fix that only ever de-escalates is a different defect**, and every other
   test here would pass on a router that always answers `light`.

Four deliverables, under the split presumption.

## Out of scope

- ⛔ **Changing how orchestrator specs are written to placate the sensor.** See above — explicitly
  rejected. The markup is load-bearing.
- **Retuning the prose sensor's thresholds.** ⛔ **The wrong fix**, and the reason this plan exists. The
  defect is a predicate over a mostly-null vector, not a badly-calibrated sensor.
- **A context helper that can never succeed at the outline phase for worktree-using plans.** ⚠ This was
  folded into the source spec as a **WEAK merge, labelled as such**: it shares a *phase*, not a
  *mechanism*. ⛔ **It is excluded here** to keep this plan's blast radius honest. It is a single-site,
  falsifiable claim (*"can never succeed"*, not *"sometimes fails"*) and deserves its own plan rather
  than a ride on this one — **record it in the report as owed work** so it does not rot as an unowned
  lead.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-status/**` — the planning-lane route, the
  `signal_set` predicate, and the prose-risk sensor.
- `marketplace/bundles/plan-marshall/skills/phase-1-init/**` — where `plan_source` should be populated
  from the request's `source_id`.
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/**` — the detection verb, **if D0
  finds the classifier is the seam**.
- Tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The route entry is as quoted, with all seven signal values | OBSERVED | ⛔ the archived decision log — **under `.plan/`, not reachable from this clone.** The vector is transcribed above **so D3(a) can replay it without needing that file** |
| The scope estimate resolved to `single_module` seconds before the route | OBSERVED | same source, same caveat |
| The realized footprint was 9 files, +2,083 / −16 | OBSERVED | the squash commit — **this one IS reachable via git**; verify it |
| The markup convention is used in this epic's own specs | OBSERVED | **this file** — it is its own evidence |
| The prose signal fires on markup rather than on semantics | HYPOTHESIS | the sensor's implementing source — ⛔ **read it before choosing D2's lever**; if it scores semantics, the provenance exemption is the wrong fix |
| `plan_source` is null for **every** orchestrator-launched plan | HYPOTHESIS | ⛔ **n=1. Derive it at D0** over whatever corpus is reachable. If confirmed, re-prioritise |
| The deep lane cost ~1.2M dispatched tokens (29% of the plan's spend) | HYPOTHESIS | ⚠ **REPORTED, NOT VERIFIED.** It is **not re-derivable** from the artifacts the related measurement work cites, and depends on a per-step attribution that does not exist. ⛔ **Size it at D0; do NOT carry a 700K–1.2M figure into any justification** |
| A prior fix at this same seam addressed a false *negative* | HYPOTHESIS | git history for the lane-router change. ⛔ **Re-ground against it before scoping** — this is a false *positive* at the same seam and the two must not fight |
| Nothing already reports signal-resolution confidence | HYPOTHESIS | ⛔ asserted **absence** — check the route record's existing fields before adding D1 |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D3(d), the control, is the most important test in this plan.** Everything else confirms the router
  stops over-escalating; only the control confirms it can still escalate. Without it, a router hardwired
  to `light` passes the suite.
- ⛔ **D0's ordering-versus-scoring verdict must be explicit in the report.** If the field arrives late,
  shipping a scoring change would be a fix aimed at the wrong layer that also *looks* successful — the
  epic's archetype, committed by the plan that exists to close it.
- **D1's resolved-versus-null counts should get a cold read**: show the Step 6 verification sub-agent a
  route record with three nulls and ask how confident the decision was. If it reads as confident, the
  new field is not doing its job.
- **Report the token figure, if any, with its population and its derivation** — or do not report it. An
  unsourced saving estimate is the thing this plan's own claim table refuses.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Do not go looking for the orchestrator spec, the archived plan's decision log, or any landing
  record.** They live under `.plan/`, which is git-ignored and absent from this clone. The signal vector
  this plan needs is **transcribed in full above** precisely so the run never has to reach for that file.
- ⚠ A sibling plan quantifies the same run from the metrics side. It is **surface-disjoint** (router
  versus metrics renderer) and may run in parallel.
