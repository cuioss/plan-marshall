envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:12:18Z

# A confident verdict refuted by data already at the same site

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 5 lessons. **Suggested fold target:** yours to decide.

## Boundary against the sibling clusters

- The **empty-population** cluster: the check looked at nothing.
- The **cannot-fail-test** cluster: the test's arrangement made its subject unreachable.
- **This one:** the discriminating data was *present, at the same site, in the same payload*,
  and the check read the wrong field. No new plumbing is needed for any member — the fix is
  to read what is already there.

That distinction is the cluster's whole argument for existing separately: these are the
cheapest fixes in the corpus.

## The five instances

| Lesson | The verdict | The data that refutes it, at the same site |
|--------|-------------|--------------------------------------------|
| `2026-08-26-06-001` | `pre-commit-verify-freshness` → `status: fresh`, `notation_cross_check: corroborated` | The **same ledger row** carries `tests_run: 0`, `analyses_examined: compile, lint`, `command: ./pw quality-gate plan-marshall`. Every build canonical shares one notation, so a lint run and a full test run are indistinguishable to a notation-only filter. |
| `2026-08-25-17-001` | `files_exist` → *"step.target `marketplace/bundles/**/*.py` does not exist"*, remediation *"create the file"* | Its **sibling check in the same pass** (`declared_scope_reconciliation`) expands that identical glob to 431 files. Reproduced across all five declared globs in one pass. |
| `2026-08-26-09-001` | `_start_daemon` → `running: True` | Returned on **both** branches, the post-spawn one with no liveness re-probe. It is a structural constant named like an observation, sitting in a result dict whose own new prose invites callers to "gate on a field that can report failure". |
| `2026-08-26-15-001` | `ci pr merge-queue` → `enqueued: true`, twice | The corroboration string is *"merge_queue rule active on branch"* — a property of the **branch protection config**, not of this PR's membership. `landing-state` stayed `pr_open` across ~25 minutes and three polls. The queue was `externally_managed`, so membership is not something the branch rule can report. |
| `2026-08-24-14-001` | `baseline-reconcile` reports conflicts | It counts **merge-tree informational lines** as conflicts. (Title-derived — see caveat.) |

## Two facts worth carrying

⭐ **`2026-08-26-15-001` was independently confirmed by a second observer, twice, in a
different session** — the `truthful-signals` orchestrator hit it landing PRs #1347 and #1350
and recorded it *before* draining the lesson. The two observations are independent, not one
narrative echoed. Its practical rule: after `pr merge-queue`, confirm membership with
`pr auto-merge` (which reports `disposition: enabled | enqueued`) or by polling `pr view`
for `state: merged`.

⭐ **`2026-08-26-15-001` also names the upstream concession**: `standards/pr-operations.md`
describes the GitHub arm as *"a pre-enqueue probe … run BEFORE the `gh` call"*. So the field
is documented as a **pre**-condition and consumed as a **post**-condition confirmation. The
defect is the reading the field's name invites, not a lie in the code.

⚠ Within that one surface in one run: `merge-queue` reported unverified success,
`safe-merge` **refused honestly** with a specific explanation (catching the #1081 false-green
landing defect at the tool layer), and `auto-merge` worked. The honest refusal is the shape
to copy.

## Claim labels

- **OBSERVED** — the four full-body instances, with their quoted payloads and named sites.
- **OBSERVED** — the independent second observation of `26-15-001` on #1347 and #1350; the
  lesson records both observers' verbatim output.
- **HYPOTHESIS** — `2026-08-24-14-001` belongs in this cluster. It is **unresolvable**:
  `manage-lessons list` enumerates it `active`, `get` returns `not_found`, so its body was
  never read by anything in this run and the assignment rests on its `list` title alone.
  Confirm/refute at the lesson file once the corpus-integrity defect is fixed.
  Verify-at-outline.
- **HYPOTHESIS** — that all five are fixable by reading an already-present field, with no
  schema change. It holds by inspection for `26-06-001` (the lesson says so explicitly) and
  for `25-17-001` (a shared expansion helper); it is **not** established for `26-15-001`,
  where a per-PR membership read may be a new call rather than a different field.
  Confirm/refute per member at outline.

⛔ Site references and figures are the filing plans' own and were NOT re-derived here.
