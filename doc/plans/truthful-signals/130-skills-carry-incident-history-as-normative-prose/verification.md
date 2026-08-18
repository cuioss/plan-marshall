# Verification — skills-carry-incident-history-as-normative-prose

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1163, commit `6792510a825a89d6aab77225c14b45b6d60b7087`   **Verdict:** implemented-with-gaps

## Method

What was actually done:

- Read `plan.md` and `report-01.md` in full.
- Located the landed commit (`git log --oneline --all --grep '#1163'` → `6792510a`, a squash of the
  branch); read the full stat (28 files, +1240/−302) and the complete diff for every
  `marketplace/bundles/**` path, `doc/analysis/uncompressed-output-measurement.md`, and
  `doc/refactor/README.md`.
- Opened at HEAD: `_analyze_incident_reference_in_docs.py` (whole file),
  `test_analyze_incident_reference_in_docs.py` (whole file), `_runner.py` (`run_quality_gate` and
  `run_analyze_marketplace_rules` dispatch sites), `_rule_registry.py`, `doctor-marketplace.py`
  (`_SUPPRESSIBLE_RULE_IDS`, the two count comments), `rule-catalog.md`, `rule-provenance.md`,
  `_analyze_historical_prose_in_skills.py` (to check the co-design claim),
  `ext-self-review-plan-marshall/SKILL.md`, `pr-agent.md`, `finalize-step-preference-emitter.md`,
  `unreachable-guard-detection.md`, `doc/analysis/uncompressed-output-measurement.md`.
- **Tests run:** `uv run python -m pytest test/pm-plugin-development/plugin-doctor/test_analyze_incident_reference_in_docs.py -o addopts="" -q` → **35 passed** (clean tree).
- **Functions executed** (not read): `incident_reference_targets(marketplace/bundles)` →
  **1094 files (671 `*.md`, 423 `*.py`)**; `analyze_incident_reference_in_docs(marketplace/bundles)`
  → **0 findings**.
- **Mutation check (highest-risk guard).** Saved `branch-cleanup.md` bytes to the scratchpad, then
  re-inserted the exact deleted narrative `Observed on plan-marshall#1045: the fix commit was
  reviewed by CodeRabbit and never by the required \`pr-agent\`.` into it. `test_real_marketplace_has_zero_findings`
  went **RED** (`[( .../branch-cleanup.md, 687, 'plan-marshall#1045')]`, 1 failed / 34 passed). A
  second mutation back-ticked the reference; the rule still fired (the `Observed on` opener matches
  outside the code span). Restored by copying the saved bytes back — md5 `610583497ad3409821e79d7c7bea4260`
  before and after, never via `git checkout`/`restore`/`stash`.
- **Coverage probes.** Built a synthetic bundle fixture in the scratchpad and executed the analyzer
  over it (via a throwaway test file under `test/`, deleted immediately after) to establish which
  narration forms the rule sees. Results below under D4.
- `git status --porcelain` at finish shows only other verification agents' untracked
  `verification.md` files; nothing of mine outside the two files written here.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | GATE: derive the population | occurrence list exists with derivation method stated | Yes | Yes | Yes | Partial | `report-01.md` § D1 — method (5 sweeps), volume and occurrence count reported separately. Two of the four widened forms the plan named (`as of 20YY`, `before 0.x.y`) are stated as zero-in-tree; re-derived: no such string in `marketplace/bundles/**` |
