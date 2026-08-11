# Run report — 040-generator-fails-open-and-its-fixtures-cannot-see-it (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/generator-fails-open-fixtures-qmy24g` (harness-assigned)    **PR:** _pending_    **Outcome:** completed

## Skills loaded

- `cloud-plan-lane` (working contract; loaded first, before reading the plan).
- `plan-marshall:ref-code-quality` — read at `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`.
- `pm-plugin-development:plugin-script-architecture` — read at its bundle path.
- `pm-dev-python:python-core` and `pm-dev-python:pytest-testing` — Python production code + tests.
- `plan-marshall:persona-implementer` — production-code work identity.

All loaded by reading the bundle `SKILL.md` paths directly (the `plan-marshall` plugin is not installed in this cloud session). No skill was unobtainable.

## Claim verification (against HEAD in the clone)

The plan's claim labels were re-derived in the clone before scoping, per the labels' own instructions:

| Claim | Label | Verdict in clone |
|---|---|---|
| Generator can return `status: success` with a zero surface count (arm A) | OBSERVED (log unreachable) | **Confirmed by reading the success path.** `generate_executor` returned `{'status':'success','surface_stats':…}` even when `surfaces` was empty; the OSError degradation path (`surfaces, surface_stats = {}, …`) explicitly reached the success return. |
| The four false-rejection defects' class (attribute-stripping) | OBSERVED | Confirmed by reading `argparse_surface`/template: the four defects are validator bugs that only manifest on an absent-attribute surface (empty flag set, short `-h`, leading routing flag). |
| Every hand-built fixture declared at least one flag | HYPOTHESIS — load-bearing, higher burden | **Refuted as stated, but the root-cause argument stands.** Hand-built empty-flag fixtures now exist (`test_help_flag_always_dispatches_even_on_a_flagless_surface`, `_node()` defaults) — added as per-instance guards for the four found defects (which the plan lists OUT OF SCOPE). The real population (109 derivable surfaces / 848 nodes / 199 empty-flag nodes / 70 empty-flag roots) is not systematically covered by any hand-built set. So D2's shape is unchanged: population-derived over the real index, not "add an empty-flag fixture." |
| A population-derived corpus is affordable | HYPOTHESIS | **Measured.** A full cold derivation of the whole registry is ~52–87s (`build_surface_index` over 151 notations). D2 pays this once via the shared on-disk help cache — the same `content_hash` key the sibling `slow_live` test uses — so whichever runs second is warm (~5s). The *validation* over the derived index (151×3 invocations) is microseconds. It is tiered `slow_live`, collected in CI's `verify`; no sampling. |
| Part of D1 may already exist | HYPOTHESIS | The four surface counts were already *computed and published on the success path* (via `**surface_stats`). What did NOT exist: the fail-open guard, the counts on the *error* path, and a distinct always-emitted line. D1 adds exactly those; it did not rebuild the counts. |

## Deliverables

