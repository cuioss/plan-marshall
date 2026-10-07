# PLAN-CIS-017: The Freshness Gate Accepts Evidence It Never Cross-Checks

epic: code-intelligence-substrate
workstream: WS-05

> Staged 2026-07-27 from lesson `2026-07-26-20-002`, surfaced during PR #1013 but not owned by it.
> **This is the truthful-signals HALF of a two-owner lesson** — the test-isolation half belongs to the
> `test-suite-quality` epic (see § Split). The lesson's own words: *"the gate reported green for a
> reason unrelated to the evidence it was supposed to be checking, and no signal distinguished the
> two."* That is this epic's thesis stated by an executing agent about a production gate.

## Objective

`pre-commit-verify-freshness` was satisfied by a `kind=build` change-ledger entry whose
`matched_notation` was `plan-marshall:build-npm:js_coverage` — **a notation the plan never ran**. The
gate matches on the presence of a ledger stamp without checking that the stamp corresponds to work
*this plan* actually performed. Make the match evidence auditable and cross-checked.

## ⭐ SECOND INDEPENDENT INSTANCE — n=2, folded 2026-07-27 from the PLAN-80 landing (#1021)

- OBSERVED (operator narrative, first-party, plan `refusal-recognizer` / PR #1021): the push freshness
  gate returned `fresh` by matching an **npm `--help` invocation recorded as a successful
  `kind=build` — in a repo with no npm build at all**.
- **⇒ This is the same defect as the founding instance, not a variant.** Both matched an unrelated
  `plan-marshall:build-npm:*` notation the plan never meaningfully ran. Two different plans, same gate,
  same bundle, same wrong-reason pass. **D1 must scope from n=2, and should expect more** — the
  founding lesson and this one were both found by accident, which means the observed rate is a floor.
- ⚠ **Do NOT absorb the producer half into this plan.** The reason a `--help` invocation is *recorded*
  as a `kind=build` row at all belongs to **PLAN-59 D1/D2** (the missing subcommand discriminator on the
  `kind=build` stamp). This plan owns the **consumer** question: the gate accepting evidence it cannot
  cross-check. Keep the split — PLAN-CIS-017 makes the match auditable and cross-checked; PLAN-59 stops the
  bogus rows being written. Either fix alone leaves a real hole, which is why both are staged.
- ⚠ **Sharpens D3's precision warning:** an `--help` invocation and a pure log read are *legitimately
  recorded* notations under today's producer, so a cross-check against "notations this plan ran" would
  still admit them until PLAN-59 lands. D3 must cross-check against the plan's **architecture-resolved
  canonical build commands**, not merely against "notations that appear in this plan's ledger rows".

## ⛔ RECONCILED 2026-08-09 — THE CO-DEPENDENCY IS STALE, AND THAT CHANGES D3

⛔ **`PLAN-59` belongs to the RETIRED `plan-optimization` epic and shipped long ago.** This spec
leans on it twice and both leans are now unsafe as written:

- *"Do NOT absorb the producer half into this plan — it belongs to PLAN-59 D1/D2 (the missing
  subcommand discriminator on the `kind=build` stamp)."*
- *"a cross-check against 'notations this plan ran' would still admit [`--help` invocations] until
  PLAN-59 lands."*

⇒ ⛔ **`PLAN-59` is not going to land — it already did, or it never will.** **D1 must establish
first-party whether the `kind=build` stamp now carries a subcommand discriminator**, because the
answer decides D3's shape:

| If the discriminator EXISTS at HEAD | If it does NOT |
|---|---|
| the producer half is closed; D3's cross-check can rely on it and **narrows** | the producer half is **UNOWNED** — no staged plan covers it. ⛔ **Do not silently absorb it**: record it and stage it, or state explicitly that D3 must defend against bogus rows forever |

⭐ **The spec's own reasoning survives intact and is the reason this matters**: it deliberately kept
producer and consumer apart because *"either fix alone leaves a real hole."* **That argument is
unchanged; only the assumption that someone else holds the producer half is refuted.**

⚠ **D3's stated remedy is unaffected and remains correct either way** — cross-check against the
plan's **architecture-resolved canonical build commands**, not against "notations that appear in this
plan's ledger rows". That formulation was chosen precisely because it does not depend on the
producer being fixed.

## ⚠ Mechanism — mixed labels; read them

