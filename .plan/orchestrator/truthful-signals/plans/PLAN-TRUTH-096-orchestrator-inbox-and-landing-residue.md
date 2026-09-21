> ⛔ **STAGED AT THE 2026-08-22 INGESTION — this plan closes REMEDIATION RESIDUE.**
>
> It exists because the gap-fix plans `500`/`510`/`520` ran **after** the epic audit closed, so every
> gap they filed, and every gap they left partially closed, is owned by no other staged plan. This was
> found by re-deriving ownership over the whole live gap set at ingestion: **218 gaps open, 38 unowned.**
>
> **Re-ground every gap below at HEAD before implementing it.** Its source is
> `cloud-runs/{NNN}-{slug}/gaps.md` in this ledger (git-ignored, ingested from `doc/plans/`), and a
> gap document is a snapshot. Line numbers in it are **leads, not addresses**; locate by quoted text.
> A gap that no longer reproduces is recorded as *already closed by `{sha}`* and **dropped, never
> re-fixed**.
>
> ⛔ **A run report is a dated record.** No deliverable here corrects one. Where a gap's `Where` names
> an archived `report-01.md`, the correction of record is the gap entry itself; only a live restatement
> is actionable, and it must be re-derived.

# The orchestrator inbox and landing surfaces carry counts that disagree with themselves

**Epic:** truthful-signals
**Branch prefix:** fix
**Source gaps:** `520/G1`–`G8` (`cloud-runs/520-orchestrator-inbox-lifecycle-cleanup-and-landing-payload/gaps.md`), plus `250/G4` for the epics this ledger does not own

## Problem

