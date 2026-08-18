# Gaps — 040-generator-fails-open-and-its-fixtures-cannot-see-it

All three deliverables landed and their central mechanisms work — the fail-open guard refuses and
preserves the previous executor, the population-derived test is genuinely unsampled and goes red on a
`children` strip, and the D3 smoke runs clean verbatim against the current tree. What remains falls
into three clusters. **First**, the guard's refusal exits `0`, not non-zero: the plan's literal *Done
when* is unmet, four shipped statements assert the non-zero exit anyway, and one consumer in this very
repository (`test/conftest.py`, `check=True`) is therefore blind to **every** expected error the
generator can report — though not, as first written, to the fail-open refusal specifically, which
that bootstrap cannot reach (see the narrowing in G1). **Second**, 72.6% of D2's corpus is
surface-insensitive: measured by mutation with the refusals partitioned by half, 0 of 1750 help
checks refuse against a surface stripped of every attribute, because the validator short-circuits on
a help spelling before reading the surface. **Third**, a handful of measurement and documentation
defects: a dry run publishing `scripts_registered: 0` against 158 registered scripts, a stale "four
deterministic guards" enumeration surviving at two sites, and a published population count that the
repo's own pytest flags discard.

Every gap below was re-derived independently in adversarial review: the exit-0 refusal through the
unmocked CLI, the per-attribute mutation matrix through a partitioned driver, the invisible
population count through a default-flags pytest run, and each `path:line` against the tree as it
stands.

## G1 — Make the conftest executor bootstrap detect a failed generation

- **Kind:** bug
- **Severity:** high
- **Topic:** tests
- **Where:** `test/conftest.py:116-132` (`_ensure_executor_present`), consuming
  `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:2306-2419` (`main`)
- **Evidence:** the bootstrap's only failure detection is
  `subprocess.run([...'generate'], capture_output=True, text=True, check=True, timeout=120)`, and
  nothing after the `try/except` re-checks that `executor_path` now exists. `main()`
  (`generate_executor.py:2306-2419`) ends `print(serialize_toon(result)); return 0` with no branch on
  `result['status']`, so `check=True` can never fire on any expected error. Measured three ways: a
  driver forcing Guard 5 printed `status: error` / `error: "Fail-open regeneration refused: …"` and
  exited `0`; `generate_executor.py verify` against a missing executor printed `status: error` and
  exited `0`; and the **unmocked CLI** against the real registry —
  `PLAN_TRACKED_CONFIG_DIR=<tmp with a one-entry SCRIPT_SURFACES executor> PM_SURFACE_BUDGET_SECONDS=0 python3 …/generate_executor.py generate --marketplace --marketplace-root .`
  → `surface-stats: scripts_registered=158 surfaces_derived=0 surfaces_reused=0 surfaces_not_derivable=158`,
  `status: error`, `EXIT=0`.
- **Why it matters:** the bootstrap's single failure detector cannot fire on **any** expected error.
  Every `generate` refusal is `status: error` at exit `0`: template not found
  (`generate_executor.py:1218-1219`), Guard 1 template-format skew (`:1296-1307`), Guard 2
  placeholder residue (`:1393-1402`), Guard 3 `py_compile` (`:1407-1416`), Guard 4 emitted-path
  provenance, the fail-open Guard 5 (`:1372-1386`), and `cmd_generate`'s unresolvable-base-path
  error. On each, the bootstrap returns having written nothing and having raised nothing; downstream
  tests then fail with unrelated diagnostics or (where they guard on absence) go vacuously green.
  Observed in the first audit round: the D2 population test failed with
  `Failed: no .plan/execute-script.py under /home/user/plan-marshall` after a bootstrap that raised
  nothing.
  ⚠ **One narrowing, established in adversarial review.** The first round framed this as "the plan's
  own failure shape one layer out — a regeneration Guard 5 correctly refuses is reported to the
  harness as a success." That specific coupling is **not reachable through this bootstrap**:
  `_ensure_executor_present` returns early when the executor already exists (`test/conftest.py:94-96`),
  so it only ever runs the generator with **no** previous executor on disk;
  `read_previous_surfaces` then returns `{}` at `generate_executor.py:993-994`, and Guard 5's
  predicate `if previous_surfaces and …` cannot be true. Guard 5 is therefore the one refusal this
  bootstrap can never hide. The gap stands on the other six paths, which it can and does hide — but a
  fix plan should not be sold the Guard-5 story.
