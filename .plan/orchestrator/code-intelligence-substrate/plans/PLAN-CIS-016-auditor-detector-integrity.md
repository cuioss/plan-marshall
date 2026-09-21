# PLAN-CIS-016: Audit Detectors Are Structurally Incapable Of Reporting What They Claim

epic: code-intelligence-substrate
workstream: WS-05

> Staged from the **first full-corpus audit sweep** (115 archived plans, 22 checks, 2026-07-26;
> the prior recorded run covered only 8 plans). Scale is what exposed these: three detectors emit
> confident zero/clean numbers that are **unmeasured, not healthy**. This is the epic's flagship
> archetype located inside the auditor that surfaced roughly half the epic's other plans — so every
> clean verdict that tool has ever produced inherits the doubt until these are closed.

## Objective

`audit-archived-plan-retrospectives` reports per-check counts that consumers (and this epic's
orchestrator) treat as findings. Three checks cannot produce a true positive at all: their predicate
reads a field that live data does not carry, scans for a marker that does not exist, or counts rows
that are pending by construction. Make each detector either able to fire, or explicitly report
`unmeasured` instead of a number that reads as health.

## ✅ RE-GROUNDED 2026-08-09 — ARMS A AND B BOTH STAND, AND B IS SHARPER THAN FILED

⭐ **This section replaces the "NOT yet orchestrator-verified" caveat below for arms A and B.** Both
were checked first-party against the implementing source at HEAD. **The plan's first deliverable is
no longer that verification for these two** — spend the budget on the fix.

**Arm A — STANDS, but the line number is stale and the mechanism is one step subtler.** The spec says
*"`audit.py:873` reads only `metadata.plan_source`"*. At HEAD the site is **`audit.py:1070-1074`**
(the file has grown), and it reads:

```python
plan_source = metadata.get("plan_source")
# `plan_source` populated by phase-1-init when sourced from a lesson;
# equivalent to `recipe_key` for matrix purposes.
if isinstance(plan_source, str) and plan_source.strip():
    inputs.recipe_key = plan_source.strip()
```

⇒ ⛔ **`recipe_key` is a FIELD NAME the auditor populates from `plan_source` and NEVER READS FROM
METADATA** — `grep` for `metadata.get("recipe_key")` returns **zero hits in the whole file**. So a
plan carrying `recipe_key` and no `plan_source` is invisible exactly as filed. ⭐ **And the inline
comment asserting the two are *"equivalent for matrix purposes"* is the vacuous-authority instance
this arm already claims** — the equivalence is asserted in a comment and implemented as a
one-directional read. ⚠ **Re-derive the line number at outline; do not pin a test to `:1070`.**

**Arm B — STANDS, and the finding is BIGGER than filed: the TESTS are vacuous too.**
`architecture search --content --pattern "LOCK\] \(merge"` over the whole inventory returns
**6 rows / 3 distinct files, and EVERY ONE IS A TEST**:
`test/plan-marshall/audit-archived-plan-retrospectives/test_audit.py` (11),
`test/plan-marshall/manage-locks/test_locks_core.py` (7),
`test/plan-marshall/manage-locks/test_manage_locks_merge_lock.py` (7).
**Zero production emitters.**

⇒ ⭐⭐ **The detector scans for a marker no production code writes, AND its test suite is green
because the tests synthesise the marker themselves.** That is the vacuous-guard archetype with its
own regression suite certifying it — strictly worse than the spec's framing (*"a predicate whose
input never occurs"*), because a reader checking "is this covered?" finds passing tests.
⛔ **D-scoping consequence**: the fix is NOT only "make the detector report `unmeasured`". Either the
lock lifecycle must actually emit `[LOCK] (merge:*)` lines, or the check must be retired — and
**whichever is chosen, the tests must be re-pointed at the production emitter**, or they will keep
passing over the fix. ⚠ **Coordinate with `manage-locks`**: the emission half is that skill's
surface, and this plan owns the auditor. Decide the split at outline rather than absorbing it.

## ⚠ Mechanism — three defects, audit-reported; each carries its own lesson file

Filed at `.plan/local/lessons-learned/2026-07-26-22-00{1,2,4}.md`. **All three are audit-reported and
NOT yet orchestrator-verified against the implementing source** — the first deliverable is that
verification, because this plan's whole subject is detectors trusted without it.

