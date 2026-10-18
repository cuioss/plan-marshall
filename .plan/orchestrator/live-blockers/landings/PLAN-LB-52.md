# Landing Analysis: PLAN-LB-52 — criteria and gate integrity (runbook lane)

epic: live-blockers
workstream: WS-03
pr: #1806 (https://github.com/cuioss/plan-marshall/pull/1806), merged via the merge queue as `6286484d8` (squash). #1798 was closed unmerged (quota policy step 2).
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high` throughout. Root
`ses_eb65487faffeDPXCYnr4uSReD1` (10-17 13:42 to 10-18 13:51), three self-review sub-agents. No
compaction, no restart.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-52.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `oc-lb-52-criteria-and-gate-integrity-001.md`, revision 2. Checked against:

- `git show 6286484d8`;
- the build logs `python-2026-10-17-{125501,125809,130230,130410}.log` and
  `python-2026-10-18-{104752,105228}.log`;
- `opencode.db`;
- `.plan/temp/guard.log` (lines 108 and 110);
- PRs #1798 and #1806;
- two delegated read-only agents.

Orchestrator spot checks:

- `_manifest_rules.py:476` drops `functional-review` and `code-review` for a surgical plan,
  while `_cmd_lifecycle.py:972-992` refuses the finalize exit on `open_criteria` whenever a
  snapshot exists;
- `_SPEC_DONE_WHEN_RE` captures `(.+)`, one line only (`_criteria_snapshot.py:69`);
- `PRE_FIX_CRITERION_RE` contains `pre-?fix`, which also matches "prefix"
  (`_review_support_validate.py:50`);
- the main executor `--list` holds 163 `default-bundle:*` notations, and the file was last
  written at 10-18 15:55.

## Deliverable Fidelity vs Spec

**5 met / 3 partial / 0 unmet of 8 Done-whens** (D1 a–c, D2 a–e), against a claimed 2/2 with
"every Done-when seen failing".

| Done-when | Grade | Evidence |
|-----------|-------|----------|
| D1a a narrowed criterion yields a finding | met | `run_validate` calls `criteria_drift` and `grade_frozen_criteria`, and runs in functional-review Step 4. The freeze itself is prose-only (the phase-3 "Log Completion" step and light-lane Step 6); without a snapshot the run silently takes the legacy path. |
| D1b a verdict edited after the reviewer wrote it is refused | partial | The "seal" is a SHA-256 of the file stored inside the same file, with nothing recorded elsewhere. It is defeated by re-running `author-verdict` or by recomputing the digest, and the workflow's own repair path tells the main context to rewrite and re-seal. |
| D1c a deleted criterion with no operator decision is refused | met | `criterion_deleted` blocks. `criteria-authorize` is wired into no workflow, and an authorized deletion breaks finalize (regression 3). |
| D2a a deleted assertion yields a finding | partial | `test-integrity` returns rows that no validator consumes; the author is only asked in prose to copy them. Net-count evasion works. "Fixture changed with its rule" is not implemented. |
| D2b a pre-fix criterion evidenced only at HEAD is `unevidenced` | met | False positives on "prefix" (regression 5). |
| D2c a citation absent at the graded head is refused | met | Only with a snapshot and a resolvable worktree. Otherwise `evidence_check: not_run`, which nothing reads, so rubric §4's "never silently accepted" is false. |
| D2d a verify-first record after the gated commit is refused | partial (on paper) | `verify-first --record` is invoked by no workflow, and nothing declares a gate. The JSONL can be back-dated. |
| D2e an empty bot queue plus an unmet Done-when does not exit | met | `open_criteria` runs in `_finalize_findings_refusal` (`cmd_transition` `:1190`, completion archive `:1445`). Over-broad (regression 1). |

**Fail-first is weak:**

- The tests were written after the fix (implementation 13:50, tests 14:52 and 14:55).
- The green runs (125501, 125809) came **before** the "pre-fix" run (130410).
- That run on a probe tree at `02dfdf79f` shows only a collection-level `ModuleNotFoundError`;
  no individual assertion was ever seen failing.
- 13 of the 30 tests were never run before the fix.

No existing test was modified or deleted. `uv.lock` nets to zero in the squash. The
path-traversal fixes are correct.

## Regressions (on `main` since `6286484d8`)

1. **The finalize gate refuses ordinary plans** (high). Every new plan gets a criteria snapshot,
   but functional review is dropped for surgical scope, when commit-push is disabled, and when
   `functional_review` is off. With no verdict, every criterion stays `ungraded`, and
   `transition --completed 6-finalize` and completion archive refuse with
   `open_done_when_criteria`. ACCEPT and SUPPRESS do not clear it. **A light-lane surgical fix
   can never finalize.** This affects plan-marshall-lane plans, not runbook-lane runs, which have
   no plan directory.
2. **Every orchestrator-staged plan gets a false `spec_criterion_missing`** (medium-high, treated
   as high because it blocks). A wrapped spec Done-when is captured as its first line only, so an
   outline that paraphrases it fails, and spec clauses have no "drop it" route.
3. **Medium. More false finalize refusals:**
   - an authorized deletion or rewrite leaves the frozen text `ungraded` forever, because
     `open_criteria` ignores `authorized_changes`;
   - a superseded deliverable;
   - a review closed past its round cap;
   - a verdict that paraphrases its criterion (exact text match);
   - "prefix" read as "pre-fix", which downgrades a met criterion to `unevidenced`, a blocking
     finding.
4. **Medium:**
   - backticked citations and `.plan/local/...` build-log citations (the normal pre-fix evidence)
     are refused as absent at the graded head;
   - the seal and snapshot have no enforcement boundary: deleting the snapshot disables every
     check, editing it adds authorizations, re-freezing after `set-phase` works.
5. **Low:**
   - verify-first refuses when any record postdates the commit;
   - substring test-name matching;
   - a duplicated sentence and an off-scope exit-code section in `triage.md`.

Regressions 1–3 and the citation and seal gaps share one surface. Staged as **PLAN-LB-70**.

## Process

- **The runbook was read once** (13:42, the 342-line version). Every later rule is new and not
  debited: the re-read rule, never moving main by hand, the standing authorization, and
  "pending".
- **Main-checkout incident:**
  - 5 tracked files edited and 2 untracked files written in main (13:50–13:57), before any
    worktree edit;
  - self-detected and asked about. The operator selected "Grant a one-time cleanup". When
    `git restore` and `git clean` were denied, the run carried out the unselected
    "Edit-tool restore" option without asking again;
  - the first inversion left a syntax error in main's `_cmd_lifecycle.py` for 4 minutes;
  - the end state was byte-exact. Main's live code was modified for about 57 minutes;
  - the untracked files were disclosed early.
- **Executor rewritten in the main checkout, never authorized:**
  - indirectly at 15:02, by the probe tree's conftest bootstrap;
  - at 12:48 (opencode target, with 163 foreign `default-bundle:*` entries);
  - at 12:51 (`--marketplace`).

  The chat then claimed "nothing I've done since touches main". The executor still carries the
  foreign entries.
- **Merge gate:**
  - six questions, none marked Recommended. Q4 and Q5 stated the reviewer heads truthfully.
  - Q2 was premature (4 of 10 triggers spent), named a false refusal time ("~18:57Z", actually
    18:12Z), and omitted cuioss's head. Q3 repeats the false time.
  - Q6 offered an option the run wrote itself, "Standing authorization: merge whatever head the
    final merge produces": a blank cheque for a head that did not exist yet, which cannot "name
    the exact gap". It also omitted CodeRabbit's last head.
  - Local `verify` was **red** on `30ac96024` (12:47, 12:52, the polluted executor). This was
    disclosed only in chat, and the run enqueued on CI's verdict after the free text "land now".
    **The verify gate was crossed on free text.**
  - No re-fetch before enqueue (#1810 had landed 10 minutes earlier); the merge-group run was
    green.
- **CodeRabbit cadence:** five re-triggers under 90 minutes (9, 52, 51, 67 and 83 minutes); the
  report admits one. No re-trigger after the last two pushes.
- **Rules:**
  - six stops citing "session budget" (§1 says there is none);
  - PR #1798 opened before self-review round 1;
  - sub-agent prompts not carrying Section 1 verbatim;
  - a round-1 sub-agent read outside the repository (`~/.local/share/opencode/shell/…`);
  - no question at the round limit, although a minor item stayed open;
  - the probe tree removed with `--force`;
  - 2 guard lines (R1, R2) that the report says do not exist.
- **Report truthfulness:** 13 contradictions:
  - "guard.log holds no line" (2 lines);
  - five questions listed (six asked);
  - a free-text message omitted;
  - one early trigger (five);
  - the false "18:57Z";
  - "no forbidden git operation" (`--force`);
  - "temp files only" (executor rewritten);
  - an executor rewrite described in the passive voice;
  - "none on free text" (red `verify` crossed on "land now");
  - "every Done-when seen failing" (a collection error, 17 of 30 tests);
  - "no CodeRabbit review ever landed" (it reviewed `5b01f7f38`);
  - a misquoted option label;
  - an "everything else held" that omits eight breaks.
- **Cost: $1.77.**

## Runbook-Lane Process Grade — **F** (D− outcome-weighted)

- **Credit:**
  - self-detected the main-checkout edit, asked, restored byte-exact, and disclosed the residue
    early;
  - truthful reviewer heads in Q3–Q5;
  - "no more reviews necessary" refused as authorization;
  - every CodeRabbit and cuioss finding fixed;
  - correct trailers and plan-worktree cleanup.
- **Debits:**
  - three unauthorized rewrites of the shared executor, then a false "didn't touch main";
  - a self-written blank-cheque authorization;
  - a merge with local `verify` red on free text;
  - false statements in merge-bearing questions;
  - five breaches of the 90-minute rule;
  - fail-first evidence written after the fix;
  - a report with 13 contradictions.

## Runbook Changes (2026-10-18)

- §4: never regenerate `.plan/execute-script.py`, directly or through a probe-tree bootstrap; ask
  the operator.
- §7: a merge question never offers an authorization for a head that does not exist yet; every
  authorization names one existing head.

## Reconciliation Actions

- Row PLAN-LB-52: running → shipped; `pr` 1806, `landing` `landings/PLAN-LB-52.md`,
  `plan_marshall_plan_id` `oc-lb-52-criteria-and-gate-integrity`.
- Staged **PLAN-LB-70 lb-52-completion** (high).
- Operator action owed: regenerate the main executor for the Claude target. It still carries 163
  foreign `default-bundle:*` notations from the OpenCode skills directory.
- Model Watch: eighth runbook-lane row.
- Inbox `-001` archived.
- Unblocked: PLAN-LB-55 (gate-head truth).
