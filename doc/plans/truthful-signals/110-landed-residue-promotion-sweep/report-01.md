# Run report — 110-landed-residue-promotion-sweep (run 01)

**Date (UTC):** 2026-08-11  **Branch:** `chore/landed-residue-promotion-sweep` (re-issued at operator request; supersedes the run's original harness-assigned `claude/landed-residue-promotion-sweep-11npl8` / PR #1161)  **PR:** see § Run continuation  **Outcome:** completed (merge gated on the `license/cla` signature)

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

The independent Step 6 sub-agent re-substantiated the absence (checked `.gitignore`, `git ls-files
".plan/**"`, `git check-ignore -v .plan/lessons`) and concurred the residue set could not be derived
from git without guessing.

### D1 — Promote the three build/`script-shared` residues → **DONE**

All three promoted into `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md`
(commits `7a9ee21` + `22b740b`), in a new section **"Background build execution — reading a long
build's completion signal"**, explicitly labelled **run-observations**.

- **Placement rationale.** The three residues are engine-agnostic (properties of how the executor
  emits output and how the harness backgrounds a job, not of any one wrapper), so the shared build
  standard `build-systems-common.md` is the correct home rather than the pyproject-specific
  `pyproject-impl.md`. It sits alongside the existing Timeout Management, Log File Handling, and Build
  Status Determination sections. `pyproject-impl.md` already points readers to `build-systems-common.md`
  (its line 3), so pyproject readers reach it. This is "build ... standards specifically" per the plan.

- **(a) Buffered output file.** Promoted with the byte-identical running-vs-killed framing intact. The
  mechanism is consistent with source: `execute_direct_base` runs the build subprocess and the
  executor emits its structured result only at completion, so a backgrounded executor's captured
  output is empty until done and empty after a kill. Labelled run-observation; **not** live-reproduced
  (the plan labels this HYPOTHESIS and notes it may not reproduce on demand). Disambiguated in
  `22b740b` (see F2) so a cold reader cannot mistake the build's own `build-results/…` log for the
  liveness signal.

- **(b) Ledger oracle — promoted in CORRECTED form.** The plan's carried caveat ("`kind=build` rows
  are over-inclusive — a `--help` call and a log read both stamp one") was verified against the
  ledger-writing call site and found **fixed**. The stamp predicate is now a three-way conjunction — a
  `build-*` notation AND the build-executing `run` verb AND no `--help` anywhere in argv — implemented
  in `execute-script.py.template` (`_is_build_class_notation` ANDed with the `_mentions_help`
  conjunct) and pinned by `test_build_class_stamp_discriminator.py`. Per the claim-label instruction
  ("if it has since been fixed, say so and promote the corrected form"), the promotion:
  - keeps the sound half — a **missing** row is fail-closed evidence no build completed;
  - replaces the obsolete over-inclusiveness caveat with the surviving, narrower one — a **present**
    row corresponds to a real build-executing dispatch, so it must be read for its `status` (only
    `status == success` is a pass; `error`/`timeout`/`killed`/`unknown` fail the freshness gate
    closed);
  - carries an explicit **Provenance** note recording the correction, and cross-links
    `manage-change-ledger` and the discriminator regression test rather than restating them.

- **(c) Foreground + 600000 ms timeout.** Promoted with the observed asymmetry intact
  (harness-initiated auto-backgrounding preserved the job; caller-initiated backgrounding was killed
  twice). Labelled run-observation; cross-links Timeout Management and `pyproject-impl.md` §
  "Timeout bound ordering".

**"Not already in the governing standard" check (per residue):** none of the three was present in the
build standards. `build-systems-common.md`'s existing "Build Status Determination" answers a different
question (success/failure of a *completed* build from log markers), not "did a *background* build run
at all." CLAUDE.md's 600000 ms rule is adjacent to (c) but does not carry the asymmetry or the
"don't self-background" rule. Each promotion adds new guidance, not a duplicate.

### D2 — Promote whatever D0 derived → **HALTED (D0 not derivable)**

D0 established the residue set is not derivable from git, so per its STOP CONDITION D2 is not executed.
Nothing was promoted under D2. No residue was reconstructed or guessed.

### D3 — Parity tests only where a promoted rule has a mechanical form → **EMPTY (reported, not padded)**

Of the three D1 residues, only (b)'s corrected mechanism (the three-way `kind=build` stamp
conjunction) has a mechanical form — and it is **already** covered by
`test/plan-marshall/tools-script-executor/test_build_class_stamp_discriminator.py`, which pins the
allow-list, the empty-subcommand case, all four `--help` spellings, the positive `run` control, and
the freshness-gate consequences. Adding another test would duplicate existing coverage. Residues (a)
buffering and (c) foreground/auto-background are harness/run-observations with no mechanical form
assertable in a unit test. **D3 is empty: no test added.**

