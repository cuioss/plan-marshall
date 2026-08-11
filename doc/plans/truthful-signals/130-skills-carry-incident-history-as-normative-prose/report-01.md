# Run report — skills-carry-incident-history-as-normative-prose (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/skills-incident-history-prose-l55k2b` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action, via project `.claude/skills/`)
- `plan-marshall:ref-code-quality` (read from bundle path)
- `pm-plugin-development:plugin-script-architecture` (read from bundle path)

Conditional surface skills were not separately loaded; the work is prose edits plus one
stdlib-only plugin-doctor analyzer + pytest, both covered by the two always-load skills and the
mirrored sibling rule `_analyze_historical_prose_in_skills.py` + its test.

## D1 — Population (GATE, mutates nothing)

**Derivation method.** Widened well beyond the seed pattern with content greps over
`marketplace/bundles/**`:

- broadest sweep `#[0-9]{2,}` (243 raw matches) to inventory every hash-number token;
- PR/issue URL sweep `github\.com/.../(pull|issues)/[0-9]+` — **all placeholder examples**
  (`org/repo`, `owner/repo`), zero real incidents;
- dated / version-pinned narration `as of 20YY`, `before 0.x.y`, `since 0.x.y` — **zero** in the
  bundle tree;
- narration markers `Observed on`, `plan-marshall#`, `post-#`, `pre-#`, `since #`, and the
  term-of-art form `#NNNN (failure mode|signature|shape|defect|incident)`.

**Population scanned (volume):** every file under `marketplace/bundles/*/{skills,agents,commands}/**`
(the crawled bundle tree). This is the file volume, reported separately from the occurrence count
below per the plan's Verification note.

**Raw `#NNNN` inventory (243 matches) partitions into:**

- **Out of scope — not plan-marshall incident references:** hex colour codes (`#59636e`,
  `#000`, `#121212`, …), markdown/URL anchors (`#10d-...`), syntax-teaching examples
  (`Fixes #123`, `Closes #456`, `Refs #789`, `pr#123`, `Issue: #123`, `#212` sample output),
  and **external-tracker** issues (cui-open-rewrite `#118`, OpenCode `#9292` /
  `anomalyco/opencode#8619`, Claude Code `GitHub Issue #10346`). None reason from an unseeable
  plan-marshall incident.
- **In-scope incident references — plan-marshall history used as narration / term-of-art:**
  the families below.

**In-scope occurrence count (the precise incident-narration pattern, the D3/D4 surface):**
26 canonical occurrences across 15 files, plus 9 adjacent bare/back-ticked/multi-line tags in the
same files cleaned for consistency. Families:

| Family | Mechanism it names | Occurrences (files) |
|---|---|---|
| `#866` | immediate merge on a merge-queue-required base **closes the PR unmerged** | pr-operations.md, _github_pr.py |
| `#1081` | a merge verb reports the **call was accepted, never that the merge landed** | _github_pr.py, gitlab_ops.py |
| `#948` | a cwd-scoped read is **blind to a holder in a sibling worktree** → reads as absent | _status_query.py, _locks_core.py, merge_lock.py, git-workflow.py, manage-locks/SKILL.md, cwd-keyed-store-resolution-audit.md, scope-limited-negative-is-unknown.md |
| `#1067` (consent) | a merge consent that **names no tree** can be recalled at a different HEAD | branch-cleanup.md |
| `#1067` (detectors) | the two self-review pre-fix defects the detectors pin against | ext-self-review SKILL.md, _self_review_patterns.py, _self_review_detectors.py |
| `#895/#896/#898` | (pure history parenthetical on the "current model") | phase-6-finalize/SKILL.md |
| `plan-marshall#1045` narrative | the force-done review-coverage incident narrative | branch-cleanup.md |

**Softer references present but OUTSIDE the precise pattern (classified KEEP in D2):** `#849`
(ci:wait ratchet), `#812` (metrics end_time/floor-not-truth — mostly back-ticked), `#884`,
`#990` (back-ticked), `#565`, `#979`, worked-example provenance (`#1013/#1022/#1027/#1038` in
`unreachable-guard-detection.md`), code-comment provenance citations (`PR #160 review`, `PR #629`,
etc.), `# SHIM(...)`/`shim-floor:` markers (`#1105`, `#666`, …), and the automatic-review bot
data-sheets (`pr-agent.md`/`sourcery.md` `CONFIRMED on #103`).

## D2 — Classification (one verdict per occurrence)

