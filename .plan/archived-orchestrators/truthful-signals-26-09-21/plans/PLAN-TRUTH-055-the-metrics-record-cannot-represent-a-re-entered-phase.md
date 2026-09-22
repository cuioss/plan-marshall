# PLAN-TRUTH-055: the metrics record cannot represent a re-entered phase — impossible rows, certified complete, over slots nobody writes

epic: truthful-signals
workstream: WS-01

⭐⭐ **CORPUS-CRITICAL.** This is the plan that decides whether **any** archived per-phase figure is
usable. `PLAN-TRUTH-035` shipped the *labelling*; this is the *record shape underneath it*.

## Objective

A phase row that is entered more than once **accumulates some fields and replaces others**, producing a
row that cannot be true — and the completeness signal certifies it as complete.

## OBSERVED — first-party from PLAN-TRUTH-035's own `work/metrics.toon` (`-009`)

```toon
[5-execute]
  start_time: 2026-08-03T09:22:33Z
  end_time:   2026-08-03T10:00:14Z     # span = 37m41s
  duration_seconds: 41973.0            # 11h39m
  close_count: 3
  agent_duration_ms: 0
  agent_duration_seconds: 0.0
  total_tokens: 1961416
  tool_uses: 0
```

**Three mutually inconsistent facts in one row:**

1. ⛔ **~2M dispatched tokens in ZERO tool uses over ZERO milliseconds.** The previously-rendered
   `metrics.md` (generated between close 2 and close 3) shows `tool_uses: 753` and
   `total_tokens: 1,923,639` for the same phase ⇒ across the third close **`total_tokens` ACCUMULATED
   (+37,777) while `tool_uses` and `agent_duration_ms` were REPLACED with the closing call's zeros.**
   ⭐ **Mixed accumulate/replace semantics in one write.**
2. **`duration_seconds` (a sum across all three closes) sits beside `start_time`/`end_time` (the LAST
   close only)** — two different quantities in one row, **with no field distinguishing them.**
3. ⛔⛔ **`metrics.md` rendered `5-execute` as `Start: 09:22:33Z`, `End: 07:05:28Z`** — **a phase that
   ends 2h17m before it starts.**

### The guard certifies it

`metrics.toon` states `partial: false`, `unrecorded_phases:` empty. The partiality contract keys a
phase's *recorded* status **solely off the presence of an `end_time`** — which a re-entered phase has.

⇒ ⭐⭐ **The epic archetype in its purest form: the signal is real, correctly implemented against its
stated rule, and answers a NARROWER question than the one a reader takes it to answer.**
`partial: false` means *"every phase has a closing marker"*; it is read as *"these numbers are true."*

## ⛔ Second defect, same surface: four columns nobody writes (`-010`)

`record-dispatch-boundary` accepts and persists `input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens` — documented as *"the per-DISPATCH counterpart
to the per-PHASE four-field view"*.

**Across this plan's three ledgers — `4-plan` (1 row), `5-execute` (5), `6-finalize` (13) — all four
columns are `0` on all 19 rows.** Not sparse: **uniformly zero.** Every producer call site omits the
flags, so they default to `0` and persist **as though measured**.

⇒ **Zero is indistinguishable from unmeasured**, and `cache_read: 0` is *impossible* for a dispatch that
consumed 541,951 tokens. ⭐⭐ **This matters more than an ordinary empty column because CONTEXT LOAD IS
WHERE THE COST IS** — a byte costs 1.25× on entry and 0.1× every later turn, `cache_read` dominates
billing, and **these four columns are the only per-dispatch view of it.** The roadmap's central claim has
no per-dispatch instrument.

⭐ **A schema slot is not a measurement.**

## ⛔ Third defect, same family: an eventful gate records as clean (`-012`)

`pre-submission-self-review` fired **five times**; iterations 3, 4 and 5 each found a real defect. What
survives in structured state is **one row**:

```toon
pre-submission-self-review:
  outcome: done
  display_detail: "self-review clean: 204 candidates examined, no check matched"
```

`mark-step-done` **overwrites** the step record on each call ⇒ **last-write-wins, and the terminal
outcome replaces the history.** Every structured consumer — retrospective, audit, preference emitter,
human — sees a gate that passed cleanly on what looks like one pass. The three defect-finding firings
exist only as free-text work-log lines **no structured consumer reads**.

⚠ **And `204 candidates examined` is a VOLUME, not a coverage figure** — the standing
volume-read-as-coverage archetype, with this plan's own history as proof the distinction was
load-bearing: four of five passes examined many candidates and still missed a cascade site.

## ⛔⛔ CONSEQUENCE FOR OUR OWN CORPUS — strike 4, and it subsumes strikes 1–2

Our n=47 reads exactly these fields. The mechanism is **no longer "rows are missing"** — it is that
**re-entered rows are arithmetically impossible**, and `close_count > 1` is the norm, not the exception
(`PLAN-CIS-028` reported 13 self-review loops on one plan; a multi-loop-back run is the normal shape).