- **Action:** stop relying on the exit code. Drop `check=True`, capture stdout, and treat a
  non-success generation as the failure — printing the generator's `error` and its `surface-stats`
  counts in the warning. Two mechanisms, either acceptable, and the second is the cheap floor:
  (a) parse the TOON and branch on `status != 'success'` (or an unparseable payload); (b) after the
  subprocess returns, re-check `executor_path.exists()` and warn when it does not. ⚠ If (a) is
  chosen, note that `_ensure_executor_present()` runs at `test/conftest.py:135`, **before**
  `_setup_marketplace_pythonpath()` at `:186` puts the bundle script dirs on `sys.path` — a bare
  `import toon_parser` there raises `ImportError`, so the fix must add
  `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts` to `sys.path` first, or use (b),
  or a plain `'status: error' in stdout` check. Do **not** make `main()` return non-zero:
  `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/manage-contract.md:34-36`
  mandates exit 0 for an expected error and forbids returning 1 from `main()`.
- **Done when:** a test monkeypatches `subprocess.run` (or points the bootstrap at a stub generator
  script) so the generation returns exit `0` with a `status: error` TOON on stdout, and asserts that
  `_ensure_executor_present()` emits a warning carrying that error string. ⛔ The assertion must go
  through the **subprocess boundary** — the bootstrap shells out, so stubbing
  `generate_executor.generate_executor` in-process changes nothing the bootstrap can see.
- **Effort:** S
- **Risk if fixed:** a bootstrap that now reports failures loudly may surface pre-existing generation
  problems on hosts where they were previously silent — that is the point, but it will look like new
  breakage.

## G2 — Add an exit-status assertion to the generator's error paths

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/tools-script-executor/test_generate_executor_behavior.py:372-507`
  and `test/plan-marshall/tools-script-executor/test_generate_executor.py:2865-2894`
- **Evidence:** every fail-open assertion is on the returned dict — `assert result['status'] == 'error'`
  — and no test exercises the **fail-open refusal** through the CLI. The suite does assert the
  process exit code on other generator error paths: `test_generate_executor.py:225-259`
  (`test_verify_requires_executor`, `test_drift_requires_executor`, `test_paths_requires_executor`)
  each subprocess `generate_executor.py` and assert
  `result.returncode == 0, f'Expected exit 0 (error in TOON output), got …'`. So the repository
  already pins exit `0` on an expected error, in the same test file the plan's work landed in.
- **Why it matters:** the exit code is the contract surface every shell and `subprocess` consumer
  reads, and here the suite's pre-existing tests state the **opposite** of what four shipped
  statements and the run report claim (G3-G6, G8). The plan's "exits non-zero" clause was
  unsatisfiable against a contract the suite was already enforcing three files away, and nobody
  reconciled the two. Pinning the new path closes that loop.
- **Action:** add one subprocess-level test that runs `generate_executor.py` through `safe_main` on a
  forced fail-open scenario and asserts the observed triple — exit `0` **with** `status: error` and
  the `surface-stats:` line on stdout — pinning the actual contract so a future change to any part is
  caught. A reproducible forcing recipe already exists: stage a previous executor carrying one
  `SCRIPT_SURFACES` entry under a tmp `PLAN_TRACKED_CONFIG_DIR` and set
  `PM_SURFACE_BUDGET_SECONDS=0`. Place it beside the three exit-code tests at
  `test_generate_executor.py:225-259` so the four state one contract together.
- **Done when:** a test asserts the (exit code, `status`, stats-line-present) triple for the fail-open
  refusal, and fails if any one of the three changes.
- **Effort:** S
- **Risk if fixed:** none beyond a slightly slower test file (one subprocess).

## G3 — Correct the "loud non-zero exit" claim in the emission contract docstring

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:867-869`
  (`format_surface_stats_line` docstring)
