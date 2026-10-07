envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=landing
created=2026-08-02T21:09:09Z

## What landed

Plan `fail-closed-signal-integrity` (spec `PLAN-TRUTH-010`) shipped as **PR #1081**, 8 commits.
Whole-tree verify SUCCESS (17361 passed); CI green.

Theme fit: every deliverable removes one place where a signal was confidently benign
because the machinery could not tell "nothing wrong" from "could not tell".

| Arm | What shipped |
|-----|--------------|
| D1 | `build-pyproject`'s file-to-build map now routes `*.py.template` and non-Python test fixtures, so a change to them can no longer map to "no build needed". |
| D2/D3 | The `kind=build` change-ledger stamp is gated on a build-executing-subcommand allow-list — a non-building subcommand no longer stamps a build record. |
| D3 | New **Fail-Closed Classification** section in `ref-code-quality` — the standard the arms above are graded against. |
| D4b | `resolve_test_scope` fails closed on unmappable paths instead of returning an empty (benign) scope. |
| D5 | Launch-abort pin. |
| Operator-directed addition | A derived-only `unknown` build status: an exit-0 payload carrying no recognised status can never derive `success`. |

## Refuted arms — record these as RESULTS, not as gaps

Three of the request's arms were refuted on contact. They are outcomes of the plan, not
unfinished work, and the epic should not re-queue them:

1. **D4 (leaf record-before-return invariant) was ALREADY LANDED** in `agents.md`. No
   deliverable was produced. The request arm was stale.
2. **D4b's literal example (`.claude/skills/**`) was already fail-closed.** The CLASS was
   real and was confirmed at three OTHER shapes — the example was wrong, the arm was not.
3. **The launch-abort arm was already fail-closed** (a negative returncode already maps to
   `killed`). The arm reduced to a stub-binary pin.

## Residue the epic should track

1. **D5 lesson retirement is UNFINISHED.** Classification is complete and logged;
   *application* is blocked by a fail-open in `manage-lessons restore-from-plan` (emitted
   as its own `candidate-lesson` message). 8 lessons were carried; 2 of the spec's 10 were
   already absent from the corpus before this plan ran.
2. **Ordering conflict with no current solution.** `lessons-housekeeping` was moved into
   the settle band (order 4) for edit pushability, which broke its access to the
   carried-lesson corpus (main-anchored resolution). Both halves cannot be satisfied at one
   order today. Emitted as its own `candidate-lesson` message.
3. **Epic follow-up OWED:** enforce a single authoritative `_TEST_ROOTS` — remedy B, thread
   the root set through `resolve_test_scope`. Size it against the known consumer-sweep
   hazard on that signature (this run hit that hazard twice; see the consumer-sweep
   `candidate-lesson` message).
4. **Four fail-open defects were found in our own machinery** during this run, three of
   them live in merged main. Each rides as its own `candidate-lesson` message: the
   `restore-from-plan` fail-open, the review-retrospective's inability to distinguish a
   refused reviewer from a clean one, and `scope_creep_check`'s benign `no_baseline_sha`
   verdict.

The review-retrospective item is review-apparatus-shaped, not measurement-shaped — routing
is the orchestrator's call, not this plan's.