✅ **What survives, and only this**: the **billing composition** (`cache_read` ≈76% / `output` ≈1%) is a
ratio over components a corrupted row distorts together. **"99% of cost is context" holds.**
⛔ **Every per-phase figure is retired as evidence until re-derived.**

## ⛔⛔ FOLDED 2026-08-03 — `PLAN-TRUTH-035` SHIPPED AND LEFT A RESIDUE: the aggregate is RENDER-TIME ONLY

Probed by `code-intelligence-substrate` on an independent plan's store:

✅ `work/metrics.toon` **is** the machine authority and persists `billing_weighted_total`,
`dispatch_boundary_total`, `dispatch_boundary_rows_recorded`, the four-field counts and the byte
categories — **so a recompute IS script-derivable**, and their recompute matched the file's own
published per-phase sum **to one token**.

⛔ **Three sharp exceptions:**

1. **The aggregate `Total` and its `(n=5/6)` population qualifier are RENDER-TIME ONLY.** The TOON
   header carries no aggregate. ⇒ **The headline figure and its population exist only in prose**, and
   any script must re-derive both — **possibly choosing a different population than the renderer did.**
   ⭐⭐ **Two producers of one number, one of them unpersisted** — `PLAN-TRUTH-049`'s shape landing on
   the exact figure `TRUTH-035` existed to make honest.
2. **`inline_main_context_tokens` is sparsely persisted — 1 of 6 phase blocks.** ⇒ the **3.45× gap**
   between the headline `Total` (4,157,033) and the summed inline figure (14,328,428) **is not
   reconstructible from that plan's store.**
