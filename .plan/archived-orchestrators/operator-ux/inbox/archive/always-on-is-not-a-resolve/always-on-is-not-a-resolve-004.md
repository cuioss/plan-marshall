envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T19:22:12Z

component=plan-marshall:tools-script-executor
category=improvement
bundle=plan-marshall
confidence=high

# Name the rejected flag and the canonical form in argparse-rejection messages

## Context

One plan produced 8 failed script calls across 4 unique signatures, and three of
the four were argparse rejections on three different scripts:

- `plan-marshall:manage-status:manage-status read` — exit 2, twice, at
  2026-09-03T18:22:40Z and 2026-09-03T19:09:44Z, from two *different* dispatched
  envelopes (`automatic-review` and `finalize-step-review-retrospective`).
  Executor message: ``Use a declared flag for `plan-marshall:manage-status:manage-status read`: ['plan-id', 'store']``
- `plan-marshall:manage-references:manage-references get` — exit 2, twice, at
  2026-09-03T16:03:55Z
- `plan-marshall:tools-integration-ci:ci pr prepare-body` — exit 2, twice

## Root cause

The executor's rejection message lists the flags the verb *does* declare, but
never names the flag it rejected and never points at the verb that accepts it.
A caller that reached for `--field` on `manage-status read` is told which flags
exist and is left to infer that `metadata --get --field` is the verb it wanted.
Every rejection therefore costs a diagnostic round trip, and the identical
mistake recurred across two independent envelopes in the same run — which is
what a message that does not teach the fix produces.

## Proposed action

Extend the executor's `failure_kind=argparse_rejection` message with two fields
it already has in hand:

1. the offending flag as the caller wrote it, and
2. when the flag is declared on a *sibling* verb of the same script, that verb's
   canonical form.

The `ci` router already does the second thing for its own position mirror-case
and it demonstrably works; generalising it to the executor's shared rejection
path covers every `manage-*` surface at once.

## Evidence

- aspect: script_failure_analysis — 8 total failures, 4 unique, 3 of 4 argparse rejections across 3 distinct scripts
- aspect: log_analysis — `errors_work: 8`, `errors_script: 8`
- The `manage-status read` rejection fired in two different dispatched envelopes, so this is not one caller's slip
