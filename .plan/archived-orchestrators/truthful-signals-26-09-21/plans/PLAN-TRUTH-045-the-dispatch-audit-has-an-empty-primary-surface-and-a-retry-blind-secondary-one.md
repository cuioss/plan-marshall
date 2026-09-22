# PLAN-TRUTH-045: the dispatch audit's primary evidence surface is empty and its secondary one is retry-blind

epic: truthful-signals
workstream: WS-01

## Objective

The dispatch-discipline audit exists to catch a step that ran inline when it should have been
dispatched. **Both of its evidence surfaces are broken, in the two different ways this epic tracks**,
and the audit therefore reports clean for the same reason a healthy plan would.

⭐⭐ **This is the flagship archetype sitting inside a tool built to detect that archetype** — and it is
the second time this epic has found that shape (the first: `pre-submission-self-review` unable to see
an unreachable guard, `PLAN-81`).

## OBSERVED — first-party, `PLAN-TRUTH-010`'s own logs

### Surface A — `[DISPATCH]` lines under-count envelopes by ~35%, and **every gap is a re-fire**

15 `[DISPATCH]` lines in `logs/work.log` against ~23 execution-context envelopes independently
evidenced by their own `(plan-marshall:execution-context.{name})` log prefixes:

| Step | Envelopes observed | `[DISPATCH]` lines |
|------|---:|---:|
| `pre-submission-self-review` | 5 (14:11, 14:48, 15:00, 15:51, 19:08) | **1** (13:59:11Z) |
| `automatic-review` | 3 (16:26, 19:44, 20:52) | **1** (16:25:23Z) |
| `wait-region-unified-triage` | 2 (16:33, 20:05) | **1** (16:32:16Z) |
| `phase-5-execute` loop-back re-entry | 2 (17:56, 20:07) | **0** |
| `lessons-capture` | 1 (21:07) | **0** |

⭐ **`lessons-capture` is the cleanest case**: `decision.log` `fb8d5c` at 21:06:42Z ends with the literal
word *"Dispatching"*; `work.log` at 21:07:55Z carries
`[SKILL] (plan-marshall:execution-context.lessons-capture) Loaded …`; the step is recorded
`outcome=done` — **and no `[DISPATCH]` line exists anywhere for it.** Under the audit's own
`dispatch_coverage_violation` rule, that is **indistinguishable from having run the step inline.**

⇒ **First-fire-only emission.** The audit is systematically blind to exactly the paths where dispatch
discipline is most likely to slip: retries and loop-backs.

### Surface B — the primary surface has **zero** records, ever

The audit's documented pairing rule: pair a `decision.log` `effort resolve-target` entry with the next
chronologically-following `[DISPATCH]` line carrying the same `role`; an unmatched resolve is a
`shape_violation`.

⛔ **Across 125 decision-log entries there is not one `resolve-target` record.** With the left-hand side
empty, that check **can only ever return zero**. It is structurally incapable of reporting a violation.

⭐⭐ **And the audit still reported three `shape_violation`s** — found by pairing Surface A against the
`execution-context.{name}` prefix in `[SKILL]`/`[STATUS]` lines, i.e. **by going outside the documented
rule**. ⇒ **The documented rule found nothing and could not have; a human went around it.** A green from
this audit is currently a green from an undocumented ad-hoc method, and the documented one is dead code
that has never once been able to fail.

## The rule this makes concrete

> **A check whose input surface can be empty must report `indeterminate`, never `0 findings`.**
> *"I found nothing"* and *"I had nothing to look at"* must not share a representation.

⚠ This is **clause (b) of the standard `PLAN-TRUTH-010` itself just shipped** — the audit violates a
rule that landed in the same PR that discovered the violation.

## ⭐ FOLDED — a second site in finalize with the identical shape: `scope_creep_check`

