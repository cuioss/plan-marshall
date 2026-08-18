> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Git artifact scanning stops offering live plan state, and destructive-recovery prose stops routing readers to `git checkout --`

**Epic:** truthful-signals
**Branch prefix:** `fix` — every deliverable removes a shipped false signal or an unguarded destructive instruction; nothing here is a new capability.

## Problem

Two shipped surfaces tell a reader something confidently untrue, and in both cases the untruth ends
in data loss.

**The artifact scanner.** `scan_artifacts`
(`marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`) prunes
*nested* git repositories and worktrees from its walk, but never applies that pruning to the scan
**root** itself. From phase 5 onward a plan's cwd is pinned to its own worktree and
`cmd_detect_artifacts` defaults `--root` to `Path.cwd()`, so the plan's own checkout **is** the scan
root and its live audit trail (`<root>/.plan/local/plans/{id}/logs/work.log`) sits inside it. The only
thing keeping that file out of the `safe` (auto-deletable) list is the `.gitignore` lookup — which
`--no-gitignore` disables, which a project whose `.gitignore` lacks a `.plan/*` rule never had, and
which `get_gitignored_files` silently discards on **any** git failure by returning `set()`. Meanwhile
`workflow-integration-git/SKILL.md:100` states the absolute that this cannot happen, and instructs the
agent "For safe artifacts, delete them." The two ignore-exclusion mechanisms are also mutually
covering in the test suite, so either one can be deleted by a refactor with no test going red.

**The recovery prose.** Plan `210` collapsed the named `.plan/marshal.json` recovery contract into a
single inspection-first authority at
`marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md`, and added a regression
guard at `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py`. The guard does not
hold: `_references_authority` returns true for any region that mentions `planning.md` and "named
recovery" — both true by construction of the region heading — so a full restatement of the contract
passes, and `test_named_recovery_never_instructs_unconditional_discard` sweeps every derived region
but only for two literal signatures (a `Recovery:`-prefixed `git checkout --` line and an "always
safe" phrase), never asserting that every derived region is `_is_inspection_first` — the sibling
`test_named_recovery_inspection_first_population_nonempty_and_covers_known_members` asserts that only
of the three already-known members. And a **fourth** destructive site was missed
entirely: `workflow-integration-git/standards/worktree-handling.md` § "Recovery Loop" routes a dirty
path to `git -C {main_checkout} checkout -- {path}` labelled "(typical case)", while its own § "Filter
Rule" names `.plan/marshal.json` as exactly the kind of tracked file that reaches that loop.

Alongside these sit a cluster of false statements in the phase-handshake invariants
(`plan-marshall/scripts/_invariants.py`) — a docstring diagnosing a defect that was refuted by
execution, a guard advertised as tested that is not, a `None` return called "fail-closed" that does
not block the boundary it names — plus a guard that reports a filtered zero without the population it
filtered, six dispatch sites invisible to both audit surfaces, and a command-table row naming an
anchor the code no longer reads.

Every gap this plan closes is written up in full, with its evidence, in the git-tracked gap documents
under `doc/plans/truthful-signals/*/gaps.md`. **Read the cited entry before writing its fix** — those
documents carry reproduction detail this plan does not restate.

## Goal

A scan of a plan's own worktree never offers that plan's live state for deletion, by a mechanism that
does not depend on `.gitignore`, on a flag, or on a git subprocess succeeding — and the documents that
claim so name the real mechanism. No document in the `plan-marshall` bundle routes a reader to
`git checkout --` on `.plan/marshal.json` without inspection and an explicit operator disposition, and
the regression guard that asserts this fails when a restatement or a reworded fourth site is
introduced. The handshake-invariant prose describes what the code does rather than a refuted
diagnosis, every guard that reports a filtered set also reports what it filtered, and every dispatch
site emits into the audit surface.

## Deliverables

Ordered so the six `high` gaps land in D1–D4. A run that stops early must have shipped those.

**D0 is a gate: if either derivation below fails, HALT the plan and report — do not proceed to D2,
D3 or D6 on a hand-written list.**

1. **D0 — Derive the two populations this plan's scope rests on** *(closes no gap; it is the premise
   for D2, D3 and D6)*
   Two sets are derived from the tree and written into the run report before any other deliverable
   starts. **Do not hand-maintain either as a list in this plan or in the report if the derivation
   fails — a hand-maintained population is the defect class D2 and D6 exist to close.**
   - **P1 — named-recovery regions.** Run the existing derivation
     `_derive_named_recovery_regions()` in
     `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py` and record the regions
     it returns (path + heading line). Then repeat the same heading-shape sweep over
     `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/*.md`, which D3
     brings into scope.
   - **P2 — dispatch sites.** Sweep `marketplace/bundles/**` for every `effort resolve-target`
     occurrence, then keep only the **dispatch sites**: an occurrence that instructs an agent to
     resolve a target and then use the resolved `{target}` in a `Task:` dispatch — whether the `Task:`
     block sits in the same document or in the caller the document hands the target to. Discard every
     occurrence that merely *describes* the verb: its own reference documentation
     (`manage-config/SKILL.md`, `manage-config/standards/data-model.md`,
     `plan-marshall/standards/effort-*.md`, `extension-api/standards/*.md` prose about the resolver,
     `ref-workflow-architecture/**`, `plan-retrospective/**`, the `plugin-doctor` rule text) and the
     resolver's own source (`manage-config/scripts/_cmd_effort.py`) — which documents a resolve without
     `--workflow` as a legitimate **pure query that emits nothing**, so a sweep that demands
     `--workflow` everywhere would be wrong, not thorough. Partition the kept set into those that pass
     `--workflow` and those that do not; record both halves and the discard rule applied. **Floor:** the
     six sites 280/G3 names (listed under D6(b)) must all land in the kept set. If the discard rule
     drops any of them, the rule is too narrow — widen it and re-derive before proceeding.
   *Done when:* the run report carries both populations with the command that produced each, and each
   is non-empty. **If either sweep returns an empty set, or `_derive_named_recovery_regions` cannot be
   executed, the run HALTS**: it records the failed derivation, ships nothing that depends on it, and
   reports the plan blocked at D0. (An empty P1 or P2 means the derivation broke, not that the tree is
   clean — the gap documents establish both populations as non-empty; re-derive, never assume.)

