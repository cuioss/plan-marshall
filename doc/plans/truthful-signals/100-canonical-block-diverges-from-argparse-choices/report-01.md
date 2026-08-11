# Run report — 100-canonical-block-diverges-from-argparse-choices (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/canonical-block-argparse-divergence-97j051` (harness-assigned)    **PR:** [#1158](https://github.com/cuioss/plan-marshall/pull/1158)    **Outcome:** completed — landing delegated (merge gated on the author's CLA signature + final CI)

## Skills loaded

Loaded via bundle path (the plan-marshall plugin was not needed; files read directly):

- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `pm-dev-python:python-core` (Python production code)
- `pm-plugin-development:plugin-architecture` (SKILL.md / bundle structure)
- `cloud-plan-lane` (the working contract, first action)

`pm-dev-python:pytest-testing` was not separately loaded — the plugin-doctor test
conventions (`load_script_module`, synthetic scratch trees) were read directly from
the existing `test/pm-plugin-development/plugin-doctor/` suite, which is the local
authority for these tests.

## Deliverables

### D1 — GATE: derive the population (mutates nothing)

Derived **mechanically** by building the D2 analyzer and running its
`derive_population()` over the real `marketplace/bundles/` tree — never a hand-listed
set of scripts (the STOP CONDITION was not hit; the population is fully machine-derived
from the canonical-block sweep across every `*/skills/*/SKILL.md`).

- **Enum sites examined (volume):** 144
- **Canonical blocks carrying documented enums:** 36
- **Sites with a resolved argparse-`choices=` authority (compared):** 69
- **Divergent sites (coverage number):** **1**

Reported as two separate numbers per the plan: divergent count = **1**; blocks examined
(volume) = **36** (and 144 enum sites, 69 resolved). The one divergence:
`plan-marshall:manage-config` `finalize-steps set-lane --lane` documented `{off,auto,full}`
while the live `choices=list(_RESOLVED_ASK_LANE_VALUES)` is `{off,standard,full}` (`auto`
was renamed to `standard`; `auto` is not accepted and `standard` was omitted).

**Two reported leads confirmed at their named symbols — both REFUTED at the canonical-block level:**

- *`manage-findings` documents fewer types than `FINDING_TYPES`*: `FINDING_TYPES`
  (`tools-file-ops/scripts/constants.py`) has **14** members. The `manage-findings`
  canonical block documents `--type` as a **placeholder metavar** (`--type TYPE`), not a
  `{a|b|c}` enum — so there is no canonical-block enum to diverge. Refuted: nothing for a
  canonical-block guard to catch.
- *`manage-lessons` documents fewer categories than `LESSON_CATEGORIES`*: `LESSON_CATEGORIES`
  has **4** members; the canonical block documents `--category {bug|improvement|anti-pattern|arch-constraint}`
  (all 4) in `add`/`update`/`list`. Refuted: matches exactly, `derive_population` marks it
  `resolved` and non-diverged.