- **Evidence:** "…and the fail-open guard (see :func:`generate_executor`) turns that zero into a loud
  **non-zero exit** rather than leaving it for a consumer to infer." Measured: the refusal exits `0`.
- **Why it matters:** this docstring is the deliverable's *normative emission contract* — the plan
  required the contract be stated here rather than in a comment, so this is the text a reader is
  pointed at. It currently misdescribes the very signal it defines.
- **Action:** replace "a loud non-zero exit" with the accurate mechanism — a `status: error` TOON
  result carrying the four counts, at exit `0` per `manage-contract.md`'s three-tier model — and name
  that a consumer must branch on `status`, never on the exit code.
- **Done when:** the docstring contains no exit-code claim that a live run contradicts; grepping
  `non-zero exit` in this file returns only accurate statements.
- **Effort:** S
- **Risk if fixed:** none (prose).

## G4 — Correct the "fails loudly (non-zero exit)" comment on Guard 5

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:1366`
- **Evidence:** "…unlike the shape guards 1-4: it fails loudly (non-zero exit) and writes nothing".
- **Why it matters:** the comment sits directly above the guard, so it is what a maintainer reads
  before changing it; it will propagate the same wrong assumption into the next consumer.
- **Action:** reword to "it fails loudly (`status: error`, nothing written) — the loudness is in the
  TOON status and the counts, not in the exit code, which is `0` per the manage-contract three-tier
  model".
- **Done when:** the comment no longer claims a non-zero exit.
- **Effort:** S
- **Risk if fixed:** none.

## G5 — Correct the `cmd_generate` comment that inverts the `safe_main` contract

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:1962-1965`
- **Evidence:** "…a failed self-check surfaces here as the command's `status: error` (**non-zero exit
  via the safe_main contract**)". `safe_main`'s own docstring
  (`marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py:1671-1675`) states the
  opposite: "`sys.exit(1)` is retained, so the exit code still distinguishes a crash (1) from **an
  operation failure (0)**."
- **Why it matters:** this is the single most misleading of the four instances — it does not merely
  assert a wrong outcome, it attributes it to a named contract that says the reverse. A maintainer
  wiring a new caller would reasonably trust it, and produce another G1.
- **Action:** rewrite to state that `safe_main` maps an *expected* error to exit `0` with the TOON
  `status: error`, reserving exit `1` for an uncaught exception, and that callers must branch on
  `status`.
- **Done when:** the comment agrees with `file_ops.py:1664-1700` and with `manage-contract.md:34-36`.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Correct the SKILL.md statement that the refusal exits non-zero

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md:261-265`
- **Evidence:** "…it **fails loudly** (non-zero exit) and writes nothing, leaving the still-validating
  previous executor in place."
- **Why it matters:** this is the *shipped skill documentation* — the surface an agent or operator
  reads when wiring the generator into a workflow, and the one most likely to be copied into a new
  caller's error handling. Step 1 of the same file's smoke already gets it right ("Confirm it exits
  `status: success`"), so the file contradicts itself.
- **Action:** change "(non-zero exit)" to "(`status: error`, nothing written — the exit code stays `0`
  per the manage-contract three-tier model, so read the status, not the exit code)".
- **Done when:** `SKILL.md` carries no exit-code claim contradicted by a live run, and its two
  statements about the refusal agree with each other.
- **Effort:** S
- **Risk if fixed:** none.

## G7 — Migrate the guard count from four to five in the fail-closed audit doc

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/standards/provisioning-fail-closed-audit.md:96`
  **and** `test/plan-marshall/tools-script-executor/test_generate_executor.py:1906`