- **D1 — fail a regeneration that derives zero surfaces where the previous had some.**
  Commit `dc0970a`. In `generate_executor.py`: hoisted `previous_surfaces`, added a fifth
  guard (previous non-empty ∧ emitted `derived+reused == 0` ⇒ `status: error`, non-zero exit,
  nothing written); emit the `surface-stats:` line unconditionally at the single point the
  derivation outcome is known (so it rides both the refusal and the success return); flatten
  the counts into the error result in `cmd_generate`. The emission contract ("an absence
  nothing consumes is not a signal") is stated normatively on `format_surface_stats_line`, not
  as a code comment. Verified adversarially: `test_fail_open_guard_refuses_zero_surfaces_against_nonempty_previous`
  fails against the pre-guard behaviour; the stats-line test asserts the line in BOTH the
  zero (refusal) and non-zero cases. 7 targeted tests pass. Self-exercised: a live
  regeneration with the new generator emitted `surface-stats: … surfaces_derived=2 surfaces_reused=107 …`, `status: success`.

- **D2 — population-derived surface guard.**
  Commit `e5c2972`. New `test_population_derived_surface_guard.py` (`slow_live`): derives the
  real index (`registered=151 derivable=109 help_checks=1696 flag_invocation_checks=649`),
  installs the *serialized* `to_dict()` into the validator while walking the *in-memory*
  surface for ground truth, and asserts the pre-spawn validator accepts every notation's
  `--help`, `-h`, and declared-flag invocation. Publishes the population count. Verified by
  breaking the derivation on purpose — stripping `children` from `_node_to_dict` produced
  **498 refusals** (every leaf-declared flag rejected because the childless surface can't reach
  the leaf), then reverted clean.

- **D3 — required regenerate-and-dispatch smoke.**
  Commit `93fa2a9`. `tools-script-executor/SKILL.md` § "Observation point": added a normative
  "Required regenerate-and-dispatch smoke" subsection — a required step (MUST, not a reviewer's
  discretion, not satisfied by a green unit suite) naming the two shapes that bit (a help
  spelling incl. short `-h` on a required-flag leaf; a leading top-level flag before the verb).
  Each MUST dispatch, never a pre-spawn refusal; it also checks the regeneration's stats line
  reports non-zero surfaces (the D1 shape). All commands self-exercised: `--help` and `read -h`
  print usage; `manage-architecture … --project-dir . find --pattern "*.py"` dispatches to
  `status: success` (the walk correctly steps over the value-taking leading flag). The help
  forms use the `{notation}` placeholder convention (the repo's own convention for `--help`
  examples) so the `manage-invocation-invalid` analyzer does not validate them as canonical
  calls; the concrete `manage-tasks read` leaf is named in prose.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (the generator and three test files),
so `./pw verify` (full quality-gate + tests) was run.

- **First run:** 1 failed, 18964 passed, 14 skipped (497s). The single failure was
  `test_generate_executor.py::test_failed_rederivation_drops_the_entry_rather_than_reusing_the_cached_one`
  — a genuine, expected collision with D1 (see Findings, F5). The D2 `slow_live` test passed
  warm at 11.6s and the sibling live-derivation characterization at 6.6s, confirming the
  shared-cache cost analysis.
- **Fix:** reconciled that test (gave it a good sibling so the write proceeds and the DROP stays
  observable) and added a real-path total-collapse fail-open test. Re-ran `./pw verify` — result
  recorded on completion.

Per-commit gate: `./pw quality-gate` was run before every `*.py`-touching commit and reported
`status: pass`, `total_issues: 0`, empty issue list (after fixing one ruff import-order nit and
reworking the D3 smoke examples so the invocation analyzer stopped flagging the
intentionally-partial help calls). mypy: `Success: no issues found in 391 source files`.

## Findings

Findings recorded per instance, each with source and disposition.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | verification sub-agent | D1 satisfied: guard, adversarial test, unconditional-line test, normative emission contract, fresh-install success all present. | No action — confirmed. |
| F2 | verification sub-agent | D2 satisfied and NOT sampled; `slow_live`, collected in CI. Honest boundary: the test catches serializer (`to_dict`) strips + validator bugs, but not an upstream *parse-layer* strip (truth and installed lose it in lockstep) nor a `required_flags` strip (test sends only complete valid calls). | **Accepted, no change.** The test docstring discloses this honestly; the plan's D2 verification ("strip an attribute … confirm the test fails") is met by the children-strip demonstration (498 refusals), and `_node_to_dict`/`to_dict` are part of the derivation module. The four *actual* defects were validator bugs, all caught directly. Catching a parse-layer strip needs an oracle independent of the derivation (the live script), which is out of proportion. |
| F3 | verification sub-agent | D3 cold read: reads unambiguously as a REQUIRED step (quoted "MUST", "required step, not a reviewer's discretion", "does not ship on a red smoke"); both named shapes present; guard count migrated four→five consistently. | No action — confirmed. |
| F4 | verification sub-agent (beyond-diff sweep) | Four statements still described the pre-guard-5 contract ("derived nothing → status: success, only visible as a number"): SKILL.md cost/accept-set prose (+ the `0`-disables-derivation line); `derive_script_surfaces` docstring ("both exit status: success"); `cmd_generate` comment ("exits status: success exactly like a healthy one"); `_surface_derivation_config` docstring (budget `0` "SAFE configuration"). | **Fixed** in commit `7738921` — each corrected to state the fail-open refusal and keep the fresh/empty-previous case accurate. Re-verified by a focused second sub-agent. |
| F5 | CI (first `./pw verify`) | `test_failed_rederivation_drops_the_entry_rather_than_reusing_the_cached_one` failed: its single-script fixture collapses all surfaces to zero against a populated previous — exactly the fail-open case the guard now refuses — so the write it asserted on no longer happens. | **Fixed** in commit `7738921` — reconciled to a 2-script scenario (drop observable via a good sibling) and added `test_total_surface_collapse_against_a_populated_previous_fails_open` for the total-collapse case. Both pass; full suite re-run pending. |

## Reviewer participation

_Recorded after the PR is opened and reviewers report, derived from the `author_login` registry docs and the stored comment bodies._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** a single interactive Claude Code cloud session; not separately instrumented.
- **Population:** this one cloud session's usage. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total (that counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary, which this session does not share).

## Contract check (Step 9)

_Completed at Step 9._

## What have we learned (Step 9)

_Completed at Step 9._

## Residue

- D2 is `slow_live` (a real derivation, ~52–87s cold). This is by design (the plan forbids
  sampling and sanctions the slow tier), and it shares the help cache with the sibling
  `slow_live` test, but it does add one live derivation to a cold CI run.
- The edit-time `manage-invocation-invalid` analyzer does not model the help short-circuit that
  the runtime validator does, so a concrete `{notation} --help` / leaf `-h` example cannot be
  written as a validated canonical call. D3 uses the placeholder convention to sidestep this;
  teaching the analyzer the help exemption would be a separate change (out of this plan's scope).