### A — recipe-routed plans are invisible (`2026-07-26-22-001`)

- CLAIMED — `audit.py:873` reads only `metadata.plan_source`, while live plans carry `recipe_key`.
  Decision-rule **Row 2 is therefore unreachable**, producing **false drift** on every recipe-routed
  plan and a permanent `recipe_routed: 0/114`.
- CLAIMED — `decision-rules.md:475` asserts a **composer/audit parity that does not hold**. That is a
  documented-authority claim contradicted by the implementation — the same family as PLAN-73 / -74 /
  -75, now n=4.
- **A permanent `0/114` is the tell.** A detector that has never once fired across a full corpus is
  presumptively broken, not presumptively reassuring.

### B — merge contention is never measured (`2026-07-26-22-002`)

- CLAIMED — `merge-window-accounting` scans for a `[LOCK]` marker that **appears nowhere** in
  `.plan/local/logs/` (verified by the audit's own marker histogram). `contended_plans: 0` is
  **unmeasured, not healthy**.
- This is the *saturated-marker* vacuous-guard shape the epic already tracks — a predicate whose
  input never occurs.

### C — 70% of the quality-chain "genuine" count is a permanent false positive (`2026-07-26-22-004`)

- CLAIMED — **310 of 1519** quality-chain rows are **pending by construction** (267
  `assessments.jsonl` + 41 sonar summaries; **308 have empty titles**). That is ~70 % of the
  genuine-signal count — a standing false positive that inflates every quality-chain report.
- Distinct from A and B: here the detector *does* fire, but its positives are structural noise, so
  the number is untrue in the opposite direction.

### D — a prune-cause detector attributes the drop to the wrong mechanism (folded 2026-08-02)

⛔ **THIRD sighting.** Filed first-party from PR #1079 (inbox `plan-cis-027-…-008`), independently
corroborated by `truthful-signals-026` item 3 on PR #1077, whose own prior sighting was
`review-apparatus-010` item 4. **A third independent sighting makes this a member of this plan's
class, not a separate incident.**

`check-routing-decisions` emitted `mis_prune: sonar-roundtrip … no_code_delta …
predicate_evaluated`. The predicate re-evaluation is *arithmetically correct* — the realized
footprint did touch production code. But `sonar-roundtrip` **was never removed by that predicate**.
The decision log records the real cause verbatim: `lane_resolution — dropped sonar-roundtrip …
effective tier full exceeds the standard posture cutoff`.

⭐ **The disproving fact was already inside the aspect's own fragment.** `check-routing-decisions`
emits `recorded_lane_decisions[]`, and the posture-cutoff record sits in that very list. **The
aspect loaded the contradicting evidence, rendered it, and did not consult it.**

⭐ **It is a precision defect, not merely noise.** Two sibling steps were dropped by the same posture
pass in the same run — `finalize-step-security-audit` (tier-full cutoff) and `adr-propose` (explicit
`off` override) — and **neither was flagged**. So the check does not flag posture drops in general;
it flags exactly those posture drops that happen to carry a `prunable_when` predicate the footprint
refutes. **That is an arbitrary population, which makes the finding neither reliably present nor
reliably absent** — a fourth failure mode alongside cannot-fire and fires-but-counts-noise.

#### ⛔ D — the exact mechanism, now MEASURED first-party (folded 2026-08-03 from the CIS-028 drain)

⭐ **FOURTH sighting, and the first one where the mechanism was read off disk rather than inferred.**
The branch-on-removal-cause machinery the fix below proposes **already exists** — and it is broken:

`check-routing-decisions.py` carries a `_REMOVAL_CAUSE_PATTERNS` tuple whose `posture_cutoff` member
is (verified on `main`, `check-routing-decisions.py:105-109`):

```python
r'lane_resolution\s+—\s+execution_profile=[^,]+,\s+dropped\s+(?P<steps>.+?)'
r'\s+from\s+phase_6\.steps\s+\(tier above posture cutoff\)'
```

The emitter's contracted shape (verified on `main`,
`manage-execution-manifest/standards/decision-rules.md:418`) is:

```text
lane_resolution — dropped {step} from phase_6.steps (execution_profile={posture}): {reason}
```