**One false positive caught and fixed in the mechanism (the plan's declared/derived hazard, live):**
an early per-flag-global authority collapse flagged `manage-tasks update --status` (which is
free-form, no `choices=`) against `list --status`'s choices. Fixed by making the authority
**subcommand-scoped** — see D2.

### D2 — The structural guard (`canonical-enum-choices-drift`)

New analyzer `_analyze_canonical_enum_drift.py`, default-on, `severity=error`,
`scope=corpus-relational`, registered in `_rule_registry._DESCRIPTOR_MODULES` and in the
runner's `run_quality_gate` (build-failing) + `run_analyze_marketplace_rules`.

- **Authority = `choices=` only.** Resolved statically from the script AST (no executor —
  `.plan/execute-script.py` is git-ignored and absent in a fresh clone, so the help-derived
  `argparse_surface` path is a no-op here). Handles literal tuples/lists, `list()/tuple()/
  sorted()/frozenset()/set()` wrappers, same-file constants and aliases, and cross-module
  constant references (`choices=FINDING_TYPES` → follow `from constants import …` → resolve
  the tuple). **Never reads `description=` or prose** — this is the declared/derived
  distinction the plan's worked example (`record-dispatch-boundary`) demands.
- **Subcommand-scoped.** The authority is keyed on `(subcommand_path, flag)` derived from the
  argparse subparser tree; the documented subcommand path is parsed from the canonical block's
  invocation line. This is what prevents the `manage-tasks --status` false positive.
- **Fail-closed** on every unresolvable path (missing/unparseable script, no `choices=`,
  ambiguous per-subcommand choices, unresolvable constant) — a skip never over-rejects.
- **Population-derived + published:** `derive_population()` returns every examined site;
  findings carry `population_size`. Verified: commit `feat(plugin-doctor)…` (babf2d2).

### D3 — README vs `plugin.json` (`readme-skill-registration-drift`)

New analyzer `_analyze_readme_skill_coverage.py`, same registration path. **Coverage-keyed,
not headline-count-keyed:** every skill a bundle's `plugin.json` registers must be *named*
in the bundle README (bounded so `plan-marshall` never matches inside `plan-marshall-plugin`).
A README whose parenthetical count is off but whose enumeration is complete hides nothing and
is not flagged; an omitted registered skill is — because omission is the harm (three of the
live undercounts hid a security skill). Confirmed nothing already checked this (searched the
plugin-doctor rules; `plugin-json-orphan-component` is the reverse on-disk→manifest check,
not README coverage). Population: 10 bundles, 152 registered skills; exposed via
`derive_readme_population()`.

### D4 — Fix what the sweeps confirm

- **D1 divergence (1):** `manage-config` `set-lane --lane` corrected to `{off,standard,full}`.
- **D3 coverage (13 omissions across 5 bundles):** added every omitted registered skill to
  its README — plan-marshall (`automatic-review`, `build-server-client`, `manage-build-server`);
  pm-dev-frontend (`javascript-security`, `arch-gate-js`); pm-dev-python (`python-security`,
  `arch-gate-python`); pm-dev-java-cui (`parse-rewrite-log`, `search-markers`,
  `plan-marshall-plugin`); pm-plugin-development (`plugin-security`,
  `ext-self-review-plan-marshall`, `recipe-fix-argparse-rejection`). The three hidden security
  skills (`javascript-security`, `python-security`, `plugin-security`) are exactly the plan's
  ⭐⭐ elevation — confirmed.
- **Lead re-derivation:** the plan's "four bundle READMEs" is **five** (added
  pm-dev-java-cui); the "two READMEs with the false *not registered in plugin.json* sentence"
  is **four** (pm-dev-frontend, pm-dev-oci, pm-dev-python, pm-plugin-development — `plan-marshall-plugin`
  IS registered in every one of their `plugin.json`s). Both counts re-derived at the moment of
  the claim; the reported numbers were floors.
- **cui-logging-enforce example (highest severity):** the `skills:` example named
  `pm-dev-java-cui:cui-logging-enforce`, a skill that does not exist under that name (it is
  `recipe-cui-logging-enforce`) — copying it fails to load. Corrected.
- **pm-dev-oci refuted-as-cosmetic:** the D3 coverage guard did NOT fire on pm-dev-oci (its
  enumeration names all 4 registered skills); its `3 skills` heading was a cosmetic
  undercount, corrected to `4` alongside the false-sentence fix. Recorded here as the guard
  correctly not firing on a complete enumeration.

### D5 — Retire the confirmed cross-document contradictions

- **recipe-cui-logging-enforce unqualified `standards/…`:** the skill has no `standards/`
  dir; two references pointed at `standards/logging-{maintenance-reference,standards}.md`,
  which live in the sibling `cui-logging` skill. Qualified to
  `pm-dev-java-cui:cui-logging` (as the same file does elsewhere).
