# PLAN-TRUTH-121: Producers report success over a write nothing can read

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-27 from the `PLAN-TRUTH-114` landing drain, messages `-001` and `-005`, joined with
epic defect **D-098-d** from the previous landing. Three producers, three components, one shape — and
the epic has now been bitten by all three in its own machinery within 48 hours.

## Objective

**A producer returns `success` for a write that stores nothing a consumer can read back.** This is the
WRITE-side complement of the epic's empty-population class (`PLAN-TRUTH-104`), and it is distinct:
there the *check* looked at nothing, here the *store* received nothing while the caller was told it
worked. ⛔ **The consumer-side symptom is indistinguishable from a genuine absence**, which is why every
one of these was found by accident rather than by a gate.

**Three members, each observed first-hand:**

1. **`manage-lessons add` returns success for a lesson with no body.** The allocation succeeds, the
   body never lands, and the record enumerates as `active` forever. ⭐⭐ **This is the PRODUCER of the
   title-only-stub population that degraded an entire lessons drain**: that drain reported **11
   title-only stubs in one 08-24→08-26 band**, and had to mark whole cluster memberships HYPOTHESIS
   because *"`add` allocated it, `set-body` never ran"*. **The read-side damage is measured; this is
   the write-side cause.**
2. **`record-step` writes placeholder zeros indistinguishable from a measured zero.** A zero that was
   never measured and a zero that was measured render identically to every downstream reader — the
   epic's canonical *which-zero-is-this* failure, in the step recorder itself.
3. **`record-metrics` records no typed facts (D-098-d).** Totals ride `display_detail` PROSE;
   `phase_steps` carries no `facts` sub-dict, so `total_tokens` / `total_wall_seconds` are unreadable
   from where the landing spec points. ⚠ **Partially closed by observation:** the `-114` landing DOES
   carry `total_billing_weighted`, so the missing-schema-key half is resolved; the no-typed-facts half
   is not.

## Deliverables

1. **D0 — GATE: derive the population, and settle whether these three share one remedy.** Sweep the
   producer surface for *a write path that can return success having stored nothing readable*. ⛔
   **Publish the swept population and its size.** ⚠ **Do NOT assume one fix serves three** — a
   required-body validation (member 1), a sentinel-vs-measured distinction (member 2), and a typed-facts
   emission (member 3) are three different remedies, and the router-style "they look alike" inference is
   exactly what this epic makes plans verify.
2. **D1 — `manage-lessons add` must not report success for an unreadable record.** Either require the
   body at allocation, or return a distinct non-success state naming the incomplete record. ⛔ **A
   two-call allocate-then-set-body flow is legitimate; what is not legitimate is the intermediate state
   enumerating as `active` and indistinguishable from a complete lesson.** ⭐ Consider a `pending_body`
   lifecycle so `list` can report the population honestly — the corpus already needs that read.
