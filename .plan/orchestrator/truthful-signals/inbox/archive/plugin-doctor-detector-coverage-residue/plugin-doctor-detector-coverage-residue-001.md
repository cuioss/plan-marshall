envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=truthful-signals
kind=finding
created=2026-08-25T07:26:03Z

# Findings from PLAN-TRUTH-094 (plugin-doctor-detector-coverage-residue)

Twelve findings recorded during the plan's execution and finalize, all resolved
`taken_into_account` in the plan store because they are infrastructure defects
outside the plan's deliverable set. Each is reproducible and was measured, not
inferred. Grouped by what they say about *signal truthfulness*, which is this
epic's theme.

## A. A report whose vocabulary cannot express the actual condition

These are the epic's archetype in its purest form: the payload is well-formed,
the field names assert something, and the data contradicts it.

- **`8d655d` — `branch-sync-state` reports `ahead` for a DIVERGED branch.**
  After the sync-baseline rebase, `git merge-base --is-ancestor <remote> HEAD`
  exits 1, so a plain push is rejected non-fast-forward. The verb's state set is
  `ahead | synced | remote_absent_landed | remote_absent_unverified` — there is no
  `diverged` member, so a rebased branch is structurally forced into `ahead`. The
  push barrier consumes this to choose an action, so it picks the wrong one. The
  ancestry data is already in hand at the point of comparison.

- **`ed23b9` — `ci checks wait` buckets a PENDING check into `failing_checks[]`.**
  On `deadline_exceeded` it emitted CodeRabbit with `conclusion: PENDING` into an
  array the api-contract defines as "the subset of `checks[]` whose `result` is
  `failure`", with empty `log_file` / `run_id` because there is no failed job.
  The finalize contract routes `failing_checks[]` to triage, so a slow review bot
  opens a build-failure investigation with nothing to investigate.

- **`0c4569` — `deploy-target` / `sync-plugin-cache` published a cache one merge
  STALE, both reporting success.** `branch-cleanup` merges via the platform merge
  queue, so the merge lands only on `origin/main`; nothing in phase 6 pulls. Local
  main sat one commit behind and the generator emitted from a tree missing the
  plan's own merged changes (1176 entries / 0.1.1543 vs 1177 / 0.1.1544 after
  pulling). **The staleness guard cannot catch this by construction**: it
  fingerprints the WORKING TREE and compares against a sentinel written from that
  same working tree, so both agree with each other while both disagree with the
  merged remote. It proves emit-vs-sync consistency, never emit-vs-merge currency.

## B. A detector reporting clean over a population it cannot reach

The plan's own subject, found in four further places.

- **`ec6c97` — `test_every_emitted_rule_id_has_provenance_entry` derives 75 of 97
  emitted rule ids.** Its regex matches only the quoted-dict form `'type': 'x'`
  and is blind to every `Finding(type='x')` emission, missing nearly all of
  `_doctor_analysis.py`. Its green is CORRECT today (an independent AST walk
  confirms 97/97 have rows) — which is what makes it dangerous: it would stay
  green if any of the 22 it cannot see lost its row. It publishes no population
  size, so a reader cannot tell.

- **`7a3b32` — seven documented rule ids have no emitter; two detectors run and
  their output is discarded.** Of 18 ids `plugin-doctor/SKILL.md` cited, 7 exist
  nowhere in 426 scripts. `check_explicit_script_violations` and
  `check_command_self_containment` execute and return under keys
  `_doctor_analysis.py` never reads, so no Finding is ever constructed. NEEDS A
  DECISION: two reviewers disagreed on whether the `doctor-skills.md` sections
  documenting these are legitimate LLM-phase checks or documentation of rules
  that emit nothing. That is a design call about whether plugin-doctor's LLM phase
  is a first-class rule surface.

- **`74b801` — `validate_command_mappings` is dead code**, leaving 3 of 10
  documented `extension.py` contract requirements checked by nothing (required-
  profile presence, `discover_modules()` compliance, `ExtensionBase` inheritance).

- **`d2785d` — plugin-doctor ships a tested `extension.py` validator nothing can
  reach.** `validate_extension` / `scan_extensions` cover 7 of 10 contract bullets
  and are unit-tested, but have no caller, sit behind the unregistered
  `_validate.py`, and the gate's extension entry is the *different*
  `validate_extension_contracts`, whose population excludes these manifests by
  directory-name prefix. 11 manifests validated by nobody, green row printed.

## C. A stated contract nothing enforces

- **`b9a23d`** — `_doctor_shared.py`'s docstring says every entry must have a
  `fix-catalog.md` row; `rule-provenance.md` says a regression test enforces it;
  **no test does**, and the tree violates it while green.

- **`8668f3`** — `verification-guide.md` prescribes `verify-fix.sh` and
  `analyze-tool-coverage.sh`; plugin-doctor ships **no `.sh` files at all**.
  `safe-fixes-guide.md` sample code names `FIX_PRIORITY`, which exists nowhere.

- **`e2b602`** — `finalize-step-deploy-target` documents a TOON parse contract
  (`status`, `emitted_count`) the generator does not emit; it prints two prose
  lines. Its `mark-step-done` example also uses the unregistered notation
  `manage_status` (underscore), and its `uv run` invocation is not runnable when
  `uv` is absent from PATH — the working form is the pyprojectx alias.

## D. Two transferable rules, earned expensively

The finalize settle band ran 17 rounds (findings per round: 1, 8, 7, 4, 6, 9, 4,
1, 1, 1, 0, 2, 4, 3, 11, 1, 0). The dominant defect class was **a fix's own
replacement text being the next round's defect**.

- **`4e23cf` — derive completeness, never assert it.** Five defects in three
  consecutive rounds were one mistake in different grammar: a table's "Called by"
  column, a "seven of ten" partition, an "exactly seven subcommands", an "appears
  only inside an error message". One pair of errors *cancelled* arithmetically and
  read as consistent for two rounds.

- **`c27d5d` — a zero is evidence of absence only if the search shape can express
  every FORM the target takes.** "No module imports these three" came from a regex
  over static import spellings, in a tree whose documented loader is
  `spec_from_file_location`; the test suite imports all three on every run —
  **the very build the same commit cited as green evidence refuted it**. The same
  blindness recurred one abstraction lower (prefix-search vs substring-search).

- **Corollary, learned three times: narrowing a false universal REPRODUCES it.**
  One sentence went unscoped-false → bundle-scoped-false → deleted. Each narrowing
  felt like a fix and was the same defect one level in. Deletion is what terminates
  the cycle; a qualified universal is still a universal.
