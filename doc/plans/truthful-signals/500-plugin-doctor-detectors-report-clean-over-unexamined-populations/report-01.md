# Run report — 500-plugin-doctor-detectors-report-clean-over-unexamined-populations (run 01)

**Date (UTC):** 2026-08-20    **Branch:** `claude/plugin-doctor-detectors-report-ar5emr`    **PR:** not yet opened    **Outcome:** in progress

> **Verification loop exit:** not yet reached — the loop is open at the time of writing.

**This report is written as the run proceeds and is finalized as the last
pre-merge commit** (contract § Step 8 condition 4). Every section below that
states a figure re-derives it at the moment of the claim; sections marked
*pending* are not yet established and are not to be read as established.

## Skills loaded

Read by bundle path (the plugin is not installed in this session):

| Skill | Route |
|---|---|
| `plan-marshall:ref-code-quality` | `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` |
| `pm-plugin-development:plugin-script-architecture` | bundle path |
| `pm-dev-python:python-core` | bundle path (Python production code) |
| `pm-dev-python:pytest-testing` | bundle path (Python tests) |

`pm-plugin-development:plugin-architecture` was **not** loaded: the change edits
analyzer scripts, references and tests, and adds no skill or bundle structure.
No skill was unobtainable by both routes.

## Deliverables

D1 is the plan's GATE. Its derivation succeeded, so D2–D8 were attempted.

| # | What was done | Commit | Verification state |
|---|---|---|---|
| D1 | Root-anchored anti-vacuity findings survive a scoped run. The population was **re-derived** from `_runner.py` rather than taken from the plan's trio: every rule routed through `scoped(...)` or `suppressed(...)` was enumerated, and each routed analyzer read for a finding anchored at the marketplace root. The derived set is exactly the three the plan named. The fix keys on the finding's **anchor** (`_finding_is_tree_wide`), not on a finding-type list, so a fourth such rule is covered without registration. | `1e66475` | 7 tests; mutation-confirmed (below) |
| D2 | Pin-trap oracle: empty content comparison unrepresentable as a pass; union denominator so a pin superset is a divergence; content counts in the volatile signature; `partial` reachable from the adapter; four-state executor anchor. | `4bab9f8` | 5 guards mutation-confirmed; `partial` seen RED first |
| D3 | Enum notation latch replaced with a per-line search; router-flag placement rule added against each subcommand's OWN flags; leading router flags skipped when locating the verb. | `8889526` | 4 mutants, each killed by the test that names it |
| D4 | Two vacuous tests replaced, each seen RED against the defect it names. | `decd27b` | red observed, both directions |
| D5 | Runner publishes each rule's examined population from the same derivation the findings came from; `analyze_shim_marker` wired into the analyze pass. | `1a4b64c` | 6 tests incl. real-tree clean-run assertion |
| D6 | Router-flag note built from the caller's own argv through the executor notation; CI front-ends name their router flags; fifth (mirror) recurrence signature. | `807c825` | 15 tests incl. the REAL CI parser |
| D7 | `loader_selected_version` reduced to the line it always evaluated, with an eligibility parameter; saturation re-ranked; shape-3 constant renamed and the literal tree pinned; remedy names invocable surfaces; paired observer added. | `f879130` | 57 tests |
| D8 | Brace-less enum form + declarative dict-spec authority + declared coverage; two new incident-reference narration families; mirror rule-pack completed; two retrospective docstrings; one report count. | `e4e3515` | see § Findings |
| — | Round-1 fixes from the cold read and the plan's own coverage check. | `b3786f6` | see § Findings |

### Proposals recorded, not decided

Both are deliberate non-decisions the plan assigns to an operator (§ Out of
scope). **Neither was shipped as a change.**

**P1 — narrow the back-tick exemption in `no-incident-references` (130/G2).**
A back-ticked incident reference is exempt from every narration family whatever
the surrounding prose, so a removed reference can be reinstated by adding two
backticks and the gate stays green. The narrowing the gap describes: suspend the
inline-code skip when an incident noun stands within a short window on either
side of the match, or when the line is a heading.

*The live sites the narrowing would newly surface* — re-derived at HEAD by
running the matcher with the inline-code skip disabled and subtracting the sites
that fire with it enabled. The gap document says **two**; the measured figure at
HEAD is **six**, and the difference is this run's own doing: D8 added two
narration families, so the exempt population grew. This is exactly why the plan
said to re-derive rather than carry the recorded figure forward.

The six do not weigh the same, and the split is the argument:

