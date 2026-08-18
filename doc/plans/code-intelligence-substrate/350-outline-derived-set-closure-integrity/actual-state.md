# Actual state — 350-outline-derived-set-closure-integrity

**Date (UTC):** 2026-08-18    **Branch:** `claude/derived-set-closure-integrity-g7n8x2` (harness-assigned)
**Head:** `0f10d16`    **PR:** none — not opened
**Run outcome:** **partial — stopped by operator instruction before the PR cycle.**

This document is the honest state of play, written because the run was halted mid-contract. It is a
companion to [`report-01.md`](report-01.md), which carries the per-deliverable record; this one says
what is **done**, what is **not**, and what a reader should **not** believe.

---

## 1. How the run ended

⛔ **The verification loop did not converge, and it was not stopped because it had.**

The lane contract permits exactly two endings: the verifier answers that nothing remains, or the
declared round budget is exhausted. **Neither happened.** A 4-round budget was declared before the
first dispatch; three rounds ran; the operator interrupted the fourth and halted the run.

This is a third ending — an operator decision — and it is recorded as one. It is **not** convergence,
and nothing below should be read as a clean bill of health.

| Round | Findings | Where they landed |
|---|---|---|
| 1 | ~35 false statements + 12 behavioural | Shipped code, bundle prose, tests, the report |
| 2 | 21 false + 5 behavioural | 8 of them *inside files round 1 had just edited* |
| 3 | ~21 false + 5 behavioural | 3 of them inside files round 2 edited **to fix that exact pattern**; plus a regression round 2 introduced |
| 4 | **not run** | — |

**Every finding from rounds 1–3 was fixed and pushed.** No finding was deferred, and no survivor was
argued open under condition B. That is a fact about rounds 1–3 only.

⭐ **The signature never changed across three rounds:** each round's fix landed at the site the
finding named and not at the sites restating the same claim. Round 3 found *more* shipped-surface
defects than round 2, not fewer. **A fourth round would almost certainly have found more.**

### What to assume about the deliverables

Read the shipped change as **still carrying defects of the kind each round kept finding** —
predominantly:

- prose restatements of a changed claim, at sites the fix did not reach;
- rationale clauses asserting a mechanism nobody executed;
- guards whose fixture cannot distinguish the defect they name.

That is not a hypothetical residue. It is the measured, three-times-repeated behaviour of this
change under audit.

---

## 2. What was actually built

**37 files changed, +2831/−250, across 8 commits.** One new production module, three new test modules.

| Deliverable | State |
|---|---|
| **D0** — confirm each defect at HEAD | **Done.** All six claims verdicted with file-and-symbol citations, including the one 280 left unsited. Mutated nothing. |
| **D1** — closure, not existence | **Done.** `_qgate_closure.py` computes projection, referrer and claim-versus-index closure; wired into the phase-4-plan mechanical Q-Gate as checks 7 and 8. |
| **D2** — run the declared sweep before freezing the write-set | **Done.** Declared globs are expanded and reconciled against the enumerated declaration; the `{declared scope wide, write-set narrow}` pair is detected mechanically. |
| **D3** — assert `detector_population ⊇ fix_set_population` | **Done.** Stated normatively in `q-gate-validation.md` § 2.9a; discharged by a published `population` block that flips `ambiguous` when incomplete. |
| **D4** — a closure claim is a hint, never a licence | **Done, structurally.** The closure checks live in the unconditional Step 8, not the bypassable Step 8b. Verified adversarially. |
| **D5** — tests, each verified to fail pre-fix | **Done via mutation.** 49 new test functions; 32 mutants, each detected by the guard that names it. |

### The finding that most justified the work

The survey-scope declaration (`**Files to survey:**` / `**Files expected to mutate:**`) — the form
`outline-workflow-detail.md` *mandates* for discovery-style deliverables — **was parsed by nothing.**
A deliverable authored exactly as the standard requires parsed to an empty file list, **failed
outline validation**, had an empty write-set, and contributed nothing to the recall check. The
standard's own statement that recall "runs against the `Files expected to mutate:` subset" was
therefore **false** — every citation in it valid, the behaviour claim not. That is the plan's
*"verification checks a spec's CITATIONS but not its ASSERTIONS"* sub-class, found first-party.