**Different field order, different trailing clause — the regex cannot match, ever.** `removal_cause`
falls through to `predicate_evaluated`, `no_code_delta` is re-evaluated against a footprint holding
`.py` files, and the check FAILs. ⛔ **This affects EVERY standard-posture plan**, because
`standard` always drops `sonar-roundtrip` by posture — so the aspect's own highest-severity output
has been false on every such run since the emitter's line shape changed.

⭐ **The sharpest form of the vacuous-authority archetype yet recorded.** The comment above the tuple
asserts each shape is *"copied verbatim from `decision-rules.md` (the emitter contract)"*, and the
module docstring explains that a step matched by these mechanisms is skipped because *"its predicate
never fired, so its absence proves nothing about the footprint"*. ⇒ **The guard documents the exact
defect it produces, and asserts a verbatim-copy property that is false on disk. Nothing observes the
copy.** The drift is not in prose describing behaviour — it is in a **regex whose correctness is
asserted by a comment and checked by nobody**.

⛔ **Scope obligation carried into D1**: re-derive the OTHER THREE members of
`_REMOVAL_CAUSE_PATTERNS` (`unresolved_ask_provider_drop`, `simplify_inactive`,
`ceremony_finalize_selection`) against the live emitter **in the same pass**. One member drifted;
that is a sample of one and says nothing about the other three — this plan's own
named-list-is-a-sample rule applied to itself (lesson `2026-08-03-06-002`).

⭐ **Preferred remedy, stronger than fixing the regex**: emit the line through a **shared formatter
both sides import**, so the shape has exactly one home and the consumer parses what the producer
produced. A hand-written test fixture drifts in lock-step with the wrong copy and would not have
caught this.

**Root cause**: the check re-evaluates *every* absent prunable step's `prunable_when` predicate
unconditionally, without first asking **why** the step is absent — and where it *does* ask, it asks
through a pattern that cannot match. **Fix**: branch on the recorded
removal cause — parse the `lane_resolution` entries the aspect **already loads**, re-evaluate
`prunable_when` only when the recorded removal was predicate-driven, and report posture-cutoff or
explicit-`off` removals as *intentional configuration outcomes* with no mis-prune verdict.
⭐ **This needs no new input** — it is a consumption change over data the aspect already reads.

## Deliverables

#### ⭐ Class member E — `RE_ENTRY_COVERAGE` (folded 2026-08-03, lesson `2026-08-03-14-004`)

**FIFTH member, and the purest instance of failure mode A the epic has recorded.** Its precondition
is **the presence of a marker it exists to detect the absence of** — so it is vacuous at *exactly*
the value it was written to catch, and green everywhere else.

⇒ ⛔ **A guard whose precondition is its own subject can never fire on its subject.** Add it to D1's
classification pass; it is *cannot-fire* (class A), and its remedy is the same reporting change the
other A-members need: **publish the population the precondition admitted**, so a pass over an empty
admitted set is distinguishable from a pass over a full one.

#### ⭐⭐ Class members F and G (folded 2026-08-03 from PR #1086) — and F is a NEW failure mode

**F — the script-failure sweep measured a log it was still writing to.** From `…-010`: it counted 11
failures from a log **still open for its own appends** — and **missed one of its own**, which
occurred after it sampled.

⛔⛔ **This is a fifth failure mode and it is not on the existing list** (*cannot-fire*,
*fires-but-counts-noise*, *fires-on-an-arbitrary-population*): **the detector is INSIDE its own
population and samples it before it finishes contributing to it.** ⇒ Its count is not merely a floor
— it is a floor **that systematically excludes the detector's own contribution**, so the one class of
failure it can never report is its own. ⭐ **Add this mode to D1's classification vocabulary; the
remedy differs from the other four** (sample at a settled boundary, or exclude self and declare it),
and a detector that cannot see itself is a distinct hazard from one that sees an arbitrary set.

**G — `config_hash` drift fired at 4 of 4 phase boundaries.** Rescued from PR #1086's withheld
medium-confidence proposals so it is not lost with the plan directory. ⭐ **A warning that fires at
100% of boundaries is not a detector** — it is a constant, and it trains readers to ignore the
channel it shares with real warnings. Classify under *fires-but-counts-noise*, and note that its
remedy is the inverse of the vacuous-guard remedies: **the others never fire and this one never
stops.**

### D1 — GATE: verify every claim against the implementing source, then classify (mutates nothing)

