# The six invalid (headerless) corpus entries — preserved before removal

These six files sat in `.plan/local/lessons-learned/` carrying **no metadata header** — no `id=`,
`component=`, `category=`, `status=` or `created=` line. The corpus's own surfaces disagreed about them:

- `manage-lessons list` **showed** them (it derives its population from file presence), with empty
  component and category cells;
- `manage-lessons get --lesson-id {id}` returned **`not_found`** for every one;
- `manage-lessons remove` therefore had no sanctioned path to retire them, and calling it on an
  unresolvable id is the documented failure mode that destroys a DIFFERENT lesson when retried.

They were removed from the corpus on 2026-09-18 by operator instruction. **This directory is the only
surviving copy**, which is why it exists.

⛔ **These removals wrote NO tombstone.** Every other retirement in this sweep left
`.plan/local/lessons-learned/.tombstones/{id}.json` recording the verdict and reason. These could not:
the tombstone is written by `manage-lessons remove`, and that verb cannot resolve a headerless file. So
the audit trail for these six is this README and the epic's decision log — nothing else. That gap is
itself a finding, and it is owned by `PLAN-PRQ-05`.

## The six, and what each said

| File | Subject | Where it belongs |
|---|---|---|
| `2026-09-08-22-004` | a completeness sweep must derive its population from the claim, not from one phrasing of it | self-review sweep discipline — not post-run quality |
| `2026-09-08-22-005` | declare a file as expected-to-mutate from a value-pin check, not a keyword hit | `phase-3-outline` declared surface — not post-run quality |
| `2026-09-08-22-006` | `manage-metrics reconcile-ledgers` is a producer with no consuming aspect; 24 findings over 32 union rows never reach the report | **PLAN-PRQ-08 D1** (carried) |
| `2026-09-08-22-007` | a precondition keyed on the marker whose absence is the defect can never fire (`RE_ENTRY_COVERAGE`) | **PLAN-PRQ-09 D1** (carried) |
| `2026-09-13-06-001` | `step_params` persists a lane override that lane resolution refused; a retrospective dispatch prompt reasoned from the discarded value and was wrong | **PLAN-PRQ-06 D2a** (carried) |
| `2026-09-13-06-002` | nothing consumes `reconcile-scope`, so a sanctioned scope expansion never re-syncs the footprint | ⚠ `truthful-signals` **PLAN-TRUTH-145**, which folded it on 2026-09-13 |

⭐ **Four of the six were already carried into a spec before removal**, so no owned work was lost with the
files. The two that were not (`-22-004`, `-22-005`) are out of this epic's scope by subject; their text
survives here and nowhere else, which is the reason this directory is not a convenience copy.

## Why they were invalid in the first place

Unestablished. The corpus allocates a header at `manage-lessons add` time, so a headerless file was either
written outside that path or lost its header afterwards. ⛔ Neither was verified before removal, and the
files are now gone from the corpus — so the cause is no longer observable there. `PLAN-PRQ-05`'s D1
precision measurement must count a headerless file as its own state rather than as an absent lesson, and
its D0 should establish how one comes to exist at all before the class is declared closed.