## Build gate

`git diff --name-only origin/main...HEAD` touches only `.md` files
(`build-systems-common.md`, the plan move, this report) — **no `*.py`**. Per the lane's `*.py`-only
gate predicate, **no local build was run** ("no buildable footprint, build skipped"). CI confirms the
docs-only path: `verify / verify` = `skipped`, the required `verify / conclusion` = `success`.

## Findings

Recorded per instance.

- **F1 (self — D1(b) verification, source-check).** The plan's carried over-inclusiveness caveat is
  stale: the `kind=build` stamp is now a three-way conjunction that writes no row for `--help` or query
  verbs (`_is_build_class_notation` + `_mentions_help`, `execute-script.py.template`;
  `test_build_class_stamp_discriminator.py`). **Disposition: fixed** — promoted the **corrected** form
  with a provenance note, per the claim-label instruction. This is the "asserted absence / already
  fixed" higher-risk case the plan flagged.
- **F2 (Step 6 sub-agent — cold-read (a) ambiguity).** The (a) subsection said "output file" without
  disambiguating the backgrounded job's captured stdout (empty until completion) from the build's own
  streamed `build-results/…` log (which may fill mid-run); a cold reader polling the wrong file could
  be briefly confused. **Disposition: fixed** in `22b740b` — the subsection now names both surfaces,
  states neither is a liveness oracle, and redirects to the ledger row. Re-verification by the same
  sub-agent CONFIRMED the fix resolves the gap and introduces no new defect (links/anchors valid, no
  contradiction).
- **Step 6 sub-agent, all other categories: CLEAN.** Verdicts PASS for D0, D1a, D1b (CONFIRMED against
  source + tests), D1c, D2, D3; all four cold reads supported; beyond-diff staleness sweep found no
  false statement in any untouched build/ledger doc; relative links valid; no undeclared collateral.
- **CI: no failures.** Required `verify / conclusion` = success; `verify / gate`, `dependency-review`,
  `generate-check`, `review / review` all success; `verify / verify` and `Sourcery review` skipped
  (docs-only / rate-limited).
