# Run report — 050-plan-state-and-records-test-reduction (run 02)

**Date (UTC):** 2026-08-16 **Branch:** `claude/test-quality-plan-execution-evap45` **PR:** [#1266](https://github.com/cuioss/plan-marshall/pull/1266) **Outcome:** completed

This run does **not** execute the plan's deliverables. It closes the findings run 01 recorded as
**"recorded, not fixed"**, on operator instruction ("fix all the findings"). The plan's own residue —
D2's remaining builders, D3's missing fixture modules, D4's over-budget modules, D5's parametrization
— is untouched and stays in run 01's § Residue. Scope is stated here so the two are not conflated:
**a finding is a defect this plan surfaced; residue is deliverable scope it did not reach.**

## Skills loaded

Run 01 recorded skipping Step 1 and reported it as a deviation. This run loads them, which is the
correction.

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) |
| `plan-marshall:ref-code-quality` | bundle path — always-load |
| `pm-plugin-development:plugin-script-architecture` | bundle path — always-load |
| `pm-dev-python:pytest-testing` | bundle path — conditional: Python tests |
| `pm-dev-python:python-core` | bundle path — conditional: Python production code (the doctor rule) |

Every skill resolved by bundle path; none was unobtainable.

## Deliverables — the seven findings

### #13 — rule 7 cannot tell a named value from a cited record — **FIXED** (`d210db0`)

The `test-docstring-historical-prose` rule scoped itself to docstrings and comments, on the reasoning
that the same textual shapes appear far more often as string-literal test data. That discriminator is
right and **insufficient**: prose has to name values as well as cite records. A docstring stating the
id a generator returns, or a comment naming the task file a command creates, states the contract under
test and cites nothing.

Shape cannot separate the two. **Formatting can**: an identifier named as a value is written in an
inline literal; a citation appears bare in the narrative. Rule 7 now skips a match inside a backtick
span or a quoted string, which gives the rule a convention it can teach — **backtick the value you
name**.

The exemption is **per occurrence, not per segment**, so backticking one identifier cannot launder the
rest of a sentence. Three tests pin the new behaviour, including that mixed case; all 18 pre-existing
rule-7 tests still pass unchanged, because every one of them cites a **bare** id in narrative position.

**The 24 → 0 drop, split honestly by cause** — re-derived, not recalled:

| Measurement | `test-docstring-historical-prose` over the ten plan-state directories |
|---|---|
| `origin/main`, rule as shipped | **24** |
| `origin/main` corpus, **new rule** | **16** |
| this branch (new rule + corpus) | **0** |

So **the rule change alone clears 8; the remaining 16 came from editing the corpus** — backticking
14 task ids that prose names as values, and rewriting 2 genuine citations. Stating that split rather
than claiming the rule did the work: the convention is the fix, and the corpus now follows it. A
reader who assumed the rule alone took 24 to 0 would over-credit it.

**A live instance of the defect, found during the fix.** The docstring explaining the new discriminator
used a real-shaped lesson id as its example, and the sibling `no-lesson-id-in-skill-prose` rule — which
governs `marketplace/bundles/**` and does **not** carry this exemption — flagged it. The example is now
a shape placeholder, which documents the rule better anyway. **Recorded, not fixed:** that sibling rule
has the same false-positive class over bundle prose. It was left alone because bundle prose rarely needs
to name a lesson id as a value, so the case for widening the exemption there is unproven — and this run
had no evidence for it beyond one self-inflicted instance.

### #28 — `detect_outcome_for_diffed_tasks` name versus selector — **NOT a production defect; test fixed** (`d210db0`)

Run 01 recorded this as a *possible production defect* it could not resolve, because doing so required
reading a `marketplace/bundles/**` file the plan forbids editing. Read this run:
`analyze-logs.py:866` already documents the behaviour at its definition site — the per-task SHA range
is not persisted anywhere stable, so `status: done` is a **deliberately over-inclusive proxy** and the
LLM rule applies the diff guard downstream.