- OBSERVED (lesson, first-party account by the executing agent, `component:
  plan-marshall:manage-change-ledger`) — on plan `executor-version-split-resolvers`, Step 12a's
  freshness gate was satisfied by a ledger row for `plan-marshall:build-npm:js_coverage`, a notation
  that plan never invoked.
- OBSERVED (orchestrator-verified first-party, 2026-07-27) — **the pollution source is a CONSUMER
  test, not the ledger's own tests.** `test/plan-marshall/manage-change-ledger/test_manage_change_ledger.py`
  carries **10** `PLAN_BASE_DIR` / `tmp_path` isolation markers, while
  `test/plan-marshall/build-npm/test_js_coverage.py` carries **zero** and reaches the real ledger
  through the build wrapper. **⇒ The lesson's directive to "point the test suite at an isolated store
  the way `PlanContext`-based tests already do" MIS-LOCATES the offender** — the ledger's tests
  already do that. Do not scope against the lesson's wording here.
- **HYPOTHESIS (verify-at-outline) — the gate performs no notation cross-check at all.** The lesson
  asserts the gate cannot tell a real build's stamp from a test fixture's. **Confirm/refute at the
  `pre-commit-verify-freshness` implementation**, reading whether the matched notation is compared
  against the plan's architecture-resolved canonical commands, and whether the matched notation is
  recorded in the decision record. If a cross-check already exists and merely failed open, the fix is
  different — narrow the existing check rather than adding one.
- **The verdict was substantively CORRECT on that run** (the agent's own `verify` and `coverage` runs
  had genuinely covered the same tree). **That is what makes it dangerous, not what makes it benign**:
  a gate that is right for the wrong reason produces no failure to learn from, so it can be wrong for
  the same reason indefinitely. Same shape as PLAN-73's gate anchored to the wrong reference.

## ⛔ SECOND, INDEPENDENT WEAKNESS — the gate is TIER-BLIND (`2026-07-27-08-002`, added 07-27)

From PR #1015: *"`pre-commit-verify-freshness` returns fresh on a tree whose tests never ran. The
`kind=build` ledger row is **tier-blind**, so the gate's predicate is **strictly weaker than the claim
its consumers read**."*

**This is NOT the same defect as the wrong-notation one above, and D1 must handle both.** There, the
evidence was *unrelated* (a notation the plan never ran). Here the evidence can be entirely *related*
and still insufficient — a `kind=build` row does not record **which tier** ran, so a build that
compiled but never tested satisfies a gate whose consumers read it as "tests are fresh".

⚠ **Reframing that changes this plan's shape — adopt the lesson's own words: "one structural gap, not
four bugs."** `2026-07-27-08-002` is the **fourth** lesson filed against this one store. Four lessons
on the same store is the tell that **the store's evidence model is under-specified**, not that four
gates each need a patch. **D1 must therefore address the evidence model** — what a ledger row must
record for a consumer to read a claim off it — rather than adding a second special-case check beside
the notation cross-check. If D1 concludes two independent checks really are the right answer, record
why the model-level fix was rejected.

## Deliverables

### D1 — GATE: establish what the gate currently checks (mutates nothing)

