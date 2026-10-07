# PLAN-TRUTH-106: One payload, two renderings — retire the operator paste as a transport

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-106-the-terminal-emission-and-the-operator-report-do-not-check-themselves.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.
>
> ⚠ **The filename retains the original slug** because the row is queued under it and a staged spec is
> never renamed. The title above is the current scope; the slug records where it started.

## Provenance and the operator's directive

Staged 2026-08-24 after verifying PLAN-TRUTH-075's operator report against ground truth. **Rewritten
the same day on explicit operator direction**, which supersedes this spec's first scope and one clause
of the payload standard:

> *"It must become unnecessary for all aspects. The goal was to prevent pastes completely. All infos
> must be transported via inbox."*

⛔ **This is a DECIDED SCOPE, not a proposal to re-litigate.** The orchestrator raised a narrative-only
objection; the operator overrode it. The objection is recorded in § "What the override actually costs"
below — **with the correction that it was largely WRONG** — so the run inherits the reasoning rather
than re-deriving it.

## Objective

**A plan reports its outcome to two audiences over two channels, and neither channel carries
everything.** The goal is a single one: **make the drained inbox fully substitutable for the pasted
report, so no paste is ever required to transport a run's information.**

Three defects stand between here and that, and they compound:

**1. The machine channel is not being filled at all.** `PLAN-TRUTH-080` shipped the terminal
machine-readable emission on **2026-08-13 (PR #1215, `5a5446d37`)**, and `emit-landing.md:186`
**REQUIRES** a `landing-facts` block carrying eight keys. **PLAN-TRUTH-075 finalized ten days later,
its `emit-landing` step reported `[OK]`, and its landing carries NO BLOCK AT ALL** — `landing-check`
reports all eight keys missing, `schema` included.

**2. The typed facts are discarded at the render boundary.** `output-template.md:5` states the
renderer *"is a pure assembler: it never invents per-step content. Each finalize step authors its own
one-line `display_detail` string … the renderer only concatenates those strings."* ⇒ **the typed
per-step `facts` map that `manage-status --fact` records is thrown away**, and the report is
reconstituted from prose. The landing, separately, carries a different subset. **Two producers, two
lossy projections, no single complete record.**

**3. Half of what the operator actually pastes is governed by no template at all.** The report the
operator pasted = the rendered skeleton (headline / Goal / Deliverables / Finalize steps / Repository
trailer, per `output-template.md:17-38`) **plus agent-authored closing prose that appears in no
template and no store** — the defect-cascade narrative, three self-corrections, the cost judgement, and
an open item for a sibling plan. ⭐⭐ **That half was never transportable because nothing ever captured
it.** Any fix that mechanizes only the skeleton leaves the operator still pasting.

## The invariant this plan installs

> **ONE PAYLOAD, TWO RENDERINGS.** The finalize run produces a single complete record. The operator
> report and the epic landing are both **views** of that record. Neither is authored independently.

⛔ This is the deliverable that matters. Every other item is machinery in service of it. **Substitutability
achieved by discipline decays; substitutability achieved by construction does not** — and this epic has
recorded producer-consumer drift (n≥3) every time two surfaces were maintained in parallel.

## What the override actually costs — and the correction the orchestrator owes

`landing-payload-spec.md` classifies two of its seven control items as **NARRATIVE-ONLY** and argues
they must not be mechanized: **#4** a merge call returning `merged: true` on an unmerged branch, and
**#7** a review-bot withdrawal. The orchestrator cited these when raising the objection.

⭐⭐ **RE-READING THEM, THE OBJECTION WAS LARGELY WRONG AND IS WITHDRAWN.** Both control items are
**OPERATOR OBSERVATIONS, not run output** — the spec says so itself: #4 *"was caught by the operator
reading the PR against the claim — it arrived as operator narrative, not as a step fact"*, and #7 is
*"a runtime observation the operator surfaced"*. **Neither was ever in the run report.** They are
things a human noticed, not things the run produced and failed to transport.

⇒ **Retiring the paste as a transport for RUN-PRODUCED information costs nothing and fabricates
nothing.** The narrative-only reasoning protects against inventing a `merge_state` fact the run never
generated — and this plan does not do that. The run's own prose (the cascade narrative, the
self-corrections) **is** run output; it is narrative in FORM, not unavailable. ⭐ **The inbox already
carries arbitrary prose** — messages `-008` and `-009` are prose and transported perfectly — so the
transport was never the obstacle. **Nothing was capturing the prose.**

