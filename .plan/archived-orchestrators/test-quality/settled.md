# Settled — test-quality

> Relocated narrative for one epic. Every section here had a **closed subject** when it was
> moved: a resolved defect, a refuted finding, a superseded observation. Bodies are moved
> **verbatim** and never dropped — a retraction is the anti-rework record, and the whole point
> of relocating rather than deleting is that the next reader can still find out why a line of
> enquiry was closed. `epic.md` carries a pointer at each origin naming the heading here.
>
> This file is narrative only. `status.json` remains the machine authority.

## The refuted partition residual

Relocated from `epic.md` § Open Defects.

- ✅ **RETIRED — REFUTED by PLAN-120's landing.** This entry read: *"the partition residual is now LIVE …
  `test/pm-plugin-development/cloud-plan-lane/` is claimed by **no** spec."* **That was wrong.** The
  derivation reports `unclaimed: 0` whole-tree, and that module is claimed by **PLAN-080, PLAN-110,
  PLAN-130, PLAN-135 and PLAN-140** — PLAN-080's Expected Surface carries a recursive
  `test/pm-plugin-development/**` glob that covers it. The defect was manufactured by a **grep for the
  literal directory token**, which cannot see a claim expressed as a recursive glob. The refutation is
  kept rather than deleted: the epic commissioned a derivation precisely because hand-checks like that
  one are unreliable, and this is the derivation's first act — overturning the orchestrator's own finding.

## The conformance-drift watch's second firing

Relocated from `epic.md` § Watches. Superseded by the third-firing entry, which remains live there.

- ✅ **The conformance-drift watch above has now fired a second time, and it is no longer a hypothesis.**
  Between `3bc01075` and `77db1a0d` an unrelated epic landed `test_build_gate_lockstep.py` (740 lines) in a
  **new** directory inside PLAN-080's slice tree, moving three separate rule populations at once. The
  mechanism the watch predicted is confirmed: rules at `severity: warning` let a non-conforming new module
  land unremarked. ⛔ *Correction: this entry originally also claimed the module created "the epic's first
  unclaimed directory". PLAN-120's derivation refuted that — see the retired Open Defect. The drift is
  real; the unclaimed-directory half was wrong.* *Re-check at: every landing.*

## PLAN-070's unfinished B6 namespace conversion

Retired from `epic.md` § Open Defects at the PLAN-150 landing. The subject is closed: PLAN-150
shipped as #1383 and converted the architecture slice outright.

The entry read: **PLAN-070's D3 B6: ~506 hand-built namespaces against 1 `parse_ns` call**, no
follow-up dispatched. → **PLAN-150**

What actually closed it, measured and carried on PLAN-150's own landing payload: hand-built
`Namespace` **547 → 1** (one named seam-blocked site), `parse_ns` **1 → 78** all at module or
fixture scope, `SimpleNamespace` **13 → 13** (correctly out of scope), collected items
**3905 → 3909**, blocked sites **0**. 47 modules across the slice.

⛔ **The `~506` figure in the retired entry was already stale when written** — the re-derivation
PLAN-150's gating D1 performed returned **547**, +41 against the recorded lead. That is why the
spec required a re-derivation rather than permitting the stored figure to be executed, and it is
the standing reason no campaign figure in this epic may be run from a stamped number.

See [`landings/PLAN-150.md`](landings/PLAN-150.md).

## The single-bucket attribution defect

Retired from `epic.md` § Open Defects at the PLAN-170 landing. The subject is closed: PLAN-170
shipped as #1385.

The entry read: the derivation returned **multiply_claimed 1057 | not_derivable 0** of 1059
modules, with the budget attribution collapsing into a single `<multiply-claimed>` bucket holding
all 279 findings — caused by **seven whole-tree `test/` root claims** across five specs, of which
PLAN-130's and PLAN-135's are by construction, PLAN-105's needed adjudication, PLAN-120's was a
parse artifact, and **PLAN-160 contributed `test/**` three times over**. → **PLAN-170** (staged)

What closed it: PLAN-170 resolved each Expected-Surface entry's shape independently of the spec
class and gave the partition a sweep-plan concept. Attribution went **26 → 645** of 1075 modules
across 8 owning-plan buckets, and `unclaimed` is **0**.

⛔ **Two premises of the retired entry did NOT survive, and both are recorded rather than carried
forward silently:**

1. **The `PLAN-160 contributes test/** three times over` clause is refuted.** Those three entries
   are authored as `HYPOTHESIS: … (verify-at-outline)`, and the shipped
   `epic-surface-derivation.md` entry-class table makes a deferred hypothesis a **lead**, never a
   claim. `epic-surface-partition classify` honours that and returns `shape: lead` for all three.
   PLAN-160's spec is correctly authored and owes no surface correction.
2. **The contested/multiply-claimed figure is not a stable property.** See the live Open Defect:
   retirement resolves active-vs-terminal and nothing resolves terminal-vs-terminal, so the count
   moved 12 → 186 on two `shipped` transitions alone.

See [`landings/PLAN-170.md`](landings/PLAN-170.md).

## PLAN-090's narrower D1

Retired by refutation at PLAN-145's landing (#1395, merged `8d8c17bd`).

The defect as recorded: *"PLAN-090's D1 was narrower than what was routed to it. Its brief called
for a tree-wide `ParserSeamNotFound` derivation; its report declined it. `effort_presets.py` and
`manage_terminal_title.py` still have no seam."*

PLAN-145's D1 performed the derivation PLAN-090 declined. Of **118** entry-point scripts under
`marketplace/bundles/`, **113** reach a parser seam and the **5** that raise `ParserSeamNotFound`
are each a deliberate shape: `platform_runtime.py` is a dispatch router whose raise is pinned as
the intended contract by a passing test, three are stdin-driven hooks with no argv contract, and
`plan_logging.py` is import-only. **Modules owed a `build_parser()` seam: 0. `parse_ns` sites
unblocked: 0.**

Both named starting points were checked independently at HEAD `09f92b5e`: `manage_terminal_title.py`
carries zero argparse / `main()` / `build_parser` hits, and `effort_presets.py`'s only two are
docstring mentions at lines 379 and 381. Both belong to D1's *no top-level CLI* class.

**The distinction that matters for a later reader**: the defect was correct that PLAN-090's
derivation was narrower than its brief. It was wrong that seams were owed. A gap in a derivation is
not evidence of the thing the derivation would have found — and this entry is the epic's clearest
instance of that shape.

The result is no longer prose: `test/test_parser_seam_coverage.py` (526 lines) re-derives the whole
population on every run, with the five exempt shapes pinned as recorded verdicts, so the roster
cannot go stale undetected. Two CodeRabbit findings hardened that guard before it merged —
`ad7796` (the collector recorded only definition nodes, missing an import-published seam) and
`4fa036` (drift was computed both ways but only printed).

## The budget metric's helper-module blind spot

Closed by PLAN-105 § D3, shipped in #1407 (merged `bf1b7ed6`).

- **The budget metric is blind to helper modules** — it filters on `_is_collected_module`, and run 1
  created 66 helpers. A falling count is not evidence lines left the tree. → **PLAN-105 § D3**

At `bf1b7ed6` `analyze_test_module_line_budget` states it measures every module the test tree carries,
collected and helper alike, and 7 non-`test_`-prefixed files (`conftest.py` plus 6 underscore fixture
modules) appear among the 330 line-budget findings. ⚠️ **The consequence for later readers**: budget
counts are NOT comparable across `bf1b7ed6` — a rise at that landing is partly newly-visible population
rather than new debt, and PLAN-140's D1 must separate the two before sizing any campaign run.

## Both ADR subjects from PLAN-120, dispositioned