So the production code is correct and self-explaining. The defect is test-side: a reader of
`test_detect_outcome_for_diffed_tasks_regression` had no way to see why the selector says `done` when
the function and its `tasks_with_diff_no_outcome` key both say *diff*. The test docstring now states
the proxy. **No production change was needed, and none was made.**

### #29 — duplicate `plan_id` across two tests — **FIXED** (`d210db0`)

`test_mark_step_done.py` used `'mark-step-legacy-force'` in two tests. They are safe only while
`plan_context` grants each test a fresh root; if that isolation ever weakened, the second `cmd_create`
would collide and the failure would present as a canonicalization bug rather than a fixture-name
collision. The ids are now distinct.

### #35 / #36 — stale epic-brief references — **FIXED** (`d210db0`)

`doc/plans/test-quality/README.md` and `findings-test-corpus-review.md` both still described
`test_audit_checks.py` as a live ~8,700-line module. Run 01 deliberately left them, because the briefs
are read concurrently by plans `030`–`080` and editing them risked a collision the epic README itself
warns about. That risk has since resolved: **#1258 merged**, so the file genuinely no longer exists and
the briefs were simply wrong. Both now describe the outcome rather than the pre-split state.

### #38 — `test_audit.py` over budget, five checks unmapped — **FIXED** (`386066b`)

At 1,509 lines it was the last module in the directory over the 400-line budget, and it held the five
`SKILL.md` checks no filename mapped. Split into **15 modules**, all within budget.

**All 24 of 24 checks in the SKILL.md inventory now map to a module by filename**, up from 19. The five
that gained one:

| Check | Module |
|---|---|
| `dispatch-topology` | `test_audit_check_dispatch_topology.py` |
| `execution-context-manifest` | `test_audit_check_execution_context_manifest.py` |
| `finalize-flow-conformance` | `test_audit_check_finalize_flow_conformance.py` |
| `lane-lever-effectiveness` | `test_audit_check_lane_lever_effectiveness.py` |
| `merge-window-accounting` | `test_audit_check_merge_window_accounting.py` |

`execution-context-manifest` is the one that needed reading rather than pattern-matching: its tests are
the step-owner-drift cluster, which the old section banner named ("execution-context-manifest
owner-drift") while the filename did not.

**Verified a pure move:** 82 test functions before, 82 after, none missing or added (AST inventory);
**555 collected items at `origin/main` and 555 after**, measured in a worktree rather than recalled.

⭐ **This split slices by LINE range between section banners, not by AST node range** — directly
applying run 01's own lesson. That run's decomposition sliced by node and silently dropped 162 column-0
comments including 8 rationale blocks, because **a leading comment belongs to no AST node**.

**Measured, not asserted:** 290 comments before, 276 after — 44 occurrences did not carry over, and
every one is information-free or deliberately replaced. 28 are `# ---` separator rules, meaningless
once each section is its own file; 2 are `noqa` pragmas suppressing the import preamble that no longer
exists (`ruff check` passes without them); 14 are the section banners themselves, replaced by module
docstrings stating the same contract. **No fixture invariant and no cross-reference was lost** — the
class run 01's finding #30 was about. What did not survive is issue-number provenance (`#849`, `#812`,
`#852 D6`), which lived only in those banners; that is a deliberate B3 strip, not an accident.

Three changes beyond the move, each a consequence of it:

- **The directory was loading `audit.py` twice**, under two `sys.modules` names — this module via
  `sys.path` + `import audit`, its sibling via `spec_from_file_location`. The new modules take the one
  loader in `_audit_fixtures.py`. Safe to consolidate: the module has **zero** `monkeypatch` calls and
  its only attribute reads are `audit.__doc__`, identical either way.
- **`_write_log` existed in two incompatible shapes** — a 2-arg single-line writer here, the 3-arg
  shared writer in `_audit_fixtures`. The local one is the shared one with a fixed filename, so it is
  gone rather than hoisted, and its call sites now name the log file they write, which is the part that
  matters because the name must match the glob.
- `minimal_corpus` is used by four of the new modules and moved to `_audit_fixtures.py`.

