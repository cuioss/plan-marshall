envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T07:59:05Z

component=plan-marshall:manage-status
category=bug

# Candidate lesson: manage-status mark-step-done --head-at-completion rejects a short SHA

**Source signal**: script failure observed by the finalize orchestrator during this run (reported by the dispatcher; not independently present as a [FAILED] line in the plan work log).
**Component**: plan-marshall:manage-status (mark-step-done) and the phase-6-finalize step docs that build the call.

## What happened

`mark-step-done --head-at-completion <short-sha>` was rejected; only the full 40-character commit SHA is accepted. The call had to be re-issued with the full SHA.

## Candidate rule

Callers must resolve the full SHA (`git rev-parse HEAD`, not `--short`) before passing `--head-at-completion`. Either the docs that construct this call should say "full SHA" explicitly, or the verb could expand an unambiguous short SHA itself.

## Classification hint

Marketplace contract/usability issue (plan-marshall bundle); argparse-rejection class.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-10 (#256); previously lesson 2026-10-04-06-003. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