- **Evidence:** two sites, found by a whole-tree sweep for the phrase.
  (1) `provisioning-fail-closed-audit.md:96` — "| `generate_executor` | (a) | **JUSTIFY.** Runs
  **four** deterministic guards (format-version handshake, placeholder-residue, `py_compile`
  self-check, emitted-path provenance) and commits atomically…". The fifth (fail-open) guard appears
  in neither the count nor the list.
  (2) `test_generate_executor.py:1906` — "# generate_executor() runs four deterministic guards on the
  substituted content BEFORE any write". This one heads the shape-guard test section and is narrower
  (Guard 5 runs on the derivation outcome, before substitution), but it carries the same stale count.
- **Why it matters:** this document is the standing fail-closed justification for the generator. Its
  justification is now incomplete in the one dimension that changed, and `report-01.md` finding F3
  explicitly asserts "guard count migrated four→five **consistently**" — a claim this line refutes.
- **Action:** at site (1), update the count to five and add the fail-open guard to the enumeration,
  noting it is a semantic guard on the derivation outcome rather than a shape guard, and that it
  refuses with `status: error` while preserving the previous executor. At site (2), say "four
  deterministic **shape** guards on the substituted content (Guard 5 is the semantic fail-open guard
  on the derivation outcome, covered in `test_generate_executor_behavior.py`)" — the count there is
  correct once it is scoped, so the fix is to scope it, not to renumber it.
- **Done when:** a whole-tree grep for `four deterministic guards` returns exactly one hit, the
  scoped comment at `test_generate_executor.py:1906`; the fail-closed audit row enumerates all five.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Correct the run report's non-zero-exit claim

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/040-generator-fails-open-and-its-fixtures-cannot-see-it/report-01.md:30-32`
- **Evidence:** "added a fifth guard (previous non-empty ∧ emitted `derived+reused == 0` ⇒
  `status: error`, **non-zero exit**, nothing written)". The same claim appears in the merged commit
  message of `a3a4da6` — verified verbatim there: "it exits `status: error` (non-zero) and" (body
  line 27) and "against a non-empty previous exits non-zero" (body line 35).
- **Why it matters:** the report is the record a later plan reads to decide whether D1 is closed. As
  written it certifies a *Done when* clause that was never met, so the gap is invisible to anyone who
  trusts the report.
- **Action:** amend the D1 bullet to state the delivered mechanism (`status: error` at exit `0`,
  counts flattened to the TOON top level) and record that the plan's literal "exits non-zero" clause
  was **not** met because `manage-contract.md:34-36` forbids it — cross-referencing G1 as the
  consequence that remains open.
- **Done when:** `report-01.md` contains no claim of a non-zero exit, and names the substitution
  explicitly.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Stop publishing `scripts_registered: 0` on the dry-run path

- **Kind:** bug
- **Severity:** high — re-calibrated from medium in adversarial review. A shipped payload states a
  count that is false (`scripts_registered: 0` beside `scripts_discovered: 158`), which is squarely
  "a measurement misreports" and "shipped behaviour is wrong". Confined to `--dry-run`, and no
  consumer of the field was found, which is why it was first read as medium — but neither fact makes
  the published number true.
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:1271-1286`
  (`generate_executor`, dry-run early return)
- **Evidence:** measured on the live tree —
  `python3 …/generate_executor.py generate --dry-run --marketplace --marketplace-root .` prints, in
  one TOON payload:

  ```text
  scripts_discovered: 158
  ...
  scripts_registered: 0
  surfaces_derived: 0
  surfaces_reused: 0
  surfaces_not_derivable: 0
  ```

  The dry-run branch returns `dict(_EMPTY_SURFACE_STATS)` verbatim, never setting
  `scripts_registered`. The sibling OSError degradation path at `:1344-1346` does set it
  (`= len(mappings)`), so the two disagree.
- **Why it matters:** D1's whole premise is that a consumer "establishes the derivation outcome by
  reading its VALUES". On this path a value is *false*, not merely absent — worse than the absence the
  deliverable set out to remove — and it violates the residual invariant asserted at `:1987-1989`
  ("the three buckets always sum to `scripts_registered`"): 0 + 0 + 0 = 0 ≠ 158.
