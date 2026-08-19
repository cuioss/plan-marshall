# Verification — 450-cloud-lane-assumes-local-runtime-affordances

**Verified against:** commit `c806e3e1afb0ae573c59287e6edee3f60cbc1c27`   **Landed as:** PR #1147, commit `a3eb36bb8f6b67f80b0670cfe26b25cfaab26eec` (squash; follow-up PR #1148 = `ceeb8427`)   **Verdict:** implemented-with-gaps

## Method

Read in full: `plan.md`, `report-01.md`. Located the landing with `git log --oneline --all --grep '#1147'`
(→ `a3eb36bb`, plus `ceeb8427` for PR #1148) and read the complete landed diff for
`.claude/skills/cloud-plan-lane/SKILL.md` and the four sibling reports (`git show a3eb36bb -- <path>`).
Reconstructed the pre-plan file (`git show a3eb36bb^:.claude/skills/cloud-plan-lane/SKILL.md`) to separate
what this plan changed from what was already there. Listed the 28 later commits touching the same file
(`git log --oneline a3eb36bb..HEAD -- <path>`) to classify each divergence as *this plan's gap* vs
*superseded by a later plan*.

Opened the current `SKILL.md` (1597 lines) at every site the plan's § Expected surface names: § Scope and
precedence (carve-out row), § Cloud session affordances (new section + `gh`↔MCP mapping), § GitHub access,
Step 4 § "Gate before committing", Step 5 (table + rationale + "Read the output" paragraph), Step 7
(skip-bot-review paragraph), Step 8 (condition 1, the `BLOCKED` blocker paragraph, the arm-and-hand-off
paragraph), Step 9 (contract-check rows 4 and 8), § Rules that outrank convenience, § Report template
(Build gate + Contract check lines).

Completeness sweeps run at the moment of the claim: `grep -rn 'marketplace/bundles/\*\*'` and
`grep -rn 'third row\|second row'` over the skill (the collapsed-table consumers); `grep -n -i 'sync\|owe'`
over the skill; `grep -rn -i 'sync is owed\|owes a local\|sync owed'` over all `*.md` in the repo;
`grep -rn '400-cloud-lane-build-gate'` (retired-plan references); `grep -rn 'went red\|missing \`mode:\`'`
(the removed rationale); `grep -n 'license/cla\|coderabbit\|sourcery\|cuioss-review-bot'` over the skill
(the "name no individual check" prohibition).

External facts executed rather than read:

- `.github/workflows/python-verify.yml` opened directly — confirmed `skip-on-docs-only: true` and the
  literal comment *"A merge_group run and any change touching buildable source still verify."*
- **The load-bearing "merge queue is the net" claim was executed, not trusted.** Listed the 30 most
  recent `merge_group` runs of `python-verify.yml`, selected a queue run whose head commit is a
  **genuinely docs-only** change, and opened its jobs: run **`32049413943`** (queue ref
  `gh-readonly-queue/main/pr-1281-d1c3153…`, head `b814d2fd` — PR #1281, **one file changed,
  `.claude/skills/cloud-plan-lane/SKILL.md`, no `*.py`**). Its `verify / gate` job **skipped** the
  "Footprint filter" step, and `verify / verify` then ran the full verification (`Run verification`
  17:14:34 → 17:26:47, ~12 min, `success`). **The docs-only net is real.**
  ⚠ **Correction made under adversarial review.** This bullet previously cited run `32134873877` and
  described it as "merge queue for PR #1293, a `SKILL.md`-only change". That description is false:
  `get_files` on PR #1293 returns **18 files, 9 of them `.py`** (`manage-metrics.py`,
  `_ledger_reconciliation.py`, six test modules, …). A merge-queue run on a change that touches buildable
  source verifies for the ordinary reason and says nothing about `skip-on-docs-only`, so the original
  citation did not support the claim it was offered for. The claim is now carried by run `32049413943`
  above, which does.
- PR #1147 read live over the GitHub MCP server: `get` (merged, `merged_at 2026-08-10T20:39:53Z`, head
  `b1f10a64`, 10 commits, 3 comments), `get_check_runs` (6 runs), `get_comments` (3), `get_review_comments`
  (0 threads), `get_reviews` (**1 — sourcery-ai**), `get_commits` (10).
