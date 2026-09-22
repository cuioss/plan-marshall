# Epic: test-quality — house style and reduction of the Python test corpus

slug: test-quality

> Ledger document for one epic under `.plan/orchestrator/test-quality/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Bring the repository's ~770-module, ~377,000-line Python test corpus under a stated, enforced house
style (rules **B1**–**B10**) and shrink it **without losing a single assertion**. The epic is too
large for one plan because the corpus partitions into six disjoint reduction slices, each of which
needs its own run, plus a standards plan, a harness plan, a production-gap plan, and a module-budget
campaign that spans all six slices one run at a time. Done at the epic level means: the house style is
written into the owning skills and enforced by `plugin-doctor`'s `test-conventions` scope; every slice
has been through a reduction run; the 400-line module budget (**B1**) is driven to zero honestly; the
suite reports zero unexplained skips and no wall-clock regression; and the epic's own cross-file sets
(partition, collision matrix, per-slice attribution) are **derived and checked** rather than held in
prose.

**This epic was ingested from `doc/plans/test-quality/`**, a standalone `doc/plans/` cloud-lane epic
that ran ten plans to completion outside the orchestrator. The version-controlled directory is now
empty; every plan document, every run report, and the epic's scoping brief live under this tree. See
`## Provenance` below.

## Run Conditions 3 and 4 — the commands

Every reduction run holds the **five conditions** stated in `archive/README.md` § "What a reduction
run must hold". Four of them always carried a command; conditions **3 (skipped count)** and **4
(wall-clock)** did not, which is why two runs could produce figures that were not comparable.

