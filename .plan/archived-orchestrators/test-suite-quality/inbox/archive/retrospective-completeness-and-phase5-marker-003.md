envelope_version=1
sender_type=plan
sender_id=retrospective-completeness-and-phase5-marker
epic=test-suite-quality
kind=candidate-lesson
created=2026-07-28T16:25:17Z

component=plan-marshall:phase-6-finalize
category=bug
proposed_bundle=plan-marshall
origin_plan=retrospective-completeness-and-phase5-marker
origin_pr=1036

# A finalize freshness-reconciliation record can launder a real source change into "already verified"

The finalize pipeline reconciles build freshness by comparing the HEAD a verify observed
(`head_at_completion`) against current HEAD. The reconciliation record's stated premise is
*"the source a verify observed is unchanged"*. When a **finalize-internal `mutates_source`
step** commits an edit to genuine source, that premise is **false**, but the record is still
produced — and applying it mechanically would push un-built source.

## Evidence (this plan's own `status.metadata.phase_steps["6-finalize"]`)

```
pre-push-quality-gate      outcome=done  head_at_completion=52a9de7d6…
                           "1 bundle + whole-tree quality-gate green, test-compile + module-tests green"
pre-submission-self-review outcome=done  "self-review clean: 41 candidates examined"
finalize-step-simplify     outcome=done  head_at_completion=6d51ae704…
ci-verify                  outcome=done  head_at_completion=6d51ae704…
```

Between the quality gate at `52a9de7d6` and the push, pre-submission self-review filed
Q-Gate finding `a3ebfe` and fixed it, producing commit `6d51ae704` —
`fix(phase-6-finalize): name the timeout path in the step-completion pairing enumeration`.

That commit edits `phase-6-finalize/SKILL.md`. **`phase-6-finalize/SKILL.md` is a build
input**: `test/plan-marshall/phase-6-finalize/test_step_completion_emission.py` — a file
this very plan added — *parses that SKILL.md at test time* to derive its expected emission
sites. So the finalize-internal commit changed source that the test suite reads. A
"nothing changed since the verify" reconciliation over that commit is factually wrong.

## Why the trap is well-hidden

1. The mutating step's own `display_detail` can read as a no-op. `finalize-step-simplify`
   reported **"Simplify: 0 edits, 0 findings"** while its `head_at_completion` had already
   advanced to `6d51ae704` — the HEAD move came from a *sibling* settle-band step, not from
   simplify. A reader checking the step that reports the new HEAD sees "0 edits".
2. Doc-shaped edits look non-buildable. A `.md` under `marketplace/bundles/**` reads as
   documentation, so the reflex is "docs-only, no rebuild needed". That reflex is exactly
   wrong in a repo where SKILL.md bodies are **parsed by tests** — the population-derived
   detector pattern this epic has been standardising on (`test/_shared/_dispatch_roster.py`,
   and now `test_step_completion_emission.py`) makes markdown a first-class build input.

## Corrective rule

**A freshness-reconciliation record is only valid when NO `mutates_source` step committed
between the verify's `head_at_completion` and current HEAD. When one did, the record is
void — re-run the build; do not reconcile.**

Do not weaken this to "re-run only if the changed files look buildable". In this repo the
buildable/non-buildable split cannot be read off the extension: markdown under
`marketplace/bundles/**` is parsed by tests. (`build_map` as THE oracle — the pending
WS-10 PLAN-35 work — is the structural fix; until it lands, the conservative rule stands.)

**This run did the right thing**: the build was re-run and CI is green at `6d51ae704`.
The lesson records the trap, not a defect that shipped.

## Impact

Every finalize run in which a settle-band `mutates_source` step (pre-submission-self-review,
simplify, security-audit, plugin-doctor, era-stamp-fill) produces a commit after
`pre-push-quality-gate`. That is the majority of non-trivial plans. Symptom when the rule is
violated: un-built source reaches the push barrier, and the failure surfaces as CI red on a
tree that "already passed the gate" — a false-green in the local record.