| # | Site | Snippet | Genuine narration? |
|---|---|---|---|
| 1 | `plan-marshall/skills/phase-6-finalize/standards/finalize-step-preference-emitter.md:100` | ``the failure mode `#990` closed cannot recur`` | **YES** — incident narration in a normative standard, exempt only because the reference is quoted. This is 130/G2's real subject. |
| 2 | `pm-dev-frontend/skills/javascript/standards/jsdoc-essentials.md:109` | ``` `@since 1.2.0` ``` | No — a JSDoc **tag documentation example**, not prose pinned to a moment. |
| 3 | `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py:92` | ``` ``plan-marshall#123`` ``` | No — that analyzer's own **specification prose**, documenting the shape it matches. |
| 4 | `…/_analyze_test_conventions.py:99` | ``` ``plan-marshall#123`` ``` | No — same specification, second occurrence. |
| 5 | `…/_analyze_test_conventions.py:101` | ``` ``pre-#812`` ``` | No — and the surrounding sentence says so outright: *"a schema-state literal the corpus asserts on, not a citation of 812"*. |
| 6 | `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_incident_reference_in_docs.py:41` | ``` ``#948 sibling-worktree shape`` ``` | No — the incident rule's **own module docstring**, documenting its own pattern. |

**One of six is a real finding; five are false positives, and four of those are
the detectors' own specification prose.** The narrowing as the gap describes it
would make `no-incident-references` fire on the document that specifies it, and
on a sibling analyzer's specification of the shapes IT matches — a rule flagging
its own definition. That is a stronger argument against the narrowing than the
convention-amendment reason alone, and it was not available to the gap author,
whose two-site measurement predated these families.

If an operator still wants site 1 addressed, the cheap remedy is to fix that one
sentence (the mechanism is already stated beside it), not to narrow a
project-wide exemption whose false-positive rate on this corpus is 5-in-6.

A suppression entry is the wrong remedy here: the rule ships **unconditional**
by explicit design — no prefix is registered under `no-incident-references` in
`config/default-suppression.yml` — and the exemption is published across the
rule catalogue, the provenance table, a named test, and a sibling rule that
states the same posture. Narrowing it is an amendment to a stated convention,
which a run with no operator cannot approve.

**P2 — broaden the pin-trap shape-3 condition (320/G4).** The implemented
condition can only fire when a non-pin dir sorts HIGHER than the pin, so the
literal tree the plan's shape 3 named — an older stale unmarked dir beside a
correct newest pin — is a PASS. The alternative is to broaden the condition to
report two unmarked dirs regardless of which the loader follows. Whether that
tree is a finding or the benign post-sync window before the retention sweep runs
is a policy call about what counts as a finding. This run **pinned the current
behaviour** with `test_shape3_literal_older_stale_beside_newest_pin_is_a_pass`
and renamed the constant to describe the condition the code evaluates
(`SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR`), so whichever way the policy goes, the
present behaviour is recorded rather than assumed.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — this
change edits Python under `marketplace/bundles/` and `test/` — so the full
`./pw verify` applies.

- **`./pw verify` green** at the D8 commit (`e4e3515`): `21402 passed, 14
  skipped` in 412.51s, with `ruff … All checks passed!`, `mypy … Success: no
  issues found in 416 source files`, and `SPDX-header check passed`.
- **Not yet re-run on the current head.** Commit `b3786f6` landed after that
  run; it was gated with `./pw quality-gate` (clean on all three tools) plus the
  affected test files, **not** the full suite. The full `./pw verify` is owed on
  the current head before the PR, and again on the merged tree if the base has
  moved. Stated here rather than left implicit: a green recorded against an
  earlier commit is not evidence about this one.

**Stale-base re-verification (§ Step 8 condition 2): pending.** `origin/main`
has already advanced past this branch's merge base (66b686b → 0682705) while the
run was in progress, so the condition will apply; the count, the shape used, the
tested merge commit and the gate's result on it are recorded before arming.

### Per-commit gate

Every commit touching `*.py` was preceded by `./pw quality-gate`, each reporting
`ruff … All checks passed!`, `mypy … Success: no issues found`, and
`SPDX-header check passed`. Two commits took no gate and needed none: the plan
directory move (`2c67ed2`, a `git mv` with no content change) and the initial
branch push (no content at all).

## Findings

Recorded per instance. `RF-*` are the run's own findings; `CR-*` came from the
cold-read verifier; `CC-*` from the plan's own coverage check against the gap
documents.

