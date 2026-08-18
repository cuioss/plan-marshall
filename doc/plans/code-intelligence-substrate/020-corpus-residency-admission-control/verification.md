# Verification — 020-corpus-residency-admission-control

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` at first audit; every claim below re-derived at `57c63a8` during adversarial
review (the 16 intervening commits are all `doc/plans/**` audit documents — no source changed)
**Overall verdict:** CONFIRMED WITH GAPS

The run's load-bearing outcome — the **D0 gate halted on outcome (b)**, no git-reachable population of
instrumented corpus-residency records exists — is independently re-derived and holds at `57c63a8`. The
gaps are entirely in the *supporting* claims of the run report: one materially wrong equation between
the metrics field the run identified and what D1 actually asks for, one misreading of the
automatic-review registry, and seven stale or inaccurate citations. No shipped code, no out-of-scope
work, no collateral.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: can the residency population be derived in this clone? | HALT (b) — no git-reachable population | Re-derived at `57c63a8`: zero tracked `metrics.toon`, no `.plan/plans/`, no `.plan/local/archived-plans/`, no `metrics*.toon` anywhere under `.plan/`, no tracked archived-plan record, no tracked transcript | **CONFIRMED** |
| D1 | Derive the corpus-residency population | Not attempted — gated by D0 | Nothing in the tree derives per-phase residency/consumption; no three-state record read exists | **CONFIRMED (correctly not attempted)** |
| D2 | Section-granular corpus read verb | Not attempted — gated by D0 | Nothing addresses a named section of a `SKILL.md` or `standards/*.md`. ⚠ But the analogous verb **does** exist over plan documents (`manage-solution-outline`/`manage-plan-documents` `read --section`), and a corpus language server has since shipped — see D2 detail, G11, G12 | **CONFIRMED (correctly not attempted)** |
| D3 | Re-read elimination within an envelope | Not attempted — gated by D0 | Not built; not dropped-on-evidence either (D1 never ran to supply the refutation) | **CONFIRMED (correctly not attempted)** |
| D4 | Restate the epic's value case | Not attempted — gated by D0 | `doc/concepts/token-management.adoc:35` § 4 still carries the unrevised skill-driven-guidance claim | **CONFIRMED (correctly not attempted)** |

## Per-deliverable detail

### D0 — GATE: can the residency population be derived in this clone at all?

- **Required (plan):** `plan.md:56-65` — *"the run has established, from git-reachable evidence alone,
  either (a) a population of instrumented records it can measure, or (b) that no such population is
  reachable here. ⛔ On (b): HALT. Report the plan blocked on corpus availability and stop."*
- **Claimed (report):** `report-01.md:38` — HALT (b), established from git-reachable evidence alone.
- **Found / checks run** (each re-run at `61a43e5` and again at `57c63a8`, not copied from the report):
  - `git ls-files "*metrics.toon"` → **empty**. Control: `git ls-files "*.toon"` returns **39** paths
    (39 at `61a43e5` too), so the pattern is not silently failing.
  - `git show HEAD:.gitignore` → `.plan/*` at line 45, un-ignored back only `!.plan/marshal.json`
    (46) and `!.plan/project-architecture/` (47). Report claim 1 exact.
  - `find .plan -maxdepth 2` → `marshal.json`, `project-architecture/{11 modules,_project.json}`,
    plus machine-local scratch this working tree has since grown (`execute-script.py`, `local/logs`,
    `local/marshall-state.toon`, `temp/`). The load-bearing negatives are the ones that matter and all
    hold: **no `.plan/plans/`, no `.plan/local/archived-plans/`, and `find .plan -name "metrics*.toon"`
    → empty.** Report claim 3 is exact on its substance; its literal "`.plan/` holds only two entries"
    form is a property of an untracked, machine-local directory and decays — do not re-assert it.
  - `grep -l "exploration_\|residency" .plan/project-architecture/*/enriched.json` → **no output**.
    The only tracked `.plan/` content carries no metrics field.
  - `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:2720,4923,4990,9374` — the
    archived-plan audit walks `.plan/local/archived-plans`, which is absent. Report claim 2 exact.
  - `git grep -l exploration_doc_residency_bytes` → 6 paths at `61a43e5`, of which one is
    `report-01.md` itself (10 at `57c63a8` — these audit documents inflate it, so the durable form of
    the claim is the five non-audit files, not the count);
    the other **five** are `manage-metrics/standards/data-format.md`,
    `platform-runtime/scripts/runtime_base.py`, `platform-runtime/standards/contract.md`,
    `test/plan-marshall/manage-metrics/test_manage_metrics.py`,
    `test/plan-marshall/platform-runtime/test_metrics_tokens.py`. Exactly the "five tracked files, all
    non-data (two tests, two schema/contract docs, one producer)" the sub-agent reported. Report
    claim 5 exact.
  - `git ls-files "*.jsonl"` → **empty**; no committed transcript corpus.
  - Adversarial extension of my own: `git ls-files "*.toon" | grep -v "^test/"` → three template/document
    fixtures under `marketplace/bundles/**` only; `git ls-files | grep -i archived-plan` outside
    `test/` and the audit skill → **empty**; sibling plan `080-…` (`report-01.md:3`) records
    **`Outcome: blocked (D0 gate → outcome (b))`** on 2026-08-12, two days *after* this run, so no
    sibling has since landed a population.
- **Verdict:** **CONFIRMED.** Outcome (b) is the correct answer, was correct when reported, and is
  still correct at `57c63a8`. The run halted, reported blocked, and did not substitute a stand-in —
  exactly what `plan.md:62-65` demands. Per `plan.md:139-141` this is a **success at D0**.
- **Prohibition respected:** `plan.md:129` forbids going looking for the machine-local measurement.
  The run established structural absence via `git ls-files` and a top-level `ls .plan` — the same two
  observations I re-ran — which establishes (b) without mining anything. **No violation.**

### D1 — derive the corpus-residency population

- **Required (plan):** `plan.md:66-75` — per-phase residency **and consumption** figures, each with
  its own population size, plus a three-state (`current` / `old-schema` / `pre-migration`) archived
  record read.
- **Claimed (report):** `report-01.md:39` — not attempted, gated by D0.
- **Found:** No per-phase residency figure is derived anywhere in the tree; no three-state record read
  exists (`git grep` for `old-schema` / `pre-migration` in `manage-metrics` returns nothing).
- **Verdict:** **CONFIRMED (correctly not attempted).** The gate fired; `plan.md:63` forbids
  proceeding.
- ⚠ **But the report mis-identifies the instrument D1 would use.** See § Report accuracy, item 1, and
  `gaps.md` G1/G2 — this is the audit's most consequential finding, because it means the re-run's
  premise is wrong even once the corpus becomes reachable.

### D2 — a section-granular read verb for the corpus

- **Required (plan):** `plan.md:76-80` — a leaf retrieves one named section of a `SKILL.md` or
  `standards/*.md` without loading the file, carrying the existing content reader's coverage contract,
  with three separately-representable states verified by **three negative controls**.
- **Claimed (report):** `report-01.md:40` — not attempted, gated by D0.
- **Found:** No such verb exists **over the skill corpus**. `manage-architecture`'s `search --content`
  still returns location and strength only (`doc/concepts/code-intelligence.adoc:236` § "Location and
  strength, never the lines"), and nothing addresses a named section of a `SKILL.md` or a
  `standards/*.md`.
  ⚠ **The absence is narrower than "no section-addressed read on any surface", which is false.** Two
  section-granular read verbs already ship, over **plan documents** rather than the corpus, and a
  re-run must extend or explicitly reject them rather than rediscover the shape —
  `plan.md:132-135` names exactly this risk ("an unverified absence produces duplicate work against
  something that already exists"), and `plan.md:106-107` requires extending an existing surface or
  justifying a new home explicitly:
  - `manage-solution-outline read --plan-id X --section S`
    (`marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:606-636`,
    flag declared at `:1015`) — slugifies the requested heading, splits the document on top-level `##`,
    and returns **that section's body alone**. Its coverage contract already separates two of D2's
    three states: a missing section returns `status: error, error: section_not_found` carrying
    `requested_section`; an unreadable file returns the read helper's error before the section branch
    is reached; an empty section returns `status: success` with an empty `content`. That is a working
    precedent for D2's three negative controls, not a fresh design problem.
  - `manage-plan-documents read --section S`
    (`marketplace/bundles/plan-marshall/skills/manage-plan-documents/scripts/manage-plan-documents.py:101`,
    `scripts/_cmd_request.py:172-196`) — the same shape over the request document.
- **Verdict:** **CONFIRMED (correctly not attempted)** — the run was right not to build it. The plan's
  own Verification (`plan.md:142-144`) requires the three negative controls; building the verb on an
  unverified population premise is what D0 exists to prevent. → `gaps.md` G11 records the precedents so
  a re-run starts from them.

### D3 — re-read elimination within an envelope

- **Required (plan):** `plan.md:81-85` — *either* the elimination ships *or* D1 shows intra-envelope
  re-reads are rare and the run records the refutation and drops the deliverable.
- **Claimed (report):** `report-01.md:41` — not attempted, gated by D0.
- **Found:** Neither branch was taken, correctly: the "drop on evidence" branch requires D1's
  magnitude, which the gate blocked. Nothing shipped.
- **Verdict:** **CONFIRMED (correctly not attempted).**

### D4 — restate the epic's value case against the corpus measurement

- **Required (plan):** `plan.md:86-90` — the written value case matches what D1 measured, verified by
  an independent **cold read** (`plan.md:145-148`).
- **Claimed (report):** `report-01.md:42` — not attempted, gated by D0.
- **Found:** `doc/concepts/token-management.adoc:35-41` § 4 "Skill-driven guidance — no tool
  exploration" is unchanged and still asserts pre-loaded skills prevent the exploration loop — which
  is precisely the claim `plan.md:115-117` flags as applying to the *codebase* loop while the skills
  are themselves the larger cost. Nothing was restated; no cold read was dispatched for D4 (the
  sub-agent that ran was dispatched against the D0 halt, `report-01.md:101-141`).
- **Verdict:** **CONFIRMED (correctly not attempted).** With no measurement, there is nothing to
  restate the value case *against*; writing one anyway would be the hand-assembled substitution
  `plan.md:63-64` forbids.

## Correctness review

**No production code shipped, so there is no shipped behaviour to defect-hunt.** PR #1149 changed
exactly two files (`pull_request_read get_files`): `plan.md` — status `renamed` from
`doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control.md`, **zero content
additions** — and `report-01.md`, `added`, 249 additions. `wc -l report-01.md` = 249, so the PR's
`additions: 249` is fully accounted for by the report and the plan move was a pure rename.

What I read to conclude that, and what I checked in it:

- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py:700-790` — the
  producer docstring for the three `exploration_{sub}_bytes` keys. Correctness-relevant properties I
  confirmed for the audit's own use (not defects, they are deliberate): the sub-split **fails open**
  into `exploration_unattributed_bytes` for an unrecoverable path, and there is **no matching
  `_tool_calls` sub-split** (stated verbatim at `runtime_base.py:770` and
  `manage-metrics/standards/data-format.md:186`).
- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:13,163,175-186`.
- `.claude/skills/cloud-plan-lane/SKILL.md:479-510` — the build gate is `*.py`-only
  (`SKILL.md:501-502`), so the report's "no buildable footprint, build skipped" is contract-correct.

**One correctness observation about the run's reasoning, not about code:** the D0 evidence chain is
sound but the field it anchors on cannot answer D1 (§ Report accuracy item 1). Because the answer at
the gate is HALT either way, this does not change the verdict — it changes what a re-run must do.

## Test adequacy

**No test is warranted and none was added** — the run shipped no executable surface. `git ls-files`
under `test/` shows no file touching this plan, and PR #1149's file list is two `doc/plans/**` files.

For completeness, the *existing* coverage of the field the report cites is real, not vacuous. The
first audit asserted this from the fact that two test files **mention**
`exploration_doc_residency_bytes`, which is not evidence — a mention could be inert fixture data. It
was therefore re-established during adversarial review by two mutation sweeps that could have come
back green:

| Mutation | Test file run | Result |
|---|---|---|
| `claude_runtime.py:269,271` — both `doc_residency` returns in `_classify_exploration_target` → `index_answerable` | `test/plan-marshall/platform-runtime/test_metrics_tokens.py` | baseline 32 passed → **1 failed** (`test_document_targets_route_to_doc_residency`), 31 passed |
| `manage-metrics.py:3411` — `_EXPLORATION_SUBSOURCES` loses `'doc_residency'` | `test/plan-marshall/manage-metrics/test_manage_metrics.py` | **3 failed** (`TestExplorationSubsourceRoundTrip::test_measured_zeros_persist_and_render_as_zero`, `::test_split_round_trips_and_still_partitions_after_persistence`, `test_exploration_subsource_fields_match_platform_runtime_contract`), 204 passed |

Both mutated files were snapshotted before mutation and written back from the snapshot afterwards (no
`git checkout`/`restore`/`stash`); `git status --porcelain` shows neither file modified. ⚠ The second
sweep's *first* reading came back all-green because a concurrent agent restored that file mid-run; it
was re-taken and is the reading recorded above. These are not this plan's tests — this plan neither
wrote nor changed them — but the report's D0 evidence chain leans on the field, so the coverage behind
it is worth having measured rather than assumed.

## Report accuracy

Nine claims in `report-01.md` are false, stale, or overstated. The report's central conclusion is
unaffected by all nine. Each is tagged **wrong-when-written** or **stale** — a distinction the first
audit could not always draw, because it read a 50-commit shallow clone; the clone now reaches 280
commits back to `741a1c9`, so every one of these is checkable against `60c34cb`, the run's own merge
commit.

1. **The equation between the metrics field and D1 is materially overstated** (wrong-when-written).
   `report-01.md:46-52` states the field is *"exactly D1's 'how much of each read document a step
   actually consumes.'"*
   It is not. Per its own schema (`data-format.md:163`) and producer
   (`runtime_base.py:754-758`), `exploration_doc_residency_bytes` is **one integer per phase**. It
   therefore cannot answer any of D1's four questions (`plan.md:67-68`):
   - *which* documents are read — no path granularity is retained, only a bytes total;
   - *how often* — `data-format.md:186`: *"There is no matching `_tool_calls` sub-split"*;
   - *how many times within one envelope* — same absence, so D3's magnitude is unmeasurable from it;
   - *how much of **each** read document* — an aggregate, not a per-document figure.
   It also measures **residency** (bytes that entered context) and not **consumption** — the very
   distinction `plan.md:125` insists on: *"D1 must measure **consumption**, not just residency."*
   Correct statement: the field is the closest existing *proxy* for D1's residency half; D1's
   per-document and consumption halves have **no instrument in the tree at all**. → `gaps.md` G1, G2.
2. **`data-format.md:152` no longer resolves** (stale — and it was **exact when written**).
   `report-01.md:111` cites the per-phase definition at `data-format.md:152`. At `60c34cb`, the commit
   that landed this report, `exploration_doc_residency_bytes` was at **line 152** — the citation was
   right. The file has grown since; it is at **163** now. The companion citation `data-format.md:13`
   is still exact. (The first audit could not establish this: it saw only back to `3cb595f`, where the
   line was 154, and so recorded the citation as never-correct.) → G3.
3. **"three synthetic test fixtures … `{legacy,plan,unmeasured}`" is now four** (stale).
   `report-01.md:68-70`. `git ls-tree 60c34cb .../fixtures/dispatch-loop-replay/` returns exactly the
   three named directories, so the enumeration was exhaustive when written; `undatable` was added by
   `d1c3153` (#1278) afterwards, and `ls` now returns four. → G4.
4. **"carry per-*dispatch* context-load columns (`input/output/cache` tokens)" is false for two of
   the three named fixtures** (wrong-when-written). `report-01.md:72-73`. The `legacy` and `plan`
   fixtures carry `rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}` — no
   input/output/cache columns — at `57c63a8` **and at `60c34cb`, the run's own commit**, so this was
   wrong when written, not merely stale. Only `unmeasured` (and the later `undatable`) carry them. The
   conclusion the clause supports — none carries the residency field — is nonetheless true. → G5.
5. **"Committed run reports … grepped for residency/consumption vocabulary — no matches" no longer
   holds** (stale). `report-01.md:115-116`. At `60c34cb` only **8** report files were committed and
   only 020's own mentioned residency, so the sub-agent's sweep was accurate then. Now
   `git ls-files "doc/plans/**/report-*.md" | wc -l` = **112** and `git grep -il residency` over that
   set returns **7** files (020's own report, plus 030, 090, 200, 240, 250 in this epic and
   `multiplattform/010`). None of the seven carries a residency *measurement* — only the vocabulary —
   so the halt is unaffected. → G6.
