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
- **The load-bearing "merge queue is the net" claim was executed, not trusted.** Listed `merge_group`
  runs of `python-verify.yml` and opened the jobs of run `32134873877` (merge queue for PR #1293, a
  `SKILL.md`-only change): its `verify / gate` job **skipped** the Footprint filter and `verify / verify`
  ran the full 15-minute verification. The docs-only net is real.
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
| D0 | GATE: publish the cloud affordance set, calibrated to this run | Affordance set published, per-fact source, each marked *confirmed here* / *reported-only* | Yes | **No** | **No** | Partial | `report-01.md:30-38` — 6-row table with per-fact source. But rows for Self-wake (`:34`) and Auto-merge arming (`:36`) say "not probed (no PR opened…)" / "not probed (no arming this run)" while the same report opens PR #1147 (`:3`, `:179`) and arms auto-merge (`:162`). See G1 |
| D1 | "Cloud session affordances" section + `gh`↔MCP mapping | A reader handed any `gh`-form line names the exact MCP call; the affordance facts appear in **exactly one place** | Yes | Yes | Partly | **No** | `SKILL.md:46-75` — 8-row affordance table + 7-row mapping; `SKILL.md:994` cross-references it from § GitHub access. Mapping cold read passes. The "exactly one place" clause is not met (G4); three rows overstate certainty against D0 (G3) |
| D2 | Step 8: arm-and-hand-off is a completed run | A cold reader classifies "armed, green, `MERGED` not observable" as **completed**; row 8 no longer demands in-session `MERGED` | Yes | Yes | Yes | Yes | `SKILL.md:1327-1338` ("Record the outcome as **completed with the landing delegated** — not `partial`, and not a failure"); Step 9 row 8 at `SKILL.md:1407` now reads "both are completed, neither is partial". Self-confirm rule preserved: "(A run that *can* self-confirm still does — this is not licence to assert a merge that was never read back.)" Hand-off target verified in `doc/plans/cloud-bridge.md:143-144` |
| D3 | Step 8 condition 1: reachable-surface increment | (i) reader reads `mergeStateStatus`, attempts no ruleset-config API call; (ii) blocker = unsatisfied **required** context, never the salient non-required one | Yes | Yes | Yes | Yes | (a) `SKILL.md:1205-1207`: "**The ruleset-config API itself is not reachable on the cloud MCP path** … so 'read it from the ruleset' means read `mergeStateStatus` — never a ruleset-config API call, which returns `403` here." (b) `SKILL.md:1244-1251`: "derive **which** context blocks from (required contexts ∩ non-green contexts) — never from whichever pending status is loudest … never promote a non-required pending status to 'the blocker'". Plan `030`'s landed text is preserved verbatim around the insertions (diff-verified) |
| D4 | Interactive-vs-headless escalation duality | Reader picks escalate-via-`AskUserQuestion` for the interactive case, autonomous-fallback for the headless one; escalation is `MAY` | Yes | Yes | Yes | Yes | `SKILL.md:1570-1580` in § Rules that outrank convenience: "the run **MAY** escalate a decision via `AskUserQuestion` … A **headless** run, or a **dispatched leaf** … never waits: it takes the plan's stated autonomous fallback". `MAY`, not `MUST`, preserved. Later-added ("recording both the question and its answer", PR #1148; the round-budget exception, PR #1292) build on it without inverting it |
| D5a | Build gate `*.py`-only at BOTH sites + `errors[]` | Step 5 table has two rows; no rationale claims a markdown-only change fails the local build; both gate sites read `status` **and** `errors[]` | Yes | Yes | Yes | Yes | Step 5 table `SKILL.md:427-430` — exactly two rows (`Any *.py` → `./pw verify`; `No *.py` → "Nothing locally — record 'no buildable footprint, build skipped'"). Rationale `SKILL.md:432-439` replaced by the `merge_group`-is-the-net explanation; `grep 'went red\|missing \`mode:\`'` → **no match**. Step 4 gate `SKILL.md:296` narrowed to `*.py`; `errors[]` read at Step 4 (`:317-321`) and Step 5 (`:497-505`). Downstream consumers clean: `grep 'third row\|second row'` → **0 hits**; the two surviving `marketplace/bundles/**` mentions (`:1016`, `:1022`) are Step 7's *review* predicate, deliberately wider |
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

Two separate problems at `SKILL.md:52-61`.

First, the plan's D0 gate carries an explicit ⛔: *state "is gated" only where this run confirmed it, and
"may be gated (reported)" otherwise*. The run applied it to exactly one row — Self-wake is correctly hedged
("may be **approval-gated**"). Three rows the run's own D0 marked *reported-only / not probed* are stated as
flat fact: **GitHub access** — "There is **no `gh` CLI**, and Bash cannot reach `api.github.com`
(egress-blocked — direct calls return `403`)"; **Ruleset-config API** — "**Not reachable**"; **Auto-merge
arming** — "arming auto-merge … **queues the PR at once**". Gap **G3**.

Second, D1's done-when required the affordance facts to appear "in exactly one place (no restatement that
can drift)". They do not: the self-wake fact is restated at `SKILL.md:1327-1331`, the `403`/ruleset fact at
`:1205-1207`, the `*.py` build fact at `:427-439`, the sync fact at `:38`. The run recorded this itself
(report finding #5, "Accepted, no change") and its § What have we learned names the same multiply-stated
predicate as "a mild drift risk". The drift is no longer hypothetical: the affordances row still instructs
"Read required-ness from `mergeStateStatus`", while the note added later at `SKILL.md:1216-1222` establishes
that the MCP payload has **no `mergeStateStatus` key** and the field is `mergeable_state`. Gap **G4**.

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
3. **"Run commits on the branch: `8b0c455`, `92620f4`, `9f192df`"** (`report-01.md:20-21`) — PR #1147
   carries **10** commits, seven of them from this session: `8b0c455`, `92620f4`, `9f192df`, `84ad5b0`
   (report), `fbf1438` (sibling annotations), `dae86fd`, `b1f10a6`. (G5)

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
