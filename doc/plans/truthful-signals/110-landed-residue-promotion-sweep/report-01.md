# Run report — 110-landed-residue-promotion-sweep (run 01)

**Date (UTC):** 2026-08-11  **Branch:** `claude/landed-residue-promotion-sweep-11npl8` (harness-assigned, kept as-is)  **PR:** _pending_  **Outcome:** completed

## Skills loaded

- `cloud-plan-lane` (first action, before reading the plan) — the working contract.
- `plan-marshall:ref-code-quality` (always) — read from bundle path.
- `pm-plugin-development:plugin-script-architecture` (always) — read from bundle path.
- `pm-plugin-development:plugin-architecture` (conditional: the change edits skill standards under
  `marketplace/bundles/`) — read from bundle path.

`persona-implementer` / `python-core` / `pytest-testing` were **not** loaded: the change is docs-only
(a standards `.md`), no production or test Python is touched. No skill was unobtainable by both routes.

## Deliverables

### D0 — GATE: is the promotable residue set derivable from git-reachable evidence? → **NOT DERIVABLE**

**Verdict: the residue set cannot be derived from git-reachable evidence.** This triggers the plan's
STOP CONDITION — D2 is halted and D1 shipped alone.

**Derivation method attempted (git-reachable evidence only, mutating nothing):**

1. **Confirm the input set is unreachable from this clone.** The residue set was bound as ~24 lesson
   identifiers in a `manage-lessons` store under `.plan/`. `.gitignore` line 46 ignores `.plan/*` with
   exactly two exceptions (`!.plan/marshal.json`, `!.plan/project-architecture/`); `git ls-files
   ".plan/**"` returns only those two trees. There is no lessons store, no plan directory, and no
   orchestrator ledger tracked in git. The lesson identifiers are therefore **unresolvable** here —
   the OBSERVED, load-bearing absence the plan names.
2. **Assess whether git-reachable evidence can reconstruct the promotable set.** A *promotable
   residue* is the generalizable rule underneath a specific lesson whose fix shipped but whose rule was
   never written into standards. Git records what fixes **shipped** (commits, merged PRs) and what the
   standards **currently say** — but it carries **no mapping** from a retired lesson identifier to "the
   generalizable rule that lesson recorded and that was never promoted." That mapping existed only in
   the git-ignored lessons store.
3. **Conclusion.** Any residue set produced from commit messages, PR bodies, or the epic's own plan
   prose would be **inference about what a dated identifier probably meant** — the reconstruction D0's
   stop condition and the plan's "do not reconstruct" rule explicitly forbid. An unresolvable
   identifier is dropped and reported, never guessed. → **NOT DERIVABLE.**

**Population:** the input was ~24 lesson identifiers, **zero** resolvable from this clone. The plan's
secondary claim (the authoring machine's live corpus held 23 active lessons, none from the dated
range) is **not verifiable from this clone** and is recorded, not relied upon.

### D1 — Promote the three build/`script-shared` residues → **DONE**

All three promoted into `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md`
(commit `7a9ee21`), in a new section **"Background build execution — reading a long build's completion
signal"**, explicitly labelled **run-observations**.

- **Placement rationale.** The three residues are engine-agnostic (properties of how the executor
  emits output and how the harness backgrounds a job, not of any one wrapper), so the shared build
  standard `build-systems-common.md` is the correct home rather than the pyproject-specific
  `pyproject-impl.md`. It sits alongside the existing Timeout Management, Log File Handling, and Build
  Status Determination sections — the exact neighbourhood. `pyproject-impl.md` already points readers
  to `build-systems-common.md` (its line 3), so pyproject readers reach it. This is "build ...
  standards specifically" per the plan.

- **(a) Buffered output file.** Promoted with the byte-identical running-vs-killed framing intact. The
  mechanism is consistent with source: `execute_direct_base` runs the build subprocess and the
  executor emits its structured result only at completion, so a backgrounded executor's captured
  output is empty until done and empty after a kill. Labelled run-observation; **not** live-reproduced
  (would require starting a long build and reading the output file mid-run — the plan labels this
  HYPOTHESIS and notes it may not reproduce on demand).