Plan `520` (PR #1317) closed 29 of 30 upstream gaps and verified the orchestrator group's highest
defect — `302/G1`, where `'n/a'` counted as a present fact — closed **by execution**. Its residue is a
tight cluster of self-disagreeing counts, and one of them has a live consequence.

`merge_state: unknown` — the value that means *could not be read* — still yields `complete: true` from
the landing-completeness check. That is the same defect as `302/G1` at a different key: a sanctioned
degraded value counted as a supplied fact.

`inbox-envelope.md` states two different in-place-edit counts **12 lines apart**, which is the residue
of upstream `250/G7`.

**And `250/G4` is only partly discharged.** The per-sender archive migration was run for this epic at
the 2026-08-22 ingestion — 582 messages into 49 sender directories, 0 flat remaining, re-run moves 0.
It has **never** run for `code-intelligence-substrate` (195 flat) or `review-apparatus` (136 flat).

## Goal

No landing reads complete on a fact that could not be read, and no inbox contract states a count that
contradicts itself.

## Deliverables

**D0 — GATE: re-derive the landing-completeness key classification.** For every required and optional
fact key, state whether each sanctioned degraded value counts as supplied, and why. Publish the table.
*(gates D1–D4.)*

**D1 — an unreadable `merge_state` is not a supplied fact.** *(closes 520/G7)*
Distinguish *degraded-but-answered* from *could-not-read* at every key, not only at the four already
rejecting sentinels. Pin with the same mutation shape that proved `302/G1`: dropping a key from the
rejecting set must turn a test RED.

**D2 — one in-place-edit count, stated once.** *(closes 520/G6; completes 250/G7)*
`inbox-envelope.md` must state the sanctioned in-place edits in exactly one place, with the sibling
clause deferring to it.

**D3 — pin `--workflow` at the three dispatch doc sites.** *(closes 520/G4)*
The fix that closes upstream `280/G7` at its two resolving sites is held by nothing but prose.

**D4 — derive the collateral and survivor lists at report time.** *(closes 520/G1, 520/G2, 520/G3, 520/G5)*
Four separate stale figures in one report are **one cause**: the review cycle widened the diff after the
counts were taken. Derive them last, and state the rule.

**D5 — run the per-sender archive migration for the two sibling epics.** *(closes 250/G4 in full)*
`orchestrator inbox migrate-archive --slug code-intelligence-substrate` and
`--slug review-apparatus`. ⚠ **This is an operator action on a machine holding the orchestrator store**
and is outside this epic's write boundary; the deliverable is to have it run and its per-sender counts
recorded, not for this epic to perform it unasked.

**D6 — correct the `_marker_indices` docstring return contract.** *(closes 520/G8)*

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- `test/plan-marshall/plan-orchestrator/test_landing_completeness.py`

## Out of scope

- Correcting any archived `report-01.md` under `cloud-runs/` — a run report is a dated record; see the
  banner. Where the same false claim is restated on a live surface, that restatement is in scope and
  must be re-derived rather than inherited from the gap's `Where` line.
- Any gap owned by another staged plan. Ownership was derived at ingestion; if a re-derivation shows
  an overlap, **record it and serialize**, do not silently absorb the sibling's gap.
- Re-fixing a gap that no longer reproduces at HEAD.

## Claim Labels

Every claim in this plan is **HYPOTHESIS** unless the deliverable marks it otherwise. The gap entries
it derives from were OBSERVED at their verification commit and re-checked at the 2026-08-22 ingestion,
but that check was per-gap and sampled, not exhaustive. **Treat every asserted absence as unverified
until the D0 gate re-derives it.**

## Verification

- The D0 gate publishes the population it examined **and** the count that reproduced, as two separate
  numbers. A zero must state which zero it is: *examined N, none reproduced* is a result; *could not
  look* is not.
- Every guard added or widened here is proved by a **matched positive/negative control** — a case that
  goes RED against the defect the guard names, and a near-identical case that stays green. A guard
  whose population can be empty publishes its population size on a clean run.
- No deliverable is reported complete on a read alone where the claim is about behaviour: execute the
  symbol, or mutate it and observe the red.

## Notes

**Derived figures are re-derived AFTER the review cycle closes, not before.** Both `500` and `520` had
their diff silently widened by CodeRabbit after their counts were taken, and `510`'s own participation
figure used a floating `origin/main` endpoint three sections after its own § Build gate corrects that
exact defect. The review is a diff-widening event. Take every count last.

## Folded from PLAN-TRUTH-074's drain (2026-08-22)

### F1 — `emit-landing` never fired, and the stated cause is only half of it (from inbox `-007`)

**The observable failure is corroborated.** PLAN-TRUTH-074's `manifest.phase_6.steps` was composed
2026-08-09 and carries **22 steps**; `emit-landing` (order 1000) is not among them, though it is
present in bundle source with `default_on: true` and presets `local, standard, full`. Its activation
predicate is presence in that persisted list, so it could not fire. `lessons-capture` (order 991) had
already been relocated so it no longer owns the landing — yet on that run it emitted one anyway, nine
slots early, which is exactly why the landing's token total was a **floor** and its last five step
outcomes read `pending` / `in_progress`. Had it not, the epic would have lost the plan's
machine-readable hand-off entirely, silently, behind a fully green finalize — and `archive-plan`
(order 1100) destroys the plan directory immediately after, so the facts would have been
unrecoverable.

⛔ **The root cause the message states is INCOMPLETE, and its proposed fix is unsafe as written.**
The message attributes the absence to manifest staleness alone — the step shipped after this manifest
was composed. But current `marshal.json` carries **`default:emit-landing: lane: off`**, so a manifest
composed **today** would also exclude it. These are two independent causes with different fixes:

| Cause | Fix shape |
|---|---|
| Manifest staleness — the step post-dates the composed list | Reconcile / warn at finalize entry |
| Lane exclusion — `lane: off` in live `marshal.json` | An operator/config decision, not a bug |

The message's remedy #1 — *"compare `manifest.phase_6.steps` against the live dispatch table's
`default_on: true` set and report additions as a WARNING"* — would, as written, fire a warning on a
step the operator has explicitly laned off, on every plan, forever. ⇒ **Settle which of the two is
intended BEFORE building the guard**, and make the guard read the lane, not just `default_on`.
(⭐ Note the shape: `lessons-capture` and `adr-propose` are *also* `lane: off` in live `marshal.json`
yet `lessons-capture` ran on this plan — because its manifest predates that setting. So the two
causes are already interleaved in one live ledger.)

⭐ **The generalisation is worth carrying regardless of which cause wins**, and it is this plan's own
subject: *an activation predicate read from a persisted artifact freezes the capability set at
compose time.* Any capability added after that artifact was written is unreachable for that
artifact's lifetime, and no runtime signal reports the absence — because **absence from a list is
indistinguishable from a deliberate opt-out.** Every guard in the area is a *presence* check against
the manifest, and the manifest is exactly the artifact that is stale. A green finalize proves the
composed steps ran; it does not prove the composed set is still the right set.

**A step relocation that moves an obligation from step A to a NEW step B is not complete when B is
added to the dispatch table.** Already-composed manifests still name A and not B, so the obligation is
dropped rather than moved. Either reconcile at finalize entry, or keep A emitting until no
un-composed manifest can exist.

### F2 — the `steps` key's grammar is ambiguous for namespaced step IDs (latent)

`landing-payload-spec.md` defines `steps` as comma-joined `{step}:{outcome}` and **states no split
rule**. 5 of PLAN-TRUTH-074's 22 step IDs contain a colon themselves (`project:finalize-step-*`,
`plan-marshall:plan-retrospective`), so a consumer splitting on the FIRST colon reads `project` as
the step name; splitting on the LAST is correct.

