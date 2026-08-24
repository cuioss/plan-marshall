# Landing payload specification

The machine-readable payload a `kind: landing` inbox message carries. The envelope schema
([`inbox-envelope.md`](inbox-envelope.md)) owns the message FORMAT and its header; this document owns
the `landing` payload BODY — what a landing must carry so the orchestrator can drain the run's facts
instead of re-reading them from an operator paste.

It is the shared contract of three sites: `phase-6-finalize/standards/emit-landing.md` PRODUCES the
payload, `_orchestrator_inbox.check_landing_completeness` VALIDATES it, and
`plan-orchestrator/workflow/analyze.md` DRAINS it. When those three disagree, this document wins.

## Why a spec, and why a delta

A plan reports its outcome to two audiences over two channels — the operator report
([`../../phase-6-finalize/standards/output-template.md`](../../phase-6-finalize/standards/output-template.md))
and the epic inbox landing. The report renders from each finalize step's one-line `display_detail`
PROSE (`output-template.md` § "The renderer is a pure assembler"); the typed per-step `facts` map that
`manage-status --fact` records is discarded at that render boundary. The landing, historically, carried
free narrative. So the two channels carried DIFFERENT facts, and the operator paste kept surfacing
things the drained inbox never saw.

The payload specification is the **set difference** between what the report render schema exposes and
what the inbox envelope carried — derived below, classified item by item into MECHANISABLE (routable as
a typed fact) or NARRATIVE-ONLY (irreducibly prose). The mechanisable set is what the landing routes as
typed `key=value` facts — a proper superset of the REQUIRED set, since some of those facts ride optional
keys (see the note under the delta table); the narrative-only set is what the landing carries as prose
residue and what correctly keeps a manual channel.

> **Scope of the derivation.** The archived plans, run reports, and drained messages that would let this
> delta be measured empirically "over three archived plans" live under `.plan/` and are **absent from a
> fresh clone** — the delta here is derived from the report render schema and the inbox envelope schema,
> with the seven known report-only findings below as the non-empty control. The empirical sample was not
> taken and is not claimed.

## The report↔inbox delta

What the report render schema exposes that the historical narrative landing did not — and the direction
of each:

| Report exposes | Inbox (historical) | Classification | Routed as |
|---|---|---|---|
| PR number + merge/landing state (headline token `MERGED`/`OPEN`/…) | narrative "the PR reference" | MECHANISABLE | `pr`, `merge_state` |
| Deliverables `N_done/N_total` + titles | narrative "what shipped" | MECHANISABLE | `deliverables_total`, `deliverables_done` |
| Per-step outcome + `display_detail` for every finalize step, in composed order | absent | MECHANISABLE | **required** `steps`, which carries the per-step `{step}:{outcome}` pairs ONLY (split each element on its LAST colon — a namespaced step id contains one; [`../workflow/analyze.md`](../workflow/analyze.md) § Step 4 is where the drain applies it); each step's typed `facts` ride the **optional** `step.{name}.{fact_key}` keys |
| Token totals + wall-clock (`record-metrics`) | absent | MECHANISABLE | **required** `total_tokens`; the wall-clock rides the **optional** `total_wall_seconds` |
| Repository end-state (main up-to-date, worktree removed, tree clean) | absent | MECHANISABLE | the **optional** `step.branch-cleanup.{fact_key}` typed-fact keys; `steps` carries that step's outcome alone, not its end-state facts |
| Anomaly the operator noticed but no step recorded (a false-merge claim, a bot withdrawal) | narrative | NARRATIVE-ONLY | prose `## Residue` section |

> **MECHANISABLE does not mean required.** Every row above is routable as a typed fact, but the routing
> target may be an OPTIONAL key: the required set is exactly the table in § "Required machine-readable
> fact keys", which is what `check_landing_completeness` enforces. So a landing can be COMPLETE while
> carrying no per-step typed facts, no wall-clock, and no repository end-state — those rows are
> mechanisable and optional, and a landing that omits them has still satisfied the check. Promoting them
> to required would change what a conforming producer must emit and make every landing written before the
> change incomplete; the spec deliberately does not do that.

