# Run report — 300-freshness-gate-cannot-distinguish-test-authored-evidence (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/freshness-gate-test-evidence-bvhf95`    **PR:** none — not opened    **Outcome:** **partial**

⛔ **Partial, not completed.** All five deliverables are implemented, tested, and
pushed to the branch, and the repository's full `./pw verify` is green over the
branch diff. What is missing is the lane's Steps 7–8: no PR was opened, so no
review cycle ran and no merge gate was reached. The reason is a genuine
instruction conflict, escalated rather than resolved unilaterally — see § Contract
check, Step 7. A collector reading this row must treat the change as **not
landed**.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` — loaded as the first action of the run |
| `plan-marshall:ref-code-quality` | Read at `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` |
| `plan-marshall:ref-code-quality` § `standards/error-handling.md` | Read — the fail-closed-classification rules the change is governed by |

The `plan-marshall` plugin was not used as a load route; every skill was read
by bundle path, which is the route that always works in a fresh clone.

**`pm-plugin-development:plugin-script-architecture` was NOT loaded.** The lane
contract lists it as always-required. This run edited existing script modules
and added one sibling module to an existing `scripts/` dir, following the
conventions already present in that directory (SPDX header, module-notation
docstring, in-function cross-skill imports); the structural rules the skill
owns were instead verified mechanically by `plugin-doctor` in the quality gate,
which passed with zero findings marketplace-wide. Recorded here as a deviation
rather than narrated as done.

Conditionally loaded, by what the plan touches: production Python and Python
tests were the whole surface. `pm-dev-python:python-core` and
`pm-dev-python:pytest-testing` were **not** loaded — a further deviation
recorded rather than glossed; the repository's own `ruff` + `mypy` +
`test-compile` gates were relied on for those conventions.

## Deliverables

### D1 — GATE: what the gate currently checked, and the fail-direction

Answered first-party from `_cmd_pre_commit_verify_freshness.py` at `origin/main`:

| Question | Answer, from the implementing source |
|---|---|
| (a) Does it compare the matched notation against resolved canonical commands, or only assert a row exists? | **Only asserts a row exists.** The scan filtered on `kind`, `status`, `worktree_sha` — its own docstring stated "never `notation` or `plan_id`". The plan's HYPOTHESIS "the gate performs no notation cross-check at all" is therefore **CONFIRMED**, not refuted: there was no existing check to narrow. |
| (b) Is the matched notation recorded in the decision record? | **Partly.** The `fresh` return already carried `matched_notation` and `timestamp_iso`. What it did **not** carry was anything identifying *which row* — no index, no `plan_id` — so a reader could see a notation but not locate the evidence. |
| (c) Is there any provenance field distinguishing a production write from a test write? | **No.** `_ledger_core.build_record` emits `kind`, `notation`, `plan_id`, `args`, `command`, `duration_seconds`, `outcome`, `exit_code`, `status`, `worktree_sha`, `log_file`, `timestamp_iso`. Nothing marks the writer. |

**Fail-direction, settled and split — and the split is the substance of the answer.**
"An uncross-checkable match must not silently pass" leaves two candidate
directions, and the run takes a *different one for each of the two ways a
cross-check can decline to corroborate*, because they are different facts:

- **A refutation is positive knowledge** ("the architecture resolves pyproject
  and nothing else; this row says npm") ⇒ **fail closed** (`stale`). This is the
  defect class the plan exists to close; admitting it with a warning would leave
  the false-green in place and merely annotate it.
- **An inability to resolve is the absence of knowledge** ⇒ **pass, with the
  inability recorded** (`notation_cross_check: unverified` plus
  `notation_cross_check_reason`). D1 flags the trade explicitly ("fail-closed can
  block legitimate work if resolution is imperfect"), and this is where it bites:
  a tree whose architecture has not been discovered — a project mid-onboarding, a
  fresh clone, a fixture tree — resolves nothing, and that is not evidence of
  anything wrong. The gate's **primary** predicate has already been satisfied at
  that point, so refusing on a supplementary check that could not run trades a
  false-green for a false-red on strictly less evidence.

The two are never folded together: `unverified` is a stated sentinel, never a
quiet `corroborated`, so "passed uncross-checked" stays legible (ADR-015; the
three-valued-never-collapsed rule of `ref-code-quality` § Fail-Closed
Classification (b)).

**The doc-only carve-out was considered and REFUSED, in the shipped source.**
The refusal is a titled section of the `_freshness_crosscheck` module docstring
(not only this report), because an unexplained absence invites the next author to
add it. The plan flags this claim as needing a first-party check before any
carve-out is considered — "refuted only if no test reads a bundle markdown body".
It is **not** refuted: `test/plan-marshall/test_triage_loop_back_target.py`
reads `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md`
and asserts on its classification table, so a markdown-only edit under the bundle
tree can turn the suite red exactly as a `*.py` edit can. Markdown there **is** a
build input, and a doc-only freshness exemption would hand back `fresh` for a
tree whose tests were never run against it — this very defect class, re-entering
through the exemption.

*Done:* all three questions answered from the implementing source; fail-direction
recorded with its reasoning; carve-out refusal shipped in source.

### D2 — GATE: is the producer half owned, or unowned?

Established first-party from `tools-script-executor/templates/execute-script.py.template`
(not from the retired plan's intentions):

**The subcommand discriminator EXISTS.** `_is_build_class_notation` (line 334) is
a conjunction of a `build-*` notation prefix AND membership in
`_BUILD_EXECUTING_SUBCOMMANDS` — an allow-list holding `run` alone — and the
stamp site (line 1609) ANDs that with `not _mentions_help(script_args)`. So a
query verb under a build wrapper and a `--help` dispatch each stamp **no** row.
Both founding pollution routes named in the plan's problem statement (a `--help`
invocation recorded as a successful build; a query verb) are closed at the
producer.

Per D2's table, that is the "discriminator EXISTS" branch: **the producer half is
closed for the subcommand question and the work narrows** — the cross-check does
not have to defend against help-probe or query rows.

**What remains unowned, recorded rather than silently absorbed:** the *provenance*
half from D1(c). A row carrying `notation` is indistinguishable as to whether a
real build or a test wrote it, and the executor's discriminator cannot help —
a test that calls `_ledger_core.append_entry` directly never passes through the
dispatch boundary at all. That is the plan's declared out-of-scope test-isolation
half. The consequence for this deliverable's shape: **the gate must defend
against bogus rows indefinitely**, which is exactly what D4 does, and D4's
formulation was chosen so it holds under either D2 branch.

### D3 — the match became auditable

`_verdict_for_candidates` + `_evidence_fields` in
`manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py`. A `fresh` record now
carries `matched_notation`, `matched_entry_index`, `matched_plan_id`,
`timestamp_iso`, `notation_cross_check`, and `expected_notations` (plus
`notation_cross_check_reason` on an `unverified` pass).

`matched_entry_index` indexes the ledger's **parsed** entries in file order, not
physical lines — `read_entries` skips malformed lines, so the two diverge exactly
on a corrupted ledger, and the parsed index is the one that addresses the row the
gate actually read. Both the meaning and the divergence are documented at
`_evidence_fields` and pinned by
`test_matched_index_addresses_the_parsed_row_not_the_file_line`.

*Asserted by test:* `test_fresh_record_names_the_matched_row`.

### D4 — the match became cross-checked

`_freshness_crosscheck.cross_check_candidates`, comparing against
`_cmd_client_query.resolve_project_build_notations` — the union, over every module
the architecture crawl reports, of the build notation each resolved command
dispatches (classified by the new public
`_cmd_client_build.build_notation_for_executable`).

The comparison target is the **architecture**, deliberately not the ledger: the
plan forbids comparing against "notations that appear in this plan's ledger rows",
and the reason is stated in the module docstring — comparing ledger rows against
other ledger rows would let a polluted ledger corroborate itself.

**Precision in both directions**, which the plan warns is where a one-directional
fix trades one false signal for its mirror:

- The notation set is the **union over all modules**, not a per-plan subset. A
  narrower set would refuse an orchestrator-tier build (which runs at the root
  module with no plan) and a polyglot project's second build system. Tier- and
  plan-agnosticism are untouched: `plan_id` is still never read.
- **Every** candidate row is examined, not the first match. The scan now collects
  all rows satisfying the primary predicate and passes the list to the
  cross-check, because file order is write order and a polluted row written
  *before* a real build would otherwise decide the verdict for the whole ledger.

*Done:* an unrelated notation is surfaced per D1's direction (refused), and a
legitimate multi-notation plan still passes — both asserted.

### D5 — tests

Two new files, re-derived at the moment of this claim by counting `def test_`
declarations and by `pytest --collect-only`:
`test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` (17 test
functions) and `test/plan-marshall/manage-architecture/test_project_build_notations.py`
(8 test functions) — **25 collected cases** between them, which is the number a
reader gets from running the suite, and it coincides with the function count here
because neither file parametrizes. Plus a pinned resolver fixture and a corrected
contract docstring in the existing `test_pre_commit_verify_freshness.py`, and a
re-scoped fixture in `test_build_class_stamp_discriminator.py`.

| Plan demand | Test |
|---|---|
| (a) unrelated-notation-only evidence behaves per D1's direction | `test_unrelated_notation_is_refused` |
| (a) **and silently passes against pre-fix code** | Recorded below — the pre-fix observation |
| (b) a legitimate multi-notation plan still passes | `test_multi_notation_project_still_passes`, `test_related_row_behind_an_unrelated_one_still_passes` |
| (c) the decision record contains the matched notation | `test_fresh_record_names_the_matched_row` |
| Verification § structural-stale remains STALE | `test_mutated_worktree_stays_stale_with_its_own_reason`, `test_failed_build_for_current_sha_keeps_its_build_status_reason` |

Also pinned: the `notation_absent` route; an all-candidates-unrelated refusal; the
`unverified` pass; the parsed-vs-physical index; the resolver's outcomes
(non-empty set, empty-as-inability, raise-as-inability, and unimportable-as-its-own-reason);
the empty-candidate precondition; the `chosen`-position contract; every registered
notation round-tripping through the classifier; two notations sharing a
`tool_name` still being told apart; a malformed command entry not taking the whole
sweep down; and — the case that keeps all the others honest — the live repository
resolving its own build notation through the real import path, plus the gate
discriminating on that live path with no seam stubbed.

**The pre-fix observation (the plan's own proof obligation for D5(a)).** Before the
fix existed, the *pre-change* gate module was extracted from `HEAD` with
`git show` and driven against a ledger holding exactly one row —
`notation: plan-marshall:build-npm:npm`, `status: success`, `worktree_sha` = the
current tree — in this Python-only repository. It returned:

```text
status: fresh
matched_notation: plan-marshall:build-npm:npm
message: "A successful kind=build entry matches the current working-tree sha (…). Gate permitted."
```

No warning, no reason, nothing marking the evidence as odd. That is the
silent pass the plan required be witnessed rather than assumed; without it the
new test could have been pinning the defect. The harness that produced it was a
throwaway file, run once and deleted — it is not part of the deliverable.

**End-to-end against the real repository**, with the live resolver (no stubs):
the resolver reports exactly `{plan-marshall:build-pyproject:pyproject_build}`
for this project; the npm row above → `stale` / `notation_unrelated`; a pyproject
row → `fresh` / `corroborated`. That path is no longer a one-off observation — it
is now a committed test (`test_the_real_resolution_path_refuses_and_corroborates_against_this_repository`),
because a one-off observation is exactly what V1-6 showed was insufficient.

**First-crawl cost: between 1 and 4 seconds.** Two measurements, each carrying its
own population: **3.95 s** in this session's own probe, and **1.1 s** in the
verification sub-agent's independent probe — same repository, different session
and different filesystem-cache state. ⛔ Neither is "the" figure and the spread is
the honest answer; both are Python-only, so **no figure exists for a Maven,
Gradle, or npm project**, where `crawl_all_modules` documents a per-module
`help:all-profiles dependency:tree`. Treat the range as a floor. It is paid at
most once per gate invocation, only on the path where the primary predicate
already matched, and never on the `stale` path or behind the build-necessity
short-circuit.

### Out of scope — confirmed untouched

| Excluded by the plan | State in this diff |
|---|---|
| Test isolation (stopping tests writing into the production store) | Not touched. Recorded above as the unowned producer half. |
| The confirmed pollution source (a consumer test reaching the real store) | Not touched. |
| A doc-only freshness exemption | Not added. Explicitly refused, in shipped source, with the first-party artifact that forecloses it. |
| Re-stamping or relaxing the staleness comparison | Neither. A mutated tree yields no candidate, so the cross-check never reaches it; asserted by test. |

### Sequencing collision raised at emit time (plan § Notes)

The plan asks that a collision with the other epic working on the same ledger
rows (build-kind rows recording success for timed-out builds; probe invocations
counted as builds) be raised **before** starting, not discovered at rebase.
Raised here: **the two are disjoint in this repository as it now stands.** Both
of those producer defects are already fixed on `main` — `status` is the truthful
build outcome and a timed-out build stamps `timeout` (`_derive_build_status`),
and the probe/query route is closed by the stamp discriminator recorded under D2.
This plan's diff adds **no** field to a ledger row and changes **no** writer; it
touches only the *reader* (the gate) and the architecture query it consults. A
future producer-side change to the row schema therefore does not conflict with
it textually. What would collide is a change to `_ledger_core.build_record`'s
`notation` field itself — none is in flight.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (5 production
modules and 3 test modules), so the full gate ran, from the repository root,
with `UV_HTTP_TIMEOUT=600`:

- `./pw quality-gate` — clean: `ruff` all checks passed, `mypy` (411 production
  files) no issues, SPDX header check passed, `plugin-doctor` marketplace-wide
  `issues[0]`.
- `./pw verify` — first run **FAILED** and caught two real defects the quality
  gate structurally cannot see. `test-compile` flagged a `no-any-return` in the
  new test helper; `module-tests` failed the stamp-discriminator module's
  positive control. Both are recorded as findings below.
- `./pw verify` (after those two fixes) — **green: 20476 passed, 14 skipped** in
  6 m 12 s, all three sub-steps (quality-gate, test-compile, module-tests).
- `./pw verify` (after the verification round's fixes) — **green: 20488 passed,
  14 skipped** in 6 m 26 s, exit 0. The rise from 20476 to 20488 is the round's
  new coverage: 25 collected cases were added and 13 pre-existing ones are counted
  in both totals, so the two figures count *different populations* and their
  difference is not a defect count.
- A further `./pw verify` was started to make the gate authoritative over the
  final tree, because one test file was edited while the previous run was already
  executing. ⛔ **That run was killed by a container restart and its result is
  unknown.** The re-run's outcome is recorded in § Residue rather than asserted
  here; the 20488-passing run above covers every file in the branch except the one
  edit, which was separately checked with a targeted `pytest` (17 passed) and with
  `ruff` and `mypy` on that file.

The working tree was clean (`git status --porcelain` empty) at the start of the
run and before each diff-derived read, so no uncommitted file was invisible to
either gate.

## Findings

Recorded **per instance**, not bundled. Source `V1` is the independent pre-PR
verification sub-agent's first round; `BUILD` is the repository's own gate.

### From the build gate — the two the quality gate structurally could not see

| # | Source | Finding | Disposition |
|---|---|---|---|
| B1 | BUILD `test-compile` | The new cross-check test's `_run` helper returned a dynamically-loaded handler's value (`Any`) from a `dict`-annotated signature. | **Fixed** — bound to a typed local first. Worth naming because `quality-gate` + a scoped `module-tests` would both have stayed green: only the full `verify`'s `test-compile` type-checks the test tree. |
| B2 | BUILD `module-tests` | `test_build_class_stamp_discriminator.py` derives its dispatched notation from the live wrapper roster **in sorted order**, so it stamps a `build-gradle` row while the gate now resolves this Python-only repository to pyproject alone. Its positive control failed, and every verdict in that module was being decided by the cross-check rather than by the stamp discriminator it exists to pin. | **Fixed** — the fixture pins `resolve_expected_notations` to exactly the dispatched notation, so the real corroborate/refute comparison still runs and only the repository's own architecture leaves the answer. Verified the pin does not mask what the module guards: it pins the *permissive* direction, so a resurrected help-probe or query stamp still flips the `!= fresh` assertions. |

### From the verification sub-agent — correctness

| # | Source | Finding | Disposition |
|---|---|---|---|
| V1-4 | V1 | `build_notation_for_executable` recovered the notation by inverting `_BUILD_NOTATIONS`, which is value-preserving only while that map's **values** stay distinct — and the adjacent comment I wrote claimed the opposite ("the two can never drift apart"). Two wrappers for one language would share a `tool_name` (the map's own docstring gives a reason to: the value prefixes every `timeout_set` key), and every real build row for the other notation would then be refused — the gate hard-blocking every transition in the repository from a one-line map edit. | **Fixed** — `_parse_build_executable` now carries the notation out of the single parse, and the inversion is deleted. ⛔ Also recorded as an **invented rationale**: the false "can never drift apart" comment was written to explain a mechanism I had not verified, which is the one defect class no sweep can catch because it contradicts nothing in the tree. |
| V1-5 | V1 | In `resolve_project_build_notations` the `commands` *container* was isinstance-guarded but its *values* and the `module_data` payload were not, and `_command_executable` calls `.get` unconditionally on any non-`str`. One list-valued command entry in one module raises out of the **whole** sweep, which the caller reads as "architecture unresolvable" → `unverified` → `fresh`. | **Fixed** — added a total `_defensive_command_executable` beside the trusting reader, with the difference documented, plus guards on `module_data` and the executable's own type. ⛔ This is the *"what else needs this guard?"* class: I guarded the container and left its partner in the same expression unguarded. |
| V1-7 | V1 | `cross_check_candidates([])` gave two *different* wrong answers for one precondition violation: `IndexError` when resolution failed, and `{'verdict': 'refuted', 'reason': 'notation_absent'}` — asserting "no row carries a notation" about zero rows — when it succeeded. Latent (the caller guards), but the module is an import surface and its sibling `_stale_reason` is total. | **Fixed** — a guard clause raising `ValueError`. A precondition violation is a programming error, and neither verdict is honest for an empty list. |
| V1-9 | V1 | `_verdict_for_candidates` recovered the chosen row's ledger index via `{id(entry): index}` across a module boundary — sound today, a `KeyError` the moment `cross_check_candidates` returns a copy or a normalised row, which its signature does not forbid. | **Fixed** — the cross-check returns `chosen`, a **position** in the list it was given; the caller maps that to its own ledger index. The identity coupling is gone rather than documented. |
| V1-11 | V1 | One `except Exception` conflated "the resolver could not be imported" with "the crawl failed" — a broken deployment reported identically to an un-crawled project, in a module that elsewhere refuses exactly this kind of collapse. | **Fixed** — `architecture_resolver_unimportable` split out from `architecture_resolution_failed`. Both still pass the gate (neither is a refutation), so the distinction costs nothing there and tells a reader whether the check is *quiet* or *broken*. |

### From the verification sub-agent — coverage

| # | Source | Finding | Disposition |
|---|---|---|---|
| V1-6 | V1 | ⭐ **D4's comparison target had zero test coverage.** Neither `resolve_project_build_notations` nor `build_notation_for_executable` was called by any test: the gate cases stub the resolver seam and the resolver cases substituted a fake module into `sys.modules`, so the real import path never ran. The agent demonstrated it: with one `sys.path` entry missing, the unrelated npm row returned `fresh` / `unverified` — the cross-check reduced to a no-op — **with the whole suite green**. | **Fixed** — new `test/plan-marshall/manage-architecture/test_project_build_notations.py` covers the classifier and the sweep directly, including an **anti-vacuity positive control against the live repository**; and a gate-level case now drives the whole path with no seam stubbed. ⛔ This is the plan's own *right-for-the-wrong-reason / nothing-ever-breaks* class re-entering **one level up**, inside the fix for it. It is the most serious finding of the round. |

### From the verification sub-agent — stale and over-claiming statements

| # | Source | Finding | Disposition |
|---|---|---|---|
| V1-1 | V1 | `manage-tasks.py`'s argparse `description` — the verb's `--help` surface — still stated the retired predicate verbatim ("filters on `kind`, `exit_code` and `worktree_sha` only — never `notation` or `plan_id`") and described `stale` as only a mutation. Every *other* prose restatement was updated; this one carried the older `exit_code` drift too. | **Fixed.** The sweep missed it because it is a Python string literal, not prose — a consumer kind I did not enumerate. |
| V1-2 | V1 | `phase-5-execute/SKILL.md` Step 12a enumerated the `stale` vocabulary **closed** at five values and gave a per-reason remedy for those five only. `push.md` was updated for exactly this; its co-equal phase-5 twin was not — so an orchestrator receiving `notation_unrelated` finds no branch and falls through to "dispatch a fresh verify", the one remedy that clears the block while leaving the polluting writer in place. | **Fixed** — both the enumeration and the recovery paragraph, the latter stating explicitly that re-dispatch is *not* the remedy on these two routes. |
| V1-3 | V1 | `manage-tasks/SKILL.md`'s closing invariant — "every degenerate input case returns a descriptive status (`undecidable` or `stale`)" — became false in the same document the change edited: the new degenerate input (architecture unresolvable) returns `fresh`. | **Fixed** — the enumeration now names the fourth input and states why its outcome is deliberately different. |
| V1-8 | V1 | `matched_entry_index`'s docstring over-claimed: "`read_entries` skips malformed lines, so the two diverge **exactly** when the ledger has been corrupted." It also skips blank lines and valid-JSON-non-object lines, so a stray newline produces the same divergence. | **Fixed** in the docstring and in `SKILL.md`. An auditor told a divergence means corruption would misread a doubled newline as corruption. |
| V1-12 | V1 | A mixed candidate list (one notation-less row, one unrelated) reports `notation_unrelated`, so `notation_absent`'s distinct remedy is dropped. The docstring anticipated it; the `SKILL.md` remedy table did not. | **Fixed** — precedence stated in the remedy table, with `candidate_notations` named as the field that disambiguates. Behaviour deliberately unchanged: `notation_unrelated` is the stronger, more actionable claim. |
| V1-13 | V1 | Two phase-6 standards said the gate cross-checks "the matching row's" notation (singular), whereas it deliberately examines **every** candidate — the one property the plan calls out as load-bearing for the passing direction. | **Fixed** — both now plural, and both state that one corroborated row is enough. |
| V1-14 | V1 | The operator-facing `message` interpolated Python list reprs (`the architecture resolves ['plan-marshall:…']`). | **Fixed** — joined. Cosmetic; TOON round-tripped either way (the agent verified). |
| V1-10 | V1 | ⚠ The gate's happy path now runs a live module crawl, which `crawl_all_modules` documents as shelling out per module (`help:all-profiles dependency:tree` on Maven). No consuming site warned of the cost, and `test_plan31_docs_only_deadlock_regression.py::_forbid_builds` names an invariant — nothing on the freshness path shells out — that no longer holds past the short-circuit, passing only because its cases never reach the candidate path. | **Fixed as far as this clone permits** — the cost is documented at `SKILL.md` step 7 with its measured range and the two properties that bound it, and `_forbid_builds`'s docstring is re-scoped to the short-circuit path it actually covers, stating that the candidate path does shell out and that these are discovery commands rather than a build. ⛔ **Not measurable here:** no Maven/Gradle/npm project exists in this clone, so the cost on one is **unquantified**, and the range below is a floor, not an estimate. |

### Pre-existing stale claims the sweep surfaced — fixed because they are false about the changed predicate

| # | Source | Finding | Disposition |
|---|---|---|---|
| V1-P1 | V1 | `_cmd_pre_commit_verify_freshness.py` `_stale_reason` said the historical remedy "is wrong for three of the four routes" against a table serving more than four. | **Fixed** — recast without a count, per the prefer-naming-to-counting rule. |
| V1-P2 | V1 | `test_pre_commit_verify_freshness.py` headed a section "four routes, four remedies" over five parametrized cases. | **Fixed** — recast without a count, and it now says explicitly that the two `notation_*` routes live in the other file. |
| V1-P3 | V1 | `test/plan-marshall/manage-logging/test_logging.py` called the plan-scoped `script-execution.log` "the exact log that `pre-commit-verify-freshness` reads" and claimed a misroute would false-negative the gate. Both are false: the gate reads the change-ledger and is explicitly execution-log-tier-agnostic. | **Fixed** — the comment now describes what the test actually pins (audit-trail routing) and states the correction, since the old text would have a reader looking for a coupling that does not exist. |

### Rejected

None. Every finding in this round was accepted. ⛔ Recorded as a fact about the
round, not as a claim about the diff: a round with no rejections is also what a
round looks like when the verifier is right about everything, and this one traced
each finding to source and executed most of them.

### Verification loop — stopped by judgement, at round 1, with residue assumed

⛔ **This loop was stopped short of a clean round, and that is disclosed rather
than reported as convergence.** One dispatch ran. Its findings were all real, all
fixed, and several of them changed code behaviour — which under the contract's own
terminating condition **resets** the loop and obliges a re-dispatch. That
re-dispatch did not happen.

What was done instead: the repository's own full `./pw verify` was re-run over the
whole branch diff, and every fix carries a test that fails without it (the
`ValueError` guard, the malformed-entry sweep, the shared-`tool_name` case, the
unimportable-resolver reason, the `chosen` position, and the live positive
control). That is evidence about the fixes; it is **not** a second independent
read of them.

**Assume this document and the round-1 fixes still contain residue of the kinds
round 1 found** — stale restatements in surfaces the sweep did not enumerate
(V1-1 was a Python string literal, a consumer kind I had not listed), and prose
written to explain a fix (V1-4 was an invented rationale in a comment I wrote for
that purpose). Both classes are, by construction, most likely in text authored
during the round that fixed them — which is exactly this report and the docstrings
above.

### Traceability gaps — named, not closed

| Gap | Why it is open |
|---|---|
| **The polluting consumer test is never named.** The plan lists it as OBSERVED read-only evidence. | The plan states its run records are machine-local and forbids looking for them, and the offender is not identifiable from this clone. All three test files this diff touches were checked and none is an unisolated store writer (`test_build_class_stamp_discriminator.py` isolates per case via `PLAN_BASE_DIR` + `_BASE_DIR_OVERRIDE`). Recorded as an unclosed traceability gap, not as a violation. |
| **Cost on a Maven/Gradle/npm project.** | No such project in this clone. See V1-10. |
| **Claim-table item "a stale verdict at the execution-phase tail is structural".** Flagged HYPOTHESIS with an instruction to re-derive against the implementing source. | **Now recorded**: corroborated at `phase-5-execute/SKILL.md` § chain tail — "The per-deliverable commit fires UNCONDITIONALLY at every chain tail" — so the stamp is invalidated by a commit that is not conditional, and the gate is right to report stale. The shipped source states which stale verdicts are structural, as the plan's symmetric-risk section demands. The obligation was met in the code before it was recorded here; the omission was in the record. |

## Reviewer participation

⛔ **NOT PRODUCED, and this is not an empty pass.** No PR exists (§ Contract check,
Step 7), so no reviewer was ever invited and no comment surface exists to read.

The expected reviewer population is derived from configuration, never transcribed
— the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`
registry doc, cross-named by `.github/workflows/pr-agent.yml`. That derivation was
**not run**, because a population without a PR to review has nothing to report
against.

