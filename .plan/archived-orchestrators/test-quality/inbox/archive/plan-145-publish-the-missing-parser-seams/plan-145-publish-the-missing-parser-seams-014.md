envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:49:17Z

# Script-failure cluster: review_completeness --measured-diff-size supplied without a value

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan) — and the notation behind this plan's automated-review signal
**Notation**: `plan-marshall:automatic-review:review_completeness`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence

```text
[2026-09-04T13:45:02Z] [ERROR] plan-marshall:automatic-review:review_completeness check (0.07s)
  exit_code: 2
  args: check --plan-id ... --required-bots cuioss-review-bot,coderabbit --optional-bots sourcery
        --participated-bots coderabbit:inline,cuioss-review-bot:issue_comment
        --refused-bots sourcery --stale-participation-bots --declined-bots
        --refused-causes sourcery:quota --refusal-size-caps
        --unrecognised-refusal-bots --measured-diff-size
  stderr: usage: review_completeness.py check [-h] --plan-id PLAN_ID [--required-bots [REQUIRED_BOTS]] ...
```

Corrected and green six seconds later.

## Why it is candidate-lesson material

Five of the invocation's list-flags are declared `nargs='?'` and are therefore legal bare (`--stale-participation-bots`, `--declined-bots`, `--refusal-size-caps`, `--unrecognised-refusal-bots`) — the empty-is-safe guarantee. `--measured-diff-size` is the **one flag in the same trailing run that requires a value**, so a caller pattern-matching on its four bare neighbours writes it bare and is rejected. This is already recorded verbatim as global lesson `2026-08-25-09-014` ("`review_completeness --measured-diff-size` is the one flag the empty-is-safe guarantee does not cover"), so this run is a recurrence.

## Surrounding context on the same notation this run

The `automatic-review` step fired **5 times** on this plan (4 `loop_back`, 1 `done`), and its final `display_detail` reads "0 comment(s) found - 1 reviewed, 1 empty, 1 refused (unified triage pending)". Sourcery posted a hard-quota refusal (250,000 diff characters exhausted) anchored to a superseded head; it was closed as a review-process signal. Two already-active lessons name that exact refusal-classification gap (`2026-09-02-08-001`, `2026-08-25-09-012`) and a third names the pacer a dispatched leaf cannot execute (`2026-09-03-06-002`) — all three were reinforced by this run.

## Proposed rule (for orchestrator judgement)

Where a flag run mixes `nargs='?'` and value-required flags, either make the odd one out consistent, or have the rejection say "`--measured-diff-size` requires a value; the neighbouring list flags do not". The uniform-looking neighbourhood is the whole defect.

## Related already-active lessons (all reinforced this run)

- `2026-08-25-09-014` — `--measured-diff-size` is the one flag the empty-is-safe guarantee does not cover
- `2026-09-02-08-001`, `2026-08-25-09-012` — Sourcery quota/refusal phrasing unmatched by `refusal_patterns`, so a declination is credited as participation
- `2026-09-03-06-002` — replace the standalone sleep pacer the dispatched leaf cannot execute