**A bonus catch the split surfaced:** the section banners cited deliverable ids and PR numbers
("Deliverable 2 (a): … (#849)"). Rule 7 never caught them — it matches `deliverable D<n>`, not
`Deliverable 2`, and `PR #<n>`, not a bare `#849`. Each banner is now a module docstring stating what
its check asserts in the present tense. **Recorded:** rule 7's `_PLAN_DELIVERABLE_ID_RE` and
`_PR_REFERENCE_RE` do not match these two spellings. Not widened here — widening a matcher without a
measured false-positive rate is how the rule acquired the problem #13 just fixed.

### #39 — commit message off-by-one — **NOT FIXABLE**

`984c257`'s message says the prose count went "66 to 25" where the tool said 24. Commit messages are
immutable history; run 01's report already carries the re-derived figure. Recorded, not actionable.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **32 files** of 35 changed. Python footprint
present, so the gate applies.

`./pw verify` → **`=== verify: SUCCESS ===`**, 20,325 passed, 14 skipped, whole tree.

Per-commit gates: both commits touch `*.py` and both were preceded by a clean direct
`./pw quality-gate`, read from the tools' own output (`ruff … All checks passed!`, `mypy … Success: no
issues found in 408 source files`, `SPDX-header check passed`) since the direct path emits no
structured log.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | This run, while fixing #13 | The new rule docstring's own lesson-id-shaped example tripped the sibling `no-lesson-id-in-skill-prose` rule — a live instance of the very false-positive class | **Fixed** — example replaced with a shape placeholder |
| 2 | This run, while fixing #13 | The sibling `no-lesson-id-in-skill-prose` rule has the same citation-vs-datum gap over `marketplace/bundles/**` | **Recorded, not fixed** — no measured false-positive rate there; widening on one self-inflicted instance is how #13 arose |
| 3 | This run, while fixing #38 | `test_audit.py` section banners cited deliverable ids and PR numbers that rule 7 does not match (`Deliverable 2`, bare `#849`) | **Fixed in the corpus** (banners became present-tense docstrings); **matcher gap recorded, not widened** |
| 4 | This run, while fixing #38 | The directory executed `audit.py` twice under two `sys.modules` names | **Fixed** — one loader for the directory |
| 5 | This run, while fixing #38 | Two incompatible `_write_log` helpers in one directory | **Fixed** — the near-duplicate is gone, not hoisted |
| 6 | This run, verifying #28 | Run 01 recorded a *possible production defect*; the production docstring already documents the proxy | **Rejected as a production defect, with reason** — fixed test-side instead |
| 7 | **PR review — `coderabbitai`** | `_INLINE_LITERAL_RE`'s newline bound does not cover the SAME-line case: two apostrophes in one sentence still span a citation between them | **Fixed** — quote delimiters may not sit against a word character; its text added verbatim as a negative control |

### Independent pre-PR verification (contract Step 6)

Dispatched read-only against run 01's findings table. It wrote its own AST and probe scripts rather
than reading, and it found a **blocking regression this run introduced** plus a real false-negative
class in the rule-7 fix. Both are closed; nothing it raised was rejected.

**⛔ BLOCKING — the split broke `finalize-step-era-stamp-fill`, and that step's own test passed anyway.**

`era_stamp_fill.py:37` hard-coded `TEST_REL = '…/test_audit.py'`, the file commit `386066b` deleted.
`run()` checks existence before the token check, so the step returned **`status: error`, exit 1, on
every invocation** — where it previously returned exit 0 / `skipped: true`. It is a registered
project-local finalize step at **order 21, pre-merge, `mutates_source: true`**, so the next plan
running finalize in this repository would have hit it.

**Why no test caught it is the more important half:** `test_era_stamp_fill.py:47` *re-declared* the
constant instead of importing `era_stamp_fill.TEST_REL`, and the fixture **creates** that path under
`tmp_path`. All 15 tests therefore passed against a synthetic worktree regardless of the real tree —
precisely the "fixture hardcodes a retired value and still passes" class the contract's Step 6
instruction names.

Fixed: `TEST_REL` repointed at `test_audit_check_era_model.py` (where the era mirror actually landed),
and **the test now binds to `era.AUDIT_REL` / `era.TEST_REL`** so a future repoint cannot diverge from
production again. Verified **empirically**, not by inspection: the step now returns `status: success`,
`skipped: true`, exit 0, mutating nothing. Four further surfaces naming the deleted file were repointed
— the step's `verdict_inputs:` frontmatter (machine-read), its SKILL.md prose and `git add` line,
`phase-6-finalize/standards/source-edit-pushability.md`, and two test comments.

**⛔ Rule 7's fix had a false-negative class — the serious direction.** Two independent bugs, both
closed:

| Bug | Effect | Fix |
|---|---|---|
| `_INLINE_LITERAL_RE`'s quote alternatives matched across newlines, and a prose segment arrives as ONE multi-line string | An English **possessive apostrophe** opened a "literal" span swallowing everything to the next apostrophe — 7 lines in one observed case — silently exempting every citation inside. Verified live on this corpus: `PR #515` and `PR #887` were being silenced | No alternative may cross a newline (`'[^'\n]+'`) |
| `_LESSON_BACKTICK_ID_RE` understood only **single** backticks, while this repo's house convention is RST double backticks | The one guard designed to keep narrative lesson citations flagged was defeated by the house style, so 6 genuine citations became exempt | Matcher accepts `` `{1,2} `` |

Both named citations are confirmed flagged again, and two **negative-control tests** now pin the
hazards — the verifier's point that the three original tests pinned only the intended behaviour, never
the failure mode. Slice 050 remains at **0** after both fixes, so the exemption still does its job.

**Quality defects in the corpus edits — all fixed.** The verifier read them as "the edit followed the
regex rather than the meaning", which is fair: ``` ``TASK-001``.toon ``` and ``` ``TASK-001``.json ```
backticked *half a filename* when the value is the whole name (the assertion two lines below reads
`'TASK-001.json'`); ``` ``TASK-001``/002/003 ``` named only the first element of a sequence; and
`property-1` — which I introduced replacing `D1` — was defined nowhere in its file, the same dangling
class as run 01's finding #33, and arguably worse since `D1` at least resolved to something.

**Documentation contradictions — all fixed**, including one false claim of my own:

| Surface | Defect | Fix |
|---|---|---|
| `doctor-test-conventions.md` | Asserted a "**24/24** false-positive rate", inherited unverified from run 01 — contradicted by this report's own "2 genuine citations rewritten" | Corrected to **22 of 24**, with the two real ones named |
| `rule-catalog.md` | Still taught only the prose-vs-data discriminator; a reader would not learn the backtick convention exists | Both discriminators documented, including the newline bound and why it exists |
| `doc/plans/test-quality/README.md` § B3 | Unconditional "**Never**: … a lesson id" — would classify this run's own corpus fix as a violation, and plans `030`–`080` read this brief | "Never cite" is not "never name": the formatting distinction is stated |
| `persona-module-tester/standards/testing-methodology.md` | Same unconditional list, and it is the teaching surface `rule-catalog.md` points at | Same clarification |

**Accepted and acted on, minor:** `_PROBE_LOG_NAME` was duplicated verbatim in two modules, which
`_audit_fixtures.py`'s own stated rule ("helpers more than one test module needs") says belongs in the
fixture module — hoisted. And this report's claim that line-slicing "carries **every** comment along"
was false as written: 290 → 276, and the corrected passage now gives the measured split.

**Confirmed clean by the verifier**, recorded so its verdict is not read as unexamined: the split is a
pure move at AST level (82/82 callables, 0 docstring diffs, 555/555 collected, free names resolve);
all twelve textual definition changes are value-preserving, each traced individually; the 24 → 0
decomposition matches its own independent 2×2 measurement exactly; **zero** remaining duplicate
`plan_id` literals across all ten directories, swept by AST; `test-module-line-budget` for the audit
directory is **0**; and every file in the diff maps to one of the findings, with `test/conftest.py` and
`test/_shared/**` untouched.

**Recorded, not fixed:**

- `test_test_conventions_rule6.py` is named for rule 6 but holds tests for rules 6 **and** 7; this run
  added 5 more rule-7 tests to it. Pre-existing, mildly aggravated. Renaming it is plan `010`'s
  surface, and a rename mid-flight would collide with any concurrent work there.
- `ruff format --check` fails on 3 of the 15 new modules — and on 48 pre-existing files at `main`.
  `build.py` runs `ruff check`, not `ruff format`, so this is not a regression and not a gate.

**What the verifier could not establish**, carried forward rather than presented as clean: it could
not execute the mutating finalize step (permission-blocked), so its regression finding was derived by
inspection — **this run closed that gap by running the step**; and it did not re-derive that each test
still exercises the same production path under the new fixture import, treating the green run as
strong evidence rather than proof.

## Reviewer participation

**Population derived from configuration**: the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc.
**M = 3.** Each verdict is read from the author's own comment bodies across all three surfaces.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence |
|---|---|---|---|
| `coderabbitai` | **reviewed** | — | Initially refused ("Review limit reached … **next review available in 9 minutes**"). **Re-requested after the window elapsed, and it reviewed** — publishing one actionable finding against `_INLINE_LITERAL_RE`, reproduced and fixed below. |
| `cuioss-review-bot` | **reviewed** | — | *"PR Reviewer Guide 🔍 — PR contains tests / No security concerns identified / No major issues detected."* An explicit nothing-to-report over the diff. |
| `sourcery-ai` | **rate-limited** | **yes** | *"you have reached your **weekly** rate limit of 500000 diff characters. Please try again later."* Clears on the weekly reset; no specific time stated. |

**Coverage: 2 of 3** — up from 1 of 3, because the `Reopens?` value was acted on rather than merely
recorded.

⭐ **The re-request is the whole point of the `Reopens?` column, and it paid out.** CodeRabbit's
`Reopens? yes` carried a 9-minute countdown, so re-requesting was productive rather than futile —
unlike `sourcery-ai`, whose refusal on #1258 was a per-diff size ceiling that would never clear.
Waiting cost minutes and bought the one finding neither this run nor its own verification sub-agent
had found.

**Contrast worth recording:** the *same* reviewer, `sourcery-ai`, refused #1258 on a **per-diff** 150k
ceiling (`Reopens? no`) and this PR on a **weekly** 500k quota (`Reopens? yes`). Same verdict, opposite
handling — which is exactly why the verdict alone cannot carry the decision.

### CodeRabbit's finding, and why it mattered

**It found a residual false negative in the very fix that closed the previous one.** My own
verification sub-agent found the *multi-line* case — quote alternatives crossing newlines — and I
bounded them to a single line. CodeRabbit pointed out that the bound does nothing for the **same-line**
case:

```text
The resolver's PR #515 guard doesn't fall through.
```

Two apostrophes, one line, and the span between them swallows the citation. Reproduced against the
shipped analyzer before changing anything:

```text
spans : [(12, 35)] -> ["'s PR #515 guard doesn'"]
result: nothing flagged
```

**Fixed:** a quote delimiter may no longer sit against a word character. That is the discriminating
property — a possessive or contraction apostrophe is *always* preceded by a word character, an opening
delimiter never is. Verified in all four directions: the citation flags; `key is '<id>',` and `writes
"TASK-001.json" into` stay exempt; the mixed case still reports the bare citation beside a backticked
value. Slice 050 remains at **0**.

CodeRabbit asked for its text as a negative control; it is now
`test_two_apostrophes_on_one_line_do_not_open_a_literal_span`, using the sentence verbatim, with a
docstring recording that the newline bound alone does not cover this — so the two guards are not later
collapsed into one. Answered on the thread.

**Every comment on all three surfaces is dispositioned**: one actionable finding (fixed), one
nothing-to-report review, one quota refusal, and this run's own two comments. `get_review_comments`
returns `totalCount: 0` — no inline threads.

**Shortfall disclosure (§ Step 8 condition 4) — it fired:**

> Review coverage: **2 of 3**. `coderabbitai` reviewed after a re-request and its finding is fixed;
> `cuioss-review-bot` reviewed and reported no issues. `sourcery-ai` is rate-limited on a **weekly**
> 500,000-diff-character quota and **reopens** on the weekly reset, with no time stated. Merging on
> 2-of-3.

## Cost

- **Tokens:** not available to the agent in this session — the harness exposes no per-session figure
  to the running agent, so no number is given rather than an estimated one.
- **Wall-clock:** not separately instrumented. The durable timestamps are the commit times on the
  branch and the PR's `created_at`.
- **Population:** one interactive Claude Code cloud session plus one dispatched verification
  sub-agent. ⛔ **Not comparable** to a plan-marshall `metrics.toon` total, which counts the
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary. This
  session does not share that boundary and emits no `metrics.toon`.

## Contract check (Step 9)

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **DONE** | Five, all by bundle path — § Skills loaded. This is the correction of run 01's recorded deviation |
| 2 Branch | **DONE** | `claude/test-quality-plan-execution-evap45`, **harness-assigned**, restarted from `origin/main`. The PR for it had merged, so the merged-PR rule and the lane's keep-the-assigned-branch rule agree: same name, new base. GitHub had auto-deleted the remote branch at merge, so publishing it was a fresh push, not a force-update — the first `--force-with-lease` failed on a stale ref, which is what surfaced the deletion |
| 3 Plan directory | **N/A, and stated rather than assumed** | This run executes no plan file; `doc/plans/test-quality/050-…/plan.md` already exists from run 01 and carries the first-instruction block. Nothing was moved |
| 4 Implement | **DONE** | Six commits, each carrying the trailer, none with a "Generated with Claude Code" footer |
| 4 Per-commit gate | **DONE** | Every commit touching `*.py` was preceded by a clean direct `./pw quality-gate`, read from the tools' own output (`ruff … All checks passed!`, `mypy … Success: no issues found in 408 source files`, `SPDX-header check passed`). The final report-only commit touched no `*.py`, so the gate did not apply |
| 4 Pushed | **DONE** | `git status -sb` reports nothing ahead. One lapse, caught and corrected: the PR-number edit was deliberately held to batch with the Step 9 sections, which is the one move the push-cadence rule forbids — a completed unit left uncommitted. Committed and pushed on the spot |
| 5 Build gate | **DONE** | git-derived verdict: 39 of 42 changed files are `*.py`, `.claude/skills/**` or `marketplace/bundles/**`. `./pw verify` → `=== verify: SUCCESS ===`, 20,327 passed, 14 skipped |
| 6 Verification sub-agent | **DONE, and it changed the outcome** | Found a blocking regression and a false-negative class, both closed — § Independent pre-PR verification. Nothing it raised was rejected |
| 7 PR cycle | **DONE** | PR #1266. No `skip-bot-review`: 39 files are code, skill or bundle. All three comment surfaces read; participation below |
| 8 Merge gate | **DONE** | `verify / conclusion` **success** on the head; every comment on all three surfaces dispositioned; report committed as the last pre-merge commit. The condition-4 disclosure fired at **2-of-3** and is quoted verbatim in § Reviewer participation |
| 8 Bridge | **DONE** | Nothing written under `doc/plans/` outside this plan's own directory except **declared deliverables**: the epic `README.md` and `findings-test-corpus-review.md` edits ARE findings #35/#36, not bookkeeping |
| 9 This check | **DONE** | this table |
| 9 What have we learned | **DONE** | below |

**GitHub access path:** the GitHub MCP server. No `gh` CLI in this session.
**Branch form:** harness-assigned, restarted from `origin/main`.
**Plugin cache sync:** not owed — a machine-local step a cloud run never performs, even though this run
edited `marketplace/bundles/`.

## What have we learned (Step 9)

### Run 01's proposal is still pending, and this run is evidence FOR it

Run 01 proposed one change: *the site of a deletion is itself a defect surface, and a "pure move" is
verified by diffing comments and prose as their own dimension, because an AST-faithful move is not a
text-faithful move.* **The operator has not ruled on it.** This run applied it voluntarily — the
`test_audit.py` split slices by line rather than by AST node, and the comment count was **measured**
(290 → 276) instead of asserted. It worked: zero rationale blocks lost, against 8 lost by run 01's
node-slicing. That is confirming evidence, not a new proposal.

### One new proposal, and this run produced the evidence the hard way

**A deletion has consumers, and they are not found by sweeping the changed value's restatements.**

Step 6 tells the verifier to sweep beyond the diff "across the owning bundle/skill" for statements a
change makes false, enumerating consumer kinds for a **changed value**. This run's blocking defect fit
none of that shape:

- The change was a **deletion** — `test_audit.py` ceased to exist. There was no changed value whose
  restatements one could enumerate.
- The consumer was a **hard-coded path constant in a different tree**: `.claude/skills/…/era_stamp_fill.py`.
  "The owning bundle/skill" points at `marketplace/bundles/**` or the test directory; `.claude/skills/`
  is neither, and is exactly the tree a sweep phrased that way skips.
- The consumer's own 15-test suite **passed**, because it re-declared the constant instead of importing
  it and its fixture created the path under `tmp_path`.

Step 6 *does* name the last of those three ("a test stub that hardcodes the retired value and still
passes"), and that instruction is what led the verifier to it. The gap is the first two: the sweep is
written for a changed **value**, not a removed **path**, and its scope phrase does not reach `.claude/`.

**Concrete proposed edit** to `.claude/skills/cloud-plan-lane/SKILL.md` § Step 6, as a bullet:

> - when the change **deletes or renames a file**, the instruction to grep the **whole repository for
>   the old path** — not only the owning bundle or skill, and explicitly including `.claude/`, which is
>   neither `test/` nor `marketplace/bundles/` and is skipped by a sweep scoped to "the owning
>   bundle/skill". A path is a consumer surface with no "changed value" to enumerate restatements of,
>   so the value-oriented sweep above cannot reach it. Machine-read frontmatter (`verdict_inputs:`) and
>   hard-coded path constants in scripts are the two kinds that fail silently: the first is never
>   executed by a test, and the second is routinely shadowed by a test that re-declares it.

Ship it together with run 01's pending proposal if both are accepted — they are the same class of
defect (a change's blast radius exceeding the diff's own text) and one `chore/` PR should carry both.

**Presented, not self-approved. No contract change has been made by this run.**

### Considered and NOT proposed

- **The per-commit push rule.** It caught a real lapse here (a completed unit held back to batch), via
  the stop hook rather than via the contract. The contract's wording is already unambiguous — "batch
  the commits is not delay the push" — so this is a compliance failure, not a contract gap. No change.
- **The `Reopens?` column.** It paid out again and differently: `sourcery-ai` refused this PR on a
  **weekly** 500k-diff-character quota, where on #1258 it refused the *same* reviewer on a **per-diff**
  150k ceiling. Same verdict, different reopen semantics, and the column carried the distinction with
  no amendment needed. Working as designed. No change.

## Residue

**The plan's own deliverable residue is unchanged and still lives in run 01's § Residue** — D2's 15
remaining namespace builders, D3's five directories without a fixture module, D4's over-budget modules,
and D5's unstarted parametrization. This run closed findings, not deliverables.

One figure moved: `test-module-line-budget` over the slice is **58**, down from 59, because
`test_audit.py` was the module #38 split. Every other residue figure in run 01 stands.

Two items recorded here for a future plan, neither actionable within this run's scope:

- **`no-lesson-id-in-skill-prose` has rule 7's old gap.** The same citation-versus-datum confusion
  applies over `marketplace/bundles/**`. Fixing it needs a measured false-positive rate over bundle
  prose, which this run did not gather.
- **Rule 7's matchers miss two live spellings** — `Deliverable 2` (it requires `deliverable D<n>`) and
  a bare `#849` (it requires `PR #<n>`). Both appeared in this repository's own test prose. Widening
  the matchers is a change that needs its own false-positive measurement first.