2. **D1 — `scan_artifacts` never offers a plan's live state, and each ignore mechanism is pinned on
   its own** *(closes 140/G1, 140/G2 — both `high`)*
   In `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`:
   - **(a)** Before the `respect_gitignore` branch in `scan_artifacts`, drop any relative path whose
     **first segment** equals the plan-state directory name. The name is already read in this module as
     `_PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')` — reuse that constant (it is currently
     defined *below* `scan_artifacts`; move the definition above the function rather than duplicating
     the literal). The exclusion must be unconditional: neither `--no-gitignore`, nor a `.gitignore`
     with no `.plan` rule, nor a failed git call may defeat it.
   - **(b)** Rewrite the `scan_artifacts` docstring and the sentence at
     `workflow-integration-git/SKILL.md:100` so the guarantee they state is the unconditional
     exclusion, not `.gitignore`. The current sentence beginning "Between the two mechanisms a plan's
     finalize never offers…" is the false absolute; it must not survive in a form that attributes the
     scan-root case to `.gitignore`.
   - **(c)** Give the prefix-aware collapsed-directory exclusion (`_split_ignored` / `_is_ignored`) a
     test that reaches it **without** the nested-boundary pruning: monkeypatch
     `git_workflow.get_gitignored_files` to return `{'ignored-tree/'}` against a plain, non-repo
     directory containing a matching artifact, and assert nothing beneath `ignored-tree/` is offered.
     Rename `TestDetectArtifactsLivePlanArtifacts::test_gitignored_worktree_contents_excluded_per_contract`
     (or rewrite its docstring) so it names the mechanism it actually pins rather than the exact-match
     defect it does not detect.
   *Done when:* four tests exist in
   `test/plan-marshall/workflow-integration-git/test_git_workflow.py` and **each has been seen RED
   against the defect it names, with the red run recorded in the run report**: three build a repo whose
   scan root is a plan worktree containing `.plan/local/plans/{id}/logs/work.log` plus a control
   artifact beside it and assert `work.log` is in neither `safe` nor `uncertain` while the control **is**
   in `safe`, for (i) `respect_gitignore=False`, (ii) `respect_gitignore=True` with a `.gitignore` that
   does not mention `.plan`, and (iii) `respect_gitignore=True` with `get_gitignored_files`
   monkeypatched to `set()` — all three red when (a) is reverted; and the fourth is (c)'s prefix-branch
   test, red when the prefix test in `scan_artifacts` is reverted to the exact-string form
   `rel.replace(os.sep, '/') in ignored_files` **while the nested-boundary pruning is left in place**.
   That last condition is the one the current suite fails; see `140-…/gaps.md` G2 for the measured
   mutation.