- **(b) Ledger oracle — promoted in CORRECTED form.** The plan's carried caveat ("`kind=build` rows
  are over-inclusive — a `--help` call and a log read both stamp one") was verified against the
  ledger-writing call site and found **fixed**. The stamp predicate is now a three-way conjunction — a
  `build-*` notation AND the build-executing `run` verb AND no `--help` anywhere in argv — implemented
  in `execute-script.py.template` (`_is_build_class_notation` ANDed with the `_mentions_help`
  conjunct) and pinned by `test_build_class_stamp_discriminator.py` (query verb, bare `--help`, and
  `run --help` all write no row). Per the claim-label instruction ("if it has since been fixed, say so
  and promote the corrected form"), the promotion:
  - keeps the sound half — a **missing** row is fail-closed evidence no build completed (the
    whole-tree-kill signature);
  - replaces the obsolete over-inclusiveness caveat with the surviving, narrower one — a **present**
    row corresponds to a real build-executing dispatch, so it must be read for its `status` (only
    `status == success` is a pass; `error`/`timeout`/`killed`/`unknown` fail the freshness gate
    closed);
  - carries an explicit **Provenance** note recording the correction, and cross-links
    `manage-change-ledger` and the discriminator regression test rather than restating them (avoids the
    duplication defect).

- **(c) Foreground + 600000 ms timeout.** Promoted with the observed asymmetry intact
  (harness-initiated auto-backgrounding preserved the job; caller-initiated backgrounding was killed
  twice). Labelled run-observation; cross-links Timeout Management and `pyproject-impl.md` §
  "Timeout bound ordering" for the harness ceiling.

**"Not already in the governing standard" check (per residue):** none of the three was present in the
build standards. `build-systems-common.md`'s existing "Build Status Determination" answers a different
question (success/failure of a *completed* build from log markers), not "did a *background* build run
at all." CLAUDE.md's 600000 ms rule is adjacent to (c) but does not carry the asymmetry or the
"don't self-background" rule. So each promotion adds new guidance, not a duplicate.

### D2 — Promote whatever D0 derived → **HALTED (D0 not derivable)**

D0 established the residue set is not derivable from git, so per its STOP CONDITION D2 is not executed.
Nothing was promoted under D2. No residue was reconstructed or guessed.

### D3 — Parity tests only where a promoted rule has a mechanical form → **EMPTY (reported, not padded)**

Of the three D1 residues, only (b)'s corrected mechanism (the three-way `kind=build` stamp
conjunction) has a mechanical form — and it is **already** covered by
`test/plan-marshall/tools-script-executor/test_build_class_stamp_discriminator.py`, which pins the
allow-list, the empty-subcommand case, all four `--help` spellings, the positive `run` control, and
the freshness-gate consequences. Adding another test would duplicate existing coverage (the
duplication defect the plan tracks). Residues (a) buffering and (c) foreground/auto-background are
harness/run-observations with no mechanical form assertable in a unit test. **D3 is therefore empty:
no test added.**

## Build gate

`git diff --name-only origin/main...HEAD` touches only `.md` files
(`build-systems-common.md`, the plan move, this report) — **no `*.py`**. Per the lane's `*.py`-only
gate predicate, **no local build was run** ("no buildable footprint, build skipped"). The merge queue's
`merge_group` run verifies the docs-only change before it lands.

## Findings

Sources: the D1 verification-against-source I performed, the Step 6 verification sub-agent, CI, and PR
review. Recorded per instance.

- **F1 (self, D1(b), FIXED-IN-SOURCE → corrected promotion).** The plan's carried over-inclusiveness
  caveat is stale: the `kind=build` stamp is now a three-way conjunction that writes no row for
  `--help` or query verbs (`_is_build_class_notation` + `_mentions_help`, `execute-script.py.template`;
  `test_build_class_stamp_discriminator.py`). Disposition: promoted the **corrected** form with a
  provenance note, per the claim-label instruction. This is the "asserted absence / already-fixed"
  higher-risk case the plan flagged.
- _(Step 6 verification-sub-agent findings appended below.)_
- _(CI / PR-review findings appended below.)_

## Reviewer participation

_Derived from the `author_login` of each `automatic-review/standards/{bot_kind}.md` registry doc;
filled in after the PR review cycle._

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| _pending_ | _pending_ | _pending_ |

Coverage: _pending_. Step 8 shortfall disclosure: _pending_.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** single interactive cloud session; not separately instrumented.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total (which counts an orchestrator-plus-agent dispatch tree under a different
  per-task billing boundary a single interactive session does not share).

## Contract check (Step 9)

_Filled in at Step 9, committed as the last pre-merge commit._

## What have we learned (Step 9)

_Filled in at Step 9._

## Residue

- **The plan is a strong candidate for closure.** D0 established the residue set is gone (not
  derivable from git); D1's three residues shipped; D2 is unexecutable; D3 is empty. Per the plan's
  Notes, the honest outcome is to **recommend the plan be closed** — not to manufacture plausible
  rules. This recommendation is surfaced to the operator (Step 9 / What have we learned).
- No follow-up production behaviour change is owed: the D1(b) over-inclusiveness was already fixed in
  source; nothing promoted requires code to change.
