envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=finding
created=2026-08-29T23:39:06Z

# Carried-forward findings from PLAN-CIS-051 (detector-and-auditor-integrity)

Four findings surfaced during execution that sit outside this plan's declared
Expected Surface. They are recorded here for the orchestrator to stage; this plan
does not stage plans.

All four are the epic's own theme — a signal that reads as an evaluation which
never happened — so each is a candidate deliverable rather than a stray defect.

## 1. `3e7381` — `pre-commit-verify-freshness` is canonical-blind (bug, error)

**Component:** `plan-marshall:manage-tasks`

Observed live at `worktree_sha 0b31f4466ee1dfd0f6f6159a75345c9dbda0ef73e2300eeb151ebacf77f36e61`.
A `module-tests plan-marshall` run against that exact tree returned
`status: timeout` / `exit_code: -1` after 722s, producing **no suite verdict**.
`pre-commit-verify-freshness` nonetheless reported `status: fresh`, matching the
**test-compile** success row from the same sha, and stated *"Gate permitted on
corroborated evidence"*.

The gate filters on `kind`, `status` and `worktree_sha`, then cross-checks the
row's notation. Every pyproject canonical shares one notation
(`plan-marshall:build-pyproject:pyproject_build`), so a compile-only run
satisfies a gate a reader takes as "this tree was verified end to end".

This is the epic's theme sitting in the gate that guards the 5→6 transition, and
it is the gate this very plan relied on. Severity is `error`: it can admit an
unverified tree to finalize.

**Candidate remedy:** record the canonical command on the `kind=build` ledger row
and require a row whose canonical actually exercises tests — or publish which
canonical corroborated the verdict so the caller can judge.

## 2. `00d481` — footprint sites 2 and 4 emit a bare count with no resolution basis (improvement, warning)

**Component:** `plan-marshall:audit-archived-plan-retrospectives`

PLAN-CIS-051 routed all five footprint consumers through the tier order and that
fix is confirmed correct at every site. Two still publish a count without the
discriminator that makes it readable: `check_execution_manifest` emits
`'modified': inputs.realized_footprint_count`, and `_collect_token_economics_rows`
emits `'files': graded_file_count(inputs)` feeding `tokens_per_file`. In both, a
`0` is produced **both** by a tier that resolved and named no path **and** by no
tier resolving at all, and the emitted row cannot tell them apart.

Site 3 was given a `count_basis` column plus a `basis=` segment in its mismatch
string. Sites 2 and 4 were deliberately **not** widened: site 2's discriminator
shape differs (it never falls back to declared, so its basis is `footprint_tier`
itself, not `graded_count_basis`), and extending a committed deliverable's emitted
surface across two further check documents
(`checks/execution-context-manifest.md`, `checks/token-economics.md`) is a scope
decision for the gate, not for a leaf. No gate currently fails on this.

## 3. `b234fd` — PROPOSAL: producerless `SECTION_SPEC` row `_executive-summary` (improvement, info)

**Component:** `plan-marshall:plan-retrospective`

⛔ **Recorded, not decided.** `SECTION_SPEC` and `report-structure.md` are
unchanged — confirmed by diff, twice, independently.

A content sweep for `_executive-summary` returns 18 hits across 9 files —
consumer, registry, spec and 6 test modules — and **no producer**.
`collect-fragments.py` structurally refuses underscore-prefixed aspect keys, so
`report-structure.md` item 1, which specifies a mandatory 3–5 sentence synthesis,
has never been produced by any retrospective this system has compiled.

- **Option A:** add a producer (an LLM synthesis step writing the fragment before
  compile). Restores the specified headline, but adds an LLM-authored surface to a
  compiler documented as a pure assembler.
- **Option B:** delete the row and its `report-structure.md` entry. Keeps the
  assembler pure and removes a spec requirement nothing satisfies.

**Recommendation: Option B** — the documented compiler boundary (assembler only)
is the stronger invariant and Option A forks it; the synthesis, if wanted, belongs
in the fragment-producing LLM pass that already exists. Either option must also
resolve the mandatory-content requirement in `report-structure.md`.

## 4. `08a140` — PROPOSAL: producerless `SECTION_SPEC` row `dispatch_boundaries` (improvement, info)

**Component:** `plan-marshall:plan-retrospective`

⛔ **Recorded, not decided.** `SECTION_SPEC` unchanged.

A content sweep for `dispatch_boundaries` returns 38 hits across 19 files. The
only producer is `analyze-logs.py`, which writes it **nested** inside the
log-analysis fragment and never registers it as a top-level aspect. The dedicated
Phase Dispatch Boundaries section therefore lands in `sections_omitted` on every
run, while `render_dispatch_boundaries_body` stays live and correct. Nothing is
lost from the compiled document — the data renders inside Log Analysis — only the
dedicated per-phase table is absent.

- **Option A:** register `dispatch_boundaries` as a top-level aspect so the
  dedicated table renders, at the cost of publishing the same data twice.
- **Option B:** delete the row and `report-structure.md` item 6.

**Recommendation: Option A** — the per-phase table is the only place the
terminal-error versus retryable dispatch-spend split is presented as a table, and
the duplication is bounded to one fragment.

## Additional observations (no finding filed, worth staging)

These were established by measurement during the run and are recorded so the
orchestrator can decide whether any deserves a deliverable.

- **The `_load_module` conftest blind spot is systemic.** The loader-collision
  guard bounds statically-unresolvable call sites at 90; the wrapper is used in
  **97 files**. `test_resolve_dependencies.py` still hides a real `_dep_detection`
  collision the guard cannot see. This plan reduced the blind spot by three
  registrations rather than raising the bound, but the structural gap remains.
- **`scope_creep_check` was inert for this entire plan.** It returns
  `could_not_look` / `no_baseline_sha` on every call because `references.json`
  carries no `plan_creation_sha`. It correctly withheld a false zero, but no
  scope-creep guard ran at any point.
- **`finalize-step` closes a task before its verification runs.** On the last
  step it marks the task `done`, which auto-closed tasks 11 and 12 while their
  `module-tests` gate was unrun. The module_testing profile forbids exactly that,
  so the seam and the profile disagree.
- **Plan-time `execution_tier` stamps are stale.** `module-tests plan-marshall`
  was stamped `per_task` 471s but live-resolves `orchestrator` 633s;
  `module-tests pm-plugin-development` stamped `per_task` 360s, live 755s;
  `verify` stamped 736s, live 1657s. Every leaf hit the ceiling before the live
  resolve corrected it.
- **`manage-solution-outline` parses only one `Command:`/`Criteria:` pair per
  deliverable.** A cross-module deliverable can therefore only structurally
  declare half its verification; the second command had to be written into the
  criteria prose to reach phase-4 at all.
- **`.claude/**` is outside the architecture inventory**, contradicting
  `CLAUDE.md`'s allowlist. `architecture find` returns `count: 0` on the auditor's
  `checks/` directory while sibling `test/` paths return 148 rows;
  `manage-lessons consult` independently reports the same paths under
  `unmapped_paths[25]`. A `search --content` zero there is a coverage boundary,
  never a clean negative.
- **`manage-tasks` has no verb to retarget a step.** `update-step` changes intent
  only, so a step whose declared target turns out to be the wrong file can only be
  recorded as diverged, never corrected.
- **Declared write sets under-reported on three consecutive deliverables** — D3
  7→11, D4 10→13, D5 8→12 — each caught only after a test in an undeclared file
  failed.
