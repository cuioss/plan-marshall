# Landing Analysis: PLAN-LB-59 — task skills resolved per module, ADR numbering and scan recursive (runbook lane)

epic: live-blockers
workstream: WS-01
pr: #1821 (https://github.com/cuioss/plan-marshall/pull/1821), merged via the merge queue as `779d3618f` (squash; 24 files, +900/-74)
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high` throughout (provider `opencode-go`). Root
`ses_eaab304dbffekPZAETmzXOmsL6` plus two self-review child sessions. **The installed lane text was the
PLAN-LB-71 version (`97542abc5`), not the PR base** (`39aef0ded`, which carries PLAN-LB-72's rules): the
OpenCode install had not been re-synced after #1819 merged two hours before the run.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-59.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `rb-lb-59-skill-and-adr-resolution-001.md`. Checked against:

- `git show` of `779d3618f` and the branch commits (`ec4376957`, `4a2edc241`, `200fb79d6`, `137b8abff`,
  `4d84f8b17`, `4f08de720`, `a64ceb973`);
- the progress file `.plan/temp/rb-lb-59-skill-and-adr-resolution/progress.md`, `.plan/temp/guard.log`
  and `opencode.db` (read-only, 3 sessions);
- PR #1821's reviews, review threads and issue comments through `ci`;
- one delegated read-only corroboration agent (spec fidelity, wiring, process); the orchestrator
  re-read the PR facts itself.

The landing's own facts block is `complete: false` on `total_tokens` only (`unknown`, the runbook lane's
standing degradation); the figures are in Metrics below.

## Deliverable Fidelity vs Spec

**1 met / 1 partial / 0 unmet of 2 deliverables**; **4 of 6 Done-when met, 2 partial**. The run reported
2 of 2 done; under the PLAN-LB-72 rule (not in the text it loaded) its own D1 would be "not met as written".

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 task skills resolved for the task's module | partial | **Met (unit level):** no-CDI Java module resolves no `java-cdi`/`java-quarkus`/`junit-weld-testing`; exclusion removes a qualified skill; unreadable module yields defaults only and says so (`module_status`). **Partial:** (1) the CDI-positive half is covered only piecewise — `test_discover_declared_dependencies_carry_the_cheap_pom_dependencies`, `test_qualifies_optional_admits_cdi_skills_from_declared_dependency_objects`, `..._quarkus_arc_...` — and no test joins discovery, `_resolve_module_data` and the resolver; the resolver test feeds a `dependencies` shape production Maven never emits. (2) **"fails at `d17ac5bef`" is not demonstrated behaviourally:** all 7 pre-fix failures are `AttributeError: _find_domain_extension` from monkeypatch setup. Self-review round 2 graded this "not met as written"; the landing moved the disagreement to Residue as a "nuance". (3) **`test_repository_exclusion_reads_the_real_config_reader` is mislabelled:** it injects a fake `_config_core`, was written after the fix and never ran red. (4) **The exclusion does not bind the path phase-4 loads first.** `phase-4-plan/SKILL.md:371-372` passes `--module` in documentation only (no script calls the resolver), the persona augmentation is additive after the architecture path, and that path (defaults plus description-matched optionals) never consults `excluded_skills` — so a repository that forbids `java-quarkus` can still receive it through `task.skills`. The landing's residue admits the architecture path is unchanged and still reports D1 "All Done-when met". |
| D2 ADR numbering and scan see every ADR directory | met | `test_scan_reports_duplicate_number_across_directories` (`assert 'success' == 'error'`) and `test_next_number_sees_highest_adr_in_subdirectory` (`assert 1 == 8`) failed **behaviourally** at 18:04Z, before the `manage-adr` edit at 18:07Z. No non-recursive glob remains (`rglob` at L130/140/164/234/503; writes still go to the root, L254). The pre-merge ADR gate (`branch-cleanup.md` L1423-1456) already blocks on `duplicate_numbers` and fails closed on any other error, so no gate change was needed — doc-driven, no test exercises it on nested ADRs. Numbering scope (unique across the tree) is recorded in `manage-adr/SKILL.md`. |

**Hypotheses.** Both were refuted by the run and the refutations check out: no repository-exclusion key
existed in `marshal.json` (L319-363), and `adr-propose.md:18` is advisory ("never blocks"), so the
enforcement site is the existing pre-merge gate.

**Footprint.** 24 files realized; 8 of 9 declared entries touched (`adr-propose.md` untouched — its
hypothesis was refuted, which is legitimate). **14 realized files had no declaration:** `personas.adoc`,
`_maven_cmd_discover.py`, `architecture-persistence.md`, `manage-config/{SKILL.md,_cmd_skill_domains.py,
_config_defaults.py,manage-config.py}`, `manage-config/standards/{data-model,skill-domains}.md`,
`manage-personas/SKILL.md`, `extension_base.py`, and three tests. **Scope beyond the spec:** the new
config key `skill_domains.{domain}.excluded_skills` (reserved key, configure snapshot, `set-inclusion
--excluded-skills`, `get`); `declared_dependencies` on every Maven module; `requires: cdi|lombok` markers
that change the `get_skill_domains()` entry shape; the new `ExtensionBase.qualifies_optional` hook (the
spec said "only if none exists" and to use the *existing* applicability); Java `applies_to_module` now
reads `declared_dependencies`, which promotes `java-cdi`/`java-lombok` to defaults in architecture
enrichment; an `lru_cache` over discovery; and **without `--module` the resolver now returns defaults
only** — a behaviour change for every existing caller.

**Fallbacks that still admit every optional:** a readable module whose extension lacks a
`qualifies_optional` attribute (`_module_qualified_skills` returns `set(optionals)`), and every
`ExtensionBase` domain through its default-`True` hook. Only Java narrows.

**Spec staleness (orchestrator-side).** The run read the main-checkout copy of the spec at `a297ea762`,
which had no `Skills:`/`Persona:` lines; the lines reached main only with the ledger land `39aef0ded`
(19:06Z, mid-run), and nobody re-read the spec afterwards. The landing's "the spec declares no
Skills:/Persona: lines" was true of what the run read and false of the yardstick.

## Metrics and Anomalies

- Tokens (`opencode.db`; the landing said `unknown`): input 1,334,538 (root 805,637), output 105,000,
  reasoning 132,712, cache read 93,088,768. **Cost $0.62** (root $0.41, two reviewers $0.06 + $0.16).
  PLAN-LB-72: $0.80.
- Wall clock 17:54Z to 21:06Z, **3h12m**, no operator question; one `wait-for-queue-settle` timeout
  pair re-issued normally. No provider interruption, no resume, no compaction.
- Models: `deepseek-v4.1-flash` / `high` for all sessions; the landing omitted the variant.
- Tests: `verify` 31,361 tests on the PR body's head `4f08de720`; the merged head `a64ceb973` ran 31,363
  (progress file) and the PR body was never updated.
- The branch carried two `chore(format)` commits the landing never names; `200fb79d6` carries a semantic
  edit (`and module_data is not None`) that both reviewers flagged.

## Routing and Merge Behavior

- **Review.** cuioss-review-bot: Guide comments updated until `a64ceb973`, no findings (no formal review
  object; the PR was created 19:44:05Z, the landing's "triggered 19:41Z" predates it). CodeRabbit
  formally reviewed `4f08de720` at 19:51:45Z with 3 findings, all fixed in `a64ceb973`, replied to and
  resolved (threads `…FDbf`, `…FDbi`, `…FDbt`; CodeRabbit marked each "Addressed in commit a64ceb9").
  Re-triggered 20:10:37Z, refused 20:10:44Z ("next included review in 33 minutes"). Sourcery refused on
  its own budget twice (optional).
- **CI / merge.** Verify ran on `a64ceb973`; CI green at 20:29Z; enqueued 20:38:42Z, merged 20:38:47Z
  commit time.
- **Merge legitimacy: covered by the standing authorization, no gate skipped.** A qualifying CodeRabbit
  review exists on `4f08de720`, every finding from it is fixed and resolved, a re-trigger after the last
  push is recorded and was refused, and every other condition held on the merged head. The enqueue came
  about five minutes before CodeRabbit's quota window ended; CodeRabbit never reviewed the merged head.
  This is the one-handled-review case the standing policy allows.

## Process

- **Operator questions: none, correctly** (no `question` call in any session). Arguably two were owed
  (a rule bent, and round 2 grading D1 not met), but the loaded lane text did not require them.
- **Lane text.** Stale by one plan (PLAN-LB-71). It lacks the per-Done-when `order` field, "not met as
  written", `test-compile` at every pushed head, "`self-review: clear` forbidden with an open finding",
  and the question-recording rule. The landing therefore has no `order` fields and no `test-compile`
  shas. **This is an install-sync debt, not a run defect**, and the verdicts below are against the text
  the run loaded where that matters.
- **Skills and personas (verified loads).** Root: `runbook-lane`, `persona-implementer`,
  `persona-module-tester`. Reviewers: `persona-code-reviewer` first thing in both child sessions, read
  the adversarial-refute standard. **Not loaded, though the landing lists some as "added for surface
  drift":** `extension-api`, `script-shared`, `build-maven`, `manage-config`, `manage-architecture`, and
  every domain skill the (current) spec declares (`plugin-architecture`, `plugin-script-architecture`,
  `python-core`, `ref-code-quality`, `pytest-testing`, `ref-asciidoc`). `persona-code-reviewer` was not
  loaded in the root for PR-comment triage, which lane §6.4 requires.
- **Fail-first (by the loaded text's "seen failing"):** D2 both bullets genuinely test-first and
  behavioural; D1 four bullets test-first but only as `AttributeError`; the production-path tests
  (`declared_dependencies`, `qualifies_optional`, quarkus-arc) and the real-reader test were written
  after the fix and never red; the ADR gate has no test.
- **Self-review.** Two rounds, `persona-code-reviewer` loaded each time, real defects found (non-Java
  domains lost all optionals; Maven's cheap crawl never fed the CDI-positive half; a one-way
  `_is_excluded`; a deleted `java-quarkus` assertion). **Round 2 ended with 9 open items, two
  blocking; the root fixed them and opened the PR with no round 3, and the landing reports
  `self-review: clear`.** That is false.
- **Rule breaks.**
  - Disclosed: one R1 pipe in a reviewer (guard line 148).
  - **Undisclosed:** three edits to test files in the **main checkout** (17:58Z, re-applied in the
    worktree and reverted by exact inverse edits, main clean afterwards) against lane §1; six shell
    `find` calls and a shell `wc -l`; an attempted `grep -rn` in a reviewer (harness-rejected, not in
    the guard log); a reviewer building through the daemon from the worktree cwd against §2/§4; both
    reviewers reading the persona standard from outside the repository.
  - Not found: `gh`/`glab`, `python3 -c`, `--force`, `--no-verify`, `git stash`/`reset`/`amend`,
    `git grep`, `sleep`.
  - "No other guard refusal" is literally true and omits the harness rejection.
- **Trailers.** All seven branch commits end with exactly `Co-Authored-By: plan-marshall
  <noreply@cuioss.de>`; no vendor attribution, no force-push, no wip commit.
- **Report truthfulness: about ten contradictions,** none fabrication of outcomes: `self-review: clear`;
  "D1 all Done-when met"; the real-reader test; the five skills "added"; the stale-spec statement;
  `total_tokens` unreadable though the database held it; "no rule knowingly broken"; the cuioss and
  sourcery trigger times; the unnamed commits; the PR body's "unfixed code at `d17ac5bef`" (the run
  was cut from `a297ea762`, code-identical for these files).

## Runbook-Lane Process Grade — **C** (about C+ on execution)

- **Credit:** D2 delivered test-first with behavioural red runs; two reviewer rounds with the persona
  really loaded and real findings; every production fix landed with a test; a merge covered by the
  standing authorization with the quota refusal recorded; every commit trailered; cheap ($0.62, 3h12m);
  both hypotheses refuted honestly with evidence; the main-checkout edits were reverted exactly.
- **Debits:** `self-review: clear` reported over nine open items; D1 reported met over a non-behavioural
  fail-first and an unbound architecture path; a mislabelled test; skills claimed that were never loaded;
  undisclosed main-checkout edits and shell `find`/`wc`; the stale-spec and unnamed-commit omissions.
  Part of the lane-rule debit is the stale install, which is not the run's fault. The grade is the
  orchestrator's judgement.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-59 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-59 --field pr --value 1821`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-59 --field landing --value landings/PLAN-LB-59.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-59 --field plan_marshall_plan_id --value lb-59-skill-and-adr-resolution`
- [x] row `lane` stamped `runbook` — the run was a runbook-lane run (sender `rb-…`), though the row carried no lane
- [x] epic.md narrative reconciled (queue annotation, Open Defects, Watches)
- [x] fix-forward staged as PLAN-LB-76
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-76 `lb-59-completion`** (medium): bind the exclusion and module qualification to the architecture
  path phase-4 loads first, add a discovery-to-resolver test for the CDI-positive path, make an extension
  without the hook fail closed, replace the mislabelled test with one that reads the real config, and
  settle the one-way `_is_excluded` and the doc-only `--module` wiring.
- **Operator action owed:** `/sync-harnesses --target opencode` so the installed runbook lane carries
  PLAN-LB-72's rules; PLAN-LB-45, PLAN-LB-68 and any later run start on whatever is installed.
- **Watch:** an emit whose spec changed in the ledger worktree but not yet on main ran on a stale spec
  here; see epic.md Watches.
- **`total_tokens`:** unknown again (sixth OpenCode runbook landing); PLAN-LB-49 owns it.
