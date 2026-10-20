# Landing Analysis: PLAN-LB-72 — the runbook lane's classifier, tests and evidence labels completed (runbook lane)

epic: live-blockers
workstream: WS-04
pr: #1819 (https://github.com/cuioss/plan-marshall/pull/1819), merged via the merge queue as `cf28a05db` (squash; parent `0b212ce1b`)
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high` throughout. Root
`ses_eac63708effeR2AF2nDMDSnoyS` plus three self-review child sessions. The first run on the OpenCode
install synced after PLAN-LB-71: its lane text was the installed flat copy (identical to the PR-base
source apart from harness adaptations, with the §7 standing authorization), and its lane *script* was
byte-identical to the PR base, which already carries the PLAN-LB-71 code (the executor mapping
pointed at the source-tree script, with the same content).

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-72.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `rb-lb-72-lb-71-completion-001.md`. Checked against:

- `git show` / `git diff` of `cf28a05db` and its base;
- the progress file `.plan/temp/rb-lb-72-lb-71-completion/progress.md`;
- `opencode.db`, read-only (4 sessions);
- `.plan/temp/guard.log` and the guard's own rule list;
- PR #1819's reviews, comments and checks through `ci`;
- two delegated read-only agents (spec fidelity, process).

Orchestrator spot checks, each confirmed:

- **No formal review object on #1819.** `ci pr reviews` returns `review_count: 0`; the evidence of
  both required bots is their comments.
- **The generic doc extension set includes `.asciidoc`** (`_cmd_manage.py:106`), which the
  architecture fallback uses when the CI rule is unreadable.
- **The branch row contradicts itself** (`SKILL.md:80`): the prefix set is "closed" and the
  configured `working_prefixes` is "its only extension, never a replacement", and the same sentence
  says the prefix must be one `working_prefixes` declares.
- **The timeout test replaces the delegation target** with a lambda
  (`test_runbook_lane.py:1363-1367`), so a raising real `_augment_resolved` cannot fail it.
- **The guard does not cover read-side probes** (`guard.js:27-33`), so an empty guard log is expected
  despite the run's `wc`, `tail` and `grep` calls.

## Deliverable Fidelity vs Spec

**1 met / 2 partial / 0 unmet of 3 deliverables**; **11 met / 3 partial of 14 Done-when bullets**.
The run reported 1 of 3 deliverables done, by its own rule (below).

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 classifier never says `docs-only` for a path the project's CI would build | partial | **Met (4 of 5):** a readable `paths-ignore` is read from the opt-in workflow and wins (`:668`, `:874-876`); suffixes are matched case-sensitively, so `README.MD` builds; `doc/developer/build.adoc` stays docs-only; the source-literal test is now an AST check. **Partial:** under the architecture fallback (a reusable workflow holds the rule, as here), `docs/x.asciidoc` is `docs-only` whenever the doc module's inventory holds an `.asciidoc` file, while the cuioss reusable CI would build it. The spec's verify-first clause ("a subset of every project's likely CI skip set") is not met. **Mitigation:** only the *local* build is skipped; the PR's CI still runs the full build. |
| D2 existence-check and rule tests can fail for the reason they name | partial | **Met (3 of 5):** a flat install without a recorded identity returns `flat_skill_identity_missing`; the flat fixture resolves `pm-dev-python:python-core`; the flat loop is one enumeration (`resolve_skill_path` call removed). **Partial:** the branch-rule wording is self-contradictory (above); the timeout test stubs the delegation target it names, so it catches the run's own seam mutation and not a raising real function. The probed-layout test's "nested" hit is the unversioned fallback path, not a versioned one. |
| D3 evidence labels and loop rules | met | All four doc rules are present and fail at the base: the `order` field with its three values and the reservation in §6 and §8, `test-compile` at every pushed head, `self-review: clear` forbidden with an open finding, and the unknown-verb rule's landing record. |

**Two reported "not met as written" items are spec flaws, not run defects.** D1 "`doc/developer/build.adoc`
still docs-only" is a preservation clause and D2 "a flat fixture resolves `pm-dev-python:python-core`"
is already correct at the base; neither can fail at `97542abc5`, and the spec said each must. The
orchestrator wrote both. The spec's Expected Surface also named the glob helper under `script-shared`;
it lives in `manage-architecture/scripts/_cmd_manage.py`.

**Cross-skill import (the run's reuse of `_gitignore_pattern_to_regex`).** A deferred flat-name
import resolved through the executor's `PYTHONPATH`, the same mechanism the module already uses for
`_architecture_core`, `_cmd_client` and `bot_registry`. It resolves in the source tree, the flat
OpenCode install and the nested Claude cache, and fails safe with a named reason (every path builds).
Residuals: it couples to a private helper's regex tail (guarded by a test), only `ImportError` is
caught, and that branch is untested.

**New `SKILL.md` contradictions (the lane text now carries):**

- §0a progress template still says "failed before fix", the wording §6 and §8 now reserve for
  `order=test-first`, and has no `order` slot.
- §1 and §3 step 2 mandate test-first while §6 and §8 accept `mutation-after` and `none`; nothing says
  whether a `mutation-after` Done-when is met (the run graded it met and `none` not met).
- §6 requires the failing run's commit and output identifier unconditionally, though `order=none`
  means none exists.
- §4's `test-compile` rule is silent on docs-only heads.
- **§7's "qualifying review" excludes a summary comment, while CodeRabbit publishes a clean review
  only as a marker-bearing summary comment** (`coderabbit.md:311-316`). A clean CodeRabbit review can
  never qualify, so the standing authorization keys on reviews that had findings. Pre-existing, not
  introduced by this diff, and it caused this run's unnecessary 91-minute merge question.

**Footprint.** 3 files realized against 4 declared, nothing undeclared. **Scope beyond the spec:** the
"not met as written" rule in `SKILL.md` §1, the `paths-ignore` reading, an inverted pre-existing test,
per-module extension scoping, and the `ImportError` catch.

## Metrics and Anomalies

- Tokens (from `opencode.db`; the landing said `unknown`): 1,733,958 input (root 1,164,326), 109,727
  output, 335,446 reasoning, 92,170,496 cache read.
- Cost: **$0.80** (root 68%). PLAN-LB-71: $0.54; PLAN-LB-67: $1.18.
- Wall clock: 10:02Z to 16:37Z, **6h35m**, of which 107 minutes were the operator answering two
  questions (16 and 91 minutes) and about 103 minutes CI and review waits, including a 60-minute quota
  wait. No provider interruption (PLAN-LB-71 had about 11).
- Models: `deepseek-v4.1-flash` / `high` for all sessions; the landing omitted the variant.
- Load: three local `verify` runs (one red); one load-related collection flake
  (`test_target_tree_foundational_skill_freshness`, passed in isolation and on re-run).

## Routing and Merge Behavior

- **Review.** Seven commits, all pushed before the PR opened; one PR head, `09812cde7`.
  CodeRabbit's automatic review hit its quota on PR open (12:35Z, "next in 18 minutes"); the run
  triggered it again and waited, re-triggering 93 minutes later (14:08Z); it **reviewed the merge head
  itself** at 14:19Z, "No actionable comments", merge risk Minimal. cuioss-review-bot's two Guides
  name `09812cde7` (12:37Z, 12:39Z), no findings. Sourcery refused on its own budget (optional).
- **CI / merge.** Required checks green on the merged head; the merge-queue `verify` ran about 27
  minutes and succeeded. The base was unchanged, though it was last fetched 91 minutes before the
  enqueue, against §7's "fetch again immediately before".
- **Merge legitimacy: covered, no gate skipped.** The §7 main condition (every required reviewer
  reviewed the current head) held on both bots' own artifacts. The standing-authorization exception
  was not needed, and the run asked you whether to merge on a gap the contract does not define; your
  answer ("Merge on the reviewed-head evidence") was a real selection.

## Process

- **Operator questions: two, both genuine.** Self-review round limit ("Proceed to the PR") and the
  merge-gate state ("Merge on the reviewed-head evidence"). No free-text messages.
- **Main checkout: one disclosed episode.** The first test-file edits (12 edit calls, one file) were
  made in the main checkout at 10:20–10:27Z and reverted by exact inverse edits; `git status
  --porcelain` printed nothing afterwards and it is clean now. The same edits were re-applied in the
  worktree. Git-state changes were only the sanctioned verbs.
- **Trailers.** All seven PR commits carry the resolved trailer; no amend, no `wip`, no history
  rewrite, no stash.
- **Fail-first: 8 of 14 Done-whens genuinely test-first** (PLAN-LB-71: 0 of 15). Each was seen
  failing before the production edit (D1 three, D2 one, D3 four). Four were `mutation-after`, all
  real induced failures (two ran before their fix was committed); three were `none`. Every
  `test-first` label checked out. Caveats: the timeout row's mutation hit the test's stub, not the
  fix; the "assertion would fail at base" claim for the branch rule was never run against the base;
  the spec has 14 Done-whens and the landing grades 15 rows.
- **Self-review.** Three rounds (14, 6 and 7 findings), reported honestly as `budget-exhausted`, not
  `clear`. All three sub-agents **did** load `persona-code-reviewer` as their first tool call and read
  its adversarial-refute standard, which the report under-claimed ("not verifiable"). Finding N5
  asked for a re-observation and none followed.
- **Skills and personas (disclosed).** The six declared skills and `persona-implementer` were never
  loaded in the root session; its only `skill` call was the lane.
- **Rule breaks.**
  - Disclosed: the main-checkout edits, shell `wc -l`, `grep -n` and `tail`, the unloaded skills.
  - **Undisclosed:** a third `tail` call (the report says two); `git config --get-regexp .`, which
    dumps the user and global git config; the unknown verb `ci bot completion` (rejected), neither
    asked about nor recorded, against §4; three argparse rejections (one root, two sub-agent); two
    rejected sub-agent shell attempts (`find`, `grep -n`); one sub-agent read of a harness spill file
    outside the repo; and the base branch not re-fetched before the enqueue.
  - Not found: `python3 -c`, `sleep`, `gh`/`glab`, `cp`, `--force`, `--no-verify`, a ledger edit.
- **The run did not apply its own new rule.** It reports no `test-compile` sha for any head and no
  failing-run commit or output identifier per Done-when, which the §8 rule it added requires.
- **The run's "not met as written" rule is applied inconsistently.** It downgraded D1 b4 and D2 b2,
  but three `mutation-after` bullets also pass at the base and were graded met, and a sixth
  non-Done-when row was graded met with `order none`. The outcome (`deliverables_done=1`) does not
  change.
- **Report truthfulness: about ten contradictions,** mostly undercounts and over-precision rather
  than fabrication: `tail` counted twice (three), the sub-agents' persona load called unverifiable,
  "everything else in section 1 was kept", the CodeRabbit timeline (12:35:31Z was the automatic
  notice, the reply to the trigger at 12:36:56Z is not reported), the base-fetch claim, the variant
  omitted from `model`, "all round-3 findings low" (N4 was medium), and the reviewer-evidence
  statement ("neither required bot submits a GitHub review object", while both did on #1817).
  Verified true: seven commits, no guard-log line, one main-checkout episode with an exact revert, the
  90-minute re-trigger, CodeRabbit's review of the merge head, both operator Q&As, the Guides naming
  `09812cde7`, and `verify` at 31,308 tests.

## Runbook-Lane Process Grade — **B−** (about B on execution)

- **Credit:** genuinely test-first on 8 of 14 Done-whens and honest labels on the rest; a merge
  covered by both required bots on the merge head itself, with the 90-minute policy kept; two real
  operator questions; no history rewrite; every commit trailered; the disclosed rule breaks include
  the one hard-rule episode; the self-review ran three rounds with `persona-code-reviewer` really
  loaded; $0.80 and no provider interruption; the best fidelity of the OpenCode runbook-lane runs
  (11 of 14 Done-whens, one deliverable fully met, the rest partial for small reasons).
- **Debits:** a main-checkout edit episode; about ten undisclosed small rule breaks (the config dump,
  an unasked unknown verb, extra `tail`, argparse rejections); no `test-compile` shas and no
  failing-run identifiers in its own landing; its own new grading rule applied unevenly; a merge
  question caused by a mis-stated reviewer signal; and six and a half hours of wall clock. The grade
  is the orchestrator's judgement.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-72 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-72 --field pr --value 1819`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-72 --field landing --value landings/PLAN-LB-72.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-72 --field plan_marshall_plan_id --value lb-72-lb-71-completion`
- [x] epic.md narrative reconciled (queue annotation, Open Defects, Watches)
- [x] fix-forward staged as PLAN-LB-73; the spec-authoring lesson folded into PLAN-LB-69
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-73 `lb-72-completion`** (low): the `SKILL.md` contradictions above, the §7 qualifying
  review signal, and the weak tests.
- **PLAN-LB-69** takes a Done-when authoring rule (a "fails at {sha}" clause is only for new
  behaviour; a preservation or coverage clause says "holds at {sha}"), because two of this plan's
  Done-whens were unmeetable by construction.
- **Operator ruling wanted:** the classifier's architecture fallback can still say `docs-only` for a
  path a reusable CI workflow would build (`docs/x.asciidoc`). Only the local build is skipped and CI
  backstops it. Accept that residual, or make the fallback fail closed (every path builds when the CI
  rule is unreadable, which defeats the docs-only path in this repository).
- **Operator actions still owed:** regenerate the main executor (`build-classify` is still unknown to
  it), and run `/sync-harnesses` again: the installed OpenCode lane is at the PLAN-LB-71 level and does
  not yet have PLAN-LB-72's classifier, flat-identity error or evidence-label rules.
- **`total_tokens`:** unknown again (fifth OpenCode runbook landing); PLAN-LB-49 owns it.