The reverse direction — what the inbox carries that the report does not — is the landing narrative
headline itself ("what landed"), which the operator report never emits because it addresses a different
audience. That asymmetry is not a defect to close; it is why two channels exist.

## The seven known report-only findings (the control)

Each existed ONLY in an operator paste, never in the drained inbox. A derived delta that lacks them is
measuring the wrong thing. Classification is the point — not every report-only fact is mechanisable, and
forcing one that is not into a fact is its own defect:

| # | Finding | Classification | Rationale |
|---|---|---|---|
| 1 | A fourth token total 3.4% from the others | MECHANISABLE | Token totals ride `total_tokens` with a named population; the disagreement is visible once every total is carried with its population rather than as one prose number. |
| 2 | A housekeeping step reporting `0 removed, 0 promoted, 0 adapted, 180 retained` on a run whose own log declared its input unavailable | MECHANISABLE (producer-gap) | The counts are a per-step fact; the "input unavailable" is a `work_performed`-shaped fact. Routable AS SOON AS the producing step (`project:finalize-step-lessons-housekeeping`) records those as `--fact`. Until it does, the landing carries the step's `outcome`+`display_detail` and the gap is named as residue. Recorded as residue, not silently dropped. |
| 3 | The RUNTIME step order rather than the order the merged tree shows | MECHANISABLE | The composed `phase_6.steps` order and each step's `outcome` ride `steps` in composed order, so the drain reads the order the manifest declares rather than a re-narrated one. |
| 4 | A merge call returning `merged: true` on an unmerged branch | **NARRATIVE-ONLY** | ⛔ The false-merge was caught by the operator reading the PR against the claim — it arrived as operator narrative, not as a step fact, and no finalize step recorded a contradicting fact. Forcing it into a `merge_state` fact would fabricate a signal the run did not produce. The landing carries `merge_state` as the step's OWN claim; a contradiction of that claim stays operator narrative and correctly keeps a manual check. This is the control item the plan flags as "may not be mechanisable at all." |
| 5 | A total that exposed a three-way disagreement | MECHANISABLE | Same mechanism as #1 — each total carried with its population makes the disagreement drainable. |
| 6 | A split guard never evaluated | MECHANISABLE (producer-gap) | "Guard not evaluated" is a `work_performed=false`-shaped fact on the owning step. Routable once that step records it; until then the landing carries the step `outcome` and names the gap as residue. |
| 7 | A review-bot withdrawal | **NARRATIVE-ONLY** | A bot withdrawing mid-review is a runtime observation the operator surfaced, not a deterministic step fact — `automatic-review` records its own outcome, not a third party's withdrawal. Carried as residue. |