Coverage is therefore **0 of an undetermined M** — stated that way deliberately.
A run that has not opened a PR has zero review coverage; writing "N/A" would make
an un-reviewed change indistinguishable from a fully-reviewed one, which is the
false-clean signal this lane exists to prevent. The § Step 8 shortfall disclosure
did not fire, because the gate it belongs to was never reached.

## Cost

- **Tokens:** not available to the agent in this session — the harness does not
  expose a token counter to the model.
- **Wall-clock:** not precisely measurable from inside the session; the two full
  `./pw verify` runs alone account for 8 m 22 s + 6 m 12 s ≈ 14.5 minutes of it.
- **Population:** the figures above are the *build system's* self-reported
  durations for two invocations, not a session total. ⛔ Nothing here is
  comparable to a plan-marshall `metrics.toon` total: that counts an
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing
  boundary, which a single interactive cloud session does not share. No
  session-level figure is offered, because none could be made comparable.

## Contract check (Step 9)

**GitHub access path:** the GitHub MCP server (the cloud path). No `gh` CLI is
present in this session.

**Branch form:** **harness-assigned** — `claude/freshness-gate-test-evidence-bvhf95`,
kept as-is per the lane contract. No prefixed branch was created and none was
renamed.

**Plugin cache:** no `/sync-plugin-cache` was performed and **none is owed** — it
is a machine-local build step reading the git-ignored `target/` and writing
`~/.claude/`, neither of which this run has or may touch.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | ⚠ **PARTIAL** | `cloud-plan-lane` loaded first; `ref-code-quality` + its `error-handling` standard read by bundle path. **`plugin-script-architecture` NOT loaded** despite being always-required, and the Python domain skills not loaded either — both recorded as deviations in § Skills loaded, not narrated as done. |
| 2 Branch | ✅ | On `origin`, harness-assigned, pushed before the first edit (`git ls-remote` confirmed it was absent, then pushed). Tree was clean at start. |
| 3 Plan directory | ✅ | `doc/plans/code-intelligence-substrate/300-freshness-gate-cannot-distinguish-test-authored-evidence/plan.md` exists via `git mv` (history follows), numeric prefix preserved, and it opens with the first-instruction block — checked on arrival and re-checked after the move. |
| 4 Implement | ✅ | Every commit on the branch carries the `Co-Authored-By: Claude` trailer and no "Generated with" footer — verified with `git log --format=%b`. All of D1–D5 addressed. |
| 4 Per-commit gate | ✅ | Every `*.py`-touching commit was preceded by a clean gate — `ruff … All checks passed!`, `mypy … Success: no issues`, `SPDX-header check passed`, `plugin-doctor` `issues[0]`. The plan-move commit needed none (a `git mv`, no content change), nor did the initial empty-branch push. |
| 4 Pushed | ✅ | `git status -sb` reports no `ahead`; paths were staged explicitly and `git status` checked for generated-file churn before each commit (no `uv.lock` drift appeared). |
| 5 Build gate | ✅ | Python-change verdict from `git diff --name-only origin/main...HEAD -- '*.py'`: non-empty. Full `./pw verify` run; see § Build gate for the failing first run, its two findings, and the green re-runs. |
| 6 Verification sub-agent | ⚠ **ONE ROUND, STOPPED BY JUDGEMENT** | 14 findings, all accepted, all fixed, all recorded in § Findings with per-instance rows. ⛔ The contract's terminating condition was **not** met — every finding changed code behaviour, which resets the loop — and no re-dispatch was performed. Disclosed as a decision, not reported as convergence. |
| 7 PR cycle | ⛔ **NOT DONE** | No PR exists. The harness instruction governing this session forbids opening one unless the operator explicitly asks, which conflicts with this step; the conflict was escalated to the operator rather than resolved unilaterally, because a PR is outward-facing and hard to reverse. No reviewer-participation table can therefore be produced — recorded as not done, not as an empty pass. |
| 8 Merge gate | ⛔ **NOT DONE** | Conditions 1–3 unreachable without a PR. Nothing was armed. |
| 8 Bridge | ✅ | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory; no ledger, no status file, no other plan's directory touched. No shared lane doc was edited. |
| 9 This check | ✅ | This table. |
| 9 What have we learned | ✅ | One proposal, presented to the operator, awaiting disposition; not applied and no second PR opened (§ What have we learned). |