**Do not fix from the lesson text.** Confirm or refute each claim at its named line — `audit.py:873`,
the `[LOCK]` scan site, the quality-chain row builder, the `check-routing-decisions` prune
re-evaluation — and classify each as *cannot-fire* (A, B), *fires-but-counts-noise* (C), or
*fires-on-an-arbitrary-population* (D), because the remedies differ. Settle the reporting contract:
a check that cannot substantiate its verdict must emit **`unmeasured`** (refusing, per ADR-009's
no-vacuous-success posture), never `0`.

### D2 — A: read the field live data actually carries

Make the plan-source predicate read `recipe_key` (and whatever else live plans carry), so Row 2 is
reachable. **Correct `decision-rules.md:475`** — it asserts a parity that does not hold; leaving it
is the defending-documentation pattern this epic keeps finding.

### D3 — B: measure contention, or say it is unmeasured

Either scan for the marker the logs actually contain, or report `contended_plans: unmeasured` with
the reason. **A zero that cannot be distinguished from "no data" is the defect** — whichever route
D1 picks, the two states must be distinguishable in the output.

### D4 — C: exclude structural pendings from the genuine count

Partition the quality-chain rows so pending-by-construction entries (empty-title assessments, sonar
summaries) are excluded from the genuine-signal count or reported in their own bucket — the same
partition shape PLAN-51 shipped for `sections_omitted` / `sections_dropped`, which is the proven
pattern here.

### D5 — the class guard

A per-check assertion that a detector which has produced **zero positives across a full corpus** is
surfaced as suspect rather than silently reported as clean. This is what would have caught all three
without a human noticing. Scope it to reporting, not to blocking.

### D6 — tests

Per defect: a fixture that produces a true positive and is verified to FAIL against the current
detector (A, B), a fixture asserting structural pendings are excluded (C), and one asserting
`unmeasured` is distinguishable from `0`.

**Six deliverables — at the split guard.** D1 is a gate and D5/D6 are cross-cutting, so the
implementation surface is effectively three. If D1 finds the three defects do not share a reporting
seam, **split C out** (it is a different failure direction) rather than proceeding unsplit.

## Expected Surface

- CLAIMED: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — `:873` plan-source
  predicate, the `[LOCK]` scan site, the quality-chain row builder (exact lines verify-at-outline)
- CLAIMED: `.claude/skills/audit-archived-plan-retrospectives/.../decision-rules.md:475` — the
  refuted parity assertion
- HYPOTHESIS: the per-check `checks/*.md` docs for the three checks — updated in lock-step with any
  verdict-vocabulary change (verify-at-outline)
- OBSERVED: the three lesson files under `.plan/local/lessons-learned/`, to be retired at finalize
- HYPOTHESIS: tests for this project-local skill — confirm the test module exists before assuming it

