envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:02:53Z

component=plan-marshall:tools-script-executor
category=bug
confidence=medium
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Prefer stderr over stdout in the failure detail when exit_code is 2

## Context

This plan recorded 17 script failures, 9 unique. Their classification:

| subtype | count |
|---|---:|
| `argparse_other` (the catch-all) | 8 |
| `script_internal_error` | 1 |
| `invented_subcommand` / `missing_required_flag` / `invented_flag` | **0** |

The named argparse taxonomy — the whole point of the classifier — matched **0 of 9**.
Eight of the nine findings carry an empty `stderr_excerpt`.

## Root cause

`script-failure-analysis` classifies by substring-matching the diagnostic text it is
given. For work-log-sourced failures that text is the executor's `detail=` field,
which the executor derives with **stdout-preferred** precedence (a `status: error`
TOON `message`, else raw stdout, else stderr).

Argparse writes its usage and error text to **stderr** by construction, and exits 2
before any script body runs — so there is no TOON message and no stdout. The
stdout-preferred rule therefore yields an empty string for precisely the failure
class the taxonomy exists to name.

## Two consequences

1. `build_seed_lessons` emits one seed lesson per finding, titled
   `"Argparse rejection in {component} call"`. Its docstring states that title and
   category are deterministic functions of the subtype "so the dedup-classification
   step in plan-retrospective Step 5a can recognise prior recurrences". At a 0%
   classification rate every seed collapses to the same signature-free title, and
   that recurrence dedup cannot work.
2. Nothing publishes the classification rate, so the degradation is invisible. The
   fragment reports 9 confident findings and 9 confident seed lessons over a signal
   it could not read.

## Proposed action

- In the executor's `detail=` derivation, prefer **stderr** when `exit_code == 2`.
  The existing stdout-preference is right for a script that ran and reported an
  operation error; it is wrong for a rejection that happened before the body.
- Have `script-failure-analysis` publish `classified / total` beside its findings, so
  a taxonomy that matched nothing says so. This mirrors the `evaluated_population`
  discipline the dispatch-audit aspect already follows.

## Note

The catch-all is honestly named — `argparse_other` does not claim to be a diagnosis.
The defect is that the layer above it (seed lessons) presents a confident,
dedup-keyed artifact built on it, and no rate is published.

## Evidence

- aspect script_failure_analysis: 9 findings, 8 with empty `stderr_excerpt`
- `script-failure-analysis.py` `_ARGPARSE_SIGNATURES` / `classify_failure` /
  `build_seed_lessons`, and the module docstring describing the `detail=` precedence
