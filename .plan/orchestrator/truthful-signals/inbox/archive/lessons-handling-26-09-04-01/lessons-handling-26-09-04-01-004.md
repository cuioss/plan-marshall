envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=finding
created=2026-09-04T07:45:53Z
revision=1
amended=2026-09-04T07:49:54Z

# Finding: `manage-lessons list` reports lessons that `manage-lessons get` cannot retrieve — two metadata formats coexist and only one is readable

> **Relayed from Token-Sheriff.** Source epic `lessons-handling-26-09-04-01`. Discovered *while performing* a lessons-consolidation pass over that repository's corpus, not filed by a plan — the pass would have silently dropped three of twenty-one lessons had the discrepancy not been checked.

**Proposed component**: `plan-marshall:manage-lessons` (the shared id-resolver behind `get` AND `remove`, and whatever wrote the second format)
**Category**: `bug` — two verbs disagree about the same population, and the disagreement is silent

## What was observed

In `.plan/local/lessons-learned/` (21 lesson files), `manage-lessons list` returned **21 rows**. Calling
`manage-lessons get --lesson-id {id}` for each row returned:

- **18 × `status: success`**
- **3 × `status: error` / `error: not_found`** — for `2026-08-31-12-001`, `2026-09-03-18-001`, `2026-09-03-23-001`

⛔ **The files exist.** All three are present on disk, non-empty, and well-formed markdown. `get` reports `not_found`
for a file that is right there.

## The cause, confirmed by correlation over the whole corpus

Two metadata formats coexist in one store, and the split is exact:

| Format | Example | `list` | `get` |
|---|---|---|---|
| Bare `key=value` lines, no delimiters | `id=2026-09-04-07-001`<br>`component=token-sheriff-build` | ✅ 18 rows | ✅ success |
| **YAML frontmatter**, `---` delimited | `---`<br>`id: 2026-08-31-12-001`<br>`component: maven-build`<br>`---` | ✅ 3 rows | ⛔ `not_found` |

The correlation is perfect across all 21 files: **every** YAML-frontmatter lesson is unreachable via `get`, and
**every** `key=value` lesson is reachable. The three affected files also carry different filesystem permissions
(`-rw-r--r--` vs `-rw-------`), consistent with having been written by a different producer than the one `get`
expects.

`list` degrades quietly rather than failing: the three rows appear with **empty `component` and `category`** columns,
which reads as "this lesson has no component" rather than "this lesson could not be parsed".

## The durable content

**A store whose enumeration verb and whose retrieval verb accept different formats has a population that is listed
but unreachable, and nothing in either verb's output says so.** The two failure signatures compound:

1. `get` returns `not_found` — the vocabulary for *absent*, used here for *present but unparseable*. A caller cannot
   distinguish a lesson that was removed from one it cannot read, which is the same `absent`-vs-`unreadable`
   distinction the orchestrator's own corpus verbs are careful to keep separate (ADR-019's rule, one level down).
2. `list` fills the unparsed fields with empty strings instead of marking the row degraded, so the loss is invisible
   at the only surface that would show it.

⚠ **The consumer this actually breaks is the lessons-handling mode itself.** Its Step 2 is *"list, then read each
lesson's full body, one `get` call per lesson id from the list output"* — precisely the list→get walk that drops
these three. A consolidation, a dedup pass, or a retirement sweep performed that way operates on 18 of 21 lessons
and reports success.

## ⛔ It is not only `get` — `remove` is affected too, and that turns a read gap into a stuck store

**Amended after the original filing.** The consolidation pass that found this then tried to retire the corpus, and
`manage-lessons remove` refused the same three lessons with the same `not_found`:

- **18 of 21 lessons retired** normally, each with a tombstone.
- **3 of 21 could not be retired at all** — `2026-08-31-12-001`, `2026-09-03-18-001`, `2026-09-03-23-001`.

So the defect is not `list` vs `get`; it is **`list` vs every id-addressed verb**, because they share the resolver.
⚠ **A reader who fixes only `get` will leave `remove` broken**, and the store keeps a population that can be listed,
cannot be read, and cannot be retired.

The practical consequence is worse than a silent read gap: a lesson in this state is **permanently stuck in the
corpus** through the sanctioned interface. The only ways out are to rewrite the file's metadata by hand — which
bypasses the tombstone the store writes for every other retirement, destroying the audit record the removal path
exists to produce — or to fix the resolver. The reporting orchestrator declined the hand-edit for exactly that
reason and left the three in place.

## Suggested direction (not a prescription)

Either resolution closes it, and the choice belongs to whoever owns the store:

1. **Make `get` accept both formats** — the migration-tolerant reading, if the YAML form was ever legitimate; or
2. **Make `list` refuse to emit a row it cannot fully parse**, reporting it in a distinct `unreadable[]` population
   with its id and the reason — so the walk sees a stated failure instead of a silent omission.

⛔ What should *not* happen is the third option: leaving `get` as-is and treating the three files as corrupt. They
are readable markdown carrying complete, correct metadata in a format something in the toolchain wrote.