⚠ **Evidence location:** the corroborating corpus was dormated on 2026-07-26. Rows referenced by the
report live at `.plan/temp/dormated-plans/`, and the report itself at
`.plan/local/audit-reports/20260726T202149Z.toon`. **A re-run of the audit will now find an EMPTY
corpus** — treat any zero-finding re-run as unverified until the path is confirmed (that is itself
this plan's subject matter).

**Disjointness:** `.claude/skills/audit-archived-plan-retrospectives/**` — a project-local meta
skill, disjoint from every bundle plan in the queue including PLAN-57, PLAN-75, PLAN-62.

## Dependencies and Sequencing

- Independent of everything currently in flight.
- **Relationship to PLAN-75:** both are "the tool reports clean while structurally unable to see the
  problem", but different surfaces (auditor vs manifest composer). No file overlap; may run
  concurrently.
- Not gated on #1003.

## Notes

- **The auditor surfaced roughly half this epic's plans.** Three of its detectors being unable to
  fire means the epic's own evidence base has an unmeasured margin — not that past findings are
  wrong, but that *absence* of findings from this tool has never been evidence of absence.
- Fourth instance of the **vacuous-authority / defending-documentation** family (`decision-rules.md:475`
  asserting a parity that does not hold), after PLAN-73, PLAN-74, PLAN-75.
- Scale was the detector: a 8-plan run cannot distinguish "0 findings" from "cannot find". The
  full-corpus sweep is what made `0/114` legible as a defect — worth remembering when sizing future
  audit runs.

## Inherited Inbox Evidence (folded 2026-07-29 from `truthful-signals-003`)

⚠ **Leads, not facts** — re-verify before scoping.

**Two anchor tables cannot match their producers — both vacuous-guard, occurrence 5+, both in the
measurement surface:**

| Source | Origin | Claim |
|---|---|---|
| `exploration-share-is-unmeasured-006` | PLAN-99 / #1043 | `check-manifest-consistency` **rule M3 can never fire**, and it hid a real violation on the very plan that exposed it |
| `one-coherent-automated-review-contract-010` | PLAN-92 / #1041 | The plan-efficiency **budget anchor table is keyed on vocabulary no producer emits** |
| `self-review-...-008` | PLAN-81 / #1042 | The constructive half — the anchor table is also **incomplete** (`multi_module` rows missing) |

**M3 mechanism**: tests `steps != ['module-tests']` against the composer's actual
`['verify:module-tests']`, so the predicate cannot fire.

⛔ **THIS PLAN IS AT THE SIX-DELIVERABLE SPLIT GUARD — DO NOT GROW IT TO ABSORB MORE.** The
`audit.py` `Path.cwd()` production defect was deliberately staged as **PLAN-11** rather than folded
here, for exactly this reason. ⛔ **PLAN-11 collides with this plan on `audit.py` — never pair, and
run PLAN-11 first.**

⚠ **Every set-guarding detector must be POPULATION-DERIVED.** Both defects above are the same shape:
an anchor keyed on a vocabulary nobody emits. Deriving the producer set is the general fix; patching
the two named rows is the instance fix.

## Second Evidence Fold (2026-07-29 — `truthful-signals-008` and `-009`)

⭐⭐ **`wrong-store-...-011` EXPLAINS WHY `shape_violation` IS VACUOUS, AND IT IS A DIFFERENT SUB-CLASS
THAN EVERY PRIOR INSTANCE.** The detection pairs a `decision.log` `(manage-config) effort
resolve-target` entry with a subsequent `[DISPATCH]` line. **The `resolve-target` entries are never
logged**, so the pairing has no left-hand side.

⇒ **This is a POPULATION vacuity, not a PREDICATE vacuity — the detector is written correctly and
starves for input.** ⛔ **The distinction is load-bearing: fixing the predicate would achieve
NOTHING. The producer must emit.**
⭐ **The corpus has recorded 5+ vacuous guards as predicate defects; this is the FIRST identified as
producer-starvation.** Worth stating as a distinct sub-class in this plan's output, because **the two
have opposite fixes** and misclassifying one as the other guarantees a no-op change.

**`post-merge-review-...-010`**: `plan-retrospective`'s mode heuristic keys on `--iteration`
**presence**, so a real finalize-step dispatch **silently resolves to the mode that skips the
handshake**. ⭐ The observing plan *overrode the heuristic and said so*, which is why this is a report
rather than a corrupted retrospective. **Key on the dispatch site — the fact actually being asked
about — not on an optional counter.**

## Evidence Fold — 2026-07-29, from `truthful-signals-012` item 4

⚠ **Lead, not fact** — re-verify at outline.

**The execution-context dispatch audit emits zero-valued counts for categories it never evaluated.** A
category that was **never evaluated** and a category that was evaluated and **found nothing** both
render as `0`. The reader cannot distinguish "checked, clean" from "never looked" — a zero that means
two opposite things, emitted by a detector.

⭐ **This is the plan's own thesis arriving from the outside**: a detector whose output cannot express
*"I did not check."* Pair it with the (a)-arm requirement already in this spec — the fix is a
tri-state (`checked-clean` / `checked-found` / `not-evaluated`), not a sentinel value.

⛔ **Split-guard reminder, unchanged**: this plan is already at the six-deliverable guard. Fold this as
evidence sharpening the existing detector-integrity deliverable, NOT as a seventh. The `audit.py`
`write_persisted_report` / `--plan-dir` defect stays with **PLAN-11** and must not be absorbed here.

## Second Evidence Fold — 2026-07-29, `truthful-signals-014`

⚠ **Leads, not facts.** Three detector-integrity observations, plus a method note that may be the most
useful line in the fold.

- ⭐ **`record-dispatch-boundary` accepts 11 termination causes, its SKILL documents 6, and the detector
  counts 2 — THREE different populations for ONE vocabulary.** ⛔ **Ownership note**: the doc half
  (11 vs 6) is **PLAN-CIS-009's** and must not be re-scoped here. What belongs to this plan is the **third**
  population: a detector whose counted set is narrower than either the documented or the real one, so
  its distribution is silently partial. Fix the detector's population derivation; leave the doc to
  PLAN-CIS-009.
- **`compile-report` renders 13 script-failure findings as 13 EMPTY BULLETS** — the findings exist, the
  report shows nothing. A report that renders the right *number* of the wrong *content* is worse than
  omitting the section, because the count reads as evidence that the content is there.
- **`compile-report` calls a lost section a benign omission AND an empty section written** — two
  distinct failures both reported as success. Pairs exactly with the producerless-section finding
  already folded into PLAN-CIS-010; ⛔ **the distinction to enforce is "no producer exists" vs "producer ran
  and found nothing" vs "producer ran, produced, and the render dropped it"** — three states, currently
  one.

### ⭐ Method note — carry this into ANY detector this plan derives

From the sender's own population-derivation work: **a population-derivation predicate needed three
refinements before it was sound**, and its final zero is *"a discipline property, not a structural
one"* — **661 call sites examined, 0 currently affected, but 28 of 41 relevant sites sit at
`execution_mode='auto'`**, so the population is **one un-stubbed sibling away from being non-zero**.

⇒ **The census script is the durable deliverable; the number it prints today is not.** A detector that
reports `0` must be able to say whether that zero is structural (cannot occur) or disciplinary (does not
occur *yet*). ⛔ This plan is at the six-deliverable guard — fold this as a **property every derived
detector must satisfy**, not as an additional deliverable.

## Evidence Fold — 2026-08-08, RE-ROUTED here from `lessons-handling-…-003` cluster C08

⛔ **CORRECTED SAME DAY — READ THIS BEFORE THE SECTION BELOW. `2026-07-26-22-004` IS ALREADY THIS
PLAN'S D4; THIS FOLD ADDS NO SCOPE.** The re-route (from the sender's suggested `PLAN-CIS-022`) was
correct — it is a detector-population defect, not a token-ledger one — but on re-reading this spec, **D4
already says it, and already names the same two row classes** ("pending-by-construction entries
(empty-title assessments, sonar summaries)"). ⇒ **Treat everything below as CORROBORATION of D4 from an
independent source, NOT as a new item, and do NOT re-scope D4 on it.**

⭐ **Recording the error rather than quietly deleting it**, because it is this epic's own archetype
committed by its orchestrator: I folded a "new" finding into a plan that already carried it, having read
the message but not the target deliverable. **The dedup discipline is only as good as the read that
precedes it.** The one thing the fold contributes that D4 does not already carry is the framing in the
next paragraph, which is why the section is kept at all.

**`2026-07-26-22-004` — component assessments and Sonar scan summaries are counted as unresolved
pending findings: 310 of 1519 audit rows are PERMANENTLY PENDING BY CONSTRUCTION, inflating the
genuine-signal count by ~70%.**

⭐ **This is the sharpest instance of this plan's own thesis yet, and it points the opposite way from
every other member.** The rest of this plan is about detectors that report **zero** when they should
report something. This one reports a **large non-zero** that can never go to zero — 310 rows that no
action can resolve, because they are not findings at all. ⛔ **A pending count that cannot reach zero is
not a backlog, it is a mislabelled population** — and it is worse than a false zero, because a false
zero invites a check while a large backlog invites resignation.

⛔ **Fold as a SHARPENING OF D4's rationale, NOT as a deliverable** — the plan is at the
six-deliverable guard and D4 already owns the partition. The property D4 should state explicitly:
**a detector reporting a count must be able to say what would make that count zero.** A row class that
is unresolvable by construction belongs outside the population or in a separately-named bucket.

⚠ **The 310 / 1519 / 70% figures are quoted as the lesson recorded them and are NOT re-derived** — each
carries its own unpublished population. Re-derive before any of them is cited as a result.

**Claim labels** — OBSERVED: lesson id, component, category; the re-route decision.
HYPOTHESIS (verify-at-outline): that the pending-row predicate still admits component assessments and
Sonar scan summaries. Confirm/refute artifact: `manage-findings`' pending-row predicate.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