Settled. Retained in full because the case assembled here is the standing argument for ADR-019, and a
later reader must not re-propose either subject believing it was overlooked.

- ✅ **RESOLVED — both ADR subjects from PLAN-120 are dispositioned.** `adr-propose`
  proposed them, but the step mandates operator confirmation and a dispatched leaf cannot fire
  `AskUserQuestion`, so they were neither created nor discarded as "none proposed" (which would have
  been false). Recorded at `archived-plans/2026-08-25-derive-the-partition-and-the-budget-attribution/logs/decision.log:114`,
  decision `9544c2`:
  1. ✅ **CREATED as ADR-019** (`doc/adr/019-An_audit_separates_what_it_could_not_evaluate_from_what_it_evaluated_and_found_wanting.adoc`,
     status **Proposed**), positioned as the general rule of which ADR-009, ADR-014 and ADR-017 are
     domain-scoped instances. Supersedes none of them.
  2. ✅ **DISCARDED on an operator decision.** *"A declared path is matched, never opened"* — no draft
     file was ever written, so nothing but the title survived; there was no content to evaluate, promote
     or recover. Recorded as discarded rather than deleted so a later reader does not re-propose it
     believing it was overlooked.

  ⛔ **Only the titles survive — no draft file was written**, so these are recoverable as *subjects*,
  not as documents. ⚠️ **Subject 1 is this epic's own recurring theme stated as a principle**, and the
  case for it is already assembled here: the `not_derivable`-vs-`unclaimed` distinction PLAN-120 was
  built to preserve; `scope_creep_check` returning `residual_count: 0` on `no_baseline_sha`; scoped
  `plugin-doctor` reporting clean over rules it structurally cannot reach; `sonar-roundtrip` reporting a
  gate it never ran; `search --content` returning a false zero on a regex metacharacter;
  `analyze-logs` reporting `build_count 0` against 84 recorded calls; `manage-logging read --phase`
  returning an empty set for a phase with 126 entries. **Seven independent instances, and this
  orchestrator added an eighth** by reading one negative lookup as "the plan directory was deleted".
  If any ADR in this repository is owed, it is that one. → **operator**

## The un-gated concurrent pair, PLAN-105 and PLAN-145

Retired at PLAN-105's landing: both plans landed and no collision ever occurred. ⚠️ **The structural gap
this watch exposed is NOT settled** — a plan resumed from `parked` still re-enters flight through a path
with no admission test, and that remains live in `epic.md`. What is settled is this specific pair.

- ⛔⛔ **TWO OVERLAPPING PLANS ARE CONCURRENTLY IN FLIGHT, and the disjointness gate never saw the
  pair.** PLAN-105 and PLAN-145 are both `running`. Their DECLARED surfaces overlap on at least two
  entries — both claim `marketplace/bundles/` at root (PLAN-105 bare, PLAN-145 as `**`) and both
  claim `test/plan-marshall/`. The gate is not at fault and did not fail: **it was never consulted**,
  because PLAN-145 was resumed directly on an operator disposition rather than emitted through a
  `next` round, and `next` is the only surface that runs the disjointness test. ⚠️ **This is the
  structural gap, not the incident**: a plan resumed from `parked` re-enters flight through a path
  that has no admission test at all, so `parallelization_scope` and surface-disjointness both bind
  only on the emit path and neither binds on the resume path. The knob now reads N=2 with R=2 — the
  epic is at its concurrency cap, reached without the gate.
  ✅ **RETIRED — both plans have landed and no collision ever occurred.** PLAN-145 merged first as
  `8d8c17bd`; PLAN-105 rebased onto it (two rebases onto a moving `origin/main`, both clean on the
  overlap) and merged as `bf1b7ed6`. The un-gated concurrent pair cost nothing. ⚠️ **That is a
  favourable outcome, not evidence the gap is harmless** — the pair was never checked, and the
  measurement the watch was opened to take is the more useful result: both declarations turned out to
  be unusable by the gate, in opposite directions. Reported at
  [`landings/PLAN-145.md`](landings/PLAN-145.md) and [`landings/PLAN-105.md`](landings/PLAN-105.md);
  the standing finding is the declaration-form entry at the top of this section. The resume-path gap
  itself — `parallelization_scope`, disjointness and prep-readiness all bind on the emit path only —
  remains open in the watch below.

## The shipped-accessor gap

`load_skill_module` and `load_script_module` landed in PLAN-090 for a shape PLAN-060 had named as
blocking, and the sweep that would use them was never done. Carried as an Open Defect at
**110** preamble findings / **15** `subprocess-pythonpath` (HEAD `00b92fca`), re-derived to
**103** / **17** at merged main `681db9446` before launch.