3. **D2 — The named-recovery guard detects a restatement and covers every derived region**
   *(closes 210/G2, 210/G3 — both `high`)*
   In `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py`:
   - **(a)** Replace `_references_authority`'s `'planning.md' in low and 'named recovery' in low`
     heuristic with a check that a non-authority region is **deferential**: it carries an explicit
     pointer to the authority section (the cross-reference form
     `` `plan-marshall:plan-marshall/workflow/planning.md` § "Named recovery case — `.plan/marshal.json`" ``,
     as a `- ` bullet or an inline `§` citation) **and** does not restate the contract — concretely,
     it does not carry the operator-disposition enumeration (`Keep` **and** `Discard` as list items)
     that only the authority may carry. Use that enumeration test, not a line/character budget: a
     budget needs a threshold nobody can settle mid-run.
   - **(b)** Widen `_is_authority` so it recognises any concrete `git diff` inspection command against
     `.plan/marshal.json`, not only the single literal `git diff -- .plan/marshal.json`.
   - **(c)** In `test_named_recovery_never_instructs_unconditional_discard`, add a **universal**
     assertion: every region in the derived population must satisfy `_is_inspection_first`, with
     offenders listed by `path.name:lineno`. Keep the test's existing two literal-signature checks
     (the `Recovery:`-prefixed discard and the "always safe" phrase) as an additional floor.
     Broaden `_UNCONDITIONAL_DISCARD` to match any `git checkout -- .plan/marshal.json` /
     `git restore … .plan/marshal.json` occurrence, and exclude a region from the offender list only
     when that same region satisfies `_is_inspection_first` — so the authority's own cautionary
     mention still passes.
   *Done when:* **both** mutations below have been run and recorded in the run report. (i) Injecting a
   full restatement of the contract at `planning-outline.md`'s outline boundary — *with or without* the
   exact `git diff --` literal — makes `test_named_recovery_contract_is_a_single_authority` fail.
   (ii) Adding, as a new `.md` file under
   `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/`, a named-recovery block that
   instructs `git checkout -- .plan/marshal.json` **without** the literal `Recovery:` prefix, carries
   **no** `always safe` / `always a spurious` wording, **and** carries the standard cross-reference
   bullet, makes `test_named_recovery_never_instructs_unconditional_discard` fail and name that block.
   Both mutation files are reverted before commit (verify with `git status --porcelain`), and the
   unmodified tree passes the whole module. The weaker mutation — a block *without* the cross-reference
   bullet — already fails today and does **not** settle this deliverable.

4. **D3 — The layer-D recovery loop is inspection-first, and the guard sweeps its directory**
   *(closes 210/G5 `high`, 210/G4 `low`)*
   - **(a)** In
     `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md`
     § "Recovery Loop": step 1 must surface **content**, not only paths — add
     `git -C {main_checkout} diff -- {path}` for each path in `newly_dirty[]`. Delete the
     `(typical case)` qualifier from the *Revert* bullet and replace it with the disposition
     requirement: a revert happens only on an explicit operator decision for that one path. Add the
     irrecoverability caveat in the wording the authority already uses in `planning.md` (`git checkout --`
     destroys uncommitted, unstaged content with no undo — no reflog and no `git fsck` recovers a
     worktree file). Add a cross-reference to
     `plan-marshall:plan-marshall/workflow/planning.md` § "Named recovery case — `.plan/marshal.json`"
     as the single authority, and name `.plan/marshal.json` as the highest-risk member of
     `newly_dirty[]` given the same document's § "Filter Rule". Amend the § "Granularity Trade-Off"
     bullet that restates the same recovery to match.
   - **(b)** Extend the regression surface: widen `_derive_named_recovery_regions`
     (`test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py`) to sweep
     `workflow-integration-git/standards/*.md` as well as the workflow directory, so D2(c)'s universal
     assertion covers this document. If the widened sweep does not match the § "Recovery Loop" region
     by heading shape (it carries a `###` heading, not the `**Named recovery case —` marker), add a
     sibling assertion over `worktree-handling.md` instead: no `git checkout --` / `git restore`
     instruction in that file stands without an inspection-plus-operator-disposition qualifier in the
     same section.
   - **(c)** In `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md`, tighten
     the authority's premise sentence: cite `plan-marshall:phase-3-outline` § Enforcement → Prohibited
     actions and `plan-marshall:phase-4-plan` § Enforcement → Prohibited actions alongside the existing
     `phase-2-refine` citation (so every phase the sentence names has a citation a reader can follow),
     and correct the write-confinement clause, which currently names one allowed write path while
     `phase-2-refine/SKILL.md` § Allowed write paths lists two — re-read that section and match it
     rather than copying a path list from here.
   *Done when:* `worktree-handling.md` contains no `(typical case)` qualifier on a `checkout --`
   instruction, § "Recovery Loop" step 1 names a concrete `git diff` command, the section carries the
   irrecoverability caveat and the `planning.md` cross-reference; the test from (b) has been **seen RED
   against today's `worktree-handling.md` text and green after the edit**, with the red run recorded;
   and every phase named in the `planning.md` premise sentence resolves to a citation that states the
   prohibition for that phase.