⛔ **The boundary that remains, stated so it is not mistaken for a gap in this plan:** information the
**run did not produce** cannot be emitted by it. If an operator reads a PR and catches a false merge
the run never observed, that reaches the epic as an operator observation through `analyze`, which is a
different channel with a different trust posture. **That is not a paste of the report, so the
operator's goal is fully met.** D6 makes this boundary explicit in the standard rather than leaving it
inferable.

## Deliverables

Seven deliverables. **This is at the edge of the epic's split guard of 12 and D0 must re-count** — the
guard is 12 and seven is under it, but D2 and D3 are each large enough to split further if D0's
population comes back bigger than expected.

**D0 — GATE: derive the report↔landing delta from the ARTIFACTS, not from the spec's table.**
`landing-payload-spec.md` already carries a derived delta table, and it is **provably incomplete** —
it does not contain the agent-authored closing prose (defect 3 above), because that prose is in no
template it could have been derived from. ⇒ **Enumerate the population empirically**: take the
PLAN-TRUTH-075 corpus, which is complete and on disk — the pasted report (in this epic's session
record), the ten drained messages (`inbox/archive/cloud-lane-build-gate-reads-one-field-short/`), and
the archived `status.json` — and produce a **three-way** classification of every item: *in report only*
/ *in landing only* / *in both*. **Publish the population and its size.** ⛔ The spec's existing table
is an INPUT to this, never a substitute for it. ⭐ The known-missing control set for this derivation is
the four items § "Verification" names; a derivation that misses them is measuring the wrong thing.

**D1 — `emit-landing` verifies its own emission and reports the verdict.** After writing the message,
the step MUST run the completeness check on what it just wrote and surface the result. ⛔ **`[OK]` must
become unreachable for an emission that fails its own required-key contract.** ⚠ **Do NOT make it fail
the phase** — `complete: false` is a VERDICT, not a fault, and the drain is documented to record it and
continue; an incomplete landing beats no landing. What changes is that the step stops calling it clean.
⭐ **No new checker is written**: `_orchestrator_inbox.check_landing_completeness` (exposed as `inbox
landing-check`) already implements the contract, and a second implementation is precisely the
producer-consumer drift this plan exists to end.

⛔⛔ **THE CAUSE OF PLAN-TRUTH-075's BLOCK-LESS LANDING IS `indeterminate` AND MUST NOT BE GUESSED.**
Two explanations survive the available evidence: **(a)** the step ran against a cache lacking the
standard — `emit-landing.md` is **absent from `0.1.1240`** and present in `0.1.1526`/`1527`/`1538`, and
a documented incident has the served cache regressing to 1240 with this exact file missing (⚠ that
incident is dated 2026-08-24; the finalize was 2026-08-23); **(b)** the step had the standard and did
not follow it. **Which cache was seated during that finalize is recorded nowhere reachable.** ⭐ **D1 is
correct under BOTH branches** — under (a) the step reported `[OK]` with no contract to follow, under
(b) it reported `[OK]` while violating one, and **in neither branch did anything check what was
written**. So D1 does not wait on the answer. If D0 settles it as (a), the cache-seating residue is
**recorded and referred** to the plugin-registry pin work, **not absorbed here**.

**D2 — the landing carries the COMPLETE per-step record, not one prose line per step.** The typed
`facts` map must stop being discarded. The landing must carry, per finalize step: the outcome, the
`display_detail`, **the `firing_count`, and every `prior_firings[]` entry with its own outcome**, in
composed order. ⭐ **First-party evidence for why the current shape is insufficient**, from `-075`'s
archived `status.json`: **six** steps re-fired (29 firings across 22 recorded steps, headlined
`23/23 done`), only **one** disclosed its re-fire, and **`pre-submission-self-review` carries
`prior_firings: [{"outcome": "failed"}]` while rendering `[OK] … clean on full surface`.** ⛔ **A record
that keeps only the terminal outcome cannot express "failed, then passed", and no rendering of it can.**
⚠ **The re-fires themselves are CORRECT** (head-dependent contracts) and must not be suppressed — this
is a record-and-render change only. ⚠ The `{step}:{outcome}` shape of the required `steps` key is a
FLOOR, not the target; extend it or add a companion key, but do not break existing consumers.