- **DELETE (2):** branch-cleanup.md:659 `Observed on plan-marshall#1045:` incident sentence
  (the preceding sentence already states the mechanism — *"byte-identical to one earned by a
  genuine pass … nothing downstream could distinguish reviewed from forced"*); and
  phase-6-finalize/SKILL.md:151 `(post-#895/#896/#898)` parenthetical (adds nothing to "the
  CURRENT model").
- **REPLACE (the rest of the firing set):** each incident label swapped for the mechanism it
  names — `#866`→"close-unmerged signature/failure mode", `#1081`→"accepted-not-landed
  signature", `#948`→"sibling-worktree shape", `plan-marshall#1067`→"unbound-consent shape",
  `pre-#1067 defect`→"pre-fix defect" (finding IDs `8da924`/`3e04a8` and commit SHAs kept as the
  durable provenance).
- **KEEP / out-of-scope (softer refs above):** each names its mechanism in-place (reader can act
  without seeing the incident), or is provenance/external/shim-governed, or is a genuinely
  **referential** record (bot data-sheets citing where a contract field was confirmed;
  `rule-provenance.md` / `rule-catalog.md`). **None is reached by the precise incident-narration
  pattern**, so none requires a permanent exemption entry.

**Exemption finding (the plan's asserted-absence claim).** Confirmed: **no occurrence requires a
permanent exemption.** The genuinely-referential contexts fall outside the precise pattern
(case-sensitive `Observed on` excludes lowercase mid-sentence "observed on #103"; the term-of-art
form requires an incident noun adjacent to the ref). The D4 rule therefore ships **unconditional**;
the shared config-suppression capability remains available (a future maintainer can register a
prefix) but carries **zero entries** for this rule — no unused bespoke exemption mechanism is added.

## Deliverables

- **D1 — Population (GATE).** Done. Derivation method and counts recorded above.
  Population (volume) reported separately from the in-scope occurrence count, per the plan.
  Commit `5345178`.
- **D2 — Classification.** Done. Every occurrence carries exactly one verdict (DELETE / REPLACE /
  KEEP-out-of-scope); REPLACE verdicts name their mechanism. Asserted-absence claim confirmed: no
  occurrence requires a permanent exemption. Commit `5345178`.
- **D3 — Apply edits.** Done, commit `e8faca9` (15 files). 2 DELETE + the REPLACE families;
  every normative claim preserved (verified: the precise incident-narration pattern returns zero
  matches over `marketplace/bundles`, and no `#866`/`#1081`/`#948`/`#1067`/`#1045`/`#895-898`
  token remains). The mechanism names introduced: close-unmerged, accepted-not-landed,
  sibling-worktree, unbound-consent, pre-fix.
- **D4 — plugin-doctor rule.** Done, commit `c01fa0d`. New `no-incident-references` scanner
  (`_analyze_incident_reference_in_docs.py`) co-designed with the sibling
  `no-historical-prose-in-skills` (same `_analyze_shared` exemption machinery — not a fourth
  framework), extended to `*.py` scripts. Population-derived over the bundle tree via
  `incident_reference_targets()`, published and asserted non-empty (anti-vacuity). Wired into
  `run_quality_gate` (build-failing) and `cmd_analyze`; registered in the rule registry, the
  suppressible-rule set, `rule-catalog.md`, and `rule-provenance.md`. Ships **unconditional** — no
  registered exemption prefix, because D2 found no occurrence requiring one.
- **D5 — Tests.** Done, commit `c01fa0d` (`test_analyze_incident_reference_in_docs.py`, 32 tests).
  (a) fires on `Observed on plan-marshall#NNNN` and every narration form (markdown and python);
  (b) does **not** fire on the D3-corrected mechanism prose (the load-bearing negative proving
  REPLACE not DELETE); (c) population derived and asserted non-empty over the real tree.
  Red-first evidence: (a)/(c) fail without the analyzer (which did not exist pre-change); (b) uses
  the exact pre-fix incident strings D3 removed as the positive fixtures and the exact corrected
  strings as the negatives, so the pair discriminates — a rule that had fired on corrected prose
  would fail (b). The zero-match-suite coverage gate and canonical-label-order gate were updated
  for the new rule.
- **D6 — Two transitional instances.** Done, commit `68846f1`.
  - `doc/analysis/uncompressed-output-measurement.md` — trimmed to the durable SKIP-both decision
    and its structural rationale; removed the point-in-time snapshot (per-window token totals,
    transcript/branch counts, top-noisiest tables, named plans with billed figures) the epic no
    longer stands behind; a note makes the snapshot nature explicit and points to re-measuring.
  - `doc/refactor/README.md` — confirmed a genuine maintainer roadmap (self-describes as "planning
    documents, not implementation"). **Not deleted**; quarantined with an explicit banner declaring
    it planning material intentionally exempt from the current-state documentation standards,
    scoped to the `doc/refactor/` tree. This is the plan's "if kept, quarantine it clearly" path.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (the new analyzer, tests, and comment-only
edits to several bundle scripts), so the gate takes its full path.

- `./pw quality-gate` — **pass**: mypy "no issues found in 392 source files", ruff "All checks
  passed!", SPDX header check passed, plugin-doctor `total_issues: 0` with the new
  `analyze_incident_reference_in_docs` rule running and reporting 0 over the tree.
- `./pw module-tests` — first run: 18988 passed, 2 failed (both expected new-rule bookkeeping: the
  canonical rule-label-order golden and the zero-match-suite coverage gate). Both fixed
  (label list + firing fixture) and re-verified green in isolation together with the provenance
  and new-rule tests (60 passed). Authoritative full re-run recorded in the Findings/Contract
  sections below.

## Findings

_(pending — verification sub-agent, CI, PR review)_

## Reviewer participation

_(pending)_

## Cost

_(pending)_

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

_(pending)_