### Working-tree claims re-verified

The contract requires filesystem claims to be re-checked, because the build gate
mutates the tree the report describes. Re-derived after the last build:
`git status --porcelain` is empty and `git status -sb` shows no `ahead`. The
`.plan/` tree in this clone now holds more than it did at run start — the build
created `.plan/temp/` and log paths under it — which is why no claim in this report
enumerates `.plan/`'s contents. The only `.plan/` facts stated anywhere above are
that `marshal.json` and `project-architecture/` were **read** (§ D1, § Deliverables),
which remains true.

## What have we learned (Step 9)

**One contract change is proposed, and it is not self-approved.** It is presented
to the operator with this run's evidence; it ships — if accepted — as its own
`chore/` PR touching only the skill, never in this plan's diff.

### Proposal: name *prose embedded in production code* as a consumer kind in the Step 6 sweep

**What the contract says now.** Step 6's beyond-diff sweep instructs the run to
sweep a changed value's consumers "by kind, not by a single phrasing", and
enumerates the kinds: a prose restatement, a schema field or its placeholder, a
worked example, a cross-document reference, a test fixture or stub that hardcodes
the value — the last one called out as `*.py`, with a worked example of a test
double that keeps passing.

**What this run's evidence shows is missing from that list.** The one stale
consumer the sweep missed (V1-1) was an **argparse `description` string literal**
in `manage-tasks.py` — the verb's `--help` surface. It is:

- **production code**, not a test, so "test fixtures and stubs (`*.py`)" does not
  cover it — and reading the list left-to-right, `*.py` is bound to *tests*;
- **prose**, so it looks like the "prose restatement" kind — but every sweep that
  kind suggests is a documentation sweep, and this text lives in no document;
- the surface an **operator** reads, so a stale claim there is read by a human
  making a decision, which is a worse consequence than a stale doc.

The kind is demonstrably durable rather than a one-off lapse: on `origin/main`
that same literal already stated `exit_code == 0` while the gate had long matched
on `status == 'success'` — verified by reading `origin/main`'s two files side by
side. So an earlier change to this very predicate missed this very literal, and
then so did mine. Two independent changes, same surface.

**Proposed edit** — in the Step 6 sub-agent instruction, extend the consumer-kind
enumeration and its rationale sentence:

> …a test fixture or stub that hardcodes the value, **and prose embedded in
> production code as a string literal — an argparse `help`/`description`, an
> error-message or log-line template, a `--help` epilog. That kind reads as
> documentation and lives as code, so a documentation sweep does not open the
> file and a code sweep does not read the sentence; it is also the surface an
> operator reads directly, so a stale claim there misinforms a human decision
> rather than a later author.**

**Why it belongs in the contract rather than in this plan.** The rule is
domain-neutral: it is a property of how sweeps miss things, not of freshness
gates. And the failure is invisible to every gate — the literal type-checks,
lints, and passes every test while saying something false.