**D3 — the landing carries the run's NARRATIVE, and the narrative gets a producer.** The agent-authored
closing prose is currently captured nowhere. Give it a defined home in the landing envelope — the
existing `## Residue` section is the natural anchor — and a **defined producer obligation**, so it is
authored once and rendered twice rather than improvised at report time. ⛔ **At minimum it must carry
the classes `-075` demonstrated:** a **correction the run makes to its own earlier statements** (three
of these, and two were in NO message — the highest-value class and the one most certainly lost today);
a defect-cascade or root-cause narrative; the run's own cost judgement including any **counter-argument
it declines to settle**; and **open items for named sibling plans**. ⭐ `-075` explicitly declined to
settle whether its spend was justified, calling it *"a judgement for the orchestrator, not for this
plan to settle in its own favour"* — **that restraint is correct and the channel must preserve it**,
carrying the numbers and the counter-argument rather than a verdict.

**D4 — the operator report becomes a VIEW of the landing payload.** Re-point `output-template.md` so
the report renders from the same record the landing carries. ⛔ **This is the invariant; D2 and D3 are
its prerequisites.** ⚠ The report's *presentation* need not change — the operator's terminal output may
look identical — and it **must not regress**: the skeleton (headline / Goal / Deliverables / Finalize
steps / Repository trailer) and the Phase Breakdown supplement all keep emitting. What changes is
**where the content comes from**. ⚠ `output-template.md:5`'s "pure assembler" clause is the line that
encodes today's lossy boundary and must be revised in lock-step — ⭐ note that PLAN-TRUTH-075's own
landed guard exists because two surfaces of one document drifted, and **this plan is editing exactly
that shape**: revise the clause and its consumers together.

