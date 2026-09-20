# PLAN-TRUTH-044: the lesson-retirement path fails open in three independent places that stack

epic: truthful-signals
workstream: WS-01

## Objective

Three defects filed from `PLAN-TRUTH-010`'s run (`-002`, `-003`, `-009`) sit on **one path**: the
route a lesson takes out of the corpus into a plan and back. Each fails open independently, and
**they stack** — the outcome observed live was **8 lessons absent from the active corpus, resident in
a plan directory `archive-plan` was about to move, with every detector reporting clean.**

⭐ **They are folded into one plan because fixing any one leaves the condition invisible.** 002 makes
the restore silently do nothing; 009 makes nothing ever ask whether a restore is owed; 003 means the
step that would reconcile it cannot see the corpus at all. ⛔ Splitting them re-creates the observed
outcome with one fewer contributing bug.

## OBSERVED — first-party, verified live during PR #1082

Three facts held **simultaneously**:

- `manage-lessons get --lesson-id 2026-07-22-16-003` → `error: not_found` — **not in the corpus**.
- All **8** `lesson-*.md` files present in `.plan/local/plans/fail-closed-signal-integrity/` — **in the
  plan directory**.
- `manage-lessons list-stalled` → `stalled_count: 0` — **nothing is stalled**.

### A — `restore-from-plan` fails open on a worktree-resident plan dir (`-002`)

Returns `status: success` / `no_lesson_file` when the plan directory it resolved is worktree-resident
rather than main-anchored. *"I could not determine whether a relocated lesson exists"* collapses into
*"there is no lesson to restore"*. ⭐ **`convert-to-plan` moves a lesson OUT; `restore-from-plan` is the
only path back IN** — a fail-open there is silent **corpus loss**, not a no-op.

✅ **Root cause CONFIRMED by the recovery, not merely hypothesised**: once `integrate_into_main` moved
the plan dir back to main, the same verb returned `restored_count: 8` **on the first attempt**. ⇒ The
condition is worktree-residency and nothing else.

### B — `list-stalled` is vacuous for exactly the plans that trap lessons (`-009`)

It keys the stalled condition off `status.metadata.plan_source` matching `YYYY-MM-DD-HH-NNN`. That
field identifies a plan **created from** a lesson. A plan that **carries** lessons via `convert-to-plan`
— which is **every orchestrator-staged plan with a `Lessons Carried` block** — has `plan_source` unset
and `source: description`.

⇒ **The detector's population is a strict subset of the population that can exhibit the condition.**
⭐ This is the standing population-derivation archetype, now at another recurrence, and it is the
**detection** path — distinct from A, which is the **restore** path. `plan-retrospective` Step 5.5
shares the same signal.

### C — `lessons-housekeeping` cannot satisfy pushability and corpus access at one order (`-003`)

Moved into the settle band (`order: 4`) so its edits stay pushable to the PR head. That move broke its
access to the carried-lesson corpus, which resolves **main-anchored** while the settle band runs against
the **worktree**.

⛔ **No step order satisfies both today.** Early enough to reach the corpus → too early to push. Late
enough to push → the corpus is out of reach. ⇒ **A structural conflict, not a bug in either half**, and
it reads out as *"nothing to housekeep"* — another benign verdict standing in for *"could not look"*.

### ⭐⭐ C CORROBORATED AND SHARPENED 2026-08-03 by `code-intelligence-substrate` — probed on merged main

| Step | `order` | `mutates_source` | `post_run_review` |
|---|---:|---|---|
| `project:finalize-step-lessons-housekeeping` | **4** | **true** | absent |
| `project:finalize-step-review-retrospective` | 990 | false | true |
| `default:lessons-capture` | 991 | false | true |
| `plan-marshall:plan-retrospective` | 995 | — | — |
| `default:record-metrics` | 998 | false | true |

⇒ Housekeeping sits **991 orders before** the retrospective whose `quality-verification-report.md` it
consumes. **PR #1080 relocated the post-run band DOWNWARD only; the upward-facing consumer was not
modelled. The sandwich is live in merged main.**