- **Action:** in the dry-run branch, set `scripts_registered = len(mappings)` and
  `surfaces_not_derivable = len(mappings)` on the copied stats mapping, exactly as the degradation
  path does, so the buckets sum to the registered population on every path.
- **Done when:** a test asserts that a dry run over an N-script mapping returns
  `scripts_registered == N` and `surfaces_derived + surfaces_reused + surfaces_not_derivable == N`.
- **Effort:** S
- **Risk if fixed:** any consumer that currently keys "was this a dry run?" off `scripts_registered == 0`
  would break — none found, and `dry_run: True` is already in the payload for that purpose.

## G10 — Reconcile "UNCONDITIONALLY" with the paths that emit no stats line

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:855-869`
  (the contract) versus `:1218-1219` (template not found), `:1296-1307` (Guard 1 template-format skew)
  and `:1271-1286` (dry run)
- **Evidence:** the docstring says the line "is emitted UNCONDITIONALLY on every real regeneration",
  but three `generate` paths return before the `print` at `:1358`. Measured for the dry run: grepping
  its output for `surface-stats:` yields 0 matches, while the same grep matches the line in a real
  regeneration (so this is not a filtered false negative).
- **Why it matters:** on those paths a consumer that greps for the line and finds none is back to
  inferring an outcome from an absence — the exact anti-pattern the deliverable names.
- **Action:** pick one and make the text and the code agree: either emit an all-zero line on the
  early-return paths too (with `scripts_registered` correct per G9), or narrow the docstring to "every
  regeneration that reached the derivation" and say plainly that an earlier refusal emits no line and
  is identified by its `status: error` instead.
- **Done when:** for each `generate` return path, the presence or absence of the stats line matches
  what the docstring states, asserted by a test that enumerates the paths.
- **Effort:** S
- **Risk if fixed:** none if the docstring is narrowed; if the line is added, any consumer counting
  stats lines per invocation would see more of them.

## G11 — Make the D2 help checks capable of detecting a derivation defect, or stop counting them as coverage

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/tools-script-executor/test_population_derived_surface_guard.py:177-182`,
  against `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template:1078-1089`
- **Evidence:** the validator short-circuits before reading any surface content:

  ```python
  root = _surface_for(notation)
  if root is None:
      return None
  ...
  if _mentions_help(script_args):
      return None
  ```

  Measured by mutation — with `argparse_surface._node_to_dict` patched in-process to return `{}` (every
  attribute gone: `flags`, `children`, `required_flags`, `flag_arity`, `alias_of`, both confidence
  markers), the population is `help_checks=1750 flag_invocation_checks=662` and **622** valid
  invocations are refused. Re-run in adversarial review through a driver that **counts the two halves
  separately** (the arithmetic `622 ≤ 662` does not by itself establish the split): `help_refusals=0
  flag_refusals=622`. Not one of the 1750 help checks refuses against a totally empty surface. The
  same partitioning across every single-attribute strip gives `help_refusals=0` in all eight runs.
- **Why it matters:** 1750 of 2412 checks (72.6%) cannot fail for any derivation reason. They are
  presented — in the test docstring, in the report's D2 entry, and in the published count — as part of
  a population-derived corpus that "fails the moment the derivation drops an attribute". A reader
  sizing this guard's coverage from the published numbers overestimates it by roughly 4×.
- **Action:** either (a) exercise the help spellings through a path that consults the surface — e.g.
  assert `_resolve_invocation` still resolves the same chain with the help token removed, so a
  `children` strip reddens the help half too — or (b) keep the checks as a `_mentions_help` regression
  net but rename and re-document them as such, publish the two counts separately, and state in the
  docstring that only the declared-flag half is surface-sensitive.
- **Done when:** running the total-strip mutation reddens at least one help-derived assertion, **or**
  the test's docstring and published output state that the help checks are surface-insensitive and
  the surface-sensitive population size is published as its own number.