Read the freshness gate and answer three questions before changing anything: (a) does it compare the
matched notation against the plan's resolved canonical commands, or only assert a row exists?
(b) is the matched notation recorded in the decision record, so a human could see *which* evidence
satisfied it? (c) is there any provenance field distinguishing a production write from a test write?
**Settle the fail-direction**: an uncross-checkable match must not silently pass — decide between
refusing (fail-closed, ADR-009's posture) and passing-with-a-visible-warning, and say why. ⚠ Note that
fail-closed here can block legitimate work if the resolution is imperfect; D1 owns that trade.

### D2 — the match becomes auditable

When the gate is satisfied, the decision record names the **matched notation** and the evidence row it
matched. This alone converts a silent wrong-reason pass into a visible one, and it is the deliverable
that survives even if D3's cross-check proves impractical.

### D3 — the match becomes cross-checked

Compare the matched notation against the plan's architecture-resolved canonical commands. A match on
an unrelated notation is surfaced per D1's fail-direction. ⚠ **Precision matters in both directions**:
a plan legitimately runs several notations, and resolution can be partial — an over-strict check that
refuses valid evidence trades one false signal for its mirror, the polarity guard PLAN-54 established.

### D4 — tests

(a) A gate run whose only candidate evidence is an unrelated notation behaves per D1's chosen
fail-direction — **verified to FAIL (i.e. silently pass) against current code**. (b) A legitimate
multi-notation plan still passes. (c) The decision record contains the matched notation.

Four deliverables (D1 a gate) — under the split guard.

## ✂ Split — both halves stay in THIS epic (operator-directed 2026-07-27)

The lesson carries **two independent directives**. They are split into two plans, **both owned here**:

| Half | Plan | Why |
|---|---|---|
| **Gate cannot distinguish / cross-check evidence** | **PLAN-CIS-017 — THIS PLAN** | A production gate reporting green for an unrelated reason. Confidence-hides-a-caveat; the lesson says so itself |
| **Tests write into PRODUCTION stores** | **PLAN-83** | Isolation is opt-in, so it is optional. Measured surface: 114 candidate test modules reach a write path with no isolation marker |

**Earlier framing corrected:** this half was initially flagged for handoff to the `test-suite-quality`
epic. **The operator directed both halves remain here**, so PLAN-83 was staged in this epic. Cross-check
against that epic's PLAN-CIS-007 `unit-test-truthfulness` at outline to avoid duplicate work.

⚠ **They are NOT independent, and the ordering matters.** Fixing test isolation alone removes *this*
contamination source but leaves the gate unable to distinguish evidence — so the next source
(a stray manual run, a sibling worktree, a future consumer test) reproduces it. **PLAN-CIS-017 is the
durable half; PLAN-83 is the urgent half** — pollution happens on every module-test run today.
**Neither alone closes the lesson.** They are source-disjoint (gate implementation vs test tree), so
**they may run concurrently.**

## Expected Surface

- HYPOTHESIS: the `pre-commit-verify-freshness` gate implementation and its decision-record write —
  **exact module verify-at-outline**; the orchestrator did not locate it first-party.
- HYPOTHESIS: `manage-change-ledger` — only if D1 finds a provenance field is the right fix
  (verify-at-outline).
- OBSERVED (read-only, evidence): `test/plan-marshall/build-npm/test_js_coverage.py` — zero isolation
  markers; the confirmed pollution source. **Do not fix it here** — it is PLAN-83's half.
- OBSERVED: lesson `2026-07-26-20-002`, retired at finalize **only when BOTH PLAN-CIS-017 and PLAN-83 have
  landed** — retiring it on either alone drops the other's directive from the corpus. **Whichever
  lands second performs the retirement.**

**Disjointness:** depends on D1's location of the gate. Presumed disjoint from PLAN-79
(`platform-runtime`/`manage-status` title seam), PLAN-80 (`workflow-integration-github`), PLAN-81
(`pm-plugin-development`). ⚠ **Re-check against PLAN-62** — `manage-run-config` is adjacent to the
build-invocation surface — and against PLAN-35's build/no-build oracle work if it revives.

## Dependencies and Sequencing

- Independent of everything in flight.
- **Coordinate with the `test-suite-quality` half** at finalize for the shared lesson retirement.

## Notes

- Third defect in this epic where **the gate was right by accident**: PLAN-73 (comparison anchored to
  the wrong reference), the PLAN-75 stale-cache episode (my own confirmation right about a symptom for
  a wrong reason), and now this. Worth naming in the epic vision alongside vacuous-authority —
  *correct-verdict-wrong-evidence* is a distinct failure from *wrong verdict*, and it is strictly
  harder to detect because nothing ever breaks.

## The producer half — tests write into the production store

The gate cannot distinguish test-authored evidence because tests write it into the production store
in the first place. These are the producer and consumer halves of one story: the gate change alone is
a *detector* for contamination this half simply prevents, and the producer fix alone leaves the gate
unable to classify evidence already in the store. One closed loop, one plan.

**Deliverables for this half:**
- **GATE (mutates nothing)** — narrow the candidate set, then choose **default-safe isolation over a
  file-by-file fix**.
- **Isolation becomes the default** — the test tree plus, likely, a `conftest` fixture redirecting
  the store for every test that touches it.
- **A test that writes to a production store FAILS** — the guard that keeps this closed.
- **Tests.**

⚠ **Parallelism warning — this half makes the plan LOW-COMPATIBILITY for pairing.** Its
surface is *"the test tree plus possibly a conftest — wide but shallow, and it collides with any plan
that edits tests in the same modules — which is most of them."* **Prefer running this when few plans
are in flight**, or after its D1 has narrowed the confirmed set (which may make it narrow enough to
pair safely). **Do not schedule it alongside a broad plan.**

⚠ **Derive the contaminated-test set from the population, never a hand-written list** — the
named-sample-read-as-an-enumeration archetype, which this epic has now recorded repeatedly.

## Two test-integrity defects with whole-suite blast radius

Message-supplied, HYPOTHESIS until re-verified at outline. Both belong to this plan's test-integrity
half rather than its freshness half.

**(a) `conftest.load_script_module` unconditionally overwrites `sys.modules[name]`, so a monkeypatch
can SILENTLY BECOME A NO-OP rather than an error.** It caused one of #1038's two test failures, and
**its blast radius spans the whole suite** — any test relying on a patch applied before that call is
silently not testing what it claims. ⛔ **This is the most dangerous item in this plan**: it does not
produce a wrong answer, it produces a *green* one. Fix it to fail loudly on overwrite rather than
resolving the collision silently.

**(b) A test suite that STUBS the function under test can never catch its defect.** Observed as a
class in #1038's sweep. The remedy is not "stub less" but a rule the suite can enforce: **a test whose
subject is stubbed is not a test of that subject**, and it should be detectable.

⚠ **These two compound.** (a) makes a patch silently vanish; (b) makes a stub silently stand in for
the subject. Both convert "this test proves X" into "this test proves nothing" **with no signal
either way** — the flagship archetype inside the test suite, which is the one place it is hardest to
notice because green is the expected colour.

⚠ **Split guard:** this plan now covers the freshness gate, the production-store writes, and these
two. **Evaluate a split at outline and record the verdict.**

## Evidence Fold — 2026-07-29, from the PLAN-10 landing (#1059), `end-phase-...-010`

⚠ **Lead, not fact** — re-verify at outline. ⭐ **This is the plan's thesis caught red-handed: a test
fixture wrote into a LIVE plan's audit trail, and the detector built to catch exactly that reported
zero.**

`logs/work.log:233` of a production plan:

```text
[2026-07-29T15:09:34Z] [WARNING] [f10fa1] test message with --paths flag mention
```

Written at 15:09:34, inside the `project:finalize-step-plugin-doctor` execution window. ⭐ It carries
**no category tag** (`[STATUS]` / `[ARTIFACT]` / `[VERIFY]`), which is what makes it *structurally*
recognisable as foreign rather than merely odd — a usable discriminator for a detector.

**The blind spot is exact.** `analyze-logs` reported `fixture_leak_count: 0`, `fixture_leak_signatures[0]`.
Its detector scans **only the folded-in global logs** (`{prefix}-YYYY-MM-DD.log` copied into
`<plan_dir>/logs/` at integrate-into-main). **It never scans `work.log`** — so the one channel that
received a real leak is the one channel the leak detector does not read, and the report's `0` carries no
indication that the search space excluded the plan's primary log.

⇒ **Two independent defects, and this plan should scope both**: test isolation is not airtight for the
logging path (a test reached a live plan's `logs/`), **and** the detector's population is narrower than
the phenomenon it names. The second is this epic's core archetype — *a confident zero over the wrong
population* — and it means the recurrence is invisible to the audit that exists to catch it.

**Remedy shape:**

1. Give the offending test an isolated log store (`PLAN_BASE_DIR` override or a tmp plan dir) so it
   cannot reach a live plan's `logs/`. The literal string `test message with --paths flag mention`
   locates it.
2. Widen the leak detector's population to `work.log`, `decision.log`, and `script-execution.log`.
   ⛔ **Report the scanned population alongside the count**, so a `0` reads as *"0 across these N files"*
   rather than as an unqualified zero.
3. Add an **untagged-line check**: every `work.log` entry is expected to carry a recognised category tag
   after the hash. An untagged line is either a leak or an emission-site defect — both worth surfacing.

⚠ **Minor, same message, same window**: `project:finalize-step-plugin-doctor` double-emits the
`scoped plugin-doctor cannot detect cross-skill divergence` warning 9 seconds apart with distinct
hashes, the first a prefix of the second — an emission site edited without removing the earlier call.
Harmless but it inflates warning counts. Fold only if the outline is already in that file.

⛔ **This fold reinforces the split guard above rather than relaxing it** — the detector-population half
is closely related to the freshness gate's own "cannot distinguish test-authored evidence" thesis, but
the test-isolation half is a separate surface (test tree + conftest).

## Evidence Fold — 2026-07-30, from `audit-report-path-ignores-plan-dir-004` (PR #1063, NOT yet merged)

⭐ **A stale `pre-commit-verify-freshness` at a phase-5 chain tail is STRUCTURAL, not a flake — and the
gate is behaving correctly.** Folded here because it is the counter-example that bounds this plan's
thesis: the freshness gate's *other* failure mode is being **disbelieved when it is right**.

**The mechanism, which is deterministic and follows from the ordering alone:**

1. the chain runs verify, and the build stamp records the tree at `worktree_sha = X`;
2. **Step 10a commits**, which changes the worktree sha to `Y`;
3. `pre-commit-verify-freshness` compares the stamp's `X` against the current `Y` and correctly
   reports **stale**.

⛔ **The stamp was never wrong — the commit invalidated it, and that commit is unconditional at the
chain tail.** So a post-commit verify at a phase-5 tail is a structural requirement of the ordering.

⛔ **Do NOT "fix" this by re-stamping or by relaxing the freshness comparison.** The gate is doing its
job; weakening it reintroduces exactly the false-green class it exists to catch — the same class this
plan's own thesis is about. Nor is it a routed-build failure or retry churn: budget the post-commit
verify into the chain-tail cost model so the run does not read as over-budget.

⭐ **Why this sharpens this plan rather than merely decorating it.** This plan says the gate *cannot
distinguish* test-authored evidence — i.e. it is too credulous in one direction. This fold shows the
symmetric risk: a correct stale verdict that reads as noise invites a "fix" that would make the gate
*more* credulous. Any remedy this plan ships must therefore state which stale verdicts are structural
and expected, or the next reader will silence the true positives along with the false ones.

⚠ **Provenance caveat.** The sending plan announced a landing that had **not** occurred — PR #1063 is
open, verified against `origin/main` at `d38b769ba`. The mechanism above is internally consistent and
matches the known Step 10a ordering, but re-derive it against the implementing source before scoping.

## Evidence Fold — 2026-08-08, from `lessons-handling-26-08-08-01-001` (cluster C03)

⚠ **THREE OF THE CLUSTER'S FOUR MEMBERS ARE ALREADY IN THIS SPEC — the fold adds ONE thing, and
saying so is the point.** The router proposed C03 as a four-instance cluster; on read, `2026-07-26-20-002`
is this plan's founding lesson (§ Objective), `2026-07-27-08-002` is already folded verbatim as
§ "SECOND, INDEPENDENT WEAKNESS — the gate is TIER-BLIND", and `2026-07-29-18-004` (a `--help`
invocation accepted as build evidence) is already carried as the n=2 instance in
§ "SECOND INDEPENDENT INSTANCE" (there in its npm form). ⇒ **Do NOT re-scope D1 upward on a count of
four.** The admission-path count this plan already works from is unchanged; what follows is the one
genuinely new member.

### ⛔ NEW — `2026-07-28-19-007` forecloses the remedy D1 is most likely to reach for

- OBSERVED (lesson, `category: arch-constraint` — the corpus's strongest category): **markdown under
  `marketplace/bundles/**` IS a build input in this repository**, because tests parse SKILL.md bodies.
- ⇒ ⛔ **A doc-only freshness-neutrality exemption is UNSAFE HERE.** Any narrowing of the gate that
  exempts a doc-only footprint from needing fresh evidence reintroduces the whole defect class through
  the exemption, in the one repo where "docs" are executable inputs.
- **This is inverse-facing and that is why it is worth carrying**: every other member of this plan says
  the gate admits too much. This member says the obvious way to make it admit less is wrong. D1's
  fail-direction trade must state explicitly that a doc-only carve-out was considered and refused on
  this constraint — an unexplained absence would invite the next author to add it.

### ⚠ Sequencing collision to raise BEFORE either plan starts

`2026-07-27-00-002` (`kind=build` rows record `exit_code 0` for timed-out builds; `--help` probes count
as builds) was routed to `truthful-signals` as cluster C02, and it is **the same ledger rows this plan
reads**. If that epic's fix and this plan's D1 both touch `manage-change-ledger`, they are not disjoint.
⇒ Raise it at emit time; do not discover it at rebase.

**Claim labels** — OBSERVED: lesson ids, categories, and the three-of-four overlap above (verified by
reading this spec). HYPOTHESIS (verify-at-outline): that the `marketplace/bundles/**`-markdown-as-build-input
constraint still holds. Confirm/refute artifact: the test module(s) that parse SKILL.md bodies — the
constraint is refuted if no test reads a bundle markdown body.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