3. **D2 — `record-step`'s placeholder zeros become distinguishable from measured zeros.** Adopt the
   discriminator vocabulary the codebase already uses (`inbox list`'s `inbox_state`,
   `manage-lessons list-stalled`'s `store_resolution`) rather than inventing a third.
4. **D3 — `record-metrics` emits typed facts.** Route `total_tokens` / `total_wall_seconds` (and the
   now-carried `total_billing_weighted`) into `phase_steps.facts` where the landing spec points, so a
   landing reads them mechanically instead of by hand from the metrics store.
5. **D4 — matched controls, one per member.** Each must show the failing state is now REPORTED **and**
   that the healthy state still reports success unchanged. ⛔ **The negative control is load-bearing
   here**: a fix that makes every write suspect is as wrong as one that makes every write silent, and
   this epic has recorded a fix re-introducing its own target archetype at least twice.

## Claim Labels

- OBSERVED: `manage-lessons add` returns success for a body-less lesson — candidate-lesson `-001` of the `PLAN-TRUTH-114` drain, first-hand from that run
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-lessons.py docstring plus _allocate_and_write_scaffold(body='') confirm add still allocates a body-less lesson returning success
- OBSERVED: `record-step` writes placeholder zeros indistinguishable from measured zeros — candidate-lesson `-005`, same drain
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: FIXED at HEAD: cmd_record_step now uses _record_step_column with UNMEASURED_COLUMN_TOKEN, distinguishing an explicit 0 from an omitted value. Re-scoped: member 2 is closed.
- OBSERVED: the read-side damage from member 1 is MEASURED, not inferred — the `lessons-handling-26-08-26-01` drain reported 11 title-only stubs in a single 08-24→08-26 band and downgraded cluster memberships to HYPOTHESIS because of them
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Historical drain-report count (11 title-only stubs in the 08-24 to 08-26 band) not accessible from this checkout
- OBSERVED: `record-metrics` carried no `facts` sub-dict on the `PLAN-TRUTH-098` run (epic D-098-d), and the `PLAN-TRUTH-114` landing DOES carry `total_billing_weighted` — so the schema-key half is closed and the typed-facts half is not
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Historical run-specific facts (PLAN-TRUTH-098/-114 landings) not accessible; landing-payload-spec.md now formally routes total_tokens and total_wall_seconds as facts
- HYPOTHESIS: the three members share one remedy. ⛔ **This orchestrator's grouping by SHAPE, not a claim any lesson makes.** D0 settles it; splitting into three plans is a legitimate outcome (verify-at-outline)
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED: the three members are in materially different repair states (member 1 OPEN, member 2 FIXED, member 3 substantially addressed via landing-payload-spec.md), so they do not share one remedy. Re-scoped: the spec is now SINGLE-MEMBER and its own D0 gate against assuming a shared fix is vindicated.
- HYPOTHESIS: `manage-lessons list` has no state for an allocated-but-bodyless record, so the honest report D1 wants requires a lifecycle addition rather than a filter — confirm/refute at `manage-lessons` § `list` / `add` (verify-at-outline)
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-lessons.py VALID_STATUSES is still (active, superseded, removed); no allocated-but-bodyless state exists
- Verify-first clause: before D3, settle whether `record-metrics`'s consumer actually reads `phase_steps.facts`, or whether the landing spec's pointer is itself the stale half. If the consumer never read it, D3 is a spec correction rather than a producer fix and re-scopes accordingly.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: landing-payload-spec.md plus test_mark_step_done_facts_only.py confirm per-step facts ARE read by the landing and inbox drain contract

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-lessons/**` — `add` and `list` (D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-metrics/**` — `record-step` and `record-metrics` (D2, D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — the facts pointer D3 targets (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-lessons/**`, `test/plan-marshall/manage-metrics/**` — the D4 controls (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the dispatcher’s item-5f `mutates_source` branch and the `branch-cleanup` ordering, added 2026-09-03 by the drain folds of `deployment-and-refresh-gaps-010` and `dual-homed-hook-install-renders-identically-009` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the worktree-removal guard those folds ask for (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` — a producer reporting `persisted: false` over a write that landed, added 2026-09-04 by the drain fold of `review-apparatus-026` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-TRUTH-104` — the read-side complement. ⛔ Keep the write/read boundary explicit in the shipped docs; do not merge.
- Adjacent to: `PLAN-TRUTH-116` (obligations that cannot fail) — member 1 manufactures an unfalsifiable record, but by a producer rather than by a test arrangement.
- ⚠ **Cross-epic:** the lessons corpus that member 1 degrades is drained by the `lessons-handling-*` router epics, whose own `PLAN-LH2-18` was named as owning corpus integrity. ⛔ **A duplicate held in another ledger is invisible to this queue** — check `manage-status list` and the sibling epics at emit.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-121-producers-report-success-over-a-write-nothing-can-read.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-08-31 — inbox drain (2 message(s))

- **`disjointness-gate-reads-declared-surface-wrong-005.md`** — A red CI run is never archived, so the offline record shows an unbroken green history
- **`git-artifact-scanning-and-destructive-recovery-006.md`** — Every dispatch-boundary row in this run recorded its four context-load columns as unmeasured

⛔ Each is the sending plan's own first-party observation, relayed verbatim by title. **Treat every one as a LEAD** — the drain did not re-derive them, and several were observed against tree states that have since moved. Re-ground at outline.

## ⭐ FOLDED 2026-09-03 — inbox drain (3 message(s))

- **`deployment-and-refresh-gaps-010.md`** (relayed from Token-Sheriff, plan `refresh-identity-and-scope-defences` PR #682) — *`adr-propose` writes durable files but declares no `mutates_source`, so `branch-cleanup` would destroy them.*

  Self-caught `[WARNING]` at `2026-09-01T16:22:38Z`: four ADRs written by the step were live **only as uncommitted files in a worktree that `branch-cleanup` was ordered to remove.** They were committed by hand. ⛔ **On any run where the operator did not notice, the step would have appeared to succeed and produced nothing** — which is this spec’s objective sentence, reached from the step-contract side rather than the store side.

  ⭐ **Why it is structural, not incidental:** the dispatcher’s item 5f reads the **declared** `mutates_source` fact and skips commit instrumentation entirely on `false`. **The declaration is the whole contract — nothing observes whether the step actually wrote anything on the `false` path.** So a `mutates_source: false` step that writes tracked source loses the writes at worktree removal with no error and no finding, and the loss is invisible in the plan record because the step’s own `mark-step-done` reports success.

  ⭐⭐ **The asymmetry is the fold’s real content:** the INVERSE defect (a `post_run_review: true` step’s post-merge dirty-tracked-path guard) **is already instrumented**. The under-declaring direction is not. The ask: before `branch-cleanup` removes a worktree, fail (or file a finding) when the worktree carries uncommitted **tracked** paths that no step’s declared `mutates_source` accounts for — **so the declaration is checked rather than trusted, symmetrically with the guard that already exists in the other direction.**

- **`dual-homed-hook-install-renders-identically-009.md`** — *`build_time` reports an all-zero block for a plan that ran 77 builds.* (Supersedes `-003.md`, retired by this drain.)

  `metrics.md`’s `build_time` block was emitted as all zeros — `total_build_seconds: 0.0`, `build_count: 0`, every bucket 0 — for a plan whose own `script_cost_rollup` ranks `pyproject_build` **first at 77 calls / 16,475,540 ms = 67.3% of all script time in the plan.** Four of those builds hit a `timeout` or `failure` verdict during a two-hour incident window. **None of it is in the build-time oracle.**

  ⭐ **The two zeros are byte-identical.** A plan that genuinely ran no builds and a plan whose oracle was destroyed produce the same block, with no discriminator in the artifact. `plan-efficiency.md` already tells the *reader* to render `build_count: 0` as `unavailable`; **the defect is on the PRODUCER side**, which publishes no field saying whether the ledger was read. ⛔ The error direction is the damaging one: it under-reports build cost to **exactly zero**, so any roadmap figure derived from `build_time` treats the most build-heavy plans as free.

  ⚠ **The ordering half is a HYPOTHESIS this drain did not settle.** The sender derives it first-hand from `reconcile-ledgers` wall-clock rows — `branch-cleanup` at `08:01:14`, then `finalize-step-deploy-target` 08:04, `sync-plugin-cache` 08:10, `review-retrospective` 08:56, `plan-retrospective` 09:56 — concluding the worktree-resident ledger is destroyed strictly before every reader, and that **every worktree-using plan is exposed identically**. ⛔ **Confirm/refute against `code-intelligence-substrate`’s SHIPPED `PLAN-CIS-028-post-run-steps-ordered-before-their-evidence` and `PLAN-CIS-034-post-run-band-contract-and-ordering-residue`** — if those closed this ordering class, this is a regression or a second oracle they did not cover, and the difference decides the remedy. **Do not re-derive the ordering fix without settling that first.**

  The sender’s two halves are explicitly **not** to be conflated: (1) snapshot the ledger before destruction or move the derivation ahead of `branch-cleanup` — an ordering fix either way; (2) **make the zero self-describing regardless**, `builds: 0 (observed)` vs `builds: unavailable (oracle absent)`, *“without this, the next ordering regression is silent again”*. ⭐ And: **derive the blast radius rather than assuming `build_time` is the only consumer** — enumerate every metrics/report surface whose oracle is worktree-resident and whose reader runs post-`branch-cleanup`.

- **`dual-homed-hook-install-renders-identically-011.md`** — *zero cache/billing attribution: 0 of 14 dispatch-boundary rows carry the four context-load columns.* **RECURRENCE of an item already folded into this spec on 2026-08-31** (`git-artifact-scanning-and-destructive-recovery-006.md`, *“Every dispatch-boundary row in this run recorded its four context-load columns as unmeasured”*). Recorded here as a recurrence on the existing item, not as a second one.

  ⛔⛔ **THE MESSAGE’S PROPOSED FIX IS REFUTED AT HEAD — do not implement it as written.** Corroborated first-party by this drain against `manage-metrics record-dispatch-boundary --help`:
  - Its directive 1 (*“record the four columns at `record-dispatch-boundary`”*) is **already done**: `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens` and `--cache-creation-input-tokens` are all declared flags.
  - Its directive 2 (*“make an unattributed row say so rather than silently omitting four columns”*) is **also already done**: the help text states an omitted value is written as `'unmeasured'`, **NOT as 0**, and the key is absent from the result TOON.

  ⭐⭐ **So the residue is a CALL-SITE omission, not a schema gap** — materially different work, and much cheaper. The writer accepts the columns; the phase dispatchers do not pass them. **The observation (0 of 14 rows attributed) stands; the diagnosis does not.** This is the verify-against-ground-truth rule paying for itself: staging the message’s directive as written would have re-implemented landed work.

  ⚠ **Its directive 3 survives intact and is the one to keep:** *“size the lever before staging the work — state what fraction of dispatches actually surface `<usage>` before committing; a widening that populates 30% of rows produces a NEW partial-coverage instrument.”* ⭐ The sender also asks whether this belongs to `code-intelligence-substrate` rather than here. **It does not need to move:** this spec already owns the item, and CIS has shipped `PLAN-CIS-030` (context-byte attribution instrumentation) and `PLAN-CIS-042` (attribution populations and the cost decomposition), which is very likely WHY the schema half is already closed.

## ⭐ FOLDED 2026-09-04 — inbox drain (3 message(s))

- **`documented-invocations-...-004`** — *`analyze-logs build_time` publishes bare zeros beside a sibling block attributing 69% of script time to builds.* **Eight fields, every one a zero, no population marker and no could-not-look discriminator** — while in the SAME fragment `script_cost_rollup` ranks `pyproject_build` **FIRST at 50 calls / 19,009,450 ms = 69.107% of all script time**, with **25 build-result logs sitting in the plan directory**. ⛔⛔ **THIRD independent observation of this exact block** (after `dual-homed-...-009` and `-011`), and it adds the decisive framing: *“the consumer knows the discriminator is needed; the producer declines to publish it”* — `plan-efficiency` **explicitly mandates** rendering `total_build_seconds` as `unavailable`, never `0`, because *“a 0 asserts a measurement nobody made, and it averages into every cross-plan roll-up as though the plan had built instantly.”* Ask: publish `ledger_rows_scanned` and a `build_oracle_state` of `present`/`absent`, **and separately investigate why builds run inside a worktree do not land plan-attributed ledger rows** (sampled rows carry `plan_id: null` and empty `duration_seconds`).

- **`documented-invocations-...-006`** — *no dispatch in the plan recorded its four context-load columns.* All **21** boundary rows (1 in `4-plan`, 6 in `5-execute`, 14 in `6-finalize`) record all four as the literal `unmeasured`; `context_position_cost` reports `measured_rows: 0` of `total_rows: 21`, `position_multiple: unmeasured`. `enrich` was never run, so `billing_weighted_total` has `population_count: 0` and the `Billing (cost)` column is **empty on all six phase rows**.

  ⭐⭐⭐ **THIS INDEPENDENTLY CONFIRMS THE REFUTATION THIS EPIC RECORDED ON 2026-09-03.** When `dual-homed-...-011` asked for the four columns to be ADDED to the schema, this orchestrator checked at source and found them already declared, already writing `unmeasured` rather than `0`, and concluded the residue was a **CALL-SITE omission**. This message reaches the same conclusion from the other side, in its own words: *“the design is sound — an omitted flag correctly writes `unmeasured` rather than a false `0` — but with no caller supplying them the honest-absence path is the only path ever taken, so the measurement exists in the SCHEMA and never in the DATA.”* ⇒ **the schema half is closed; the call sites are the work.** ⭐ It adds a second route worth costing: **make `enrich` a finalize step** rather than something run by hand, since it reaches the same four fields. ⛔ *“Given that cache-read dominates billing weight, a corpus in which `measured_rows` is 0 on every plan cannot support any cost analysis at all.”*

- **`review-apparatus-026`** (carried-out finding `1d5140`, `PLAN-PR-038`) — *`ci_verify run` reports `persisted=false` / `persist_skipped_reason=head_sha` while it DID persist `head_at_completion`.* ⭐⭐ **This is this spec’s objective INVERTED, and the inverted form is the more dangerous one.** The payload returned `outcome=green, head_sha='' (empty), persisted=false, persist_skipped_reason=head_sha, step_marked_done=true` — **which read literally says a head-dependent step was marked done WITHOUT an anchor**, the documented absent-SHA case that makes the dispatcher re-fire and report the prior verdict UNVERIFIED. Acting on that reading, the orchestrator re-stamped — **and the re-stamp’s own return showed `previous_head_at_completion: 0a6fa35f7a…`, i.e. the anchor was ALREADY correctly persisted and all three fields were wrong about what the script had just done.**

  ⛔ **Both directions matter and only one was benign here:** *“a consumer that trusts `persisted=false` does redundant work (observed); a consumer that trusts a `persisted=true` when the write did NOT land would leave a head-dependent step anchored to nothing and never notice.”* The empty `head_sha` compounds it — **the `run_id` is populated from the same CI read, so the head was available.** Remedy: report `persisted` / `persist_skipped_reason` **from the actual write result rather than from a pre-write branch**, and populate `head_sha` from the same source the anchor is written from — *“or, if the anchor is written by a path that does not return through this payload, say so rather than reporting a skip.”*

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

- **§1.7 — a multi-argument mutation's aggregate success is not per-argument evidence.** `ci pr edit` returned `status: success`. ⛔ **The title was applied; the body was NOT.** `ci prepare-body` defaults to `--for create` and the edit consumer requires `--for edit`, so **the body was silently dropped and the call reported success on the strength of `--title` alone.** The stale body propagated into a replacement PR and was caught by a **review bot noticing the description did not match the diff** — not by any local check. ⭐ Two obligations, and the second is the structural one: **read the mutation back at the call site**, and **in a producer/consumer pair the preparer's default must not silently produce something the consumer discards.**

- **§6.1 — a step that writes tracked files while declaring no `mutates_source`. ⭐ RECURRENCE, and this is now the THIRD independent report of this exact defect** (after `deployment-and-refresh-gaps-010`, folded here 2026-09-03). ⛔⛔ **The new fact is the recurrence interval: TWICE, IN TWO DIFFERENT PLANS, FIVE DAYS APART, WITH THE LESSON FILED IN BETWEEN.**

  **The mechanism is a composition of two individually-reasonable choices**, and the document states it better than the earlier report: `mutates_source` **defaults to false when undeclared**, and verification of that claim is **band-scoped rather than universal**. `default:adr-propose` is outside the `post_run_review` band, so item-5f(0) — **the guard that exists precisely to CHECK an asserted `mutates_source: false` rather than trust it** — does not fire either. The step nevertheless writes tracked `.adoc` files; **caught by neither mechanism, they would have been destroyed when `branch-cleanup` removed the worktree**, and survived only because an orchestrator committed them by hand.

  ⭐⭐ **The matched pair the document supplies is the part worth keeping, because it names why a blanket fix is wrong:** `default:lessons-capture` declares `mutates_source: false` **correctly** — every branch writes only untracked `.plan/` state. **Two steps under the same declaration, opposite cases, and NOTHING distinguishes a truthful `false` from a false one at the point the dispatcher trusts it.** ⇒ the remedy cannot be "stop trusting the declaration"; it must be an observation. **The document's own one-line form: a step whose output is destroyed by worktree removal should not be able to record `outcome: done`.** The step records `done` with no `head_at_completion` and no commit fact.

## ⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (2 claims contradicted). ITS OWN D0 GATE IS VINDICATED.

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 1 | `record-step` writes a placeholder zero indistinguishable from a measured zero | **FIXED** — `cmd_record_step` now uses `_record_step_column` with `UNMEASURED_COLUMN_TOKEN`, which distinguishes an explicit `0` from an omitted value |
| 4 | the three members share one remedy | **REFUTED** — they are now in **materially different repair states** |

⭐⭐⭐ **THE REFUTATION OF CLAIM 4 VINDICATES THIS SPEC'S OWN D0 GATE, WHICH FORBADE ASSUMING ONE FIX
SERVES THREE.** The members have diverged exactly as D0 warned they might:

| Member | State at HEAD |
|---|---|
| 1 — `manage-lessons add` allocates a body-less lesson and returns success | **OPEN** (`_allocate_and_write_scaffold(body='')`, and `VALID_STATUSES` still has no allocated-but-bodyless state) |
| 2 — `record-step` placeholder zero | **FIXED** (three-state `UNMEASURED_COLUMN_TOKEN`) |
| 3 — `record-metrics` facts unread | **SUBSTANTIALLY ADDRESSED** — `landing-payload-spec.md` now routes `total_tokens` / `total_wall_seconds` as facts, and `test_mark_step_done_facts_only.py` pins that per-step facts ARE read by the landing/inbox drain contract (claim 6) |

⇒ ⛔ **Re-scope: this spec is now SINGLE-MEMBER.** Only member 1 remains open. **Emitting it as a
three-member plan would rebuild two closed fixes.** ⭐ **Keep the D0 gate's rationale in the shipped
doc** — a gate that refused to assume a shared remedy was proved right by the corpus moving underneath
it, and that is a positive control worth preserving.

## ⛔ FOLDED 2026-09-07 — PLAN-TRUTH-128 drain (1 item), AND THE REPORTER'S OWN ERROR IS THE EVIDENCE.

### `freshness-gate-...-002` — validate `--head-at-completion` as a real commit instead of trusting a typed SHA

⭐⭐⭐ **The reporting run disclosed, unprompted, that it FABRICATED A FULL SHA FROM A SHORT FORM THREE
TIMES into `head_at_completion`** — caught each time, by a human. ⇒ **This is not a hypothetical
hardening request: the producer accepted three invented values, and only attention stopped them.**

⛔ **It is this spec's exact archetype at the STATUS-WRITE seam**: a producer reports success over a
value nothing can read back — here a 40-hex string that is well-formed, stored, and **names no object
in the repository.** ⛔⛔ **And the consequence is load-bearing**: `pre-submission-self-review` uses
`head_at_completion` as its **delta anchor** (*"the outcome test is what makes the SHA an anchor rather
than a timestamp"*), so a fabricated SHA silently mis-anchors the next delta round — **and the round
still closes clean.**

⭐ **The remedy is one call and mechanically checkable**: resolve the value with `git cat-file -e` (or
`rev-parse --verify`) at write time and refuse a SHA that names no object. ⛔ **Do not settle for
validating the SHAPE** — 40 hex characters is exactly what a fabrication looks like.

⚠ **Expected Surface widened in this same act**:
`marketplace/bundles/plan-marshall/skills/manage-status/**` — the `--head-at-completion` write path
(HYPOTHESIS, verify-at-outline).

## ⛔⛔⛔ FOLDED 2026-09-08 — lessons-handling drain (1 item). A TOTAL WRITE LOSS THAT RECORDS `done`.

### `-022` — `adr-propose` escalations are UNREACHABLE: the dispatcher wires `escalate_ask` for `automatic-review` ONLY

A dispatched leaf **cannot** fire `AskUserQuestion` — that is the documented leaf contract — so
`adr-propose` returns a prompt-required escalation and relies on the dispatcher to raise it.
**`phase-6-finalize`'s dispatch loop consumes `escalate_ask` for `automatic-review` only. No other
step's escalation is read.**

⇒ ⛔⛔ **The consequence is TOTAL, not partial**: the leaf returns its proposals · the dispatcher never
reads that field for this step · no prompt ever reaches the operator · **and the step records a clean
`outcome: done`.**

⭐⭐⭐ **This is this spec's archetype at its purest — a producer succeeding over a write NOTHING CAN
READ — and it has an OBSERVED cost.** Two ADR-worthy decisions were identified and neither reached the
operator; **the operator learned of them only from the plan's own closing narrative.**

⛔ **And the only trace is a `display_detail` that reads as a benign zero**:
`"no ADRs proposed (2 candidates need operator confirmation)"`. ⇒ **A sentence that states the loss in
plain words and still renders as success.** ⚠ **That makes it worse than a silent drop**: a reader who
skims sees `done`, and a reader who reads the detail must notice that a parenthetical contradicts the
verdict beside it.

⚠ **The general shape for D0**: `escalate_ask` is a channel with **one registered consumer and an open
set of producers.** ⛔ **Enumerate the producers, not the consumer** — every leaf that can return the
field and is not `automatic-review` is losing writes today.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-144-the-lessons-corpus-and-producers-that-report-success-over-a-write-nothing-can-read.md` (PLAN-TRUTH-144)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
