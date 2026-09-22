# PLAN-TRUTH-136: The declared footprint cannot learn a path the outline did not predict

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-04 from inbox drain message `review-apparatus-028.md` — carried-out finding `5a5761`
> from `PLAN-PR-038` (PR #1388, merged `ef974632c`), **rescued from an archived plan's findings store**
> and transferred here under the three-way rule.

## Objective

**`references.affected_files` is re-derived from the solution outline's structured deliverable data by
set union. Loop-back fix tasks created by the finalize triage are NOT in the outline, so their paths
never enter the declaration.** The union-only contract means the key can never *narrow* — and it also
means **it never learns paths the outline did not predict**.

⇒ **Any finalize step deriving scope from `affected_files` under-scopes on any plan whose scope moved
during execute, and each such step's skip-clean exit writes a FALSE ASSERTION rather than a detectable
gap.**

**Observed twice on one plan**, at HEAD `7ddf3963` and again at `23179a2f9`: `finalize-step-plugin-doctor`
read `affected_files`, got **11 paths with no skill directory among them**, and would have taken its
documented **skip-clean exit — writing a HEAD-bound record asserting the plan genuinely touched no
skill**. `git diff 7ddf3963..23179a2f9` shows the commits touched **two marketplace skill
directories** the declaration does not record: `build-server-client` and `script-shared`.

⭐⭐ **The refresh ran and was faithful and wrong at the same time.** The loop-back admission gate's
`sync-affected-files` reported `added_count: 0` with `total: 11` — **faithful to the outline, wrong
about the tree.** There is no error, no warning, and no field that distinguishes a declaration the
outline predicted completely from one it predicted partially.

⛔⛔ **The step survived only by not trusting its own input.** `plugin-doctor` happens to cross-check
against git, refused the skip, and ran whole-tree. **A step that trusts the read does not**, and
nothing marks which steps do which.

⭐ **This is the epic's archetype at the scoping layer:** a skip-clean exit is a confident negative
("this plan touched no skill") published over a population that was never capable of containing the
answer.

## Deliverables

1. **D0 — GATE: enumerate every consumer that derives scope from `affected_files`, and classify each
   by whether it cross-checks.** ⛔ **Publish the population and its size.** `plugin-doctor` is the one
   consumer that happened to be safe; **the finding names it as an accident, not a design**, and this
   epic's rule forbids treating one observed member as the population. D0's output partitions the
   consumers into *cross-checks* and *trusts the read* — and the second set is the actual blast radius.
2. **D1 — close the learning gap at the loop-back refresh.** Union the **realized** footprint (the
   git-derived worktree state, via `manage-references capture-realized-footprint`) into
   `affected_files` at the loop-back refresh, so the declaration learns paths the outline did not
   predict. ⛔ **The union-only, never-narrow contract stays** — this widens what the union draws from,
   it does not relax the invariant.
3. **D2 — publish a PROVENANCE field on the `affected_files` reader**, so a consumer can tell an
   **outline-derived** declaration from a **tree-corroborated** one. ⭐ **This is the half that closes
   the defect even if D1 lands narrowly**: today the two are byte-identical at the read, and a
   skip-clean exit taken over an outline-derived declaration is exactly the false assertion. Adopt the
   in-tree discriminator vocabulary rather than inventing another.
4. **D3 — a skip-clean exit over an unprovenanced declaration is INDETERMINATE, not clean.** Whichever
   arm D1 takes, a step that skips must record *what it skipped over* and *how the scope was derived*,
   so the HEAD-bound record it writes is falsifiable.
5. **D4 — matched controls.** A plan whose scope never moved must still take its skip-clean exit
   unchanged (**load-bearing: a fix that makes every skip indeterminate has removed the optimisation
   the exit exists for**), and a plan with loop-back fix tasks outside the outline must have those
   paths present in `affected_files` and its skip refused.

## Claim Labels

- OBSERVED: the two HEADs, the 11-path read with no skill directory, and the two skill directories the diff touched — first-party in the sending run, twice.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: git diff 7ddf3963..23179a2f9 shows build-server-client and script-shared skill dirs touched
- OBSERVED: `sync-affected-files` reported `added_count: 0` / `total: 11` at the loop-back admission gate.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Historical plan references.json / sync run no longer exists on disk
- OBSERVED: `finalize-step-plugin-doctor` refused the skip and ran whole-tree because it cross-checks against git.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED: plugin-doctor/SKILL.md is unchanged since ancestor 7566efd95 (76 commits) and implements only F1/indeterminate modes; no git cross-check exists. Re-scoped: no second reader of the realized footprint may be assumed.
- HYPOTHESIS: `sync-affected-files` re-derives from the outline's structured deliverable data by set union, and loop-back tasks are absent from that data. ⛔ Stated by the finding; **not read at source by this orchestrator**. Confirm/refute at `manage-references` § the footprint derivation and `manage-tasks` § loop-back task creation (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: cmd_sync_affected_files derives paths only from the outline via declared_paths_by_intent set union
- HYPOTHESIS: consumers other than `plugin-doctor` derive scope from `affected_files` and do NOT cross-check. ⛔ NOT enumerated by the finding; D0 settles it (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: D0 consumer sweep incomplete; 73 files mention affected_files, unclassified
- ⚠ Verify-first clause: `manage-references` already ships a realized-footprint capture and a three-way reconciliation. **Settle whether the loop-back refresh could simply CALL the existing reconciliation before D1 designs a new union** — if the mechanism exists and is merely not invoked at that site, D1 is a call-site fix and re-scopes accordingly.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-references already ships cmd_capture_footprint and cmd_reconcile_scope

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md` — the `affected_files` contract and the provenance field (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/` — `sync-affected-files` and the realized-footprint capture (D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — the loop-back admission gate and the skip-clean exits (D0, D3) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-references/` — the D4 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⛔⛔ **`PLAN-TRUTH-126` IS LAUNCHED and is the closest sibling** — *shipped guards assume the meta-project's own layout and go vacuously green elsewhere*. Its subject is the same skip-clean-exit class from the **layout** direction; this is the same class from the **scope-derivation** direction. ⛔ **DO NOT EMIT while `-126` is live**, and re-ground this spec against `-126`'s landed changes: if `-126` reworks the skip-clean exits, D3 may already be closed.
- ⚠ **Adjacent to `PLAN-TRUTH-134`** — `affected_files` corrupted from a **different** cause (an unanchored bullet regex inventing and dropping paths at outline time). ⛔ **Different causes, same key.** `-134` is the outline-time writer, this is the execute-time learner; keep separate and cross-reference in the shipped docs.
- Adjacent to: `PLAN-TRUTH-113` (shipped) — its residual-error table names **under-declaration as the dominant class by roughly an order of magnitude**. This spec is one named mechanism behind that measurement.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-136-the-declared-footprint-cannot-learn-a-path-the-outline-did-not-predict.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (1 claim contradicted)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 2 | `plugin-doctor` performs a git cross-check that would have caught the undeclared path | **REFUTED** — `plugin-doctor/SKILL.md` is **unchanged since ancestor `7566efd95`** (76 commits back) and implements only the F1 / indeterminate modes; **no git cross-check exists** |

⭐ **The refutation removes a false backstop, which makes the plan MORE necessary, not less.** The spec
partly rested on another gate catching what the declared footprint missed. **Nothing catches it.**
⇒ **D0 must not assume any second reader of the realized footprint; the declaration is the only signal.**

⚠ **Claims 3 and 5 both CORROBORATED and together they bound the fix**: `cmd_sync_affected_files`
derives paths **only** from the outline via `declared_paths_by_intent` set union, while
`manage-references` already ships `cmd_capture_footprint` and `cmd_reconcile_scope`. ⇒ **The realized
side already exists. This spec supplies the LEARNING path between them, and must not re-derive either.**

## ⛔⛔ FOLDED 2026-09-07 — PLAN-TRUTH-128 drain + a review-apparatus forward (2 items). THE SYNC VERB IS STRUCTURALLY INCAPABLE OF CLOSING THE GAP.

### `arm-the-refusal-...-001` item 1 — the declared footprint understates the realized diff, and the obvious remedy DOES NOT WORK

`references.affected_files` declared **19**; `git diff --name-only origin/main...HEAD` was **21**.
Missing: `plugin-script-architecture/references/stdlib-modules.md` and
`test/plan-marshall/script-shared/test_extension_base.py`.

⛔⛔⛔ **`sync-affected-files` added ZERO when re-run — and that is the finding, not the shortfall.**
It re-derives from the **SOLUTION OUTLINE** (`deliverables_scanned: 5`, `bullets_parsed: 36`), **and the
outline is what is short.** ⇒ **The verb is structurally incapable of closing this particular gap, and a
run that reaches for it gets a clean-looking `added_count: 0` that READS AS CONFIRMATION.**

⭐⭐ **The cause is recorded honestly, including the orchestrator's own share**: `stdlib-modules.md` was
an **orchestrator-directed** mid-execute addition (TASK-5) that no step re-declared, and
`test_extension_base.py` was touched by TASK-9 beyond its declared targets. ⇒ **Scope moved during
execute and nothing re-declared it — the declared footprint is written once at outline and HAS NO
WRITER AFTER THAT.** That is this spec's title, with a mechanism and a failed remedy attached.

⭐ **Correct behaviour observed, and it does not carry**: `project:finalize-step-plugin-doctor` detected
the under-scope and widened to a superset **by hand** (6 skill dirs → 7). **Per-step, not systemic.**

⇒ **Second independent corroboration of the `affected_files` under-recording archetype** (first from
PLAN-CIS-001), and **third counting this epic's own `affected_files: 0` observation** — which is the
*opposite* direction and must stay distinguished.

### `freshness-gate-...-008` — deliverable 4 closed `done` at 62.5% declared-file coverage with no gate

A deliverable closed while **5 of 8 declared files** were touched, and **nothing compared the two.**
⇒ **The declaration exists, the realization exists, and no gate reads them together at close.** ⛔ That
is the same missing comparison as item 1 seen from the other end: **item 1 is realization exceeding
declaration; this is declaration exceeding realization.** ⚠ **D0 must own BOTH directions or it will
ship a one-way check** — and a one-way check over a two-way defect reports clean on half of it.

## ⛔⛔⛔ FOLDED 2026-09-07 (b) — `review-apparatus-034` item 1. THE UNDER-DECLARED FOOTPRINT GATES WHAT A PLAN CAN LEARN. THIRD CONSEQUENCE, AND THE MOST EXPENSIVE.

> **`lessons-consult` RAN, SUCCEEDED, and searched exactly ONE component** (`tools-integration-ci`) —
> derived from a **9-file declaration against a realized 158-file footprint.**

⛔⛔⛔ **Lesson `2026-08-27-16-005` carries `component: plan-marshall:phase-6-finalize`, and its proposed
action is VERBATIM what the operator later redirected the plan to do.** It came from **PR #1356 — the
immediately preceding plan — and was invisible because its component fell outside the shrunken consult
set.** ⇒ **The run paid a SIX-HOUR detour to rediscover a lesson it already owned.**

⭐⭐⭐ **This spec now has THREE distinct consequences of ONE root cause, and the third is new:**

| # | Consequence | Where it lands |
|:-:|---|---|
| 1 | the footprint cannot learn a path the outline did not predict | this spec's original subject |
| 2 | the disjointness gate reads the declaration — **~two thirds of the files a landing touched were never declared** | `review-apparatus`'s gate; their dominant residual class |
| 3 | **the CONSULT SET is derived from it, so the declaration gates what the plan can LEARN** | **NEW — and it is the one with a measured cost** |

⛔⛔ **And the failure is silent in the way this epic cares about most:** *"a successful `lessons-consult`
return is indistinguishable from a complete one — it reports that it SEARCHED, never that it searched
EVERYWHERE IT SHOULD HAVE."* ⇒ **A `success` over a shrunken population, with the population unstated.**

⭐ **The sibling epic flagged rather than merely routed it, and their reasoning is worth keeping:**
*"the defect is yours (footprint recording + consult-set derivation); the blast radius reaches our
gate, and a fix on your side RETIRES A DEFECT ON OURS."* ⇒ **This is now a cross-epic dependency, not
only a local defect** — and it raises this spec's value well above its original framing.

⚠ **D0 must publish the consult-set derivation as a THIRD consumer** alongside the two it already
knows. ⛔ **A fix that widens the footprint but leaves `lessons-consult` reporting an unstated
population closes one of three.**

⚠ **Expected Surface widened in this same act**: the `lessons-consult` set-derivation site
(HYPOTHESIS, verify-at-outline).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-145-declarations-that-cannot-learn-and-cannot-go-stale.md` (PLAN-TRUTH-145)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