From the same run (`-005`), on **merged main**: `scope_creep_check` returned `no_baseline_sha` — it had
nothing to diff against — **and alongside it reported `residual_count: 0` and `finding_emitted: false`.**

⇒ **The two halves of one payload disagree.** The reason field says *"I could not measure"*; the verdict
fields say *"I measured and found nothing wrong"*. **Downstream reads the verdict fields**, so a check
that could not run passes as a check that ran clean, and the finalize summary shows a clean scope gate.

⭐ **Folded here rather than filed separately** because it is **D3's obligation at a second site** — an
empty input surface rendered as a zero. ⛔ **The fix must be the same shape, or D3 is a local patch
rather than a rule**: when the baseline SHA is absent, either **omit** `residual_count` /
`finding_emitted` and let the absence be the signal, or carry an explicit **`measured: false`**
discriminator every consumer must branch on.

⚠ **Note the history**: `scope_creep_check` was already one of the two 100%-broken persists repaired by
`PLAN-86` (#1038). ⇒ **Second defect at the same site, different mechanism** — the earlier fix made the
persist land; it did not make the verdict honest. **Do not assume the site is now understood.**

## ⭐ SECOND MEASUREMENT 2026-08-03 (#1085) — the under-count reproduces, and the omission is worse

**11 `[DISPATCH]` lines against ≥17 envelopes that provably ran — ≥35% under-count**, independently
measured on a different plan from the 15-vs-23 figure above.

⛔⛔ **And the newly-named omission is the severe one: `branch-cleanup` is ENTIRELY ABSENT from the
dispatch trail** — the step that **holds the merge mutex, performs the merge, and prunes the branch.**

⇒ **The audit is blind to the single most consequential dispatch in a plan's life.** ⭐ Under its own
`dispatch_coverage_violation` rule that is indistinguishable from `branch-cleanup` having run inline —
i.e. **the merge itself would read as an undispatched operation.**

⚠ **Two independent measurements now** (≈35% both times) on two plans. ⛔ **That does NOT make 35% the
population figure** — both are samples, and D0's obligation to derive the emission population from code
rather than from logs is unchanged. **What it does establish is that the first measurement was not an
artifact of one run.**

## Deliverables

1. **D0 — GATE: derive the emission population, both directions.** Every code path that creates an
   execution-context envelope, and every path that emits `[DISPATCH]`. ⛔ **The mismatch set is the
   deliverable** — do not sample from the 5 steps above; they are what one plan's logs happened to
   show, and a 15-vs-23 count from one run is **a sample, not an enumeration** (standing archetype).
2. **D1 — move the emission into the seam.** Emit `[DISPATCH]` from the dispatcher itself (or from
   `effort resolve-target`, which today logs nothing), so **no code path can skip it by forgetting to
   restate a hand-written logging step**. ⛔ **A re-fire that reuses the envelope must still emit.**
   ⭐ **Load-bearing** — this is the only deliverable that closes the retry blindness by construction
   rather than by adding more emission sites to forget.
3. **D2 — `resolve-target` logs its intent.** One `decision.log` line per resolve carrying the role key
   and the resolved target. Without it the documented pairing rule has no left-hand side.
4. **D3 — the audit fails closed on an empty surface.** Zero `resolve-target` records ⇒ `status:
   indeterminate` for the `shape_violation` check. ⛔ **A control assertion is required**: the check must
   be *shown to report indeterminate* on a zero-record fixture, or this is a vacuous guard in a new place
   (counter now n≥5, one prior instance **introduced by a fix for it**).
5. **D4 — reconcile the documented rule with the method that actually worked.** The three real
   `shape_violation`s were found by the `execution-context.{name}` prefix pairing. ⛔ **Either promote
   that to the documented rule or make D2's surface carry the same information — never leave a
   documented rule that has never fired standing next to an undocumented one that does.**
6. **D5 — tests, each verified to FAIL pre-fix.** (a) A re-fired step emits `[DISPATCH]` — **use the
   live `pre-submission-self-review` 5-fire shape**. (b) `lessons-capture` emits at all. (c) A
   zero-`resolve-target` corpus yields `indeterminate`, not `0`. (d) The D0 population is asserted
   non-empty and the emission set equals the envelope set.

## Claim Labels

- **OBSERVED (plan-reported, first-party to it, with log ids and timestamps)**: the 15-vs-23 counts, the
  per-step table, the `fb8d5c` / `[SKILL]` / `outcome=done` triple for `lessons-capture`, the `69d6d2`
  re-fire entry, **zero `resolve-target` records across 125 decision-log entries**, and that the three
  reported violations were found outside the documented rule.
- ⚠ **NOT independently re-derived by this orchestrator.** The counts and ids are the filer's; they are
  precise, internally consistent, and the `lessons-capture` case is corroborated by this epic having
  received that step's message. ⛔ **Re-derive at D0 before scoping** — and note the 23 is itself an
  approximation (*"roughly 23"*), which is the kind of number D0 exists to replace.
- **HYPOTHESIS**: the mechanism is first-fire-only emission from a hand-written logging step rather than
  from the dispatcher. Consistent with every observed gap being a re-fire. ⛔ **Confirm by symbol.**
- **HYPOTHESIS**: `resolve-target` has no logging at all (as opposed to logging under a different key
  the audit does not read). ⚠ **An asserted absence — verify it exactly like an asserted presence.**

## Expected Surface

- **HYPOTHESIS**: `ref-workflow-architecture` — the dispatch audit rules and the pairing contract
- **HYPOTHESIS**: the effort/dispatch resolution path — `effort resolve-target`
- **HYPOTHESIS**: `plan-retrospective` — the audit's consumer

## FOLDED IN — PR #1115 retrospective evidence (from `landings/PLAN-TRUTH-042.md`)

PLAN-TRUTH-042's own run produced five first-party instances of this spec's archetype, read out
of `quality-verification-report.md` in its dormated plan dir. They are **evidence, not new
deliverables** — D1–D3 already cover the class; these give them named, reproducible targets.

- **OBSERVED — the empty-population instance, verbatim this archetype**: the dispatch audit's
  `shape_violation` detector reported **0 violations over an EMPTY population**. Surface B
  (`decision.log` `effort resolve-target` entries) carries **zero rows** across the whole plan
  while Surface A carries **25 `[DISPATCH]` lines**. `shape_violation` is defined as
  resolve-with-no-dispatch, so with no resolves it is *structurally incapable of firing*.
  ⭐ **The inverse condition actually present — 25 dispatches with zero recorded resolves — has
  no category at all.** That missing category is the sharper half: D1 should add it, not only
  publish the population.
- **OBSERVED — a declared population that is 5.3% of the evidence**: `agent-initiated-redispatch`
  declares the 5-execute boundaries file as its population — **1 row of the 19 the plan
  recorded**. The 17 rows in `metrics-dispatch-boundaries-6-finalize.toon` (including two
  `termination_cause=error` rows) and the 1 row in the 4-plan file are outside its scope, so a
  `0.00` share was computed over a twentieth of the evidence and reported unqualified.
- **OBSERVED — a skip that silently swallowed the only rule that fired**:
  `check-manifest-consistency` skipped `tests_only_diff` as *"not applicable —
  verification_steps != [module-tests]"* while the manifest carries `verify:module-tests` and the
  decision log records *"Rule tests_only fired"*. A **namespaced-vs-bare token mismatch**; the
  check then summarised `failed:0 findings:0`. ⭐ A skip that renders as a pass is the same defect
  as a vacuous green, and D2 should treat *not-applicable* as a reportable population outcome
  rather than a silent exclusion.
- **OBSERVED — an inconclusive that was trivially resolvable**: `artifact-consistency` reported
  `affected_files_recall` / `affected_files_exact_match` as inconclusive because the worktree was
  removed at branch-cleanup and `references.modified_files` no longer existed — while the
  footprint was recoverable from the plan's own `status.metadata.head_at_completion`
  (`aa606b617`). This is the *retrospective-runs-after-branch-cleanup* shape, not a one-off.
- **OBSERVED — a not-applicable that is honest**: `settings_review` skipped steps 2–4 on a
  zero-prompt input and *said so*. Keep as the matched control: D2's population disclosure must
  distinguish this from the three above, or it will flag honest skips as defects.

**Verify-first clause for this fold**: every instance above was read from PR #1115's dormated
artifacts, which are a **snapshot of one run**. Re-derive each against the current detector source
before scoping — a detector fixed since #1115 refutes its instance and the plan re-scopes.

### ⭐ RECURRENCE — the same class on a DIFFERENT plan, so it is not a one-run artifact

`lesson-retirement-fails-open-002` (PR #1113, a different plan): **"Four retrospective checks
publish verdicts over populations they never established."** With #1115's own message
`-002` (*"Two retrospective checks report clean over a population they never examined"*), the
class is now **observed on two independent plans, n=2 runs, 6 checks total**. ⇒ **This is a
property of the checks, not of a run** — which retires the "maybe that run was unusual" reading
and makes D2's population-disclosure obligation the load-bearing deliverable rather than a
nice-to-have. Recorded as a recurrence on this item, **not** as a second item.

### ⭐ FOLDED — the two dispatch-record defects raised at the #1115 landing

Both were recorded as Open Defects at the landing; they belong to this spec's surface and are
folded here so the spec, not the ledger, carries them:

- **All 19 dispatch rows carry `0`** for `input_tokens` / `output_tokens` /
  `cache_read_input_tokens` / `cache_creation_input_tokens` — the artifact's own verdict line
  says `rows_with_nonzero_context_load: 0`. The per-dispatch billing-composition columns are
  **wired at no call site**. ⭐ `a-rule…-004` adds the half the landing did not see: **the
  termination-cause enum is short by five values.** A schema with unwired columns *and* a short
  enum cannot support the audit built on it.
- **`phase_steps` is last-write-wins and erases errored attempts a sibling store recorded**
  (`a-rule…-007`) — this is the *mechanism* behind the landing's observation that two
  `cause=error` dispatches (392,736 tokens) appear as one clean `done`. ⛔ Establish whether this
  is a gap `PLAN-TRUTH-031` (#1076) left open or a regression of it **before** scoping.

## Dependencies and Sequencing

- ⚠ **Adjacent to `PLAN-TRUTH-031`** (finalize step records are prose not facts) — same log substrate,
  different consumer. **Evaluate absorption at outline; sequence, do not pair.**
- ⚠ Adjacent to `PLAN-TRUTH-042` (a rule green because it examined nothing) — **same archetype, different
  gate**. Deliberately NOT merged: 042 is Java arch rules in a consuming project, this is our own
  dispatch audit. ⭐ **But D3's negative-control obligation is the same obligation 042's D1 states** —
  whichever lands first should be cited by the other rather than re-derived.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-045-the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one.md"
```

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -066

**Component:** `plan-retrospective (checks that examined nothing, over a record not yet written)` · **Deliverables after merge: 11** (raised cap is 12).

Both plans are `plan-retrospective`, and they are the two halves of one failure.

- **`-045`** — the checks publish verdicts over populations they never established (now **n=2 plans, 6
  checks**, so it is a property of the checks, not of a run).
- **`-066`** — the retrospective runs at order 995 and reads `metrics.md`, which `record-metrics` writes
  at 998, so it measures a partially-written file.

⭐⭐ **The merge is the point**: `-066` explains *why* several of `-045`'s checks had nothing to examine.
A check whose population is empty because its source has not been written yet is not the same bug as a
check whose population is empty by construction — **and `-045` alone could not tell them apart.** Fixing
the checks without fixing the read order would have "fixed" checks that were never broken.

⛔ **The correctness evidence**: #1115's retrospective published `6-finalize = '-'` and a plan total of
`1,438,440` ⇒ *"2.01×"*; the on-disk file reads `3,635,563` and `5,157,173 (n=5/6)`. Both figures
reached the operator report as facts.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count deliverables at outline.** The figure above is the sum of the pre-merge counts; overlapping deliverables should COLLAPSE rather than concatenate, and a merged plan that still reads as two plans stapled together has not been merged.

## ⭐⭐ SECOND INDEPENDENT INSTANCE 2026-08-08 — M3's skip reproduces on a different plan, with a re-run

From `daemon-baseline-interpreter-is-unregistrable-001` (PR #1122's run). The drain already folded this
shape from PR #1115; **this is the same defect on a different plan, and the filer went further than
observing it.**

- **The predicate**: `check-manifest-consistency.py` `evaluate_tests_only` (`:324`) gates on
  `steps != ['module-tests']`. **The composer never emits that value** — `_manifest_decide._decide`
  Rule 4 matches on `_role_of(...) == 'module-tests'` but keeps the candidate's **canonical id**, which
  is `verify:module-tests`. ⇒ **The rule always takes the skip branch**, emitting
  *"rule M3 not applicable — verification_steps != [\"module-tests\"]"*, while the decision log on the
  same run records **`Rule tests_only fired`**.
- **The run reported `passed: 2, failed: 0, findings: 0`** — a clean pass over exactly the violation M3
  exists to catch.
- ⭐⭐ **The filer RE-RAN it against the true 9-file footprint from squash commit `263f216d9` and M3
  still skips**, and named what the culprit set *would* have been: `marshalld.py` and
  `_marshalld_verifier.py` — two production files. **That is a counterfactual with a named result, not
  an observation** — it rules out "the footprint was genuinely tests-only" as an explanation.

⇒ **n=2 plans for this specific rule**, on top of the n=2 already recorded for the broader
*checks-over-unexamined-populations* class. ⛔ **A one-token vocabulary mismatch (`module-tests` vs
`verify:module-tests`) silently disables a production-code safety gate** — and both halves of the
system are internally consistent, so neither side looks wrong on its own. **D0 must sweep for the same
bare-vs-canonical comparison elsewhere; a fix to M3 alone leaves the class open.**

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⭐⭐ FOLDED FROM THE 2026-08-09 INBOX DRAIN — 9 messages. THE POPULATION IS NOW LARGE AND THE DEFECTS ARE IN THE AUDITOR ITSELF

⛔ **The through-line: every item below is a defect in the machinery that AUDITS every plan**, so each
one silently corrupts the record of every plan audited between its introduction and its fix.

### The recurrence that is now n=3 and was asked to be scheduled or explicitly deferred

**`two-producers-...-007` (finding, and it makes an explicit request).** Lesson `2026-08-08-20-001`
**reproduced three of its four instances verbatim, one plan later** — not similar defects, the same code
paths emitting the same wrong output:

| Instance | Reproduced | Evidence |
|---|---|---|
| 1 — `check-routing-decisions` `posture_cutoff` regex does not match the emitter's line shape, so `mis_prune` falls through to predicate re-evaluation | YES | `mis_prune:sonar-roundtrip` = **false `fail`** against a decision log recording a legitimate `lane_resolution` drop |
| 3 — `check-manifest-consistency` rule M3 gates on `['module-tests']` while the canonical form is `['verify:module-tests']` | YES | `tests_only_diff` = **`skip`** against a manifest carrying `verify:module-tests`; re-confirmed at `check-manifest-consistency.py:324` and against `manage-config list-verify-steps`, which returns **only** prefixed ids ⇒ **M3's guard can never be false** |
| 4 — `extract-chat-signal` reduction keyed on a denylist of synthetic shapes | YES | `raw_turn_count: 1128` → `reduced_turn_count: 3`, and one of the three retained turns is a `<task-notification>` envelope |
| 2 — `_PRUNABLE_PREDICATES` under-enumerated | not re-tested | the plan did not exercise a mis-prune of `plan-retrospective` itself |

⭐ **Instance 3 is the M3 bare-vs-canonical skip this spec already carries at n=2. It is now n=3.**
⛔ **The sender's requested disposition is a fork, and it is recorded rather than silently taken:**
*"Either schedule the three named remedies … or record explicitly that they are deferred so the next
retrospective does not report them a third time as if they were news."* **This fold IS the explicit
deferral record** — the remedies are scheduled into this spec, not applied now, because this plan is
`staged` and blocked behind `-055`. ⇒ **If a fourth retrospective reports them, that is not news either.**

⭐ Note the two failure *directions* in one component: instance 1 emits a **false `fail`**, instance 3
emits a **`skip` indistinguishable from a legitimate non-applicable skip**. A fix that only addresses
"the checks are too quiet" leaves the false-positive arm live.

### Dispatch-boundary recording — the empty-primary-surface half, corroborated three more ways

- **`provider-...-002` (L2)** — *a finalize step can be marked done with **no execution_log row and no
  dispatch-boundary row***. ⇒ the audit's primary surface is not merely sparse, it is **writable-around**.
- **`provider-...-003` (L3)** — *the four per-dispatch context-load columns are **declared, wired, and
  zero on every row***. ⛔ **Declared-and-always-zero is the worst of the three states** (absent /
  populated / present-but-vacuous): a consumer sees a column, reads 0, and concludes "no context load".
- **`provider-...-005` (L5)** — *the Phase Dispatch Boundaries section is **unreachable**, and its loss
  reports as a **benign omission***. ⇒ the section that would expose the gap is itself the thing missing,
  and its absence is rendered as normal.

### The retrospective's own inputs are unreliable

- **`daemon-...-005`** — the plan-efficiency anchor table **cannot match three of five live
  `scope_estimate` values** ⇒ a comparison against an anchor that does not contain the observed values.
- **`daemon-...-006`** — the post-merge footprint **reports inconclusive when it could be resolved from
  the merge commit**. ⭐ A recoverable answer surrendered to an `inconclusive` — the cheap fix is named.
- **`daemon-...-007`** — the chat-history aspect is **blind to AskUserQuestion-mediated operator input**
  ⇒ every operator decision taken through the prompt is invisible to the audit that measures operator
  interaction.
- **`provider-...-006` (L6)** — *`extract-chat-signal` reports **Tier-1 success** after dropping
  **99.86%** of the transcript.* ⛔ Same mechanism as instance 4 above, quantified: **a success verdict
  computed over 0.14% of its input.** ⇒ **n=2 for this one too, from two different plans.**

### session_id — RECURRENCE, now n=3

- **`daemon-...-003`** — *session capture from a dispatched leaf **overwrites the plan's recorded
  `session_id`***.
- **`provider-...-007` (L7)** — *`status.metadata.session_id` is **single-valued** but a plan spans
  multiple sessions.*

⇒ These are the **cause and the schema** of the same defect: the field cannot hold what the plan
actually has, so the last writer wins. This spec already carries one instance (from #1115's `-001`);
with these it is **n=3**, and the two halves should be fixed together — widening the field without
fixing the leaf overwrite just loses a different value.

### ⭐⭐ AND THE SAME ROOT CAUSE PRODUCES A THIRD SYMPTOM — one fallback fixes all three

**`two-producers-...-001` (candidate-lesson).** *`direct-gh-glab` Surface B scans an **empty**
post-merge diff and reports **zero leaks**.*

`plan-retrospective` runs as a finalize step positioned **after `branch-cleanup`**, which merges the PR
and removes the worktree. By the time the aspect runs, the commits are already in `main` and the cwd is
the main checkout — so `git diff main...HEAD` is **empty**. Verified first-party for #1125: the diff
returns nothing while the real 5-file footprint is recoverable from the squash commit `cf70cf787`.
⛔ **This is not a one-off — the ordering that produces it is the NORMAL finalize order, so Surface B has
reported a clean scan over an empty diff on every post-merge retrospective.**

Two independent collapses in `direct-gh-glab-usage.py`:

1. `_git_diff_added_lines` (`:151-162`) returns `[]` on `FileNotFoundError`, on `TimeoutExpired`, **and**
   on `proc.returncode != 0`. ⇒ **a git failure and a genuinely empty diff are the same value.**
2. `cmd_run` (`:222-236`) reports `by_surface.diff_leak` **with no denominator** — no `files_scanned`,
   no `diff_lines_considered`, no `base_resolved`. ⇒ a zero is indistinguishable from *"500 lines, none
   leaked"*, *"git failed"*, and *"the diff was empty"*.

> **The aspect has no way to say *could not look*, so it says *clean*.**

⭐⭐ **This is the same defect as `daemon-...-006` above, and `check-artifact-consistency`'s
`affected_files_exact_match: inconclusive` is a third face of it.** All three are one missing capability:
**resolve the post-merge footprint from the merge/squash commit when the worktree is gone and
`status.metadata` carries a merged PR.** The answer was one `git show --name-only` away in every case.
⇒ **Fix the footprint resolver once; do not patch three aspects.**


---

## ⛔⛔⛔ FOLDED 2026-08-09 FROM #1131 — THE TWO LEDGERS UNDER-COUNT **IDENTICALLY**, SO CROSS-CHECKING THEM IS NOT CORROBORATION

**OBSERVED, first-party to the `hook-timeout-unit-confusion` run (PR #1131, `6053382ab`).**

Each settle-band fix commit **re-staled every `head_dependent` step**, so within one finalize:
`lessons-housekeeping` ran **5×**, `plugin-doctor` **7×**, pre-submission self-review **7×** — mostly
re-confirming identical verdicts. **The re-fires emit no `[STEP]` bracket.**

⇒ **The step ledger and the dispatch-boundary ledger therefore under-count THE SAME EVENTS IN THE SAME
DIRECTION.**

> **Cross-checking them looks like corroboration and isn't.**

⭐⭐⭐ **This is the sharpest methodological finding this spec has received, and it invalidates a
verification strategy rather than a number.** Every existing check of the form *"does the step ledger
agree with the dispatch-boundary ledger?"* returns **agree** — and that agreement is **evidence of a
shared blind spot, not of correctness.** Two witnesses that share a bias are **one witness**.

⛔ **CONSEQUENCE FOR THIS SPEC'S OWN DESIGN.** This plan's premise is that the primary surface is empty
and the secondary is retry-blind, and its natural remedy is *"reconcile the two."* **That remedy is now
known to be unsound as a verification**: reconciling two ledgers fed by the same emitter proves only
that the emitter is self-consistent. ⇒ **The audit needs a third source with an INDEPENDENT emitter** —
or an explicit statement that no independent source exists and the reconciliation is therefore a
consistency check, never a completeness one.

⭐⭐ **SECOND INSTANCE OF THE SHARED-BIAS-READS-AS-AGREEMENT SHAPE, IN AN UNRELATED COMPONENT.** The
first is the plugin-cache pin oracle, where the "sole unmarked dir" is a *lagging function of the
registry* and was being counted as an independent third witness alongside the registry itself
(`PLAN-TRUTH-059`, incident 14). **Same error, two subsystems, found four hours apart.**
⇒ **A general rule worth stating once and citing twice: before treating two signals as corroborating,
establish that they have independent producers.** Neither of these pairs did.

### ⚠ AND THE OBVIOUS FIX HAD ALREADY LANDED AND DID NOT HELP

**#1126 — *"perf(finalize): scope self-review and pre-push-gate re-runs to delta"* — merged as
`72982d3d4` BEFORE this plan's finalize ran.** The re-fires still happened 5× / 7× / 7×.

⇒ **Delta-scoping bounds the COST OF EACH re-run; it does not stop the RE-STALE TRIGGER.** Those are
different levers and only the first is owned. ⛔ **Do not read #1126 as having addressed this** — a
landed perf fix on the same surface is exactly the thing that would make a reader assume the problem is
handled. **It is the re-stale trigger that is unowned.**


---

## ⭐⭐⭐ FOLDED FROM THE 2026-08-09 (EVENING) DRAIN — 12 MESSAGES, AND THREE OF THIS SPEC'S FINDINGS ARE NOW MULTI-PLAN RECURRENCES

⛔ **Read the recurrence counts first — they are the argument for priority.** Three defects this spec
already carries were reported AGAIN by two further plans, independently, in the same 24 hours:

| Defect | Now at | Reported by |
|---|---|---|
| post-merge footprint unresolvable once the worktree is gone | **n=4** | `daemon-006`, `two-producers-001`, `runtime-001`, `runtime-002` |
| `check-routing-decisions` attributes a posture-cutoff prune to the predicate it re-evaluated | **n=3** | `two-producers-007` (inst. 1), `runtime-004`, `hook-006` |
| the `[STEP]`/`[DISPATCH]` under-count | **n=3, and now QUANTIFIED** | `#1131`, `hook-002`, `runtime-006`, `metrics-016` |

### The under-count is worse than "no bracket" — it is TWO different bugs that alias

- **`hook-002`** — HEAD-advance step re-fires emit **no `[STEP]` bracket**, *"under-reporting executions
  5×"*. ⭐ The 5× is now a measured figure, not an impression.
- **`runtime-006`** — the finalize `[STEP] Executing`/`Completed` **pairing is unguarded and one pair is
  broken**. ⇒ even the brackets that ARE emitted cannot be trusted to pair.
- **`metrics-016`** — **`[DISPATCH]` emits once per ROLE, not once per FIRING**, so a multiply-fired role
  contributes one record.

⇒ ⛔⛔ **Three independent under-count mechanisms, all biased the same way (downward), across BOTH
ledgers.** This compounds the shared-bias finding already in this spec: the two ledgers do not merely
share one blind spot, they share **three**, and each would individually make a reconciliation look
clean. **A fix for any one of them will make the ledgers agree MORE while remaining wrong.**

### `plan-retrospective` aspects — five more, all the same shape

- **`runtime-003`** — `plan-efficiency` **always** reads a `metrics.md` that predates `6-finalize`.
  ⭐ *"Always"* is the important word: this is not a race, it is the normal ordering.
- **`runtime-005`** — Step 3 aspect labels **do not match** the `collect-fragments` registry keys ⇒ a
  label-keyed lookup silently returns nothing.
- **`runtime-009`** — `compile-report` **deletes the fragment bundle** on the `sections_dropped` warning
  path ⇒ the evidence for the warning is destroyed by the warning path itself.
- **`hook-007`** — the coverage aspect is **structurally dead for every worktree plan** under the current
  step order. ⛔ *Structurally* dead, not flaky: it can never produce a result for that plan class.
- **`review-apparatus-021`** — four further `plan-retrospective` / phase-ordering defects from the
  PLAN-PR-022 run, **ownership TRANSFERRED to us** by the sibling epic under the three-way rule.

⇒ ⭐⭐ **The pattern across all five: the aspect returns a value, and the value is not a measurement.**
Dead label lookups, pre-dated inputs, destroyed evidence, structurally-unreachable code — **none of them
report that they could not look.** That is this spec's thesis, now with nine instances in one component.
