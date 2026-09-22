# PLAN-TRUTH-104: A `clear` verdict over an empty population is reported as a checked negative

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-104-a-clear-verdict-over-an-empty-population-is-reported-as-a-checked-negative.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-23 from § 5 of the PR #1337 run report (foreign machine, ad-hoc `NO_PLAN` lane, merged
as `2cd1a19c8`). The report **observed the vacuity in its own run** — *"`verdict: clear`, but
`commitments_considered: 0` … the check was structurally vacuous, not a meaningful pass"* — and that
observation is the whole reason this defect is visible; credit is theirs.

⛔ **But the report's FRAMING is too narrow, and the generalization is this orchestrator's, derived
first-party at HEAD `2cd1a19c8`.** The report attributes the vacuity to its lane — *"`NO_PLAN` has no
findings ledger"* — which reads as a standalone-lane artifact that ordinary plans do not hit. **It is
not.** The vacuity is a property of the branch table, and it fires for **any** plan whose `pr-comment`
findings set is empty — which is the ordinary case for a PR no review bot filed against. Read as a lane
artifact this is a curiosity; read correctly it is a live defect on the mainline path.

## Objective

`review_commitments reconcile` computes its verdict as a cross-product:

```python
conflicts = [ ... for deletion in deletions for commitment in commitments if _binds(...) ]
return {'verdict': VERDICT_CONFLICT if conflicts else VERDICT_CLEAR, ...}
```

With `commitments == []` the cross-product is empty **by construction**, so `verdict` is `clear`
regardless of what the simplify pass deleted.

⭐ **The script is NOT the defect, and this must be stated before anything is changed.** Corroborated
first-party: `review_commitments.py:361` publishes `commitments_considered` and `deletions_considered`
in the same envelope as the verdict, alongside `proves: removal_conflict_only` and `gates_merge: false`.
That is precisely what this epic's standing rule demands of a set-guarding detector — *a check that can
return 0 from an empty population MUST publish the population size*. **The producer complies.**

**The consumer discards it.** `phase-6-finalize/standards/finalize-step-simplify.md:203–209` branches on
`verdict` alone, and its `clear` row reads:

> `clear` — **No deletion touched a committed line.** Proceed to Step 4 unchanged.

That sentence asserts a **checked** negative. Over an empty commitment set the true fact is an
**unchecked** one: *no commitments existed to check against.* The population is emitted and thrown away
one layer up.

⭐⭐ **The sharpest part: the guard already exists and covers one arrival path of two.** The same
three-row table's third row reads *"An UNKNOWN verdict, never a clear pass"* and routes `status: error`
to a recorded `review_commitment_reconciliation: unknown`. The doc therefore **already has** the concept
of a non-answer that must not be read as a pass — it applies it to the failure arrival path and not to
the vacuous-population arrival path, which reaches the same table through a `status: success`. This is
the epic's recurring vacuous-guard archetype in its most literal form: the anti-vacuity guard is
present, correct, and half-installed.

## Deliverables

Three deliverables — deliberately small; this is a narrow, well-located correction, not a redesign of
the reconciliation seam.

**D0 — GATE: establish the population before changing the table.** Two questions, both answered with
evidence before D1 writes anything:

1. **How often is the population actually empty on the mainline path?** Sample real plan runs for
   `commitments_considered == 0` at this step. ⛔ Do not answer this from the `NO_PLAN` lane, which is
   the report's own framing error — a lane with no findings ledger is trivially empty and proves
   nothing about ordinary plans.
2. **Which OTHER consumers of a population-publishing seam branch on the verdict alone?** This
   producer-complies / consumer-ignores split is a shape, not an instance. Sweep the finalize step docs
   for a branch table that reads a verdict field while its seam publishes a population beside it, and
   **publish the swept population and its size.** A member found here is folded into D1; the sweep's
   size is reported even if it finds nothing, so a zero states which zero it is.

**D1 — the branch table gains the arrival path it is missing.** Make a `clear` verdict over an empty
commitment population report as its own outcome — legible, non-fatal, and distinct from BOTH a checked
`clear` and an `error`-path `unknown`. ⛔ **It must not fail the step, must not block the phase, and
must not revert anything** — the seam carries `gates_merge: false` and that stays true. What changes is
that the step stops claiming *"no deletion touched a committed line"* when nothing was there to touch.
⚠ Settle the vocabulary against the row that already exists: `unknown` is taken and means *the check did
not run*; this is *the check ran over an empty population*. They are different facts and must not
collapse into one token.

