# PLAN-CIS-020: Two retrospective report sections are structurally dead, and the emptiest one counts as cleanly written

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-30 from the PLAN-11 landing (#1063), inbox message
> `audit-report-path-ignores-plan-dir-011`.

## Objective

`retro_sections.py` declares the section registry shared by the producer (`collect-fragments`) and the
consumer (`compile-report`). Two rows are unreachable: **Executive Summary** cannot be registered at
all yet is counted in `sections_written`, and **Phase Dispatch Boundaries** can be registered but never
renders and is reported as a loud `sections_dropped`. Meanwhile `compile-report` ignores the
`status: skipped` case its own contract documents, so a benign omission is reported as a real loss.
Make the written / omitted / dropped partition mean what it says.

## Why this is ours

Evidence emission about our own runs — routing test 2. No PR/review surface.

## The probe is miscalibrated in BOTH directions at once

⭐ **This is the sharpest form of the epic's theme yet observed.** On the run carrying both fragments:

- `sections_written` included **Executive Summary** — a section whose entire body is
  `_No executive summary provided._`
- `sections_dropped` listed **Phase Dispatch Boundaries** (genuine content loss: 3 phases reporting
  `present: true`, 15 rows totalling 2.2 M tokens) **and Permission Prompt Analysis** (a harmless
  zero-result aspect whose fragment carried `status: skipped`).

⛔ **The one signal that fired loudly was the only one with nothing behind it, while an entirely empty
headline section passed as clean.** A three-valued outcome in which every bucket holds the wrong thing
is worse than a two-valued one, because it reads as precision.

## ⛔⛔ RE-GROUNDED 2026-08-08 — HALF THIS PLAN HAS ALREADY SHIPPED. READ BEFORE SCOPING ANYTHING.

**The deliverables below were authored against a tree that has since moved.** The orchestrator
re-verified every one against the implementing source at the 2026-08-08 queue reconciliation.
⛔ **Do NOT scope from the Deliverables section without this table.** Where the two disagree, **this
table wins** — it was read from the code; the list below was written from a run.

| D | Verdict | Evidence read first-party |
|---|---|---|
| **D1** | ⛔ **PREMISE REFUTED — but a sharper defect survives** | *"Executive Summary cannot be registered at all"* is **false**: `compile-report.py:313-317` accepts a `_executive-summary` fragment (dict-with-`summary` or bare string) and uses it verbatim, and `retro_sections.py:85` documents underscore-prefixed keys as registerable. **The remedy D1 asked for is already in the tree.** ⭐ **What survives is worse and more precise**: `compile-report.py:319` falls back to the literal `_No executive summary provided._`, and `:324` appends the heading to `written` **unconditionally** — so the placeholder is still counted as a written section. ⇒ **D1 is no longer "make it registerable"; it is "stop counting a placeholder as written", which is D4's invariant violated by the compiler itself.** **MERGE D1 INTO D4.** |
| **D2** | ⚠ **HALF SHIPPED** | The render path is **done**: `render_dispatch_boundaries_body` (`compile-report.py:192`), dispatched at `:340-341`, with a registry row carrying its trigger (`retro_sections.py`). ⛔ **The SKILL.md half is still OPEN** — `dispatch_boundaries` appears **nowhere** in `plan-retrospective/SKILL.md`. ⇒ **D2 reduces to the SKILL.md Step 3 registration, which is the SAME edit as D7.** **MERGE D2's residue INTO D7.** |
| **D3** | ✅ **SHIPPED** | `_fragment_has_payload` (`compile-report.py:164-189`) treats `status` and `aspect` as envelope metadata and never counts them as payload, so a `status: skipped` fragment with no other content returns `False` → **omission, not drop** — exactly what D3 asked for. ⭐ It also went further than asked, matching `False` **by identity** so a numeric `0`/`0.0` payload is not misclassified. **DROP D3.** |
| **D4** | ⚠ **MECHANISM SHIPPED, TEST STILL OWED — and now it has a known failing case** | The three-way partition is implemented (`compile-report.py:326-336`) with the drop-vs-omit discriminator. ⛔ **The invariant assertion is NOT in the tree**, and D1's residual is a **live violation of it**: an unconditional `written.append` for a placeholder section. ⇒ **D4 is the plan's centre of gravity, not a trailing assertion.** |
| **D5** | ✅ **STILL OPEN** | Registry-row reachability census; unaffected by the shipped work. Note the population is now *smaller* in effect — two of its known dead rows are alive. |
| **D6** | ⚠ **RE-BASELINE** | (b) *"a registered `dispatch_boundaries` fragment renders"* and (c) *"a `status: skipped` fragment is omitted, not dropped"* **PASS against current code** — they can no longer be *"verified to FAIL pre-fix"*, which this epic requires. ⛔ **Do not ship them as if they were regression proofs**; either drop them or re-state them as characterization tests pinning shipped behaviour, and say which. (a) still fails today and remains a genuine regression test. |
| **D7** | ✅ **STILL OPEN, AND CONFIRMED** | The canonical registry keys appear nowhere in `SKILL.md` — corroborated by the same grep that found `dispatch_boundaries` absent. **Now absorbs D2's residue.** |

⇒ ✅ **THE SPLIT-GUARD BREACH IS RESOLVED BY ARITHMETIC, NOT BY A SPLIT.** Seven deliverables become
**four**: D1+D4 merge (partition invariant, with the placeholder as its failing case), D2+D7 merge
(SKILL.md registration), D5 stands, D6 re-baselines. ⛔ **The "proceeding unsplit is deliberate"
rationale below is SUPERSEDED and must not be cited** — the plan is now comfortably under the guard.

⭐ **THIS IS THE THIRD OBSOLETE-SPEC FINDING OF ONE RECONCILIATION** (with `PLAN-CIS-008`, retired in
full, and `PLAN-CIS-015`'s struck D5). ⛔ **The systemic finding is not about this plan**: staged specs
decay against a moving tree and nothing re-grounds them, so a spec's age is a silent correctness risk.
See lesson `2026-07-29-19-001` in `PLAN-CIS-015`.

## Deliverables

⚠ **Read the re-grounding table above first — D1/D2/D3/D6 below are superseded in whole or in part.**

1. **D1 — Executive Summary: give it a registerable key, or delete the row.** Its docstring claims it
   is "injected directly by the orchestrator and never flows through collect-fragments add", but **no
   such injection path exists** — the bundle is created and mutated solely by
   `collect-fragments init / add / finalize`. A section that cannot be populated must not be emitted.
2. **D2 — fix the `dispatch_boundaries` render path** and add the aspect to the `SKILL.md` Step 3
   aspect table. ⭐ The underlying data is **already collected** inside the `log-analysis` fragment —
   it is gathered and then thrown away, so this is a wiring fix, not a new measurement.
3. **D3 — make `_fragment_has_payload` honour `status: skipped`** per the compiler's own documented
   conditional rule, so a benign skip becomes an *omission* and `sections_dropped` regains its meaning
   as a real loss signal.
4. **D4 — assert the partition invariant.** "Written" must imply non-empty. A written/omitted/dropped
   partition is only useful under that invariant; pin it with a test rather than a convention.
5. **D5 — GATE: derive the population of registry rows against their reachability.** ⚠ Two dead rows
   were found by one run — **standing rule 4: that is a SAMPLE.** Check every row in the registry for
   (a) registerability and (b) a live render path, and report the dead count separately from the
   number examined.
6. **D6 — tests, each verified to FAIL pre-fix.** (a) A report with no executive-summary content does
   not list it under `sections_written`. (b) A registered `dispatch_boundaries` fragment renders.
   (c) A `status: skipped` fragment is reported as omitted, not dropped.

7. **D7 — the document that instructs a registration must supply the exact argument** (folded
   2026-08-02 from `truthful-signals-026` item 6). `plan-retrospective` SKILL.md Step 3 names aspects
   in **prose** ("Invariant outcomes"), while `collect-fragments --aspect` validates against the
   **closed registry** (`invariant-summary`, …). ⛔ **The canonical keys appear nowhere in SKILL.md**,
   so **3 of 5 registrations were rejected on first attempt.** Add a `registry key` column to the
   Step 3 aspect table. ⭐ This is the same registry D1–D5 are repairing, approached from the
   *authoring* side rather than the *rendering* side — a caller who cannot name a row correctly
   produces the same missing section as a row that cannot render.

Seven deliverables — **past the split guard, and the rationale is recorded here as the standard
requires.** Proceeding unsplit is deliberate: D1–D4 are all one-file corrections to a single partition
contract, D5/D6 are small, and D7 (added 2026-08-02) is a single table column in the SKILL.md the same
registry already backs — it does not open a second surface. ⚠ **Re-evaluate the split at outline**: if
D5 finds a materially larger dead population, **split the sweep out and re-stage** rather than growing
this plan further.

## Claim Labels

- **OBSERVED** (first-party, quoted from source): `retro_sections.py` declares
  `('Executive Summary', '_executive-summary', None)` and
  `('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries')`.
- **OBSERVED**: `valid_aspect_keys()` excludes underscore-prefixed keys and `cmd_add` rejects them;
  attempting registration returns `error: Unregistered aspect key: 'executive-summary'`.
- **OBSERVED** (derived count, first-party): `dispatch_boundaries` is the **sole** underscored key
  among **16** hyphenated ones. ⚠ This count is the message's; re-derive it from the registry at
  outline rather than quoting it.
- **OBSERVED**: `report-structure.md` § Conditional Rule states that a fragment which is absent, has
  `status: skipped`, or carries only an empty list must be omitted and reported under
  `sections_omitted` — and the compiler does not honour it.
- **HYPOTHESIS**: **no orchestrator injection path for the executive summary exists anywhere** —
  confirm/refute by enumerating every writer of the fragment bundle, at `collect-fragments`
  (verify-at-outline). ⛔ **This is an asserted ABSENCE and carries the higher risk**: if an injection
  path does exist, D1's remedy inverts from "delete the row" to "document and wire the path". The
  epic's verify-first contract requires an absence to be verified exactly like a presence.
- **HYPOTHESIS**: `_fragment_has_payload` is the specific symbol that ignores `status: skipped` —
  confirm/refute at that symbol (verify-at-outline).
- **HYPOTHESIS**: the 2.2 M-token / 15-row `dispatch_boundaries` payload is representative rather than
  particular to that run — confirm/refute on a second plan's fragment (verify-at-outline). Not
  load-bearing for the fix; it sizes the loss.
- **Verify-first clause**: settle the absence hypothesis against the **implementing source** — the
  bundle writers — before scoping D1. The docstring asserting an injection path is exactly the kind of
  self-restating prose the verify-first contract excludes as evidence.

## Expected Surface

- OBSERVED: `retro_sections.py` — the section registry, `valid_aspect_keys()`
- OBSERVED: the `compile-report` implementation — `_fragment_has_payload`, the
  written/omitted/dropped partition
- OBSERVED: `collect-fragments` — `cmd_add`, `init`, `finalize`
- OBSERVED: `plan-retrospective` `SKILL.md` Step 3 aspect table; `report-structure.md` §
  Conditional Rule

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: ⛔ **PLAN-CIS-012, PLAN-CIS-013 and PLAN-CIS-019** — all edit `plan-retrospective`.
  **Same bundle: sequence, never pair.** This is now a four-way serialization class within WS-04.
- Adjacent to: PLAN-CIS-009 (`documented-enum-diverges-from-argparse-choices`) — also a
  documented-surface-vs-code divergence, but in `manage-metrics`; stays untouched.

## ✅ Cross-epic ownership check — RESOLVED 2026-07-30, and the split is on both records

The mandatory pre-emit check this spec carried is **discharged**. `truthful-signals` settled it
unprompted in their inbound message `truthful-signals-019`, which drew the line themselves:

| Half | Owner | Substance |
|---|---|---|
| The **producerless row** — every per-dispatch context-load column (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) reading `0` on all 15 rows across three phases | ⛔ **`truthful-signals`** — they are keeping it and folding it onto their existing item | a confident zero where the honest value is "not captured" |
| The **render path** — `dispatch_boundaries` computed in full by `analyze-logs`, nested under `log-analysis`, and reported under `sections_omitted` because the trigger key is not a registerable aspect | ✅ **OURS — D2 and D5 below** | "a retrospective losing real payload through the channel that exists to say nothing was lost"; they explicitly did not claim it and offered it to us |

⇒ **D2 and D5 stand unchanged.** Do not drop the `dispatch_boundaries` arm.

⭐ **Their framing sharpens D2's acceptance criterion**, so adopt it verbatim: the payload is *already
computed* and is lost through **the bucket whose entire purpose is to say nothing was lost**. That is
strictly worse than a loud drop, and D3's `status: skipped` fix is what restores the distinction.

⚠ **A cross-epic clearance is a snapshot, not a state** — but this one is recorded in *their* outbound
message rather than inferred from silence, which is the strongest form available. No re-check owed
unless the scope of D2 widens.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-020-retrospective-report-sections-structurally-dead.md"
```

## Relation to the epic

The retrospective component is itself an instance of the archetype it exists to detect. That is not
irony worth noting once — it is the reason this plan is scoped at the *partition contract* rather than
at the two dead rows: a reporting surface that cannot represent "empty" correctly will keep generating
these.

## ⛔⛔ D8 — the retrospective DESTROYS ITS OWN PRIMARY INPUT (folded 2026-08-03, lesson `2026-08-03-14-003`)

**OBSERVED first-party on PLAN-CIS-001 / #1084**: the retrospective **overwrote
`status.metadata.session_id` with the auditor's own session id.** It was caught and restored by hand
before `enrich` ran; **left alone it would have corrupted the metrics for the plan being measured.**

⇒ ⭐ **This is worse than the dead sections this plan already owns, and it is why it belongs here
rather than in a new spec**: a dead section loses information that existed; **this one replaces the
key that identifies the run with the key of the process observing it.** The measurement overwrites
its own subject's identity.

⛔ **The near-miss is the finding, not the outcome.** It was caught only because a human happened to
look at the right field at the right moment — **nothing in the pipeline would have reported it**, and
the corrupted value is well-formed, so no downstream consumer would reject it.

**Deliverable**: the retrospective must write its own session identity to its **own** namespace and
must never write to the measured plan's `status.metadata`. Add an assertion that the plan's
`session_id` is unchanged across the retrospective step — **a comparison, not a validity check**, since
the corrupted value is perfectly valid.

⭐ **RECURRENCE + the actual root cause, folded 2026-08-03 from PR #1086 (`…-005` and `…-003`).**
Second sighting in two consecutive plans, which settles it as systematic. ⛔ **And `…-003` supplies
the reason the naive fix is wrong**: a plan can legitimately span **multiple sessions** (#1086's own
finalize halted on a usage limit and resumed), so `session_id` is **not a single value** — the field
is a scalar modelling a list, and *that* is why a second writer overwrites rather than appends.

⇒ **Record `session_ids` as a LIST so `enrich` can span a multi-session plan.** ⭐ This subsumes the
clobber fix rather than sitting beside it: with a list there is no single slot to clobber, and the
retrospective's own session becomes an **append**, which is what it was always trying to express.
⚠ **Do not ship the guard without the list** — an assertion that the scalar is unchanged would make a
legitimate multi-session resume fail.

## Evidence Fold — 2026-08-08, from `lessons-handling-26-08-08-01-004` (cluster C09)

⚠ **TWO OF THE THREE MEMBERS ARE ALREADY IN THIS SPEC.** `2026-07-27-08-005` (Executive Summary has no
producer and is always empty) is already D1; `2026-08-03-14-003` (retrospective capture overwrites the
plan's execution `session_id`) is already D8 with the session-list remedy. ⇒ **Corroboration from a
second source, NOT new scope — do not re-scope D1 or D8 on this message.**

### ⭐ NEW and different in kind — `2026-07-29-09-002` is a POSITIVE proposal, not a defect

**Record the signals that REFUSED TO LIE — the counterexample set is evidence too.** The retrospective
should record which signals were checked and *held*, not only which failed.

⛔ **Why this belongs in this plan specifically, rather than being filed as a nice-to-have.** Every
*"zero findings"* line this report emits carries the exact ambiguity this epic exists to kill:
**looked and found nothing** versus **could not look**. A counterexample set is the discriminator — it
is the same fix as the structurally-dead-section problem, applied to a section that renders rather than
one that does not. ⇒ **A section that reports zero must be able to name what it checked.** That is one
property, and it closes D1's empty-section class and this proposal together.

⚠ **Fold as a property of the section contract, not as a deliverable** — it is the same shape as D1's
"registerable key or delete the row" and should be settled there.

### ⛔ Sequencing — this plan can be fully correct and still read a destroyed input

`plan-retrospective` runs at finalize **after** branch-cleanup destroys its footprint input and **before**
sync-plugin-cache makes the plan's own fixes live. That ordering defect is routed to `truthful-signals`
as cluster C10 (`2026-07-28-19-005`), and it is **live in merged main** — this epic tracks the same
family as PLAN-CIS-034's R1/R2/R3. ⇒ ⛔ **If this plan fixes the report while the ordering stands, the
fixed sections will faithfully render a destroyed input** — a strictly worse outcome than an empty
section, because it looks authoritative. **Coordinate before either starts; do not treat this as a
finalize-time discovery.**

**Claim labels** — OBSERVED: lesson ids, categories, and the two-of-three overlap above (verified by
reading this spec). HYPOTHESIS (verify-at-outline): the finalize step ordering as stated. Confirm/refute
artifact: the run's own manifest or step log — ⛔ **never the `order:` values on post-merge main**, which
record what the plan INSTALLED rather than what it RAN (this epic's own recorded correction).

## ⭐ Name the canonical aspect key in each Step 3 table row (folded 2026-08-09 from inbox `executor-rejects-invalid-invocations-before-spawn-006`)

**OBSERVED first-party on PR #1127's retrospective.** A Step 3 table row names an aspect in prose
without naming the **canonical aspect key** the rest of the machinery addresses it by, so a reader
(or a script) reconciling a row against the aspect registry has to infer the mapping.

⭐ **This is small and it belongs here rather than in a new plan**: this plan already owns the
`compile-report` / `retro_sections` render path and the structurally-dead-section problem, and this
is the same defect one notch milder — **a section that renders but is not addressable.**

**Deliverable**: each Step 3 row carries its canonical aspect key alongside the prose label.
⛔ **Derive the key from the aspect registry, never restate it** — a hand-copied key in a table is
this epic's count-prose archetype wearing a different hat, and lesson `2026-08-09-13-001` says the
remedy for a restated claim is to point at the declaring source rather than to copy it correctly.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