| D2 | Classify every occurrence DELETE/REPLACE | one verdict each; REPLACE names its mechanism | Yes | Yes | Yes | Partial | `report-01.md` § D2 — 2 DELETE, REPLACE families named with their mechanisms, KEEP set enumerated. The KEEP enumeration omits live in-scope-looking occurrences (see G4) |
| D3 | Apply the classified edits | edits applied, every normative claim preserved | Yes | Yes | Yes | Partial | 15 bundle files in `6792510a`; 38 incident tokens removed on 37 lines. Cold-read spot checks pass — `pr-operations.md:296` states "close the PR unmerged (the close-unmerged failure mode)"; `_locks_core.py:237` states the sibling-worktree blindness in full. One adjacent occurrence left (G1) |
| D4 | plugin-doctor rule, population-derived, publishes its population | rule ships, population-derived, publishes population | Yes | Mostly | Yes | Partial | `_analyze_incident_reference_in_docs.py`; registered in `_rule_registry.py:98`, `_runner.py:199` (quality-gate) and `:356` (analyze), `doctor-marketplace.py:276` (`_SUPPRESSIBLE_RULE_IDS`), `rule-catalog.md:748`, `rule-provenance.md:206`. Population executed → 1094 files. Detection covers a strict subset of the narration forms (G2, G3) |
| D5 | Three tests, each seen red pre-fix | (a) fires, (b) does not fire on corrected prose, (c) population asserted non-empty | Yes | Yes | Yes | Yes | 35 tests pass; `TestPositiveDetection` uses the exact pre-fix strings, `TestCorrectedMechanismProseNotFlagged` the exact post-fix strings, `test_targets_non_empty_over_real_marketplace` asserts `len(targets) > 0`. Non-vacuous: positives and negatives share `_make_skill_file`, so a broken fixture would fail the positives |
| D6 | Two transitional instances | first trimmed/relocated, second exempted-with-quarantine or escalated | Yes | Yes | Yes | Yes | `doc/analysis/uncompressed-output-measurement.md` — 343 lines removed, now 83 lines, snapshot gone, an explicit note names the snapshot nature and points to re-measuring. `doc/refactor/README.md` gained a quarantine banner in `6792510a` (the file was later replaced wholesale by `bb858993` (#1275) — superseded, not a gap for this plan) |

### D1 / D2 — the classification narrowed the pattern until the tree was clean

The run derived a "precise incident-narration pattern" and classified everything outside it as
KEEP/out-of-scope. That pattern is narrower than the plan's own Problem statement ("no marketplace
skill document reasons from an incident the reader cannot see"). Executed against a fixture of eight
realistic narration forms, the shipped rule fires on **two**:

| Form | Fires? |
|---|---|
| `The #990 defect described in the Ordering rationale above.` | yes |
| `This is the PR #866 failure mode.` | yes |
| `The failure mode #990 closed cannot recur.` (noun before ref) | no |
| `` The failure mode `#990` closed `` (ref back-ticked) | no |
| `On #1027 PR-Agent posted its Guide while reporting no major issues.` | no |
| `It has also returned CLEAN over real defects on #1013, #1022 and #1027.` | no |
| `as of 2026-07 the check is green.` | no |
| `before 0.1.1240 the writer emitted both keys.` | no |

The last two are forms the plan's D1 explicitly named. Live instances of the third, fourth, fifth
and sixth rows exist in the tree today (`finalize-step-preference-emitter.md:91-175`,
`automatic-review/SKILL.md:646`, `unreachable-guard-detection.md:154-173`). See G2/G3/G4.

### D3 — one adjacent occurrence left inconsistent

`marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` has two
consecutive paragraphs about two regression test files. Line 390 was edited by D3 (`the two PR #1067
defects` → `the two defects`, `the #1067 head ref` → `the pre-fix head ref`). Line 388, two lines
above it, still reads *"pins the **PR #1013** pre-fix scanning and post-fix anchored forms"*. Same
document, same section, same shape, opposite treatment. See G1.

### D4 — "publishes the population" is satisfied only in the negative

`analyze_incident_reference_in_docs` emits an `empty_population` finding (`population_size: 0`) when
`incident_reference_targets` returns `[]`, so a vacuous clean verdict is distinguishable from a real
one. On a non-empty run the size is never emitted — `run_quality_gate`'s `rule_summaries` entry
carries only `{'rule': label, 'findings': n}`. The plan's stated purpose ("a rule reporting clean
over an empty file set is indistinguishable from a clean tree") **is** met by the empty-population
finding; the literal instruction "publish its population size" is not. Recorded, not filed as a gap.

## Report accuracy

Contradictions found in `report-01.md`, checked by re-derivation at HEAD and at `6792510a`:

1. **"no `#866`/`#1081`/`#948`/`#1067`/`#1045`/`#895-898` token remains"** (§ Deliverables, D3) —
   contradicted. `git grep -nE '#(866|1081|948|1067|1045|895|896|898)\b' -- marketplace/bundles`
   returns one hit at both `6792510a` and HEAD:
   `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_incident_reference_in_docs.py:41`
   (`` ``#948 sibling-worktree shape`` ``, a back-ticked pattern-documentation example inside the
   rule the same PR added). Harmless in substance; the sentence as written is false.
2. **"32 tests"** (§ Deliverables, D5) and **"33/33 tests pass"** (§ Findings) — the file that landed
   in `6792510a` contains **35** test functions, and 35 pass at HEAD. The 32/33 figures were true at
   intermediate commits and were never re-derived at the pre-merge commit, which the report's own
   Step 8 requires.
3. **"26 canonical occurrences across 15 files, plus 9 adjacent"** (= 35) (§ D1) — re-derived from
   the landed diff: **38** incident tokens on **37** removed lines across **15** bundle files. The
   file count reproduces exactly; the occurrence partition does not.
4. **"(post-#895/#896/#898) parenthetical … at phase-6-finalize/SKILL.md:151"** and
   **"branch-cleanup.md:659"** — both line numbers verified correct against `6792510a~1`.
5. **The KEEP enumeration** (§ D1 "Softer references present but OUTSIDE the precise pattern") names
   `pr-agent.md`/`sourcery.md` as the bot-data-sheet carrier of `#103`-style references. It does not
   name `automatic-review/SKILL.md:646`, `bot-participation-contract.md:275`, or
   `review_completeness.py:16`, all of which carried `on #1027 PR-Agent posted its Guide` at
   `6792510a~1` and still do. Those occurrences are covered only by the blanket "softer references"
   clause, not by an enumerated verdict — a shortfall against D2's *Done when* ("every occurrence in
   D1's list carries exactly one verdict"). See G4.

Checked and found accurate: the D3 file list (15), the mechanism names introduced (close-unmerged,
accepted-not-landed, sibling-worktree, unbound-consent, pre-fix — all five present in the tree), the
registration sites (registry, runner ×2, suppressible set, catalog, provenance), the co-design claim
(the rule imports `_config_layer_suppresses` / `load_default_suppression_config` /
`read_frontmatter_disable_list` from `_analyze_shared` — no fourth framework), the unconditional
exemption posture (`_is_allowlisted` returns `False` for every path; no `no-incident-references` key
in `config/default-suppression.yml`), the two `doctor-marketplace.py` count comments made
count-neutral (lines 257 and 495 of the pre-image), and both D6 dispositions.

## Out-of-scope compliance

Compliant. The landed diff touches exactly the declared surface: 15 bundle files under
`marketplace/bundles/**` (D3), the plugin-doctor rule home + catalogue + provenance + registry +
runner + driver (D4), the plugin-doctor tests and `_fixtures.py`/`test_runner.py` bookkeeping (D5),
and the two `doc/` files (D6), plus the plan-directory move and the run report. No orchestrator
ledger, run report, or `.plan/` content was rewritten. No detector framework was duplicated — the
rule reuses `_analyze_shared`. The `test_runner.py` and `_fixtures.py` edits are the coverage-gate
and canonical-label-order bookkeeping the report discloses, not undeclared collateral.

## Residue carried forward

| Report residue item | Still open at HEAD? |
|---|---|
| CLA / `license/cla` not signed | Closed — the PR merged as `6792510a` |
| Review coverage 1-of-3 (coderabbit rate-limited, sourcery silent) | Closed by the merge; historical |
| Softer refs left in place: `#849` | **Open** — `verification-feedback.md:110`, `branch-cleanup.md:432,1399`, `phase-6-finalize/SKILL.md:230` |
| `#812` (mostly back-ticked) | **Open** — `manage-metrics/SKILL.md:166,295`, `data-format.md:356,419,493,672,673,675`, `manage-metrics.py:1457,2766,3562`, `phase-5-execute/SKILL.md:1358` |
| `#884` | **Open** — `phase-6-finalize/SKILL.md:230` |
| `#990` (back-ticked) | **Open** — `finalize-step-preference-emitter.md:91,93,100,104,175` |
| `#565` | **Open** — `manage-metrics.py:469` |
| `#979` | **Closed** — present at `6792510a` (`_build_execute_factory.py:409`), absent at HEAD; removed by a later change, not by this plan |
| Worked-example provenance in `unreachable-guard-detection.md` | **Open** — lines 30, 52, 80, 84, 125, 154, 157, 159, 160, 169, 173 |
| Code-comment provenance citations, `# SHIM(…)` markers | **Open** — by design, shim-governed |
| Proposed contract note: name the CLA check in the lane's merge gate | Not verifiable from this clone (an operator decision on `.claude/skills/cloud-plan-lane/SKILL.md`); the current lane doc still does not mention a CLA gate |

## What could NOT be verified

- **The full `./pw module-tests` figures** (18990 passed / 14 skipped / 0 failed). Only the rule's own
  test file was executed here (35 passed). The whole suite was not run.
- **The pre-PR verification sub-agent's cold read.** The report states an independent agent judged
  every edited passage actionable without the incident. That judgement is not reproducible from the
  tree; spot cold reads of `pr-operations.md`, `_locks_core.py`, `branch-cleanup.md` and
  `_github_pr.py` performed here agree with it, but this is a sample, not the same check.
- **The plan's Notes sequencing obligation** ("Sequence LAST among the finalize-surface plans, or
  scope D3 to exclude any file with an in-flight owner and record the exclusions as residue"). The
  report does not address it and cross-plan in-flight ownership is not observable from this clone.
- **The claim "per-phase token figures have been retired as unreliable by this epic"** — the plan
  itself labels this not verifiable from the clone. D6's trim does not cite it, which is what the
  plan asked for.
- **`doc/refactor/README.md`'s quarantine banner as a durable outcome** — the whole file was replaced
  by `bb858993` (#1275) after this plan landed. Verified present in `6792510a`; superseded since.
- **Two unrelated working-tree modifications** (`execute-script.py.template`,
  `git-workflow.py::scan_artifacts`) were present when this verification started and disappeared
  during it; they belong to concurrent verification sessions, not to this plan or to this check.