---

## 3. Defects the audit found in this run's own work

Recorded because they are the most useful output of the exercise.

| # | What | Round |
|---|---|---|
| 1 | **The D1 acceptance fixture was vacuous.** `_check_files_exist` skips `write-replace` intent, and every fixture step carried it — so `files_exist: 0` was a skip, not a measurement, while a docstring, a comment, a test description and the report all claimed it proved existence. Proved by swapping in absent paths and watching every test still pass. | 1 |
| 2 | **An invented rationale in shipped prose.** The B2 bypass was documented as suppressing `consumer_sweep_completeness`; it suppresses only `module-mapping-validator` / `scope-criterion-validator`. A mechanism asserted without checking which validators the call site activates. | 1 |
| 3 | **The closure checks had the defect they exist to report** — three unmeasured scopes published as measured-empty (repo-escaping glob, un-normalised in-repo `..`, directory-only match). | 1 |
| 4 | **Three vacuous guards**, each caught by mutation rather than by reading: a no-op glob filter with a docstring explaining a mechanism it was not performing; a redundant guard mistaken for load-bearing; a mutant pointed at a suite that did not test the gate it named. | 1–2 |
| 5 | **A regression introduced while fixing a finding.** Round 2's holistic carve-out was placed after the population accounting, publishing "3 targets scanned" over a population where 1 entered the check, with `population_complete: True` — a measured-looking verdict over an unexamined surface, inside the module that states the rule against it. | 3 |
| 6 | **Two mutants surviving in D2's own deliverable**, because every claim-versus-index fixture expanded to exactly one file and the only multi-hit test monkeypatched the cap. The first fix written for this was **itself vacuous** — below the cap the two numbers coincide. | 3 |
| 7 | **Two more invented version/path claims of mine**, both falsified in one command: a `ValueError`-from-3.13 claim (both interpreters raise `NotImplementedError`), and "names a real populated directory" for a path that does not exist. | 2 |
| 8 | **The build gate caught what the narrower calls could not.** `./pw verify` failed on `test-compile` while `./pw quality-gate` and per-file `pytest` runs were green throughout — and the wrapper exited 0 on the failing run. | — |

---

## 4. What is NOT done

⛔ These are contract steps the run never reached. None is "effectively done".

| Step | State |
|---|---|
| **Verification round 4** | **Not run.** Budget was 4; three ran. |
| **PR** | **Not created.** No PR number exists. |
| **Review-comment cycle** | **Not started.** No reviewer has seen this change. |
| **Reviewer participation record** | **Empty.** The expected population derived from configuration is `coderabbitai`, `cuioss-review-bot`, `sourcery-ai` (the `author_login` of each `automatic-review/standards/{bot_kind}.md`). **Coverage is 0 of 3** — not because reviewers were rate-limited or silent, but because they were never invited. |
| **Merge gate** | **Not reached.** Not armed, not merged. |
| **Contract check (Step 9)** | Superseded by this document. |
| **"What have we learned" (Step 9)** | **Not produced.** No contract-change proposal was drafted; see § 6 for the evidence a future run should use. |

---

## 5. Residue — carried, with the reason