- **Effort:** M
- **Risk if fixed:** option (a) may surface genuine fail-open behaviour in `_resolve_invocation` that
  is currently masked, producing new failures that need triage before the change lands.

## G12 — Make the published population size visible on a green run

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/tools-script-executor/test_population_derived_surface_guard.py:197-202`
- **Evidence:** the count is emitted with a bare `print(...)`. `pyproject.toml:110` sets
  `addopts = ["-v", "--tb=short", "--strict-markers", "--strict-config", "--durations=25"]` — no `-s`,
  no `-rA` — so pytest captures and discards it on a pass. Confirmed by running it both ways:
  `uv run python -m pytest test/plan-marshall/tools-script-executor/test_population_derived_surface_guard.py`
  with the repo's own flags → `1 passed in 10.04s`, and the string `surface-guard population` appears
  nowhere in the output; adding `-rA` surfaces
  `surface-guard population: registered=158 derivable=114 help_checks=1750 flag_invocation_checks=662`.
- **Why it matters:** the plan marks this ⛔ ("**Publish the population size** in the test's output"),
  and the report claims it done. The purpose is that a reader can tell a full corpus from a collapsed
  one without reading the source; under the repo's own invocation that reader sees nothing. The only
  automatic backstop is the `assert len(derivable) >= len(notations) // 2` floor at lines 151-155,
  which today admits any derivable count down to **79** — so a silent shrink from 114 to 79 (a third
  of the corpus gone) passes green and invisible.
- **Action:** emit the counts through a channel pytest surfaces on a pass — a
  `record_property`/`record_testsuite_property` entry, a `warnings.warn` visible in the summary, or a
  written artifact under `.plan/temp/` — rather than captured stdout. Whichever channel is chosen,
  name it in the docstring so a reader knows where to look.
- **Done when:** a default `uv run python -m pytest <file>` (no extra flags, repo addopts applied)
  shows the enumerated population size on a passing run.
- **Effort:** S
- **Risk if fixed:** a noisier default test output; `record_property` avoids that.

## G13 — Correct the D2 docstring's claim to cover only the attributes it can actually see

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/tools-script-executor/test_population_derived_surface_guard.py:20-22`
  and `:131-134`, and `report-01.md:94` (finding F2)
- **Evidence:** the module docstring says "a derivation that drops an attribute fails a test here
  instead of shipping". `_node_to_dict`
  (`marketplace/bundles/plan-marshall/skills/script-shared/scripts/argparse_surface.py:433-444`)
  serializes seven attributes. **Measured, one mutation per attribute**, over
  `registered=158 derivable=114 help_checks=1750 flag_checks=662`:

  | attribute stripped from `_node_to_dict` | refusals (help / flag) |
  |---|---|
  | `flags` | 0 / **622** |
  | `children` | 0 / **509** |
  | `required_flags` | 0 / 0 |
  | `flag_arity` | 0 / 0 |
  | `alias_of` | 0 / 0 |
  | `flags_confident` + `children_confident` | 0 / 0 |

  So the test reddens on `flags` and `children` only. The reasons are as read: stripping
  `required_flags` only makes the validator more permissive; `flag_arity` is unreachable because the
  test never supplies a flag *value*; `alias_of` affects only corrective text; and the two confidence
  markers fall back to permissive defaults. F2 names one of the five uncovered cases.
- **Why it matters:** the docstring is the honesty surface a later reader uses to decide whether this
  guard already covers a class before writing another test. Overstated, it will suppress a needed
  test.
- **Action:** narrow the module docstring to the two attributes actually covered (as the "Why it
  catches a derivation strip" paragraph at lines 24-32 already does correctly), and list the five
  uncovered ones with the reason each is invisible. Mirror the correction into `report-01.md`'s F2 row.
- **Done when:** every attribute in `_node_to_dict` is named in the docstring as covered or uncovered,
  with the reason, and no sentence claims blanket attribute coverage.
- **Effort:** S
- **Risk if fixed:** none (prose), though the narrower claim may prompt follow-up test work.

## G14 — Raise the conftest bootstrap timeout above the generator's own derivation budget

- **Kind:** bug
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/conftest.py:123` (`timeout=120`) versus
  `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:798`
  (`_DEFAULT_SURFACE_BUDGET_SECONDS = 180.0`)
