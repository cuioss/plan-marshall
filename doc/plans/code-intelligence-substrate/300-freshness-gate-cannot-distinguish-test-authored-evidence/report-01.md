# Run report — 300-freshness-gate-cannot-distinguish-test-authored-evidence (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/freshness-gate-test-evidence-bvhf95`    **PR:** _pending_    **Outcome:** _in progress_

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

New file `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py`
(13 tests), plus a pinned resolver fixture and a corrected contract docstring in
the existing `test_pre_commit_verify_freshness.py`.

| Plan demand | Test |
|---|---|
| (a) unrelated-notation-only evidence behaves per D1's direction | `test_unrelated_notation_is_refused` |
| (a) **and silently passes against pre-fix code** | Recorded below — the pre-fix observation |
| (b) a legitimate multi-notation plan still passes | `test_multi_notation_project_still_passes`, `test_related_row_behind_an_unrelated_one_still_passes` |
| (c) the decision record contains the matched notation | `test_fresh_record_names_the_matched_row` |
| Verification § structural-stale remains STALE | `test_mutated_worktree_stays_stale_with_its_own_reason`, `test_failed_build_for_current_sha_keeps_its_build_status_reason` |

Also pinned: the `notation_absent` route, an all-candidates-unrelated refusal, the
`unverified` pass, the parsed-vs-physical index, and the resolver's own three
outcomes (non-empty set / empty-as-inability / raise-as-inability).

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
row → `fresh` / `corroborated`. First-crawl cost **3.95 s** (measured once, this
repository, this session) — paid at most once per pre-commit transition, and only
on the path where the primary predicate already matched.

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
- `./pw verify` (after the fixes) — **green: 20476 passed, 14 skipped** in
  6 m 12 s, all three sub-steps (quality-gate, test-compile, module-tests).

The working tree was clean (`git status --porcelain` empty) at the start of the
run and before each diff-derived read, so no uncommitted file was invisible to
either gate.

## Findings

_(filled in below as each source reports)_

## Reviewer participation

_(pending PR)_

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

_(filled in at Step 8 condition 3)_

## What have we learned (Step 9)

_(filled in at Step 8 condition 3)_

## Residue

_(filled in at Step 8 condition 3)_