⛔ **PLAN-110 (#1426, landed 2026-09-06) built the instruments, and this section supersedes the brief's
"Until it lands, a run states the two figures and names how it took them."** Both conditions now ride
the ONE canonical invocation — no wrapper change, no new flag, no pytest-args passthrough:

```text
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests"
```

- **Condition 3 — how many tests did not run, and which.** Read the `SKIPPED` short-summary block. An
  empty block means every test ran. Every entry must be on the residual skippable set
  (`_SKIP_EXCEPTIONS` in `test/conftest.py`); the session-finish gate is **always on** and fails the run
  on any skip that is not listed, or on a listed nodeid skipping for a *different cause*. The set's size
  prints in the session header: `residual skippable set: 11 nodeid(s) permitted to skip`.
- **Condition 4 — how long, and where it went.** Same command. Read the `--durations=25` table for
  per-test attribution and the trailing total for suite wall-clock.

⛔ **The mechanism is `-rsfE` in `[tool.pytest.ini_options].addopts`, never a bare `-rs`.** `-r` is a
*store* option, not an accumulating one, so a later `-rs` REPLACES pytest's `fE` default and drops the
`FAILED <path>::<test>` short-summary lines. `build-pyproject`'s `_PYTEST_FAILED_PATTERN` parses those
lines to file per-test `test-failure` findings, so weakening the flag would collapse a failing build
into one synthetic `build_failure` row and take the whole per-test triage surface with it.

⚠️ **The epic's long-carried baseline of `14 skipped` is stale and must not be used.** It appears in the
landed reports of plans 010–100, from `20066 passed, 14 skipped` to `21334 passed, 14 skipped`, and
PLAN-110's own spec carried it as the hypothesis gating D1. The live figure at PLAN-110's start was
**11**, and 11 after. Whether the three vanished through drift or because those reports measured
`./pw verify` while this command measures `module-tests` is **not settled** — do not assert either.
Re-derive before using. See [`landings/PLAN-110.md`](landings/PLAN-110.md).

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug test-quality
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: PLAN-181 landed and reconciled (analyze 2026-09-22): shipped as #1582 (merge 1a9a672), landing complete:true, emit gate override vindicated (all 47 overlap rows inert); watch added on ruff-format unenforcement (WS-03 candidate). Next: operator disposition on PLAN-140 (parked; claims 1/2 re-scope owed - park accepted or resume), then carve 3 (tools-permission-doctor) staged on operator order. Open carried: 7 settled.md dangling landings refs; operator commit-scope decision on 103 uncommitted paths (5 epic-own).
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 136 archived
**Parked**:
- PLAN-140 (WS-04) — PR #1552
**Queue** (staged, in order):
- (empty)
- PLAN-181 (WS-04) — plan=run-3-carve-2-tools-permission-fix — PR #1582 — landing=landings/PLAN-181.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. This is what makes the block above genuinely regenerable: the
     per-row notes the generator cannot produce (why a row is parked, what a running
     plan is waiting on, an operator caveat on a queue entry) have a home that a
     verbatim paste does not destroy. -->

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug test-quality (paste it verbatim after a queue change),
     and rewritten in place by the compact stage (orchestrator.py compact --slug test-quality) at
     cleanup. Only the LIVE queue is rendered here — a shipped/landed row belongs in its
     landing record, not in the live queue. Per-row notes a reader wants to ADD go in the
     annotation zone below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-140 | WS-04 | parked | test/default/; test/finalize-step-deploy-target/; test/finalize-step-sync-plugin-cache/; test/marketplace/; test/plan-marshall/; test/pm-code-intelligence/; test/pm-dev-frontend-cui/; test/pm-dev-frontend/; test/pm-dev-java-cui/; test/pm-dev-java/; test/pm-dev-oci/; test/pm-dev-python/; test/pm-documents/; test/pm-plugin-development/; test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py; test/sync-plugin-cache/ |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers.
      A regeneration replaces only the table BETWEEN the markers, so everything written here
survives it. This is where the per-row narrative the generator cannot derive lives — a
sequencing caveat, a disjointness note, why a row is parked — keyed by plan id. -->

- **PLAN-181 EMITTED as `launched` (operator order, 2026-09-22).** Recorded gate
  override: strict disjointness conjuncts fail — 47 `file_overlap_matches[]` rows
  (46 containment false-positives from sibling broad `test/plan-marshall/`
  directory declarations across active AND archived epics; the one exact-file
  match `truthful-signals-26-09-21/PLAN-TRUTH-103`, overlap 2 = both carve-2
  files, is archived residue absent from the live queue post-restructure) and
  `candidate_comparison_determinate: false` (corpus-wide sibling
  declaration-completeness gap, not actionable from here). Disposition basis is
  the A4 pass of the 2026-09-22 cleanup — no live plan claims these files — plus
  the operator's explicit word, same precedent as the PLAN-140 run 3 and PLAN-165
  overrides. N=1, R=0 at emit (PLAN-140 parked; spec's stale "RUNNING owns these
  files" note superseded by the yield). `auto_emit=false`, so `launched` is
  operator-confirmed; the row awaits the operator's start (`launched → running`).
  Emit block carries the standing process-compliance trailer.
- **Transfer-in 2026-09-19 (operator direction): PLAN-180-test-fidelity-rules (WS-01,
  staged).** Nine test-fidelity lessons from the quality-aspect full-corpus ingestion
  (G19 tester fidelity + G29 pytest mirrors + TestFindSkillsRoot + script
  registration + basetemp). Fits WS-01 scope verbatim (pytest-testing +
  persona-module-tester). Sequence after PLAN-177 lands (adjacent plugin-doctor/test
  surfaces). Carries the epic's `## Execution Contract` section.
- **Relocated-lesson pointers (same transfer).** This ledger's "stay in the corpus"
  entries now resolve at `.plan/orchestrator/quality-aspect/lessons-archive/`:
  `2026-09-02-14-003` + `2026-09-09-01-001` (lessons-sweep 2026-09-17 entry),
  `2026-09-08-13-001`…`-011` and the PLAN-155-landing five (`2026-09-08-21-001`,
  `2026-09-08-22-002`, `2026-09-09-01-001/002/003`). Corpus holds only the
  superseded `2026-09-05-14-002` stub. Per-lesson plan homes are in
  quality-aspect's `lessons-disposition.md`.

**Residue disposition (operator decision, 2026-09-17): PLAN-140 stays focused on runs
2–7 — no bulk fold.** The open residue is disposed as: (1) warning→error flip and the
PR-carving rule are run-level operator instructions, decided at dispatch, not spec
deliverables; (2) harness-scope tail and stage-on-demand residue stay where they are;
(3) declaration-form stays a ledger-narrative question. Rationale: split guard (six
runs × D1–D5 already), WS-04 charter mismatch for rule-fix/harness work, and the
DERIVED-surface honesty rule. Applies to PLAN-140 keyed below.

**Standing rule (operator instruction, 2026-09-17): every staged spec in this epic
carries a `## Execution Contract` section** — process compliance mandatory, phased
lifecycle via managing skills, spec as binding brief, verify-first against implementing
source, Write-Boundary honored, report via PR + inbox. Applied to PLAN-140; apply to
every subsequently staged `plans/PLAN-NN-*.md` at stage time.

**Standing rule (operator instruction, 2026-09-18): every emitted
`/plan-marshall` command carries the trailer** — `Comply strictly to the process
rules. All issues with the process rules, file into
`.plan/orchestrator/process-compliance/inbox`` (verified present). Applies to
all commands emitted from this point forward, including the re-emit of any
already-emitted but unlaunched plan.

**Standing rules (run-3 handoff, 2026-09-21):** Tier M mechanical PRs ship with
label `skip-bot-review` (quota saved), Tier J cluster PRs keep review by
default — the label never waives gates. Every PR is checked for Sourcery
comments; each arrived comment triaged/handled before merge. Two-tier review:
Tier M gated on 5 machine facts (fidelity lost=0, duplication + banner
introduced=0, pytest green default+reverse, doctor error-0, rename-only diff),
Tier J reviews cluster boundaries only. D5 logs per PR: label y/n, CodeRabbit
skipped y/n, Sourcery present y/n + dispositions.

**Gate override (operator decision, 2026-09-20): PLAN-140 run 3 emitted despite
indeterminate surface.** Same terms as the 2026-09-17 override: N=1 sequential,
flight line empty (0 launched/running), prep-ready 8/8 admitting — no live
collision possible by construction. Residual risks: unchecked vs
live/unorchestrated plans; slice figures stale (HEAD now `1e2aa916a`, many
`test/` commits since `fb8aadc9c`), D1 re-derives at dispatch per claim 0's
standing instruction. `launched` stays operator-confirmed (`auto_emit=false`).

**Gate override (operator decision, 2026-09-17): PLAN-140 run 2 emitted despite
indeterminate surface.** Evidence: N=1 sequential, flight line empty (0
launched/running), prep-ready 8/8 admitting — no intra-epic collision possible by
construction. Residual risks: unchecked vs live/unorchestrated plans; slice figures
stale (12 `test/` commits since `fb8aadc9c`), D1 re-derives at dispatch. `launched`
stays operator-confirmed (`auto_emit=false`).

⛔⛔ **PLAN-110 HAS LANDED AND THIS LEDGER STILL SAYS `staged`.** Observed 2026-09-06 while running
`cleanup` on `operator-ux`; **not reconciled here**, because a landing belongs to this epic's own
`analyze`. PR **#1426**, squash `1c4e6febb`, *"test: zero out skipped tests and give run conditions
a command"* — the subject matches PLAN-110's D1 exactly. Realized surface 29 files: `test/conftest.py`
(+403), `test/README.md`, a new `test/test_skip_gate.py` (266), `pyproject.toml`, three
`script-shared/scripts/build/` modules, and test modules across `lsp-client`, `platform-runtime`,
`script-shared`, `marketplace/targets`, `pm-plugin-development`, `sync-opencode` and
`sync-plugin-cache`. **Next action: `/plan-orchestrator analyze slug=test-quality`.**
⚠ It also lands the pre-launch warning below as moot for PLAN-110 itself, but **not** for PLAN-165 —
and it creates fresh re-grounding debt for PLAN-130, PLAN-135, PLAN-155 and PLAN-160, several of
whose declared directories are among the 29. Re-derive at that drain rather than trusting the
matcher.

⛔ **PLAN-110 and PLAN-165 were moved under on 2026-09-05, after PLAN-110 was emitted and while it
awaited launch.** An unorchestrated plan — `unreviewed-merge-gate-holes`, PR #1409, squash
`66320e70d` — modified `test/plan-marshall/workflow-integration-github/test_github_pr.py`
(+72/−, verified from the merge commit's file list). That path is inside **PLAN-110's** declared
`test/plan-marshall/workflow-integration-github/` and inside **PLAN-165's** declaration of the same
directory. PLAN-110's re-grounding was done at `bf1b7ed6`; HEAD is now `c3d69f52a`, so the emitted
brief describes a file that has changed under it. **Re-ground that directory before the launch is
confirmed**, not after. PLAN-165 is further out but carries the same debt.

⚠️ **The gate could not have caught it, and that is the point.** `corpus cross-check` compares this
epic's specs against *sibling epics and live orchestrated plans*. A plan the operator runs directly
has no ledger row in any epic, so it is outside the population the check walks — its surface is
invisible by construction, not by a matcher bug. This is a **different** blindness from the
containment defect the epic already tracks: containment is a matcher that looks and mis-answers;
this is a population that is never enumerated. Both return a clean zero. Five other realized paths
from the same PR sit inside PLAN-130's, PLAN-135's and PLAN-160's root-level `test/` claims;
PLAN-155's declaration is genuinely disjoint from all 19.

**Emission order.** The queue renders in `plans[]` order; the order to actually *run* them is
below. ⛔ **Rewritten at the 2026-09-03 cleanup** — the previous list sequenced PLAN-120, PLAN-150
and PLAN-170 as pending work and carried a PLAN-145 → PLAN-150 dependency that was retired at the
drain. All three have shipped.

✅ **PLAN-105 SHIPPED (#1407, `bf1b7ed6`), so the campaign's blocker is cleared.** Its D3 widened the
budget metric and its D4 committed the three instruments, which is exactly the precondition
**PLAN-140**'s campaign runs were waiting on — a campaign run now reads committed instruments instead
of re-deriving them from prose, which is how run 1 shipped four false figures. **Nothing is running.**
⚠️ Every staged spec's counts are stale against `bf1b7ed6`: it moved 521 files, 3,707 insertions and
2,466 deletions, including the budget rule's own definition. **Re-ground before emitting anything** —
the next `cleanup` owes a pass over the whole corpus, not just the four specs PLAN-145 touched.
2. **PLAN-110** — before the campaign continues. The campaign is what it exists to watch.
3. **PLAN-130** → **PLAN-135** — strictly in that order, never together.
4. **PLAN-155**, **PLAN-140** (one run per emission), **PLAN-160**, **PLAN-165**.

**PLAN-145 SHIPPED as #1395 (merged `8d8c17bd`) — this note is kept as the record of how it got
there, because the path it took bypassed every admission gate.** It ran `parked` → `running` →
`shipped` inside one day, and the row spent most of that time reading `parked`. The park was
conditional by construction: the
recorded disposition was *"resume PLAN-145 for its one remaining additive deliverable (a tree-wide
seam-coverage guard), or retire it — an operator decision"*, and PR **#1395** is titled *"test:
publish a tree-wide parser-seam coverage guard"*, which is that deliverable verbatim. So this is
the park resolving as designed, **not** a bypass of it. Ground truth at the analyze: `6-finalize`,
PR #1395 **open** (`ci pr view`: state `open`, `review_decision: none`, not merged), CI green,
`automatic-review` in **loop-back iteration 2**; the last three finalize steps done are `create-pr`
(#1395), `era-stamp-fill` (no sentinel) and `ci-verify` (all checks green). ⚠️ **The `contradicted /
rescoped: no` stamp on its claim still stands** — the refutation was never absorbed into the spec,
deliberately, because the outline was already consumed. The stamp therefore no longer gates
anything: the plan is executing past the prep-ready test the stamp exists to feed. Its former role —
unblocking PLAN-150 — remains **retired**: PLAN-150's D1 proved the blocked set empty (0 sites owed
a seam) and shipped without it.

⛔ **The "PLAN-165 is the epic's best filler" note is withdrawn.** It rested on PLAN-165 admitting
the disjointness check, and the cleanup's A1 pass found it does not: `corpus surfaces` reports
`admits_disjointness_check: true` for it while the shipped `epic-surface-partition classify`
reports `false`. Until the two readers agree, PLAN-165 is a *sequenced* candidate, not a filler.

**Disjointness notes the generator cannot derive:**

- ⛔⛔ **TWO READERS DISAGREE, and the disjointness gate reads the one that has not been updated.**
  For **PLAN-155, PLAN-160 and PLAN-165**, `corpus surfaces` — the reader `orchestrate.md` Step 4
  decides on — returns `admits_disjointness_check: true`, while `epic-surface-partition classify`,
  which applies the claim/lead model PLAN-170 shipped, returns `false`. PLAN-110, PLAN-130,
  PLAN-135 and PLAN-140 agree between the two. Under ADR-019 the correct shortfall reason for those
  three is **"surface indeterminate — no comparable path declared"**, not an overlap reason.
  *Verified at HEAD `6884e9329`; the executor resolves `script-shared` to cache `0.1.1586`, byte-identical
  to the repo copy, so this is a genuine disagreement and not a stale-cache artifact.*
- ⛔ **PLAN-160's three `test/**` entries are LEADS, not claims — the earlier note to the contrary is
  withdrawn.** They are authored as `HYPOTHESIS: … (verify-at-outline)`, and the shipped
  `epic-surface-derivation.md` entry-class table makes a deferred hypothesis a lead. `classify`
  returns `shape: lead` for all three. **PLAN-160's spec is correctly authored and owes no surface
  correction**; three prior rounds recorded it as unpairable on the strength of the stale reader.
- ⛔ **`corpus cross-check` still compares normalized paths EXACTLY, so a directory or glob claim
  matches only an identical literal.** PLAN-170 fixed the *partition*, not the *gate* — its own
  residue says so, and lesson `2026-08-25-09-016` was re-examined during that run and deliberately
  **retained**. Absence from `file_overlap_matches[]` is therefore an **unchecked negative**, never a
  checked one. A pairing decision must still be made by reading the two specs' Expected Surfaces
  directly.
- **PLAN-105 claims BOTH trees at root** (`test/` and `marketplace/bundles/`), so while it runs
  nothing can pair with it. The free slot under `parallelization_scope: 2` stays free by
  construction, not by shortfall.
- **PLAN-130 and PLAN-135 each declare `test/` entire.** Neither pairs with any other `test/`-editing
  plan; both are sequenced.
- **The live contested set is 11**, not the 186 the derivation currently reports:
  PLAN-155 + PLAN-165 (10 modules under `test/plan-marshall/manage-providers/`) and
  PLAN-155 + PLAN-160 (1, `test_conftest_loader_contract.py`). The other 175 are
  terminal-vs-terminal artifacts — see the Open Defect.
- **Every overlap the cross-check reports against a landed or shipped spec is inert.** Only
  live-vs-live pairs constrain emission.
- ⛔ **Two sibling-epic plans are live and invisible to this queue:** `always-on-is-not-a-resolve`
  and `output-volume-standard`, both `operator-ux`. Read their surfaces from their `references.json`
  `affected_files` at the next pairing decision.

## Provenance

This epic was ingested from the git-tracked `doc/plans/test-quality/` tree. The relocation was verbatim —
nothing was rewritten on the way in.

⛔ **`doc/plans/` no longer exists at all.** The whole tree — its README, `cloud-bridge.md` and the plan
template — was retired at commit `3bc01075` once both standalone epics had been ingested. The
`cloud-plan-lane` and `author-cloud-plan` skills are kept, with the accepted consequence that the lane
can no longer author a plan; recover any of the three files from history if needed. **Every source path
in the table below is therefore historical**, and resolves only through `git show`.

| Source | Now at |
|---|---|
| `doc/plans/test-quality/README.md` | `archive/README.md` — the epic's scoping brief and the source of `## Vision` above |
| `doc/plans/test-quality/findings-test-corpus-review.md` | `archive/findings-test-corpus-review.md` — the corpus review the epic was scoped from |
| `doc/plans/test-quality/report-authoring-0{1,2}.md` | `archive/report-authoring-0{1,2}.md` — the epic re-scoping runs' own reports |
| `doc/plans/test-quality/{010..100}-*/plan.md` + `report-*.md` | `archive/{010..100}-*/` — the ten executed plans, verbatim |
| `doc/plans/test-quality/1{05,10,20}-*.md` | `archive/` (verbatim) **and** restaged as `plans/PLAN-1{05,10,20}-*.md` orchestrator specs |

**The `archive/` tree is the audit record and is never edited.** A landed plan's authoritative
per-deliverable verdict is its `landings/PLAN-NNN.md` record, written by this orchestrator from a
ground-truth check against HEAD — not the run's own report, which is a claim.

**The scoping brief is superseded where it disagrees with a landing record.** `archive/README.md`
carries figures taken at various points across the epic's execution; every one is a lead. Where it and
a `landings/` record disagree, the landing record governs, because it was re-derived at a stated HEAD.

## Decisions

{One entry per recorded decision — append-only, newest last. This section is a curated
human-facing VIEW; the authoritative append-only record is `logs/decision.log`, written via
`manage-logging --store orchestrator` (decision verb). Because entries carry rationale and
alternatives the log summary need not, this section is NARRATIVE — the compact stage preserves
it verbatim and never regenerates it.}

- **Ingest the standalone epic into this ledger.** The `doc/plans/test-quality/` tree ran ten plans to
  completion in the cloud lane and outgrew it: twenty plans across six workstreams with a dense collision
  graph needs a queue, a disjointness check and landing analysis the standalone lane does not have. The
  tree is absorbed and removed from version control; nothing is lost. Precedent: the `multiplattform`
  epic was ingested the same way at `ec26306e`.
- **`parallelization_scope` = 2**, overriding the project default of 1. Most open pairs are ineligible
  anyway — PLAN-130 and PLAN-135 each declare `test/` entire — so the second slot is filled only on a
  confirmed-disjoint pair. Alternatives: 1 (rejected, forgoes the genuinely disjoint
  production-plus-test pairing) and 3 (rejected, a third slot would go unfilled and raise rebase risk).
- **Landed plans keep a spec in `plans/`, not only a landing record.** A spec is the audit record of what
  was briefed; deleting one on landing would break `queue_spec_bidirectional` and lose the brief. The
  landing record carries the verdict; the spec carries the brief. Ten historical specs were reconstructed
  from the archived originals for this reason.
- **PLAN-120 re-scoped to partition-coverage plus budget attribution.** The ingestion destroyed its
  premise: it parsed `doc/plans/test-quality/` documents and gated CI on their disagreement, and those
  documents are now git-ignored ledger files no build can read. Two of its three sets are now provided
  structurally — `corpus cross-check` derives the collision matrix from each spec's Expected Surface, and
  the Ordered Queue is a generated block. **What survives uniquely is walking `test/` for entries no spec
  claims** (the defect that halted four consecutive runs) and the per-slice budget attribution.
  Alternatives: retire it entirely (rejected — gives up the four-run defect check) and keep it broadly
  re-pointed at the ledger (rejected — a second implementation of `corpus enumerate`/`cross-check`, which
  the cleanup contract forbids).
- **PLAN-105 proceeds unsplit at seven deliverables**, above the ~6 presumptive threshold. D2, D4 and D5
  are mutually dependent — D2's fidelity proof needs D4's differ and D5's figure is meaningless without
  it — so a split would build the instrument in one plan and first use it in another, with nothing
  exercising it in between. The plan carries an explicit stop-after-migration landing point for D7.
- **PLAN-145 split at cleanup; PLAN-110 proceeds unsplit.** The split guard flagged three specs.
  **PLAN-145 (6) was split** — its D4/D5 were a circular import and a coverage gap that shared its tree and
  nothing else, and bundling them delayed the parser seams PLAN-150 is blocked on; they are now
  **PLAN-165**, and PLAN-145 is 4 deliverables that unblock PLAN-150 sooner. **PLAN-110 (7) was not**:
  its D2–D5 each act on one class of D1's gating classification, so splitting would put the derivation in
  one plan and its four consumers in others, and every consumer would re-derive it — which is precisely
  how this epic's partition came to be re-derived four times with four different dispositions. PLAN-110
  instead carries an explicit stop-after-D5 landing point.
- **PLAN-105 § D6 retired at cleanup — its population no longer exists.** D6 swept for *live
  instructions* naming a deleted test module. Both halves are gone: the `doc/plans/` half went with the
  tree at `3bc01075`, and the `phase-4-plan/SKILL.md` specimens turn out to be worked examples in a
  naming-convention table (six of eight cited names do not resolve, and correctly so) — the
  deliberate-citation class D6's own rule says to leave alone. **Retired in place with the reasoning,
  not deleted**, so a reader who finds D6 in the archived original learns why it is absent. PLAN-105
  drops from 7 live deliverables to 6, which puts it at the split threshold rather than above it.
- **The stale-reference fix in `doc/plans/README.md` and `cloud-bridge.md` rides the ingestion commit.**
  A recorded, bounded exception to the prime directive: the broken relative link is created by the
  removal in that same commit, so leaving it ships a defect this session caused. Scope is prose only, no
  code. Alternatives: a separate plan (rejected — leaves a broken link on `main` until it runs) and
  record-only (rejected — leaves it indefinitely).

- **Archive citations in the staged specs are absolutized.** Twelve `archive/...` citations across eight
  staged specs were written ledger-relative, resolvable only from `plans/`. An emitted plan runs from a
  worktree, so each was a self-sufficiency defect inherited from the ingestion: the cited evidence is the
  archived cloud-lane briefs and run reports, and the spec is contractually the plan's only brief. All
  twelve now carry the full `.plan/orchestrator/test-quality/archive/...` path and every one was
  verified to resolve. Markdown links already pointing at `../archive/` were left alone — they resolve
  correctly for a reader of the spec file and are provenance pointers, not read-this instructions.

- **PLAN-160's R4 population was overstated, and re-grounding caught it.** The ingestion claim read
  `grep -rln` output as "two sites beyond PLAN-090's fix". At HEAD the two hits are one genuine call site
  (`manage-tasks/test_freshness_notation_crosscheck.py:186`) and **one docstring inside PLAN-090's own
  fix** quoting the shape to explain it. The real unexamined delitem population is **one**. The volume is
  in the sibling shape the deliverable already named but never sized: `delenv(..., raising=False)` returns
  **62** lines, none examined. R4 re-scoped, and the miscount written into the deliverable as the reason a
  sweep must classify each match as call site or prose before counting it. Claim stamped `contradicted`.
- **PLAN-165's D1 rests on a premise that did not survive re-grounding.** It read as one accidental cycle
  to break. At HEAD it is a **uniform, documented pattern across three module pairs**: `github_ops.py`
  bottom-imports `_github_ci`, `_github_issue` and `_github_pr`, and all three import `github_ops` at
  module scope. The `_github_ci` and `_github_issue` preambles state why — every monkeypatch-sensitive
  primitive is reached by attribute access at call time, because `from github_ops import <name>` would
  defeat `monkeypatch.setattr(github_ops, ...)`. **PLAN-090's decline now reads as correct on the merits.**
  D1 re-scoped from *break it* to *adjudicate it*, closing by decision or by a three-pair fix, never by
  fixing one pair. Alternatives: retire D1 (rejected — the rationale is asserted in a docstring and has
  never been tested) and leave it as written (rejected — it directs a change that may be wrong and would
  break test interception silently).
- **All 21 verdicts re-stamped at HEAD `3bc01075`, reversing the previous pass's declination.** The basis
  is now real rather than assumed: the diff from the stamped `2cd1a19c` touches 61 files, 54 of them
  deletions under `doc/plans/`; **no file under `marketplace/bundles/` changed**, and the single changed
  `test/` file is 354→373 lines (under the 400 budget at both ends, zero `Namespace(`), so it enters none
  of the stamped populations. Eight claims were additionally re-derived directly. Diff-invariance proves
  the bytes did not move; it does not prove the original measurement was right — which is exactly what the
  two contradictions above show, so both instruments were needed.

- **PLAN-145's premise is refuted by its own D1, and PLAN-150 is NOT blocked.** PLAN-145 parked at its
  3-outline gate and filed the result through the inbox rather than waiting for a landing, which is the
  channel working as designed. D1's tree-wide sweep: of **118** entry-point scripts under
  `marketplace/bundles/`, **113** reach a parser seam and the **5** raising `ParserSeamNotFound` are all
  deliberate shapes — `platform_runtime.py` is a dispatch router whose raise is pinned as the *intended*
  contract by a passing test, three are stdin-driven hooks with no argv contract, and `plan_logging.py` is
  import-only. **Modules owed a `build_parser()` seam: 0. `parse_ns` sites unblocked: 0.** Corroborated
  independently at HEAD `09f92b5e`: `manage_terminal_title.py` carries zero argparse/`main()`/`build_parser`
  hits and `effort_presets.py`'s only two are **docstring mentions** at lines 379 and 381 — so both named
  starting points belong to D1's *no top-level CLI* class, not to `ParserSeamNotFound`. **Consequence: the
  sequencing constraint "PLAN-150 depends on PLAN-145" is void** — those seams block zero sites, and
  PLAN-150's D4 figure is `0`. PLAN-150 can be staged independently. ⛔ **The spec was deliberately NOT
  re-scoped**: the plan is parked with its outline already complete and Q-Gate-clean, so editing the brief
  now would change a document that has already been consumed. The disposition — resume PLAN-145 for its one
  remaining additive deliverable (a tree-wide seam-coverage guard, measured at 0.3 s over 113 scripts), or
  retire it — is an operator decision, and the refutation is stamped on the claim either way.

## Open Defects

{Known defects surfaced by landings or observations that are not yet owned by a staged
plan. When a defect is folded into a plan spec, move it out of this list and note the
owning PLAN-NNN.}

**All figures below were re-derived at HEAD `2cd1a19c` by five read-only sub-agents during ingestion.**

### Owned — folded into a staged spec

- **The rule-widening regression class.** PLAN-090 widened the prose rules; nothing swept `test/`
  afterwards, so PLAN-050's and PLAN-060's "zero findings" are false at HEAD (22 in one directory, 14
  across fourteen), PLAN-040's 92 disclosed citations were never remediated, and PLAN-030 declared its
  deliverable done having never measured the narration half (245 census hits). Whole-tree: **205** at HEAD `00b92fca`.
  → **PLAN-130**
> ↪ Relocated to `settled.md` § "The shipped-accessor gap" — closed by PLAN-135 (#1446, merge
> `b64db667`): `test-module-preamble-boilerplate` 103 → **13**, `subprocess-pythonpath` 17 → **5**,
> both re-derived by this analyze at the merge commit itself. The 13 is the derived structural floor
> (11 unreachable sites across 4 classes + 2 in `test/conftest.py`, never edited), not a residue.
> ↪ Relocated to `settled.md` § "Circular ownership on three preamble sites" — closed by PLAN-135:
> all three contradiction sites converted, and the `Path(__file__)` parent-chain shape is at **0**.
> ↪ Relocated to `settled.md` § "PLAN-090's narrower D1" — **retired by refutation** at PLAN-145's
> landing (#1395): the tree-wide sweep found 118 entry-point scripts, 113 reaching a seam and 5
> raising deliberately. **Modules owed a seam: 0.** Both named starting points — `effort_presets.py`
> and `manage_terminal_title.py` — belong to the *no top-level CLI* class, not to
> `ParserSeamNotFound`. The defect was real as a **gap in PLAN-090's derivation**; the seams it
> inferred were owed do not exist. The guard `test/test_parser_seam_coverage.py` re-derives this on
> every run, so it cannot silently regress.
- ⛔ **`github_ops` ↔ `_github_pr` circular import**, behind a bottom-of-file `E402` suppression.
  Confirmed present; PLAN-090 checked and declined it. → **PLAN-165**
- **`credentials.py` at 52.6% coverage** — the sole cause of PLAN-090's condition-2 shortfall. Could not
  be re-derived (no coverage artifact; a build is outside the orchestrator's boundary). → **PLAN-165**

  ⚠️ **Both arrows above were re-routed `PLAN-145` → `PLAN-165` at the 2026-09-04 landing.** These two
  left PLAN-145 at the cleanup split — the split note two sections down records it — and the arrows
  here were never updated, so for one cleanup cycle they pointed at a plan that no longer owned them.
  PLAN-165's declared surface (`credentials.py`, `github_ops.py`, `_github_pr.py`, `_github_ci.py`,
  `_github_issue.py`) confirms the ownership independently.
- ⛔ **R1, R3 and R4 are defect classes fixed at one instance each**, with no sweep. A two-minute check
  found **2 further R4 candidates**. → **PLAN-160**
> ↪ Relocated to `settled.md` § "PLAN-060's D4 parametrization families" — closed by PLAN-155
> (#1455, merge `9853a7aba`): 97 files across all fourteen slice directories, the cold read
> performed AND widened from a sample to a full sweep after the sample proved untrustworthy, and
> every collapsed family re-read after repair.
> ↪ Relocated to `settled.md` § "PLAN-070's unfinished B6 namespace conversion" — closed by PLAN-150 (#1383): hand-built `Namespace` 547 → 1, `parse_ns` 1 → 78, blocked sites 0.
> ↪ Relocated to `settled.md` § "The budget metric's helper-module blind spot" — closed by PLAN-105 § D3 (#1407): the rule now measures every module the test tree carries, helper included.
- **PLAN-050 § D3's per-directory fixture criterion is false in all ten directories**, silently retired by
  PLAN-100's per-source deviation. → **PLAN-140**, which states the retirement explicitly
> ↪ Relocated to `settled.md` § "The ci-wait dated-provenance violation" — closed by PLAN-130 § D7
> (#1436). The entry had been left in this Owned list pointing at § D3 for one cycle after the
> landing section recorded its retirement; the two are now reconciled.
- **`test_test_conventions_rule6.py` at 681 lines**, over by 281 — the module PLAN-010 split off to stay
  under the budget it was introducing, now flagged by its own rule. → **PLAN-140** run 7

> ↪ Relocated to `settled.md` § "The refuted partition residual" — the defect was refuted by PLAN-120's derivation and retired; the refutation is kept as the anti-rework record.
> ↪ Relocated to `settled.md` § "The single-bucket attribution defect" — closed by PLAN-170 (#1385): attribution 26 → 645 of 1075, unclaimed 0. Two of its premises were refuted and are recorded there, not carried forward.
- **The whole-tree budget population is 279 at HEAD `00b92fca`**, triply confirmed — doctor `rules_run`,
  an independent `git ls-tree` sweep, and the landed tool's own `attribution` all agree exactly. The
  trajectory is **267** (`2cd1a19c`) → **270** (`77db1a0d`) → **279** (`00b92fca`); the mid-flight **271**
  the plan reported is a fourth sample of the same moving population, not a contradiction. The +9 is
  attributable per instance and **none of it is PLAN-120's**: 7 modules from `91bbe747` (#1342), 1 from
  `dfabe3d8` (#1344), 1 from `1169fb5b` (#1343). Companion rules at HEAD:
  `test-module-preamble-boilerplate` **110**, `test-docstring-historical-prose` **205**,
  `subprocess-pythonpath` **15** (unmoved). → **PLAN-140** and **PLAN-135**, both re-scoped in place
> ↪ Relocated to `settled.md` § "Both ADR subjects from PLAN-120, dispositioned" — ADR-019 created (status Proposed); the second subject discarded on an operator decision. Both settled; the eight-instance case for ADR-019 is preserved there verbatim.

#### Added by PLAN-135's landing (#1446, 2026-09-08)

- ⛔ **The whole-tree `test-conventions` gate is still `status: fail`, and the pre-launch anchor
  predicted it would go green.** It does not. All **5** residual `subprocess-pythonpath` findings
  carry **error** severity and are the ONLY error-severity findings in the tree (verified 5 of 5 at
  `b64db667`); every other finding across all seven rules is a warning. The 5 are confirmed rule
  false positives (`462a76`, `c0f4ef`, `02c9ea`, `79bf95`, `24970a`) — the rule matches a call
  SHAPE and cannot see a deliberate env scrub, a helper-supplied `PYTHONPATH`, or a `-m` stdlib
  invocation. PLAN-135 filed them rather than suppressing them, which is correct; the consequence
  is that **the gate stays red until the rule is fixed**. → **WS-03**, and it is a rule defect, not
  a sweep residue.
- **`a073b5` — no test discriminates whether the `_run_python` isolation holds.** The code is
  correct and the prose now accurate, but both consuming assertions pass under the old and new
  regimes, so a regression would keep them green. Missing regression protection, not a live
  defect. → **WS-03**
- ⛔ **The landing message carried no `landing-facts` block at all.** `inbox landing-check` returned
  `complete: false` with the WHOLE required set missing (`schema`, `plan_id`, `pr`, `merge_state`,
  `deliverables_total`, `deliverables_done`, `total_tokens`, `steps` — 8 of 8). The payload is rich,
  well-evidenced prose and every fact in it was corroborated independently, so nothing was lost
  *this* time — but it was recovered by hand from git, the CI abstraction and the archived metrics,
  which is exactly what the machine-readable block exists to remove. Every landing this epic has
  drained so far is in the same pre-fix state.
- **The spec's D2 named a 23-name `KNOWN_REGISTRATION_COLLISIONS` baseline; the constant holds 17.**
  Verified by reading it at HEAD. The plan's "unchanged at 17" is the correct figure. Nothing
  shipped wrong — the guard held and no baseline was widened — but a spec premise off by six was
  quoted by the run and never caught. Together with D3's stale "15 tree-wide" (actually 17), **two
  of four spec premises in this plan were numerically stale at launch**. This is the re-grounding
  cost of launching without running `cleanup` first.
- ⛔ **296,505 tokens of `baseline_drift` recovery are invisible to retrospective waste
  accounting.** `error_total_tokens` counts only fatal `error` terminations and
  `retryable_total_tokens` only `blocked_session_restart` + `harness_cancellation`, so a
  `baseline_drift` row lands in NEITHER and both read `0` on a run that burned 296K tokens for no
  work — 12.0% of the 5-execute phase. Harness-side; lesson `2026-09-08-01-001`.
- **The documented drift recovery cannot clear the gate it is dispatched against.** `2-refine`
  resolves drift as CONTENT and never advances the branch; the phase-5 entry gate tests git
  ANCESTRY. The second abort was structurally guaranteed, not unlucky. The run recovered by a
  logged deliberate divergence (hand merge), which the documented workflow does not sanction.
  Already promoted as lesson `2026-09-08-01-001`; harness scope, outside this epic.
- **`default:branch-cleanup` deadlocks its own archive gate on every clean run** — it deletes the
  worktree without reconciling `metadata.use_worktree` / `metadata.worktree_path`, so every later
  phase-entry assertion fails and the operator must hand-repair with two `manage-status metadata`
  calls. Already promoted as lesson `2026-09-08-01-003`; harness scope, outside this epic.
- ⛔ **One defect is filed four times under three component spellings.** The `baseline-reconcile`
  locale bug (localized `git merge-tree` prose scraped without pinning `LC_ALL`, reporting 8
  conflicts for 2 real ones — it drove this run's entire wasted drift cycle) is recorded as
  `2026-09-03-19-001`, `2026-09-04-07-001`, `2026-09-04-17-011` and `2026-09-07-21-001`. Gate 1
  dedup keys on component + root cause; the root cause is identical across all four and the
  component is written three ways for one script, including the empty string. This **compounds the
  carried "12 corpus lessons unaddressable by id-keyed verbs" item** — a record whose component
  does not survive listing is invisible to a `--component`-filtered dedup query by construction.
  Consolidation via `supersede` is `lessons`-mode work, not this epic's. Lesson
  `2026-09-08-01-002`.

#### Added by PLAN-155's landing (#1455, 2026-09-09)

- ⛔ **Eleven epic-relevant lessons went to the global corpus and this epic can never drain them.**
  `2026-09-08-13-001` … `-13-011`, all dated to this run. The finalize dispatcher forwarded
  `orchestrated: false` to `plan-retrospective`, `project:finalize-step-review-retrospective` and
  `lessons-capture` without ever running the resolution seam, which returns
  `orchestrated: true, epic: test-quality`. **This is the THIRD consecutive instance and the second
  inside this epic** — PLAN-135 reported the same fault, and the recurrence is appended to lesson
  `2026-09-06-07-002`. Until the dispatcher is fixed, **every landing in this epic silently loses
  its lesson stream**, and the inbox drain reports a clean zero over messages that were never
  written. The landing message states the mis-routing explicitly, which is the only reason this is
  visible at all. ⚠️ The message counts "8 plan-retrospective lessons plus 2 appended recurrences";
  the corpus holds **11** — it names three affected producers but counts only one.
- **Five infrastructure defects, filed, none of them PLAN-155's subject:** `2026-09-08-22-001` (a
  bot whose only publish shape is an issue comment can never satisfy `head_sha_verified`),
  `2026-09-08-22-002` (`scope_creep_check` emits an unregistered finding type and crashes at persist
  on **every** over-threshold plan), `2026-09-09-01-001` (the self-review surfacer reported clean on
  a class it enumerates, where a reviewer found three), `2026-09-09-01-002` (a finalize loop-back
  never re-opens the metrics row — this run recorded `loop_back_iteration: 3` while `generate`
  reported `re_entered_phases[0]`), `2026-09-09-01-003` (phase-5-execute Step 10's per-deliverable
  commit predicate tests the plan's chain tail rather than the deliverable's).
- ⛔ **A structurally-refusing optional bot satisfied the review quorum on a single-reviewer PR.**
  Sourcery refused on every round — a 150,000 diff-character cap against 14,971 measured changed
  lines — so `review_completeness` reports `proves: participation_only`. It blocked nothing because
  it is optional, but in review-CONTENT terms this was reviewed by one bot. **Third landing in five
  where coverage was thinner than the quorum implies** (PLAN-105 had zero bots, PLAN-110 had 1 of 3).
- **Three CodeRabbit nitpicks deferred, not rejected** (`2026-09-08-21-001`) — each needs a
  `marketplace/bundles/**` production change PLAN-155's Expected Surface excludes. Shared shape:
  *a test mirroring a production set that production does not expose*. → **WS-03 / WS-04**
- **The launch handshake skipped `running` for PLAN-155.** The row went `staged → launched →
  shipped`. When the start was reported, the orchestrator probed for ground truth — plan directory,
  worktree, branch, recent `.plan/local` activity — found none, and declined to record a state it
  could not observe. The plan did run (archived at `2026-09-09-close-the-runtime-slice-…`), so the
  probe was too early or aimed at the wrong checkout. The refusal was right and the ledger is
  honest; the remedy is to report a start after the plan directory exists.

### Unowned — recorded, no staged spec claims them

- **Per-slice reduction residue.** PLAN-030 D3 (arrange-into-fixtures, ratio 19.9:1 — *worse* than the
  corpus benchmark; `parse_ns` exception list empty **by non-attempt**), PLAN-040 D2/D3 (124 unpaired
  `run_script` sites, no collapse performed) and D5's `parse_ns` half (387 sites), PLAN-050 D2 (5
  `manage-status` builders) and D5's parametrization half. Each is a **re-entry into a landed slice**;
  none is staged, because staging six speculative re-entries is the over-planning the cleanup contract
  warns against. Stage on demand.
- **Three of PLAN-100's four process lessons never reached the lane contract** — PLAN-090's single lesson
  did. The harness-improvement loop is running slower than the campaign meant to consume it.
- **`uv.lock` out of sync with `pyproject.toml` on `main`** — recorded by both PLAN-010 and PLAN-020.
- **`create_nested_marshal_json` is a fourth marshal builder by behaviour**, left when PLAN-020 § D2
  collapsed three into one.
- **Three pre-existing `test-conventions` rules carry no `rule-catalog.md` row.**
- **Unowned by design, correctly:** populating the `identifier-validator-corpus` registry (a coverage
  decision, not a rule gap) and the `broken-relative-link` rule's fragment half (a new analyzer
  capability, not a widening).
- ⛔ **The epic's scoping brief states "Coverage was measured in neither run" for PLAN-080. That is
  false** — its run 01 measured 85% → 85%. `archive/README.md` is the frozen audit record and is not
  edited; [`landings/PLAN-080.md`](landings/PLAN-080.md) governs.

### Added by the lessons sweep 2026-09-17 (corpus → epic relocation)

- **Ext-self-review surfacer blind spots — retained corpus lessons, unowned
  instrument-hardening follow-up.** Two lessons describe detectors that report clean
  over populations they never evaluate (the epic's thesis defect, in a different
  instrument than PLAN-175's `_test_shape_scan`): `2026-09-02-14-003`
  (`user_facing_strings` structurally unreachable for module docstrings and `async
  def` docstrings, predicate fix proposed) and `2026-09-09-01-001`
  (hand-mirrored-table class enumerated but unmatched on three live instances,
  regression fixture proposed). Both stay in the corpus — `2026-09-09-01-001` has
  live ledger references (PLAN-155 sections) that removal would orphan — and neither
  is covered by PLAN-175. A future instrument-hardening plan takes them; until then
  this entry is the owner of record.

### Added by PLAN-176's landing (9 carves, 2026-09-18)

- **Landing-facts arrived `complete: false` (`merge_state`/`cleanup_owed` unknown).**
  Both facts corroborated independently at the drain (9 merges on main, branch
  deleted, worktree deregistered, plan archived) and the landing was reconciled on
  that basis — but the pattern (a landing that carries only narrative for its two
  terminal facts) is the pre-fix class from PLAN-135's landing, recurring two
  epics later. The machine-readable block exists to remove hand-recovery; this
   drain paid it again.

### Added by PLAN-177's landing (#1534, 2026-09-19)

- **PLAN-177 SHIPPED as #1534 (merge `a5977d953`) — both gate gaps closed as
  specified.** D1 taught the `subprocess-pythonpath` detector its five filed
  false-positive shapes with matched clean/violation control pairs; D2 added the
  `_run_python` isolation discrimination test. `landing-facts` arrived
  `complete: true` — the first complete landing since the machine-readable block
  exists, breaking the `complete: false` streak from PLAN-135 through PLAN-176.
  Residue corroborated: `create-pr` recorded `pr_number=1531`, but #1531 closed
  unmerged and the branch was re-proposed as #1534 (merge-queue merged). Claim 1
  stamped `corroborated` at `5feeff9429` (`test-quality/analyze`). Landing record:
  `landings/PLAN-177.md`.
- ⛔ **Post-merge review lead: `_has_pythonpath_env_kwarg` name-only shortcut.**
  CodeRabbit's latest round (posted `2026-09-19T06:55:51Z`, unresolved) reports
  the exempt-name check accepts `env`/`subprocess_env`/`child_env` before
  resolving the binding, so `env = {}` + `env=env` reads as safe despite no
  `PYTHONPATH`. Fix: remove the name-only shortcut or require the resolved
  binding to match a trusted shape. → **WS-03, unowned** (PLAN-177 shipped; fold
  into the next instrument-hardening plan or stage on demand).
- **Realized-vs-declared delta (absorbed, no action):** 6 files realized against
  3 declared surface entries — the extra two are
  `.../plugin-doctor/standards/doctor-test-conventions.md` (the doc the narrowed
  py_compile-only exemption had to keep in parity, fixed in-run as `b8cce0470`)
  and `test/test_runner_falsifiability.py` (harness guarding the new shapes).
  No pairing decision was misled (N=1 sequential, flight line empty).
- **Inbox drain owed:** 9 messages queued (7 candidate-lessons 001–007 from this
  sender — incl. the OUTCOME/dispatch-boundary/argparse process trio — plus the
  reconciled landing 008 and the slice-040 finding 005). Dispositions belong to
  the inbox-scan drain, not to this ship reconciliation.

### Added by the PLAN-177 inbox drain (2026-09-19, 9 drained)

- **5 promoted to the global corpus:** `2026-09-19-09-001` (OUTCOME backfill,
  from 001), `-002` (finalize dispatch boundaries, from 002), `-003`
  (argparse-rejection retry guard, from 003 — fifth family occurrence in this
  epic), `-004` (Class-3 contract drift, from 004), `-005` (review-bot guard
  trio, from 007). -004 and -005 share the doc-parity instance and cross-ref
  each other rather than duplicating.
- **2 discarded (process worked as designed):** 005 + 006 (owed re-examination
  rounds that ran and converged in-run at `b8cce0470`) — no reusable residue
  beyond current behavior.
- **Landing 008 reconciled (no duplicate writes):** already reconciled in paste
  mode (`landings/PLAN-177.md`, row shipped, `landing-check complete: true`
  re-confirmed at this drain); archived on consume.
- **Finding slice-040-005 observed (Watch):** operator-directed post-plan
  follow-up — 7 unhandled #1519 threads handled (6 fixed in #1529 merged as
  `2fd4379f`, 1 refuted), deferred-hardening pickup running outside the
  lifecycle. Watch item: canonical CI taxonomy derivation flagged as a
  feature-sized dedicated plan if wanted (not staged — operator has not ordered
  it); sibling-site claim pattern unreliable, every site AST-verified.

### Added by the PLAN-180 carve-1 finalize observation (2026-09-19, no ship semantics)

- **Carve-1 (D5) merged as #1538 (`cd6436a4a`), corroborated:** `ci pr view`
  state `merged`, merge commit in main history (HEAD now `433d0a67b` via
  #1540), tree clean, `uv.lock` restored with no diff. Scope as briefed: D5
  fixture-yield rule + AST guard with matched controls + 10 live fixes, no new
  skips. The single CodeRabbit thread resolved; CI fully green at merge.
- **PLAN-180 row stays `running` — deliberately no transition.** The spec
  carries 9 deliverables; carves 2–4 remain (carve-2: D1/D2/D3, carve-3: D4/D8,
  carve-4: D9 basetemp as dedicated plan). Shipping the row on carve-1 would
  misattribute the remaining scope; parking it would preempt the drain. The
  plan lifecycle closed (archived `2026-09-19-test-fidelity-rules`,
  `phase_closure: complete`) — the row now tracks the staged carves, not a live
  plan. Full reconciliation (carve-1 facts + carve sequencing) belongs to the
  inbox drain of `test-fidelity-rules-001/002`, not to this observation.
- **001 superseded by 002 on merge state** (open at `5194a64d0` → squash-merged
  via queue); both await drain. 001's outline-verdicts (D7 done; D1/D2/D3 →
  carve-2; D4/D8 → carve-3; D9 → carve-4) are leads for that drain.
- **006 uv.lock judgment call corroborated clean and recorded as positive:**
  dirty `uv.lock` was pure ruff-bump churn, restored to HEAD over stash/pop
  with the tradeoff disclosed — the self-correction behavior the epic wants
  (cf. PLAN-165's PR-body correction). No defect.
- **3 process-compliance findings noted, not drained here:**
  orchestrator spec-read gap, 9-deliverable split + lifecycle-shortcut
  disclosure, D9 staging evidence — all filed to the process-compliance inbox
  by the plan; outside this epic's drain.

### Added by the PLAN-180 carve-1 inbox drain (2026-09-19, 2 drained)

- **Open Defect: both carve-1 landings arrived `complete: false`.**
  `test-fidelity-rules-001.md` + `-002.md` carry narrative only — `missing_keys`
  names the whole required set (9 of 9) on both. Same pre-fix class as
  PLAN-135/176, recurring one epic later. The merge facts were corroborated
  independently (#1538 merged `cd6436a4a`, tree clean, plan archived), so the
  drain reconciled on that basis; a manual paste from a follow-up carve may
  still surface a required fact the inbox did not. 002's incompleteness folds
  here as recurrence, not a second defect.
- **Partial-carve stamps applied, no ship:** `plan_marshall_plan_id` →
  `test-fidelity-rules`, `pr` → `#1538` (one `--set-row` each, as 002 asked).
  `landing` deliberately left empty — no `landings/PLAN-180.md` exists by
  design (carves 2–4 remain; a landing report now would assert ship semantics).
  Deviation recorded here rather than silently omitted. Row stays `running`.
- **Carve-2/3/4 sequence CONFIRMED (001's ask, decided not escalated):**
  carve-2 (D1/D2 argv+prune rules, D3 mechanism test), carve-3 (D4 mirror rule,
  D8 registration rule), carve-4 (D9 basetemp as dedicated plan) — per the
  spec's own split rule for oversized mechanical changes, already staged by the
  plan. 001's outline-verdicts (D7 done) are absorbed as the sequencing basis.
  001's open-PR state is superseded by 002 (open → merged); 001 still
  contributed the verdicts.
- **Next carve needs no new row yet:** PLAN-180's row tracks the staged carves;
  when the operator orders carve-2, emit under this row or stage a successor
  row then — decided at that time, not here.

### Added by PLAN-180's landing (#1538 + #1549, 2026-09-20)

- **PLAN-180 SHIPPED — all 8 deliverables across two carves.** Carve-1 (D5) as
  #1538 (`cd6436a4a`); carves 2–4 as #1549 (merge `ada9d8d6`):
  argv/pruning/tool-default/mirror/carve-guidance/skills-root/registration/
  basetemp rules, each with guard + matched negative control, no new skips.
  19 tasks green; review-bot round, self-review loop-back and merge-queue prune
  all closed. Row: `shipped`, pr `#1538, #1549`, `landings/PLAN-180.md`; open
  HYPOTHESIS stamped `corroborated` at `1e2aa916a`. Landing record:
  `landings/PLAN-180.md` (the carve-1 partial reconciliation stands as history).
- **3 wrong `simplify` deletions reverted in-run** (would have gutted
  deliverable guards; one legitimate stale-count fix kept) — recorded as
  positive self-correction alongside the 006 uv.lock call. Tokens UNMEASURED
  (no figure reported — not zero).
- **DECLARATION FORM — severe under-declaration, second in this direction:**
  ~9 of 12 realized files outside the 2 declared directories (build wiring,
  pyproject, dev-docs, shared harness, 4 slice guards). Mechanism named
  (basetemp relocation necessarily touches production-adjacent files); no
  pairing misled (N=1, flight empty). Carried as evidence, no new plan.
- **Follow-up residue (operator-owned, not staged):** `/marshall-steward` run
  (session hook + config seed); prune the 10 compliance-inbox notes once read.
  The 2 retrospective lessons went to the corpus directly — nothing owed here.
- **Epic close candidacy re-opens:** only PLAN-140 remains non-terminal
  (running run 3 since the 2026-09-20 resume — see the run-3 drain section
  below). Close still needs the campaign's end or the operator's PLAN-140
  disposition.

### Added by the PLAN-140 run-3 drain (2026-09-21, 4 drained)

- **B0 carve 1 (manage-providers) landed as #1552, corroborated:** `ci pr
  view` state `merged`, merge commit `7a94d3e8` ancestor of HEAD, PR body
  gates match the report (fidelity 208→208 lost=0, doctor error-0/budget-3,
  pytest 282+282, test_configure 752→713). Row stamped `pr: #1552`
  (first-carve link, as requested); `landing` left empty — partial carve, same
  precedent as PLAN-180's carve-1 (no landing report asserts no ship).
- **001 (D1 re-derivation) + 002 (batch map) absorbed as observed:** 66
  over-budget collected modules at dispatch (leads 55/53 confirmed stale, not
  adopted); B0-then-B1–B4 map (~255 files, 63–65 per PR, sequential, one in
  flight) held as the carve basis. D1's 66 accepted as plan-reported — the
  doctor re-run is plan work, and 003 already verified the outcome side.
- **Carve-2 NOT separately staged or emitted — declined with rationale
  (overrides 004's request 3):** (1) the next B0 source is unnamed in the
  messages, so a spec would invent scope; (2) a second plan on slice-060
  files while PLAN-140 runs them collides under N=1 sequential. Carve
  sequencing stays with the running run-3 plan on its per-source pattern.
  Operator word with a named source overrides this.
- **Standing instructions persisted (004, minus the trailer already
  standing):** Tier M PRs carry `skip-bot-review`, Tier J keeps review
  (label never waives gates); every PR checked for Sourcery comments with
  dispositions before merge; two-tier review (M: 5 machine facts, J: cluster
  boundaries) with D5 per-PR label/skip/presence logging. See Queue
  annotations.
- **004's queue picture corrected, not parroted:** it reads PLAN-140 as
  "still launched" — actually `running` since the operator-confirmed start.
  004's 5 process-compliance filings (`test-quality-002`…`-006`) noted; that
  epic drains them, not this one.

### Added by the PLAN-140 run-3 drain II (2026-09-21, 1 drained)

- **005 absorbed as observed — the nominated carve order is now on record:**
  12 remaining B0 sources (63 over-budget modules; 63 + carve-1's 3 = 66,
  reconciles with D1): tools-permission-fix 2, tools-permission-doctor 2,
  manage-logging 2, tools-input-validation 2, manage-files 2, ref-toon-format
  2, lsp-client 2, tools-file-ops 2, extension-api 6, tools-script-executor 10,
  platform-runtime 12, script-shared 19. Giants (platform-runtime,
  script-shared) may each split a/b at staging time; ref-toon-format +
  lsp-client (zero `monkeypatch` hits) are verify-only candidates for merging.
- **Nomination: carve 2 = tools-permission-fix** (smallest, densest setup per
  file, pairs with carve-3 tools-permission-doctor, mirrors carve 1's shape).
  Counts accepted as plan-reported (read-only derivation on the landed tree;
  re-running the sweep is plan work).
- **No separate carve-2 row staged — sequencing stays with the running run-3
  plan**, per the prior drain's rationale (unnamed-source gap now closed by
  this nomination, but the file-collision half stands: a second plan on
  slice-060 files while PLAN-140 runs them violates N=1). The run executed
  carve 1 itself; it executes carve 2 on the nomination.
  (SUPERSEDED by the flip below: PLAN-181 staged, sequencing moves to separate
  rows.)
- **Close verdict on PLAN-140: NOT yet** — carve 1 of ~17 units landed (12 B0
  sources + B1–B4 remain). Row stays `running`.
  (SUPERSEDED: row parked on handoff completion; see drain III.)

### Execution-model flip (operator decision, 2026-09-21): campaign orchestrator-steered

- Carves execute as separate orchestrator-emitted rows (PLAN-181 staged first),
  not inside the run-3 plan. The run-3 plan yields execution after the handoff
  extraction below and goes verify-only; its carve sequencing role ends there.
- Handoff extraction owed from run-3 (requested by paste-command, next
  section): per-source over-budget module NAMES for all 12 B0 sources (paths +
  line counts — the counts alone cannot scope specs), in-flight state (any
  started carve-2 work, uncommitted changes, branch/worktree state), explicit
  yield acknowledgment, complete `landing-facts` blocks on every future
  message.
- Sequence: extract → park PLAN-140 → emit PLAN-181 into the free slot.
  PLAN-140 is NOT parked yet — parking it while its agent holds unreported
  in-flight state would fork authority. The park lands on the extraction
  drain.

### Added by the PLAN-140 run-3 drain III (2026-09-21, handoff 006 drained)

- **Handoff complete — flip executed: park → emit sequence.** 006 delivered
  all four extraction items: 63 per-source module paths (005 order, HEAD
  `e8a716501`; 63 + carve-1's 3 = 66), clean in-flight state CORROBORATED
  (tree clean, main at origin `e8a716501`, no plan-140 worktree/branch/commits),
  explicit yield acknowledgment, lesson status explained (no re-file).
  PLAN-140 `running → parked` on the completed yield; PLAN-181 emits into the
  free slot below.
- **006 absorbed as observed** (no candidate-lesson filed — accepted as
  stated: every reusable item already stands drained; the drain names nothing
  to extract).
- **PLAN-181 emit verdict:** declarative + admits; every overlap row terminal
  (6 landed corpus/sibling specs — inert); live side could-not-check
  (NO_PLAN/phase-gates indeterminate, same standing caveat); prep-ready admits
  (open HYPOTHESIS). N=1, R=0 → the 1 slot. `launched` operator-confirmed.

### Added by the PLAN-140 run-3 drain IV (2026-09-21, parked notice 007 drained)

- **007 absorbed as observed — run-3 sender stood down.** Parked as of the
  message; nothing in flight, tree clean at `e8a716501` (as previously
  corroborated). Stream intentionally left OPEN (no close-stream): sender
  available for verify-only work. 006's "queued" line inside 007 is stale —
  006 drained the turn before; noted, not a discrepancy in ground truth.
- **Complete chain confirmed:** D1 (001), batch map (002), carve-1 verification
  (003), handoff (004), source list + nomination (005), paths + in-flight +
  yield (006), parked notice (007) — all drained and archived. Nothing lives
  only in session context by the sender's account, and the ledger holds every
  item independently.
- **Suggested anchor not adopted verbatim** (it predates this drain and names
  006 as queued); equivalent anchor set naming the drained state.

## Watches

{Mid-flight observations that need monitoring but no immediate action — signals to
re-check at the next landing or session. Retire a watch when it resolves or graduates
into a defect/plan.}

- **Slice-040 deferred-hardening pickup running outside the lifecycle (from the
  2026-09-19 drain, finding `module-budget-campaign-run-2-slice-040-005`).**
  Operator-directed follow-up implementing the 8 findings accepted-as-hardening
  on #1526 with no ceiling; #1529 (6 thread fixes) merged clean. Open: canonical
  CI taxonomy derivation is feature-sized (production `ci_verify.py` + tests +
  docs) — stage a dedicated plan only if the operator orders it. *Re-check at:
  the next drain or status — confirm the pickup landed and whether the taxonomy
  plan was ordered.*
- **`corpus cross-check` does not distinguish a landed spec from a staged one.** Its 20 file-overlap rows
  collapse to 10 unordered pairs, of which **9 pair a staged spec against a landed one** — inheritance,
  not duplication: a follow-up plan touching a file its predecessor owned is the normal case. Exactly one
  pair is a live collision (`PLAN-110 ↔ PLAN-135` on `test/conftest.py`), and it is already recorded in
  both specs' sequencing. Every future cleanup must re-apply this filter by hand, and a genuine second
  collision could hide among the nine. *Re-check at: every cleanup, and whenever a plan lands.*
- ⛔ **Conformance drift inside an already-converted slice.** PLAN-080's "211 of 211 converted, zero
  hand-built" was falsified **within two days** by two unrelated epics' PRs landing new modules inside its
  Expected Surface that do not follow the norm it established. This is the epic's directory-level
  partition defect one level down — at file content, inside an owned directory — and **no document
  watches it**. The rules run at `severity: warning`, so a non-conforming new module is reported and
  ignored. *Re-check at: every landing, and whenever a flip-to-`error` decision is considered.*
> ↪ Relocated to `settled.md` § "The conformance-drift watch's second firing" — superseded by the third firing below, which carries the live watch.
- ⛔ **The conformance-drift watch has now fired a THIRD time, in a four-commit window.** Between
  `77db1a0d` and `00b92fca` — four commits, none of them this epic's — the budget population moved
  **+9** (270 → 279), `preamble-boilerplate` **+3** (107 → 110) and `docstring-historical-prose` **+4**
  (201 → 205). Three firings in three consecutive windows is no longer drift to monitor; it is the
  steady state. **A flip from `severity: warning` to `error` now has three instances behind it**, and
  every campaign figure this epic stages goes stale roughly as fast as it is written.
  *Re-check at: the next flip-to-`error` decision, which should now be made rather than deferred.*
- ⛔⛔ **FOURTH firing, and the largest — plus the one population asserted STABLE has now moved.** Between
  `00b92fca` and `09f92b5e` — a **270-file, 33,514-insertion** window, an order of magnitude larger than
  any previously re-grounded — every rule population moved again: budget **+27** (279 → 306),
  `docstring-historical-prose` **+9** (205 → 214), `preamble-boilerplate` **+2** (110 → 112), and
  ⛔ **`subprocess-pythonpath` **+1** (15 → 16), which PLAN-135 explicitly recorded as "unmoved at 15
  across all three measurements".** That stability assertion is refuted, so the rule set now offers **no
  fixed floor at all**. PLAN-150's namespace figures broke the same way: 518/12/506 held across three
  shas and moved **+42** in this one window. ⛔ **The flip to `error` now has FOUR instances and a
  refuted-stability instance behind it. Deferring it again is a decision to keep re-scoping every staged
  count once per window, indefinitely** — this pass re-scoped five specs for no reason other than drift.
  *Re-check at: nothing. The evidence is sufficient; make the flip decision.*
- **A drain's inbox enumeration is a snapshot, not a closed set.** PLAN-120's 15 candidate-lesson
  messages were enumerated at 09:08; its `kind: landing` message was filed at **09:09:17**, after that
  list was taken. A drain that trusted its first enumeration would have closed reporting "no landing was
  ever filed" — a wrong conclusion reached through a correct procedure. The append-only inbox is behaving
  as designed. *Re-check at: every drain — re-enumerate before declaring the queue empty.*
- **"Owner assigned" is not "owner has acted."** PLAN-030's and PLAN-040's over-budget modules have had a
  named owner since the campaign was written; the campaign has run once, against a third plan's slice.
  Three separate ground-truth checks flagged this reading. *Re-check at: every status report.*
- **Harness adoption is thin against the corpus.** 36 modules use `parse_ns` against ~2,467 remaining
  hand-built `Namespace(` sites tree-wide. Nothing either PLAN-010 or PLAN-020 claimed is refuted — but a
  reader of "**B6** complete at 211 of 211" could mis-read the whole corpus as converted.
  *Re-check at: PLAN-150's landing.*
- **36 module/name pairs patch an import-time binding of a doubly-registered module** — an AST-derived
  candidate order-dependency class with **1** confirmed live and fixed. Same "rests on a single instance"
  shape as R1/R3/R4. *Re-check at: PLAN-160's landing, which may absorb it.*
- **23 pinned `sys.modules` collisions and 90 statically-unresolvable loader call sites**, both at their
  guard's baseline. ⚠️ **Not defects — they are bounded by a guard that fails on growth**, which is the
  right posture. *Re-check at: any landing that would grow either baseline; growth is the signal.*
- **HEAD moved during this ingestion**, from `2cd1a19c` to `ec26306e`. That commit is the `multiplattform`
  epic's own ingestion — pure deletions under `doc/plans/multiplattform/`, touching no `test/` and no
  `marketplace/bundles/` file — so every figure verified at `2cd1a19c` still holds. *Re-check at: the next
  re-derivation, which should stamp its own sha.*

### Added by the PLAN-170 + PLAN-150 double landing (2026-09-03)

> ↪ Relocated to `settled.md` § "Added by the PLAN-170 + PLAN-150 double landing (2026-09-03)" — both plans shipped; every finding here is resolved, superseded, or carried forward by name in a later landing section.

### Watches added by the same double landing

> ↪ Relocated to `settled.md` § "Watches added by the same double landing" — the watches these raised have each resolved or graduated into a later landing's record.

### Defect found by verifying the PLAN-170 landing rather than recording it

> ↪ Relocated to `settled.md` § "Defect found by verifying the PLAN-170 landing rather than recording it" — the defect is closed and its verification lesson is carried in the corpus.

### Added by PLAN-105's landing (#1407, 2026-09-04)

> ↪ Relocated to `settled.md` § "Added by PLAN-105's landing (#1407, 2026-09-04)" — PLAN-105 shipped; its instruments landed and its open items were absorbed by PLAN-130/135/155.

### Added by PLAN-145's landing (#1395, 2026-09-04)

> ↪ Relocated to `settled.md` § "Added by PLAN-145's landing (#1395, 2026-09-04)" — PLAN-145 shipped; the parser-seam gap it refuted is retired and guarded by a committed test.

### Added by the 2026-09-04 analyze (mid-flight observation, no ship semantics)

> ↪ Relocated to `settled.md` § "Added by the 2026-09-04 analyze (mid-flight observation, no ship semantics)" — the mid-flight observation resolved at the next landing.

### Added by PLAN-110's landing (#1426, 2026-09-06)

> ↪ Relocated to `settled.md` § "Added by PLAN-110's landing (#1426, 2026-09-06)" — PLAN-110 shipped. RETAINED BY POINTER because its retirement of 'accurate AND narrow' is STILL BEING RE-ARGUED - see the live declaration-form question in the PLAN-160 landing section.

### Added by the 2026-09-06 analyze — the residual skips, answered

> ↪ Relocated to `settled.md` § "The residual skips, answered" — the question *why are there still disabled tests, and can they be removed?* was answered once from ground truth and carries its own do-not-re-derive instruction. The subject is closed; the record stays reachable because the remedy (install `pyright`, do not delete) is an operator call that must not be re-litigated.

### Added by PLAN-130's landing (#1436 + #1435, 2026-09-07)

> ↪ Relocated to `settled.md` § "Added by PLAN-130's landing (#1436 + #1435, 2026-09-07)" — PLAN-130 shipped; the rule-widening regression class it swept is closed.

#### Rule populations re-derived at merged `main` (`681db9446`) — the next cleanup's inputs

Captured as a side effect of corroborating this landing, so the next re-grounding does not pay for
them again. ⚠️ Every figure supersedes the `00b92fca` and `bf1b7ed6` numbers still quoted in the
staged specs.

| Rule | At merged main | Owner | Prior figures |
|---|---|---|---|
| `test-module-line-budget` | **343** / 343 files | PLAN-140 | 279 (`00b92fca`) → 330 (`bf1b7ed6`) — still climbing |
| `test-module-preamble-boilerplate` | **103** / 86 files | PLAN-135 | 110 (`00b92fca`) → 101 (`bf1b7ed6`) |
| `subprocess-pythonpath` | **17** (error severity) | PLAN-135 | 15 (`00b92fca`) → 17 — unmoved |
| `test-docstring-historical-prose` | **3** | PLAN-130 — closed | 232 / 111 files |

⛔ **The whole-tree gate's `status: fail` is entirely the 17 `subprocess-pythonpath` errors** —
`error_count: 17`, and every other finding is a warning. So the tree-wide red is PLAN-135's
population and nothing else.

### Added by PLAN-135's landing (#1446, 2026-09-08)

> ↪ Relocated to `settled.md` § "Added by PLAN-135's landing (#1446, 2026-09-08)" — PLAN-135 shipped; the shipped-accessor gap is closed and its residue is the derived structural floor.

### Added by PLAN-155's landing (#1455, 2026-09-09)

- ⛔ **DECLARATION FORM — the first informative measurement in six, and it cuts against the carried
  retirement.** PLAN-155 realized **97 of 97** files inside its declared surface, and unlike every
  prior measurement **the declaration was NARROW**: 15 entries (14 named directories plus
  `test/conftest.py`), not a root `test/` claim. All 14 directories were touched, `test/conftest.py`
  was declared and correctly not needed, nothing landed outside. PLAN-130's 112 of 112 and
  PLAN-135's 89 of 89 were uninformative precisely because a root claim means nothing COULD land
  outside; here the declaration could have been violated and was not. The gate USED it — the
  PLAN-165 collision on `test/plan-marshall/manage-providers/` was machine-detected from this exact
  surface. ⚠️ **This obliges a re-argument of the retirement.** "Accurate AND narrow" was retired as
  the remedy by PLAN-110 on the grounds that the answer must be a different SHAPE. PLAN-155 is a
  counterexample: a narrow, accurate, machine-usable declaration authored without evident
  difficulty on a 97-file sweep. One counterexample does not overturn the retirement, but leaving it
  standing unexamined against this instance would be carrying a conclusion past its evidence.
- ✅ **RETIRED AS A WATCH, PROMOTED TO A TREND — finalize no longer outspends execute.** 6-finalize
  3,981,678 vs 5-execute 5,314,683 = **0.75x**, the THIRD consecutive sub-1.0 after PLAN-130's 0.91x
  and PLAN-135's 0.90x, and monotone decreasing across all three. The prior anchor set "a third
  would make it worth acting on" as the threshold and it has been reached. The series is clean in a
  way the earlier PLAN-170/145 samples were not — those measured wasted finalize share, a different
  quantity. **What remains expensive in finalize is WALL TIME, not tokens:** 13h4m of the run's
  15h46m idle sits in 6-finalize alone, against 2h19m worked there.
- **Budget overrun is the largest this epic has recorded.** 10,806,358 tokens against a stated 2.5M
  anchor — **4.3x** by arithmetic, where the plan's own report says 4.0x. 5-execute is 49.2% of the
  spanning total (the report says 53%). Both gaps are small and neither is hidden, but the ledger
  carries the measured figures. Worth weighing before PLAN-140, which is the remaining slice-sized
  plan.
- **A bot's detection being right while its remedy is wrong is now a pattern, not an incident.**
  Twice this run CodeRabbit's observation was correct and its prescribed fix was not — once the
  remedy would have made every assertion tautological — and both were declined WITH MEASUREMENT
  while the observation was taken. PLAN-135 recorded the same shape once. Worth naming as a
  competence the finalize flow reliably exercises, and worth protecting against a future
  "apply the bot's suggestion" shortcut.
- **`test-module-line-budget` moved 354 → 350 tree-wide**, and 53 → 48 among PLAN-155's touched set
  (the touched-set figure independently re-derived at 48). Still NO reconciliation with the carried
  whole-tree population of 279 at `00b92fca` — the two remain possibly different quantities and no
  delta is asserted. Reconcile at cleanup **before PLAN-140 is sized**; it is PLAN-140's population.

### Added by PLAN-165's landing (#1480, 2026-09-13)

- ✅ **THE OVERRIDE WAS VINDICATED — record it, because the next one will be argued from this.** The
  emit of PLAN-165 carried a recorded gate override: `corpus cross-check` reported a collision with
  live plan `implement-plan-06-test-falsifiability-survey` on
  `test/plan-marshall/workflow-integration-github/test_not_triggered_detection.py`, and the emit
  proceeded on the ground-truth finding that plan-06 had *surveyed* that file and recorded
  **"Verdict: keep as-is"** for both of its call sites. Both plans have now landed — PLAN-165 as
  #1480, plan-06 as #1476 — and their realized footprints are **disjoint to the file**: PLAN-165
  touched 4 files, plan-06 touched 4 others, intersection **empty**. The declared collision was
  entirely an artefact of plan-06 declaring its whole survey population as its footprint.
  ⚠️ **This does NOT generalize to "override the gate when it looks wrong".** What made this one
  safe was a *machine-checkable artefact in the other plan's own tree* recording the non-intent — not
  a judgement that the overlap looked unlikely. Absent such an artefact, the gate's verdict stands.
- ⛔ **DECLARATION FORM — the EIGHTH measurement, and the first to fail in the OVER-declaring
  direction on both sides at once.** PLAN-165 declared 7 entries and realized 4: the three
  `_github_ci.py` / `_github_issue.py` / `_github_pr.py` siblings were read for D1's adjudication and
  correctly never modified. Plan-06 over-declared far more sharply — its survey population included
  every file it inspected and left alone, which is what manufactured the false collision above. So
  the corpus now carries counterexamples in **both** directions: PLAN-155's narrow-and-accurate
  declaration (which the gate USED correctly) and these two over-declarations (which cost a real
  emit decision). ⚠️ **The live question sharpens rather than resolves**: the problem is not
  declaration accuracy alone but that a declared surface conflates *will modify* with *will read*.
  `references.json` already distinguishes these — it carries `read_intent_files` — and two of this
  run's own candidate-lessons (-005, -009) are about consumers mishandling exactly that distinction.
  **Re-argue PLAN-110's retirement against the read-vs-write split, not against accuracy.**
- ⛔ **The merge queue did not work, and the enqueue call cannot tell you so.** `ci pr merge-queue`
  returned `enqueued: true` twice; the PR sat `open`/`mergeable`/`clean` with all 11 checks green
  through **two full 30-minute windows** and landed only after the operator enqueued it by hand. The
  return asserts a property of the BRANCH (a queue rule is configured) and the caller reads it as a
  property of the PR (this PR joined the queue). Nothing downstream re-checks the second. The
  ledger reads as though the queue path worked unaided — the manual recovery is invisible to it.
  Filed as corpus lesson `2026-09-13-12-001`. ⚠️ **Unowned by any staged spec** (it is
  `tools-integration-ci`, outside this epic's test-corpus scope).
- ⛔ **The budget error thresholds were crossed on BOTH axes — the epic's first double breach.**
  4.97M tokens against a 2.5M anchor and 16h15m wall against 180 min, and the token figure is a
  **floor** (6-finalize never closed; 14 dispatch-boundary rows fold as `(boundary floor)`).
  The mechanism is named and measured: finalize re-firing is **53%** of all tokens, with 24 step
  firings across steps that nominally fire once and the three costliest re-fired steps all recording
  the **same** `head_at_completion` (`56d5d442`) — repeated work against an identical tree. Filed as
  corpus lesson `2026-09-13-12-002`. ⚠️ **This reverses the trend PLAN-155 promoted.** That landing
  retired the finalize-cost watch on a third consecutive sub-1.0 finalize/execute ratio; this run is
  **2.85x** (3.24M vs 1.14M). The retirement was made on three points and is refuted by the fourth —
  the watch is **RE-OPENED**, and the relocated `settled.md` item should be read with this beside it.
- ⛔ **A stale required reviewer blocks the barrier, and the prescribed loop-back cannot clear it.**
  `cuioss-review-bot` had reviewed `d55f2f90` but not the three commits that landed during review;
  its registry declares no auto-review-on-push, and `automatic-review` was already `done` at the live
  HEAD — so a bare loop-back would have **SKIPPED** the review step on the re-entry check and
  re-entered the barrier with an identical verdict. A loop-back that cannot change the input is an
  infinite loop with extra steps. Cleared only by the explicit re-review trigger the registry names.
  ⚠️ Compounding it: `automatic-review` returned `escalate_ask{reason=re_review_timeout,
  outcome=declined}` on a HEAD the bot **had** reviewed, because both bots publish re-reviews by
  editing a persistent comment in place and that path reports `head_sha_verified: false`
  unconditionally. Resolved on evidence rather than by taking the `declined` verdict.
- **Two review escapes, both classified gate-addressable.** CodeRabbit surfaced a `ROUTES`
  mirror-list source-of-truth duplicate on a branch where `pre-submission-self-review` had just
  recorded "10 candidates examined, no check matched" — a rule exists for that shape and it did not
  fire. Separately, **Sourcery scores 0% on every approved PR by construction**: its registry
  declares no `review_body_summary_patterns`, so a content-free `**Approved.**` counts as actionable,
  enters the denominator, and can never enter the numerator.
- ✅ **RESOLVED — `check-manifest-consistency` false fail.** Carried unowned since PLAN-155. Now
  fully explained and corpus-tracked: it is a second occurrence of `2026-09-04-17-006`
  (a post-merge `--base-ref origin/main` resolves an EMPTY footprint at retrospective `order: 995`,
  and reports it *resolved* rather than *indeterminate*, which is what lets the rule fail rather than
  abstain). The recurrence also added the deeper half — **resolver parity**: two of three sibling
  aspects recover the footprint unaided through the shared resolver and this one cannot. Both are
  recorded on that lesson. **Removed from the carried-unowned list.**
- ✅ **RESOLVED — the epic's lesson-stream leak.** Three consecutive prior landings sent their
  lessons to the global corpus without passing through this inbox, and the standing anchor warned
  "an empty inbox does not mean a quiet run". This run filed **all 15** candidate-lessons plus its
  landing into the inbox, and the drain routed each one deliberately: 11 promoted, 3 folded onto
  existing corpus lessons as recurrences rather than duplicates, 1 folded into PLAN-160.
  **The warning is retired.**
- ⚠️ **A plan corrected a false claim in its own PR body before merge.** The body asserted the strict
  serial reverse-order pass had run and passed; it had been killed twice by host memory with no
  verdict in either direction, and the body and landing were corrected to **UNMEASURED**. Recorded
  as a positive: the self-correction is the behaviour the epic wants. The residual is that
  `module-tests --no-parallel` with `PM_TEST_ORDER=reverse` is **not runnable on this host** at the
  current suite size, so the strict serial reverse-order signal is unavailable epic-wide until that
  changes. PLAN-160's R1/R3/R5 all carry "passes in default and reverse order" done-conditions that
  currently resolve to the parallel form only.

### Added by PLAN-160's landing (#1486, 2026-09-14)

- ⛔⛔ **THE EPIC BUILT ITS FIRST MECHANICAL CHECK AND PUT ITS OWN DEFECT CLASS INSIDE IT.**
  PLAN-160 shipped `test/_shared/_test_shape_scan.py` and the guards over it — the instruments
  that were supposed to make a swept class stop regrowing. Review on #1486 filed **at least ten
  findings against those scanners**, in three families: recognizers enumerated from the
  *canonical spelling* rather than from the construct (5, of which **two are the same gap found
  twice, three days apart**, because the first fix enumerated one more spelling); guards
  credited with a property their predicate does not entail or entails about the **wrong
  subject** (4 — one is a vacuity guard that is *itself vacuous*, with a comment directly above
  it naming it a vacuity guard); and an asymmetric path normalization that silently
  over-reports (1). ⚠️ **Every one was found by a review bot — not by the author, and not by the
  guards' own tests.** A scanner nobody can falsify is not a check, it is a claim.
  → **PLAN-175 staged.** This is not a re-litigation of PLAN-160: its sweeps and verdicts
  stand. The instrument is what needs hardening, and it is now load-bearing for every future
  sweep.
- ⛔ **DECLARATION FORM — the NINTH measurement, and the first severe UNDER-declaration.**
  21 declared entries against **87** realized files: **28 inside, 59 outside, 32.2% coverage**.
  Of the 59 outside, **42 sit under `test/plan-marshall/`** in sibling directories the spec did
  not name. Every prior measurement in this epic was accurate (PLAN-155, 97 of 97) or
  over-declaring (PLAN-165 and plan-06). **This is the dangerous direction** — the one that
  admits genuinely colliding plans — and the gate passed PLAN-160 as disjoint on a surface
  covering a third of what it touched.
  ⚠️ **Consequence for PLAN-140**: its surface is `derived`, explicitly the union of other
  plans' surfaces with PLAN-160's among them. A derivation from a 32%-accurate declaration is
  not a reliable input. Second independent reason not to size PLAN-140 from the ledger.
- ⛔ **A THIRD category the declaration model cannot express: will-INVALIDATE.** D5 flipped
  `empty_parameter_set_mark` project-wide, which made `testing-methodology.md:581` false — a
  file the plan never opened, whose content its change invalidated. A declared surface
  distinguishes *will-modify* from *will-read*; it has no word for this. **No diff-scoped
  review can catch it**, because the diff and the now-wrong sentence are in different files and
  the sentence did not change. A review bot found it; the plan did not. Fixed in-plan
  (`testing-methodology.md:603` verified). Corpus lesson `2026-09-14-05-006`.
  ⚠️ **This is now the sharpest form of the live question.** The answer is not "declare more
  accurately" — it is that a declared surface conflates three different relations to a file.
- ⛔ **THE FINALIZE-COST RETIREMENT IS REFUTED TWICE.** PLAN-155 retired that watch on a third
  consecutive sub-1.0 finalize/execute ratio. PLAN-165 ran **2.85x**; this run ran **1.96x**
  (or 1.77x — see below). Three points retired it, two have refuted it, and this run's finalize
  cost more than the work it was finalizing on a product of 87 mostly-trivial test edits.
  `loop_back_iteration: 5`, `pre-submission-self-review` at `firing_count: 7`.
  **The watch stays RE-OPENED**; the relocated `settled.md` item must be read with both beside
  it. New this run: **wall time has a different dominant term than tokens** — 68.1% of
  16,009,410 ms of script wall time sits in two CI-polling notations against 24.2% in the build
  wrapper. The verification was cheap; the review and CI round-trips were not. Remedy sharpens
  to **bound the loop-back round count** (corpus lesson `2026-09-13-12-002`).
- ⛔ **TWO SOURCES DISAGREE ON EVERY PHASE TOTAL FOR THIS RUN.** `record-metrics`: 9,380,546
  tokens, finalize 5,270,710 / execute 2,689,773. The `plan_efficiency` aspect: 9,882,263,
  finalize 5,441,503 / execute 3,072,253. The ratio is 1.96x or 1.77x depending which you read.
  The conclusion is robust to the disagreement; **the disagreement itself is unexplained** and
  is recorded rather than smoothed. A measurement-truthfulness defect in the epic that exists
  to remove measurement-truthfulness defects.
- **Second consecutive double-threshold budget breach** — 9.38M tokens (3.75x the 2.5M anchor)
  and 21h25m wall (7.1x the 180-minute anchor). PLAN-165 was the first.
- **`ci pr view --plan-id` returns `auth_failed` after worktree removal** while `--project-dir`
  succeeds — operator-reported, worked around. The `--plan-id` fallback path is the suspect,
  and the post-cleanup state is the *same systematic condition* the footprint resolvers fail
  in. ⚠️ Unowned.
- ✅ **R3 correctly reported swept-only.** It admits no mechanical predicate and gained no
  ported rule, and the plan said so plainly rather than claiming a check it did not build.
  That distinction was the whole point of the deliverable and it was honoured.
- ✅ **The third occurrence of the post-merge footprint defect REFUTES the remedy recorded one
  drain ago.** Resolver parity is necessary but **not sufficient**: this run measured both
  failure directions at once — `--base-ref origin/main` gave **0** paths, the shared resolver
  gave **130** (≈43 of them sibling commits rebased under the branch), against a ground truth
  of **87**. Handing the failing aspect the shared resolver would have moved it from a false
  empty to a false wide. Correct anchor is the **merge base**, or the merged commit the landing
  facts already carry. Recorded on `2026-09-04-17-006`.
- ⚠️ **The argparse-rejection family reached FOUR occurrences, and this one fired inside the
  lessons-capture Signal Gate** — the step whose job is to notice recurrences — reproducing
  recurrence signature #5 verbatim inside the framework that documents it. A documented rule
  plus an edit-time doctor cluster has now failed to prevent the class at call time four times.
  Recorded on `2026-09-13-12-005`.

### Inbox drain 2026-09-22 (1 drained, cross-epic)

- **`truthful-signals-001.md` promoted to the global corpus as `2026-09-22-08-004`**
  (`plan-marshall:persona-module-tester`, anti-pattern). Cross-epic candidate-lesson forwarded
  from the `truthful-signals` orchestrator epic: a monkeypatched resolver makes every fixture
  constant on its far side vacuous — a production element was reclassified mid-PR, and the
  fixture kept passing because the resolver that would have surfaced the reclassification was
  mocked out. `truthful-signals` routed ownership here (its house-style/test-conventions scope)
  rather than staging it on either side, since it already holds a version as evidence inside its
  own `PLAN-TRUTH-153`, which cannot absorb further items without a split. Promoted rather than
  folded/staged: neither of this epic's two staged specs (PLAN-140, PLAN-181) owns
  house-style/`test-conventions` surface, and promotion to the global corpus is this epic's
  established disposition for a standalone rule candidate — it is picked up by the standards
  plan / `plugin-doctor` `test-conventions` scope work the epic Vision already calls for, same
  as the 5 promotions from the PLAN-177 drain above. Source inbox lesson `2026-09-19-21-006`
  (already retired from the global corpus by the time this drained). Archived on consume.

### Cleanup 2026-09-22 (corpus pass, A1–A5)

- **A1 — 11/11 claims re-grounded at HEAD `7d82d5d90`.** 6 contradicted (PLAN-140 claims
  0/1/2/3/5/6), 4 corroborated (PLAN-140 claim 4, PLAN-181 claims 0-2), 1 unverifiable-by-design
  (PLAN-140 claim 7). Whole-tree test-module-line-budget moved **362 → 429** since the last
  cleanup (+18%); `_test_shape_scan.py` moved **636 → 979** lines. Full verdicts and evidence are
  stamped on the specs via `corpus set-verdict` (producer `test-quality/cleanup`) — not
  duplicated here.
- ⛔ **The restructure commit `7d82d5d90` (#1578, "restructure epics into a fresh live/archived
  split") deleted this epic's `landings/` directory and archived every staged sibling spec except
  PLAN-140 and PLAN-181.** Two consequences surfaced by the re-grounding pass:
  - PLAN-140 claims 1 and 2 (epic-surface-partition attribution against sibling plans' surfaces)
    went from *corroborated*/*contradicted-with-real-numbers* to **structurally VACUOUS**:
    `not_derivable` is now 1335 of 1337 modules, because PLAN-030/040/050/080/155/165/020 no
    longer have specs in `plans/` to attribute against. This is a **re-scope owed, not a
    re-measurement** — the claims cannot be meaningfully re-checked as written until the corpus
    carries specs to attribute against again. Left staged and reported, not silently re-derived.
  - PLAN-140 claim 6's citation (`landings/PLAN-100.md:52-53`) went dangling — the file no longer
    exists at HEAD. The underlying historical fact is intact (confirmed via
    `git show 7d82d5d90^:...`); the citation is re-pointed in the verdict to
    `archive/100-module-budget-campaign/report-01.md`.
  - **Broader corpus-hygiene defect, unowned by this pass**: `settled.md` carries `landings/PLAN-NNN.md`
    cross-references for PLAN-105, PLAN-110, PLAN-135, PLAN-145, PLAN-150, PLAN-155 and PLAN-170
    that are now equally dangling for the same reason. Re-pointing all seven is a bounded editorial
    task outside this cleanup's A1 scope (A1 re-grounds staged specs, not `settled.md`) — recorded
    here rather than fixed silently. Stage on demand or fold into the next pass that touches
    `settled.md`.
- **A2/A3 — no findings.** Both staged specs carry Objective, Expected Surface and Claim Labels;
  neither is already-fixed.
- **A4 (duplication) — declined, no supersede applied.** `corpus cross-check` reported
  `collision_detected: true` with 47 `file_overlap_matches`, all against PLAN-181's single
  declared path `test/plan-marshall/tools-permission-fix/`. Reviewed all 47: 46 are containment
  false-positives from sibling specs' broad `test/plan-marshall/` directory-level declarations
  (unrelated doc/consistency sweeps across active and archived epics); the one exact-file match —
  `truthful-signals-26-09-21/PLAN-TRUTH-103` (`overlap_count: 2`, naming both carve-2 files) — is
  **archived residue from a pre-restructure snapshot**, absent from the live `truthful-signals`
  queue (which now starts at PLAN-TRUTH-145). No live plan besides PLAN-181 claims these files.
  `candidate_comparison_determinate: false` (93 sibling-epic specs + 2 live plans + PLAN-140 itself
  indeterminate) is a corpus-wide declaration-completeness gap in OTHER epics' specs, not
  actionable from here.
- **A5 (distribution) — declined.** Population is 2 specs, already single-component/task; no
  redistribution warranted.
- **Declared-surface half (A1, second reader) — no correction needed.** PLAN-140 stays `derived`
  by design (explicit union-of-other-plans declaration, permitted to stand per its own header);
  PLAN-181 stays `declarative` with its one claimed path matching its narrative — no understatement.

### Added by PLAN-181's landing (#1582, 2026-09-22)

- **PLAN-181 SHIPPED — carve 2 of slice-060 (tools-permission-fix) landed as
  #1582 (merge `1a9a67229`, `origin/main` tip at the drain).** All five deliverables
  reconcile against the corroborated diff and tree: D1 re-derived 2 over-budget
  files (1618, 1587) matching the nomination shape; D2 hoisted
  `_permission_fix_fixtures.py` (198) + 10 `test_*` splits (max 382), 2 originals
  deleted, 13 files +3279/−3205; D3 pytest 141 preserved both orders, AST 124
  preserved — `_fidelity_diff` lost=124/gained=124 on path-qualified identities is
  the file-move axis (`Class::test` preserved), duplication + banner introduced=0
  (2 pre-existing banner fixes) — the spec's letter "lost=0/gained=0" is unmet **by
  instrument path-sensitivity** (disclosed, filed to process-compliance; substance
  intact → **shipped-modified**); D4 doctor `test-conventions` error-0 (budget 0,
  down from 2), CI 10/10 green; D5 Tier M clean (`skip-bot-review` label, CodeRabbit
  skipped, Sourcery 1 nitpick triaged FIX → re-review DISMISSED→APPROVED via `ci pr
  reviews`, thread cleared). Landing message arrived `complete: true` (all 9
  required facts; the 4 `steps` parsed by last-colon split:
  `ship-pr-1582` / `verify-in-worktree` / `merge-queue` / `branch-cleanup` all
  `done`; `surface_delta` unmeasured — declared/realized not supplied, an optional
  key). Row: `shipped`, pr `#1582`, `plan_marshall_plan_id`
  `run-3-carve-2-tools-permission-fix`, landing `landings/PLAN-181.md`.
- ✅ **The PLAN-181 emit gate override is vindicated.** The 47 overlap rows disposed
  inert at the A4 pass stayed inert end-to-end: carve 2 touched exactly its one
  declared path and no live sibling moved against it. Same mechanism as the
  PLAN-165 vindication — the safety rested on the live-corpus read at emit, not a
  judgement that the overlap "looked unlikely".
- **Watch added — ruff-format unenforced on merge-queue triage heads.** The 3-line
  format churn (commit `ade0e8ee2`) was frozen out by GH006 (head frozen once the
  PR queued), CI stayed green without it, and the churn was dropped with the local
  branches — so `ruff format` findings can silently vanish from merged PRs. WS-03
  candidate (harness/CI gap). *Re-check at: the next landing; stage on demand.*
- **Token figure `0` read as unmeasured, not zero** — same convention as PLAN-180;
  no per-phase token/duration figures surfaced in this lane.
- **Pre-existing, carried:** PLAN-140 parked (claims 1/2 re-scope owed; operator
  disposition pending); 7 dangling `landings/` refs in `settled.md`; operator's
  commit-scope decision on 103 uncommitted paths (5 epic-own). Carve 3
  (tools-permission-doctor) remains unstaged per the just-in-time discipline —
  the next emission's candidate when the operator orders it.