- **Four superseded per-type `change-*.md`:** `ext-outline-workflow/standards/{change-bug_fix,
  change-enhancement,change-feature,change-tech_debt}.md` are redirect stubs ("consolidated into
  `change-types.md`") referenced by nothing (the live per-type files referenced by prose live in
  `phase-3-outline/standards/`, a different skill). Deleted the copies.
- **Two `standards/` docs referenced by no SKILL.md** (derived mechanically — a repo-wide
  reference scan surfaced exactly two true orphans): `manage-plan-documents/standards/adding-document-types.md`
  (current, unique) → **wired in** to its SKILL.md; `tools-script-executor/standards/script-organisation.md`
  (duplicates the canonical script-organisation standard in `plugin-script-architecture/standards/python-implementation.md`)
  → **removed**.
- **AGENTS.md governance contradictions:** (a) the `Co-Authored-By` line hardcoded
  `opencode/{model-version}` with "no email address", contradicting the repo's target-aware
  convention (`Co-Authored-By: Claude <noreply@anthropic.com>` on Claude, per
  `workflow-integration-git` and actual `main` history) — corrected to the target-aware form.
  (b) AGENTS.md's forbidden-Bash-token list (`&&`, `;`, `|`, loops, `$()`, subshells) differed
  from CLAUDE.md's; reconciled to the **enforced** set (`bash-chain-shapes-in-skills` forbids
  `&&`, `;`, trailing `&`; a bare `|` is permitted) — AGENTS.md now lists `&&`, `;`, trailing
  `&`, newlines, loops, `$()`, subshells, heredocs (matching CLAUDE.md). CLAUDE.md was already
  correct and left unchanged.

### D6 — Tests, each verified to FAIL pre-fix

Two test files (15 tests) plus the rule-integration meta-tests.

- (a) `test_flags_truncated_enum` — truncated enum flagged, `missing_from_doc` surfaced.
- (b) `test_passes_correct_enum` — correct block clean.
- (c) `test_positive_population_over_real_tree` — real-tree population non-empty, resolves an
  authority, and contains the known-good member `manage-lessons add --category` resolved to the
  4 categories (the positive-population assertion). Mirror in the D3 test asserts the real-tree
  README population is non-empty and `plan-marshall`'s registration is fully covered.
- (d) `test_flags_omitted_skill` / `test_passes_complete_enumeration` — README omission flagged
  naming the omitted skill; complete enumeration passes even with an off count.
- Plus declared-vs-derived (`test_description_hand_list_is_not_the_authority`), subcommand
  scoping (`test_free_form_flag_in_documented_subcommand_not_flagged`), fail-closed, and
  constant-resolution tests.

**Seen to fail before it passed:** with the two analyzer modules moved aside (the pre-plan
state, guards absent), both test files fail at collection —
`FileNotFoundError: … _analyze_canonical_enum_drift.py` and `… _analyze_readme_skill_coverage.py`
— so every test is red (0 collected). Restoring the modules turns all 15 green. Captured live
during the run.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (the two analyzers, `_rule_registry.py`,
`_runner.py`, `_fixtures.py`, `test_runner.py`, and the two new test files), so the full path
was taken: **`./pw verify`** (quality-gate + tests). Final result:
**`=== verify: SUCCESS ===` — 18913 passed, 14 skipped** (402.9s). Quality-gate portion:
mypy `Success: no issues found in 391 source files`, ruff `All checks passed!`, plugin-doctor
`status: pass` with both new rules reporting 0 findings on the clean tree.

Interim failures found and fixed: the first `./pw verify` reported 3 failures — the plugin-doctor
rule-integration meta-tests (`test_rule_provenance_table`, `test_runner::…canonical_label_order`,
`test_zero_match_suite_coverage`). These enforce that a new rule is fully wired (provenance row,
golden label-order slot, firing fixture). All three were satisfied and the re-run is fully green.

## Findings

### Pre-PR verification sub-agent (Step 6, general-purpose, independent)