5. **D4 — `_capture_config_hash`'s prose states what the code does, and its non-dict guard is tested**
   *(closes 290/G1 `high`, 290/G2 `medium`, 290/G3 `low`)*
   - **(a)** In `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`,
     rewrite the `_capture_config_hash` docstring's second defect clause. The claim that the pre-fix
     capture "passed `--audit-plan-id`, which the `plan` noun does not accept, so the subprocess exited
     non-zero and the capture was silently `None` at every boundary — a signal that never fired at all"
     was **refuted by executing the pre-fix body** (see `290-…/gaps.md` G1). Delete that clause
     entirely and state the one real pre-fix defect: the old capture read a **phase-scoped** config
     subtree, so its hash changed at every boundary by construction and the cross-phase scan flagged a
     spurious drift. Apply the same correction to the section comment in
     `test/plan-marshall/plan-marshall/test_invariants_behavior.py` — the lines stating the
     phase-scoping defect are accurate and **must survive**; only the `exit 2 -> silent None` half goes.
     The mechanism that refutes the claim is git-reachable in this clone at
     `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template`
     (`extract_audit_plan_id`, and its `--audit-plan-id … (stripped before passing to script)` help
     line): the executor strips the flag before the target parser runs. **Do not attempt to run
     `.plan/execute-script.py` to confirm this — `.plan/` is git-ignored and absent from this clone.
     The template is the evidence.**
   - **(b)** Add `test_capture_config_hash_none_when_marshal_not_a_dict` to
     `test_invariants_behavior.py`: write `marshal.json` containing a top-level JSON array, monkeypatch
     `inv.get_marshal_path` at it as the sibling tests do, and assert
     `inv._capture_config_hash('p', {}, '5-execute') is None`. Rename
     `test_capture_config_hash_none_when_marshal_unreadable` or its docstring so "unreadable" is not
     used for what is in fact unparseable JSON.
   - **(c)** Replace the word "fail-closed" in the `_capture_config_hash` docstring (and its echo in the
     test docstring) with an accurate statement of all three directions: at **capture** the invariant is
     recorded as not-applicable (empty column, boundary **not** blocked); at **verify** a captured value
     against an observed empty raises a blocking diff; **retrospectively** `summarize-invariants` emits a
     severity-`error` `missing invariant config_hash` finding for the blank column.
   *Done when:* a grep of the two files for `does not accept`, `exited non-zero`, `never fired at all`,
   `exit 2 -> silent`, and `fail-closed` (scoped to `_capture_config_hash` and its tests) returns zero
   hits; and the new non-dict test passes and has been **seen RED with the `isinstance` guard deleted**
   (deleting it makes the capture raise `AttributeError`, not return a hash — the mutation and its
   revert are recorded in the run report).