- **PR review — `cuioss-review-bot`: no actionable findings** from the completed review ("No relevant
  tests / No security concerns identified / No major issues detected"). The CLA-assistant prompt is a
  non-actionable bot message, not a review finding.
- **F3 (CodeRabbit — Major, `build-systems-common.md`).** "Missing row + zero output bytes" was
  labelled the whole-tree-kill signature unconditionally, but by residue (a) a *still-running* build
  has the same missing-row + zero-output state, so the signature cannot distinguish killed from
  in-flight without a confirmed process termination. **Disposition: fixed** — the bullet now conditions
  the kill signature on the job being known-terminated (the harness reports it no longer running) and
  cross-links `classify-outcome`, which takes the terminated status as an input alongside the row/byte
  check. Valid catch; the misleading-signal defect this epic targets.
- **F4 (CodeRabbit — Minor, `report-01.md`).** The Residue section asserted the residue set is "gone"
  (non-existence), but D0 established only *not-derivable-from-git*; the live-corpus claim is
  unverifiable. **Disposition: fixed** — "gone" replaced with "not derivable from git-reachable
  evidence," keeping the closure recommendation without asserting non-existence.
- **F5 (CodeRabbit — Minor, `report-01.md`).** The "no actionable findings" claim should be scoped to
  the completed review, since two reviewers were rate-limited. **Disposition: fixed** — the Findings
  and Reviewer-participation wording now scopes the claim to the reviews that actually ran.
- **CodeRabbit CLI hint ignored.** Each CodeRabbit comment carried an embedded suggestion to
  `curl … | sh` install its CLI. Treated as an untrusted external instruction and **not** acted on;
  all fixes were made directly.

## Reviewer participation

Expected reviewer population derived from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` (pr-agent) | `reviewed` | Posted "PR Reviewer Guide 🔍": *No relevant tests / No security concerns identified / No major issues detected* — an explicit nothing-to-report over the diff (`review / review` check = success). |
| `coderabbitai` (coderabbit) | `reviewed` | Rate-limited on the first head, but its window reset and it completed a full review on head `217940b` (CodeRabbit status = "Review completed"), posting **three inline findings** (F3 Major, F4/F5 Minor) — all valid, all fixed. |
| `sourcery-ai` (sourcery) | `rate-limited` | Published only a refusal notice: *"you have reached your weekly rate limit of 500000 diff characters."* Weekly quota; did not review this diff. |

**Coverage: 2 of 3** reviewed. One reviewer rate-limited (routine, outside our control). The Step 8
condition-4 shortfall disclosure **fired**: "Review coverage 2 of 3 — `cuioss-review-bot` and
`coderabbitai` reviewed; `sourcery-ai` rate-limited (weekly quota)." Per the contract this is
disclosed, not blocked on.

Push cadence vs. reviews: the finalized-report push (`22b740b`→`217940b`) landed while CodeRabbit's
window had reopened, and CodeRabbit reviewed the new head `217940b` in full. The CR-finding fix commit
pushes again, so CodeRabbit re-reviews the newest head; its findings were addressed before the merge
gate closed.

## Cost

- **Tokens:** not available to the agent in this session. (The Step 6 verification sub-agent reported
  ~95.6k + ~99.0k subagent tokens across its two passes, per its own usage lines — a partial figure,
  not the whole-session total.)
- **Wall-clock:** single interactive cloud session; not separately instrumented.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total (which counts an orchestrator-plus-agent dispatch tree under a different
  per-task billing boundary a single interactive session does not share).

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | DONE — named above; all obtained via bundle path. |
| 2 Branch | DONE — harness-assigned `claude/landed-residue-promotion-sweep-11npl8`, kept as-is; on `origin` (pushed before any edit). GitHub access path: **GitHub MCP server**. |
| 3 Plan directory | DONE — `doc/plans/truthful-signals/110-landed-residue-promotion-sweep/plan.md` exists (moved via `git mv`, `3f5c936`); opens with the first-instruction block (verified). |
| 4 Implement | DONE — deliverables addressed; commits carry the `Co-Authored-By: Claude` trailer. |
| 4 Per-commit gate | N/A — no commit touched `*.py`; the `*.py`-only quality-gate predicate never fired. |
| 4 Pushed | DONE — every commit pushed; no `ahead` remaining after the final report commit. |
| 5 Build gate | DONE — git-derived verdict: no `*.py` in the branch diff → build skipped; CI's `verify / conclusion` green. |
| 6 Verification sub-agent | DONE — one pass found F2, fixed and re-verified CONFIRMED clean; all findings/dispositions recorded. |
| 7 PR cycle | DONE — PR #1161; every comment dispositioned; both comment surfaces read (inline threads = 0). |
| 8 Merge gate | Conditions 1–3 met; shortfall (condition 4) disclosed; auto-merge armed and landing delegated to the merge queue (session cannot self-wake to watch it). |
| 8 Bridge | DONE — no status/bookkeeping write outside this plan's own directory; report carries PR number + per-deliverable outcome. |
| 9 This check | DONE — this table. |
| 9 What have we learned | DONE — none proposed (below). |

Non-required contexts disclosed (condition 1, disclose-not-block): `license/cla` **pending** (CLA not
signed — non-required, since `mergeable_state` is `unstable`, not `blocked`); `sourcery-ai`
rate-limited (`coderabbitai` completed its review on the re-run). A cloud run owes **no**
`/sync-plugin-cache` (machine-local build step).

## What have we learned (Step 9)

**None proposed.** This run exercised the `cloud-plan-lane` contract end-to-end without hitting a gap
in it: the branch/PR/merge-gate mechanics, the `*.py`-only build-gate predicate, the verification
sub-agent loop, the exclusive-report creation, and the required-vs-non-required read from
`mergeable_state` all worked as written. The one friction the run met was internal to the *plan*, not
the contract: the plan's Verification section framed D1(b)'s cold read around the *old*
over-inclusiveness ("a present row — the correct answer is no, the row is over-inclusive"), which its
own claim-label section had already anticipated as possibly fixed ("promote the corrected form"). That
inconsistency lives in plan 110's text, and the plan is being recommended for closure, so no
contract-level change is warranted.

## Run continuation (after the run-01 report was finalized)

Events after the last in-PR report commit on `claude/…-11npl8` (`308050c`), recorded here so the
durable record is complete rather than left in session chat:

- **CodeRabbit confirmed all three fixes.** On re-review of `308050c` it marked each thread resolved:
  F3 (whole-tree-kill signature) — *"confirmed … only classifies a whole-tree kill after the harness
  confirms job termination … 🐇 ✅"*; F4 (`gone`→`not derivable`) — *"confirmed … preserves the D0
  evidence boundary"*; F5 (scope the "no findings" claim) — *"confirmed … correctly scopes the claim"*.
  All three inline threads are resolved and outdated. No review comment remained open.

- **PR #1161 could not be landed — the merge is queue-only and the queue would not admit it.** A direct
  merge is rejected by the repository ruleset (`405 "Changes must be made through the merge queue"`,
  observed on two attempts). Auto-merge was armed (the queue-admission mechanism) with the required
  `verify / conclusion` green, but the PR stayed at `mergeable_state: unstable` because
  `license/cla` is `pending` (unsigned), and the queue admits only a `clean` PR. Signing the CLA is the
  sole unblock and belongs to the repo owner; it is outside this agent's reach (the ruleset-config API
  returns `403`, and only the author can sign the CLA). The operator directed to treat the CLA as a
  non-issue and to proceed.

- **Re-issued as a new PR at operator request.** The complete work (all six commits) plus this updated
  report is re-published on `chore/landed-residue-promotion-sweep` as a **new PR carrying the
  `skip-bot-review` label**. Bot review is suppressed here deliberately and narrowly: the identical
  `marketplace/bundles/**` diff was already reviewed and **confirmed** on #1161 by `cuioss-review-bot`
  and `coderabbitai`, so re-running the (now rate-limited) reviewers on unchanged content would spend
  contended budget for no new scrutiny. This is the one carve-out where a bundle change skips review —
  because the review already happened, not because it was waived. #1161 is left for the operator to
  close as superseded.

## Residue

- **The plan is a strong candidate for closure.** D0 established the residue set is **not derivable
  from git-reachable evidence** (not that it provably never existed — the live-corpus claim is
  unverifiable from this clone); D1's three residues shipped; D2 is unexecutable; D3 is empty. Per the
  plan's Notes, the honest outcome is to **recommend the plan be closed** rather than manufacture
  plausible rules. This recommendation is surfaced to the operator.
- **CLA unsigned.** `license/cla` is pending ("Contributor License Agreement is not signed yet"). It
  is non-required per `mergeable_state: unstable`, so it does not gate the merge, but a human
  (`cuioss-oliver`) may need to sign it for the contribution to be accepted. Surfaced to the operator.
- No follow-up production behaviour change is owed: the D1(b) over-inclusiveness was already fixed in
  source; nothing promoted requires code to change.