- `doc/plans/cloud-bridge.md` opened to confirm D2's hand-off target actually performs the confirmation it
  is handed (it does: collect corroborates `state: MERGED` + a real `mergedAt` + ancestry of `origin/main`).
  This rationale is asserted only because it was checked.

**Mutation check: not applicable.** The landed diff contains **no** `*.py` file (`git show --stat a3eb36bb`
→ 8 files, all `.md`), adds no code, no test, and no guard that a test could exercise. There was nothing to
break and re-run. No file in the shared tree was mutated by this verification; `git diff --quiet --
.claude/skills/cloud-plan-lane/SKILL.md` returned clean before and no write was made outside the two files
this verification produces.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: publish the cloud affordance set, calibrated to this run | Affordance set published, per-fact source, each marked *confirmed here* / *reported-only* | Yes | **No** | **No** | Partial | `report-01.md:31-38` — 6-row table (rows at `:33-38`) with per-fact source. But rows for Self-wake (`:34`) and Auto-merge arming (`:36`) say "not probed (no PR opened…)" / "not probed (no arming this run)" while the same report opens PR #1147 (`:3`, `:179`) and arms auto-merge (`:162`). See G1 |
| D1 | "Cloud session affordances" section + `gh`↔MCP mapping | A reader handed any `gh`-form line names the exact MCP call; the affordance facts appear in **exactly one place** | Yes | Yes | Partly | **No** | `SKILL.md:46-75` — **7**-row affordance table (`:54-60`, re-counted) + 7-row mapping (`:69-75`); `SKILL.md:995` cross-references it from § GitHub access. Mapping cold read passes on **today's** text, and the coverage sweep confirms it: every `gh` form the skill still spells (`:1010`, `:1029`, `:1214`, `:1215`, `:1290`, `:1315`, `:1442`) is answered by a mapping row. ⚠ Two of the six rows **as this plan landed them** named no `method:` at all ("`pull_request_read` for the conversation / issue-comment surface"), so the done-when was met only after PR #1184 and PR #1281 supplied the exact methods — credit for the passing cold read is partly a later plan's. The "exactly one place" clause is not met (G4); three rows overstate certainty against D0 (G3) |
| D2 | Step 8: arm-and-hand-off is a completed run | A cold reader classifies "armed, green, `MERGED` not observable" as **completed**; row 8 no longer demands in-session `MERGED` | Yes | Yes | Yes | Yes | `SKILL.md:1331-1341` ("Record the outcome as **completed with the landing delegated** — not `partial`, and not a failure"); Step 9 row 8 at `SKILL.md:1407` now reads "both are completed, neither is partial". Self-confirm rule preserved: "(A run that *can* self-confirm still does — this is not licence to assert a merge that was never read back.)" Hand-off target verified in `doc/plans/cloud-bridge.md:143-146` (collect corroborates `state: MERGED`, a real `mergedAt`, **and** ancestry of `origin/main`) |
| D3 | Step 8 condition 1: reachable-surface increment | (i) reader reads `mergeStateStatus`, attempts no ruleset-config API call; (ii) blocker = unsatisfied **required** context, never the salient non-required one | Yes | Yes | Yes | Yes | (a) `SKILL.md:1206-1208`: "**The ruleset-config API itself is not reachable on the cloud MCP path** … so 'read it from the ruleset' means read `mergeStateStatus` — never a ruleset-config API call, which returns `403` here." (b) `SKILL.md:1245-1252`: "derive **which** context blocks from (required contexts ∩ non-green contexts) — never from whichever pending status is loudest … never promote a non-required pending status to 'the blocker'". Plan `030`'s landed text survives, but **not verbatim** — the diff (`git show a3eb36bb`) rewords one clause of its sentence — *"read it from the ruleset"* became *"read it from GitHub's own computation over the ruleset (`mergeStateStatus`, below)"*. Within the plan's "cloud increment" licence, but it is an edit, not only an insertion |
| D4 | Interactive-vs-headless escalation duality | Reader picks escalate-via-`AskUserQuestion` for the interactive case, autonomous-fallback for the headless one; escalation is `MAY` | Yes | Yes | Yes | Yes | `SKILL.md:1572-1580` in § Rules that outrank convenience: "the run **MAY** escalate a decision via `AskUserQuestion` … A **headless** run, or a **dispatched leaf** … never waits: it takes the plan's stated autonomous fallback". `MAY`, not `MUST`, preserved. Later-added ("recording both the question and its answer", PR #1148; the round-budget exception at `:1582`+ and its headless carve-out at `:950-960`, PR #1292) build on it without inverting it |
| D5a | Build gate `*.py`-only at BOTH sites + `errors[]` | Step 5 table has two rows; no rationale claims a markdown-only change fails the local build; both gate sites read `status` **and** `errors[]` | Yes | Yes | Yes | Yes | Step 5 table `SKILL.md:427-430` — exactly two rows (`Any *.py` → `./pw verify`; `No *.py` → "Nothing locally — record 'no buildable footprint, build skipped'"). Rationale `SKILL.md:432-439` replaced by the `merge_group`-is-the-net explanation; `grep 'went red\|missing \`mode:\`'` → **no match**. Step 4 gate `SKILL.md:296` narrowed to `*.py`; `errors[]` read at Step 4 (`:314-318`) and Step 5 (`:498-505`), and at Step 9 row 4 (`:1402`) — three sites, all naming `status`/`total_issues`/`errors[]`. Downstream consumers clean: `grep 'third row\|second row'` → **0 hits**; the two surviving `marketplace/bundles/**` mentions (`:1016`, `:1022`) are Step 7's *review* predicate, deliberately wider. The report template's § Build gate needed no edit — it was already `*.py`-keyed before the plan (`git show a3eb36bb^:… ` line 758-760) |
| D5b | `/sync-plugin-cache` is machine-local, not owed | Carve-out row and report template no longer frame a cloud run as owing a sync; a cold reader reports **no sync debt** | Yes | Yes | Yes | Yes | `SKILL.md:38` — "**Not applicable — and not owed.** … A cloud run **neither performs nor owes** a sync … not a debt this run tracks or records". Report template `SKILL.md:1548-1552` — "A cloud run **never owes** a `/sync-plugin-cache`". `grep -n -i 'sync\|owe'` over the whole skill → the only remaining hits are these plus the affordances index row (`:60`); no "sync owed" framing survives |

### D0 — the affordance table's "this run" column is false in three cells

`report-01.md:34` records Self-wake as "**Reported-only** — not probed (**no PR opened**, so no self-wake
was needed)" and `:36` records Auto-merge arming as "**Reported-only** — not probed (**no arming this
run**)". `report-01.md:185` states "GitHub MCP server available; **not exercised for GitHub operations this
run (no PR)**." All three are contradicted by the same document: `:3`, `:120`, `:162`, `:179` and `:214`
report PR #1147 opened, three conversation comments read over MCP, and auto-merge armed with squash. The PR
commit list explains the mechanism — the D0 table landed in commit `84ad5b0` (whose message reads "Outcome
partial — … PR/merge held for the operator"), and the later commits `dae86fd` / `b1f10a6` updated the
header and contract-check rows 7–8 but never revisited D0 or the GitHub-access-path line. D0's product is
precisely this observation table, and the plan made the run its own fixture ("it should report which it
actually observed"), so the stale cells defeat the deliverable's purpose. Gap **G1**.

### D1 — certainty overstated on three rows, and the "exactly one place" clause is unmet

Two separate problems at `SKILL.md:54-60` (the seven affordance rows).

First, the plan's D0 gate carries an explicit ⛔: *state "is gated" only where this run confirmed it, and
"may be gated (reported)" otherwise*. The run applied it to exactly one row — Self-wake is correctly hedged
("may be **approval-gated**"). Three rows the run's own D0 marked *reported-only / not probed* are stated as
flat fact: **GitHub access** — "There is **no `gh` CLI**, and Bash cannot reach `api.github.com`
(egress-blocked — direct calls return `403`)"; **Ruleset-config API** — "**Not reachable**"; **Auto-merge
arming** — "arming auto-merge … **queues the PR at once**". Gap **G3**.

Second, D1's done-when required the affordance facts to appear "in exactly one place (no restatement that
can drift)". They do not: the self-wake fact is restated at `SKILL.md:1331-1334`, the `403`/ruleset fact at
`:1206-1208`, the `*.py` build fact at `:427-439`, the sync fact at `:38` — and the three comment-surface
mapping rows (`:73-75`) are duplicated in full by Step 7's three-surface table at `:1053-1057`. The run
recorded this itself (report finding #5, "Accepted, no change") and its § What have we learned names the
same multiply-stated predicate as "a mild drift risk". The drift is no longer hypothetical: the affordances
row still instructs "Read required-ness from `mergeStateStatus`", while the note added later at
`SKILL.md:1218-1224` establishes that the MCP payload has **no `mergeStateStatus` key** and the field is
`mergeable_state` — though the mapping row at `:72`, inside the same section, already names both spellings,
so the miss is recoverable by a reader of the whole section. Gap **G4**.

## Report accuracy

Re-derived every figure at the moment of stating it.

**Contradicted by the tree / the live PR:**

1. **D0 rows and the GitHub-access-path line** — `report-01.md:34`, `:36`, `:185` claim no PR, no arming,
   and no MCP GitHub operations; `:3`, `:120`, `:162`, `:179`, `:214` state the opposite. (G1)
2. **`sourcery-ai` verdict** — `report-01.md:127` records `silent`, evidenced as "The 'Sourcery review'
   check-run concluded `skipped`; **no comment body**." Live read of PR #1147 `get_reviews` returns **one
   review**: `sourcery-ai[bot]`, state `COMMENTED`, submitted `2026-08-10T20:13:35Z` on commit
   `fbf14384`, body *"Sorry @cuioss-oliver, you have reached your weekly rate limit of 500000 diff
   characters."* The correct verdict is `rate-limited`, not `silent`, and the merge-gate condition-2 claim
   at `:157` ("3 conversation comments … 0 inline review threads. **Satisfied**") rests on two of the three
   comment surfaces. (G2)
3. **"Run commits on the branch: `8b0c455`, `92620f4`, `9f192df`"** (`report-01.md:23-24`) — PR #1147
   carries **10** commits, seven of them from this session: `8b0c455`, `92620f4`, `9f192df`, `84ad5b0`
   (report), `fbf1438` (sibling annotations), `dae86fd`, `b1f10a6`; the other three (`780c737`,
   `7172419`, `af2eaed`) are the plan-authoring commits on the same branch. (G5)

**Checked and confirmed accurate:**

- "3 conversation comments" — `get_comments` returns exactly 3 (cla-assistant, coderabbitai, cuioss-review-bot).
- "0 inline review threads" — `get_review_comments` returns `totalCount: 0`.
- "`verify / conclusion` = success, `verify / gate` = success, `dependency-review` = success,
  `verify / verify` = **skipped**" — all four confirmed by `get_check_runs` on head `b1f10a64`.
- `cuioss-review-bot` posted the quoted "PR Reviewer Guide 🔍 — No relevant tests / No security concerns
  identified / No major issues detected" — body matches verbatim.
- "Coverage: 1 of 3" and "the required bot reviewed with no issues" — the count holds, though for a
  different reason than stated (sourcery was rate-limited, not silent); 1-of-3 is unchanged.
- "Each carries the `Co-Authored-By: Claude` trailer and no 'Generated with' footer" — all 10 commit
  messages confirm this.
- "Branch `claude/cloud-plan-lane-gaps-5kph2x` (harness-assigned, kept as-is)" — matches PR head ref.
- "**No `*.py`**" in the branch diff — `git show --stat a3eb36bb` lists 8 files, none `.py`.
- "Both defects were … re-verified directly by grep (no stale predicate remains; the dangling reference is
  gone)" — re-derived: `grep 'third row\|second row'` → 0 hits; Step 9 row 4 reads `*.py` + `errors[]`.
- Findings #1 and #2 fixes present at `SKILL.md:1402` and `:1021-1025`.
- The four sibling-report annotations landed and each names the deliverable it claims (D2 / D3 / D3(a)+D1 /
  D4+D5a), with `030` #1 correctly left open.
- Plan 400 deleted; `grep -rn '400-cloud-lane-build-gate'` → the only surviving reference is inside this
  plan's own `plan.md:261`, where it is deliberate.
- D0's build/plugin-cache rows marked "Confirmed here" — both genuinely were (no `*.py` in the diff;
  `python-verify.yml` read).