| # | Item | Disposition |
|---|---|---|
| R1 | **The routing decision's pre-override input is destroyed by its output.** `cmd_scope_estimate_heuristic` writes `references.scope_estimate`; that field is the router's own S2 signal, and the deep lane's refine Step 9 overwrites it. `scope_provenance` is logged but never persisted. **Asymmetric:** routing *deep* destroys the input that selected deep; routing *light* leaves it intact — so the evidence survives exactly when nobody needs it. | **Sited at D0, deliberately not fixed.** No deliverable names it, and the plan says to split a new arm rather than absorb it. A concrete follow-up: persist `scope_provenance` alongside `scope_estimate`. |
| R2 | **A `disabled` plan's footprint is derivable but reported unresolvable.** Carried from 280's residue, which the plan's Notes hand to this arm. | **Not scoped.** 280 implemented it, measured it, and **reverted** it with two pieces of evidence: it makes a finalize-step drop reachable, and it is non-hermetic (footprint derivation would depend on unrelated uncommitted state). Cross-cutting across `manage-references`, the composer and `extension_base`. Read 280's report before scoping. |
| R3 | **~14 pre-existing sites** say the execution manifest is composed at "phase-4-plan Step 8b"; canonical is **Step 7b**. | **Two corrected** where this change already touched them; the rest are stale on `origin/main` and out of scope. |
| R4 | **Survey-pair disjointness is an authoring rule no check enforces.** `validate_deliverable_contract` does not compare the two lists. | Consumers dedupe defensively (`deliverable_write_set`, `_foreign_paths_by_deliverable`); a validator check would close it properly. |
| R5 | **`references.affected_files` does not carry the survey pair.** The B2 predicate's documented derivation now says where to get the right cardinality, but the underlying field is still written by `q-gate-validation.md` § Step 7 from the flat list. | Documented, not fixed — the writer is outside this plan's surface. |

---

## 6. Evidence for a future contract-change proposal

Not proposed here (the run stopped before Step 9), but this run produced the evidence:

⭐ **The lane contract's stopping rule assumes a loop that converges. This one did not, and the
contract offers no way to say so except "the budget ran out."** Three rounds each found
*more* shipped-surface defects than a naive reading would predict, and round 3 found a regression
*introduced by round 2's fix*. A run that stops on the budget currently reports the same `Outcome` as
one that stops on a verifier's all-clear, with the difference buried in a stop record. The contract
would be stronger if a **non-converging** loop were a first-class outcome the report must name in its
header — because the useful signal is not "verification finished" but "each round is still finding
defects at the same rate, and the last one found a regression."

Secondary, smaller: the contract tells a run to write scratch under `$TMPDIR`, and two independent
sub-agents clobbered each other's mutation harness by choosing the same filename. A one-line rule —
*scratch paths are unique per agent* — would have prevented it.

---

## 7. Build gate

- `git diff --name-only origin/main...HEAD -- '*.py'` → **8 production scripts, 9 test modules**
  (re-derived at the moment of this claim), so the full gate applies.
- **Per-commit gate:** `./pw quality-gate` before every `*.py`-touching commit, read from the tools'
  streamed output — `Success: no issues found in 414 source files`, `All checks passed!`,
  `SPDX-header check passed`.
- **Branch gate:** `./pw verify` ran four times. ⚠ **The second run FAILED** —
  `verify: test-compile failed`, a test-only type error invisible to `quality-gate` and to per-file
  `pytest`, with the wrapper still exiting 0. Fixed in `0702530`.
- **Final gate — clean**, run at `0f10d16` with no other process touching the tree:
  `=== verify: SUCCESS ===`, **20840 passed, 14 skipped in 6:25**, 0 failed / 0 errors, all six
  sub-dimensions at full scope (mypy 414 production + 770 test files, ruff, SPDX, plugin-doctor
  marketplace-wide, whole-tree pytest).

⛔ **Read the gate for what it is.** The build's own coverage line says it: SPDX cannot evaluate file
content, plugin-doctor cannot evaluate whether a documented claim is true, `mypy(test)` cannot
evaluate whether a well-typed test asserts anything, and `module-tests` is silent on every input no
test supplies. A green gate is evidence about those dimensions and **is not** whole-tree assurance
that this change is sound — which is precisely why three verification rounds still found defects
against a green tree.

---

## 8. If this work is resumed

1. Run verification round 4 (and expect findings).
2. Open the PR. **Do not apply `skip-bot-review`** — this diff changes `*.py` and
   `marketplace/bundles/**`, and a skill is code that gets reviewed.
3. Work all **three** comment surfaces — issue comments, review-summary bodies, and inline review
   threads are three different API calls, and the review bots' consolidated findings land in the
   second one.
4. Record per-reviewer participation from the **bodies**, with a `Reopens?` value per non-`reviewed`
   verdict, and disclose any shortfall before arming auto-merge.
5. Finalize `report-01.md` and commit it as the **last pre-merge commit** — arming auto-merge locks
   the branch against further pushes.
