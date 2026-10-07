# PLAN-TRUTH-116: A test or fixture that cannot fail

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-27 from the `lessons-handling-26-08-26-01` drain, messages `-002` (4 lessons, *"a test
or fixture that cannot fail"*) and `-013` (1 lesson, *"manage-tasks has no post-creation write path for
a task's verification block"*). ⭐ **The two were routed separately and the router flagged folding them
as "a legitimate call and probably the cheaper one" — this spec takes that call**, because both halves
convert a CHECKABLE obligation into an unfalsifiable one, and both land on
`verification.criteria`.

⛔ **The suggested fold target `PLAN-TRUTH-042` is SHIPPED** — verified first-party against
`status.json`. A new spec is therefore correct, not a duplicate.

## Objective

**A test passes for a reason unrelated to the property it names, because its own arrangement makes the
subject unreachable.** Distinct from the empty-population class (`PLAN-TRUTH-104`), where a *check*
returns a verdict over nothing: here the population is fine and the *test* is arranged so the code
under test is never reached. The remedies differ — that class needs a distinct verdict token, this one
needs a **matched control**.

Two of the five members are the two halves of ONE field's write path, which is why they ship together:
`verification.criteria` can be silently truncated at creation, and cannot be corrected after it.

## Deliverables

1. **D0 — GATE: derive the population before fixing any member.** Sweep the test corpus for the shape
   *an assertion whose subject is unreachable under its own arrangement*. ⛔ **Publish the swept
   population and its size** — this epic's standing rule, and the class this plan is about. The five
   known members were each found by a different accident, which is evidence the sweep was never run.
2. **D1 — the merge-lock reentrancy test asserts a property nothing asserts.**
   `test_reentrant_grant_does_not_enqueue_into_fifo` makes `plan-a` the **holder**, then has `plan-a`
   re-acquire — so the short-circuit fires before the enqueue and the assertion holds **because the
   code was never reached**. The property the name asserts (idempotent enqueue for a **waiter**, which
   is what the poll loop actually produces) is covered by nothing.
3. **D2 — `parse_stdin_task` silently truncates `verification.criteria` to one line**, so a multi-line
   criteria block persists **empty**: a task that cannot fail its own verification, manufactured by the
   tooling. ⭐ Observed **twice in one plan**, the second time inside a dispatch that had been explicitly
   warned about the first — **a warning is not a guard**, and that is the cleanest proof of it in the
   corpus.
4. **D3 — `manage-tasks` has no post-creation write path for `verification`.** `update` reaches
   `title` / `description` / `depends-on` / `status` / `domain` / `profile` / `skills` / `deliverable` /
   cost only; `add-step` / `update-step` / `remove-step` reach `steps[]` but not `verification`. The
   only sanctioned route to a corrected criteria block is `remove` + recreate, **which renumbers the
   task and breaks any `depends_on` chain pointing at it** — so a caller amending a task's write set
   must demote a checkable obligation into `description` prose. ⭐ **The amendment MUST be ATOMIC with
   the step change it accompanies**, or a task ends with a step set and a criteria block describing
   different file sets; a naive "add an update flag" fix misses exactly that.
5. **D4 — matched controls, which are the whole point of this plan.** For D1: a waiter's repeated
   acquire must be shown to reach the enqueue path, and the test must go RED if it does not. For D2/D3:
   a test that adds a step targeting a new path to an existing task, amends `verification.criteria`
   through the new verb, and asserts the persisted `TASK-NNN.json` carries **both** the new step and the
   amended criteria **with `depends_on` unchanged**. ⛔ **"The guard did not fire" is not evidence the
   guard works** — only *"the guard stayed green while the defect was present"* is. `PLAN-TRUTH-055`
   supplied this corpus's first matched negative control; copy its shape.

## Claim Labels

- OBSERVED: the four `-002` instances and the one `-013` instance, each quoted from a lesson recording a live run — `2026-08-09-22-001`, `2026-08-26-05-001`, `2026-08-24-17-001`, `2026-08-08-19-004`, `2026-08-24-12-001`
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Quoted lesson ids are per-run artifacts; not independently reachable from this checkout
- OBSERVED: `PLAN-TRUTH-042` is `shipped`, so the router's suggested fold target is unavailable — read at `.plan/local/orchestrator/truthful-signals/status.json` § `plans[]`
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: status.json plans[] entry id PLAN-TRUTH-042 shows status shipped, pr 1115
- OBSERVED: `2026-08-24-17-001` reproduced within one plan after an explicit warning; the lesson states it first-hand
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Historical lesson-based claim about a prior run; not independently re-derivable
- HYPOTHESIS: the missing merge-lock coverage is the waiter-repeated-acquire case and nothing else covers it — confirm/refute at `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_reentrant_acquire.py` § `test_reentrant_grant_does_not_enqueue_into_fifo`, read against `merge_lock.py`'s enqueue (verify-at-outline)
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: test_reentrant_grant_does_not_enqueue_into_fifo makes plan-a the HOLDER before re-acquiring; no test in the file exercises a queued WAITER re-acquiring
- HYPOTHESIS: `manage-tasks update`'s flag list is as the lesson enumerated it on 2026-08-24 — ⛔ **the router did NOT re-derive it against HEAD.** Confirm/refute with `manage-tasks update --help` BEFORE scoping D3; a flag may have landed since (verify-at-outline)
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-tasks update --help lists no --verification flag today (title/description/depends-on/status/domain/profile/skills/deliverable/cost-size/predicted-cost-tokens/envelope-id only)
- ⛔ NOT ESTABLISHED, and do not promote it: `2026-08-26-05-001` also reports `waiting_count: 2` with `blocking_plan_id: null` read as self-blocking. **The lesson files this as an unverified report and notes its own session transcript contradicts it** (a real foreign holder). Only the coverage gap is verified.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Spec itself labels this NOT ESTABLISHED; no independent corroboration available
- Verify-first clause: settle whether D2 and D3 are one code path or two before scoping. The router asserts they are different paths (write-at-creation vs write-after-creation); if they share a validator the remedy collapses to one, and D2/D3 re-scope accordingly.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause on whether D2/D3 share one code path; deferred to outline

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/**` — `update`'s flag surface and `parse_stdin_task` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — the canonical invocation block for the new verb (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — the enqueue path D1 exercises (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_reentrant_acquire.py` — `test_reentrant_grant_does_not_enqueue_into_fifo`
- HYPOTHESIS: `test/plan-marshall/manage-tasks/**` — the D4 controls (verify-at-outline)

- HYPOTHESIS: `test/conftest.py` — the `run_script` subprocess budget, added 2026-09-04 by the drain fold of `review-apparatus-027` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-architecture/` — the inventory crawl whose cold cost the budgets are sized against (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/` — the falsification procedure §4.1 prescribes, added 2026-09-04 by the cui-http fold (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-TRUTH-104` — adjacent class, explicitly NOT the same (a check over nothing vs a test that cannot reach its subject). Keep the boundary in the shipped docs; do not merge them.
- ⛔ **Collision warning from the router, and it is real:** any other plan touching `verification.criteria` collides with D2/D3. Re-run `corpus cross-check` at emit.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-116-a-test-or-fixture-that-cannot-fail.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-08-27 (landing #1361) — two more arrangements that cannot observe what they name

From the `PLAN-TRUTH-114` landing drain (candidate-lessons `-008` and `-002`).

**A real-resolver fixture that places two resolvers at the SAME path cannot observe their divergence.**
The fixture's whole purpose is to catch the two resolvers disagreeing; co-locating them makes
divergence unrepresentable, so the test passes **because the condition it tests for cannot arise in its
own arrangement**. ⭐ A pure instance of this plan's subject, and a cheap one: the fix is fixture
geometry, not new assertions.

**A pending-task TOON schema rejection can remove shipped work from the task ledger.** Three schema
rejections during `PLAN-TRUTH-114` left **16 recorded tasks against 17 real shipped units**, and a
stray `work/pending-tasks/default.toon` survived in the plan directory. ⇒ **A rejection at the write
boundary silently reduces the ledger** rather than failing loudly, so the ledger's own count stops
being evidence of what shipped. ⚠ **Same component as this plan's D3** (`manage-tasks` write paths) —
scope them together and check whether one validation fix serves both.

## ⭐ FOLDED 2026-08-31 — inbox drain (2 message(s))

- **`findings-read-absent-plan-dir-returns-clean-zero-002.md`** — The non-vacuity control written to prove one finding fixed was itself unable to fail
- **`git-artifact-scanning-and-destructive-recovery-001.md`** — Surface a guard whose predicate is satisfiable without the evidence its docstring names

⛔ Each is the sending plan's own first-party observation, relayed verbatim by title. **Treat every one as a LEAD** — the drain did not re-derive them, and several were observed against tree states that have since moved. Re-ground at outline.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`review-apparatus-027`** (carried-out finding `1f0c43`, `PLAN-PR-038`) — *script startup cost makes `run_script` subprocess budgets marginal under `verify`’s parallel load.* Measured on an otherwise-idle machine: `architecture module --module my-module` takes **17.9s wall on a COLD inventory cache (203% CPU — genuinely crawling, not blocked)** and **6.4s warm**. `test_module_subcommand_accepts_canonical_module` calls it through `run_script` with `timeout=30`. **Under `verify`’s `-n auto` load (10 xdist workers, each spawning its own subprocesses) that 6-18s baseline exceeded 30s and the test failed with `subprocess.TimeoutExpired` — one failure in 23,744, in a test with no relationship to the plan’s changes.**

  ⭐⭐ **A contributing cause was found AND REMOVED, and the measurement before and after is what makes the residual claim credible:** 75,917 temp files / 783 MB of pytest-basetemp residue had accumulated under `.plan/temp`, and every script startup walked it — **pre-cleanup 19.8s at 22% CPU (I/O-blocked), post-cleanup 17.9s at 203% CPU (compute-bound).** ⇒ **the residue was real overhead but NOT the whole story**, and the honest split is only visible because both numbers were taken.

  ⛔ **The residual issue is a fixture-level one this spec owns:** a cold crawl costs ~18s and **several subprocess budgets across the suite are sized as if script startup were cheap** — the same class as the four plugin-doctor timeouts the plan marked and the daemon’s 15s worktree probe that failed twice. **A test whose budget is smaller than its dependency’s cold cost cannot fail for the reason it was written to detect.** Remedies named: warm the inventory once in a session fixture, raise the budget for architecture-invoking tests, or make the crawl incremental.

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

**Theme 4 folds here — tests and gates that prove nothing.**

⭐⭐⭐ **§4.1 is described by the document as "the highest-value technique in the corpus", and it is this spec's remedy stated as a procedure:**

> **A regression test that has never been observed to fail has not been shown to test anything.**

**Procedure:** write the fix and its test → **temporarily restore the pre-fix production code** → confirm the new test now **fails, for the stated reason** → restore and confirm green. ⭐⭐ **One recorded result: *"23 passed / 1 failed against the pre-fix form"* — and THE COUNT IS THE EVIDENCE**: exactly one test flipped, so the test is sensitive to precisely the claimed change and **nothing else silently depended on the old behaviour.** It catches the two modes a passing test cannot distinguish itself from: the **vacuous** test (reaches its assertion by a different path, so it stays green against the pre-fix form) and the **over-broad** test (five others fail too, so the change was wider than claimed). **Cost: one build per fix.**

⛔⛔ **§4.2 — the headline deliverable shipped as UNREACHABLE CODE and five local gates passed it.** Deliverable D2 gated on `statusCode == 304 && cachedEntry != null`; deliverable **D6**, separately in the same plan, narrowed the cache read so `cachedEntry` is **always `null`** for exactly the methods D2 was written for. **The headline deliverable was dead code on arrival, and its test passed because the generic error path coincidentally returned the same category.** `verify`, `coverage`, self-review, simplify and the Q-Gate all passed it; **two review bots caught it from opposite directions.**

⛔⛔⛔ **And the outline had EXPLICITLY FLAGGED the D6/D2 interaction as a risk.** *"It was identified at outline time, carried into execution, and never re-checked once both halves had landed."*

> 1. **A guard predicate must be shown able to FIRE in the scenario it exists for.** Coverage proves a line executed; **it does not prove the branch was reached BY THE INPUT CLASS the branch is about.**
> 2. **When an outline flags an interaction between two deliverables, that interaction is a VERIFICATION OBLIGATION** — a named end-of-phase check, not a note. ⭐ *"Neither deliverable is wrong in isolation, which is exactly why single-deliverable verification cannot see it."*

⚠ **§3.3's fixture half belongs to this spec too** (folded narratively into `PLAN-TRUTH-108`): a converter that never returns `Optional.empty()` makes every defect in that mode invisible, **including defects in the code written to fix it.**

⚠ **§4.3 and §4.4 are recorded as ALREADY-COVERED and are deliberately NOT folded** — see the epic ledger. §4.3 (a proposed fix that keeps the defect's own predicate is a restructuring, not a fix; **and the ORCHESTRATOR proposed the same wrong shape, so it is not a bot artefact**) is carried by lesson `2026-09-03-16-001`. §4.4 (a review step whose surfacer covers none of the changed content still records `done`) is `PLAN-TRUTH-126`'s subject and `-126` is **LAUNCHED**, so folding into it would re-scope a live plan.

## ⭐ FOLDED 2026-09-07 (c) — PLAN-TRUTH-125 drain (1 item)

`-001` (`test/plan-marshall/ref-toon-format`) — the concrete case behind the canonical-serializer
unification. ⭐⭐ **The shipped test is the shape this spec asks for and should be cited as the
exemplar**: it proves its population **two independent ways — by function name AND by behaviour — then
cross-checks them**, so completeness is **derived rather than asserted.**

⇒ **That is a worked answer to this spec's own question** (*what does a test that cannot fail look
like, and what does its opposite look like?*). ⛔ **A single-derivation population test is the failure
mode**; two derivations that must agree is the control. **Cite `39ec2a0ad` as the reference
implementation rather than re-inventing the pattern.**

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-153-tests-fixtures-and-detectors-that-cannot-fail-and-underived-completeness-claims.md` (PLAN-TRUTH-153)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