Verdict: **all D1–D6 SATISFIED** (code), **Out-of-scope RESPECTED**, **no undeclared collateral
change**. The agent executed both guards over the real tree and ran the synthetic controls to
confirm they discriminate. What it checked (named, so the clean verdict is not vacuous):

- **Cold-read (the plan's required test), answered correctly:** given `choices=SOURCE_TUPLE`
  vs a `description=` hand-list of the same values, **the `description=` is the mirror that can
  drift; the `choices=` is the derived truth.** The agent confirmed `_analyze_canonical_enum_drift`
  reads `choices=` exclusively (`_authority_by_subcommand_flag` → `_keyword_value(node, 'choices')`),
  never `description=`/prose, and reproduced live that a `choices=`-derived-from-tuple with a stale
  `description=` and a doc matching `choices=` yields **0 findings** — the false positive the plan
  warns against does not occur.
- **D2** authority resolution, subcommand scoping (`update`-vs-`list --status` not conflated),
  and fail-closed paths all verified live, including `--promoted {true|false}` correctly skipping
  (`resolved=False`).
- **D3** coverage keying, sibling-token boundary, and per-bundle population verified (10 bundles,
  0 undocumented on the real tree). The "nothing already checks this" claim confirmed by searching
  the existing rules.
- **D4/D5** each item verified against its manifest/source; **out-of-scope** confirmed —
  `manage-metrics` SKILL.md untouched, no `--enabled-bots`/`--participated-bots` work.
- **D6** controls confirmed to genuinely discriminate (reading `description=`, or dropping
  subcommand scoping, would each turn a named test red).

**One finding, disposition: rejected — already resolved (timing artifact).** The agent reported
"no run report exists." It was dispatched **before** this report was written; `report-01.md` now
exists and is committed (c867667), and it carries exactly what the agent said was missing: the
swept population and divergent count reported **separately** (D1 §), the refuted leads with
evidence (D1/D4 §), the D6 "seen to fail before it passed" attestation (D6 §), and the cold-read
answer (recorded immediately above). No code change was required by any finding.

_CI / PR-review findings recorded during Step 7 below._

## Reviewer participation

Expected reviewer population derived from `automatic-review/standards/{bot_kind}.md` `author_login`
(never transcribed): `coderabbitai`, `cuioss-review-bot`, `sourcery-ai` (3). Verdicts derived from
the stored comment/review bodies on PR #1158, never from a check state:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | `rate-limited` | Issue comment: "Review limit reached … you've reached your PR review limit … Next review available in: 14 minutes." Engaged, did not review this diff. |
| `sourcery-ai` | `rate-limited` | Review body: "you have reached your weekly rate limit of 500000 diff characters." The `Sourcery review` check concluded `skipped`. |
| `cuioss-review-bot` | `silent` | The `review / review` check concluded `success`, but the bot published **no** review or comment body against the diff — a green check is not a review. No findings to disposition. |

**Coverage: 0 of 3 reviewed.** All three engaged the PR but none produced a review of the diff — two
hit provider rate limits (outside our control, routine), one ran its check green without posting a
body. The § Step 8 shortfall disclosure fired (below). No push aborted any review — all three
reached their terminal state before the report-finalization commit.

## Cost

- **Tokens:** not available to the agent in this session (the harness does not expose a
  per-session token total to the agent).
- **Wall-clock:** the run is a single interactive cloud session; the two full `./pw verify`
  passes cost ~473s and ~403s respectively, plus a ~125s plugin-doctor-scoped run.
- **Population:** these figures count this single Claude Code cloud session's own activity. This
  is **not** comparable to a plan-marshall `metrics.toon` total (which counts the
  orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, absent
  here) — no parity is claimed.

## Contract check (Step 9)

GitHub access path: **GitHub MCP server** (cloud path). Branch form: **harness-assigned**
(`claude/canonical-block-argparse-divergence-97j051`, kept as-is). No `/sync-plugin-cache` is owed
(machine-local build step, not a cloud-run debt).

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named in § Skills loaded (read by bundle path; plugin not required) |
| 2 Branch | Done — on `origin`, harness-assigned; pushed before any edit |
| 3 Plan directory | Done — `…/100-…/plan.md` exists and opens with the first-instruction block (present on hand-over; no repair needed) |
| 4 Implement | Done — 8 commits, each carrying the `Co-Authored-By: Claude` trailer; all deliverables addressed |
| 4 Per-commit gate | Done — every `*.py`-touching commit was preceded by a clean quality-gate/verify (`total_issues: 0`, empty `errors[]`) |
| 4 Pushed | Done — no unpushed commit remains |
| 5 Build gate | Done — Python changed → `./pw verify` → SUCCESS (18913 passed, 14 skipped) |
| 6 Verification sub-agent | Done — verdict + cold-read + the one (timing-artifact) finding recorded in § Findings |
| 7 PR cycle | Done — PR #1158 open; both comment surfaces read; the two informational notices (CodeRabbit rate-limit, CLA) need no fix/reply; no inline review threads |
| 8 Merge gate | **Pending an external gate** — see § note below. Conditions 2 (comments handled) and 3 (report finalized) met; condition 1 awaits the final `verify` conclusion; the CLA (`license/cla`) is unsigned and only the author can sign it |
| 8 Bridge | Done — no status/ledger/other-plan write under `doc/plans/` outside this plan's own directory |
| 9 This check | Done — this table |
| 9 What have we learned | Done — below |

**Merge-gate note.** At report-finalization the required `verify / verify` check was in progress
(it passed locally and on `verify / gate`), and `license/cla` was pending because the CLA is
unsigned — a **human action only `cuioss-oliver` can take**, not something this run can resolve or
push past. The review-coverage shortfall (§ Reviewer participation, **0 of 3**) is disclosed here
per Step 8 condition 4 and is explicitly **not** a merge block. Because the merge is gated on an
external human action (CLA) plus the final CI conclusion, the run hands the landing off rather than
self-confirming `state: MERGED`: everything the lane asks of the run is complete, and the operator
report is the durable channel. If the CLA proves non-required once `verify` is green
(`mergeStateStatus` → `UNSTABLE`), auto-merge can be armed to let the queue land it; if required,
the human signature is the gate.

## What have we learned (Step 9)

**No contract change proposed.** The `cloud-plan-lane` contract carried this run end to end with no
step that was ambiguous in practice, no artifact that could not be produced as written, and no
command that failed in the environment. The one friction — the first `./pw verify` failing on the
plugin-doctor rule-integration meta-tests (provenance table, golden label order, zero-match
fixtures) — is **repo-specific**, not a lane-contract gap: those meta-tests are exactly the guard
that a new plugin-doctor rule must be fully wired, and the lane cannot (and should not) enumerate a
repo's meta-tests. The Step 6 sub-agent's "no report exists" finding was a **timing artifact of this
run's own dispatch** (the sub-agent was sent before the report was written, and the lane legitimately
finalizes the report later at Step 8 condition 3), not a contract defect — so it argues for how a run
sequences its own sub-agent prompt, not for a change to the contract. The cloud affordances the lane
names (no executor in a fresh clone → static AST authority for D2; can't self-wake → arm/hand-off;
harness-assigned branch kept) all held as written.

## Residue

- None of the D1 population's 75 unresolved-authority enum sites are defects — they are
  free-form flags, helper-added flags (`add_phase_arg`/`add_domain_arg`), or `choices=`
  referencing something the static resolver deliberately fails closed on. They are examined and
  skipped, not silently dropped (each appears in `derive_population` with `resolved=False`).
- The D3 guard is forward-only (registered → must be named). The reverse direction (a README
  naming a non-existent skill) is not enforced as a rule to avoid false positives on prose that
  mentions other bundles' skills; the one known reverse instance (the `cui-logging-enforce`
  example) was fixed directly in D4.