Two of the seven (#4, #7) are irreducibly narrative; the residue section and the manual paste are the
correct home for them, and the report below says so. The other five are mechanisable — two with a
producer-gap that the landing names rather than fabricating.

## Required machine-readable fact keys

The landing body carries a fenced block, opened by ` ```landing-facts ` and closed by ` ``` `, of
`key=value` lines (one per line, `parse_markdown_metadata` shape). It is the machine-readable payload
the drain consumes. These keys are **required** — a landing missing any of them is INCOMPLETE (see
[`check_landing_completeness`](../scripts/_orchestrator_inbox.py)):

| Key | Value | Source |
|-----|-------|--------|
| `schema` | `landing-facts/1` — the payload-version marker, fail-closed like `envelope_version` | constant |
| `plan_id` | The plan's id (the message `sender_id`) | run |
| `pr` | PR reference (`#NNN`) or `n/a` | `create-pr`'s `pr_number` fact |
| `merge_state` | The merge/landing state the step recorded (`merged` / `open` / `closed` / `unknown` / `n/a`) — the STEP'S claim, never a corroboration. `closed` is a PR the merge queue dequeued without merging; `unknown` is a PR whose state could not be read, and asserts only that nothing was observed. Neither collapses into `open` | `branch-cleanup`'s `merge_state` fact |
| `deliverables_total` | Total deliverable count from the solution outline | run |
| `deliverables_done` | Completed deliverable count | run |
| `total_tokens` | The run's token total (raw integer) | `record-metrics` facts |
| `steps` | Comma-joined `{step}:{outcome}` for every finalize step in composed order. **A consumer splits each element on its LAST colon**, never its first: a namespaced step id contains a colon itself (`project:finalize-step-plugin-doctor:done`, `plan-marshall:plan-retrospective:done`), so a first-colon split yields the bare namespace as the step and the rest as the outcome. The split is APPLIED by the one consumer of this key, [`../workflow/analyze.md`](../workflow/analyze.md) § Step 4, which carries the worked example — this row states the rule, that step is its mechanism | `manage-status read` phase_steps |

Optional keys a landing MAY carry (not required, so their absence is not incompleteness): `epic`,
`total_wall_seconds`, and any per-step typed fact transcribed as `step.{name}.{fact_key}={value}`.

**A degraded value is not a fact.** A degraded value comes in TWO classes, and they are rejected on
different terms because they assert different things.

The **answered-degraded** class is `n/a`. `emit-landing.md` sanctions writing it for a fact the run has
no value for — no PR was ever created, the step legitimately did not run — so it asserts an ABSENCE THE
RUN OBSERVED. For `pr` and `merge_state` that IS an answer — "no PR exists" is a real end state, which
is why both rows above name `n/a` as a legal value. For the remaining required keys — `plan_id`,
`deliverables_total`, `deliverables_done`, `total_tokens`, `steps` — it is not: each names something a
landed plan always has, so an absence there is a producer gap, not an answer.
`check_landing_completeness` treats those as MISSING and names them, so a landing whose token total,
step list and deliverable counts all degraded is INCOMPLETE rather than silently accepted.

The **could-not-read** class is `unknown` — the value the `merge_state` row above defines as a state that
could not be read, asserting only that nothing was observed. `emit-landing.md` routes EVERY failed read
here, at every key: a value the producer could not read is written as `unknown`, never as `n/a`. It is
therefore a GAP AT EVERY REQUIRED KEY, with no carve-out: `merge_state=unknown` is INCOMPLETE exactly as
`total_tokens=unknown` is, and `pr` is no exception either. The carve-out above belongs to the answered
class ALONE. The asymmetry is the reason
the two are separate vocabularies rather than one list: `merge_state=n/a` must stay an answer while
`merge_state=unknown` must read as a gap, and a single per-key allow-list cannot express both — widening
the allow-list to cover `merge_state` would reject the legitimate `n/a` alongside the failed read.

The two classes therefore split by CONDITION, not by key. Routing a failed read to `n/a` is the
false-completeness defect this split closes: `n/a` is exempt at `pr` and `merge_state`, so a merge state
nobody managed to read would drain as a settled "no PR exists".

`schema` needs no such rule for either class: any value other than
`landing-facts/1` is already fail-closed by the stricter check below.

The block is **schema-versioned and fail-closed**: a block whose `schema` is not `landing-facts/1` is
treated as INCOMPLETE, mirroring the envelope's `unknown_envelope_version` posture — a forward-compatible
reader never best-effort-accepts an unrecognised payload version.

## The narrative residue section

Below the fenced block, the landing MAY carry a `## Residue` markdown section for the NARRATIVE-ONLY
class — the anomalies the operator would otherwise paste (a contradicted merge claim, a review-bot
withdrawal, a producer-gap the run could not mechanise). This section is prose by design; it is not
validated by the completeness check, and it is where the irreducibly-narrative half of the delta rides.
Its presence is what lets the report state honestly whether the manual paste is retired: the mechanisable
delta is drained as facts, and only the residue class keeps a manual channel.

## Related

- [`inbox-envelope.md`](inbox-envelope.md) — the envelope schema, header fields, and the `landing` kind
- [`../../phase-6-finalize/standards/emit-landing.md`](../../phase-6-finalize/standards/emit-landing.md) — the terminal step that produces this payload
- [`../workflow/analyze.md`](../workflow/analyze.md) — the drain that consumes it and runs the completeness check
- [`../../phase-6-finalize/standards/output-template.md`](../../phase-6-finalize/standards/output-template.md) — the operator report render schema this delta is derived against
