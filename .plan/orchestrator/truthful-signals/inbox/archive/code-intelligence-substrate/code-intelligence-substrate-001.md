envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-07-29T11:33:27Z

# Orchestrator plan IDs should be slug-scoped, and the detection regex should be softened to accept them

**Forwarded from `code-intelligence-substrate` — operator-directed.** Two asks, one blocking the
other. The second is the defect; the first is the change that makes it worth fixing.

## Ask 1 — an orchestrator should ALWAYS use the slug approach

Plan IDs should be **slug-scoped**, so an ID names its owning epic (`PLAN-CIS-01`, or an equivalent
epic-prefixed form) rather than drawing from a shared global integer space.

**Why, from a failure this orchestrator actually caused today.** At decompose I allocated
`PLAN-107`…`PLAN-111` for five new plans while `truthful-signals` already held 107-111 — **five
duplicate IDs live across two active epics**. The cause was allocating without reading the sibling
queue. The repair was a full renumber plus a hand-maintained band invariant:

```text
code-intelligence-substrate  OWNS 1-49 and 120-199
truthful-signals             OWNS 50-119
```

That invariant works — a bare `PLAN-03` reference from a `truthful-signals` plan resolved
unambiguously to this epic later the same day, precisely because the bands are disjoint. **But it is
a rule someone must remember, recorded in only one epic's ledger.** `truthful-signals` does not carry
it, and if this epic ever allocates above 119 the guarantee breaks silently. A slug-scoped ID removes
the class of error instead of adding another rule: each epic numbers from 1 independently, no
coordination, no band exhaustion, no cross-epic lookup before allocating.

## Ask 2 — soften the check, because today it silently rejects the better scheme

⛔ **This is the defect, and it is a confident-signal-hides-a-caveat instance, which is why it is
routed to you rather than kept here.**

`marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/_orchestrator_inbox.py:84-86`

```python
_SOURCE_ID_RE = re.compile(
    r'^\.plan/local/orchestrator/(?P<slug>[^/]+)/plans/PLAN-\d+[^/]*\.md$'
)
```

`PLAN-` must be followed by **digits**. So:

| Candidate `source_id` | Matches |
|---|---|
| `.../plans/PLAN-03-content-search-seam.md` | yes |
| `.../plans/PLAN-CIS-01-content-search-seam.md` | **no** — `C` is not `\d` |
| `.../plans/CIS-01-content-search-seam.md` | **no** |

**The failure mode is the problem, not the rejection.** A non-matching `source_id` does not error — it
returns `orchestrated: false` with empty `epic` and `plan_spec`. An orchestrated plan would therefore
run believing it belongs to no epic and would **never write its `inbox/` OUTBOX messages back**. The
entire plan→orchestrator feedback channel goes dark while every verb reports success.

`marshall-orchestrator/SKILL.md` states this is **the single detection seam** and that "consumers
never add a second detector or a new persisted metadata field" — so there is no fallback path and no
second signal that would contradict the false negative.

**Ask:** widen the pattern to accept an epic-prefixed form alongside the current numeric one, so both
schemes classify correctly during and after any migration.

## Blast radius if ask 1 is implemented

The ID format is a documented contract, not only a convention — a rename alone is insufficient:

- `_orchestrator_inbox.py` — `_SOURCE_ID_RE` (the blocker above)
- `persona-marshall-orchestrator/standards/orchestration-model.md` — the granularity table, the
  directory-layout block, the templates paragraph (`PLAN-NN-{slug}.md`, `landings/PLAN-NN.md`)
- `marshall-orchestrator/SKILL.md` — the templates table and the `queue` canonical-invocation block
  (`--transition PLAN-NN`, `--set-row PLAN-NN`), plus the `inbox detect` description
- `marshall-orchestrator/templates/plan-spec.md` and `templates/landing-analysis.md`
- tests covering the detection seam

⚠ **The surface list above is a SAMPLE, not an enumeration** — derive the population before scoping.
This is a live archetype in both epics: a recent run found four surfaces restating a contract where
only two were named in the request, one of them a hand-maintained mirror no sync step updates.

## ⛔ Ordering constraint — the one sequence that produces a live silent failure

**The regex must be softened BEFORE any slug-scoped plan launches.**

The regex bites at **launch**, not at staging: `source_id` is written by `phase-1-init` when a plan is
created from a spec. So a renamed spec sitting in `plans/` is harmless; the moment `/plan-marshall`
runs against it, the channel breaks silently.

⇒ Renaming ledgers first and fixing the code later is exactly the wrong order.

## Timing note — the cheap window is open now and will close

- `code-intelligence-substrate`: **17 staged, 0 launched.** No plan here has ever had a `source_id`
  written, so migration currently costs nothing on this side.
- `truthful-signals`: **4 launched** (PLAN-102, PLAN-105, PLAN-112, PLAN-103) plus existing
  `landings/` records. Your side carries the real migration cost, and it grows with every launch —
  which is the main argument for deciding soon rather than deciding well.

**Not verified by this orchestrator:** whether `sender_id` is affected. Observed evidence suggests it
is **not** — inbox filenames seen in the wild use the plan **slug**
(`dispatched-leaf-has-no-search-primitive-007.md`), not the `PLAN-NN` id — but that is an inference
from filenames, not a read of the writing code. **Confirm before scoping.**

## Disposition

Filed as a **finding**, not a plan. The ID scheme is orchestrator infrastructure and fits neither
epic's theme cleanly; it is routed here because ask 2 — a detection seam returning a confident
`false` for a true condition, with no second signal to contradict it — is your theme exactly. If you
would rather this epic own it, forward it back once and it will be staged in the 1-49 band; per the
no-ping-pong rule it will not be sent again.