**Corroborated as a real ambiguity, and confirmed LATENT**: `inbox landing-check` only tests key
presence and never splits the value, so no current consumer is bitten. Fix the grammar in the spec
(state "split on the last colon", or switch to a delimiter that cannot occur in a step id) **before**
the first consumer parses it — this is cheap now and a silent mis-attribution later.

### F3 — the Expected-Surface parser is CASE-SENSITIVE, and it silently disarms the disjointness gate for 8 of 13 staged specs

⛔ **Found by the orchestrator during the 2026-08-22 emit, not drained from a message.** The
`resume-summary` / `corpus` surface reader matches the heading `## Expected Surface` **literally**.
Across this epic's staged corpus:

| Heading as written | Specs | Renders as |
|---|---|---|
| `## Expected Surface` (template form) | `-075`, `-094`, `-095`, `-096`, `-097` | the real path list |
| `## Expected surface` (lowercase `s`) | `-086` … `-093` — **8 specs** | `(no expected surface)` |

The 8 specs **do** declare their surface; it is simply never read. Per this epic's own apply-policy,
*"a spec with no Expected Surface is indistinguishable at the disjointness gate from **no candidate
qualified**"* — so the parser converts a fully-prepared spec into an unschedulable one, silently,
and the Ordered Queue table renders the false absence as though it were the spec's own omission.

⭐ **This SHARPENS the standing R8 correction rather than replacing it.** R8 attributes
`corpus cross-check`'s undercount to *path form* — "34 abbreviated/bare surface entries it cannot
resolve". That may hold independently, but it is not why these 8 are invisible: **their sections are
not being parsed at all.** Do not fix the path forms and conclude the gate is repaired.

**Two fixes, and they are not alternatives — take both:**

1. **Make the reader case-insensitive** (and ideally whitespace-tolerant) on the heading match. This
   is the durable fix and belongs to this plan.
2. **Normalise the 8 headings to the template's `## Expected Surface`.** This is corpus work under
   the `cleanup` verb's ambiguity apply-policy, NOT this plan's — `/plan-orchestrator cleanup
   slug=truthful-signals` owns it.

⛔ **Add a matched control**: a spec whose heading differs only in case must resolve to the SAME
surface list as its template-cased twin, and a spec that genuinely declares no surface must still
render `(no expected surface)`. Without the negative control the fix cannot distinguish "read it
correctly" from "stopped reporting absence at all".
