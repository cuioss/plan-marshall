envelope_version=1
sender_type=plan
sender_id=retrospective-completeness-and-phase5-marker
epic=test-suite-quality
kind=candidate-lesson
created=2026-07-28T17:06:03Z

component=plan-marshall:manage-execution-manifest
category=anti-pattern
proposed_bundle=plan-marshall
origin_plan=retrospective-completeness-and-phase5-marker
origin_pr=1036

# Manifest composition prunes steps on a footprint that is ALWAYS empty at compose time — the quality gate was dropped and only an unrelated rule put it back

The execution manifest is composed in phase 4-plan, before a single file has been changed.
One of its pruning inputs is the plan's footprint. At that moment the footprint is empty **by
construction, for every plan that has ever run**. So any prune predicate reading it is
vacuous, and it fires in the maximally-dangerous direction: "nothing changed, drop the
build".

## Evidence (this plan's `decision.log`, all at 13:05:04, compose time)

```
(manage-execution-manifest:compose) pre-push-quality-gate omitted —
    plan footprint is empty — no changed files to build
(manage-execution-manifest:compose) ceremony_finalize selection —
    finalize.qgate=always, added pre-push-quality-gate to phase_6.steps
```

Read those two lines in order. The composer **dropped the pre-push quality gate** from a plan
that went on to change 10 files across four skills plus four test files — and then a
completely unrelated rule (`finalize.qgate=always`, a ceremony setting) happened to add it
back one line later.

The gate ran, CI was green, nothing shipped broken. **That is luck, not a control.** Flip
`finalize.qgate` to anything but `always` and this plan pushes 10 changed files with the
pre-push quality gate silently pruned, while the manifest reports a clean, deliberate
composition decision with a plausible-sounding reason attached.

## Why this is the vacuous-guard archetype again

The predicate is not merely *often* false — it is **never** true at the point it is
evaluated. A footprint-emptiness test at compose time is a constant, and the constant is
"empty". This is the same shape the epic has now hit repeatedly: a branch whose condition
cannot take the other value at the moment it is read (D2 of this very plan was
`phases[5-execute].status == "pending"`, already falsified by the preceding transition).

The tell is identical too: the log line **reads like a measurement**. "plan footprint is
empty — no changed files to build" states an observation about the plan. It is actually an
observation about the clock.

## Two further compose-time signals in the same window

Both self-reported, neither acted on:

```
unresolvable_step — phase_5 step `verify:compile` in marshal.json is unresolvable:
    names an unknown canonical `compile` — no ext-point-build-verify-step implementor
    (nor the composer canonical->role table) declares it
unresolvable_step — phase_5 step `verify:test-compile` in marshal.json is unresolvable: …
```

`marshal.json` declares two phase-5 verification steps that no implementor provides. The
composer routed them, stamped execution tiers for them, then discovered they were
unresolvable and dropped them across three recompose cycles. The final manifest carries three
verification steps; the config asked for five. Nothing failed, and nothing surfaced the
discrepancy outside the decision log.

## Corrective rule

**A prune predicate MUST NOT read a quantity that is not yet determined at the point of
evaluation. When the input is structurally unavailable, the predicate must abstain — keep the
step — not evaluate to the permissive branch.**

Concretely:

1. Footprint-derived pruning belongs at **phase-5 exit / phase-6 entry**, where a realized
   footprint exists, not at 4-plan compose time. If a compose-time decision genuinely needs a
   footprint, it must use the *predicted* footprint (deliverable-declared targets) and say so
   in the log line, never the empty realized one.
2. Until then, footprint-emptiness must **fail safe**: empty footprint at compose time means
   "unknown", and unknown keeps the build step. A build step must never be dropped by a
   predicate that cannot distinguish "no changes" from "not measured yet".
3. `unresolvable_step` should be a **composition warning surfaced to the operator**, not an
   INFO line. A `marshal.json` naming steps no implementor provides is a configuration defect
   that currently self-heals into silence.

## Impact

Every plan, on every compose. The pre-push quality gate is currently protected only by
`finalize.qgate=always` being set in this project's config — a coincidental dependency
between an unrelated ceremony setting and the primary pre-push build control. Any project
adopting plan-marshall without that setting inherits the unguarded path, and the symptom is a
false-green local record followed by red CI.

## Verification note

Reproducible from `decision.log` alone — no session context required. The two decisive lines
are adjacent and timestamped identically.