6. **D5 — `get_gitignored_files` cannot silently mean "nothing is ignored", and says which command it
   runs** *(closes 140/G5 `medium`, 140/G3 `medium`, 140/G4 `low`)*
   In `git-workflow.py`:
   - **(a)** Give `get_gitignored_files` a return type that distinguishes "no ignored files" from
     "could not determine" — return `None` on any non-zero exit, `TimeoutExpired`, `FileNotFoundError`
     or `OSError`. Propagate it: when `respect_gitignore=True` and the ignore set is indeterminate,
     `cmd_detect_artifacts` returns `make_error(...)` — the shape it already uses for a missing
     directory — rather than a `safe` list computed from an empty ignore set. A caller that genuinely
     wants the non-repo behaviour passes `--no-gitignore`. If an existing test in
     `test_git_workflow.py` scans a non-repo root with default flags and now errors, update that test
     to pass `--no-gitignore` and name it in the run report as a deliberate behaviour change.
   - **(b)** Correct the `get_gitignored_files` docstring, which currently says it "Uses `git
     check-ignore`" while the body runs
     `git ls-files --others --ignored --exclude-standard`. Name the real command and the two properties
     that matter here — it enumerates ignored files individually but collapses a nested repository to a
     single trailing-slash directory entry — and keep the existing not-a-repo/git-unavailable clause,
     updated to the new return contract.
   - **(c)** Extend both `--no-gitignore` descriptions — in `git-workflow.py` the `'help'` value of the
     `--no-gitignore` entry in the declarative `detect-artifacts` command spec (the file registers
     arguments as spec dicts; it contains no `add_argument` call and no `help=` keyword, so locate it by
     the `'flags': ['--no-gitignore']` entry), and the parameter line in
     `workflow-integration-git/SKILL.md` — to state that the nested git repository/worktree skip is
     unconditional and unaffected by the flag.
   *Done when:* a test in `test_git_workflow.py` monkeypatches the `git ls-files --ignored` call to
   raise, invokes `cmd_detect_artifacts` with default flags against a repo containing one gitignored
   artifact, and asserts the result carries an error status and no `safe` entry for that artifact —
   **seen RED before (a) lands**; no occurrence of `check-ignore` remains in `git-workflow.py`; and both
   `--no-gitignore` strings mention the unconditional nested-boundary skip.

7. **D6 — Every guard publishes the population it examined, and every dispatch site emits**
   *(closes 330/G3, 280/G3 — both `medium`; the dispatch half is gated on D0's P2)*
   - **(a)** Capture the exempted half of the layer-D main-dirty filter, which
     `_filter_main_dirty_paths` currently drops on the floor (`retained, _exempted = …`, only
     `retained` returned). Add a `main_dirty_exempted` list column: register it in `HANDSHAKE_FIELDS`
     **and** `HANDSHAKE_LIST_FIELDS` in
     `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_store.py`, have
     `_capture_main_dirty_files`'s sibling capture return the exempted set, and register it in the
     invariant tuple list in `_invariants.py` alongside `('main_dirty_files', _always,
     _capture_main_dirty_files)`. Register it as **informational and non-blocking**, which takes two
     explicit acts, because both defaults run the other way: add
     `'main_dirty_exempted': 'informational_only'` to `INVARIANT_BLOCKING_SCOPE` in `_invariants.py`
     (`is_invariant_blocking_at_phase` documents that an **unmapped** invariant fail-safes to
     `blocking_at_every_boundary`, so omitting the entry makes the column block every boundary on a set
     that legitimately changes at every boundary); and do **not** add it to
     `summarize-invariants._CORE_INVARIANTS`, or every historical row without the column becomes a
     severity-`error` `missing invariant` finding. Document the new column in
     `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md`: both the
     invariant table row next to `main_dirty_files` **and** the `handshakes[N]{…}` TOON field-order
     header above that table, which enumerates every column and would otherwise disagree with the
     store.
   - **(b)** For each member of D0's P2 that lacks `--workflow`, add
     `--workflow {the workflow doc the subagent loads} --plan-id {plan_id} --caller
     plan-marshall:{calling-skill}` to the `effort resolve-target` call, following
     `plan-marshall:ref-workflow-architecture/standards/dispatch-logging.md` § "Canonical invocation" —
     the same document that states the obligation ("Callers that today emit no dispatch log MUST pass
     the dispatch context to their resolve"). The six sites the gap names are in
     `plan-marshall/workflow/planning.md` (light-lane phase-3-outline),
     `plan-marshall/workflow/research-best-practices.md`,
     `persona-plan-marshall-agent/standards/agent-behavior-rules.md` (two calls),
     `phase-6-finalize/standards/finalize-step-simplify.md`,
     `extension-api/standards/ext-point-dynamic-level-executor.md`, and
     `pm-plugin-development/skills/plugin-doctor/standards/doctor-marketplace.md` — **treat that as a
     lead and use D0's P2 as the authority; every line number in the gap document has already drifted
     once.** In the same edit, correct the sentence in `research-best-practices.md` that says
     `resolve-target` "returns an `execution-context-reader-{level}` variant": the reader surface reads
     the level and *composes* the variant name, while `resolve-target` returns the plain
     `execution-context-{level}` — confirm against
     `plan-marshall/standards/effort-roles.md` and `manage-config/standards/data-model.md` before
     rewording.
   *Done when:* a new test under `test/plan-marshall/plan-marshall/` — sited in whichever existing
   handshake/invariants module already exercises the main-checkout captures, derived from the test tree,
   not guessed — drives the new capture against a tree carrying a dirty **untracked** `.plan/` path and
   asserts that path appears in the returned exempted set and **not** in `main_dirty_files`, and that
   test passes; `phase-handshake.md` describes the column in both the invariant table and the TOON
   header; the existing handshake and `summarize-invariants` suites pass unchanged; and a **re-derived**
   P2 finds no member of its dispatch-site set that omits `--workflow` (occurrences discarded by P2's
   non-dispatch rule are out of scope and stay as they are).

8. **D7 — Correct the stale row, the dead marker, and the run report**
   *(closes 310/G1 `medium`, 050/G7 `low`, 310/G6 `low`)*
   - **(a)** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md` — the
     `baseline-reconcile` row of the `git-workflow` command table still says the verb "lists upstream
     commits since the captured `worktree_sha`". No code reads `status.metadata.worktree_sha` for this
     any more; `_cmd_baseline_reconcile.py`'s `_resolve_merge_base` computes
     `merge-base(HEAD, origin/{base})` on every call. Replace the clause with "lists upstream commits
     since `merge-base(HEAD, origin/{base_branch})`, recomputed per call", and add "non-mutating on
     every classification — never moves the branch ref" to the row.
   - **(b)** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — the
     `# SHIM(B):` marker block sitting above `_REFERENCES_REQUIRED_KEYS` names a tolerance that is a
     key's *absence* from a tuple, not a code branch: nothing would be deleted when its
     `shim-remove-when` holds. First check `_capture_references_valid` and its callers for a real
     tolerate-branch over a pre-retirement `references.json`; **if one exists, move the marker onto
     that branch; if none exists, delete the marker block**, keeping the prose comment immediately
     above it that already records the retirement in full. Record which of the two the run found.
   - **(c)** `doc/plans/truthful-signals/310-baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges/report-01.md`
     — complete the two unfilled header placeholders (`**PR:** _pending_`, `**Outcome:** _in progress_`)
     with the PR number and the merge commit. The report's § Contract check names the PR (row "7 PR
     cycle" — a lead, re-read it) but names **no** merge commit — it was committed with the merge
     still pending, and the
     only SHA it carries is the branch head. Derive the merge commit from this clone's history
     (`git log --oneline --grep="(#{pr})"` for that PR number), never from the report. Correct the
     § Build gate count word, which says "three `.py` files" and then enumerates four (re-derive the
     count from `git show --name-only` on the derived merge commit rather than trusting either
     figure); and
     **do not strike** the § Findings clause claiming "no stale … 'init-time SHA anchor' prose
     survives" — a run report records what the run claimed. Append a one-line correction after it
     naming the surviving site(s) and pointing at that plan's own `gaps.md` G1/G2.
   *Done when:* `grep -rn "captured .worktree_sha" marketplace/` returns zero hits and the
   `baseline-reconcile` row names the merge-base anchor; `_invariants.py` carries no `# SHIM(B):` block
   on `_REFERENCES_REQUIRED_KEYS` (or carries one on an actual tolerate-branch, with the branch named
   in the run report); and `report-01.md`'s header carries the PR and merge commit, its build-gate
   count matches the re-derived figure, and the sweep clause carries an appended correction line.