| # | Source | Finding | Disposition |
|---|---|---|---|
| RF-1 | red-first, D4 | The first replacement fixture for `test_backticked_inline_code_ref_is_exempt` was **itself vacuous**: `` the `#812` failure mode `` puts a backtick BETWEEN the reference and the noun, which breaks the term-of-art pattern before the exemption is ever consulted. The mutation sweep caught it — disabling the inline-code skip left the test green. | Fixed: the whole narration phrase is quoted (`` `#812 failure mode` ``). Both earlier framings are named in the test's docstring so the next author does not repeat either. |
| RF-2 | self-review, D2 | `Path.rglob` over a path that does not exist does **not** raise — it yields nothing — so an ABSENT source directory was reported as `empty_comparison` rather than `source_unreadable`. The same launder-an-absence-into-an-observation defect the module exists to prevent, one level down. | Fixed: `_relative_file_set` tests `is_dir()` before walking. |
| RF-3 | self-review, D6 | `_after_verb` re-derived the leading-router-flag split by re-running the pattern over `leading + rest`, which greedily swallows the POST-verb flags too — a misplaced flag would have been invisible to the rule written to find it. | Fixed: the split is carried explicitly on `_Invocation` (`leading` / `rest`) rather than re-derived. |
| RF-4 | self-review, D8 | The brace-less enum member class `[^\s{}\|]+` swallowed the optional-argument closing bracket, reading `[--mode local_and_remote\|local_only]` as a member named `local_only]` and manufacturing **two drift findings on the real tree** out of punctuation, against correctly-documented flags. | Fixed: members restricted to identifier characters. Both false findings gone; real-tree findings back to 0. |
| RF-5 | self-review, D8 | The two new narration families made the analyzer **fire on its own comments** — the module's existing examples use a literal `#NNNN` placeholder for exactly this reason and the new ones did not. | Fixed: placeholders throughout, with the reason stated in the comment so the next editor keeps it. |
| RF-6 | full verify, D6 | The new `ARGUMENT_NAMING_ROUTER_FLAG_MISPLACED` rule had no provenance row and no firing positive fixture; two whole-tree guards failed. | Fixed: provenance row added; firing fixture added to `build_fixture_corpus`. |
| CC-1 | coverage check vs 360/G3 | That gap's *Done when* is a literal `grep -n -i 'retention.pin\|degraded fallback'` returning nothing. The rewritten docstring USED both phrases while explaining they were fiction, so the stated condition was not met. | Fixed: the paragraph describes what the body once computed without the two banned phrases. Condition now met (`grep` exits 1). |
| CC-2 | coverage check vs 320/G5 | That gap requires that **no surface** still claims the backward-resolution divergence is "practically unreachable". `320-.../report-01.md` still did. | Fixed: replaced with what the mechanism actually is. **Collateral, justified**: the file is outside this plan's Expected surface, but it is a location the gap itself names, and the claim is false — condition A admits no deferral. |
| CC-3 | coverage check vs 320/G5 | `320-.../verification.md` also matches "practically unreachable". | **Rejected — not a defect.** The match is inside that document's `**Contradicted:**` section, which QUOTES the claim in order to refute it. That surface already corrects the claim; editing it would delete the correction. |
| CR-1 | cold read, item 3 | **The operator remedy named a command that does nothing.** Step (2) gave `plan-marshall:marshall-steward:cache_retention sweep` as the command that prunes superseded version dirs. `sweep` is a read-only **dry run** unless `--apply` is passed (`cache_retention.py`: *"Perform the unlink. Without this flag the sweep is a read-only dry run."*). An operator following the remedy literally gets a report of what would be removed, sees no error, and moves to step (3) believing the prune happened — the false-clean shape this module exists to prevent, committed by its own remedy text. | Fixed: the step gives the full invocation including `--apply` and states what the flag's absence means. The remedy test asserts the `--apply` form. |
| CR-2 | cold read, item 4a | **The declared-coverage figure was published but not actionable.** All 75 unresolved sites landed in one bucket, `no_choices_or_unresolvable_choices`, merging two things of opposite risk: a flag declaring no `choices=` (no enum claim to contradict — not a blind spot) and a `choices=` the resolver could not reduce (a real claim left unverified — a blind spot). The module docstring separated them in prose while the published field merged them. Causes with zero occurrences were also omitted, so an absent cause was indistinguishable from one folded into a neighbour. | Fixed: split into `no_choices_declared` / `choices_unresolvable`, and the census is complete (zeroes reported). Re-derived on the real tree: **68 sites with nothing to check, 7 genuine blind spots** — not 75 undifferentiated ones. |

