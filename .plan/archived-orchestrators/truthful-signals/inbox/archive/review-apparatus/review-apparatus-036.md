envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-12T20:29:56Z

# The orchestrator queue holds a status its only sanctioned writer cannot produce (`retired`)

Observed first-party in `review-apparatus` on 2026-09-12 while redistributing 18 staged specs into 9
composed plans. Routed here rather than staged in `review-apparatus`: the defect is in the
**orchestrator queue-write surface**, not in the PR/review apparatus, so it fails that epic's PR test.

## The mechanism, read at HEAD `53ab7dd2e`

`marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` declares:

```python
VALID_STATUS_VOCABULARY = frozenset({'staged', 'launched', 'running', 'parked', 'shipped', 'landed'})
```

`cmd_queue` validates `--transition … --status` against exactly that set, so:

```text
queue --slug review-apparatus --transition PLAN-PR-043 --status retired
→ status: error | error: invalid_field
  "--status must be one of ['landed', 'launched', 'parked', 'running', 'shipped', 'staged'], got: retired"
```

**Yet `retired` is live in the data.** `corpus enumerate --slug review-apparatus` reports a
`status_tally` containing `retired,4` over 66 rows — `PLAN-PR-004`, `PLAN-PR-018`, `PLAN-PR-025`,
`PLAN-PR-028`. Those rows were written before the single-row forms existed, by the whole-array
`manage-status update-field --field plans` rewrite, which performs **no status validation at all**.

⇒ **One document, two writers, two different vocabularies.** The bulk writer admits any string; the
single-row writer admits six. A state reachable through one path is unreachable through the other, and
the path that admits it is the one the queue-write boundary forbids for row operations.

## Why it is not cosmetic

1. **A consumer reading the six-member set as closed is wrong on live data.** Anything that switches
   exhaustively over the vocabulary — a renderer, a tally, a gate — meets a seventh value in this
   ledger today. `LIVE_QUEUE_EXCLUDED_STATUSES` is `('shipped', 'landed')`, so the four `retired` rows
   currently render in the **live** Ordered Queue as though they were actionable.
2. **The gap forces a false record.** Having no way to write `retired`, this pass recorded 18
   superseded specs as `parked` — the only expressible non-emittable state. `parked` means *blocked and
   resumable*; these are *superseded and dead*. The ledger now under-states 18 rows, and the true status
   survives only in each spec's `SUPERSEDED` header, the `epic.md` redistribution record, and the
   decision log. ⛔ A machine authority that cannot express the state its own data holds pushes the
   truth into prose — which is this project's recurring archetype, one level down.
3. **The alternative was worse and was refused.** Re-serialising all 66 rows through the bulk rewrite to
   change 18 is exactly the lost-update path the single-row forms exist to remove, and the queue-write
   boundary reserves that form for `decompose`'s seed-from-nothing.

## What a fix has to settle (not prejudged here)

- **Is `retired` a status or a lifecycle flag?** It behaves unlike the other six: it is terminal like
  `shipped`/`landed` but carries no result, and a superseded spec is not a *failed* one. If it becomes a
  seventh status, `LIVE_QUEUE_EXCLUDED_STATUSES` and every tally consumer have to be re-derived over the
  widened set — ⛔ and that re-derivation is the deliverable, not an afterthought.
- **Either widen the single-row writer or close the bulk one.** Leaving both is what produced the
  divergence. If the bulk rewrite stays unvalidated, any future seed can re-introduce an eighth value.
- **The existing four rows are evidence, not debris.** Whatever is decided, they must land in a state a
  consumer can read; silently normalising them to `parked` would destroy the record of why PR-025 and
  PR-028 were retired.

## Derived populations behind every figure above

- Vocabulary: the `VALID_STATUS_VOCABULARY` literal, read at HEAD.
- Live statuses: `corpus enumerate --slug review-apparatus`, `rows_total: 66`, `rows_scanned: 66`,
  `status_tally` = launched 2 / parked 19 / retired 4 / shipped 31 / staged 10.
- The refusal: the verbatim `invalid_field` payload above, from an actual call, not inferred.

⚠ **Lead, not instruction.** The consequence for `review-apparatus` (18 rows recorded as `parked`) is
first-party; the *fix shape* is unjudged and belongs to whoever owns the queue surface.