## Out of scope

Every exclusion carries its reason, because there is no operator watching for drift mid-run.

- **Every other gap in the seven source plan directories** — `140/…` is fully assigned here (all five
  of its gaps), but
  `050` G1–G6, `210` G1, `280` G1/G2/G4+, `290` G4/G5, `310` G2/G3/G4/G5/G7/G8, and `330`
  G1/G2/G4/G5 are **not** in this plan's assignment. A finding is recorded per instance and each of
  those is assigned to another plan; editing the same file for an unassigned gap risks a merge
  collision with a concurrent run. Specifically excluded even though they are adjacent and tempting:
  `210/G1` (the phase-2-refine test that still pins the removed `git checkout --` recovery — same
  contract, different file, assigned elsewhere) and `290/G5` (`build-decision`'s `--audit-plan-id`
  alias being unreachable through the executor — the same stripping mechanism D4(a) cites, but a live
  CLI-surface bug rather than a false statement).
- **Any correction to `290-…/report-01.md`** — its § D0 paragraph carries both the claim D4(a)
  corrects *and* the `build-map` misattribution filed as `290/G4`, which is not assigned here. Two runs
  editing one paragraph is the collision this boundary prevents. D4 corrects the production docstring
  and the test comment only.
- **`auto_reconcilable`, the `baseline-reconcile` return-documentation block, and the phase-5-execute
  drift call site** — named in `310` G3/G5/G7/G8, none assigned here. D7(a) touches exactly one table
  row and adds no return block.
- **Running `.plan/execute-script.py`, or any marketplace script through it** — `.plan/` is
  git-ignored and **absent from this clone**. Do not go looking for it, and do not treat its absence as
  a finding. Every piece of evidence this plan needs is a git-tracked file; where a claim was
  originally established by execution, the plan names the tracked artifact that carries it instead.
- **Syncing the plugin cache** — a lane run neither performs `/sync-plugin-cache` nor records one as
  owed; the merged bundle source is authoritative. See `CLAUDE.md` § Standalone Plan Lane.
- **Broadening D6(a) into a general "every guard publishes its population" refactor** — the post-run
  source guard already publishes `considered_paths`/`exempted_paths`; only the layer-D capture is
  short. A generalisation would need a contract decision this run cannot make.

## Expected surface

Labelled `OBSERVED` below — every path was opened at HEAD while authoring. Re-derive line numbers; do
not trust any cited in this plan or in the gap documents.

- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — D1(a)(b), D5(a)(b)(c)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md` — D1(b), D5(c), D7(a)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md` — D3(a)
- `test/plan-marshall/workflow-integration-git/test_git_workflow.py` — D1(c), D5
- `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py` — D2, D3(b)
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — D3(c), D6(b)
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — D4(a)(c), D6(a), D7(b)
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_store.py` — D6(a)
- `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md` — D6(a)
- `test/plan-marshall/plan-marshall/test_invariants_behavior.py` — D4(a)(b)(c)
- one module under `test/plan-marshall/plan-marshall/` for D6(a)'s exempted-population test — **not
  named here**: derive it from the test tree (several handshake/invariants modules sit there) and name
  the one chosen in the run report
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/research-best-practices.md`,
  `.../persona-plan-marshall-agent/standards/agent-behavior-rules.md`,
  `.../phase-6-finalize/standards/finalize-step-simplify.md`,
  `.../extension-api/standards/ext-point-dynamic-level-executor.md`,
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-marketplace.md` — D6(b)
- `doc/plans/truthful-signals/310-baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges/report-01.md` — D7(c)

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `scan_artifacts` applies no unconditional plan-state exclusion; the `respect_gitignore` branch is the only thing excluding `.plan/**` at the scan root (140/G1) | OBSERVED | `git-workflow.py` — `scan_artifacts`, the `_split_ignored(get_gitignored_files(root) if respect_gitignore else set())` line and the per-file `_is_ignored` test |
| `TestDetectArtifactsLivePlanArtifacts::test_gitignored_worktree_contents_excluded_per_contract` exists and its fixture is a nested worktree (140/G2) | OBSERVED | `test/plan-marshall/workflow-integration-git/test_git_workflow.py` — the class and method |
| The mutation figures in 140/G2 (96 passed / 3 red / 4 failed-92-passed) were measured on another machine, not re-run here | HYPOTHESIS | Settled by D1's own red-first runs — re-run the mutation, do not carry the numbers |
| `_references_authority` is `'planning.md' in low and 'named recovery' in low` (210/G2) | OBSERVED | `test_named_recovery_marshal_config.py` — `_references_authority` |
| `test_named_recovery_never_instructs_unconditional_discard` asserts only over offenders matching a literal `Recovery:` prefix and an `always safe` phrase, never universally over `_is_inspection_first` (210/G3) | OBSERVED | same file — `_UNCONDITIONAL_DISCARD`, `_has_always_safety_claim`, and the test body |
| `worktree-handling.md` § "Recovery Loop" routes a dirty path to `git checkout --` labelled "(typical case)", and its § "Filter Rule" names `marshal.json` as a retained tracked `.plan/` file (210/G5) | OBSERVED | `workflow-integration-git/standards/worktree-handling.md` — § "Recovery Loop" step 2 and § "Filter Rule" |
| `_capture_config_hash`'s docstring still carries the refuted "does not accept / exited non-zero / never fired at all" clause, echoed as "exit 2 -> silent `None`" in the test comment (290/G1) | OBSERVED | `_invariants.py` — `_capture_config_hash` docstring; `test_invariants_behavior.py` — the `_capture_config_hash` section comment |
| The executor strips `--audit-plan-id` before the target parser runs, which is why the refuted clause is wrong | OBSERVED | `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — `extract_audit_plan_id` and the `--audit-plan-id … (stripped before passing to script)` help line (git-tracked; the generated `.plan/execute-script.py` is not in the clone) |
| No test exercises the `isinstance(config, dict)` guard in `_capture_config_hash` (asserted **absence**, 290/G2) | OBSERVED | `test_invariants_behavior.py` — the only `non_dict` symbol is `test_hash_dict_handles_non_dict_payload`, which tests `_hash_dict`; no `_capture_config_hash` test writes a non-dict `marshal.json` — they cover absent / unparseable / plan-section / phase-stability / genuine-change. **Counts here are leads — re-derive the test set from the file** |
| `_filter_main_dirty_paths` discards the exempted half, and no exempted-population column exists in `HANDSHAKE_FIELDS`/`HANDSHAKE_LIST_FIELDS` (asserted **absence**, 330/G3) | OBSERVED | `_invariants.py` — `_filter_main_dirty_paths` (`retained, _exempted = …; return retained`); `_handshake_store.py` — the field list and `HANDSHAKE_LIST_FIELDS`, which holds `main_dirty_files` alone |
| Five of the six dispatch-site files contain zero `[DISPATCH]` occurrences, and the two in `planning.md` belong to other sites (280/G3) | OBSERVED | `grep -c DISPATCH` over the six files; `grep -n resolve-target` over the same set. **A count — re-derive both at the moment of the change, via D0's P2** |
| `SKILL.md`'s `baseline-reconcile` row still names the captured `worktree_sha` and is the only such hit under `marketplace/` (310/G1) | OBSERVED | `grep -rn "captured .worktree_sha" marketplace/` — one hit, the `baseline-reconcile` row |
| `310-…/report-01.md` still carries `**PR:** _pending_` / `**Outcome:** _in progress_` and the "three `.py` files" count (310/G6) | OBSERVED | that report's header line and § Build gate paragraph |
| The `# SHIM(B):` block above `_REFERENCES_REQUIRED_KEYS` names a tolerance with no code branch (050/G7) | OBSERVED | `_invariants.py` — the marker block and the tuple `('base_branch', 'branch')` immediately below it |
| Whether a real tolerate-branch for a pre-retirement `references.json` exists elsewhere, onto which the marker could be moved | HYPOTHESIS | Settled inside D7(b) by reading `_capture_references_valid` and its callers; the deliverable branches on the answer and needs no decision from outside |
| The expected surface above is complete — no other file needs editing | HYPOTHESIS | Settled by the pre-PR verification pass: any file in the diff not listed above is collateral change and is named in the run report |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
The three absences above (no non-dict test, no exempted-population column, no unconditional plan-state
exclusion) were each confirmed by opening the file, not by inference — re-confirm each before building
against it.

## Verification

**Build gate.** This plan changes `.py` files under both `marketplace/` and `test/`, so the build gate
takes its full path. Run it as `cloud-plan-lane` specifies; do not hand-roll a narrower command.

**Targeted suites**, each run green at the end and each named in the run report:
`test/plan-marshall/workflow-integration-git/test_git_workflow.py`,
`test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py`,
`test/plan-marshall/plan-marshall/test_invariants_behavior.py`, plus whatever covers the handshake
store and `summarize-invariants` (derive that set from the test tree; do not guess a filename).

**Red-first evidence is a deliverable condition, not a nicety.** D1, D2, D3(b), D4(b) and D5 each name
a mutation. For each: apply it, record the failing test names and counts, revert it, confirm
`git status --porcelain` is clean, and re-run green. A deliverable whose test was never seen red is
**not** closed — report it as partial. This applies most sharply to D1(c) and D2, whose whole subject
is a guard that passes against the defect it names.

**Three independent cold reads.** Dispatch the pre-PR verification sub-agent (`cloud-plan-lane`
§ Step 6) and have it read each of the following **cold** — without this plan, without the gap
documents — and report *which reading it took*, in its own words, before any comparison to intent:

1. The rewritten `workflow-integration-git/SKILL.md` detect-artifacts paragraph (D1(b)). Ask: *if a
   plan runs `detect-artifacts` against its own worktree with `--no-gitignore`, can the plan's own
   `logs/work.log` appear in `safe`?* The answer must be an unambiguous **no**, attributed to the
   unconditional exclusion — not to `.gitignore`, and not hedged.
2. The rewritten `worktree-handling.md` § "Recovery Loop" (D3(a)). Ask: *`newly_dirty[]` contains
   `.plan/marshal.json`. What does the document tell me to do first, and may I revert it without
   asking anyone?* The reading must be **inspect the diff first**, and **no** — a revert requires an
   explicit operator disposition for that path. A reading of "revert is the normal case" means the
   wording failed however complete it looks, and the text is rewritten before the PR opens.
3. The two `--no-gitignore` descriptions (D5(c)). Ask: *what does this flag include that the default
   excludes, and what stays excluded either way?* The reading must name the nested repository/worktree
   skip as unaffected by the flag.

Each cold read's verbatim answer goes in the run report. A failed cold read is a defect in this run's
output, not an observation about the reader.

**Read-only checks** (no execution settles these): that D3(c)'s citations resolve to blocks which
actually state the prohibition for the phase named; that D6(a)'s new column appears in *both* the
`phase-handshake.md` invariant table and its TOON field-order header; and that D7(c) **appended** a
correction to the report's sweep clause rather than deleting the original claim.

## Notes

- **Scope.** This plan closes 17 gaps drawn from seven source plan directories under
  `doc/plans/truthful-signals/`. Each gap's full entry — Kind, Severity, Where, What is wrong, Why it
  matters, Fix, Done when, and the adversarial-review record — is git-tracked in that directory's
  `gaps.md`; those are the authoritative briefs and this plan does not restate their reproduction
  detail. The map: D1 → `140/G1`, `140/G2`; D2 → `210/G2`, `210/G3`; D3 → `210/G5`, `210/G4`;
  D4 → `290/G1`, `290/G2`, `290/G3`; D5 → `140/G5`, `140/G3`, `140/G4`; D6 → `330/G3`, `280/G3`;
  D7 → `310/G1`, `050/G7`, `310/G6`. D0 closes no gap by design — it is the derive-or-halt gate for
  D2, D3 and D6.
- **All 17 were re-grounded at HEAD while this plan was authored** — every cited file and symbol was
  opened and the defect confirmed present. None was dropped as already-closed. The gap documents'
  **line numbers are stale by construction** (280/G3's own record shows all six drifting once
  already); treat every `file:line` in this plan and in those documents as a lead and re-locate by
  symbol or by text.
- **Where a gap's Fix offered two directions**, this plan picks one and states it, so the run never
  faces a choice it cannot resolve: 140/G2 takes direction (i) (add the reaching test), never the
  deletion; 210/G2 takes the disposition-enumeration test, never a line-length budget; 210/G5 takes
  widening `_derive_named_recovery_regions`, with the sibling-assertion fallback stated as a
  mechanical condition on the heading shape, not as a judgement; 330/G3 takes the constructive
  "capture the exempted set" branch, never the "document why it is not recorded" branch, which would
  need a decision. 050/G7's branch (move the marker vs. delete it) is settled by a fact the run can
  read, and both outcomes are acceptable.
- **Cohesion.** Two of the three clusters — the detect-artifacts scanner (D1, D5) and the
  named-recovery prose (D2, D3) — are the plan's centre of gravity. D4, D6 and D7 are the residue: they
  share the epic's mechanism (a confident statement that the code does not support) and, for D4/D6(a)/D7(b),
  the same file, `_invariants.py`. They do not share a mechanism with the first two clusters, and a run
  that ships D0–D4 and reports D5–D7 as not-started is a good partial outcome, not a failure.
- **Sequencing.** D1 and D5 both edit `scan_artifacts` / `get_gitignored_files` in the same file; land
  D1 first — its unconditional exclusion is what makes the `.plan/` case independent of D5's return
  contract, and doing it the other way leaves the high-severity gap open behind a medium one. D2 must
  land before D3(b), which extends the population D2's universal assertion runs over.
- **Concurrency.** Other plans in this epic are assigned the sibling gaps in the same source
  directories. `workflow-integration-git/SKILL.md`, `_invariants.py` and
  `test_named_recovery_marshal_config.py` are the likely contention points. The Out of scope section
  is what keeps this run out of their edits; hold that line rather than fixing an adjacent defect
  noticed in passing — record it in the run report instead.