3. **The disambiguating caveats are render-only** (*"excludes cache_read"*, *"not preferred — smaller
   than…"*, *"Start is the latest entry only"*). **They carry the semantics that make the numbers safe,
   and a script reading the TOON gets the values WITHOUT them.**

> ⛔⛔ **A renderer that computes a figure it does not persist has produced a number nobody can check.**

⇒ **This plan gains the LABELLING half**: *which population a Total names must be a **FIELD**, not a
sentence.* ⚠ **`code-intelligence-substrate` staged the persistence half (`PLAN-CIS-022`) and offered to
cut it if we would rather own both.** ⛔ **Answer them before implementing** — two plans writing the same
fields is the defect both epics keep filing.

✅ **And the good news, verified on a plan we never saw**: `TRUTH-035`'s labelling **works** —
`(n=5/6)` is correctly attached to **Worked** and **Tool Uses** (the two columns `1-init` genuinely
lacks) and correctly **absent** from Tokens, which is complete. Phase tokens sum exactly to the
published Total; tool uses sum exactly to 1,106. **Verified, not assumed.**

## Deliverables

1. **D0 — GATE: derive the per-field write semantics of a phase-row close.** For **every** field:
   accumulate, replace, or last-write-wins? ⛔ **The mixed semantics are the defect — an inventory is the
   only way to see it**, and there is no document stating them today. ⚠ Include `mark-step-done`'s step
   records in the same sweep: `-012` is the same shape at a different granularity.
2. **D1 — a re-entered phase must be representable.** Either per-close records with derived aggregates,
   or explicitly-named cumulative-vs-last-close fields. ⛔ **`duration_seconds` and
   `end_time − start_time` must never again be two different quantities under one row with nothing
   saying so.** ⭐ **Load-bearing.**
3. **D2 — the completeness signal must answer the question readers ask, or say that it does not.**
   `partial: false` currently means *"every phase has a closing marker."* Either widen it to an internal
   consistency check, or **rename it so its narrowness is visible at the point of use.** ⛔ **A test that
   FAILS on the live `5-execute` fixture is required** — tokens>0 with tool_uses==0, and
   `duration_seconds` inconsistent with the stored span.
4. **D3 — an unwritten column must not persist as `0`.** Either the producers pass the four context-load
   values, or the columns are **absent** rather than zero. ⭐ **Prefer making them measurable** — this is
   the only per-dispatch view of the cost the roadmap targets. ⛔ **If they cannot be measured, remove
   them**; a permanently-zero column documented as a measurement is worse than no column.
5. **D4 — a step record must not lose its history.** An eventful gate and a first-pass-clean one must be
   distinguishable in structured state. ⚠ **Do not solve this by appending prose** — that is
   `PLAN-TRUTH-031`'s defect returning.
6. **D5 — tests, each verified to FAIL pre-fix.** (a) the impossible-row fixture; (b) a re-entered phase
   round-trips both cumulative and last-close quantities; (c) an unwritten context-load column is absent,
   not `0`; (d) a five-firing gate's record shows more than the last firing; (e) the D0 semantics
   inventory is asserted non-empty and complete over the row schema.

⚠ Six deliverables, at the threshold. **D4 is the split point** (`manage-status`, a different store).
Kept because D0's semantics sweep covers both and the failure mode is identical — **splitting would run
the same inventory twice.** ⭐ Rationale recorded at staging.

## Claim Labels

- **OBSERVED (plan-reported, first-party, quoting its own `work/metrics.toon` and both renderings of
  `metrics.md`)**: every figure above, the 19 uniformly-zero rows, the five firings against one row.
- ⚠ **NOT independently re-derived by this orchestrator.** ⭐ **The archive is on disk at
  `.plan/local/archived-plans/2026-08-03-token-total…` — re-read it at D0**, and it is also the
  ready-made fixture for D5(a).
- **HYPOTHESIS**: mixed accumulate/replace is the complete mechanism. ⚠ Inferred from **one** re-entered
  phase in **one** plan. ⛔ **D0 must derive it per-field from the code, not from this row** — the row
  shows *that* semantics differ, not *which* fields differ.
- ⛔ **NOT ESTABLISHED**: how many archived plans carry impossible rows. **The corpus-wide blast radius
  is unquantified**, and D0 should say whether it is knowable at all. ⚠ **Do not report a corpus-wide
  figure until it is.**

## Expected Surface

- **OBSERVED**: `manage-metrics/scripts/manage-metrics.py` — phase-row close, `record-dispatch-boundary`, `cmd_generate`
- **OBSERVED**: `manage-metrics/standards/data-format.md` — the partiality contract and the four-field view
- **HYPOTHESIS**: `manage-status` — `mark-step-done` step records (D4)

## Dependencies and Sequencing

- ⚠ **Directly downstream of `PLAN-TRUTH-035` (SHIPPED #1083)** — **read its landing first**; this plan
  fixes the record shape its labelling sits on. ⛔ **Do not re-derive 035's discriminator semantics.**
- ⛔ **Gates the corpus work**: `PLAN-CIS-030` (L3) cannot re-derive per-phase shares over a store that
  cannot represent a re-entered phase. **Notify CIS — this is a precondition of their plan.**
- ⚠ Surface-adjacent to `PLAN-TRUTH-053` (yield denominator, same renderer) and `PLAN-TRUTH-027`
  (build-time oracle). **SERIALIZE.**
- ⚠ `PLAN-TRUTH-050` owns the finalize ORDERING that makes the retrospective read this store early.
  **Different defect, same symptom surface — cite, do not merge.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-055-the-metrics-record-cannot-represent-a-re-entered-phase.md"
```

## ✅ CROSS-EPIC ORDERING DECIDED 2026-08-08 — this plan lands FIRST and supplies the vocabulary

From `code-intelligence-substrate-023` § 1, answering our `-040`. CIS **declined the reverse
order and gave the reason rather than mere assent**:

- **Vocabulary before slot is the safer direction.** If `PLAN-CIS-022` landed first it would
  write a field whose permitted values are still unsettled, and the only way to populate it
  would be to **invent an enum** — the precise *"neither of us invents a second population
  enum"* failure both epics agreed to avoid. With `TRUTH-055` first, their deliverable writes
  into a vocabulary that already exists and there is nothing to reconcile.
- ⇒ **`CIS-022` is now a CONSUMER of this plan's vocabulary, not a co-author of it.** The
  labelling half stays here; the persistence half stays there.
- ⛔ **ONE OBLIGATION BACK**: if this plan changes shape such that it **no longer supplies a
  population vocabulary**, CIS must be told **before it lands** — that is the single event that
  re-opens the question. Emit an inbox message to `code-intelligence-substrate` if D-scope moves.
- ⚠ It is also a precondition of `PLAN-CIS-030` (the L3 measurement plan), which CIS has agreed
  not to schedule ahead of it. **Two CIS plans are waiting on this one.**

## ⚠ SEQUENCING ADDED 2026-08-08 — `PLAN-TRUTH-066` follows this plan on `manage-metrics`

`PLAN-TRUTH-066` (the retrospective reads a record that is not yet written) touches
`manage-metrics` for its ledger-reconciliation and regenerate-after-loop-back deliverables.
**Serialize: this plan first, 066 after.** Do not pair them.

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -053

**Component:** `manage-metrics (the record and its denominators)` · **Deliverables after merge: 11** (raised cap is 12).

The `manage-metrics` chain, collapsed from three plans to two. `-055` and `-053` are one plan's worth
of work on one renderer.

- **`-055`** — a re-entered phase row accumulates some fields and replaces others, producing rows that
  cannot be true (`~2M` tokens with `tool_uses: 0`; a phase ending before it starts) all certified
  `partial: false`.
- **`-053`** — the record has numerators and no denominators, so it supports exactly one verdict:
  *"this got more expensive."*

⭐ **A denominator computed over a row model that cannot represent a re-entry is a ratio built on a
defect** — which is precisely why these could never have run in parallel, and why merging is better than
the serialization note they were carrying.

⛔ **Two `code-intelligence-substrate` plans wait on `-055`'s population vocabulary** (`CIS-022`
consumes it, `CIS-030`/L3 is gated on it). Merging does not change that obligation — **tell CIS if the
merged scope moves the vocabulary**, per the standing agreement.
⚠ `-053` is the SAME SURFACE as the shipped `-035`: **state the sampling point**, or it reproduces 035's
defect in a new field.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count deliverables at outline.** The figure above is the sum of the pre-merge counts; overlapping deliverables should COLLAPSE rather than concatenate, and a merged plan that still reads as two plans stapled together has not been merged.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