## Out-of-scope compliance

The plan states an unusually hard boundary: *"⛔ **Every edit lands in
`.claude/skills/cloud-plan-lane/SKILL.md` and nowhere else**"*, and separately *"⛔ `doc/plans/**` —
individual lane plans. This plan changes the lane's contract, never a plan executed under it."* The landed
diff touches 8 files: the skill, this plan's own `plan.md` + `report-01.md`, **four sibling run reports**,
and the **deletion of staged plan 400**.

Both excursions are **declared, not silent**. The four annotations are recorded in `report-01.md`'s Step 9
Bridge row as an explicit operator-directed exception ("document in the reports that they are mitigated"),
and the plan itself recommends retiring plan 400 ("**Recommend retiring plan 400**"), which commit
`8b0c455` executes with that reason in its message. The operator direction is a conversation event and is
**not verifiable from the tree** — I record the claim, not its truth. No undeclared collateral change was
found: no `CLAUDE.md` edit, nothing under `marketplace/bundles/**`, no `.plan/` write, no other file.

The plan's "no `/sync-plugin-cache` is owed" self-prediction held — the diff touches no
`marketplace/bundles/**` path.

## Residue carried forward

| Residue in `report-01.md` | Status in today's tree |
|---|---|
| **PR + merge (Steps 7–8) completed; landing delegated** | **Closed.** PR #1147 `merged: true`, `merged_at 2026-08-10T20:39:53Z`; `a3eb36bb` is on `main` |
| **Sibling-report annotations (operator-directed)**; `030` #1 (`license/cla` pending on cloud-run authorship) left open | Annotations present in all four reports. `030` #1 **still open** — no lane-contract lever landed, and the skill still names no individual check |
| **`CLAUDE.md` sync-mirror divergence** — flagged for a separate operator touch | **Closed by a later plan.** `git log -S 'neither performs a sync nor records one as owed' -- CLAUDE.md` → `cd11d46b` ("align the lane's plugin-cache carve-out with the operator ruling", PR #1267). `CLAUDE.md:91` now matches the skill |
| **Plugin-cache sync: none owed** | Holds; reinforced by the `CLAUDE.md` alignment above |
| Process observation: the build-gate predicate is stated in ≥4 places | **Still open** as a drift risk — and now realized once, see G4 |

## What could NOT be verified

- **Operator direction for the sibling-report annotations and for the two mid-run rulings** (`*.py`-only
  build gate; sync is machine-local). These are conversation events with no committed artifact. The plan
  text itself carries both rulings, which is consistent with them having been given, but the tree cannot
  confirm the annotation instruction.
- **The exact bodies the run read at review time.** The coderabbit comment quotes "Next review available in
  57 minutes" in the report while the stored body now reads "48 minutes"; that comment's `updated_at`
  (`20:25:36Z`) is later than its `created_at` (`20:13:51Z`), so the bot edited it. Not assertable as an
  error. (The sourcery finding in G2 is different in kind — a whole surface was never read, and the
  review still exists unedited.)
- **The three pre-squash branch SHAs** (`8b0c455`, `92620f4`, `9f192df`) exist only on the deleted PR
  branch; they were corroborated through the PR's commit list, not through this clone's object store.
- **`skip-on-docs-only`'s internal path classification.** The reusable workflow lives in
  `cuioss/cuioss-organization` and is not in this clone; whether `.claude/skills/**` is formally in its
  "non-building" set could not be read from source. Its *effect* was confirmed twice empirically (PR #1147's
  `verify / verify` skipped on the PR trigger; PR #1293's `merge_group` run built in full), which is what
  D5a's rationale actually depends on.
- **Whether `gh` was truly absent, or the self-wake tools truly gated, in the run's session.** The run
  itself recorded these as reported-only; nothing in the tree can settle them retroactively. This is the
  substance of G3, which asks the skill's wording to match that uncertainty rather than asking anyone to
  re-establish the facts.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document. Working assumption: every claim
here is wrong until the tree, the live PR, or an executed command says otherwise. Nothing was confirmed
by re-reading `verification.md` or `gaps.md`.

**Checked.** *(a) Every gap.* All five re-derived from primary sources — G1 by opening `report-01.md` at
each cited line and at the lines said to contradict them; G2 by calling `pull_request_read` `get_reviews`
on PR #1147 live (one review, `sourcery-ai[bot]`, `COMMENTED`, `2026-08-10T20:13:35Z`, commit `fbf14384`,
body quoted verbatim) **and** `get_check_runs` (the `Sourcery review` check-run, id `93587334538`,
`skipped`, on the *final* head `b1f10a64`); G3 and G4 by opening `SKILL.md` and re-deriving every cited
line number with `grep -n`; G5 by calling `get_commits` (10 commits) and reading all ten messages.
*(b) Every clean-pass row.* D2, D3, D4, D5a and D5b were each re-opened at their evidence sites and their
behavioural done-when re-read against the current text, not against this document's summary of it.
*(c) Every "swept, clean" claim, re-run with a broader pattern than the original*: `marketplace/bundles`
without the `**` suffix (3 hits: `:38`, `:1016`, `:1022` — the first is the carve-out row's own heading);
`-i 'sync'` over the whole skill (3 hits: `:38`, `:60`, `:1551`) plus a repo-wide `-i 'sync is
owed|owes a local|sync owed|unsynced|owe a sync|owes a sync'` over every `*.md` (15 hits, none in the
skill, none in `CLAUDE.md`); `-iE 'plan .?400|400-cloud'` instead of the exact slug (all remaining hits
are inside this plan's own `plan.md`/`report-01.md`); the named-check prohibition widened from four bot
names to `dependency-review|verify / |cla-assistant|codecov|sonar` (6 hits, none inside § Cloud session
affordances); and a **new** sweep this document never ran — every `gh` form in the skill (backticked forms plus
fenced `gh ` command lines) checked against the mapping table, all seven covered.
*(d) Every re-derivable figure*: 1597 lines; 28 later commits; 8 files in `a3eb36bb`, all `.md`;
`ceeb8427` = PR #1148; PR #1147 `merged: true`, `merged_at 2026-08-10T20:39:53Z`, head `b1f10a64`,
10 commits, 3 comments, 8 changed files, head ref `claude/cloud-plan-lane-gaps-5kph2x`; 6 check runs with
the four named conclusions; `CLAUDE.md:91` aligned by `cd11d46b` (PR #1267); the four sibling annotations
read from the landed diff. **The affordance table is 7 rows, not 8** — this document's only miscount.
*(e) The one claim asserted as executed* — the merge-queue net — re-executed from scratch (below).

**Not re-checked**, and a third reviewer should treat these as still resting on this document's word:
the operator's two mid-run rulings and the annotation instruction (conversation events, no artifact); the
three pre-squash branch SHAs (the PR branch is deleted; they were read from `get_commits`, not from this
clone's object store); the reusable workflow's internal path classification (it lives in
`cuioss/cuioss-organization`); and whether `gh` was truly absent or the self-wake tools truly gated in the
run's own session. No mutation was applied to any source file — the landed diff contains no code, and
`git diff --quiet -- .claude/skills/cloud-plan-lane/SKILL.md` was clean before and after this review.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `report-01.md` D0 rows `:34`/`:36` and the access line `:185` assert an absence the same file contradicts — `high` | **upheld**, refined | Lines re-read: `:34`, `:36`, `:185` vs `:3`, `:120`, `:162`, `:179`, `:214`. `high` sustained: this is a shipped false signal in the evidence corpus later plans mine. Refined per cell — `:36` and `:185` are false outright, `:34`'s verdict ("not probed") is **accurate** and only its reason ("no PR opened") is stale |
| G2 | `sourcery-ai` was `rate-limited`, not `silent` — `medium` | **upheld**, evidence strengthened | Live `get_reviews` returns the quoted rate-limit body; live `get_check_runs` returns the `skipped` check-run. Both are true of **different heads** (`fbf14384` vs `b1f10a64`); only the inference *check-run skipped ⇒ nothing filed* is false. `medium` correct — it misstates a disclosure's cause, it does not change 1-of-3 |
| G3 | Three affordance rows overstate certainty against D0's ⛔ — `medium` | **upheld**, references corrected | Cited lines were `:53`/`:55`/`:56`; actual `:54`/`:56`/`:57` (`grep -n`). All three are this plan's landed text, unchanged since `a3eb36bb`. Scope corrected: D0 marks the GitHub-access row "Confirmed (partial)", not "reported-only" — only its *no-`gh`* clause is reported-only, and that is the clause the skill states flatly |
| G4 | The affordance facts are not single-sourced, and the index has drifted — `medium` | **upheld**, widened and bounded | References corrected (`:55`→`:56`, `:1216-1222`→`:1218-1224`, `:54`→`:55`, `:1327-1331`→`:1331-1334`, `:57`→`:59`). A **fifth** restatement found that this document missed: mapping rows `:73-75` are duplicated in full by Step 7's three-surface table at `:1053-1057`. Severity held at `medium` — the D1 done-when is genuinely unmet — but the drift's harm is bounded: the mapping row at `:72`, in the same section, already names both spellings, so "worse than no table" was an overstatement and is removed |
| G5 | The commit list names 3 of the run's commits — `low` | **upheld**, arithmetic corrected | `get_commits` → 10. The gap said "under-reports by four", true against the 7 execution-session commits but not against the 10 "on the branch" it claims to describe; both figures now stated, with the three plan-authoring commits named |
| Verdict `implemented-with-gaps` | — | **upheld** | All six deliverables are present in the landed diff and each done-when is at least partly met; none is unimplemented, so `partially-implemented` would be wrong. Two carry quality gaps (D0, D1) |
| Method: "merge queue is the net", executed via run `32134873877` (PR #1293, "a `SKILL.md`-only change") | asserted as executed | **REFUTED as evidence; conclusion re-established** | `get_files` on PR #1293 → **18 files, 9 `.py`** (`manage-metrics.py`, `_ledger_reconciliation.py`, six test modules). It is not docs-only, so its merge-queue run verifying proves nothing about `skip-on-docs-only`. Re-executed properly: run **`32049413943`**, queue ref `gh-readonly-queue/main/pr-1281-…`, head `b814d2fd` — **one file, `SKILL.md`, no `*.py`** — `verify / gate` **skipped** the Footprint filter and `verify / verify` ran 17:14:34→17:26:47. The conclusion stands on evidence that supports it |
| Method: D3 "plan `030`'s landed text is preserved verbatim around the insertions" | — | **re-stated** | `git show a3eb36bb` shows one clause of `030`'s sentence reworded, not merely surrounded. Within the plan's licence, but "verbatim" was wrong |
| D1 evidence: "8-row affordance table"; "`SKILL.md:994`" | — | **re-derived** | 7 rows (`:54-60`); the cross-reference is at `:995` |
| D1 done-when attribution | "Mapping cold read passes" | **qualified** | It passes on *today's* text. As this plan landed the mapping, two of six rows named no `method:` — the exact methods came from PR #1184 and PR #1281. Not an open gap (already fixed), but the credit is not wholly this plan's |
| Line references throughout | — | **corrected** | `:1205-1207`→`:1206-1208`; `:1244-1251`→`:1245-1252`; `:1327-1338`→`:1331-1341`; `:1570-1580`→`:1572-1580`; `:317-321`→`:314-318`; `:497-505`→`:498-505`; `report-01.md:20-21`→`:23-24`; `:30-38`→`:31-38` |

**Documents corrected.** In `verification.md`: the merge-queue evidence replaced with a run that actually
supports it, and the false citation recorded rather than deleted; the affordance-row count re-derived
(8→7); nine line references corrected; the D3 "verbatim" claim re-stated; the D1 cold-read credit
qualified; the fifth restatement site added to the D1 narrative; the D5a evidence extended with the third
gate site and the report-template finding; the verdict re-checked and upheld. In `gaps.md`: G1's per-cell
distinction added; G2's two-heads reconciliation added; G3's three line references and its scope
corrected; G4's five references corrected, its fifth restatement site added, its overstatement removed and
its Fix/Done-when extended; G5's arithmetic corrected; a `## Refuted during adversarial review` section
added recording that **nothing was refuted** plus two candidate gaps considered and deliberately not filed
(D0's never-performed probes — no actionable fix distinct from G3's; and the run applying the `*.py`-only
gate before it landed — a real, disclosed, operator-authorized deviation from `plan.md`'s ⚠⚠ block with no
change an implementer could now make). Open items re-derived: **5**.

**Residual doubt.** A third reviewer should start with the two things no artifact can settle and this
document leans on: (1) **the operator direction** for the four sibling-report annotations and for the two
mid-run rulings — the Bridge-rule excursion's whole justification is a conversation event, so if the
direction was misremembered, the excursion is an undeclared cross-plan write, and the `*.py`-only gate and
the no-sync rule both rest on the same unrecorded authority; and (2) **G3's premise in the other
direction** — this review confirmed the *wording* is unhedged but could not confirm the *facts* are
wrong, so a reviewer with a live cloud session should simply probe `gh --version`, `send_later`, and the
ruleset-config API and settle the three rows on evidence instead of hedging them. Third: this review
found one asserted-as-executed claim that had not been executed as described; that class of defect is not
detectable by reading, so any remaining "confirmed by running" claim here deserves the same treatment.