⛔⛔ **And the decisive new fact neither epic had: it CANNOT be fixed by the same mechanism.** Band
membership **requires `mutates_source: false`**, and `lessons-housekeeping` declares
`mutates_source: true`. Relocating it into the post-merge band would place **a declared mutator after
the merge gate with no push path** — precisely the defect `post_run_source_guard` was added in #1080 to
detect.

⇒ **This upgrades D3 from "no order satisfies both" to "no order CAN satisfy both under the current band
contract."** ⭐ **Direction (b) — split the step into a main-anchored classify pass and a pushable apply
pass — is now the strongly-favoured option**, because it is the only candidate that does not require a
mutator to cross the merge gate. ⚠ **Still record the rejected option**; (a) may survive if the store
handle removes the need to move the step at all.

### ✅ OWNERSHIP SETTLED 2026-08-03 — D3's gate is DISCHARGED, implement against it

`code-intelligence-substrate` **accepted the split exactly as proposed** and staged **`PLAN-CIS-034`**
(their WS-04, queue position 3), which **names this D3 explicitly** and records the boundary in its own
§ *Ownership boundary* so neither side re-litigates it:

- **THEIRS** — the **band contract**: whether a `mutates_source: true` step can ever be post-run, what
  `post_run_source_guard` should say about it, and the finalize ordering that follows.
- **OURS (D3)** — the **corpus-resolution half**: decoupling the store handle from cwd so a step's
  *order* stops determining what it can *see*, sized with the `restore-from-plan` fail-open (D1).

⛔ **CIS-034 D2 must read this D3 before scoping, and the two must agree** — written into their spec.
⭐ **Split-the-step is carried into CIS-034 as the LEADING CANDIDATE, not as a decision.** Their D2
settles it, and *"declare the case unrepresentable and have the guard say so"* is an **acceptable
outcome** there. ⛔ **What is not acceptable is leaving it silently unrepresentable** — that constraint
binds our D3 too.

⭐ They declined to take both, on our own argument: this D3 was staged four hours before their answer,
so moving it would relocate correctly-placed work — the symmetric call to `PLAN-TRUTH-035` /
`PLAN-CIS-033`.

### ⭐ FOLDED 2026-08-03 (`-016` § 2) — the step reports all-zeros on the run where it could not see its input

Operator finalize report for #1080, that step's outcome verbatim:
**`0 removed, 0 promoted, 0 adapted, 180 retained`** — while its own log said
*"`quality-verification-report.md` unavailable (retrospective runs at order 995, after this settle-band
step) … proceeded on `request.md` plus the branch diff."*

⛔⛔ **The sender explicitly does NOT claim the zeros were caused by the missing artifact — and that is
the point.** A genuinely clean corpus returns **the same row**, and nobody has distinguished the two.

> ⭐ **A step that ran without its input reports exactly what a step that ran with its input and found
> nothing reports.** `0 removed, 0 promoted, 0 adapted` is **not evidence of a clean corpus** — it is a
> number computed from a substrate the step itself **declared unavailable**, and nothing in the outcome
> says so.

⇒ **This is D3's reporting obligation, distinct from its ordering obligation**: even after the ordering
is settled, the outcome must carry *which substrate it was computed from*. ⛔ **A remedy that only fixes
the order leaves the zeros unreadable on every future run where the input is unavailable for some other
reason.**

## ⭐ The shared root cause, stated once

**CWD-keyed store resolution produces a benign-looking empty read.** A and C are the same mechanism at
two call sites; B is the detector that should have caught the result and cannot. ⚠ **The standing rule
that `manage-lessons` resolves its store by CWD git-common-dir is already recorded in this epic** — it
was known and still produced a silent corpus loss, because knowing a resolution rule is not the same as
any code path refusing to act on an unresolvable one.

## ⛔⛔ Safety by unrelated bug is not a control

⭐ In this run the lessons survived **only because A was broken.** The `remove` disposition could not be
applied, so a load-bearing lesson retired on a false justification (see `PLAN-TRUTH-047`) was not in
fact deleted. **Fixing A alone, without D3's evidence standard, converts a latent corpus loss into an
actual one.** ⇒ Sequencing against TRUTH-047 is load-bearing, not tidiness.

## Deliverables