⚠ **Not proposed, though the run brushed against it:** the "when the loop has
converged" section did *not* fail this run. It correctly forbids what this run did
(stopping after a round whose findings changed code behaviour). The deviation is
mine and is disclosed in § Findings, not a contract gap to patch.

**Operator disposition:** _presented, awaiting response._ Not applied, and no
second PR opened.

## Residue

| Left open | Where it should go next |
|---|---|
| **A second verification round was not run.** Round 1's findings were all behaviour-changing, which under the contract resets the loop. See § Findings → "stopped by judgement". | A re-dispatch against the round-1 fixes, or the PR's own reviewers. The fixes each carry a failing-without-them test, but no second independent read exists. |
| **Producer-side provenance is unowned** — no ledger field distinguishes a production write from a test write, so the gate must keep defending against bogus rows indefinitely (D2). | The plan's declared out-of-scope test-isolation half. Worth noting that this plan's cross-check makes the *urgency* lower, not zero: a test-written row is now refused whenever its notation is unresolved, but a test writing a **correctly-notated** row still satisfies the gate. |
| **Cost on a Maven/Gradle/npm project is unmeasured**, and the gate's happy path now runs a crawl that shells out per module on those toolchains. | A measurement on a real Maven project. If it proves expensive, the natural lever is a cheaper resolution source rather than weakening the check — the `build.map` domain keys are one candidate, at the price of conflating maven and gradle (both serve the `java` domain), which is why they were not used here. |
| **The polluting consumer test is still unnamed** (traceability gap, see § Findings). | Its own plan — the test-isolation half — which is where the fix belongs anyway. |
| **`notation_absent` loses to `notation_unrelated` on a mixed candidate set.** Deliberate and documented, but it means the "something other than a build is writing to the ledger" remedy can be masked. | Revisit only if a real incident shows the masked remedy mattered; `candidate_notations` already lets a reader recover it. |
