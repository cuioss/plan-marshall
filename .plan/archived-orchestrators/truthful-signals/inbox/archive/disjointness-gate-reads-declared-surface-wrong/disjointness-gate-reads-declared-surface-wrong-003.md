envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:34:46Z

component=plan-marshall:plan-retrospective
category=bug
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# The realized-footprint derivation cannot represent a declared delete on a renamed path

## What happened

Deliverable 2 of PLAN-TRUTH-113 declared two paths with `intent: delete`:

- `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_spec_parser.py`
- `test/pm-plugin-development/tools-epic-surface-partition/test_epic_spec_parser.py`

Both were deleted exactly as declared. `git diff --no-renames --name-status
b510ef29c..b758d5c02` lists both as `D`, and the true footprint is **24 files**.

But every footprint-consuming aspect reported them as **declared but not realized**:

- `check-artifact-consistency`: `affected_files_recall` **90.9%**, `missing[2]` naming
  exactly those two paths, with `footprint_resolved: true`.
- `check-outline-vs-shipped`: `include_unrealised: 3 of 23`, two of them the same
  paths.

True recall is **100%**.

## Root cause

The shared footprint resolver derives the realized surface from a `git diff` with
**default rename detection**, which reports only a rename's **destination**. Both
deletes were halves of moves:

- `_epic_spec_parser.py` -> `script-shared/scripts/epic_spec_parser.py`
- `test_epic_spec_parser.py` -> `test/plan-marshall/script-shared/test_epic_spec_parser.py`

Git collapsed each pair and emitted only the new path, so the source path — the one
the deliverable declared — is structurally absent from the compared surface.

This is **not** an artefact of the `--diff-file` the retrospective supplied.
`check-artifact-consistency` ran before that file existed, resolved the footprint
through the shared resolver's own tier chain, and produced the identical `missing[2]`.

## Why it matters

The plan's own subject is a gate that reported *could-not-compare* as a *clean
verdict*. This is the same shape inside the machinery that audits the plan: an
operation the instrument **cannot represent** is reported as a **coverage
shortfall** (90.9%) rather than as indeterminate. A reader grading thoroughness to
the floor is handed a false 9-point deficit and two false "silent descope"
candidates.

## Remedy shape

Derive the realized footprint with rename detection disabled, or record **both**
sides of each rename, inside the shared footprint resolver — one derivation, three
consuming aspects corrected. Where the derivation still cannot decide, report
indeterminate rather than counting the path as unrealized.
