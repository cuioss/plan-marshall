envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T06:45:30Z

component=plan-marshall:manage-lessons
category=bug

# Plans override a correctly-firing `wrong_store` guard, so plan-marshall lessons accumulate invisibly in a consuming repository

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, observed across PLAN-11 and PLAN-10
(PRs #718 and #725).

## Observation

Token-Sheriff's lessons store now holds **9 active lessons, every one of them a `plan-marshall:*`
component** — `phase-4-plan` ×2, `phase-5-execute`, `manage-lessons`, `build-maven` ×2,
`manage-architecture`, `automatic-review`, `plan-marshall`.

They cannot have been filed through the sanctioned path, because the guard refuses. Probed directly at the
relaying orchestrator:

```
manage-lessons add --component plan-marshall:build-maven …
→ status: error
  error: wrong_store
  message: "lessons store repo '…/TokenSheriff/.plan/local' does not own bundle 'plan-marshall'
            (from component 'plan-marshall:build-maven'); refusing to file into the wrong store.
            Pass --allow-foreign-store to override."
```

⛔ **The guard works. It is being overridden** — by `--allow-foreign-store` or an equivalent path — and the
override is what produces the harm the guard exists to prevent.

## Why this matters more than a misfiled record

A lesson about a plan-marshall defect, filed into a consuming project's store, is **invisible to the
repository that owns the defect**. Nine defects in this list — including a `diff-modules` that reports all
modules changed over byte-identical input, and a build wrapper under-reporting a 762-test Surefire run —
are recorded where nobody who can fix them will read them.

⚠ **And the consuming project pays twice**: this epic's founding goal was to empty its lessons corpus, and
it did (21 of 21 retired, 47 tombstones). The corpus has since regressed **0 → 9**, entirely from
foreign-bundle lessons, so the project's own signal is now buried under another repo's defects.

## Suggested corrective action

- Treat `--allow-foreign-store` as an operator-only escape hatch, not something a plan reaches for when the
  guard fires. A plan that hits `wrong_store` has learned where the lesson belongs — the correct response
  is to route it there (an inbox relay, as this epic does), not to force the local write.
- Consider whether the guard should be **fail-closed for automated callers** and overridable only with an
  explicit operator confirmation, since the failure is silent and its cost is deferred.
- ⚠ There may be a second path that bypasses the guard entirely rather than overriding it — the relaying
  orchestrator could not determine from the store alone which route these nine took. Worth establishing,
  because a bypass and an override need different fixes.
