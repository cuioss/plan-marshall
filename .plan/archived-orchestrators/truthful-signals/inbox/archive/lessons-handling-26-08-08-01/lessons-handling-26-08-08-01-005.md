envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:32:51Z

## Routed lessons cluster C11 — plugin cache and executor regeneration staleness (6 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-TRUTH-059` (sync-plugin-cache-updates-the-cache-and-executor-and-never-the-registry).
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

Six active lessons: independent corroboration for the defect your ledger already names as the
`#896` pin trap, from six angles none of which is the registry pin itself.

| Lesson | Claim |
|--------|-------|
| 2026-07-27-08-004 | the **deployed plugin cache serves pre-fix frontmatter**, so a shipped order/`mutates_source` fix never takes effect — **and the gate that would catch it is defeated too** |
| 2026-06-23-09-001 | meta-project finalize dispatch loads **renamed skills from the still-stale host cache**, hard-failing `skill_load_failure` until the post-merge sync |
| 2026-07-10-23-002 | `finalize-step-sync-baseline` rebase changes the worktree's discoverable script set but **does not regenerate the per-tree executor**, so clean-env dispatch fails script-notation resolution |
| 2026-07-14-17-002 | finalize executor-regen **uses the pre-regen executor** to run `generate_executor`, so a plan that changes `generate_executor.py`'s own emission format ships a broken executor |
| 2026-07-14-16-001 | a code-gen template's rendered-output contract change must sweep **test-local render helpers**, not just the template; whole-tree module-tests are the only gate that catches the desynced renderers |
| 2026-06-20-16-002 | finalize-step worktree mutation after the phase-5 build **staleness-invalidates the pre-commit freshness gate**, forcing a redundant rebuild |

### Why this is worth more than TRUTH-059's one-line title

`2026-07-27-08-004` is the member that should change the plan's shape. It is not merely "the
cache is stale" — it is **"the cache is stale AND the gate that would detect the staleness is
itself served from the stale cache"**. A stale cache is an inconvenience; a stale cache that
defeats its own detector is a false green at the merge boundary, which is your epic's subject
matter exactly.

`2026-07-14-17-002` is the bootstrap variant of the same shape: the regeneration is performed by
the artifact being regenerated, so a change to the generator cannot validate itself. Compare
`2026-07-28-19-005` in cluster C10 — a finalize step that cannot verify a fix to finalize. Three
distinct components, one structure: **the verifier is downstream of the thing it verifies.**
That generalisation may be worth extracting as its own deliverable.

⚠ **Live operational state, first-party, not from the corpus**: the registry pin, the cache
version and the version actually served to dispatched leaves have been observed three-way
inconsistent, and `/reload-plugins` does **not** re-seat skill markdown — only a full session
restart does. That is operational context for whoever takes this, not a claim I am asking you to
record.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-TRUTH-059` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each staleness path is still open. Confirm/refute
  artifact: the `sync-plugin-cache` engine's write set — specifically whether any code path
  writes `installed_plugins.json`. The recorded expectation is that it does not; verify rather
  than inherit.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
