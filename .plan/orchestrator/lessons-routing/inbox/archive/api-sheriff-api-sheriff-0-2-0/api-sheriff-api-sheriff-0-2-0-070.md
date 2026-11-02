envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-29T09:10:05Z

# The finalize preference emitter derives an "accept intermittent failures under load" hint from accepted findings, which a project can hold the opposite of

Observed by `plan-v02-50-enumeration-detection-substrate` while landing PR #532 in the API-Sheriff repository
(epic `api-sheriff-0-2-0`, plugin 0.1.2021). The step's owed message was `-009`, kind `candidate-lesson`.

- Two within-plan recurrences cleared `preference_min_recurrence` (accepted `test-failure` findings x5, accepted `build-error`
  findings x2), all attributed to the `maven` build tool, and the step recorded an owed `architecture enrich` call with the
  generalised hint "intermittent test failures and build errors that only appear under foreign load are accepted as load
  artefacts after a solo re-run".
- The orchestrator declined the call. The project's standing rule is the opposite: a CI-red integration test is a suspected
  production defect until a root cause is named, and earlier plans found real races behind "flakes". The same plan's own candidate
  `-003` says so. The accepted findings were individual acceptances after a solo re-run, not a project policy.
- The target was also not a project module: the findings were attributed to the build tool (`maven`), so the hint had no sound
  architecture module to land on.

Suggested direction: do not promote accepted-finding recurrence to a standing "accepted" preference without a human decision; when
the attribution is a build tool and not a module, drop the hint rather than leave an owed call for the orchestrator to guess a module.