- **Evidence:** the bootstrap allows the generator 120 seconds; the generator's own default wall-clock
  budget for surface derivation alone is 180 seconds, before script discovery, probe writing and the
  atomic write. Observed here: repeated bootstraps produced no executor, and a hand-run generation of
  the same tree took roughly four minutes under load, printing
  `surface-stats: scripts_registered=158 surfaces_derived=100 …` when it finally completed. The
  `TimeoutExpired` is caught at `:125-132` and downgraded to a stderr warning.
- **Why it matters:** on a cold checkout or a loaded CI runner the bootstrap can be killed
  mid-derivation by construction, leaving no executor. The D2 population test then hard-fails with
  `pytest.fail('no .plan/execute-script.py …')` — a red build whose cause is a harness timeout, not a
  product defect. I reproduced exactly this failure before generating the executor by hand.
- **Action:** raise the bootstrap timeout above the generator's budget with margin (e.g. `240`), or
  derive it from `PM_SURFACE_BUDGET_SECONDS` / `_DEFAULT_SURFACE_BUDGET_SECONDS` so the two move
  together, and state the coupling in a comment at both sites (the pattern `pyproject.toml`'s
  `timeout = 300` already uses for the `slow_live` budget).
- **Done when:** the bootstrap timeout is documented as strictly greater than the generator's default
  derivation budget, and neither number can be changed without the comment at the other site becoming
  wrong.
- **Effort:** S
- **Risk if fixed:** a genuinely hung generation now stalls collection for longer before the warning
  appears.

## G15 — Distinguish "previous had no surfaces" from "previous unreadable" in the fail-open guard

- **Kind:** bug
- **Severity:** medium — re-calibrated from low in adversarial review. `low` is reserved for a stale
  claim in the run report, a cosmetic doc inconsistency, or a harmless unstated deviation, and this
  is none of those: it is a guard that cannot fire on a real input class. It is not `high` because
  the guard does fire on the ordinary class — only a previous executor that exists but whose
  `SCRIPT_SURFACES` block is unreadable slips past.
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:983-1017`
  (`read_previous_surfaces`) feeding the Guard 5 predicate at `:1372`
- **Evidence:** `read_previous_surfaces` returns `{}` on every failure — file absent, `OSError` on
  read, missing `SCRIPT_SURFACES` block, unterminated block, `ValueError`/`SyntaxError` from
  `ast.literal_eval`, or a non-dict parse. Guard 5 reads `if previous_surfaces and emitted_surface_count == 0:`,
  so an unreadable previous executor is indistinguishable from a fresh install.
- **Why it matters:** a guard that cannot fire on a real input class. An executor that in fact carried
  158 surfaces but whose block failed to parse (a partially written file, a permissions change, a
  future reformat of the literal) makes Guard 5 pass through and a surfaces-less executor gets
  written — the precise outcome the guard exists to prevent, reached by a different door.
- **Action:** have `read_previous_surfaces` report the failure mode separately from the empty result
  (return a `(surfaces, read_status)` pair or raise a typed error the caller handles), and treat
  "previous executor exists but its surfaces could not be read" as a refusal condition with its own
  error message rather than as "no previous surfaces".
- **Done when:** a test in which the previous executor exists with a deliberately malformed
  `SCRIPT_SURFACES` block, and the generation derives zero, produces `status: error` rather than a
  surfaces-less write.
- **Effort:** M
- **Risk if fixed:** a first regeneration after any legitimate change to the emitted surfaces-block
  format would now refuse instead of silently re-deriving; the migration path needs an explicit
  "unparseable previous is treated as empty" escape for that case.