### Cold reads (plan § Verification)

Four texts were read **cold** by an independent sub-agent — without this plan,
without the gap documents, and without the diff — and asked what a reader would
DO with each. Readings taken:

1. **Router-flag error note (D6).** Correct: the reader produced the exact
   working invocation, through the executor convention, with their own values in
   it, and reported nothing left to guess. No bare `*.py` path, verb supplied.
2. **Fifth recurrence signature (D6).** Correct and, critically, **two different
   answers** — before the verb for the CI surface, after it for
   `manage-architecture`. The reader named the bidirectional cross-references as
   what stopped them generalizing the first signature into a flag-level fact.
3. **Pin-trap operator remedy (D7).** **Failed** on step 2 — see CR-1. Steps 1
   and 3 were directly typeable.
4. **Declared coverage (D8) and the anti-vacuity claim (D1).** The
   enum-coverage statement **failed**: the reader could state the size and shape
   of the excluded set but **could not name it concretely** — see CR-2. The
   shim-marker recall statement passed, and the reader reproduced the permitted
   inference and both forbidden ones unprompted from the measured 4-of-25 pair.

### Round record

- **Round 1** — two verifiers dispatched: a code/deliverable verifier and a
  cold-read verifier. The cold read returned CR-1 and CR-2, both fixed in
  `b3786f6`. **The code verifier's result is outstanding at the time of
  writing**; its findings, their dispositions, and any further rounds are
  recorded before the merge gate.
- **Budget:** five rounds (the contract default — this plan sets no other).
  Rounds used so far: 1.

## Reviewer participation

*Pending — no PR yet.* The expected reviewer population is derived at PR time
from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`
registry doc, never transcribed here.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** *pending* (recorded from run start/end at finalization).
- **Population:** whatever is recorded will count **this single Claude Code
  cloud session's usage as the harness counts it**. That is **not** comparable
  to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent
  dispatch tree under plan-marshall's own per-task billing boundary — a boundary
  a single interactive cloud session does not share. The two figures are not
  made comparable here, and no parity is implied.

## Coverage check against the gap documents

Per gap id: met / not met / recorded-as-proposal. **Pending completion** — the
checks performed so far are recorded under § Findings (CC-1..CC-3) and the
per-gap table is written before the PR.

## Interaction with PR #1314 (test-module-budget campaign)

Flagged by the operator mid-run: PR #1314 restructures the test corpus and this
branch must rebase onto it once it lands. Assessed at the time of writing —
**#1314 is open and unmerged**, `mergeable_state: clean`, 281 files,
+50848/−42993; `origin/main` is at `0682705`, which does not contain it.

The overlap with this branch is **two files**, both from D8's 460/G5 item:

| File | What #1314 does | Consequence |
|---|---|---|
| `test/plan-marshall/plan-retrospective/test_analyze_logs.py` | **deleted outright** (2440 lines removed, 0 added) | this run's docstring fix is lost on rebase and must be re-applied |
| `test/plan-marshall/plan-retrospective/test_analyze_logs_behavior.py` | survives, +3/−2 | this run's fix conflicts or needs re-application |

The deleted file's `test_per_column_mix_of_measured_and_unmeasured` moves to
`test_analyze_logs_dispatch_boundary_context_load_columns.py`, where it **still
carries the stale "three-way read" docstring**, as does
`test_analyze_logs_behavior.py`. So both 460/G5 sites survive #1314 unfixed and
re-applying is a re-edit at two known anchors, not a merge resolution.

Nothing else is exposed: #1314 touches neither `test/conftest.py` nor any file
under `test/pm-plugin-development/plugin-doctor/`, which is where this run's
remaining test work sits.

Two consequences recorded now so they are not forgotten at rebase time:

- A rebase **rewrites every commit SHA on this branch**. No commit message here
  quotes a same-branch SHA, so none goes stale — but the commit column in
  § Deliverables above does, and is re-derived after the rebase by pairing old
  to new with `git range-diff origin/main...{old} origin/main...{new}` (by patch
  content, never by subject).
- The full `./pw verify` is re-run on the **rebased** tree. #1314 restructures
  281 test modules; a green run on the pre-rebase tree is evidence about a tree
  that no longer exists.

## Contract check (Step 9)

*Pending — performed and appended as the last pre-merge commit.*

## What have we learned (Step 9)

*Pending.*

## Residue

*Pending — completed at finalization.*