**D2 — tests: three verdict shapes, three distinct outcomes, and a matched negative control.** One case
per arrival path — checked `clear` (non-empty commitments, no conflict), vacuous `clear` (empty
commitments), and `status: error` — asserting the three are **distinguishable from each other**, not
merely that none crashes. ⭐ **The matched negative control is the load-bearing one**: a run with a
non-empty commitment set and no conflict must still report an ordinary `clear`, or the fix has replaced
a false pass with a false alarm. ⚠ This epic has recorded the vacuous-guard archetype **being
re-introduced by a fix for it** (n≥6, see the anchor); a control that cannot fail is how that happens.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` *(expected
  READ-ONLY — the producer already publishes the population; touch it only if D1's vocabulary genuinely
  needs a new emitted field, and record the reason if so)*
- `test/plan-marshall/phase-6-finalize/` *(the review-commitments test module)*

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/**` — `scope_creep_check`’s finding-type rejection, added 2026-09-03 by the drain fold of `deployment-and-refresh-gaps-009` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — witness 3’s bulk re-stamp of head-dependent steps, same fold (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/` — `qgate-mechanical-checks`’ `declared_scope_reconciliation`, added 2026-09-04 by the drain fold of `documented-invocations-...-012` (verify-at-outline)

## Dependencies and Sequencing

✅ **MACHINE-DERIVED at staging (`corpus cross-check`, 2026-08-23 — 152 specs / 7 sibling epics / 7
live plans).** ⭐ The hand-written version named ONE collision and **missed two**, both cross-epic —
the same R39 failure that recurred on `-103`. ⛔ Re-derive again at emit time.

- ⛔ **`PLAN-TRUTH-097` — SERIALIZE, confirmed by the machine map.** One-file overlap on
  `finalize-step-simplify.md`. `-097` is the epic's largest staged plan (14 deliverables, already above
  the split guard of 12) and its DB deliverable acts on the `verdict_inputs` declarations of six SILENT
  head-dependent finalize steps, `finalize-step-simplify` among them. ⛔ **This is exactly why `-104`
  was NOT folded into `-097`**: `-097` cannot absorb more without a split, and the two changes to that
  file are different subjects — *whether the step re-fires* vs *what its reconcile verdict means*.
- ✅ **`review-apparatus/PLAN-PR-030` — cross-epic, one file (`review_commitments.py`). CHECKED AT
  STAGING: NOT a duplicate; ordering constraint only.** *(Missed by the hand-written map.)* PR-030's
  item on this file is **G17, the dead guard** — `cmd_reconcile` catches `(OSError, ValueError,
  KeyError)` where the callee has no error-return branch, and PR-030 drops `KeyError`. That is the
  exception tuple; `-104` is the branch table in a different file, and PR-030 touches
  `finalize-step-simplify.md` nowhere. ⭐ **The two are allies, not rivals**: PR-030's stated principle
  — *"a dead guard against a shape the callee never produces reads as defence and provides none"* — is
  the same principle `-104` applies one layer up, where a guard that DOES exist covers one arrival path
  of two. Cite it; do not re-derive it. ⚠ `-104` declares `review_commitments.py` READ-ONLY, so
  contention is minimal — but serialize if `-104`'s D1 vocabulary ends up needing a new emitted field.
- ⚠ **`code-intelligence-substrate/PLAN-CIS-052` — cross-epic, one file
  (`finalize-step-simplify.md`).** *(Missed by the hand-written map.)* CIS-052 is `staged`, is that
  epic's **recommended first pair**, and CIS is under a standing 2026-08-09 operator hold. Its subject
  is finalize dispatch observability. ⛔ Check the SUBJECT before pairing — R14 records a 3-file overlap
  with CIS-052 that understated a direct contract conflict for `-100`.
- **Depends on:** nothing.

## Claim Labels

- OBSERVED: `reconcile` returns `VERDICT_CLEAR` whenever `conflicts` is empty, and `conflicts` is a cross-product over `commitments × deletions` — read at `phase-6-finalize/scripts/review_commitments.py` § the `conflicts` comprehension and its return, `:340-356`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: review_commitments.py:341-357 cross-product unchanged; verdict is CONFLICT if conflicts else CLEAR
- OBSERVED: the same envelope publishes `commitments_considered` and `deletions_considered`, so the PRODUCER complies with the population rule — read at `review_commitments.py` § `:361`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: review_commitments.py:362-363 still publishes commitments_considered and deletions_considered beside the verdict
- OBSERVED: `finalize-step-simplify.md`'s branch table has exactly three rows; its `clear` row asserts *"No deletion touched a committed line"* and its `status: error` row already says *"never a clear pass"* — read at `phase-6-finalize/standards/finalize-step-simplify.md` § `:203-209`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: finalize-step-simplify.md:208-212 table has exactly 3 rows; clear and status-error wording verbatim as quoted
- OBSERVED: the step rendered `reconcile clear` with no population beside it on a real run — read at the archived `status.json` for `cloud-lane-build-gate-reads-one-field-short` § `phase_steps["6-finalize"]["finalize-step-simplify"].display_detail`.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Named archived plan dir not found; only inbox archive messages survive, no live status.json to inspect
- HYPOTHESIS: the vacuity generalises off the `NO_PLAN` lane to any plan whose `pr-comment` findings set is empty — confirm/refute at `review_commitments._read_pr_comment_findings` § its call path, sampled over real plan runs (verify-at-outline). ⛔ **This is the claim the report's own framing denies; D0 must settle it on the MAINLINE path, not on `NO_PLAN`.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to D0(1); mainline-path sampling not performed this pass
- HYPOTHESIS: other finalize branch tables read a verdict while their seam publishes a population beside it — confirm/refute at D0's sweep of the finalize step docs (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to D0(2) finalize-doc sweep; not performed this pass
- Verify-first clause: the new vocabulary must not collapse into the existing `unknown` token — *the check did not run* and *the check ran over an empty population* are different facts and must stay separable.

---
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause on an unbuilt D1 vocabulary
- OBSERVED: the three same-seam instances and their four siblings, each quoted from a lesson recording a live run
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: References lesson-quoted historical instances; not independently re-derivable from current source
- HYPOTHESIS: a single reporting change (a distinct empty-population verdict token) addresses all three `review_commitments` instances — confirm/refute at `phase-6-finalize/scripts/review_commitments.py` § `_read_pr_comment_findings` and its verdict-emitting return (verify-at-outline)
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward hypothesis on an unbuilt reporting-change design
- HYPOTHESIS: PR #1340's `population_size` / `blind_spots` columns are the right vehicle for the plugin-doctor roster fix — confirm/refute at `pm-plugin-development/skills/plugin-doctor` § the rule-result schema (verify-at-outline)
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: References a different plan (plugin-doctor roster) schema question, not this plan subject
- ⛔ **Counts in the source message are the filing plans' own and were NOT re-derived by the router.** Treat them as a sample of the corpus, never an enumeration — this plan's own D0 must derive the population.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Advisory caution note about the router counts, not an independently checkable state claim

## ⭐⭐ INDEPENDENTLY CONFIRMED BY TWO LIVE PLANS — and one instance is SHARPER than this spec's framing

Surfaced 2026-08-24 by the first orchestrator sweep of live plans' findings stores. **Neither was
visible through the sanctioned read path** (`PLAN-TRUTH-109`), and neither had reached the epic.

- `metrics-ledger-readers-and-timestamp-provenance` filed: **"review_commitments reconciliation is
  structurally vacuous at order 8"** — this spec's exact subject, found independently.
- `plugin-doctor-detector-coverage-residue` filed: **"review_commitments reconcile saw 0 commitments on
  a run with 8 resolved self-review findings"**.

⛔⛔ **THE SECOND ONE BREAKS THIS SPEC'S FRAMING AND D0 MUST ABSORB IT.** This spec reasons throughout
from an **empty** commitment population — *"with `commitments == []` the cross-product is empty by
construction"*. **That run was not empty of findings: it had EIGHT resolved self-review findings and
the reconcile still saw ZERO commitments.**

⇒ **There is a second, independent path to a vacuous `clear`** — not "no findings existed" but
**"findings existed and did not become commitments."** The two have different causes and different
fixes: the first is a population that is genuinely empty; the second is a **read that does not see the
population it is supposed to.**

⚠ **D0's first question is re-scoped accordingly.** It currently asks *how often the population is
empty on the mainline path*. It must ALSO ask: **when findings exist, do they become commitments the
reconcile can see?** ⭐ A `resolved` self-review finding may be precisely the case the commitment read
skips — and if so, the vacuous `clear` fires **hardest on the runs that did the most review work**,
which is the opposite of the harmless reading. ⛔ **Do not fix D1's vocabulary before D0 settles which
of the two paths produced the observed zeros** — a "vacuous population" token would mislabel the second
case as an empty one.

## Folded from the PLAN-TRUTH-096 drain (2026-08-24) — a THIRD instance, on R92's path

Inbox `-005`. The permission-prompt aspect (Aspect 9) emits `prompts[0]` on **every** finalize-step
run, and nothing distinguishes *"no prompt fired"* from *"a prompt fired and the reducer discarded
it."*

The mechanism is R92's second path exactly — not an empty population, but **a read that cannot see
the population it is supposed to**:

- The aspect declares itself conditional on a `--session-id` being present. One was, so it ran and
  was in scope.
- Its only transcript reader is `extract-chat-signal`, whose reduction keeps operator text turns and
  `operator-decision` gate records and drops everything else — **2020 of 2031 raw turns dropped**
  across the two transcripts.
- A permission prompt is neither an operator text turn nor an `AskUserQuestion` gate decision, so it
  **cannot survive that reduction** at all.

⭐ **The aspect's own severity contract is what makes this sharp, and it is sound**: a prompt is an
*observed event*, "there is no inference chain whose confidence could reasonably be below high."
Precisely so — the aspect has **no observation channel in this mode**, yet its output is shaped
identically to an observation that found nothing. High confidence attached to a channel that does not
exist is worse than a missing figure.

⇒ This spec's remedy must cover the **channel-absent** case, not only the empty-population case. A
verdict is admissible only when the reader can name the population it examined; an aspect whose input
reducer structurally cannot carry its subject must resolve to `indeterminate`, never to a shaped zero.

## Folded from the PLAN-TRUTH-088 drain (2026-08-24) — inbox `-008`, and a THIRD arrival path

**"A detector that reports non-ambiguity must have measured what it is confident about."** A
detector emitting a *no-ambiguity* verdict is asserting a property of a population it must therefore
have enumerated — and the observed detectors emit it as a default when the comparison could not be
made at all.

⭐ **This is a THIRD arrival path at the same vacuous verdict, and the three are worth keeping
distinct** because they need different fixes:

| # | Path | Instance |
|---|---|---|
| 1 | the population is genuinely empty | the original `commitments × deletions` cross-product |
| 2 | the read cannot SEE its population | R92's `review_commitments` on a run with 8 resolved findings |
| 3 | **the comparison was never performed and its absence renders as the negative** | this message; and `scope_creep_check` rendering an unmeasured comparison as a clean zero (one of `-088`'s nine unfixed findings) |

⛔ Path 3 is not a special case of path 1: there is no population to be empty, because the measurement
step did not run. A fix that only publishes `population_count` closes 1 and 2 and leaves 3 reporting
`0` beside a `count: 0` that is equally unmeasured. ⇒ The verdict vocabulary needs a value for
**"not computed"** that is distinct from both "computed over nothing" and "computed, found nothing" —
which is the same three-way split `manage-lessons` already ships and `-109` is told to copy.

## Folded from the PLAN-TRUTH-094 drain (2026-08-25) — inbox `-001`, finding `ec6c97`

A FOURTH instance, and the first where **the green is CORRECT today** — which is precisely what makes
it the cleanest statement of this spec's thesis.

**`test_every_emitted_rule_id_has_provenance_entry` derives 75 of 97 emitted rule ids.** Its regex
matches only the quoted-dict form `'type': 'x'` and is blind to every `Finding(type='x')` emission,
missing nearly all of `_doctor_analysis.py`. An independent AST walk confirms **97/97 currently have
provenance rows**, so the test passes and its pass is not a lie.

⛔ **The defect is that it would stay green if any of the 22 it cannot see lost its row**, and it
**publishes no population size**, so no reader can tell 75-of-97 from 97-of-97. ⭐ This is the
population-derivation rule (`DERIVE completeness, never assert it`) meeting this spec's subject: the
verdict is not over an EMPTY population but over a **silently PARTIAL** one — a fourth arrival shape
alongside the three already recorded here.

⚠ **Keep it distinct from D1's empty-population case when scoping.** An empty population and a partial
population need different remedies: the empty case needs a three-way verdict, the partial case needs
the denominator published. A single `indeterminate` state does not cover both, and collapsing them
would reintroduce the defect one level up — the failure mode this epic has now recorded at n≥6.

## ⭐⭐ FOLDED 2026-08-27 — the seam this plan names was hit on THREE plans with THREE DIFFERENT empty-population causes

From the `lessons-handling-26-08-26-01` drain, message `-001` (7 lessons, *"a guard's verdict computed
over an empty or unexamined population"*). ⛔ **The router's suggested fold target `PLAN-TRUTH-042` is
SHIPPED** — verified first-party — so this plan inherits the cluster.

⭐⭐ **The decisive addition: `review_commitments reconcile` — THIS plan's seam — failed on three
different plans for three unrelated reasons, so a fix addressing any ONE cause leaves the other two
live.**

| Lesson | Empty-population cause at the same seam |
|---|---|
| `2026-08-23-20-001` | `verdict: clear` with `commitments_considered: 0` **while six review dispositions were on record** |
| `2026-08-24-08-001` | `deletions_considered: 5`, `commitments_considered: 0` — and the population is **empty BY CONSTRUCTION at that order**: simplify is order 9, create-pr is order 20, so no PR and no review exist yet. ⛔ **The guard as ordered can only ever examine nothing.** |
| `2026-08-26-10-001` | `_read_pr_comment_findings` derives commitments from `pr-comment` findings ONLY, so a run reviewed entirely by **self-review** has an empty population. That run carried **22 findings and 16 applied fixes**. |

⇒ **The three together are the argument for fixing the seam's REPORTING — a distinct verdict token for
the empty case — rather than any one population.** ⛔ Fixing the filter (10-001) or the ordering
(08-001) alone still ships a `clear` over nothing.

**Four further members of the cluster, for D0's population** — they are NOT this seam and may belong
elsewhere; enumerate them, do not silently absorb them:

- `2026-08-24-16-003` — `scope_creep_check` → `residual_count: 0` with `reason: no_baseline_sha`: **a counter that never counted.**
- `2026-08-24-09-002` — `scan_manage_invocation` → `findings: 0`, `population_size: ""`, while **four doc-vs-script divergences of exactly its class sat live in the tree it had just scanned.** ⚠ That analyzer is `PLAN-TRUTH-101`'s class; the two meet here.
- `2026-08-26-06-003` — **33 of 37 plugin-doctor rules** report `findings: 0` with an empty `population_size`. The 4 that DO fill the columns include `analyze_argument_naming` at **2805 with 304 blind spots** — a zero over ~89% coverage, legible ONLY because that one rule reports its population. ⚠ **This is `PLAN-TRUTH-112`'s roster**; route it there rather than absorbing it.
- `2026-08-09-22-004` — the standing rule itself: *"The distinction the reader needs is not pass vs fail — it is **looked and found nothing** vs **could not look**."*

## Claim Labels — folded 2026-08-27

> ↪ The bullets filed here on 2026-08-27 were merged into `## Claim Labels` above.
> `_parse_claims` reads ONE `## Claim Labels` section, so claims under a decorated
> second heading were structurally unstampable — the R97/R102 class, self-inflicted.

## ⭐ FOLDED 2026-08-27 (landing #1359) — a capture that supplies no base, so 4 of 5 rules skip on EVERY plan

From the `PLAN-TRUTH-098` landing drain (message `-002`).

**Aspect 12's capture supplies no base**, so **4 of its 5 rules skip on every plan**. ⛔ The aspect
reports normally; the skip is not a failure and not a finding — it is a **rule set that has never once
been evaluated**, on any plan, since it shipped.

⭐ This is a **purer instance than the ones already here**: the other members return a passing verdict
over an empty population, whereas this one *skips* — and a skip is even easier to read as "nothing to
report". ⇒ **D0's sweep predicate must cover BOTH shapes**: a verdict emitted over nothing, and a rule
that never runs. **A rule that skips on every plan and a rule that passes on every plan are
indistinguishable to a reader of the summary**, which is this plan's whole subject.

## ⭐ FOLDED 2026-08-31 — inbox drain (3 message(s))

- **`disjointness-gate-reads-declared-surface-wrong-011.md`** — review_commitments reconcile returned `clear` over an empty commitment population
- **`disjointness-gate-reads-declared-surface-wrong-012.md`** — Re-running a subset of a verification gate is not re-running the gate — the arm that was skipped is the one that catches what the new code introduced
- **`findings-read-absent-plan-dir-returns-clean-zero-009.md`** — review_commitments reconcile returns verdict clear over a population that is empty by step ordering, not by evidence

⛔ Each is the sending plan's own first-party observation, relayed verbatim by title. **Treat every one as a LEAD** — the drain did not re-derive them, and several were observed against tree states that have since moved. Re-ground at outline.

## ⭐ FOLDED 2026-09-03 — inbox drain (1 message(s))

- **`deployment-and-refresh-gaps-009.md`** (relayed from Token-Sheriff, plan `refresh-identity-and-scope-defences` PR #682) — *a signal that could not be observed must never be recorded as an observed pass.* **Two of its three witnesses fold here; the third is already owned elsewhere and is NOT re-staged.**

  ⭐ **The sender’s unifying rule is this spec’s own thesis, arrived at independently in a consumer project:** *“every green must state which kind of green it is — looked and found nothing, or could not look”*, and it names the in-tree precedents (`manage-lessons list-stalled`, `manage-findings findings_store_state`, `inbox list`) as the discipline the review/guard surfaces were never brought under.

  **Witness 2 — a guard whose failure reads as a pass.** `scope_creep_check` emits finding type `scope_creep_warning`; `manage-findings qgate` rejects that type as invalid, so the check exits 1 with `finding_persist_failed` on **every** invocation. Logged in the sending run at `2026-09-01T06:07:59Z`: *“scope creep therefore went UNMEASURED on tasks 11-13, not measured-clean”*. The same gap had already appeared earlier under a **different cause** (`could_not_look` / `no_baseline_sha` on tasks 1-5, `references.plan_creation_sha` unset). ⇒ **Across an 18-task plan, scope creep was never once actually measured, and nothing in the pipeline said so.**

  ⚠ **Two causes, one vacuous guard — and only one of them is already recorded.** Lesson `2026-08-27-07-001` (*“scope_creep_check can never fire: plan_creation_sha has readers and tests but no writer”*) is the **baseline-sha** cause. The **finding-type-rejection** cause is NEW here. ⛔ A fix addressing only the writer would leave the guard just as vacuous.

  **Witness 3 — head-dependent steps bulk re-stamped without being re-run.** Self-caught `[CRITICAL]` at `2026-09-01T09:58:28Z`: five head-dependent finalize steps re-stamped at one HEAD in a single loop; only `pre-push-quality-gate` and `push` had been earned. `finalize-step-simplify`, `finalize-step-security-audit` and `pre-submission-self-review` were stamped **without running**, over a delta containing production code. The sending orchestrator’s own words: *“Stamping a security audit as having validated code it never examined is precisely the false-green this session has repeatedly refused from tooling.”* All three were re-fired for real before merge. ⭐ Its stated legitimacy rule is worth carrying verbatim: **re-stamping is legitimate only when the delta is provably inert, and that inertness must be SHOWN, not assumed for a batch.**

  ⛔ **Witness 1 is NOT folded here.** *(A stale CodeRabbit review credited as current participation, because `participation_requires_update: false` skips the currency arm.)* It is already owned by `review-apparatus` as **`PLAN-PR-045`**, whose own header names the same upstream source message (`refresh-identity-and-scope-defences-002.md`). Verified against that epic’s corpus on 2026-09-03 before the drain declined to re-stage it. **Do not re-derive it into this spec.**

## ⭐ FOLDED 2026-09-03 (b) — TokenSheriff mid-flight data-point

**Source:** operator-relayed mid-flight observation from `TokenSheriff`, worktree
`plan-09-local-gate-truthfulness`. **RECURRENCE of the `deployment-and-refresh-gaps-009` witness-2
fold recorded earlier today** — recorded on that item, not as a second one. **No surface added:**
`phase-5-execute/**` was already added to this spec by that fold.

**Observed:** `scope_creep_check` returned `could_not_look` on **all three tasks**, because
`references.json` carries no `plan_creation_sha`. **No scope-creep comparison was made on any task.**

⭐⭐ **This is the THIRD independent observation of this guard never firing, and the second of THIS
cause specifically.** The three: lesson `2026-08-27-07-001` (*"`plan_creation_sha` has readers and
tests but no writer"*); `deployment-and-refresh-gaps-009` witness 2, which recorded **both** causes in
one 18-task plan — `could_not_look`/`no_baseline_sha` on tasks 1-5 **and** the `scope_creep_warning`
finding-type rejection on tasks 11-13; and now this run, all three tasks, the `no_baseline_sha` cause.

⭐⭐⭐ **The writer-absence is now DERIVED, not asserted.** `architecture search --content --pattern
plan_creation_sha` at HEAD `71279cc02` returns **10 matches over 5 files, and every one is a reader, a
doc, or a test**: `phase-5-execute/scripts/scope_creep_check.py` (4, the reader),
`phase-5-execute/SKILL.md` (2, doc), and three test files — `test_qgate_persist_contract.py`,
`test_scope_creep_check.py`, `test_scope_creep_could_not_look.py`. **`manage-references` does not
appear at all.** ⛔ Nothing writes the field. ⚠ The sweep is inventory-scoped, so a writer living
outside the crawled inventory would be missed — but a marketplace script IS in the inventory, so the
zero is trustworthy for the question asked.

⭐ **The operator's framing is the rule this spec exists to enforce, stated in one line:** *"a guard
that never ran is not a guard that passed."* `could_not_look` is the CORRECT return here — the guard
is honest about its own blindness. **The defect is that nothing downstream treats `could_not_look` as
different from a clean pass**, so an 18-task plan and a 3-task plan both complete with scope creep
never once measured and no phase transition refusing to read that as clean.

⛔ **Note what is NOT broken.** `scope_creep_check` already discriminates its zeros correctly and has a
dedicated test for it (`test_scope_creep_could_not_look.py`). **The producer is right and the consumer
is missing** — which is precisely this spec's subject, and means the remedy is at the phase gate, not
in the guard.

## ⭐ FOLDED 2026-09-04 — inbox drain (3 message(s))

- **`documented-invocations-...-002`** — *`check-manifest-consistency` reports a post-merge empty diff as a measured empty footprint.* `plan-retrospective` runs at `order: 995`, AFTER `branch-cleanup` merged the PR, so `--base-ref origin/main` already contained the plan’s own squash-merge. It reported `files_total: 0`, `oracle_available: true`, `diff_available: true`, and its `branch_cleanup_changes` rule returned **fail**: *“the observed diff is empty — no implementation file changed.”* **The plan changed 28 files**, and `git merge-base --is-ancestor 71279cc0 origin/main` exits 0. ⭐⭐ **The honest vocabulary ALREADY EXISTS in the same script** — an absent `--base-ref` records `base: unknown` and reports every diff-fed rule `indeterminate` — **the post-merge case simply never routes into it.** ⛔ Sibling aspects in the SAME run resolved the footprint correctly (`footprint_path_count: 33`; `declared: 24, found: 24, recall 100%`), so the data was available and one consumer chose the wrong branch. Remedy is one `git merge-base --is-ancestor` call.

- **`documented-invocations-...-012`** — *`declared_scope_reconciliation` reports a contradiction it cannot observe: it never reads intent.* Q-Gate `535ff7` fired `{declared scope wide, write-set narrow}` against `test/**` — an entry whose declared **intent is `read`**, in a deliverable whose `mutation_scope` is **empty**. ⛔ **There is no write-set for the declaration to be wider than.** And the 1999 “unenumerated” hits are dominated by `__pycache__/*.pyc` — 17 of the 19 quoted entries — **which no declaration would ever enumerate.** ⭐ The finding closes with a caveat that makes its own number unusable: *“the expansion hit the match ceiling, so this hit list is a LOWER BOUND on the contradiction”* — **a lower bound on a contradiction that does not exist.** Two cheap repairs, both over data already in hand: read `intent`, and exclude always-ignored artifacts from the expansion denominator. ⛔ **A check that a CORRECT declaration cannot pass trains its readers to dismiss it** — which is exactly what the `taken_into_account` disposition recorded.

- **`review-apparatus-030`** (carried-out finding `d4501c`, `PLAN-PR-038` / PR #1388, rescued from an archived findings store) — *`review_commitments reconcile` returns `verdict: clear` over `commitments_considered: 0`.* In a run that had **just resolved four self-review findings as fixed** in commit `6715ae207`. ⛔ **A clear verdict over an empty commitment population cannot distinguish “no conflict exists” from “nothing was loaded to compare against”** — and the seam’s whole purpose is to catch a simplify deletion that reverses a review decision made earlier in the same run. With an empty population it cannot catch any. ⭐ The `finalize-step-simplify` agent **did not trust the verdict** and re-checked by hand (`6715ae207` touched README/target.py/pyproject/test_runner; the proposed deletion was in `build_server.py`, disjoint) — **so no wrong deletion landed, but the guard supplied no evidence for that conclusion.** ⭐ This spec’s Expected Surface already names `review_commitments.py`, so the fold adds no surface.

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

**Theme 5 folds here in full — the document's own name for it is *"Which kind of zero is this?"*, which is this spec's subject stated in four words.**

⭐⭐⭐ **The document's cross-cutting observation #2 is the strongest external validation this spec has:** *"**Which kind of zero is this?** is the corpus's single most common defect shape. It appears in at least NINE findings across SIX themes"* — `skipped` meaning both *did not apply* and *could not resolve*; `could_not_look` reported as clean; a fail-closed default indistinguishable from a real invalidation; an empty skill set; a surfacer with no applicable detectors recording `done`; a rate-limit notice counted as participation; *"0 new comments"* meaning both *reviewed clean* and *never reviewed*; a timeout meaning both *slow* and *not installed*; a green placeholder status meaning *nothing happened*. ⇒ **"Every instance is the same request: make the degraded case say which zero it is."**

- **§5.1 — a verification step whose canonical does not resolve records `skipped`.** `verify:module-tests` recorded `skipped` **not because module tests were unnecessary but because the canonical does not exist in the project** (six are registered; that is not one). ⛔ **`skipped` is doing two jobs.** Two aggravating properties: the outcome is **per-run**, so a permanently-unresolvable canonical produces an **indefinite run of clean-looking `skipped` records**; and **nothing reconciles the manifest's declared steps against the project's registered canonicals**, so there is no other detection surface. ⭐ Ask: a distinct `unresolvable` / `not_configured` outcome carrying the resolver's error and its `available[]` list, **and validate the manifest against `architecture resolve` at manifest-COMPOSITION time, not at execution time.**

- **§5.2 — the scope-creep guard has never measured anything. ⛔ FOURTH independent observation**, after lesson `2026-08-27-07-001`, `deployment-and-refresh-gaps-009` witness 2 (folded here 2026-09-03) and the TokenSheriff data-point (folded here as a recurrence). ⭐⭐ **The new content is the reframing, and it is decisive:** two separate plans reported it and both correctly called it *absence of evidence rather than a clean result* — **neither could say why.** ⇒ *"They were not two flaky runs but ONE SYSTEMIC GAP: the guard has no baseline on ANY plan."* **That converts a per-run anomaly into a population statement.**

- **§5.4 — a skill domain registered for a profile it declares no skills for.** The `documentation` module declares a bundle and a triage extension but **no `skills_by_profile`**, while `active_profiles` includes `implementation`. ⇒ a documentation task running that profile resolves an **empty skill set** — no `ref-asciidoc`, no `ref-documentation`, no `persona-documenter`. ⛔ **The task still runs; it runs on general knowledge, and an empty resolution produces no error and no warning, which is what makes it persist.** ⭐ Treat *"registered for an active profile but declaring no skills for it"* as a health-check smell — **an absent block cannot express *deliberately no skills*.**

- **§8.6 — ✅ A GUARD THAT WORKED, recorded as a POSITIVE and load-bearing for this spec's D-level work.** A simplify pass trimmed a near-duplicate line; `review_commitments reconcile` showed the trimmed line was **a fixed review commitment made earlier in the same run** — text that existed *because* a reviewer asked for it, and **whose apparent redundancy was the point.** The trim was reverted. *"Without it, the run would have silently deleted its own fix and shipped a PR whose review threads claimed a change the merged tree no longer contained."*

  ⛔⛔ **Read this BESIDE `review-apparatus-030`, folded here on 2026-09-04**, which recorded the same verb returning `verdict: clear` over `commitments_considered: 0`. **They are not in conflict — they are the two halves this spec must keep apart.** §8.6 proves the guard has **real, demonstrated catch value**, so the remedy for the empty-population case **must not weaken it**: publish the population and treat a zero as `indeterminate`, ⛔ **never disable or relax the guard.** ⭐ The document adds the reason it must stay mandatory: *"simplify and review-response have genuinely OPPOSING objectives — one removes redundancy, the other often adds it deliberately — and the reconcile is the only arbiter."* And: **treat a revert it triggers as a SUCCESS signal to report, not an anomaly to suppress**, so the guard is not optimised away as *"never fires"*.

## ⭐⭐ FOLDED 2026-09-05 (c) — PLAN-TRUTH-089 drain (2 messages). BOTH ARE THIS SPEC, AT OPPOSITE ENDS OF ONE SKILL.

### `planning-lane-...-003` — a post-merge empty diff is reported as `diff_available: true`, and a confident `fail` follows

`plan-retrospective/SKILL.md` instructs *"supply `--base-ref` whenever `--diff-file` is absent — it is how
the script obtains a diff at all."* Following that instruction on a **merged** plan:
`check-manifest-consistency run --mode live --base-ref origin/main` returned `files_total: 0`,
every `filtered_by_category` bucket zero — **alongside `oracle_available: true`, `majority_discarded:
false`, and `diff_available: true`.** It then emitted:

> `branch_cleanup_changes,fail,"phase_6.steps includes branch-cleanup but the observed diff is empty — the
> footprint resolved to no changed path at all, so no implementation file changed"`

⭐ **Re-run with `--diff-file` naming the merge commit's 51 paths, the same check PASSES** (*"50 changed
file(s), 1 filtered as bookkeeping"*). **The plan modified 51 files. The `fail` was an artefact of the
base ref.** ⛔ On a merged plan `origin/main..HEAD` is legitimately empty — the branch's content **IS**
main now — so the emptiness is a property of the query, not of the plan. ⇒ **`diff_available: true` over
a zero-file diff is this spec's exact defect: a coverage flag asserting a look that produced nothing.**

### `planning-lane-...-006` — a `not_evaluated` fragment is DROPPED, erasing the coverage gap it declared

The permission-prompt aspect **could not look** (its only input is the session transcript, which the
skill never reads) and emitted an honest fragment: `status: not_evaluated`, `population_examined: 0`,
and a `coverage_gap` finding saying so. **`compile-report` dropped the whole section** —
`sections_dropped[1]: Permission Prompt Analysis`.

⛔⛔ **A fragment reporting `status: success` with `prompts[0]` and a bare "No permission prompts
detected" renders WITHOUT COMPLAINT.** ⇒ **The honest declaration of not-looking is erased and the
vacuous zero survives — the exact inversion of what this spec exists to prevent.**

**Root cause: two halves of one skill disagree about the vocabulary of not-looking.**
`retro_sections.ZERO_DECLARED_UNMEASURED_STATUSES` is `frozenset({'not_evaluated', 'skipped'})`,
documented there as the statuses with which a fragment DECLARES it could not look — and the compile
stage does not honour that set. ⇒ **D0 must reconcile the two halves, not add a third.**

⚠ **Expected Surface widened in this same act**:
`marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — `check-manifest-consistency`'s
`diff_available` derivation and `compile-report`'s section-drop predicate (HYPOTHESIS,
verify-at-outline).

## ⭐⭐ FOLDED 2026-09-06 — `review-apparatus-033` drain (2 items, both this spec's exact archetype)

### Item 9 (`-012`) — two set-guarding outline checks ran over an empty population and NEITHER could say so

⭐⭐ **The rule violated is one this corpus already holds: *every set-guarding detector must be
population-derived; a check that can return 0 from an empty population MUST publish the population
size.*** ⇒ **Violated TWICE IN ONE STEP**, which is evidence the rule has no mechanical enforcement
anywhere — only prose. ⛔ **That makes it a D-candidate, not just an instance**: a rule broken twice in
one step by one author is not an authoring lapse, it is an unenforced contract.

### The `manage-logging read --phase` observation — a VACUOUS FILTER, and it was never emitted as a candidate

> Two reads with **different `--phase` values returned the same `total_entries: 396`**, and the shorter
> result was **exactly the tail of the longer one.**

⛔ **A filter flag that is accepted and does not filter** — the accepted-and-ignored shape this epic
folded into `PLAN-TRUTH-129` from a different seam, here producing a *confident count over an unfiltered
population*, which is squarely this spec.

⭐⭐⭐ **THE PROVENANCE IS THE MOST INSTRUCTIVE PART: it was observed during `lessons-capture` but sat
OUTSIDE that step's candidate population, so it was never emitted as a candidate-lesson at all.** It
survived only because a human wrote it into a landing's Residue and a sibling orchestrator forwarded it.
⇒ **A step's candidate population is itself a filter, and what falls outside it is invisible to every
downstream mechanism.** That belongs in this spec's shipped doc as the reason a population must be
published beside every verdict.

⚠ **Expected Surface widened in this same act**: `marketplace/bundles/plan-marshall/skills/manage-logging/**`
— the `read --phase` filter (HYPOTHESIS, verify-at-outline).

## ⭐⭐⭐ FOLDED 2026-09-07 — PLAN-TRUTH-128 drain. FOUR INSTANCES OF THIS SPEC'S SHAPE IN ONE RETROSPECTIVE.

### `freshness-gate-...-006` — four aspects report clean over an input channel the pipeline never supplies

| | Instance | Why it is this spec |
|---|---|---|
| **(a)** | `check-artifact-consistency` graded `affected_files_exact_match` **warn** (3 outline-only, 2 references-only), downgraded to one `info`, and set `forwarded_to_manifest: true` — but `check-manifest-consistency`'s five checks contain **no declared-vs-realized set comparison** | ⛔ **The forward has NO RECEIVER. A real 3-file delivery gap was detected and then lost.** |
| **(b)** | `permission-prompt-analysis` names the session transcript as its input; the pipeline supplies only `extract-chat-signal`'s reduction — **4 turns of 1689** — and a permission prompt travels on the tool-result denial channel the reduction drops | **The aspect's zero is a zero over 4 turns.** |
| **(c)** | `logging-gap-analysis.md` mandates a `VERIFY` observed count; `analyze-logs` publishes `top_tags[5]` only (STATUS 79, ARTIFACT 72, STEP 50, SKILL 49, DISPATCH 37) | **Any tag outside the top five can only be FABRICATED or silently dropped.** |
| **(d)** | `check-dispatch-audit` publishes `findings[0]` / `counts.total: 0` alongside `channel_completeness.confidence: low`, `ratio: 0.27`, `no_evidence: 9` of 16 | **The block-level honesty is real; the section-level verdict `compile-report` renders is `0 findings`.** |

⭐⭐⭐ **THE SENDER'S ROOT CAUSE IS THE MOST TRANSFERABLE SENTENCE IN THIS DRAIN:** *"none of the four
is wrong at the field level — each publishes accurate values — and all four are wrong at the level a
reader consumes."* ⇒ **This spec's defect is not a bad value; it is a TRUE value at the wrong
altitude.** A field-level audit passes all four.

⛔ **(d) is the one to build the detector on**: the confidence figure IS published and the summary
**does not inherit it**. ⇒ **D-line: a section-level verdict must inherit the lowest confidence of any
sub-block it summarises**, which is mechanically checkable, unlike the other three.

⚠ **(a) is separately actionable and cheap**: a forward whose named receiver has no matching check is a
**producer/consumer pair with no consumer** — detectable by comparing the forward target against the
receiving verb's declared check list, no semantics required.

⚠ **Expected Surface widened in this same act**:
`marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — `check-artifact-consistency`,
`check-manifest-consistency`, `analyze-logs`, `check-dispatch-audit` and `compile-report`
(HYPOTHESIS, verify-at-outline).

## ⭐⭐⭐ FOLDED 2026-09-07 (b) — PLAN-TRUTH-099 drain (6 items). ONE IS A ONE-DAY-LATER CONFIRMATION OF YESTERDAY'S FOLD.

| Msg | Item |
|---|---|
| `-016` | **let an honest `not_evaluated` fragment RENDER instead of dropping it** |
| `-008` | fall back to the shared footprint resolver when a base-ref diff is empty |
| `-009` | derive re-entry coverage from **dispatch rows**, not from the markers it checks |
| `-010` | emit `reduced_transcript` so it **survives its own TOON envelope** |
| `-017` | register `dispatch_boundaries` as an aspect, or hoist it out of log-analysis |
| `lessons-...-014` | `review_commitments` reconcile anchors on **line numbers**, which decay as the file grows |

⭐⭐⭐ **`-016` IS THE SAME DEFECT FOLDED HERE YESTERDAY** (the `-128` drain's item (a): `compile-report`
drops a `not_evaluated` fragment while a vacuous `success` fragment renders). **Reported independently
one day later by a different plan.** ⇒ **Independent rediscovery inside 24 hours settles it as a
property of the pipeline, not one run's luck**, and it is now the highest-confidence member of this
spec.

⭐⭐ **`-008` is the same shape as the `--base-ref` finding already folded here**: an empty base-ref diff
is treated as a measured empty set rather than as *the query could not reach the tree*. **The remedy
named — fall back to the SHARED footprint resolver — is a pointer at an existing seam, not a new
mechanism**, which is the right shape.

⛔ **`-009` is the sharpest of the six and generalises past this spec**: *derive coverage from the
dispatch rows, not from the markers it checks.* **A coverage metric computed over the very artifacts it
is auditing is circular** — it can only ever report on what was emitted, so a step that emitted nothing
scores as fully covered. ⇒ **D0 should look for other detectors keyed on their own output.**

⚠ **`-010` is a TRANSPORT defect, not a verdict defect, and must not be folded as one**: the reduced
transcript does not survive its own TOON envelope, so downstream aspects read a truncated input and
report cleanly over it. **It is the CAUSE of several members here rather than a peer of them** —
and this epic has an independent instance (TOON capturing only the first line of a multiline value).

⚠ **`lessons-...-014` is mechanically checkable**: an anchor that decays with file growth is a
positional binding where a semantic one belongs — the same defect class as a positionally-bound skip
row this epic has recorded before.

⚠ **Expected Surface widened in this same act**:
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` — the
reconcile anchor (HYPOTHESIS, verify-at-outline).

## ⭐ FOLDED 2026-09-07 (c) — PLAN-TRUTH-125 drain (1 item), AND A CONTAMINATED DENOMINATOR

`-003` (`plan-retrospective`), reinforced by the run's own summary:
**`check-artifact-consistency`'s failing 57% recall has a CONTAMINATED DENOMINATOR — six of its ten
"missing files" are `lessons-consult` PROSE BULLETS. Real recall ≈ 71%.**

⛔⛔ **This is the sharpest denominator defect this spec has drawn.** The metric is not merely wrong —
it is wrong in the direction that manufactures a failure, and **the contamination is invisible in the
verdict**: `57%` and `71%` are both plausible numbers and only enumerating the ten reveals that four of
them are not files at all.

⇒ **A recall figure must publish its denominator's MEMBERSHIP, not merely its size** — the same
membership-over-cardinality rule this epic applies to surfaces and to `(n=k/N)` markers, arriving at a
third instrument. ⛔ **A fix that only corrects the parser leaves every historical recall figure
uninterpretable**, so the remedy must make the denominator inspectable, not just cleaner.

## ⭐ FOLDED 2026-09-08 — lessons-handling drain (1 item)

`-020` (`phase-6-finalize`): **the merge barrier must RE-READ the provider, not the cached state.**

⛔ **A barrier that decides on a cached read is deciding on a state that was true, not one that is.**
⇒ This spec's family at the highest-stakes gate in the pipeline: **the verdict is accurate about its
input and its input is stale**, which is indistinguishable at the verdict from a fresh read.

⚠ **This epic already carries the matching incident**: `ci pr merge` once returned `merged: true` and
deleted the branch **without merging**, and the standing rule from it is *stamp PR ids from PR STATE,
never from the landing message.* ⭐ **Same principle, one layer earlier** — the barrier is where the
re-read is cheapest and the consequence largest.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-147-a-lane-reports-green-yields-or-transitions-without-the-artifact-its-own-gate-requires.md` (PLAN-TRUTH-147)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