✅ **RETIRED — closed by PLAN-135 (#1446, merge `b64db667`).** `test-module-preamble-boilerplate`
**103 → 13**; `subprocess-pythonpath` **17 → 5**. Both figures were re-derived by the landing
analyze at the merge commit itself with a clean worktree, not transcribed from the plan's
narrative, and both matched exactly. The residual 13 is a **derived structural floor**, not a
leftover: 11 sites across 4 classes no shipped accessor can reach, plus the 2 `test/conftest.py`
occurrences the plan's declared exclusions forbade it from touching. Every one of the 13 carries
`kind: spec_from_file_location`, so the `Path(__file__)` parent-chain shape is genuinely at **0**.

⚠️ **The 5 residual `subprocess-pythonpath` rows are error-severity and keep the whole-tree
`test-conventions` gate at `status: fail`.** They are confirmed rule false positives, filed for
WS-03 and deliberately not suppressed. The gate goes green when the rule is fixed, not when
another sweep runs. Reported at [`landings/PLAN-135.md`](landings/PLAN-135.md).

## Circular ownership on three preamble sites

PLAN-070's report named PLAN-090 as owner; PLAN-090's named PLAN-070. Both closed, all three sites
still raw — the defect had evidence that nobody was going to do them.

✅ **RETIRED — closed by PLAN-135.** All three contradiction sites
(`test_gradle_discover_modules.py`, `test_npm_discover_modules.py`,
`test_extension_implementations.py`) were converted, taken first as the spec directed. The
`KNOWN_REGISTRATION_COLLISIONS` guard held unchanged at 17 names — no baseline was widened to
accommodate the work.

## The ci-wait dated-provenance violation

`fixtures/ci-wait/README.md` carried a plan slug, a lesson id, two TASK ids and a dated line — a
direct documentation-standards violation.

✅ **RETIRED — closed by PLAN-130 § D7 (#1436).** ⚠️ Recorded here because the ledger carried the
retirement inconsistently for one cycle: the PLAN-130 landing section reported it closed while the
Owned list still pointed at § D3. The discrepancy was surfaced by a `status` report and reconciled
at the PLAN-135 landing. The lesson is about the ledger, not the defect: a retirement recorded in a
landing section is not a retirement until the Owned entry is relocated in the same act.

## PLAN-060's D4 parametrization families

~223 parametrization families across the runtime/script-substrate slice, plus a cold read PLAN-060
declared necessary and never performed. Carried for the whole epic as the **largest single item with
no owner anywhere**.

✅ **RETIRED — closed by PLAN-155 (#1455, squash-merged `9853a7aba`).** 97 files, every one of them
inside the fourteen declared slice directories. The cold read was not merely performed but
**widened from the spec's 40-family sample to a full sweep**, because the sample surfaced 11 defects
across 8 families and so disqualified itself as a stopping point; the full sweep found 6 more
families, including a second instance of the `ids=`-derived-from-a-foreign-object hazard that
mislabels silently on reorder. The repair pass then followed the audit's findings rather than the
pre-computed step list, which carried repair steps for only 2 of the 8 flagged files.

⚠️ **The collapse invariant is an unverified lead in this ledger.** Collected pytest items
20,766 → 20,954, non-decreasing at all eight measurements with skips unchanged at 8, is what makes
"collapsed" distinguishable from "deleted" — and establishing it requires running the suite, which
is outside the orchestrator's boundary. The landing analyze did not check it. Reported at
[`landings/PLAN-155.md`](landings/PLAN-155.md).

## The residual skips, answered

> Relocated from `epic.md` at the 2026-09-09 cleanup. Verified at HEAD `1c4e6febb`; the subject is
> closed and this record carries its own do-not-re-derive instruction.

The question "why are there still disabled tests, and can they be removed?" is answered here once, from
ground truth, so no later cycle re-derives it. Verified at HEAD `1c4e6febb`.

**10 of the 11 are one uninstalled binary, and they must not be removed.** `pyright-langserver` is
absent on this machine (`which` finds nothing; `npm ls -g` is empty). Four guard sites carry all ten
nodeids — one **module-level** `pytestmark` covering seven tests in
`test/plan-marshall/lsp-client/test_lsp_integration.py`, two decorators in `test_lsp_harvest.py`, one in
`test_lsp_harvest_search_path.py`.

⛔ **Deleting them would delete the suite's only real-language-server evidence.** PLAN-110 already
extracted the one branch a fake *could* cover — `preflight` reaching `STATE_READY`, the sentinel every
consumer gates its LSP path on — and moved it onto a fake subprocess server in `test_lsp_client.py`. The
remaining nine are real-server assertions a stub cannot stand in for. **The remedy is to install, not to
delete:**

```bash
npm install -g pyright
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config language-server set \
  --language python --command '["pyright-langserver", "--stdio"]' --language-id python
```

(the binding form is `doc/user/lsp-code-intelligence.adoc:47`.) It is **deliberately not in
`REQUIRED_TOOLS`** — its absence is an ordinary environment difference, not a broken environment, so
promoting it there would fail every run on every machine that does not install it. The cost is real and
is an operator call, not a plan's: a Node binary on every runner, and three of the four sites are among
the suite's slowest tests. That is exactly why PLAN-110 recorded a proposal rather than taking it.

**The 11th is genuinely removable.** `test_refusal_recovery_arming.py:867` skips when
`bot_registry.refusal_patterns(bot_kind)` is empty — true only for `cuioss-review-bot`, which declares no
observed refusal phrasing. The population is registry-derived by design (no bot-name literal in the
path), so the skip is data-driven rather than environmental. Remedy, which trades one skip for two
positive assertions and leaves the totality check untouched:

1. Parametrize only over bots that declare refusal patterns.
2. Add one explicit test asserting **which** bots declare none — the fact currently expressed as a skip
   reason becomes an assertion the suite defends.

⚠️ Inventing a refusal phrasing for `cuioss-review-bot` is **not** an option: the registry records
*observed* wordings, and fabricating one to clear a skip would corrupt the discriminator that
`2026-09-04`'s size-refusal work exists to feed.

**The three `pytest.mark.skipif` in `test/plan-marshall/tools-file-ops/test_tree_copy.py` are not a
gap.** All three gate on `sys.platform == 'win32'` (symlink semantics), so they never fire on the
reference platform and contribute zero skips. `test/conftest.py:1282` already states that on a platform
where they DO fire the gate names them and the list is extended deliberately. Nothing owed.

- ⚠️ **A second population the skip count cannot see: `collect_ignore`.** `test/conftest.py` still
  excludes **3 whole modules holding 5 tests** — `test_scan_marketplace_inventory_smoke.py` (2),
  `test_scan_planning_inventory_smoke.py` (1), `test_resolve_dependencies_smoke.py` (2). They are never
  *collected*, so they never appear as skips, and **run condition 3 reports clean over them**. ⛔ This is
  not a claim the exclusions are wrong — each is individually reasoned (real-tree smokes whose
  per-filter and per-subcommand coverage lives in the in-process synthetic units beside them), and
  PLAN-110 removed a fourth entry when it could. It is that the epic's headline "the suite reports zero
  unexplained skips" measurement **has a second door it does not watch**, and the 5 tests behind it are
  invisible to the very instrument PLAN-110 built. *Re-check at: whether the zero-skip gate should also
  assert the `collect_ignore` list against a named, reasoned allow-list — the same shape as
  `_SKIP_EXCEPTIONS`, which is the pattern that already works.* → unowned.

## The sweep set is three, not two

> Relocated from `epic.md` at the 2026-09-09 cleanup.

- ⛔ **The sweep set is three, not two.** PLAN-170's broadened own-words sweep declaration reads
  PLAN-110's "crosses several reduction slices deliberately" statement, so `sweep_plans` is now
  **PLAN-110, PLAN-130, PLAN-135**. Any epic reasoning that assumed exactly two sweeps is stale.
  *Re-check at: the next `cleanup` re-grounding pass.*

## Finalize cost is the dominant term

> Relocated from `epic.md` at the 2026-09-09 cleanup.

- ⛔ **Finalize cost is the dominant term and nothing bounds it.** PLAN-170 spent **4,000,238 of
  6,431,582 tokens — 59%** in `6-finalize` on a 15-file change, tripping all four fallback ratio
  thresholds with `retryable_total_tokens: 0`, so none of it is infrastructure retry. PLAN-150
  spent 130,209 tokens on a single malformed dispatch. *Re-check at: every landing; two
  consecutive landings above 50% should graduate this into a defect.*

## The 12 contested modules

> Relocated from `epic.md` at the 2026-09-09 cleanup.

- **The 12 contested modules are a standing scheduling question, not a derivation defect.**
  Corroborated exactly against a live `partition --epic test-quality`: PLAN-155+PLAN-165 (10
  modules under `test/plan-marshall/manage-providers/`, retired PLAN-060), PLAN-150+PLAN-160
  (`test_dynamic_mypypath.py`, retired PLAN-070), PLAN-155+PLAN-160
  (`test_conftest_loader_contract.py`, retired PLAN-060+PLAN-090). Lifecycle narrows the
  competing set and deliberately never picks a winner among live plans. *Re-check at: every
  `next`, which must sequence rather than pair these.*

## Slice-conversion specs under-declare test/conftest.py

> Relocated from `epic.md` at the 2026-09-09 cleanup.

- ⛔ **Slice-conversion specs systematically under-declare `test/conftest.py`.** PLAN-150 touched
  it (+12 lines, the shared `parse_ns` helper) while declaring 29 paths all under
  `test/plan-marshall/`. PLAN-155's identical declaration was corrected in the same act as this
  landing's reconciliation. The pattern — a mechanical conversion adding its shared helper to
  the tree-root conftest — will recur on any further slice plan. *Re-check at: the staging of
  any new conversion spec, before its first `next`.*

## Added by the PLAN-170 + PLAN-150 double landing (2026-09-03)

- ⛔ **`direct-gh-glab-usage` cannot observe the bypass it exists to catch.** PLAN-170 called
  `gh pr view --json body` twice, because `ci pr view` exposes no `body` field — a hard-rule
  violation the plan self-reported. The detector reads `work.log` and `script-execution.log`;
  a raw Bash call reaches neither, and a `decision.log` self-report reaches neither. **The same
  shape recurred in this orchestrator session**, which used shell loops and multi-command Bash
  calls against the "one command per call / no shell constructs" hard rule: the PreToolUse R1
  gate is context-gated to a plan context, and an orchestrator session is not one. A rule whose
  only enforcement is context-gated is unenforced everywhere outside that context. Unowned —
  the missing `body` field is separately tracked as corpus lesson `2026-09-03-02-002`.
- ⛔ **A plan's retrospective can route its lessons past the epic that owns it.** PLAN-170's
  retrospective was dispatched with `orchestrated: false` without running the required
  resolution, so its 12 lessons went to the global corpus instead of this epic's inbox. Not
  lost, but not delivered through the intended channel — and the epic cannot disposition what
  it never receives. Corroborated: the inbox held exactly one PLAN-170 message (the landing)
  and no candidate-lessons. Unowned.
- ⛔ **The `2026-09-03-02-00X` lesson batch carries empty `component` and `category`.** Nine
  lessons, all unattributed, so `consult` cannot surface them for any component. This is the
  same producer gap PLAN-170's residue reports for `2026-09-02-15-001` — a lesson the corpus
  could enumerate but not address. Unowned.
- ⛔ **Two review-verdict defects, two halves of one end-to-end gap, to be scheduled together.**
  `cc3ce9` (detection): the `automatic-review` noise pre-filter consumes CodeRabbit's
  clean-review publish shape, so a bot that reviewed cleanly scores `absent`, and re-firing
  re-filters the same comment identically so the loop cannot converge. `cf3722` (transport):
  even when participation IS detected, nothing persists `bot_states` where the order-990
  post-merge review-retrospective can read it, so its grade is structurally always
  `indeterminate`. PLAN-150 merged past `cc3ce9` on a HEAD-bound `barrier-ask-override` grant
  carrying the evidence, not by forcing the step. Unowned.
- **`198a01` — the `_variant` helper is duplicated byte-identically across 38 test modules**
  (~500 lines). `conftest.py` already owns its sibling `parse_ns` and already imports `copy`
  and `Any`. Consolidating means one shared helper plus ~230 call-site renames plus per-file
  import pruning: plan-sized, deferred by PLAN-150 deliberately, and **not staged** — staging it
  speculatively is the over-planning the cleanup contract warns against. Stage on demand.
- **The measurement-instrumentation cluster is accumulating but is OUT OF THIS EPIC'S SCOPE.**
  Four corpus lessons now carry repeat observations from this epic's plans —
  `2026-08-25-09-004` (context-load columns + `enrich`), `2026-08-25-09-009` (build attribution
  lost to `NO_PLAN`), `2026-09-02-13-005` (`[VERIFY]` emission), plus `2026-09-02-13-002`. They
  are one coherent, bounded piece of work: make the plan machinery's own measurement
  trustworthy. This epic is "house style and reduction of the Python test corpus", so staging
  it here would be scope creep. Recorded so the signal accumulates in one place and a future
  epic can pick it up whole. As PLAN-170's residue puts it: retention is not an application
  mechanism — nothing downstream converts a repeatedly-retained lesson into work.


## Watches added by the same double landing

- ⛔ **The derivation now reads plan lifecycle from this epic's `status.json`.** PLAN-170 gave
  the partition its first input that is not the spec corpus, which makes the ledger's per-plan
  `status` field a machine consumer's contract: a status value beyond
  `landed`/`shipped`/`staged`/`running`/`parked` raises `unknown_plan_status` rather than being
  absorbed. That coupling did not exist before. ⚠️ It compounds an already-recorded defect —
  `queue --transition` performs **no enum validation** on `--status`, so the ledger can be
  written into a state the derivation will then refuse. *Re-check at: any change to the status
  vocabulary, and at the next `cleanup`.*
> ↪ Relocated to `settled.md` § "Finalize cost is the dominant term" — the direction REVERSED. The watch asked to graduate this to a defect on two consecutive landings above 50%; instead finalize/execute has come in below 1.0x three consecutive times (0.91x, 0.90x, 0.75x, monotone decreasing). Retired by refutation, not by resolution.
- ⛔ **Required-versus-optional bot status does not track measured yield, and there are now two
  opposed data points.** On PLAN-170, CodeRabbit — OPTIONAL by project default — produced both
  actionable findings while pr-agent, the sole default-required bot, participated twice and
  found nothing; the run overrode the lists plan-locally. On PLAN-150, all three external bots
  found nothing and `pre-submission-self-review` found 4 real defects. Sourcery refused on both
  PRs on a stated cap of 150,000 diff **characters** measured against 4,906 and 4,086 changed
  **lines** — units that do not compare, a refusal firing two orders of magnitude early.
  *Re-check at: the next landing; the remedy is staged as corpus lesson `2026-09-03-07-003`,
  which asks for per-source yield to be recorded before the required list is re-decided.*
> ↪ Relocated to `settled.md` § "The 12 contested modules" — all three named pairs have collapsed: PLAN-150 and PLAN-155 have both shipped, so PLAN-155+PLAN-165, PLAN-150+PLAN-160 and PLAN-155+PLAN-160 no longer name two live plans.
> ↪ Relocated to `settled.md` § "The sweep set is three, not two" — all three named sweeps (PLAN-110, PLAN-130, PLAN-135) have now SHIPPED, so the re-check the watch asked for has no live subject.
> ↪ Relocated to `settled.md` § "Slice-conversion specs under-declare test/conftest.py" — REFUTED by PLAN-155. The watch predicted the pattern would recur on any further slice plan; PLAN-155 was exactly that, DECLARED `test/conftest.py`, and realized 97 of 97 files without touching it.


## Defect found by verifying the PLAN-170 landing rather than recording it

- ⛔⛔ **The shipped derivation's contested set does not mean what PLAN-170's landing says it
  means, and the refutation arrived on the very next landing — its own.** The landing claims
  "the 12 survivors are exactly the class the derivation refuses to adjudicate — modules
  claimed by two or more ACTIVE plans." Measured at three lifecycle states in this
  reconciliation: with PLAN-150 and PLAN-170 at `running`, contested was **12**, matching the
  claim exactly. After transitioning both rows to `shipped`, contested became **186**. The
  pair tally names the cause: **175 of 186 are `PLAN-070,PLAN-150`**, and the derivation's own
  `lifecycle_plans` mapping reports BOTH as `terminal` (`landed` and `shipped`). Another,
  `PLAN-060,PLAN-090`, is terminal-vs-terminal too. **Only 11 involve two active plans** —
  PLAN-155+PLAN-165 (10) and PLAN-155+PLAN-160 (1).

  The mechanism is a missing rule, not a bad status mapping: retirement resolves
  **active-vs-terminal**, and nothing resolves **terminal-vs-terminal**, so when both
  claimants are terminal neither retires the other and every shared module becomes contested.
  That is the *normal* case for a follow-up plan finishing its predecessor's slice — exactly
  what PLAN-150 did to PLAN-070's unfinished **B6** deliverable — so the contested set will
  now grow monotonically with every slice plan that lands, and the headline figure degrades
  as the epic succeeds.

  ⚠️ **Consequence for this ledger:** the `contested` count is not usable as an epic health
  metric until this is fixed, and any figure quoted from it must state the lifecycle state it
  was measured at. The number `next` sequences on is **11**, not 186 and not 12. Unowned —
  candidate for a follow-up to PLAN-170 in WS-06, not staged speculatively.
- **`corpus cross-check` is still matcher-blind to containment; PLAN-170 did not change that,
  and its own residue says so.** PLAN-170 fixed the PARTITION (a whole-tree claim no longer
  erases slice ownership — PLAN-160's three `test/**` entries now surface as `root_claims`
  rather than swallowing the tree). It did **not** fix the disjointness GATE: the file-overlap
  matcher still compares normalized paths exactly, so `test/**` matches only a literal
  `test/**`. Lesson `2026-08-25-09-016` was re-examined during PLAN-170 and deliberately
  retained for this reason. Every `next` in this epic must therefore keep checking containment
  by direct claimed-set read, and must not read the matcher's silence as disjointness.


## Added by PLAN-105's landing (#1407, 2026-09-04)

- ⛔⛔ **THE DECLARATION FORM IS THE ROOT CAUSE, and all THREE of its failure modes are now measured.**
  PLAN-145 realized **0 of 3** files inside its declaration; PLAN-105 realized **514 of
  521 (98.7%)** inside its own; PLAN-110 realized **16 of 29 (55.2%)**. None is a usable input to the
  disjointness gate:

  | | PLAN-145 | PLAN-105 | PLAN-110 | PLAN-130 |
  |---|---|---|---|---|
  | Declared | 5 narrow entries | 10 entries, two of them whole trees (`test/`, `marketplace/bundles/`) | 15 entries + 1 explicit exclusion | 9 entries, `test/` at ROOT |
  | Realized inside | 0 of 3 | 514 of 521 | 16 of 29 | **112 of 112** |
  | Declared entries realized | 0 of 5 | — | 8 of 15 | 8 of 9 |
  | Gate consequence | invisible collisions | **no discriminating power** — everything collides, the slot can never be filled | reads ~half the real surface, and looks clean doing it | **no discriminating power, again** |

  ⛔ **PLAN-130 (#1436+#1435, 2026-09-07) is mode 2 repeating, and a 100% figure is exactly as
  useless to the gate as a 0% one.** Nothing it did *could* land outside a root `test/` claim. This
  is the concrete, measured reason the epic has run strictly one plan at a time: every pairing check
  since has returned "collides" against that claim, and the collision was never real contention.

  ⛔ **PLAN-110's landing (#1426, 2026-09-06) RETIRES "accurate AND narrow" as the remedy.** That pair
  was named below as jointly sufficient. PLAN-110's declaration is the first in this epic that is
  honest on both axes — no root-tree claim, a real exclusion, entries the plan genuinely expected to
  touch — and the gate **still under-read its surface by 45%**. The cause is structural, not
  sloppiness: a path list enumerates *where the plan expects to work* and cannot express *what the work
  entails*. Changing the shared `conftest.py` pulls in the build wrapper that parses its output; adding
  an always-on gate needs a new gate-test file at the test root; making a command's output readable
  needs the command's own config. None of those is scope creep and none was listable at outline time.
  ⚠️ **The answer therefore has to be a different SHAPE — a predicate, an entailment closure, or a
  declared-plus-observed reconciliation — not a better-written list.** Any follow-up that only asks
  authors to try harder is already refuted by this landing.

  ⚠️ **A declaration is useful only when it is accurate AND narrow, and nothing in the current form asks
  for the second.** *(Superseded above by PLAN-110 — necessary, but demonstrably not sufficient. Kept
  because it is the reasoning the third measurement was designed against.)* PLAN-105's own
  candidate-lesson reached the same conclusion from inside the plan:
  521 realized paths against 221 declared-and-hit, **57% of what shipped outside every deliverable's
  declared surface**, because a sweep's real scope is a *predicate* and the outline offers only a path
  list. Now corpus lesson `2026-09-04-17-003`. ⚠️ **This is the epic's own recorded "PLAN-105 claims both
  trees at root, so nothing pairs with it" observation, re-read as a defect rather than as a fact of
  life** — the free slot was never blocked by real contention, it was blocked by a declaration too coarse
  to discriminate. → **unowned; the strongest candidate yet for a WS-06 follow-up to PLAN-170**, and
  deliberately not staged speculatively.
- ⛔ **The lost review coverage and the scope growth are ONE event.** The sweeps declared an outline-time
  snapshot, execution reached ~300 files past it, and the resulting 515-file diff is what every reviewer
  then refused: Sourcery on the GitHub API's 300-file ceiling, CodeRabbit on its 100-file plan limit,
  `cuioss-review-bot` triggered and silent. **No bot reviewed this diff.** Neither refusal was recognised
  at FIND time — Sourcery credited `participated`, CodeRabbit recorded `absent` — until `394e0fcf`
  registered both wordings mid-run. The operator accepted the gap under a `barrier-ask-override` granted
  **twice**, the first having lapsed on a rebase. Machine verification (24,246 tests, CI, merge-queue
  re-verify) is what stands behind the merge. ⚠️ **Fixing the declaration form is also the fix for the
  review gap** — they are not two follow-ups.

  ⛔ **PARTIALLY REFUTED by PLAN-110's landing (#1426).** Fixing the declaration form fixes the
  *size-driven* half and no more. PLAN-110's diff was **29 files** — inside every published ceiling,
  with nothing for a reviewer to refuse — and `reviewer_coverage` was still **2 of 3**: Sourcery did
  not review at all, and `cuioss-review-bot` participated but filed nothing scoreable. Two landings,
  two entirely different causes, the same outcome of one reviewer carrying the whole PR. **The review
  gap is a second follow-up after all**, and it is not downstream of the declaration form.
- ⛔ **D5 shipped partial, and the RECORD is the hole.** `test_footprint_resolver.py` and
  `test_footprint_tier_precedence_control.py` were never touched, and nothing in the run says whether
  the survey judged them non-removable or simply missed them. Those are different facts with different
  follow-ups, and the run can no longer be asked which. → **unowned**; a re-entry into slice 050,
  joining the per-slice reduction residue already recorded below. Stage on demand.
- ⛔ **The `verdict_inputs` gap is now THREE-FOR-THREE and the trend is worsening.** PLAN-170: 59% of
  budget in finalize. PLAN-145: 66%, 18 re-firings of 34. PLAN-105: finalize **2.40 M against execute's
  0.72 M** — 3.3× — on ~20 re-fires across five head-dependent steps, every one tracing to the
  verdict-currency classifier failing closed because no head-dependent step declares a `verdict_inputs`
  surface. Two rebases onto a moving `origin/main` multiplied it. The remedy remains proven in-tree by
  `era-stamp-fill`. ⚠️ **Still OUT OF THIS EPIC'S SCOPE and still not staged** — but three measurements
  on three consecutive landings is no longer an accumulating signal, it is a standing tax, and the
  measurement-instrumentation cluster below now has its best-evidenced member.
- **`pyproject_build` was 71.1% of all in-plan script time (155 calls, 16,262,880 ms) and the plan
  reports `total_build_seconds: unavailable`.** The build wrapper appends no change-ledger row, and the
  ledger is the declared oracle — so the contract behaved exactly as specified over an oracle nothing
  fed. Corpus lesson `2026-09-04-17-005`. Unowned; out of scope.
- **A dangling `recurrence_of` pointer.** Candidate 007 declared `recurrence_of=2026-05-08-14-001`, and
  that id resolves to nothing in the corpus at `--status all` — so it is not superseded or removed, it is
  absent. The lesson was promoted on its own merits as `2026-09-04-17-007`; the pointer is recorded here
  because a recurrence claim against a non-existent lesson is a silent provenance break. Unowned.
- **Two defects the run named as unfixable from inside itself.** `2026-09-03-17-001` is fully covered by
  this plan's codified rule but `manage-lessons remove` returns `not_found`: the file opens with YAML
  frontmatter, so it is listable but unaddressable by every id-keyed verb — **12 corpus lessons share
  that shape** (tracked as `2026-09-03-22-001`). And `check-manifest-consistency` emits a false `fail`
  on any plan with `branch-cleanup`, because that step is manifest order 13 while the retrospective is
  17, so `--base-ref origin/main` is legitimately empty post-merge — it reported `diff.files_total: 0`
  against a 521-path footprint. Corpus lesson `2026-09-04-17-006`. Both unowned; out of scope.


## Added by PLAN-145's landing (#1395, 2026-09-04)

- ⛔⛔ **A PLAN'S DECLARED SURFACE CAN DESCRIBE A DIFFERENT PLAN, and nothing detects it.** PLAN-145
  declared five Expected-Surface entries and realized **zero** of them; its entire product —
  `test/test_parser_seam_coverage.py`, 526 lines — is an undeclared tree-root file, and the
  declaration explicitly said *"this plan does not otherwise edit `test/**`"* while two of its three
  realized files are exactly that. The cause is legitimate and well-evidenced: D1 refuted the
  premise, so the plan pivoted from publishing seams to shipping a guard that re-derives the
  refutation. ⚠️ **What is missing is that nothing updated the declaration when the pivot happened.**
  The standard names two writers of post-staging scope — the Step 5b fold, which carries a same-act
  obligation, and *the plan itself during execute*, which carries **none**. This is the second one,
  observed end-to-end for the first time. It is a different defect from ordinary under-declaration
  (about two thirds of a landing's files going undeclared): here the declaration was not incomplete,
  it was about other work entirely. *Re-check at: every landing — compare the merge diff against
  `## Expected Surface` and record the realized-vs-declared delta in the landing report, which is now
  done for PLAN-145 and should become the norm.*
- ⛔ **The disjointness gate would have been right about PLAN-105 ↔ PLAN-145 for the wrong reason.**
  It would have matched PLAN-145's declared `marketplace/bundles/**` against PLAN-105's
  `marketplace/bundles/` and sequenced the pair. The actual overlap is in `test/`, which PLAN-145
  declared it would not touch. **A gate that is right by accident is not evidence the gate works** —
  and this is the one measurement the epic had available to test it, because the pair ran
  concurrently without ever being gated. *Re-check at: the next concurrent pair, if one occurs.*
- ⛔ **Four staged specs now hold premises against files PLAN-145 changed.** The merge touched
  `test/conftest.py` (+1), `test/plan-marshall/script-shared/test_conftest_loader_contract.py` (+83)
  and added `test/test_parser_seam_coverage.py` (+526). `test/conftest.py` is declared by **PLAN-110**
  and **PLAN-155**; `test_conftest_loader_contract.py` is declared by **PLAN-160** *by name* — one of
  its three surface entries — and by **PLAN-155** by directory. PLAN-160's premise is the most
  exposed: it stages a sweep of single-instance defect classes against a file that just gained 83
  lines of new contract. → **owed a re-grounding pass at the next `cleanup`**, not staged as work.
- **The re-firing cost finding is now the epic's SECOND independent measurement of one shape.**
  PLAN-145 spent **2,346,273 of 3,532,602 finalize tokens (66%)** on 18 re-firings of 34; PLAN-170
  spent 59% of a larger budget in the same phase. Cause identified and remedy proven in-tree: three
  CodeRabbit quota-recovery force-pushes each advanced HEAD, the verdict-currency classifier returned
  `invalidated` for every settle-band step because none declares a `verdict_inputs` surface, and the
  one step that *does* declare it — `project:finalize-step-era-stamp-fill` — resolved `preserved` and
  skipped at zero cost every time. ⚠️ **Out of this epic's scope** (house style and reduction of the
  Python test corpus) and deliberately not staged; it belongs to the measurement-instrumentation
  cluster recorded below, which this entry is the newest and best-evidenced member of.
- ⛔ **The retrospective-misrouting defect recurred — second occurrence, same mechanism.** PLAN-145's
  `plan-marshall:plan-retrospective` was dispatched with `orchestrated=false` / `epic=""` because the
  dispatcher resolved the orchestration verdict at item 4b.a0, *after* the order-995 retrospective had
  already run. Its 12 lessons went to the global store; `lessons-capture` recovered 6 by carrying
  pointers inside its own messages, and **6 are reachable only globally**: `2026-09-04-14-006`,
  `2026-09-03-19-005`, `2026-09-03-11-007`, `2026-08-25-09-004`, `2026-09-04-12-001`,
  `2026-09-03-22-002`. `2026-09-03-19-005` is the epic-relevant one — the recorded form of the
  re-firing cost story above. Recorded as a **recurrence on the PLAN-170 entry**, not as a second
  defect. The structural fix is unchanged: `plan-retrospective` needs the same `orchestrated` / `epic`
  runtime inputs `lessons-capture` already gets.
- **`scope_creep_check` compared nothing, again.** `could_not_look` / `no_baseline_sha` on both
  phase-5 firings, because `references.json` carries no `plan_creation_sha`. This is the exact shape
  ADR-019 was created for, and it is now a named instance on a second plan. Scope was confirmed by
  direct inspection instead. Unowned; out of scope.
- **`build_queue` slot release fails from inside a worktree and the failure is invisible.** Four
  non-zero exits of `pyproject_build run`, all `git rev-parse --git-common-dir` timing out at 10 s
  during the *release* after a green build. Because the build itself passed, no gate went red — the
  only trace is a script-level exit 1. Unowned; out of scope.


## Added by the 2026-09-04 analyze (mid-flight observation, no ship semantics)

> ↪ Relocated to `settled.md` § "The un-gated concurrent pair, PLAN-105 and PLAN-145" — retired: both landed and no collision occurred. ⚠️ The structural resume-path gap it exposed is NOT settled and stays live in the bullet below.
- ⚠️ **A `contradicted / rescoped: no` verdict does not survive a resume.** PLAN-145's claim carries
  that stamp deliberately, as the thing that kept it unemittable. The plan is now executing anyway,
  because the stamp feeds the **prep-ready admission test in `next`** and nothing consults it on the
  resume path. The stamp is not wrong and should not be cleared — it is simply no longer load-bearing
  for this plan. *Re-check at: whether the prep-ready test belongs on the resume path too; this is
  the same gap as the watch above, seen from the verdict side rather than the surface side.*


## Added by PLAN-110's landing (#1426, 2026-09-06)

> ↪ **Pre-launch warning RETIRED as satisfied.** The 2026-09-05 anchor flagged that the unorchestrated
> plan `unreviewed-merge-gate-holes` (PR #1409) had modified
> `test/plan-marshall/workflow-integration-github/test_github_pr.py` inside PLAN-110's declared surface,
> and demanded that directory be re-grounded before the launch was confirmed. PLAN-110 **never touched
> that directory** — it is one of the 8 declared-but-unrealized entries. The warning was worth raising
> and cost nothing; it resolved as a non-event. ⚠️ The **unorchestrated-plan blindness** underneath it
> is unchanged and stays carried: `corpus cross-check` walks sibling epics and live orchestrated plans,
> so a plan the operator runs directly is outside the enumerated population entirely.

- ⛔⛔ **Three head-dependent finalize gates rendered verdicts over a tree that is not the one that
  merged, and all three read `outcome: done`.** The fourth loop-back was authorised under the
  operator's standing unattended instruction but handled *inside* `automatic-review` rather than
  admitted as a loop-back, so it never went through `manage-status set-phase` — the path that re-arms
  head-bound steps.

  | Step | anchored at | merged head |
  |---|---|---|
  | `project:finalize-step-plugin-doctor` | `150ead51` | `c8cf10d5` |
  | `pre-submission-self-review` | `150ead51` | `c8cf10d5` |
  | `pre-push-quality-gate` | `b5400e55` | `c8cf10d5` |

  ⛔ Not theoretical: `pre-submission-self-review` had **already caught two contract-drift defects in
  `build-pyproject/SKILL.md`**, and that same file was edited twice more after its anchor without the
  step looking again. Build and test coverage held (`ci-verify` green at `c8cf10d5`); the **structural**
  half was lost, silently. Corpus lesson `2026-09-06-10-001`. → **unowned, out of this epic's scope**
  (it belongs to `phase-6-finalize`), recorded because the epic's own reading of a green step list
  depends on it.
- ⛔ **The epic's head-currency problem now has BOTH directions measured, and the new one is worse.**
  The `verdict_inputs` gap this epic has recorded three times is gates **over**-firing on an
  invalidated verdict — expensive, but visible. PLAN-110 is the same missing capability making them
  **under**-fire and stay green — cheap, and invisible. Lesson `2026-09-06-10-001` names the contrast
  itself and is explicit that its remedy (a pre-merge staleness assertion independent of the loop-back
  path) *complements* rather than duplicates `2026-09-04-17-001`'s `verdict_inputs` proposal. ⚠️ Any
  future framing of this epic's gate-currency thread that treats it as one-directional is now wrong.
- ⛔ **The review-versus-gate delta has never once rendered a share.** Excluded on PLAN-105
  (`gate_head_sha != reviewed_head_sha`) and again on PLAN-110 (`gate_tree_unsubstantiated`,
  `structural_share: null`) — the latter for two independent reasons: the `pr-comment` findings carry
  two different `reviewed_commit_sha` values because the plan looped back and re-pushed, and
  `reviewed_head_sha` was not supplied. Both runs behaved correctly by passing nothing rather than
  deriving one SHA from a mixed set. ⚠️ **A measurement that is excluded every time it is attempted is
  not a measurement.** The escape counts remain real (PLAN-110: 7 escapes, 6 `gate_addressable`, 1
  `gate_structural`). Unowned; measurement-instrumentation cluster.
- ⛔ **Scope-creep measurement was unavailable for PLAN-110's entire run.** `references.json` carried no
  `plan_creation_sha`, so `scope_creep_check` returned `could_not_look` on every task and
  `residual_count` is **absent, not zero** — on the one run that took an operator-authorised
  write-boundary widening into 7 `marketplace/bundles/**` files. The widening itself is a recorded
  expansion, not drift; what is missing is any instrument that would have said so independently.
- ⛔ **The `launched` transition was never recorded, for the second consecutive emit.** PLAN-110's row
  read `staged` for the whole 32-hour run, so the ledger asserted nothing was running while a plan was
  in flight. `auto_emit` is `false` by design and emit≠running is the intended invariant; the gap is
  that **nothing closes the loop between the operator launching and the ledger learning of it.** A
  landing reconciliation eventually repairs the row, which is exactly why the gap survives — it is
  self-healing after the fact and therefore never urgent. → unowned.
- ⚠️ **The epic's inbox channel is only as good as the moment a run learns it is orchestrated.**
  PLAN-110 resolved its orchestration verdict late, so `review-retrospective`, `plan-retrospective` and
  `lessons-capture` all ran with `orchestrated=false` and wrote to the **global** corpus instead of
  emitting `kind: candidate-lesson` here. Nothing was lost — `2026-09-06-10-001` and `2026-09-06-10-002`
  are live (verified), plus recurrence sections on nine existing lessons — but the epic's per-item
  disposition step never saw them. ⚠️ Every candidate-lesson count this epic has recorded is therefore a
  **lower bound**, not a census. → unowned.
- ⚠️ **Two of PLAN-110's own spec premises were refuted by its execution**, both recorded in
  [`landings/PLAN-110.md`](landings/PLAN-110.md): `pytest-randomly` occurs **nowhere** in the
  inventoried tree, so PLAN-060's randomised hermeticity arm went unrun because the plugin was never a
  dependency of this project — not because a listed dependency was absent; and the predicted
  "genuinely variable platform" skip class (Windows symlink semantics, `/proc`) emptied to **zero**
  entries. ⛔ Also: the `skipped == 0` gate the epic relied on across its whole executed half was
  **dead code** — no producer ever set `PLAN_MARSHALL_STRICT_NO_SKIP`, so it never once rendered a
  verdict. It is now always-on and the flag is deleted.
- ⚠️ **Order-independence is half-settled and owned by nobody.** PLAN-110's reverse-order arm ran green
  but under parallel workers; the strict serial arm (~53 min CPU) was not run, and the plan said so
  itself. PLAN-105's candidate-lesson 009 item 1 asked for exactly this and was **deliberately not
  folded into PLAN-110** (correctly — PLAN-110 was already at the split guard's threshold). It now sits
  half-answered in the Unowned list. *Re-check at: the next WS-02 slice re-entry, which is the cheapest
  place to add a strict serial arm.*
- ⚠️ **`main` is red on the LOCAL whole-tree quality gate, and it is a false positive.** Two
  `plugin-doctor` errors at `build-server-client/SKILL.md:161` claim `--timeout` is undeclared on
  `build_server submit`. **Verified false here** — `build_server submit --help` declares it. Reproduces
  on the parent commit `0fde908d0`, so it is pre-existing and not PLAN-110's. Corpus lesson
  `2026-09-06-10-002`. ⛔ Consequence for this epic: **a local quality-gate red is not currently
  evidence of a regression**, and any plan launched from here will meet it.


## Added by PLAN-130's landing (#1436 + #1435, 2026-09-07)

> ↪ **Open Defect RETIRED — `fixtures/ci-wait/README.md`.** The long-carried
> documentation-standards violation (a plan slug, a lesson id, two TASK ids and a dated line) was
> D7 of this plan and the file is in the realized set. Closed by delivery, not by refutation.

- ⛔⛔ **THE WARNING-TO-ERROR FLIP NOW HAS ITS DECISIVE INPUT, and it is not the backlog size.**
  PLAN-130 drove `test-docstring-historical-prose` from **232 findings / 111 files to 0** over its
  own population. ✅ Re-derived here rather than accepted: `doctor-marketplace test-conventions` at
  merged `main` (`681db9446`) returns **3**, all in
  `test/plan-marshall/manage-tasks/test_freshness_exempt_vs_verified_discrimination.py` at lines
  27/214/313, and `git show --name-only ef129d6a3` confirms **PR #1425 authored that file — mid-run**.
  ⛔ **The closure was falsified inside the same 22-hour window that produced it.** With PLAN-080's
  "211 of 211" falsified within two days, this is the **second observation of the shape**. The
  argument runs honestly in both directions and the ledger records both: at `error` severity PR
  #1425 would have been **blocked** — exactly what the flip buys, and exactly what it costs, since
  #1425 is unrelated upstream work stopped on a docstring-prose rule. ⚠️ **The input to weigh is
  that a population refilling faster than sweeps can drain it is not a backlog problem.** Corpus
  lesson `2026-09-07-15-006`. → the flip decision remains the operator's; it is no longer
  under-evidenced.
- ⛔ **`facts.pr_number` is write-once across re-created PRs, and it corrupted a verification
  instrument.** `create-pr` stamped `1432`; #1432 was closed unmerged (`merge_commit_sha: null`,
  verified) and shipped nothing, while the plan shipped as #1436 + #1435. ✅ The plan **refused to
  transcribe the stale fact** and named the discrepancy — which is why this ledger carries the right
  PRs. The same stale fact then made the retrospective's footprint resolver return **36 of 112
  files** and emit a spurious `Recall 32% below threshold` naming 76 correctly-shipped files as
  missing. Corpus lesson `2026-09-07-15-003`. → unowned, out of this epic's scope.
- ⛔ **A skip gate was undercounting by 6×, and this analyze proved it rather than repeating it.**
  Candidate 011 arrived explicitly as an *unverified observation* asking the orchestrator to confirm
  or refute. Settled: the archived `work.log` carries **14 `[ERROR] … script_failure` lines over 7
  distinct failing notations**, **6 of them before the gate evaluated**, against a forwarded
  `signal_script_failure_clusters_count: 1`. Both of the leaf's own alternative explanations are
  **refuted** — a narrower phase scope yields 3, not 1, and the records sit in the `work` log the
  gate reads. **Root cause is in the instruction text**: `phase-6-finalize/SKILL.md` § Signal 3 says
  to bucket by "the `bundle:skill:script` token in the line", but every line carries **two** — the
  emitting `(plan-marshall:execute-script:2)`, identical on every line, and the failing `notation=`
  value. Taking the first reproduces `1` exactly. ⚠️ **This is a SKIP decision**: at zero signals
  `lessons-capture` never runs, so a counter collapsing every distinct failure to one is one step
  from discarding the whole class. Corpus lesson `2026-09-07-15-011`. → unowned, out of scope.
- ⛔ **CodeRabbit's 100-file cap is a STRUCTURAL constraint on this epic's remaining sweeps, and
  splitting is a coverage mechanism rather than a workaround.** A tree-wide sweep cannot be reviewed
  as one PR. PLAN-130 split along its own deliverable boundaries into 76 + 36 and **both halves were
  reviewed**, finding 2 real defects. ✅ Set against PLAN-105 (zero bots, size refusal) and PLAN-110
  (1 of 3 reviewers), this is the first landing in three where review coverage actually held — and
  the split is why. ⚠️ **Every remaining sweep in this epic must plan its split at outline time**:
  PLAN-135 (103 findings / 86 files) and PLAN-140 (343 files) both exceed the cap as single PRs.
  ⚠️ Follow-on trap, now recorded: after a **squash** merge of a stacked base, retargeting the child
  does **not** recompute its merge base — #1435 kept reporting 112 files and kept being refused,
  costing two 90-minute quota waits. Remedy is rebasing the child's own commits. Corpus lesson
  `2026-09-07-15-004`.
- ⚠️ **A standing unattended authorization consumed a `decision=needs_user` gate — for the SECOND
  time.** The sync-baseline classifier returned `classification=overlap_no_content_conflict`,
  `threshold=no_overlap_only`, `decision=needs_user`, and the run resolved it against the standing
  instruction instead of firing `AskUserQuestion`. PLAN-110 recorded the **identical** pre-rebase
  bypass. Two plans, same gate: a recurrence, not an incident. ✅ Both outcomes were correct and both
  were logged rather than taken silently; the concern is the precedent, and the proposed line is
  clean — a standing authorization covers gates whose threshold the situation *satisfies*, never one
  whose threshold it *exceeds*. Corpus lesson `2026-09-07-15-007`. → unowned.
- ✅ **The finalize-outspends-execute streak BROKE.** 5-execute 1,615,513 against 6-finalize's
  1,469,848 — a ratio of **0.91×**, the first landing in five where finalize cost less. The last
  three are monotone: 3.33× (PLAN-105) → 1.29× (PLAN-110) → 0.91× (PLAN-130). ⚠️ One point is not a
  trend and the earlier PLAN-170/145 figures measure a *different* quantity (wasted finalize share,
  59% and 66%), so this is recorded as a direction to watch, **not** as a demonstrated improvement.
- ✅ **The inbox channel worked as designed, and the launch handshake held.** PLAN-130 emitted 11
  candidate-lessons plus a landing; the queue transition read `previous_status: launched`, so the
  emit→launch gap that went unrecorded on the two prior emits did **not** recur. ⚠️ The
  "candidate-lesson counts are a lower bound" caveat this ledger carries applies to **PLAN-110's**
  run specifically, not to this one.
- ⚠️ **Six prose/identifier incoherences left for a follow-up pass**: a de-referenced comment beside
  an identifier still carrying the old number — `test_maven_rewrite_log.py` prose no longer says
  "deliverable 1" while the constant is still `D1_CORPUS`; `test_comments_stage.py` dropped `1014`
  while `_SOURCERY_1014_REFUSAL` keeps it. Renaming identifiers is behaviour-adjacent and was
  correctly outside a prose-only sweep. → unowned; a natural fold into PLAN-135 or PLAN-160 at
  whichever is re-grounded next.
- ⚠️ **`manage-solution-outline`'s own description defeats its argparse surface.** `SKILL.md:3` reads
  "deliverable extraction"; the declared verb is `list-deliverables`. The plan was rejected 5 times,
  its retrospective a 6th, and **reproducing it during this analyze makes 7**. ⛔ This orchestrator
  hit three further instances of the same class in the same session (`manage_status`, `pr view`,
  `--pr-number`), so the class belongs to the documentation surface, not to any one run. Corpus
  lessons `2026-09-07-15-005` (the concrete fix) and `2026-09-07-15-010` (the authoring-site rule:
  a workflow step that states an intent instead of quoting its invocation has delegated verb
  selection to the model).


## Added by PLAN-135's landing (#1446, 2026-09-08)

- ⛔ **A sweep authored the very defect class it exists to remove, and every internal gate passed
  it.** PLAN-135 D4 wrote a new docstring paragraph asserting an isolation the code did not
  establish — false on all three of its claims — in a file it was already editing, on a plan whose
  whole subject is preambles asserting invariants the code does not establish. The pre-plan
  docstring made no isolation claim at all, so this was **manufactured, not inherited**. Task
  verification, the deliverable sweep, end-of-phase verification, pre-submission self-review and
  the quality gate all passed it; CodeRabbit caught it by **running a probe**.
  **Root cause is method-level and applies to every remaining sweep in this epic (PLAN-140, 155,
  160):** the remedy vocabulary is shape-based (`run_script` / explicit `env=`) while the defect is
  claim-based, so a sweep validated by a shape rule is structurally blind to its own defect class
  the moment it writes prose. The classification artifact attached a claim-verification obligation
  to the row whose claim ALREADY existed and none to the row about to have one written into it —
  backwards, since authored prose is precisely the prose no prior reviewer has ever checked.
  Promoted as lesson `2026-09-08-06-001`. **Watch this on every remaining sweep**, and prefer
  attaching the obligation per site at outline time over catching it at review.
- **The finalize-outspends-execute streak is now broken twice running.** 5-execute 2,463,442 vs
  6-finalize 2,207,257 = **0.90x**, after PLAN-130's 0.91x. Two consecutive sub-1.0 samples is more
  than the single point recorded last landing, but the earlier PLAN-170/145 figures measure a
  DIFFERENT quantity (wasted finalize share), so the series is still not a clean trend. Re-check at
  the next landing; three consecutive would make it worth acting on.
- **Declaration form has a FIFTH measurement and it is mode 2 for the third time.** PLAN-135
  realized **89 of 89** files inside its declared surface — as useless to the gate as PLAN-130's
  112 of 112, because the declaration claims `test/` at ROOT so nothing COULD have landed outside.
  The root claim remains the measured reason this epic has run strictly one plan at a time, and
  'accurate AND narrow' stays retired as the remedy: the answer must be a different SHAPE.
- **PR size was a non-event this landing.** 89 files, under the 100-file CodeRabbit cap, no split
  needed — the spec's 86-file estimate was close and the cap was never approached. The structural
  constraint still binds PLAN-140 (343 files, exceeds it outright); it did not bind here.
- **`test-module-line-budget` reads 354 at `b64db667`.** The epic's carried figure is a whole-tree
  budget population of **279** at `00b92fca`. These may be different quantities (modules measured
  vs findings over budget) and many PRs separate the two commits, so **no delta is asserted here**.
  Reconcile the two readings at the next `cleanup` before PLAN-140 is emitted — it is PLAN-140's
  population and the plan should not be sized against an unreconciled number.
