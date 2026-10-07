envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:32:34Z

## Routed lessons cluster C01 — derive-verification emits a build_class phase-5 cannot route (8 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: **NEW spec** — I found nothing in your 109-row queue that owns this surface.
**You decide**: stage, fold onto something I missed, or decline. Nothing was written into your tree.

⭐ **This is the flagship dedup result of the run.** Five separate lessons, filed over four days
against three different components, are ONE defect. Nobody noticed because each was filed from
the failing side it happened to be observed from.

### The five-way duplicate

| Lesson | Component it was filed against | Wording |
|--------|-------------------------------|---------|
| 2026-07-28-15-001 | `manage-architecture` | `derive-verification` emits compile / test-compile `build_class` commands that `manage-execution-manifest`'s per-task orchestrator-tier routing cannot map to a valid phase-5 canonical |
| 2026-07-28-15-002 | `phase-4-plan` | `derive-verification`'s compile/test-compile `build_class` breaks manifest compose (`unresolvable_step verify:compile`) |
| 2026-07-28-19-001 | `manage-architecture` | `architecture derive-verification` emits an unresolvable test-compile command **behind `status: success`**, breaking manifest compose |
| 2026-07-28-20-001 | `manage-execution-manifest` | `derive-verification`'s compile `build_class` has no phase-5 canonical route, so stamping it into a task's sole `verification.commands` fails compose with `unresolvable_step` |
| 2026-07-28-21-001 | `manage-execution-manifest` | `execution_tier` routing generalizes compile/test-compile to an unregistered verify step, breaking compose |

Same defect, three components, five lessons. `2026-07-28-19-001` adds the part the other four
miss and the part your epic cares about most: **the emission reports `status: success`**. The
producer says it succeeded; the consumer cannot route what it produced. That is a
confident-signal-hides-a-caveat instance sitting inside a producer/consumer contract gap.

### The three adjacent members

| Lesson | Claim |
|--------|-------|
| 2026-07-27-15-001 | `manage-tasks update` has **no write-back flag for `verification.commands`**, blocking phase-4-plan's Step 6 derive-verification stamp |
| 2026-07-27-23-003 | a compose-time force-out declared via `lane=off` **does not remove its step** — enforcement lives only in a run-time check |
| 2026-08-03-14-005 | `sonar-roundtrip` pruned as `no_code_delta` while compose logged the footprint **unresolvable** |

These are the same compose surface viewed from three other angles: the write-back that cannot
happen, the subtraction that does not take, and a prune whose stated reason contradicts the
compose log. `2026-08-03-14-005` in particular is a **two-reasons-one-event** case — the row
says `no_code_delta`, the log says unresolvable — which is your epic's exact theme.

### Scope caution

Eight lessons across `manage-architecture`, `manage-execution-manifest`, `manage-tasks` and
`phase-4-plan` is plausibly more than one plan. The five-way duplicate is one tight deliverable;
the three adjacent ones may not belong with it. Recommend staging the duplicate set first and
deciding the other three against it.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; the absence of a covering plan in
  your queue (read from `status.json`, 109 rows).
- **HYPOTHESIS (verify-at-outline)**: that the routing gap is still open — several of these are
  late-July and something may have landed since. Confirm/refute artifact: the
  `derive-verification` command handler in `manage-architecture`, and the `unresolvable_step`
  branch of `manage-execution-manifest`'s composer. ⚠ Per your own standing rule, establish the
  merge order before concluding the defect survives in main.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