6. **The coordination quote is attributed to the wrong document** (wrong-when-written).
   `report-01.md:244-245` says plan 010's *"closing note"* anticipates *"a sibling WS-06 plan [that]
   wants this same client pointed at the document corpus."* That sentence is in 010's
   **`plan.md:178-179`**, not in its report — `grep -rin "document corpus\|WS-06" 010-…/report-01.md`
   returns nothing (control: the same grep over the directory hits `plan.md:178`). The substance is
   correct: PR #1140 is confirmed at `010-…/report-01.md:3`, and
   `marketplace/bundles/plan-marshall/skills/lsp-client/` exists with four tracked test files. → G7.
7. **The sibling-plan path no longer resolves** (stale). `report-01.md:80` cites
   `080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case.md` as a flat file. It was
   one at `60c34cb`; 080's own run has since moved it into a directory. The quoted D0-gate text is
   verbatim from what is now `080-…/plan.md:59-60`. → G8. *(This item was missing from the first
   audit's list, which is why its count read "six".)*
8. **The explanation for why `cuioss-review-bot` reviewed despite `skip-bot-review` is a misreading
   of the registry it cites** (wrong-when-written). `report-01.md:168` asserts *"the pr-agent registry
   records that `skip-bot-review` gates only its inline `/improve` comments, not the Guide."* The
   registry records the opposite on both halves: `automatic-review/standards/pr-agent.md:65` sets
   `honors_skip_label: true` (annotated `UNVERIFIED`, which is a reason to treat the outcome as
   untested — not a licence to assert the reverse), and `:168-174` states the label skip *"is enforced
   by the reusable workflow's job-level `if:` guard"* — a guard over the whole `review` job, corroborated by
   `.github/workflows/pr-agent.yml:3-6` ("The org skip rules (… the skip-bot-review label, fork PRs)
   are enforced by the reusable workflow's job-level `if:` guard"). What *is* gated to `/improve` is
   gated by a different, **enabling** label, `pr-agent-improve` (`pr-agent.md:266`, `:345-352`) — not
   by `skip-bot-review`. The **observation** holds and is re-confirmed: `cuioss-review-bot[bot]`
   posted the Guide at 2026-08-10T21:22:32Z on a PR created 21:21:43Z carrying the label. But the
   registry predicts suppression, so the honest reading is an unexplained result — most plausibly a
   label/`opened`-event race — and not a documented exemption. → G10.
9. **The residue's coordination note now points at only half the surface** (stale).
   `report-01.md:243-249` tells the eventual D2 to coordinate with 010's `lsp-client` and to re-verify
   whether that or `manage-architecture` is the better home. Since then plan `240-skill-lsp-server`
   (PR #1256, `5edca5a`, 2026-08-16 — an ancestor of `61a43e5`, so present in the tree the first audit
   read) shipped `pm-plugin-development:tools-corpus-language-server`: a resident language server
   **over the marketplace skill corpus**. It is component-granular, not section-granular
   (`_corpus_index.py:159-185` — `definition` returns the component's file at line 0 by deliberate
   design, `hover` returns description plus frontmatter; no heading or anchor concept exists in the
   index), so it does not satisfy D2 — but it is the corpus-facing client the plan's *"Coordinate; do
   not fork a second client"* (`plan.md:157-160`) now most directly names. → G12.

**Claims that held exactly**, re-verified rather than assumed:

- All six numbered D0 evidence items' *conclusions* (§ D0 above).
- Every reviewer-participation verdict, read from the stored comment bodies via
  `pull_request_read get_comments` on #1149: `cuioss-review-bot` posted the PR Reviewer Guide with
  *"No relevant tests / No security concerns identified / No major issues detected"*; `coderabbitai`
  posted only a skip notice naming `skip-bot-review`; `sourcery-ai` posted nothing; `cla-assistant`
  reported `not_signed`. Coverage 1-of-3 is exact. (The *verdicts* hold; the report's stated
  **mechanism** for `cuioss-review-bot`'s participation does not — see item 8 above. The first audit
  listed that mechanism here as holding exactly; it does not, and the entry is withdrawn.)
- The build-gate claim — `cloud-plan-lane/SKILL.md:501-502` (the `*.py` / no-`*.py` gate table rows,
  read verbatim).
- The Step-8 bridge claim *"No write landed under `doc/plans/` outside this plan's own directory"* —
  PR #1149 `changed_files: 2`, both inside the plan directory.
- PR #1149 is `merged: true`, merged 2026-08-10T21:42:53Z by `cuioss-oliver`, head
  `claude/corpus-residency-admission-control-p6zv1u` — the harness-assigned branch, kept as-is, as the
  lane contract requires.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| The plan is **blocked on corpus availability, not retired**; it becomes runnable when a git-reachable population of instrumented corpus-residency records exists (`report-01.md:238-242`) | **STILL OPEN** | `git ls-files "*metrics.toon"` → empty at `57c63a8`. No `.plan/plans/`, no `.plan/local/archived-plans/`, and `find .plan -name "metrics*.toon"` → empty. Sibling plan 080, run 2026-08-12 (two days later), records the *same* D0 outcome (b) — `080-…/report-01.md:3`. No sibling has landed a population. ⚠ The precondition as the residue words it is also **insufficient**, not merely unmet — see G2. |
| The orchestrator's collect step should **keep 020 queued, not mark it shipped** (`report-01.md:241-242`) | **UNVERIFIABLE** | The orchestrator ledger lives under git-ignored `.plan/`, absent from this clone. Nothing git-reachable records 020's queue state. |
| **Coordination note for the eventual D2** — coordinate with 010's `lsp-client` rather than forking a second one, and re-verify at outline whether an LSP-shaped client suits section-granular markdown reads (`report-01.md:243-249`) | **STILL OPEN; the advice is right but its candidate set is now out of date** | `marketplace/bundles/plan-marshall/skills/lsp-client/{SKILL.md,scripts/lsp_client.py}` exists at `57c63a8` with four tracked test files under `test/plan-marshall/lsp-client/`. No corpus-facing client was forked. Three surfaces the note does not name now bear on D2's home, all present at `61a43e5`: **(1)** `pm-plugin-development:tools-corpus-language-server` — a resident language server *over the skill corpus*, shipped by plan 240 (PR #1256, `5edca5a`), component-granular not section-granular; **(2)** `manage-solution-outline read --section` and **(3)** `manage-plan-documents read --section` — working section-granular reads over plan documents, with a `section_not_found` state already distinguished. A re-run must start from these, not from `lsp-client`-versus-`manage-architecture`. → G11, G12. |

## Out-of-scope and collateral

**None.** Every one of the plan's four exclusions (`plan.md:97-107`) is respected trivially, because
the run shipped no mechanism:

- No skill or standard was dropped from a profile (no `marketplace/bundles/**` change at all).
- No standards document was shortened.
- No token saving was quantified — `report-01.md:186-192` explicitly declines to state a token figure
  rather than guessing one, which is the honest form.
- No second content-search verb was created.

No undeclared change: PR #1149's file list is exactly the two files the report declares.

**One unmet plan instruction, not an out-of-scope violation:** `plan.md:43-45` carries an unconditional ⛔ directing
the run to re-derive the size figures in the clone (`wc -c` over the persona skill directory, and a
re-count of registered components). The report does not record doing so. I re-derived them, so a
future run need not: `persona-plan-marshall-agent/SKILL.md` = **14,835 bytes**; its `standards/` =
**5 files, 102,086 bytes**; whole directory = **116,921 bytes**; `find marketplace/bundles -name
SKILL.md | wc -l` = **156** across 11 bundles. All three of the plan's leads hold. → G9.

## Method and coverage

**Checked, with the command re-run at audit time in every case:**

- Plan contract read in full (`plan.md`, 163 lines) and report read in full (`report-01.md`, 249
  lines); epic README read.
- Each of the six D0 evidence items re-derived independently by the command the report names, plus
  four adversarial extensions of my own (non-`test/` `.toon` sweep, tracked-`archived-plan` sweep,
  `enriched.json` metrics-field sweep, sibling-plan outcome check).
- Every `path:line` citation in the report resolved against the tree; nine discrepancies found, each
  additionally resolved against `60c34cb` to separate wrong-when-written from stale.
- The corpus-facing surfaces the plan's D2 would extend, read rather than assumed absent:
  `tools-corpus-language-server` (`SKILL.md`, `_corpus_index.py`, `corpus_lsp.py`),
  `manage-solution-outline read --section`, `manage-plan-documents read --section`.
- Two mutation sweeps against the field the D0 evidence chain anchors on (§ Test adequacy), both
  restored from a byte snapshot rather than by any `git` command.
- PR #1149 verified live through the GitHub MCP: `get` (merged state, head/base, file count,
  additions), `get_files` (rename + add), `get_comments` (all three bot bodies verbatim).
- The lane contract's build gate and `skip-bot-review` rule read at `cloud-plan-lane/SKILL.md:479-510`
  and `1112-1145`.
- The plan's LEAD size figures re-derived from scratch.
- Grep false-negative discipline: every "found nothing" above is paired with a control that finds
  something with the same pattern shape (e.g. `git ls-files "*metrics.toon"` empty *vs* `git ls-files
  "*.toon"` → 36; `grep "document corpus"` in 010's report empty *vs* the same grep over 010's
  directory → `plan.md:178`).

**Not checked, and why:**

- **The originating per-phase measurement.** Deliberately not sought — `plan.md:129` forbids it and it
  is the condition D0 exists to detect. Its absence is what I verified, structurally.
- **Whether the orchestrator kept 020 queued.** UNVERIFIABLE — the ledger is under git-ignored
  `.plan/`.
- ~~**What the report's citations pointed at *when written*.**~~ **Now checked.** The first audit
  recorded this as unreachable because the clone was shallow at 50 commits (base `3cb595f`). It now
  reaches **280** commits (base `741a1c9`), so `60c34cb` — the commit that landed this report — is
  readable, and every item in § Report accuracy is resolved against it. That reversed item 2 (the
  citation was exact when written) and confirmed item 4 directly instead of by proxy.
- **`./pw verify`.** Not run, per the audit brief; the plan's diff carries no `*.py`, so the lane's
  own gate would skip it too.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

Re-derived at `57c63a8`, 16 commits after the audited state `61a43e5` — all 16 are `doc/plans/**`
audit documents, so no source file moved between the two.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | **No gap was fabricated** — G1 and G3–G9 each re-derived and each holds. Four citation defects: `report-01.md:47-53`→`46-52` (G1), `:112`→`:111` (G3), `:69-71`→`:68-70` (G4), `:245-246`→`:244-245` (G7); plus `plan.md:66-73`→`66-75`, `:74-80`→`76-80`, `:143-146`→`142-144`, `:146-148`→`145-148`, `:64`→`63-64`. G3's *evidence* was wrong in the other direction: `data-format.md:152` was **exact at `60c34cb`**, the report's own commit — the first audit called it a wrong line only because a 50-commit shallow clone hid that. | All nine ranges repinned. G3 re-titled and re-framed as decayed-not-wrong, with a stable Done-when (cite the field name, not a line). |
| A1 | False positives | The D0 bullet *"`find .plan -maxdepth 2` → only `marshal.json` and `project-architecture/`… no `.plan/local/`"* is **now false**: this working tree has grown `.plan/execute-script.py`, `.plan/local/{logs,marshall-state.toon}` and `.plan/temp/`. `.plan/` is untracked and machine-local, so any inventory of it decays. | Bullet and the matching residue cell rewritten around the load-bearing negatives, which all still hold: no `.plan/plans/`, no `.plan/local/archived-plans/`, `find .plan -name "metrics*.toon"` empty. **The D0 verdict is unaffected.** |
| A2 | False negatives | **The D2 row asserted an absence it never checked.** *"There is no section-addressed read on any surface"* is false: `manage-solution-outline read --section` (`manage-solution-outline.py:606-636`) and `manage-plan-documents read --section` (`_cmd_request.py:172-196`) both return one named `##` section without the file, and the first already separates `section_not_found` / read-error / empty-body — D2's three negative controls, working. They are over plan documents, so D2's literal target is still unbuilt and the CONFIRMED verdict survives. | D2 § rewritten with the precedents and their state discrimination; **new G11** (medium, `architecture-core`) to record them in `plan.md` § Expected surface before D2 is built. This is `plan.md:132-135`'s own named risk. |
| A2 | False negatives | **A shipped corpus surface was missed.** Plan 240 (PR #1256, `5edca5a`, an ancestor of `61a43e5`) shipped `pm-plugin-development:tools-corpus-language-server` — a resident language server *over the marketplace skill corpus*. The audit's residue named 240 as "a plan that now exists", never as a landed surface. It does not satisfy D2 (component-granular: `definition` → file at line 0 by design, `hover` → description + frontmatter; no heading/anchor concept in the index), but it is what `plan.md:157-160`'s "do not fork a second client" now points at first. | Residue row rewritten; § Report accuracy item 9 added; **new G12** (low, `lsp/resolvers`) to repoint the coordination note. |
| A2 | False negatives | **A false claim was certified as "held exactly".** The report's explanation that the pr-agent registry exempts the Guide from `skip-bot-review` is a misreading: `pr-agent.md:65` sets `honors_skip_label: true`, `:168-174` and `.github/workflows/pr-agent.yml:3-6` put the skip in a job-level `if:` guard over the whole review job, and the `/improve` gate is a *different, enabling* label (`pr-agent-improve`). The observation holds — Guide posted `21:22:32Z` on a PR created `21:21:43Z` carrying the label, re-read live via `get_comments` — only the mechanism is invented. | Entry withdrawn from "Claims that held exactly"; § Report accuracy item 8 added; **new G10** (medium). |
| A3 | Vacuous evidence | § Test adequacy claimed the existing coverage is *"real, not vacuous"* on the strength of two files **mentioning** the field — which is exactly the re-reading the attack targets. Re-run as a real sweep: mutating `claude_runtime.py:269,271` (`doc_residency`→`index_answerable`) turns `test_metrics_tokens.py` red (1/32); dropping `'doc_residency'` from `_EXPLORATION_SUBSOURCES` at `manage-metrics.py:3411` turns `test_manage_metrics.py` red (3/207). ⚠ The second sweep's first reading came back **all-green** because a concurrent agent restored that file mid-measurement; re-taken per the brief. | § Test adequacy replaced with the mutation table and baselines. Both files snapshotted to `$TMPDIR/adv-020-…-mutsweep/` and written back from the snapshot — no `git checkout`/`restore`/`stash`; `git status --porcelain` confirms neither is modified. The claim survives, now on evidence. |
| A4 | Counts and quotes | One number wrong: the control `git ls-files "*.toon"` returns **39**, not 36 (39 at `61a43e5` too). Everything else re-derived exact: `git grep -l exploration_doc_residency_bytes` = 6 at `61a43e5` (10 now — the audit documents themselves inflate it, so the durable form is "five non-audit files"); 112 reports; 7 residency hits; 249 report lines; 163 plan lines; 156 `SKILL.md` over 11 bundles; 14,835 / 5 files 102,086 / 116,921 bytes; PR #1149 merged, 2 files, 249 additions. Every quoted line verified verbatim against its source (`data-format.md:13,163,186`; `runtime_base.py:770`; `080-…/plan.md:59-60`; `010-…/plan.md:178-179`; `cloud-plan-lane/SKILL.md:501-502`; `pr-agent.yml:3-6`). | 36→39 corrected; the `git grep` count annotated as self-inflating. |
| A5 | Actionability | G3's *Done when* — "resolves to the line it names at the current `main`" — decays on the next edit of `data-format.md`, so it can never stay satisfied. G2's Action said "an instrument that exists", which needs a judgement call to check. Every other gap already carries a concrete path, change and observable condition; none says "review"/"consider"/"investigate". | G3's Done-when rewritten to cite the field name. G2's rewritten to require a per-question mapping (four questions → field or predecessor deliverable). |
| A6 | Severity and topic | Severities re-checked against the calibration and all hold: G1/G2 **medium** (they change a re-run's premise), G3–G9 **low** (stale or unstated claims confined to the run report). No topic was mis-assigned. | New gaps rated: G10 medium (a false claim about a documented review contract, in the section later runs read to judge bot participation), G11 medium (`architecture-core` — the owning surface is the two `manage-*` read verbs), G12 low (`lsp/resolvers`). |
| A7 | Coverage | D0–D4, out-of-scope, report accuracy, test adequacy, residue and method were all covered. One hole: the audit asserted D2's absence and assessed the coordination residue **without reading any corpus-facing surface** — neither the shipped corpus language server nor the two `--section` verbs. That is the only deliverable whose "Found" rested on an unexamined negative. | Closed by the two A2 rows; § Method now lists the corpus surfaces actually read. |
| A8 | Internal consistency | The overall verdict follows from the rows. Two breaks: **(1)** G8 (the 080 flat-file path) traced to nothing in `verification.md` — § Report accuracy listed only six items and G8 was not among them; **(2)** the header's arithmetic ("one equation plus five citations") therefore under-counted. | § Report accuracy now runs to **nine** items, with item 7 covering G8 and items 8–9 the new findings; header restated as one equation, one registry misreading, seven citations. Every gap now traces to a numbered item, and every item to a gap. |

**Residual doubt:** The next round would most likely land on **G11's consequences rather than its
existence** — whether extending `manage-solution-outline`'s section splitter to `SKILL.md` and
`standards/*.md` is actually sound, given that a skill body's `##` structure is not a plan document's
and that progressive disclosure may already bound what a `Skill:` load admits (`plan.md:130`, still
unverified by anyone). That question is D2's design work, not this audit's, and the plan is halted
before it. Two smaller residuals: the *cause* of the pr-agent Guide appearing on a labelled PR is
recorded as unexplained rather than resolved — settling it needs the workflow run log, which is not
reachable from this session; and every count over `.plan/` or over `doc/plans/**` decays by
construction, so the corrected documents pin claims to `60c34cb`/`57c63a8` rather than pretending to
be timeless.

**Verdict on the audit:** SOUND AFTER CORRECTION — the D0 halt and all five deliverable verdicts were
right and are re-confirmed independently, but the audit certified a false claim as exact, asserted D2's
absence without examining the corpus surfaces that would have refuted its scope, and rested a
non-vacuity claim on a grep; all three are now corrected and evidenced.