1. **D0 — GATE: derive the population of CWD-keyed store resolutions on the lesson path.** Every verb
   in `manage-lessons` plus the finalize steps that consume it, classified by whether it resolves
   main-anchored, worktree-relative, or cwd-relative. ⛔ **Both directions**: sites that could-not-look
   and report benign, AND sites that looked in the wrong store and reported a real-but-irrelevant
   answer. **Do not sample — 8 lessons went missing behind a hand count.**
2. **D1 — `restore-from-plan` distinguishes three states, not two.** `restored` / `no_lesson_file`
   (resolved AND scanned, a real observed zero) / a **distinct non-benign outcome** for "the plan
   directory could not be resolved to the main-anchored store". ⭐ **Reuse the in-repo precedent** —
   `orchestrator inbox list` already carries exactly this discriminator (`epic_not_found` vs
   `inbox_state: missing` vs `present, count: 0`). Do not invent a new shape.
3. **D2 — `list-stalled` derives its population from the observable.** Scan every plan directory for
   `lesson-*.md`; **presence of the file IS the condition**, independent of `plan_source`. ⛔ Report the
   other direction distinctly too: a `lesson-*.md` whose id is ALSO in `.plan/local/lessons-learned/`
   is a **duplication** fault, not an absence fault. `plan-retrospective` Step 5.5 consumes the widened
   signal rather than re-deriving `plan_source`.
4. **D3 — resolve the housekeeping ordering conflict.** Two candidate directions, **neither validated**:
   (a) decouple corpus resolution from cwd — give the step an explicit main-anchored store handle so its
   order stops determining what it can see; (b) split the step — a main-anchored classify pass early, a
   pushable apply pass in the settle band, with the classification handed between them. ⭐ **(a) is the
   same root cause as D1 and should be sized with it.** ⛔ **Pick one and record the rejected one.**
   ⚠ Until this lands, a green `lessons-housekeeping` does **not** mean any lesson was retired.
5. **D4 — tests, each verified to FAIL pre-fix.** (a) `restore-from-plan` against a worktree-resident
   plan dir returns the non-benign outcome, not `no_lesson_file`. (b) `list-stalled` reports a plan
   holding `lesson-*.md` with `plan_source` unset — **this is the exact live fixture, 8 files, zero
   reported**. (c) The duplication direction reports distinctly. (d) The D0 population is asserted
   non-empty.

## Claim Labels

- **OBSERVED (plan-reported, first-party to it, three facts verified together at retrospective time)**:
  the `not_found` / 8-files-present / `stalled_count: 0` triple; the `restored_count: 8` recovery after
  `integrate_into_main`.
- **OBSERVED (source-cited by the filer)**: `list-stalled` keying off `status.metadata.plan_source`;
  the settle-band `order: 4` move.
- ⚠ **NOT independently re-derived by this orchestrator** — the field names and the order value are the
  filer's. **Re-read them at D0 before scoping.** *A corrective is a hypothesis until the named site is
  read.*
- **HYPOTHESIS**: A and C share one mechanism (cwd-keyed resolution). Strong — the recovery evidence
  supports it for A — but **C's mechanism was not directly instrumented.** Confirm at D0; if C is a
  different mechanism, D3 splits from D1 and this plan is at the bloat threshold.
- **HYPOTHESIS**: 8 is the complete set of trapped lessons. ⛔ It came from a **hand count**, which is
  precisely what D2 exists to replace. Do not carry it as a population.

## Expected Surface

- **HYPOTHESIS**: `manage-lessons/scripts/` — `cmd_restore_from_plan`, `list-stalled`, store resolution
- **HYPOTHESIS**: `project:finalize-step-lessons-housekeeping` and the finalize step manifest (order 4)
- **HYPOTHESIS**: `plan-retrospective` — Step 5.5's trigger

## Dependencies and Sequencing

- ⛔ **Sequence AFTER or WITH `PLAN-TRUTH-047`** — see the safety-by-unrelated-bug section. Fixing D1
  without 047's evidence standard makes a latent corpus loss actual.
- ⚠ **Adjacent to `PLAN-90`** (the corpus is written and never read). **Different side of the same
  store** — 90 is the prospective READ, this is the retire/restore WRITE. Sequence, do not pair.
- ⚠ Surface-adjacent to `PLAN-TRUTH-014` (landed-residue promotion sweep).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-044-the-lesson-retirement-path-fails-open-in-three-independent-places.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
