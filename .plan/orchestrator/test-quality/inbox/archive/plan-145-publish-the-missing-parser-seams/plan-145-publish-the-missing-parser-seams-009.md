envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:52Z

# Script-failure cluster: manage-findings rejected four times, three of them by argparse-surface paraphrase

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan)
**Notation**: `plan-marshall:manage-findings:manage-findings`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence — four rejections, all exit 2

```text
[2026-08-30T16:27:51Z] qgate query   -> unknown_verb / rejected: query
                                        accepted: add, clear, list, resolve, resolve-evidenced
[2026-08-30T16:27:53Z] qgate list --status pending
                                     -> unknown_flag / rejected: --status
                                        accepted: iteration, phase, plan-id, resolution, source
[2026-09-03T16:13:16Z] qgate add --title <unquoted multi-word> --detail <unquoted multi-word>
                                     -> argparse usage dump (stderr)
[2026-09-03T16:21:09Z] qgate resolve --resolution-detail <text>
                                     -> unknown_flag / rejected: --resolution-detail
                                        accepted: detail, hash-id, phase, plan-id, resolution
```

The first two fired **two seconds apart**: the caller corrected `query` to `list` and immediately hit the next paraphrase (`--status` for `--resolution`) in the same invocation it had just repaired.

## Why it is candidate-lesson material

Three distinct paraphrase classes on one script surface in one plan — verb (`query`→`list`), filter flag (`--status`→`--resolution`), and result flag (`--resolution-detail`→`--detail`) — plus one quoting failure on the free-text `--title`/`--detail` pair. Two of these three are already named verbatim in the project's recurrence-signature checklist (signature 1 verb-paraphrase, signature 5 `--resolution` vs `--status`), which means the checklist is present and was not consulted at call time. That is the finding: the guidance exists, is accurate, and did not fire.

The back-to-back pair also shows the cost shape — a corrected verb does not re-validate the flags carried alongside it, so a single call can be rejected once per wrong token rather than once.

## Proposed rule (for orchestrator judgement)

Two candidate directions, both cheap:

1. **Reject once, name everything.** `manage-findings` rejects on the first offending token; validating the whole invocation and naming every rejected token would collapse the 16:27:51 / 16:27:53 pair into one round trip.
2. **Free-text flags take a staged file, not a shell argument.** `qgate add --title/--detail` carries multi-sentence prose through the shell argument vector; the `manage-lessons set-body --file` path-allocate pattern already solves this class and is not offered here.

## Related already-active lessons

- `2026-09-03-19-004` — name the rejected flag and the sibling verb's canonical form in argparse-rejection messages
- `2026-09-03-19-003` — `ci pr prepare-body` must reject a router-position `--plan-id` by name instead of reporting it missing