**D5 — the report states the landing reached the epic inbox, WITH its completeness verdict.**
*(the operator's original request.)* When the plan is orchestrator-originated, the report says plainly
that the orchestrator has the record and no paste is needed.

⛔⛔ **THE LINE MUST CARRY D1's VERDICT, NEVER THE BARE FACT OF EMISSION.** *"Landing emitted to
`{epic}` inbox"* printed on a block-less message tells the operator to skip the only channel currently
carrying the facts — **the request implemented naively makes this defect worse, not better.** ⇒ **D1 is
a hard prerequisite of D5.** ⭐ **The detection plumbing already exists and MUST be reused:**
`phase-6-finalize/SKILL.md` Step 3 item 4b.a0 resolves `source_id` via `manage-plan-documents request
read` and classifies it through **`orchestrator inbox detect` once per finalize run**, carrying the
`orchestrated` bool to four write-sites, and the SKILL forbids any consumer re-issuing either call.
⛔ **`inbox detect` is the single sanctioned detection seam — no second detector, no new persisted
field.** When `orchestrated: false`, no line is emitted.

**D6 — retire the narrative-only transport carve-out, and state the boundary that replaces it.** Amend
`landing-payload-spec.md`: run-produced prose is **transported**, not classified un-transportable.
⛔ **Do NOT delete the reasoning** — restate it as the boundary it actually is: *a landing carries
everything the RUN produced; information the run did not produce (an operator's own observation of a
PR, a bot withdrawal nobody's step recorded) reaches the epic through `analyze`, a different channel
with a different trust posture.* ⭐ Control items #4 and #7 keep their classification **for the right
reason** — they are operator observations — rather than being used to justify leaving run prose
untransported. ⚠ Record that this amendment was made on operator direction, and that it costs no
fabricated signal.

## Verification

⭐⭐ **The load-bearing test is SUBSTITUTABILITY, and it must be mechanical, not a reviewer's
judgement.** Feed a complete finalize run's landing message to a check that asserts every class D0
enumerated is present. **The PLAN-TRUTH-075 corpus is the fixture** — it is complete, on disk, and its
report is known to contain four things its landing did not:

| # | Present in the pasted report | In the landing? |
|---|---|---|
| 1 | the 23-line finalize step table with per-step `display_detail` | **no** |
| 2 | three corrections the run made to its own earlier statements | **one of three** (`-009` carried the chronology; the CodeRabbit over-claim and the gate-8 durability correction were in NO message) |
| 3 | the repository end-state trailer | **no** |
| 4 | the open item for `PLAN-TRUTH-092` | yes (`-010`) |

⛔ **A matched negative control is mandatory**: a landing with a class deliberately removed must FAIL
the substitutability check. This epic has recorded the vacuous-guard archetype re-introduced **by a fix
for it** at least twice — most recently inside PLAN-TRUTH-075's own guard cascade, five rounds deep —
so a check that cannot fail is the expected failure mode here, not an unlikely one.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` *(the `orchestrated` carry — expected READ-ONLY)*
- `test/plan-marshall/phase-6-finalize/`
- `test/plan-marshall/plan-orchestrator/test_landing_completeness.py`

## Dependencies and Sequencing

✅ **MACHINE-DERIVED at staging (`corpus cross-check`, 2026-08-24 — 154 specs / 7 sibling epics / live
plans).** ⭐ **The hand-written version named 4 and MISSED 7**, six of them cross-epic — the third
consecutive recurrence of R48 on this orchestrator's own maps. ⛔ Re-derive again at emit time; a
running plan's real surface can exceed its spec.

**The full machine-derived set**, beyond the four detailed below: `PLAN-TRUTH-064` (1 —
`phase-6-finalize/SKILL.md`, READ-ONLY here) · `PLAN-TRUTH-100` (1 — `_orchestrator_inbox.py`;
sequenced after `PLAN-CIS-052`, so it will likely move first) · `code-intelligence-substrate/PLAN-CIS-050`
(1) and `PLAN-CIS-052` (2) · `review-apparatus/PLAN-PR-027` (1) and `PLAN-PR-033` (1) · live plan
`finalize-step-contract-guard-residue` = `PLAN-TRUTH-095` (1, RUNNING at staging). **Every one of these
touches `phase-6-finalize/SKILL.md`, which this plan declares READ-ONLY** — so most are expected to be
benign, but that expectation is a hypothesis to confirm at emit time, not a finding.

⛔⛔ **`review-apparatus/PLAN-PR-028` — 4-FILE OVERLAP, CHECKED AT STAGING: NOT a duplicate.
Sequencing constraint only.** *(Missed by the hand-written map; found only by the machine.)* Its title —
*"a landing message that cannot outrun its merge"* — and its 4 shared files made it the one candidate
that could have made this plan redundant, so it was read rather than counted. **It is not:**

| | `PLAN-PR-028` | `PLAN-TRUTH-106` |
|---|---|---|
| Governs | **WHETHER** a landing is emitted — *"no landing for a run that did not merge"*, and a foreign-PR gate that clears only on evidence | **WHAT** the landing carries, and whether the producer checks itself |
| Failure it prevents | asserting a merge nobody observed | transporting less than the run produced |

⭐ **Complementary, and PR-028's rule is the stronger one where they meet**: a landing that must not
exist is not made acceptable by being complete. ⚠ **PR-028 is `review-apparatus`'s successor to the
transferred `PLAN-100`** — the landing-emitted-pre-merge-with-no-outcome defect this epic's routing rule
names — so it is that epic's, not ours, and **this plan must not touch the emission precondition.**
⚠ PR-028 carries its own ⛔⛔ *"DO NOT EMIT AS WRITTEN — must be re-authored against HEAD first"* banner,
so it is not imminent and should not be waited on.

⛔ **THREE PLANS NOW TOUCH `merge_state` SEMANTICS AND THEY MUST NOT ANSWER SEPARATELY:** `-096` D1
(*an unreadable `merge_state` is not a supplied fact*), `PR-028` D1 (the `merge_state`→terminal-branch
mapping, whose keys that spec's own re-grounding calls *"wrong-shaped"* since `merge_state` alone
discriminates every branch at HEAD), and this plan's D1 (which reads `merge_state` as one of eight
required keys). **Whichever lands first sets the vocabulary; the other two consume it.** Record the
overlap and serialize — do not silently absorb a sibling's gap.

- ⛔⛔ **`PLAN-TRUTH-096` (`orchestrator-inbox-and-landing-residue`) — SERIALIZE, `-096` FIRST. The
  surface overlap is now REAL, unlike in this spec's first version.** Its Expected Surface includes
  `landing-payload-spec.md` and `_orchestrator_inbox.py`, **both of which this plan now edits.** Its
  **D0** re-derives the landing-completeness key classification and its **D1** distinguishes
  *degraded-but-answered* from *could-not-read* at every key. ⭐ **Complementary, not duplicate**:
  `-096` decides what a degraded value MEANS (consumer side); this plan decides what gets emitted and
  whether the producer checks itself. ⛔ **This plan's D6 amends the very document `-096` D0 is
  re-deriving** — landing them concurrently would produce two answers to one question. `-096` was
  RUNNING at staging; re-check its landed scope before starting.
- ⛔ **`PLAN-TRUTH-104` — SERIALIZE, `-104` FIRST**, if D0's population includes the reconcile verdict.
  `-104` owns the checked-vs-vacuous vocabulary in `finalize-step-simplify.md`; this plan renders it.
  ⚠ `-075` rendered *"reconcile clear"* with no population beside it — probably genuine, since that run
  did have `pr-comment` findings, **but "probably" is the defect**. Consume `-104`'s vocabulary; do not
  invent a second.
- ⚠ **`PLAN-TRUTH-097` — check.** Its F3/F4/F5/F6 concern the same `phase_steps` re-fire record D2
  reads. `-097` fixes the RECORD and the audit; this plan fixes the TRANSPORT and the RENDERING.
- ✅ **`PLAN-TRUTH-080` — SHIPPED (#1215), not a constraint.** It built the emission this plan makes
  self-checking and complete. ⭐ Read `landings/PLAN-TRUTH-080.md` first: this plan finishes what it
  started, and its D0 gate should establish why the emission it shipped is not being filled.
- **Depends on:** `-096` (hard), `-104` (hard, for the reconcile class only).

## Claim Labels

- OBSERVED: `emit-landing.md` REQUIRES a `landing-facts` block carrying eight named keys — read at `phase-6-finalize/standards/emit-landing.md` § `:186`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: emit-landing.md:245 requires schema, plan_id, pr, merge_state, deliverables_total, deliverables_done, total_tokens, steps -- exactly 8 keys
- OBSERVED: `PLAN-TRUTH-080` shipped that emission on 2026-08-13 as PR #1215 / `5a5446d37` — read at `git log` § the commit subject *"terminal machine-readable landing emission (plan 302)"*.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: git log 5a5446d37 subject matches verbatim and is an ancestor of main (merge-base --is-ancestor exits 0)
- OBSERVED: `cloud-lane-build-gate-reads-one-field-short-010.md` carries NO block at all — `inbox landing-check` returns `complete: false` with all eight keys missing, `schema` included.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: References an archived inbox message; the orchestrator inbox landing-check script was deliberately not invoked under this pass read-only constraint
- OBSERVED: `output-template.md` declares the renderer *"a pure assembler"* over per-step `display_detail` strings, and its skeleton contains no narrative section — read at `phase-6-finalize/standards/output-template.md` § `:5` and `:17-38`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: output-template.md:5 the renderer is a pure assembler and only concatenates those strings -- verbatim
- OBSERVED: `emit-landing.md` is absent from cache `0.1.1240` and present in `0.1.1526` / `1527` / `1538` — read at `~/.claude/plugins/cache/plan-marshall/plan-marshall/*/skills/phase-6-finalize/standards/`.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Cache version 0.1.1240 no longer present in the local plugin cache (oldest present is 0.1.1571); historical seating now unreachable
- OBSERVED: `pre-submission-self-review` carries `prior_firings: [{"outcome": "failed"}]` with `outcome: done` — read at the archived plan's `status.json` § `phase_steps["6-finalize"]`.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Named archived plan status.json not locatable this pass
- OBSERVED: `landing-payload-spec.md` control items #4 and #7 are OPERATOR observations, not run output — the spec says so verbatim; this is what makes the paste retirable without fabricating a signal.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: landing-payload-spec.md:72 and :75 both mark items 4 and 7 NARRATIVE-ONLY, operator narrative and runtime observation the operator surfaced -- verbatim
- HYPOTHESIS: which of (a) a cache lacking the standard or (b) the step ignoring it caused the block-less landing — ⛔ **INDETERMINATE and must be reported as such**; the seated cache version for that finalize is recorded nowhere reachable. D0 settles it or says it cannot (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Cause (a) vs (b) indeterminate by the spec own design; -075 seated cache version remains unreconstructable
- Verify-first clause: D0's report↔landing delta must be derived EMPIRICALLY from the PLAN-TRUTH-075 corpus, never from `landing-payload-spec.md`'s own table, which is provably incomplete because it could not derive prose no template contains.

---
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause on an unbuilt D0 empirical delta

## ⭐⭐ NEW DATA POINT 2026-08-24 — A COMPLETE `landing-facts` BLOCK EXISTS, AND IT MOVES D0

`PLAN-TRUTH-095` (`finalize-step-contract-guard-residue`) emitted its landing at **10:41:04Z**, and:

```text
inbox landing-check --slug truthful-signals --message finalize-step-contract-guard-residue-013.md
  complete: true
  missing_keys[0]:
```

⇒ **The machine channel WORKS. It is being filled.** This is the first complete block observed, against
`PLAN-TRUTH-075`'s landing which was missing **all eight** required keys.

### What this changes

⛔ **This plan's Objective claim — *"the channel `-080` built is not being filled"* — is now TOO
STRONG and must be re-scoped at outline.** The accurate statement is: **`-075` did not fill it; `-095`
did.** One plan's failure is not the channel's failure, and a spec that opens on the wider claim will
send its run looking for a systemic break that the evidence no longer supports.

⭐ **It also moves D0's indeterminate cause toward (a).** D0 records two surviving explanations for
`-075`'s block-less landing: **(a)** the step ran against a cache lacking `emit-landing.md` — absent
from `0.1.1240`, present in `1526`/`1527`/`1538` — or **(b)** the step had the standard and ignored it.
A second plan **on the same machine**, days later, produced a complete block through the same step.
⇒ **(b) now requires the step to have ignored the standard once and honoured it once, with no proposed
discriminator**; (a) requires only that the seated cache differed between the two runs, which is
independently documented as happening on this machine.

⛔ **This is a SHIFT IN LIKELIHOOD, NOT A SETTLEMENT, and D0 still owns the question.** The seated cache
version for `-075`'s finalize remains recorded nowhere reachable. **Report `indeterminate` with the
evidence leaning to (a), never `(a)` as a finding.** ⚠ If D0 settles it as (a), the residue is the
plugin-registry pin work's, **recorded and referred, not absorbed here.**

### What this does NOT change

⭐ **D1 stands entirely, and this data point strengthens it rather than weakening it.** The producer
still does not check its own emission: `-095` produced a complete block and `-075` produced none, **and
both reported `[OK]`.** ⇒ **The step's outcome carries no information about whether its contract was
met** — which is exactly D1's subject, and is now demonstrated across a *matched pair* rather than
argued from a single failure. **A producer that reports success identically for a conforming and a
non-conforming emission is the defect, and it survives whichever way D0 resolves.**

⚠ D2/D3 (the complete per-step record, and the narrative) are also unaffected: `complete: true` certifies
only the eight REQUIRED keys. It says nothing about `firing_count`, `prior_firings[]` outcomes, or the
agent-authored closing prose — the three things D0's empirical delta must still enumerate.

## ⛔⛔ D0's CAUSE (a) IS NOW DIRECTLY EVIDENCED — a plan OBSERVED seating at `0.1.1240` (2026-08-24)

From PLAN-TRUTH-095's inbox `-007`, and this is first-party evidence from a session, not an inference:

> Every skill body loaded into this retrospective envelope came from
> `~/.claude/plugins/cache/plan-marshall/plan-marshall/**0.1.1240**/skills/...` — the path printed in
> each skill-load banner.

⭐⭐⭐ **`0.1.1240` is exactly the cache version this plan's D0 identified as LACKING
`standards/emit-landing.md`.** D0's cause (a) was *"the step ran against a cache lacking the
standard"*, and its weakness was that no run had been observed seated there. **One now has.** ⇒ **(a) is
no longer the merely-cheaper explanation; it is the evidenced one.**

⛔ **It is STILL not settled and D0 still owns it.** This observation is of PLAN-TRUTH-095's
*retrospective envelope*, not of PLAN-TRUTH-075's *`emit-landing` envelope* — a different plan, a
different dispatch, a different moment. **What it establishes is that seating at `1240` HAPPENS on this
machine, which is precisely the premise (a) needed and lacked.** Report `indeterminate` with (a)
evidenced, never (a) as settled.

### ⭐⭐ A SECOND, INDEPENDENT FINDING THE SAME MESSAGE FORCES — "the session is seated at X" IS NOT WELL-FORMED

The message closes with a correction aimed at this orchestrator:

> the dispatching orchestrator stated the session was seated at `0.1.1526` against a cache of
> `0.1.1539`. **The observed seating is `0.1.1240` — lower than both, so the orchestrator's own belief
> about the seated version was itself wrong.**

⛔ **Accepted, and the diagnosis matters more than the correction.** This orchestrator derived
`0.1.1526` from **its own skill base directory path** — which is true of *its* envelope and says
nothing about a dispatched leaf's. ⇒ **Seating is PER-ENVELOPE, not per-session.** A dispatched
retrospective can load bodies from a different cache version than the orchestrator that dispatched it,
**and both readings are correct about different things.**

⚠ **Consequence for this plan and for every pin-split claim:** *"the session is seated at X"* is not a
well-formed statement. A seating claim must name **which envelope observed it and how** — a skill-load
banner (what `-007` used) or a base-directory path (what the orchestrator used) — because the two can
legitimately disagree. ⛔ **D0 must not treat a single seating observation as a session-wide fact**, in
either direction.

⭐ **The near-miss is the reason this message exists and is worth carrying into D0's method.** Reading
the seated `manage-metrics/SKILL.md` (a 6-value `--termination-cause` enum) against the plan's real
dispatch rows, **10 of 11 rows carried causes absent from the documented enum** — a textbook
doc-contract-divergence with a plausible severity and a plausible fix. The repo source documents **12**
values, argparse confirms 12, and a contract test guards three enumeration sites. **The finding was
refuted only because the repo source was checked before it was written.** ⇒ **A stale seated body is not
merely a missing feature — it is an active generator of confident false findings**, and any D0
conclusion drawn from reading a seated body must be re-checked against repo source first.

## Folded from the PLAN-TRUTH-096 drain (2026-08-24) — finding `e9ef2c` (severity: error)

⭐⭐ **This is the first landing whose `landing-facts` block was complete but for ONE key, and the
missing key is missing for a reason this spec owns.** `landing-check` on
`orchestrator-inbox-and-landing-residue-012.md` returns `complete: false`, `missing_keys: [pr]` —
seven of eight required keys supplied, against `PLAN-TRUTH-075`'s all-eight-missing a day earlier.

**The producer gap.** `emit-landing` sources `pr` from `create-pr`'s `pr_number` typed fact. This
run's `create-pr` record carries **no `facts` sub-dict at all** — only `display_detail: "#1338"`.
`create-pr.md` declares `pr_number` in `records_facts` and mandates `--fact pr_number={pr_number}` on
**both** Branch A and Branch B, and the runner verified that doc is byte-identical across cache
versions `0.1.1538` / `0.1.1539` / `0.1.1541` ⇒ **a live producer gap, not version skew.**

⭐ **The emitter's choice was correct and must be preserved by whatever this spec builds.** `n/a` was
rejected deliberately: at `pr` it is exempt from the completeness check and would drain as the settled
fact *"no PR exists"* for a PR that demonstrably merged. Re-parsing `#1338` out of `display_detail` is
forbidden by the same section. `unknown` is the honest token, and the landing is recorded INCOMPLETE
at `pr` — **the accurate outcome**. A "fix" that made this landing report complete would be the defect.

⛔ **What nothing surfaces is the loss at the step.** `create-pr`'s `display_detail` is intact, so the
step reads as fully successful; **only the drain sees the missing fact.** ⇒ D-scope: a step that
declares `records_facts` and records none must fail its own check, at the step, not two ordering bands
later in a consumer.

**Scope note — do NOT widen this into the whole `n/a` question.** `emit-landing` and `archive-plan`
carry `n/a` outcomes **structurally** (orders 1000 and 1100; neither had a recorded outcome when the
message was written). That is the legitimately-did-not-run-yet class, inherent to step placement, and
is not a defect of this run.

## Folded from the PLAN-TRUTH-088 drain (2026-08-24) — the Objective must be RE-SCOPED AGAIN

⭐⭐⭐ **`-088`'s landing `-016` returns `complete: true` with ZERO missing keys, and it carries
`step.create-pr.pr_number=1342` — the exact fact `-096` lost.** The progression across four drained
landings is now measured, not argued:

| Landing | Result |
|---|---|
| `-075` (`-010`) | `complete: false`, **all 8** missing — no block at all |
| `-013` | `complete: true` |
| `-096` (`-012`) | `complete: false`, **1** missing (`pr`) |
| `-088` (`-016`) | **`complete: true`, 0 missing**, plus `total_billing_weighted`, `merge_commit`, per-step facts |

⛔⛔ **R82 already narrowed this spec's Objective once; it must narrow AGAIN.** The claim *"the
channel `-080` built is not being filled"* is now refuted for the current producer: three of the last
four landings filled it, and the newest fills it completely. **A spec opening on the wider claim
sends its run hunting a systemic break that the evidence contradicts.** What survives — and what D1
is actually for — is unchanged and is now the whole of it: **the producer cannot fail its own
contract.** `-075` emitted nothing and reported `[OK]`; `-096` lost a mandated fact and reported
`[OK]`; `-088` emitted a complete block and reported `[OK]`. **Three different contract outcomes,
one indistinguishable step result.**

**Inbox `-002` generalises `e9ef2c` into the deliverable's actual shape: record a step's PARTIAL
FAILURE in structured facts, not only in `display_detail`.** `-096`'s `create-pr` carried
`display_detail: "#1338"` and no `facts` sub-dict; `-088`'s carries `step.create-pr.pr_number=1342`.
The difference is invisible at the step in both runs. ⇒ The check D1 installs must read the step's
**declared** `records_facts` against what it actually recorded — a step that declares a fact and
records none must fail there, not two ordering bands later in a consumer.

⭐ **D0's indeterminate cause (a) is now DIRECTLY EVIDENCED, and this closes it.** `-088`'s
`lessons-capture` emitted the duplicate landing `-015` **from a `0.1.1240`-era served body** — the
version documented as lacking `emit-landing.md` — while the same run's terminal step emitted a
complete `-016`. **The same run, two bodies, two contract outcomes.** Cause (a) — the step ran against
a cache lacking the standard — is no longer a hypothesis leaning on a dated incident; it was observed
directly. ⛔ D0 may now report (a) as ESTABLISHED for the `-015` case specifically, and must still
report the `-075` case as `indeterminate` — a different run, a different moment, no seating record.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`documented-invocations-...-018`** — *unattended mode was armed mid-run and nothing records whether it was ever disarmed.* The run’s defining conversational event was the mid-flight arming. **The transcript records the arming. It records no un-arming, and no artifact establishes the end-of-run state.** Everything after that point — the loop-back, the re-fired settle band, the merge-queue landing — ran without an operator gate, under `final_merge_without_asking: true`, `pre_merge_comment_barrier: fail_into_loopback`, `re_review_on_timeout: proceed`.

  ⭐ **The knob LOCATION is correct and must not be “fixed”:** the aspect notes the knobs live on the **manifest snapshot** — the prescribed per-run location for finalize knobs — rather than in a tracked config file. ⛔ **That is exactly why the residual state is hard to see afterwards:** the snapshot is per-run and nothing carries an arming record forward.

  ⛔⛔ **The retrospective structurally CANNOT close this**, and says so: the chat reduction is signal-selective (**9 of 977 turns retained**), so an un-arming performed without producing a retained turn would not survive into the population. It reports *not recoverable* — **and “not recoverable” is indistinguishable from “never happened” to every downstream reader.**

  **The ask, which is this spec’s own subject:** make the finalize run **report the posture it actually ran under, in the run’s own artifacts**, so a reader can answer *“did this plan merge unattended, and were the overrides plan-scoped?”* without reconstructing it from chat. Record the arming as a structured act with a scope (`unattended_armed_at`, the overridden knob set, the intended scope) rather than a conversational one. ⭐ *“A confident ‘the overrides were plan-local, so nothing leaked’ is precisely the claim this run cannot substantiate.”*

  ⚠ **SURFACE DELIBERATELY NOT ADDED.** The natural carrier is the manifest snapshot, whose surface (`manage-execution-manifest/**`) is claimed by the **LAUNCHED `PLAN-TRUTH-089`**. Adding it here would manufacture a collision against a live plan. **Re-scope this fold after `-089` lands.**

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-149-the-landing-payload-and-what-the-epic-learns-from-it.md` (PLAN-TRUTH-149)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
