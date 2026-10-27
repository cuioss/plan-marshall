# PLAN-LB-98: The executor-skew check can answer on a flat install, so a stale executor is caught there and a current one is not asked about

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-98-flat-install-executor-skew.md` and is queued as one row file, `queue/PLAN-LB-98.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-27, **high**, on the operator's instruction ("it is high") after the PLAN-LB-93 lane asked the question
> again: `executor-skew` answered `could_not_check` (executor `0.1.2021`, lane text version unknown, "not derivable from its
> install path") and the lane stopped to ask whether to proceed. The question has been asked, and answered "proceed", in every
> OpenCode lane of this epic. On the operator's second machine the same verdict sat on top of a genuinely stale executor
> (`0.1.2010`) and hid it until an unrelated failure surfaced. **Each deliverable is its own outline deliverable, and each
> Done-when is its own success criterion. Do not merge them.** A criterion that says "fails at HEAD" means the lane's worktree
> base, not a fixed SHA.

## Objective

`runbook_lane executor-skew` compares the version the executor carries with the version of the lane text the run read, and
refuses to run on a `skew`. It derives the lane text's version from a `{bundle}/{version}/skills/{skill}` directory, which only
a versioned plugin cache has. A flat install (OpenCode, Antigravity: `{root}/skills/{bundle}-{skill}/`) and a source checkout
carry no version directory, so the lane text version is `None` and the verdict is `could_not_check` on every run there. The
design is deliberate and safe: an unmakeable comparison is never read as "no skew". It is also useless on the harnesses that
need it most, and it has two costs:

- **A question per lane that cannot change the outcome.** Every OpenCode lane stops and asks the operator whether to proceed,
  and the answer has always been "proceed".
- **A real stale executor passes unnoticed.** The check was written to catch exactly that case and cannot, on a flat install.

A flat install does carry a version witness: the sync writes `dist-manifest.json` at the install root with the deployed
`version` and `source_sha` (this machine: `~/.config/opencode/dist-manifest.json`, `version: 0.1.2021`). The shared
`plugin_registry` reads the executor's version; no reader of the install root's own stamp exists for this check.

## Where the delta is (measured)

- `runbook-lane/scripts/runbook_lane.py` L481-511 `_lane_text_version` reads the live version from
  `{bundles_root}/{bundle}/{version}/skills/{skill}/SKILL.md` through `select_live_version_dir` and returns `None` when no
  version directory exists. Its docstring states that the source tree and a flat install "carry no version directory; either
  is an UNMAKEABLE comparison, never 'no skew'".
- L514-537 `_executor_skew` returns `could_not_check` whenever the executor state is not found, the executor version is `None`
  or the lane version is `None`; L540-590 `cmd_executor_skew` reports the reason `lane text version not derivable from its
  install path` for that case.
- Reproduced here this pass, as an OpenCode-runtime call (`OPENCODE=1`, so the flat copy is selected):
  `verdict: could_not_check`, `executor_version: 0.1.2021`, `lane_version: unknown`, `reason: lane text version not derivable
  from its install path`. The same text as the PLAN-LB-93 lane's question.
- `~/.config/opencode/dist-manifest.json` holds `version`, `source_sha`, `executor_scripts_fingerprint`,
  `executor_changed_at_version`, `config_seed_fingerprint` and `config_changed_at_version`. The version equals the cache and the
  executor on this machine after today's sync.
- `script-shared/scripts/plugin_registry.py` (module docstring, "The authoritative reference version, per caller") says the
  cache-root `dist-manifest.json` "is never a reference: it describes what was built, not what is pinned or what is loaded".
  That sentence is about a Claude registry parity check; a flat install has no registry or pin, so what was deployed is what is
  loaded. The decision belongs to the outline (Verify-first).
- `runbook-lane/SKILL.md` L132-146 states the rule: a `could_not_check` stops the run for the operator, "never read as no skew",
  and lists "the lane text's own version cannot be derived" among its causes.
- The tests that cover the check: `test/plan-marshall/runbook-lane/test_runbook_lane.py` and
  `test/plan-marshall/tools-script-executor/test_executor_harness_independence.py`.

## Deliverables

1. **On a flat install the lane text version is read from the install root's sync stamp, so the check answers `match` or `skew`.**
   - `_lane_text_version` gains a flat-install leg: when the lane's own skill directory is a flat skill (its parent is a
     flat skill root, by `deployed_layout`'s predicate) and no version directory exists, the version is the `version` field of
     the `dist-manifest.json` at the directory that contains that skill root. Unreadable, absent or version-less stamp stays
     `None`, so the result stays `could_not_check`.
   - The nested and versioned legs, and their order, are unchanged. The source tree (no stamp, no version directory) stays
     `could_not_check`: it is the meta-project, where the executor is generated from the tree.
   - A `skew` still means the executor is OLDER than the lane text, and `match` still includes a newer executor.

   *Done when:* tests, with a flat fixture built from the real emitter output (`test/plan-marshall/_flat_install_fixtures.py`) and
   a `dist-manifest.json` at its root: executor `0.1.2021` against stamp `0.1.2021` is `match`; executor `0.1.2010` against stamp
   `0.1.2017` is `skew` with the remedy; executor newer than the stamp is `match`; no stamp, an unreadable stamp and a stamp with
   no `version` are each `could_not_check`; a nested versioned-cache fixture and a source-tree fixture return what they returned
   before. The first two fail at the worktree base (`could_not_check`).

2. **The reason says what was probed, and the lane text stops describing a flat install as an exception.**
   - `could_not_check` names the thing it could not read: the executor, or the lane text with the stamp path that was probed on
     a flat install (and "no version directory" on a nested one), instead of "not derivable from its install path".
   - `runbook-lane/SKILL.md` § executor-skew states where each layout's lane version comes from, in one place, and keeps the
     rule that a `could_not_check` is asked, never read as no skew.

   *Done when:* a test pins the reason text for each of the three unreadable cases (executor, flat without stamp, nested without
   version directory) and fails at the worktree base for the flat case; the SKILL.md sentence exists once and `plan-doctor` /
   the docs verify pass.

3. **The flat-install verdict is exercised the way a lane reaches it.**
   - One test drives `runbook_lane executor-skew` through the executor under the OpenCode runtime signal (as `OPENCODE=1`
     selects the flat copy here) against a flat fixture, so the verdict is proved on the path a lane takes and not only on the
     helper.
   - The stale-executor case from the operator's second machine is the fixture: an executor generated at an older version than
     the install's stamp ends the run as `skew` naming both versions.

   *Done when:* the end-to-end test returns `match` for the current executor and `skew` (with both versions and the remedy) for
   the stale one on the flat fixture, and `could_not_check` with the new reason when the stamp is removed; the `skew` case fails
   at the worktree base.

Split guard: three deliverables, one theme (the check works on a flat install). D1 is the derivation, D2 the wording, D3 the
end-to-end proof. D3 depends on D1 only through the fixture; a run may order them freely and report each on its own.

## Claim Labels

- OBSERVED (D1): `runbook_lane.py` L481-511 `_lane_text_version` returns the version of a `{bundle}/{version}/skills/{skill}` directory or `None`, and its docstring calls the source tree and a flat install unmakeable (read at `2001a8a13`).
  - verdict: corroborated | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read runbook_lane.py L481-511: _lane_text_version resolves the bundles root, selects a live version dir under {bundle} and returns its name, else None; the docstring calls the source tree and a flat install unmakeable.
- OBSERVED (D1, D2): `_executor_skew` (L514-537) returns `could_not_check` when the lane version is `None`, and `cmd_executor_skew` (L540-590) gives the reason `lane text version not derivable from its install path` when the executor version was read (read at `2001a8a13`).
  - verdict: corroborated | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read runbook_lane.py L514-537 (_executor_skew returns could_not_check on a missing executor version or a None lane version) and L578-590 (reason 'lane text version not derivable from its install path' when the executor state is FOUND).
- OBSERVED (D3): reproduced this pass as an OpenCode-runtime call, `env OPENCODE=1 python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane executor-skew`: `verdict: could_not_check`, `executor_version: 0.1.2021`, `lane_version: unknown`, the reason above (orchestrator-run).
  - verdict: corroborated | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: Run 2026-10-27: env OPENCODE=1 python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane executor-skew printed verdict could_not_check, executor_version 0.1.2021, lane_version unknown, the install-path reason.
- OBSERVED (D1): `~/.config/opencode/dist-manifest.json` exists and carries `version: 0.1.2021` and `source_sha: 2001a8a1391a…`, the version the sync of 2026-10-27 deployed (read).
  - verdict: corroborated | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read ~/.config/opencode/dist-manifest.json: version 0.1.2021, source_sha 2001a8a1391aecd275db25614c117541c6bc5e12, plus the executor and config fingerprints; written by the sync of 2026-10-27.
- OBSERVED (D1): `plugin_registry.py`'s module docstring says the cache-root `dist-manifest.json` is never a reference for the registry parity check because it describes what was built, not what is pinned or loaded (read).
  - verdict: corroborated | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read plugin_registry.py module docstring L33-45: the cache-root dist-manifest.json is never a reference for classify_parity because it describes what was built, not what is pinned or loaded.
- OBSERVED (Objective): `runbook-lane/SKILL.md` L132-146 stops the run for the operator on `could_not_check` and lists "the lane text's own version cannot be derived" among its causes (read).
  - verdict: corroborated | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read runbook-lane/SKILL.md L132-146: could_not_check is reported and the operator asked, never read as no skew; the causes listed include the lane text own version not derivable.
- OBSERVED (D1, D3): the check is exercised by `test/plan-marshall/runbook-lane/test_runbook_lane.py` and `test/plan-marshall/tools-script-executor/test_executor_harness_independence.py` (grep over `test/`).
  - verdict: corroborated | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: grep -rln over test/ finds executor-skew or _lane_text_version in test/plan-marshall/runbook-lane/test_runbook_lane.py and test/plan-marshall/tools-script-executor/test_executor_harness_independence.py; their content was not read.
- HYPOTHESIS (Objective): on the operator's second machine the same `could_not_check` hid a stale executor (`0.1.2010` against an install at `0.1.2017` or newer) in the PLAN-01 lane of the ui-improvements epic (operator-pasted lane report, 2026-10-27; not re-run here).
  - verdict: unverifiable | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: Operator-pasted lane report from the second machine (executor 0.1.2010, lane text version not derivable, answered proceed), read but not re-run; whether the installed version at that moment was newer than 0.1.2010 rests on the same machine's steward report (executor regenerated to 0.1.2017 in another project).
- Verify-first clause (D1): decide whether the install root's sync stamp is an acceptable witness of the lane text version on a flat install, given the `plugin_registry` caveat that a manifest describes what was built. For a flat install there is no pin, so deployed equals loaded, but the stamp is written once per sync and a lane text edited in place would not move it. Alternatives: stamp the version into each deployed skill's frontmatter metadata (the emitters already write the identity block there), or compare the lane's own `SKILL.md` content hash with the stamp's source. Record the choice and the reason, and say what the check does not catch.
  - verdict: unverifiable | checked_at: 6ec4df565ed60531342743000c41e2e0643bc542 | by: live-blockers/cleanup | rescoped: n/a | evidence: Outline-time design decision (the install stamp, a per-skill version stamp or a content hash as the witness), not a code fact at HEAD.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_lane_text_version`, `_executor_skew`, `cmd_executor_skew` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — § executor-skew (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py` and `marketplace_bundles.py` — the flat-skill predicate and a stamp reader, reused rather than re-spelled (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/targets/skill_identity.py` and the OpenCode and Antigravity frontmatter emitters — only if the outline chooses a per-skill version stamp (verify-at-outline) (D1)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the existing executor-skew tests that stay green (D1, D2, D3)
- HYPOTHESIS: `test/plan-marshall/_flat_install_fixtures.py` — extended with a sync stamp (verify-at-outline) (D1, D3)
- OBSERVED: `test/plan-marshall/tools-script-executor/test_executor_harness_independence.py` — the harness-independent executor tests that stay green (D1)

## Dependencies and Sequencing

- Depends on: PLAN-LB-96 and PLAN-LB-97 (shipped, #1868 and #1872): the flat-install vocabulary and `test/plan-marshall/_flat_install_fixtures.py`.
- Overlaps with: nothing running or staged. The PLAN-LB-93 surface (generator, `permission_fix`, `build.py`, the guard, `pre_merge_gate`, `branch-cleanup.md`, the automatic-review skill) shares no file with this plan, so the two can run in parallel; the only common ground is the flat-install test fixture, which LB-93 reads and this plan may extend.
- Adjacent to: the fix reaches an installed lane only through a sync, like every other change; until then the question stays and the answer is "proceed" when the executor version equals the installed version.
- Operator workaround until this ships: answer "proceed" after checking that the executor's `MARSHALL_VERSION` equals the version in `dist-manifest.json` at the install root; that is the comparison this plan automates.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-98-flat-install-executor-skew.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
