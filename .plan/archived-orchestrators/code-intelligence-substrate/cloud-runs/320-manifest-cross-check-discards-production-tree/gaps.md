# Gaps — 320-manifest-cross-check-discards-production-tree

All six deliverables are implemented, at both sites, and every guard I mutated went red on the defect it names — the substance of the plan landed. What remains is a ring of the plan's own archetype around the fix: two corrections that landed at one of two sites (a CLI help string still contradicting the SKILL.md it was corrected in; the summarize-every-status fix applied to one of the two sibling checks), one rule that still reports "no diff data available" over a diff it demonstrably received, a documented capture invocation that now yields nothing but `indeterminate`, two false test counts in the run report, and four declared-residue items that are still open. Eleven entries follow. Entry IDs are stable (an adversarial review re-severitied G2, G3 and G8 without
renumbering), so read the `Severity` field per entry rather than inferring it from position.

## G1 — Correct the `--base-ref` help string to match the behaviour SKILL.md already documents

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py:836` (the `--base-ref` argparse `help`)
- **Evidence:** the shipped help reads `'Git base ref for the diff (e.g. origin/main). Required when --diff-file is absent.'` — byte-identical to `eb0124c^`. `SKILL.md:483` was corrected by the same run to *"Supply `--base-ref` whenever `--diff-file` is absent … It is **not CLI-enforced**, and the behaviour when both are absent is defined rather than fatal."* CR-4's disposition in `report-01.md` reads "**fixed by documenting the real behaviour**"; it was fixed at one of the two places that state it.
- **Why it matters:** `--help` is the surface a caller reads at the moment of invocation. It asserts an enforcement that does not exist, which is what CR-4 objected to; a caller who believes it will not learn that omitting both arguments now yields `indeterminate` for every diff-fed rule.
- **Action:** replace the help text with the real contract, e.g. `'Git base ref for the diff (e.g. origin/main). Supply it whenever --diff-file is absent — with neither, no diff evidence reaches the rules and every diff-fed check reports indeterminate. Not CLI-enforced.'`
- **Done when:** `check-manifest-consistency.py run --help` no longer contains the word "Required" for `--base-ref`, and its wording agrees with `SKILL.md:483`.
- **Effort:** S
- **Risk if fixed:** none beyond a help-text assertion in any test that greps for the old string (none exists today).

## G2 — Give rule M4 the diff-availability signal instead of inferring absence from an empty file list

- **Kind:** bug
- **Severity:** high — the rule cannot fire in exactly the state it exists to judge, and the message it emits there states something the fragment two lines above contradicts (a measurement misreporting). Re-severitied from medium by adversarial review, which reproduced the state independently.
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py:476-481` (`evaluate_branch_cleanup`'s skip guard) and its call site at `:760-762`
- **Evidence:** run against a `--diff-file` naming an existing but empty file, the script emits `diff: {'base': 'file:empty.txt', 'files_total': 0, …, 'diff_available': True}` beside `{'name': 'branch_cleanup_changes', 'status': 'skip', 'message': 'rule M4 skipped — no diff data available (base=unknown or empty diff)'}`. Reproduced twice, independently, on the tree as it stands: `base` reads `file:empty.txt`, not `unknown`, so the message is false about its own inputs. The loader (`:166-222`) already computes and returns `evidence_available`, and `cmd_run` stores it at `:728`, but `evaluate_branch_cleanup` is handed only `base_label` and `len(raw_files)`, so it re-derives availability from `raw_files_total == 0` — the exact `len(files) == 0` inference the module docstring at `:171-181` forbids.
- **Why it matters:** M4 is the one rule that fails on the survivor set being empty. A supplied, resolved, genuinely-empty footprint is precisely the state M4 exists to judge (branch-cleanup scheduled, nothing changed), and it withholds itself there while emitting a message that contradicts the `diff_available: True` it publishes two lines away. The run's own headline defect — a could-not-look reported with the same token as a nothing-to-look-at — survives inside the rule whose two shapes D2's rationale analyses by name.
- **Action:** thread `evidence_available` into `evaluate_branch_cleanup` and skip only when it is `False`; when evidence exists and the raw diff is empty, evaluate the rule (a resolved empty footprint with `branch-cleanup` in `phase_6.steps` is the `branch_cleanup_without_changes` finding, worded for an empty *observed* diff rather than for a filtered-away one).
- **Done when:** with an existing empty `--diff-file` and `branch-cleanup` in `phase_6.steps`, `branch_cleanup_changes` is no longer `skip` with the message "no diff data available"; with no `--diff-file` and no `--base-ref` it still skips; both states are pinned by test.
- **Effort:** S
- **Risk if fixed:** M4 begins emitting an `info` finding on plans whose realized diff is genuinely empty — a new (correct) finding class that retrospective reports have not seen before; check `references/report-structure.md` renders it sanely.

## G3 — Make `check-routing-decisions`' summary total over the statuses it emits

- **Kind:** bug
- **Severity:** high — a summary that reports zero checks over two emitted ones is a measurement misreporting, which the calibration places above medium. Re-severitied from medium by adversarial review, which reproduced the zero-summary independently.
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py:774-778` (`cmd_run`'s `summary` literal), against `:596-600` where `inconclusive` is emitted
- **Evidence:** running `cmd_run` on a plan with a manifest, a supplied footprint, and no decision log yields `[('mis_prune:sonar-roundtrip', 'inconclusive'), ('mis_prune:finalize-step-simplify', 'inconclusive')]` with `summary {'passed': 0, 'failed': 0, 'skipped': 0}` — `sum(summary.values()) == 0` against two emitted checks. Reproduced independently on the current tree. The sibling `check-manifest-consistency.summarize_checks` (`:559-578`) was fixed by this very run for the identical defect and its docstring says so: *"Silently dropping an unrecognised verdict is exactly the absent-reads-as-nothing defect this aspect exists to surface, so it must not be reproduced in the aspect's own summary."*
- **Why it matters:** a summary consumer (`compile-report`, and any corpus audit reading the fragment) sees a mis-prune aspect whose checks vanished. An `inconclusive` mis-prune — the honest verdict when the removal cause is unestablishable — is the one a reader most needs to see, and it is the one that lands in no bucket. Pre-existing, but in the file this plan edited and of the plan's own archetype.
- **Action:** replace the three hardcoded comprehensions with a total counter over `mis_prune_checks` (a `_STATUS_BUCKETS`-style map with `.get(status, status)`, or reuse the sibling's `summarize_checks` shape) so `sum(summary.values()) == len(mis_prune_checks)` unconditionally.
- **Done when:** a run producing two `inconclusive` checks reports `inconclusive: 2` in `summary`, and a test asserts `sum(summary.values()) == len(mis_prune_checks)` over a check list containing every status the script emits plus one unknown.
- **Effort:** S
- **Risk if fixed:** `summary` gains keys; any consumer that iterates its keys rather than reading named ones (check `compile-report` and `references/routing-decision-verification.md`) must tolerate them.

## G4 — Correct the D5 test-count figure in `report-01.md` (25 → 31)

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/320-manifest-cross-check-discards-production-tree/report-01.md:197-201` (§ D5, first paragraph)
- **Evidence:** the report states *"`test/plan-marshall/plan-retrospective/test_footprint_oracle_classification.py` carries **25 test functions, collecting as 25 cases** … Both figures re-derived against the delivered tree"*. `grep -c 'def test_'` on that file → **31**; `pytest --collect-only -q` → **31 tests collected**; `git show eb0124c:… | grep -c 'def test_'` → **31**, and no commit has touched the file since. The six unaccounted tests are the PR-review round's own additions (`TestDiffFedRuleRegistryIsTheSingleSource` ×4 for CR-2, `TestVerdictWithheldWhenNoDiffEvidenceExists` ×2 for CR-5), so the figure was right at round 4 and was not re-derived after the review round — while the build-gate figure in the same report was.
- **Why it matters:** the report's own § Residue tells a later reader to re-derive any count in it; a reader who trusts this one under-counts the delivered guard population by six and may conclude the CR-2/CR-5 guards do not exist. It is also the report's stated failure mode occurring one section from where it is described, which matters for the epic's retrospective signal.
- **Action:** replace both figures with 31/31 and state the population as "the delivered tree including the PR-review round's six additions".
- **Done when:** the § D5 figure equals `pytest --collect-only` on the file at the delivering commit.
- **Effort:** S
- **Risk if fixed:** none — the report is a record; correcting a figure in it changes no behaviour.

## G5 — Correct the D5 reconciliation sentence that arithmetically confirms the wrong total

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md:235` — *"11 + 14 = 25, which reconciles with the collected count above."*
- **Evidence:** the collected count is 31 (measured, see G4). The sentence reconciles two sub-populations against a total that the tree does not hold, which reads as corroboration and is the second site of the same false figure — the *"corrected in the body, not in the line that restates it"* shape the report itself names as its residue.
- **Why it matters:** an arithmetic check that "reconciles" is exactly what stops a later reader from re-deriving. Leaving it while fixing G4 would leave the report internally contradictory.
- **Action:** re-derive both sub-populations against the delivered file (11 red-first + 14 verification-round + 6 review-round) and restate the sum as 31, or drop the reconciliation and cite the collected count directly.
- **Done when:** no sentence in § D5 asserts a total other than the measured one.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Give the documented Aspect 12 capture invocation a diff to evaluate

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md:262-267` (Aspect 12's capture block; the aspect's prose heading is at `:260`), against Aspect 13's block at `:273-278` which does pass `--diff-file work/footprint.txt` (the flag is on `:275`)
- **Evidence:** the documented command is `check-manifest-consistency run --plan-id {plan_id} --mode {live|archived}` with neither `--diff-file` nor `--base-ref`. Since the CR-4 fix, that invocation takes the no-evidence path: `test_no_diff_file_and_no_base_ref_withholds_the_verdict` pins `docs_only_diff: indeterminate` with *"no diff evidence was available"*, and M4 skips on `base_label == 'unknown'`. So as documented, the manifest cross-check aspect can never substantiate a diff-fed verdict — every applicable rule returns `indeterminate` and every other one skips. Reproduced by running the documented command against a synthetic plan: `diff.base: unknown`, `diff_available: false`, `docs_only_diff: indeterminate` with the no-diff-evidence message, and every other diff-fed check `skip`. Nor can a diff-fed rule `fail` there — M1/M2/M3 draw their culprits from an empty survivor set — so no verdict of any kind is reachable.
- **Why it matters:** the aspect exists to compare the manifest against the realized diff. Before this plan the same invocation emitted a *misleading clean pass*; it now emits an honest non-verdict, which is better but still no signal — and the workflow already has the footprint on disk at `work/footprint.txt`, which Aspect 13 two paragraphs later passes to its own script. The plan's D4 principle ("the documentation and the script must agree") is what this misses: the documented invocation and the script's contract disagree about whether the aspect can produce a result.
- **Action:** ⛔ **Do not simply copy Aspect 13's `--diff-file work/footprint.txt` into Aspect 12.**
  That path has no producer: the audit of plan 050 records that a full-repo search finds **no writer
  of `work/footprint.txt` anywhere** (14 hits, all `plan-retrospective` docs/scripts/tests —
  `doc/plans/code-intelligence-substrate/050-post-run-band-contract-and-ordering-residue/verification.md:181`),
  and that since `eb0124c` (#1288) `resolve_diff_file_path` **raises** on an unresolvable supplied
  path instead of degrading to the resolver (`:185`). Adding the flag would turn a documented
  no-verdict aspect into a documented command that errors. Nor does the script have a
  `realized_footprint` fallback: `load_diff_files` (`check-manifest-consistency.py:166-222`) reads
  only `--diff-file` or `--base-ref`. So pick one of two, and carry Aspect 13 with it since it has
  the same broken premise:
  - **Name and add the producer.** Add an explicit capture step to the workflow that writes the
    footprint to `work/footprint.txt` before Aspects 12 and 13 run — the natural source is
    `manage-references` `capture-footprint` / `compute-footprint`
    (`_cmd_compute_footprint.py:35,90`), whose output currently lands in `references.json` under
    `realized_footprint`, not in a `work/` file — and document the step in `SKILL.md` beside the
    aspects that consume it.
  - **Or use `--base-ref`.** Pass `--base-ref` in Aspect 12's block where the retrospective knows the
    base, which needs no new file and no new producer.

  Either way, state in `standards/manifest-crosscheck.md` that an invocation without either flag
  produces an all-indeterminate aspect.
- **Done when:** the Aspect 12 command in `SKILL.md` reaches diff evidence by a route whose producer
  is named in the same document; **an end-to-end test executes the exact documented invocation**
  (string-for-string, on a plan prepared exactly as the workflow prepares one) and asserts it exits
  successfully and produces at least one non-`indeterminate` diff-fed verdict — so a documented
  command that raises or that silently withholds cannot pass this criterion; and the same test (or a
  sibling) covers Aspect 13's invocation, which today names the same producerless path.
- **Effort:** M — S for the `--base-ref` route; M if the producer step is added.
- **Risk if fixed:** the aspect starts emitting real M1/M3/M4 findings on plans where it previously emitted none; expect a first wave of genuine findings in retrospective reports.

## G7 — Add `diff_available` to the documented TOON fragment shape

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/manifest-crosscheck.md:139-153` (the `diff:` block of the fragment example)
- **Evidence:** the example lists `base`, `files_total`, `files_filtered`, `files_kept`, `filtered_by_category`, `oracle_available`, `majority_discarded` — but not `diff_available`, which `check-manifest-consistency.py:796` emits on every success fragment and which the same document names in prose at `:120` ("The `diff` block publishes the evidence: … and `diff_available`").
- **Why it matters:** the fragment shape is the contract a renderer and any corpus consumer read; a field present in every fragment and absent from the documented shape is the kind of omission that makes a consumer treat it as optional or unknown. The document contradicts itself between `:120` and `:139-153`.
- **Action:** add `diff_available: true | false` to the `diff:` block of the example.
- **Done when:** every key `cmd_run` puts in the `diff` block appears in the documented shape.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — State both causes of `indeterminate` in the LLM interpretation rule

- **Kind:** doc-defect
- **Severity:** medium — the rule states a cause that is false for one of the two producers of the status, which is a false claim in shipped documentation, not a cosmetic inconsistency. Re-severitied from low by adversarial review.
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/manifest-crosscheck.md:180`
- **Evidence:** the rule reads *"It reports that the rule saw only a minority of the supplied footprint, so it is surfaced with the reduction its message names"*. There are two producers of `indeterminate`: the majority-discarded downgrade (`apply_input_reduction`, `:683-685`) and the no-evidence withholding (`_withhold_on_absent_evidence`, `:581-605`), whose message says *"no diff evidence was available … the rule evaluated an empty footprint rather than an empty change"* and names no reduction at all. The same document states the second cause correctly at `:116`; only the interpretation rule restates one of them.
- **Why it matters:** this is the instruction the report-rendering LLM follows. Told that `indeterminate` means "saw only a minority of the footprint", it will describe a no-evidence verdict as a filtering artefact — a wrong cause attached to a correct status, and after G6 the no-evidence case is the *common* one.
- **Action:** rewrite the rule to name both causes and to instruct the renderer to surface whichever the message states.
- **Done when:** `:180` names the no-evidence cause alongside the majority-discarded one.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Stop defaulting `reduction['diff_available']` to `True` in `filter_bookkeeping`

- **Kind:** bug
- **Severity:** low
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py:275-276` — the seed `'diff_available': True,` under the comment `# Filled in by the caller, which owns the base-label signal.`
- **Evidence:** the reduction block is seeded with the optimistic value and corrected by the single caller at `:728` (`reduction['diff_available'] = evidence_available`). `apply_input_reduction` reads that key to decide whether to withhold verdicts; a caller that did not overwrite it would assert evidence that never existed and re-open the exact bare-pass path D2 closes.
- **Why it matters:** latent today (one caller), but it is a default that lies in the failure direction inside the function whose whole subject is not confusing absence with emptiness. The fail-closed default is `False`.
- **Action:** either default the key to `False`, or drop it from `filter_bookkeeping`'s output and make `apply_input_reduction` take `diff_available` as an explicit parameter so it cannot be forgotten.
- **Done when:** no code path can reach `apply_input_reduction` with `diff_available` unset-but-true; a test constructing a reduction block without the caller's assignment does not produce a bare pass.
- **Effort:** S
- **Risk if fixed:** none if the caller assignment is kept in lock-step.

## G10 — Sweep the remaining blanket "`.plan/` is git-ignored" premise

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py:268-269` (the `_resolve_plan_root` docstring, whose `def` is at `:262`)
- **Evidence:** *"CI runners, fresh clones, and consumer installs have no `.plan/local` yet because `.plan/` is gitignored"*. `git ls-files .plan/` returns **13** tracked paths, including `marshal.json` — the file that holds `build.map`, the oracle this plan adopted. The run corrected the same blanket premise in `_footprint_resolver.py:173-178` because that file was in its diff, and `report-01.md`'s § Residue explicitly hands this sweep to a later `chore/`.
- **Why it matters:** it is the premise that produced the defect `script-shared/_plan_state_exemption.py` exists to fix — a bare `.plan/` rule keyed on trackedness hiding tracked edits. The operative conclusion here (`.plan/local` is absent in a fresh clone) is true; only the stated reason is over-broad, and a stated reason is what a later reader checks instead of the code.
- **Action:** narrow the clause to the subtree that is actually ignored (`.plan/local/**`), matching `workflow-integration-git/standards/worktree-handling.md:27`, which already states it correctly. Re-grep the tree for the blanket form before and after, per the sweep-and-count rule.
- **Done when:** no `.py` or `.md` under `marketplace/bundles/` asserts that `.plan/` as a whole is git-ignored.
- **Effort:** S
- **Risk if fixed:** none — comment-only.

## G11 — Share one canonical-verify step-id normalizer instead of four private copies

- **Kind:** omission
- **Severity:** low
- **Topic:** dispatch/finalize — the knowledge being copied is the phase-5/6 canonical-verify *step-id* vocabulary, whose owning surface is the step-key/dispatch layer, not architecture. Re-topiced from `architecture-core` by adversarial review.
- **Where:** four declarations, not three (`report-01.md`'s § Residue names three; an independent sweep found the fourth):
  1. `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py:68` — `_CANONICAL_VERIFY_PREFIXES = ('default:verify:', 'verify:')`, consumed at `:79`.
  2. `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_detection.py:169` — `CANONICAL_COMMAND_PREFIXES = ('default:verify:', 'verify:')`, consumed at `:179`. Its comment at `:166-169` already declares itself a mirror of site 1, so this copy is *acknowledged* rather than silent.
  3. `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py:324` — `_CANONICAL_VERIFY_PREFIX = 'verify:'`, consumed at `:373-374` inside `_role_of`, which does `canonicalize_step_key(step_id)` and then strips that prefix. **This is the site the run's residue missed, and it is the composer's own copy — the one that produces the step-list shape D3 was fixed to read.**
  4. `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py:83` + `:378-395` — `_CANONICAL_VERIFY_PREFIX = 'verify:'` and `normalize_verification_step`, added by this plan's D3.
- **Evidence:** the four declarations were read individually and agree behaviourally today. Sites 3 and 4 are more than a shared constant: `_manifest_core._role_of` (`:368-374`) and `check-manifest-consistency.normalize_verification_step` (`:392-395`) perform the *same two-step normalization* — `canonicalize_step_key`, then strip `verify:` — so D3 re-implemented a function that already existed in the module whose output it consumes. `manage-config/scripts/_config_defaults.py:751` (`_VERIFY_STEP_PREFIX = 'default:verify:'`) is a fifth, partial copy of the same knowledge and belongs in the same sweep. This is the plan's own "a named list is a SAMPLE, not an enumeration" archetype applied to *step ids* rather than *paths* — reproduced, this time, inside the residue entry that names it.
- **Why it matters:** the plan's whole thesis is that a private list mirroring a set defined elsewhere goes stale silently and is discovered only when a consumer misbehaves. The step-id vocabulary already has a shared owner (`script-shared/_step_key_canonical.py`, which strips `default:` for every writer and reader); the `verify:` half of the same knowledge is the piece that is still copied — including across the producer/consumer boundary D3 sits on, which is exactly where a divergence would recreate D3's unreachable rule.
- **Action:** move the canonical-verify prefix knowledge into `_step_key_canonical.py` (e.g. a `strip_canonical_verify_prefix` helper, and a `normalize_verification_step` that composes it with `canonicalize_step_key`, both beside the existing `canonicalize_step_key`) and have all four sites import it; declare the constant once. Fold `_config_defaults.py:751` in if its `'default:verify:'`-only reading survives the move unchanged.
- **Done when:** `grep -rn "verify:'" --include=*.py marketplace/` finds exactly one declaration of the canonical-verify prefix (in `_step_key_canonical.py`), each of the four former sites imports the shared helper, `_manifest_core._role_of` and `check-manifest-consistency.normalize_verification_step` call one function rather than two, and the existing tests for all four consumers stay green.
- **Effort:** M
- **Risk if fixed:** the consumers differ in what else they strip and in which forms they accept (`_dep_detection` matches command prefixes, `_cmd_quality_phases` matches phase entries, `_manifest_core` feeds a role table, `check-manifest-consistency` must keep accepting the bare `module-tests` form); a shared helper must not widen any of them. Pin each consumer's current behaviour by test before the move.
