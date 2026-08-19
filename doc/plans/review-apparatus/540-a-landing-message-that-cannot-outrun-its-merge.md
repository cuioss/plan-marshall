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

# Finalize asserts at completion only what it positively read

**Epic:** review-apparatus
**Branch prefix:** fix — bug fix

## Problem

When a finalize run reaches its end, three artefacts assert something about the work: the `kind: landing`
message written to the epic inbox, the pre-archive foreign-PR gate's `clear` verdict, and the pull-request
body a reviewer reads. Today all three can assert more than the run established. A run that never merged
still files a landing that says it shipped. A gate that never saw a classification still reports the
population clean. A PR body composed against one diff still describes that diff after the PR has grown a
different one. In each case the artefact's shape is well-formed and its content is unsubstantiated, which
is the failure mode this epic exists to close: a signal that asserts more than it establishes.

**The mechanism, for the landing — read, not inferred.**
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` (the merge gate,
frontmatter `order: 70`) closes with six `mark-step-done` call sites, labelled **Branches A through F**
at line 1696, and **every one of them records `--outcome done`** (lines 1720, 1751, 1760, 1769, 1782,
1796). Only Branches A and E record the `merge_mechanism` fact, which the same document says at line 1702
is recorded *iff* "the merge actually **landed** and was corroborated". Three of the remaining four are
non-merging by their own text: **Branch C** — "declined by user … Nothing was rebased, merged, or cleaned
up" (`:1756`); **Branch D** — "no PR found … exits before the rebase and before any merge" (`:1765`);
**Branch F** — "enqueued, merge not yet landed … It records **no `merge_mechanism`**, because no merge
landed" (`:1790-1792`). (The fourth, Branch B, is local-only mode, where `pr` and `merge_state` are `n/a`
by design.)

Nothing halts the pipeline on a terminal `done`. The dispatcher's only per-outcome branch is the
resumable re-entry check — "IF outcome == "done": SKIP this step (continue to next iteration)"
(`phase-6-finalize/SKILL.md:720`) — a skip of one step, never a stop; and the prohibition that closes the
set is "Never skip a step in the manifest list based on PR state, CI state, or earlier step outcomes. The
ONLY valid skip condition is the resumable re-entry check" (`SKILL.md:37`). The loop therefore runs on to
`default:emit-landing` at `order: 1000`, whose own document states "the emission is unconditional when the
step runs" (`standards/emit-landing.md:48`) and whose only worked headline is
`{plan_id} shipped as {pr} ({merge_state}).` (`emit-landing.md:175`). Its sole skip is the Step 0
non-orchestrated guard; there is no merge-state gate anywhere in it. `branch-cleanup.md:1068` already
names the consequence in its own words: settling a blocked path with a terminal `done` "lets the FOR loop
continue through to `archive-plan` — archiving the plan with the PR unmerged, the worktree unremoved, and
the branch undeleted." **A landing is asserted for a run that did not merge, and the plan is archived
behind it.**

The same shape recurs in the other two artefacts. The pre-archive gate
(`phase-6-finalize/scripts/foreign_pr_gate.py`) selects its population with bare truthiness tests on
`entry.get('foreign')` (`_foreign_paths_by_deliverable`, `:186-220`) and returns `status: clear` when that
population is empty (`:280-288`) — so a deliverable listing carrying **no `foreign` key at all**, which is
exactly what the fail-open classifier `_annotate_foreign`
(`manage-solution-outline/scripts/manage-solution-outline.py:505-547`) produces when it cannot resolve the
project root, is the same bytes on the wire as a genuinely host-only population. Both clear, against the
gate's own stated posture: "The gate CLEARS only when it has POSITIVELY read a landing state … never on an
absence of evidence" (`foreign_pr_gate.py:50-52`). And the PR body's file references are bound to a diff
resolved once at `order: 20` (`workflow/create-pr.md:100-108`), while `create-pr` declares no
`head_dependent:` and its existing-PR branch reads "Skip creation; reuse the returned `pr_number`"
(`:71`) — so after a loop-back the body describes a narrower diff than the PR carries, with nothing in the
rendered body naming the HEAD it was composed against.

## Goal

Every claim finalize emits at completion is traceable to something the run positively read. A landing
message asserts a landing only when a merge was substantiated, and says plainly what happened when it was
not; the landing's fact block is validated at the value level, carries the commit its claim is about, and
exists exactly once per plan; the foreign-PR gate clears only against a population it can prove was
classified, judged on the branch the foreign change is actually on; and the PR body and the review
retrospective each name the tree they describe. Where settling a question would change the lifecycle
itself, this plan records a proposal rather than deciding.

## Deliverables

Seven entries: one gating derivation (D0), five substantive changes (D1–D5), and one proposal record
(D6). Each names the gap ids it discharges, so nothing is silently dropped. The detailed evidence for
every gap id lives in the two git-tracked audit files named under Notes; this plan restates everything the
run needs, so those files are corroboration, never required reading.

1. **D0 — Derive the completion surface from the tree, or halt** *(gating; discharges 080-G10)*
   Before any other deliverable, derive and record three things, each from a git-tracked source:
   (a) **the terminal-branch set** — every `mark-step-done … --outcome done` call site in
   `phase-6-finalize/standards/branch-cleanup.md`, with its branch letter, its `work_performed` value,
   and whether it records `merge_mechanism`. The plan observed **six** call sites, of which **three**
   (C, D, F) are non-merging and one (B) is local-only — ⚠ **re-derive both counts by reading the
   document; do not trust these numbers**, the tree may have moved since authoring.
   (b) **the step order and head-dependence** of `create-pr`, `branch-cleanup`, `emit-landing` and
   `archive-plan`, read from each document's own frontmatter (`order:`, `head_dependent:`). The plan
   observed `20`, `70`, `1000`, `1100`, with `head_dependent:` declared by **none** of them — ⚠ re-derive.
   (c) **the registered finalize-step key set**, parsed from the dispatch table in
   `phase-6-finalize/SKILL.md`, and each key's classification in
   `phase-6-finalize/standards/dispatch-inline-split.md`, whose line 9 states the closure invariant:
   every registered step "carries **exactly one** classification: it appears in either the dispatched
   roster or the inline roster, never both and never neither".
   **HALT and report the run blocked if (a) or (c) cannot be derived from git-tracked files.** Do not
   hand-maintain either list as a fallback — a hand-maintained population is the defect class this plan
   closes, and reproducing it inside the fix would defeat the fix.
   Then discharge **080-G10** with the derived set: add `default:emit-landing` to exactly one roster in
   `dispatch-inline-split.md` (it is registered at `SKILL.md:178` and described there as inline, and a
   search of the roster document for `emit-landing` returns nothing), and change
   `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py::_registered_steps` so its
   population comes from the same git-tracked source D0 used rather than from the `marshal.json`
   snapshot alone — the snapshot is tracked but **stale**, holding 25 steps and not `emit-landing`, so
   the invariant meant to catch an unclassified step is currently blind to the one this plan is about.
   *Done when:* the run report carries the three derived tables; `emit-landing` appears in exactly one
   roster; and `test_dispatch_roster_closure.py` fails when a registered step is unclassified, proven by
   temporarily removing one roster row and observing red before restoring it.

2. **D1 — The landing's claim is gated on a substantiated merge** *(discharges 080-G1 (blocker),
   080-G2, 080-G5 (documentation half), 080-G11)*
   In `phase-6-finalize/standards/emit-landing.md`: its Step 1 already derives `pr` and `merge_state`
   from the `create-pr` and `branch-cleanup` step records, so the substantiation read has a hook. Add a
   merge-substantiation arm to it — when `branch-cleanup`'s recorded facts carry `merge_mechanism`, emit
   the landing-asserting message; when they do not, emit a **distinct, explicitly non-landing message
   shape** naming what the run did instead (declined / no PR / enqueued-not-landed).
   ⛔ **Do not implement this as a step skip.** `SKILL.md:37` bars skipping a step on earlier step
   outcomes, so the "emit nothing" arm is closed by the dispatcher contract; the remedy changes *what is
   emitted*, never *whether the step runs*. State in the document the failure mode of the arm not
   chosen, so a later reader cannot re-open the question by guessing.
   Replace the single worked headline at `:175` — `{plan_id} shipped as {pr} ({merge_state}).` — with a
   merge-state-conditioned pair or table: a landing-asserting form usable only on a substantiated merge,
   and a non-landing form for every other state **including the local-only `n/a` case**, which today
   renders as `shipped as n/a (n/a)`. Appending a correct outcome field beside a false sentence leaves
   the false sentence there; the claim itself must change.
   In `branch-cleanup.md`, correct the Branch F closing sentence at `:1801` — "Re-entering finalize once
   the queue merge lands takes the `state == merged` path, which performs the deferred local cleanup" —
   which the same document contradicts at `:1068` ("an already-`done` `branch-cleanup` is SKIPPED by the
   resumable re-entry check"). This deliverable makes the **document truthful** about what happens
   today; changing the mechanism is D6's proposal, because it alters dispatcher control flow.
   In `phase-6-finalize/SKILL.md:533`, replace the citation of `failed_outcome_strategy` — a repo-wide
   search finds that identifier in no skill document, script, schema or test, only in this line and in
   the audit files — with the mechanism that actually governs a `failed` outcome (the resumable-re-entry
   retry at `:721` and the continue-to-next-step behaviour at `:1057` / `:592`).
   *Done when:* a test fails against the current unconditional emission and passes against the new one,
   asserting that a run whose `branch-cleanup` facts carry no `merge_mechanism` produces a message whose
   payload **and** prose assert no landing; `emit-landing.md` contains no unconditional
   landing-asserting headline template and carries a worked example for the non-merged case; and no
   sentence in `branch-cleanup.md` claims a re-entry the re-entry check suppresses.

3. **D2 — The landing's facts are validated at the value level, carry their commit, and exist once per
   plan** *(discharges 080-G3, 080-G6, 080-G9)*
   In `plan-orchestrator/scripts/_orchestrator_inbox.py`:
   — `cmd_inbox_write` (`:890-982`) validates slug, sender id, sender type, kind, epic existence,
   target-plan deliverability and payload non-emptiness, and never checks for an existing landing from
   the same sender; `allocate_message_path` (`:721-749`) simply takes the next free sequence. Refuse a
   second `kind: landing` from the same `sender_id` at the write boundary with a **named error**. Prefer
   this over an automatic supersession link (`cmd_inbox_supersede` exists as a manual verb): a
   supersession marker leaves the drain reconciling a sequence, which the single-landing invariant exists
   to avoid. The invariant every source states today is scoped per *run*
   (`emit-landing.md:201`, `plan-orchestrator/standards/inbox-envelope.md:97`); restate it per *plan*
   wherever it appears.
   — `check_landing_completeness` (`:859-887`) tests presence and non-emptiness only
   (`missing = [key for key in LANDING_REQUIRED_KEYS if not facts.get(key)]`), while the producer's Error
   Handling table instructs writing a failed fact read as `n/a` (`emit-landing.md:235`) — a non-empty
   value, so every degraded field passes. Add a value-level arm: report a `degraded_keys` list beside
   `missing_keys` and refuse `complete: true` for an all-`n/a` block, and validate `merge_state` against
   the vocabulary the spec declares — `merged` / `open` / `n/a`
   (`plan-orchestrator/standards/landing-payload-spec.md:84`) — which nothing validates today.
   — Add a merge-commit SHA key to `LANDING_REQUIRED_KEYS` (**eight** keys today — ⚠ re-derive by
   reading `:811-820`), to the payload spec's mechanisable table and to the producer's fact assembly,
   sourced from the merge the `branch-cleanup` facts substantiate. A case-insensitive search for `sha`
   over `emit-landing.md` and `landing-payload-spec.md` returns only incidental substring matches, so no
   commit field exists in either today. Record explicitly in `landing-payload-spec.md` whether the two
   remaining unpicked-up fields — cost against the anchor, and what was deliberately left unchanged —
   become optional keys or stay residue prose.
   — Give the shared-source test a real assertion: `test/plan-marshall/plan-orchestrator/`
   `test_landing_completeness.py:137-141` asserts three membership facts about `LANDING_REQUIRED_KEYS`
   and never reads the producer. Parse `emit-landing.md`'s required-key list and compare it against the
   constant.
   *Done when:* a second landing write from the same sender is refused with a named error; an all-`n/a`
   landing is not reported `complete: true` and an out-of-vocabulary `merge_state` is named as a defect;
   a landing emitted for a merged PR carries the merged commit SHA and the completeness check reports it
   missing when absent; and the shared-source test fails when producer and validator diverge.

4. **D3 — The PR body and the retrospective name the tree they describe, and a reader failure is not an
   absence** *(discharges 080-G4, 080-G7, 080-G8)*
   — `phase-6-finalize/scripts/pr_intent_section.py::_run_outline_read` returns `{}` on `OSError`
   (`:115-116`), on a non-zero exit (`:117-118`) and on an unparseable envelope (`:121-122`);
   `has_outline_intent` then returns `False` and `cmd_render` prints `omitted: True` with
   `reason: 'no outline intent: …'` and exits 0. The conflation is restated at the consuming site —
   `workflow/create-pr.md:169-172` tells the agent `omitted: true` means the plan has no outline intent
   and "This is a normal outcome for outline-less plans, not a failure" — and the decision-log line
   interpolates the script's reason, so a reader failure is logged **as** the absence claim. Distinguish
   the three degradations: return an error status (or an `omitted: true` carrying a distinct
   `reason: outline_unreadable`) when the reader raises `OSError`, exits non-zero, or returns an
   unparseable envelope, and reserve the absence reason for a reader that succeeded and reported empty
   or not-found sections. Route the new reason in `create-pr.md`'s branch table to a failure disposition.
   Only the non-success-status path is exercised today
   (`test/plan-marshall/phase-6-finalize/test_pr_intent_section.py:67-68`, through a stand-in that
   always carries `returncode=0` and parseable output); cover the other three.
   — Add an **as-of line to the composed PR body** naming the HEAD its diff scope
   (`git diff --name-only origin/{base_branch}...HEAD`, `create-pr.md:100-108`) was resolved against.
   ⚠ **Take the stamp arm, not the regeneration arm**: recomposing on every loop-back re-spends the
   Intent distillation each time, while the stamp costs one line; and the alternative would require
   declaring `create-pr` `head_dependent: true` plus a body-recompose path through the existing-PR
   branch, which is a larger change to a step that runs on every plan. Record the choice and the arm not
   taken in the body of `create-pr.md`.
   — In `.claude/skills/finalize-step-review-retrospective/SKILL.md`, Step 4 (`:388-425`) enumerates
   everything the artifact must contain and never the step's own resolved HEAD, which goes only to
   `mark-step-done --head-at-completion {sha}` in Step 5 — yet `:94` claims "the artifact this step
   persists is a verdict about a specific tree, and the stamp is what ties it to that tree for anyone
   reading the retrospective later." Add the resolved SHA to the artifact body as an unconditional
   as-of line, alongside the `gate_head_sha` / `reviewed_head_sha` the delta section already carries,
   and correct the `:94` claim to name where the stamp actually lands.
   *Done when:* a reader failure produces an outcome distinguishable from a genuinely intent-less plan,
   pinned by a test, and no document describes a reader failure as normal; the composed PR body states
   the HEAD its diff scope was resolved against; and the composed `review-retrospective.md` carries the
   HEAD it describes regardless of which optional sections are present.

5. **D4 — The foreign-PR gate clears only against a population it can prove was classified, judged on
   the right branch** *(discharges 020-G1, 020-G2, 020-G3, 020-G7, 020-G9, 020-G15, 020-G16)*
   — **Positive classification (020-G1).** `manage-solution-outline list-deliverables` publishes whether
   classification was performed — a top-level `foreign_classification: resolved|unresolved` plus the
   `project_root` it used — and `foreign_pr_gate.check` requires it: `status: error` when the field is
   absent or `unresolved`, and `status: error` when a deliverable record carries no `foreign` key at all.
   The `clear` path asserts it saw a positively-classified population. Keep the column itself advisory
   and fail-open in `_annotate_foreign`; move the certainty into the published status the gate reads.
   — **The branch the change is on (020-G2).** `_resolve_landing_state` (`:147-164`) builds
   `[… 'pr', 'landing-state']` with no `--branch`, so `_resolve_landing_branch`
   (`workflow-integration-github/scripts/_github_pr.py:664-685`) falls back to
   `git rev-parse --abbrev-ref HEAD` **in the foreign checkout** — classifying whatever ref that tree
   happens to have out. Pass `--branch` on every invocation, fail closed with a named reason when the
   branch cannot be determined rather than silently classifying HEAD, and echo the returned `branch`
   into each `repos[]` row so the verdict names its subject.
   — **The blocking set (020-G3).** `BLOCKING_LANDING_STATE = 'pushed_no_pr'` (`:78`) refuses on exactly
   one state, and `test_foreign_pr_gate.py::test_unpushed_foreign_deliverable_clears` pins that
   `unpushed` clears. **This plan decides: widen the refusal to a named set containing both
   `pushed_no_pr` and `unpushed`**, renaming the constant accordingly. The reason is the gate's own
   purpose as `archive-plan.md:38` states it — a foreign change must not archive while it has no pull
   request — and a change on no remote at all certainly has none; `unpushed` is the strictly worse case
   passing the gate that the stricter case fails. The arm not taken (keep `unpushed` clearing) fails by
   letting a locally-committed, never-pushed foreign change archive cleanly, one step earlier in the
   lifecycle than the case the gate was built for; state that in the gate docstring. Update the
   docstring, `archive-plan.md` and the tests together, and assert the disposition **against the
   constant** rather than against a literal.
   — **One base for a relative path (020-G7).** `_plan_parsing.py:95` joins a relative candidate onto
   `project_root`; `foreign_pr_gate._resolve_repo_root` (`:123-144`) computes
   `os.path.dirname(path)` and calls `os.path.isdir` with no anchoring, i.e. against the gate process's
   cwd. Anchor `_resolve_repo_root` on the `project_root` the gate already resolves at `:261` (and today
   never uses for classification), and give `list-deliverables` an explicit project-root argument the
   gate passes, so the two agree by construction rather than by cwd inheritance.
   — **What `unpushed` is evidence of (020-G9).** `_branch_pushed_state`
   (`_github_pr.py:706-723`) derives the whole pushed/unpushed axis from
   `git branch -r --contains <branch>` and its docstring asserts `rc == 0` with empty output "proves it
   is not" on a remote — a statement about local remote-tracking refs, not about the remote; a search of
   `_github_pr.py` finds no `fetch` or `ls-remote` anywhere in the landing-state path. Either refresh the
   ref the verdict rests on before deciding, or state in the docstring **and** in
   `tools-integration-ci/standards/leaf-command-reference.md` that `unpushed` means "not on a known
   remote-tracking ref", and pin whichever is chosen with a test.
   — **The ordering comment (020-G15).** `tools-integration-ci/scripts/ci_base.py:814` says the tuple is
   "in refuse-most-first precedence order" above
   `LANDING_STATES = ('merged', 'pr_open', 'pushed_no_pr', 'unpushed')`, which is ordered landed-first to
   match `derive_landing_state`'s check order. Reword the comment to describe the actual ordering.
   — **One record shape (020-G16).** `_annotate_foreign` is called from exactly one site
   (`manage-solution-outline.py:495`, `cmd_list_deliverables`), so `_lookup_deliverable` — which backs
   both `read --deliverable-number` and `get-deliverable`, two verbs `SKILL.md:175` says return
   byte-identical output — returns an unannotated record. Call `_annotate_foreign` from that path too,
   update the `SKILL.md` worked example to show `affected_files` entries as `{path, intent, foreign}`
   plus the deliverable roll-up, and add a short section describing what `foreign` means and who consumes
   it: a search for `foreign` across that skill's `SKILL.md` and `standards/` returns nothing today.
   *Done when:* a gate test whose loader returns success-shaped deliverables with no `foreign` key
   yields `status: error`, and one whose loader reports an unresolved classification yields
   `status: error`; a test drives the real `_resolve_landing_state` and asserts `--branch` in the argv,
   and each `repos[]` row carries the branch it classified; one named constant holds the blocking set and
   docstring, `archive-plan.md` and tests all assert against it; a gate test with a `../`-relative foreign
   path and a cwd that is not the checkout root resolves the same root as the classifier; the
   pushed/unpushed contract is pinned by a test; and a test asserts `read --deliverable-number N` and
   `list-deliverables` return the same keys for the same deliverable.

6. **D5 — The gate is proven where it bites, and its off-normal paths keep its contract's shape**
   *(discharges 020-G5, 020-G6, 020-G8, 020-G10, 020-G11, 020-G14)*
   — **Enforcement (020-G6).** A repo-wide search for `foreign_pr_gate` returns the prose invocation in
   `phase-6-finalize/standards/archive-plan.md:42-45`, the module's own docstring, the executor
   registration, and two test files — **no code path calls the gate**, and the only refusal assertion
   tests `check()` directly. Deleting the entire "Pre-Archive Foreign-PR Landing Gate" section therefore
   breaks no test. (⚠ Prose-only invocation is the house convention for this skill's scripts, not an
   anomaly — the missing thing is the proof, not a different call style.) Add an enforcement test at the
   archive boundary: a document-contract test asserting `archive-plan.md` carries the gate invocation and
   the `blocked` / `error` STOP handling **ahead of** the archive call.
   — **Where `done` is decided (020-G5).** The landed report
   `doc/plans/review-apparatus/020-a-foreign-task-reports-done-with-no-pr-anywhere/report-01.md` § D0
   records "`done` is written in exactly one place: `manage-tasks/scripts/_tasks_crud.py::cmd_update`".
   That is false at HEAD: `manage-tasks/scripts/_cmd_step.py:73` reads
   `task['status'] = 'failed' if has_failed else 'done'` inside the `all_terminal` branch of the
   `manage-tasks step` verb — the path the phase-5 task runner drives. Correct the finding in place:
   name both writers, identify which the runner uses, and restate the single-seam claim-label verdict as
   "two seams, both locatable". This belongs here because it is the same question the enforcement test
   asks — where the archive/`done` boundary actually is — and any later plan that moves enforcement to
   "the" completion seam would otherwise miss one.
   — **Timeouts and contract shape (020-G8).** `foreign_pr_gate.py:135-140` runs
   `git rev-parse --show-toplevel` with no `timeout`, against `timeout=120` on the two executor calls at
   `:107` and `:165`; the plugin-script standard
   (`pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md:266`)
   states `timeout=N` is always recommended for external calls. Worse, all three `subprocess.run` calls
   sit outside the `try` blocks that guard `parse_toon`, so `subprocess.TimeoutExpired` propagates out of
   `check()` and `cmd_check` uncaught — exiting on a traceback with no TOON on stdout, while
   `archive-plan.md:51` instructs the dispatcher to return the error TOON verbatim. Pass an explicit
   timeout to all three, and catch `TimeoutExpired` at every seam, returning the module's
   `{'status': 'error', 'error': …}` shape naming the command that timed out.
   — **Provider parity (020-G10).** `pr landing-state` is registered on the github provider only
   (`workflow-integration-github/scripts/github_ops.py:1834-1868`); a search for `landing` across
   `workflow-integration-gitlab/` finds only an unrelated "landing poll" docstring line. The constraint
   is stated only in `leaf-command-reference.md` ("**GitHub provider only.**"), and the gate has no
   provider check. Have the gate detect the configured provider and return `status: error` with an
   explicit `landing_state_unsupported_on_provider` code naming the provider and the remedy, rather than
   surfacing an argparse rejection verbatim.
   — **Seam tests (020-G11).** Every existing gate test injects all three seams
   (`test_foreign_pr_gate.py:38-63`), so the argv the gate actually builds, the TOON parse paths, the
   empty-stdout branches and the `git rev-parse` handling are exercised by nothing. Add tests that call
   each seam with `subprocess.run` monkeypatched, asserting the full argv (including `--project-dir` and
   the `--branch` D4 adds), the empty-stdout error shape, and the unparseable-TOON error shape.
   — **Two kinds of unresolved row (020-G14).** The field comment at `foreign_pr_gate.py:30` documents
   `unresolved[K]{path,reason}` as "foreign paths whose repo could not be resolved", but its two writers
   append different things: `:300` appends a declared **file path**, `:324` appends a resolved
   **repository root**. Add a `kind` discriminator (`declared_path` / `repo_root`) or split into two
   named lists, and correct the docstring and `archive-plan.md:51`'s "resolve every `unresolved[]` item"
   instruction to match.
   *Done when:* a test fails if the gate section is removed from `archive-plan.md` or if the archive path
   stops honouring a `blocked` verdict; `report-01.md` § D0 names both `done` writers with the verdict
   restated; every `subprocess.run` in the gate passes a timeout and a patched `TimeoutExpired` yields a
   TOON `status: error` with exit code 1 rather than a traceback; a non-github provider yields the named
   error code; each of the three seam functions is entered by at least one test and one asserts the full
   argv; and each `unresolved[]` row states which kind of path it carries, with a test producing one of
   each.

7. **D6 — Record the open lifecycle choices as proposals, and give the foreign column a consumer**
   *(discharges 020-G4, 020-G17, 080-G5 (mechanism half))*
   Two questions this plan surfaces cannot be settled by a run with no operator, because settling either
   changes lifecycle behaviour for every plan rather than fixing a stated defect. Record each as a
   **proposal for the operator**, in a git-tracked location the epic will read — a
   `## Proposals` section of this plan's run report, plus a pointer from the affected document — and
   **change no behaviour for either**:
   — **(020-G4) The gate's blocking population: declared surface, or write set?**
   `_foreign_paths_by_deliverable` (`:205`) and `_annotate_foreign` both read `entry.get('foreign')`
   alone and never `entry['intent']`, although `_extract_affected_files` returns `{'path', 'intent'}` and
   `_plan_parsing.py:456`'s `deliverable_write_set` states the repository's own rule: every entry "whose
   declared intent is not `STEP_INTENT_READ`". So a foreign path declared `(read)` — a file consulted in
   another repository and left untouched — enters the population and can refuse an archive for a
   repository the plan never wrote to. Two landed commits pull opposite ways: `deliverable_write_set`
   post-dates the gate, and `survey_scope` was added to the field list **deliberately**, with a test
   asserting "the population this gate iterates must be the whole declared surface". The proposal states
   both options and their failure modes (narrow it: a genuine foreign write declared only in
   `survey_scope` escapes the gate; keep it: read-only foreign paths block archives). ⚠ Note that the
   pinning test's fixtures carry no `intent` key, so an intent filter would leave it green while changing
   real behaviour — so **do** add intent-bearing fixtures to that test now, under whichever disposition
   is current, since that is a strict improvement either way.
   — **(080-G5) What outcome Branch F records.** `branch-cleanup.md:1801` names a re-entry recovery that
   `:1068` says the step's own terminal `done` suppresses. D1 makes the document truthful; the mechanism
   choice — record `loop_back` or `failed` as `:1068` prescribes for a structurally-blocked path, declare
   `branch-cleanup` `head_dependent: true` so the re-entry comparison can re-arm it, or accept that
   Branch F's cleanup is deferred to an operator action — changes the dispatcher's control flow on every
   finalize run and is not this run's to take. The proposal states all three with the cost of each.
   — **(020-G17) One consumer for the column.** The `foreign` column exists and exactly one site reads
   it: searches for `foreign` across `manage-metrics/`, `plan-retrospective/` and
   `manage-execution-manifest/` return nothing, so every coverage ratio still pools host paths with
   foreign ones — the standalone second reason the column was built for. Give at least one emitted
   coverage figure a host/foreign split (or a documented exclusion stated in the payload), starting from
   `manage-metrics`' `files_modified` denominator and the retrospective's declared-surface recall check.
   *Done when:* the run report carries a `## Proposals` section naming both open choices, each with its
   options and their failure modes, and asserting that no behaviour was changed for either; the
   survey-scope pinning test carries intent-bearing fixtures; and at least one emitted coverage figure
   carries a host/foreign split or a documented exclusion, asserted by a test against a fixture
   containing both populations.

## Out of scope

Each entry names why it is excluded — with no operator watching, the written reason is the only thing
that holds the line against a tempting adjacent change mid-run.

- **Changing the orchestrator drain's per-kind routing** (`plan-orchestrator/workflow/analyze.md`, which
  routes every `kind: landing` to the full-ship branch). Excluded because the fix belongs at the
  producer: teaching the consumer to second-guess a message would leave the false claim on the wire and
  weaken the corroboration duty the drain already carries. Changing the drain contract is also a change
  to a governing contract this run may not self-approve.
- **Making `archive-plan` refuse on the host PR's unmerged state.** Excluded because it changes the
  terminal condition of the plan lifecycle — an operator-visible policy change, not a defect fix — and
  the same run that would need it is the one that cannot ask. D6 records the adjacent Branch F question
  as a proposal instead.
- **Implementing `pr landing-state` on the GitLab provider.** Excluded because provider parity is a
  separate implementation with no GitLab substrate to test against in this repository; D5 delivers the
  named, actionable error in its place so a GitLab user is not handed an argparse rejection.
- **Documenting `pr landing-state` on the `tools-integration-ci` canonical surfaces, and extending the
  doc-parity test from `checks` verbs to `pr` verbs** (020-G12, 020-G13). Excluded because neither
  changes a verdict or an emitted claim, and bundling a `tools-integration-ci` documentation sweep onto
  the critical path of a blocker fix delays the blocker for no gain in correctness.
- **The owed API-Sheriff re-review** (020-G18). Excluded because it is an owed *check* about
  language-specific reviewer packs, not about what finalize asserts at completion; it belongs beside the
  reviewer pack in `automatic-review/standards/`, where the plan that owns that pack can close it.
- **Reconciling the two test-count figures in the 020 run report** (020-G19). Excluded because it is
  report hygiene on a landed record with no runtime behaviour behind it; this plan already reopens that
  report for the substantive D0 correction in D5, and mixing a cosmetic edit into that correction makes
  the correction harder to review.
- **Rewriting `branch-cleanup`'s merge-gate control flow**, beyond making its text truthful. Excluded for
  the reason D6 states: the choice changes dispatcher behaviour for every finalize run and is recorded,
  not taken.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` — the landing's
  claim, its headline forms, and its required-key list (D1, D2)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the Branch F
  re-entry sentence (D1); read by D0 to derive the terminal-branch set
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the
  `failed_outcome_strategy` citation (D1); read by D0 for the registered step set
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md` — the
  roster `emit-landing` is missing from (D0)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md` — the gate's
  blocking-set text and the `unresolved[]` instruction (D4, D5)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py` — population
  selection, branch passing, blocking set, root anchoring, timeouts, provider check, row discriminator
  (D4, D5)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py` and
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md` — reader-failure
  distinction and the PR body's as-of line (D3)
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — landing
  uniqueness, value-level completeness, the SHA key (D2)
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` and
  `.../standards/inbox-envelope.md` — the payload contract and the per-plan invariant (D2)
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`
  and that skill's `SKILL.md` — the published classification status and the single record shape (D4)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` and
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` — the
  pushed/unpushed contract and the `LANDING_STATES` comment (D4)
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md` —
  the `unpushed` contract wording, if that arm is chosen (D4)
- `marketplace/bundles/plan-marshall/skills/manage-metrics/` — the coverage figure that gains a
  host/foreign split (D6)
- `.claude/skills/finalize-step-review-retrospective/SKILL.md` — the artifact's as-of line and the
  line-94 claim (D3)
- `test/plan-marshall/phase-6-finalize/` (`test_foreign_pr_gate.py`, `test_pr_intent_section.py`,
  `test_dispatch_roster_closure.py`), `test/plan-marshall/plan-orchestrator/`
  (`test_landing_completeness.py`, inbox channel tests),
  `test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py` — the pinning tests
- `doc/plans/review-apparatus/020-a-foreign-task-reports-done-with-no-pr-anywhere/report-01.md` — the D0
  single-seam correction (D5)

## Claim labels

Every premise below was settled by reading the named file at the head of this branch unless labelled
otherwise. An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk
half — an unverified absence sends the run to build something that already exists.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| All six `branch-cleanup` terminal call sites record `--outcome done`; Branches C, D and F are non-merging and record no `merge_mechanism` | OBSERVED | `phase-6-finalize/standards/branch-cleanup.md:1696-1802` (the six fenced `mark-step-done` blocks and the fact table at `:1698-1703`) |
| Nothing in the dispatcher halts the step loop on a terminal `done`; the only skip is the re-entry check | OBSERVED | `phase-6-finalize/SKILL.md:37`, `:716-726` |
| `emit-landing` runs at `order: 1000` and emits unconditionally, with no merge-state gate | OBSERVED | `phase-6-finalize/standards/emit-landing.md` frontmatter `order: 1000`, `:48`, `:201` |
| The only worked landing headline asserts a ship: `{plan_id} shipped as {pr} ({merge_state}).` | OBSERVED | `emit-landing.md:175` |
| `branch-cleanup.md` itself states that a terminal `done` on a non-merging path lets the loop archive an unmerged PR | OBSERVED | `branch-cleanup.md:1068` |
| **Absence:** `failed_outcome_strategy` has no definition anywhere in the repository | OBSERVED | repo-wide search returns `phase-6-finalize/SKILL.md:533` plus the two 080 audit files only |
| **Absence:** no commit-SHA field exists in the landing payload contract or producer | OBSERVED | case-insensitive `sha` search over `landing-payload-spec.md` and `emit-landing.md` returns only incidental substring matches; `LANDING_REQUIRED_KEYS` at `_orchestrator_inbox.py:811-820` holds eight keys, none of them a SHA |
| **Absence:** `cmd_inbox_write` performs no landing-uniqueness check | OBSERVED | `_orchestrator_inbox.py:890-982` read in full — slug, sender id, sender type, kind, epic, target-plan and payload validations only |
| `check_landing_completeness` tests presence and non-emptiness only, so an all-`n/a` block passes | OBSERVED | `_orchestrator_inbox.py:886`; producer instruction at `emit-landing.md:235`; vocabulary at `landing-payload-spec.md:84` |
| **Absence:** `emit-landing` appears in neither roster of the document that claims exactly-one classification | OBSERVED | `dispatch-inline-split.md:9` (invariant) and a search of that file for `emit-landing` returning nothing, against its registration at `SKILL.md:178` |
| The roster closure test's registry snapshot is git-tracked but **stale** — 25 steps, not including `emit-landing` | OBSERVED | `.gitignore:45-47` (the `!.plan/marshal.json` exception), `test_dispatch_roster_closure.py:86`, `:213-217`, and the snapshot's own step list |
| `create-pr` declares no `head_dependent:`, resolves its diff scope once, and reuses an open PR without recomposing the body | OBSERVED | `workflow/create-pr.md` frontmatter, `:71`, `:100-108` |
| `pr_intent_section` collapses `OSError`, non-zero exit and unparseable envelope into the "no outline intent" claim, and `create-pr.md` calls that outcome normal | OBSERVED | `pr_intent_section.py:115-123`, `:133-139`, `:194-211`; `create-pr.md:169-178` |
| The review-retrospective artifact carries no completion-HEAD stamp although `:94` claims it does | OBSERVED | `.claude/skills/finalize-step-review-retrospective/SKILL.md:94`, Step 4 at `:388-425`, Step 5 at `:427-445` |
| The gate selects its population by bare truthiness on `foreign` and clears on an empty population | OBSERVED | `foreign_pr_gate.py:186-220`, `:280-288`; classifier fail-open at `manage-solution-outline.py:505-547` |
| `_resolve_landing_state` passes no `--branch`, so the verb classifies the foreign checkout's current HEAD | OBSERVED | `foreign_pr_gate.py:147-164`; `_github_pr.py:664-685` |
| The gate refuses on `pushed_no_pr` alone, and a test pins that `unpushed` clears | OBSERVED | `foreign_pr_gate.py:78`, `:328`, `:334`; `test_foreign_pr_gate.py::test_unpushed_foreign_deliverable_clears` |
| Both foreign selectors ignore `intent`, so a `(read)` foreign path enters the blocking population | OBSERVED | `foreign_pr_gate.py:205`; `manage-solution-outline.py:505-547`; the write-set rule at `_plan_parsing.py:456` |
| **Absence:** no code path invokes `foreign_pr_gate`; its only invocation is prose in `archive-plan.md` | OBSERVED | repo-wide search for `foreign_pr_gate` returns `archive-plan.md:43`, the module docstring, the executor registration and two test files |
| `git rev-parse --show-toplevel` runs without a timeout, and all three `subprocess.run` calls sit outside the `try` blocks | OBSERVED | `foreign_pr_gate.py:135-140` against `:107`, `:165`; standard at `cross-skill-integration.md:266` |
| `unresolved[]`'s two writers append different kinds of path under one documented field | OBSERVED | `foreign_pr_gate.py:30` against `:300` and `:324` |
| `_annotate_foreign` is called from `cmd_list_deliverables` only, so the single-deliverable read verbs return an unannotated record | OBSERVED | `manage-solution-outline.py:495` is the sole call site; `_lookup_deliverable` at `:550` |
| **Absence:** nothing consumes the `foreign` column outside the gate | OBSERVED | searches for `foreign` across `manage-metrics/`, `plan-retrospective/`, `manage-execution-manifest/` and `manage-solution-outline`'s docs all return nothing |
| `done` is written in two places, not one as the 020 report records | OBSERVED | `manage-tasks/scripts/_cmd_step.py:73` and `_tasks_crud.py`'s `cmd_update`, against `report-01.md` § D0 |
| The `LANDING_STATES` comment describes an ordering the tuple does not have | OBSERVED | `ci_base.py:814` against `:817` and `derive_landing_state`'s check order |
| A stale remote-tracking ref makes a pushed branch read `unpushed` | HYPOTHESIS | `_github_pr.py:706-723` (`git branch -r --contains` is the whole axis) plus the absence of any `fetch` / `ls-remote` in that file's landing-state path — settled by a test that seeds a checkout whose remote-tracking ref is behind |
| On a GitLab-configured project the gate surfaces an argparse rejection rather than an unsupported-provider statement | HYPOTHESIS | `github_ops.py:1834-1868` (github-only registration) and the absence of any landing-state handler in `workflow-integration-gitlab/` — settled by driving `check()` with the provider set to gitlab |

## Verification

Beyond each deliverable's *Done when*:

- **Cold read of the landing message (D1) — the check that matters most.** The landing is text a human
  reads to learn whether work shipped, so "implemented as specified" cannot verify it. Dispatch an
  independent reader (the lane's pre-PR verification sub-agent, `cloud-plan-lane` § Step 6) that has
  **not** read this plan. Give it only the composed message a run would emit on `branch-cleanup`
  Branch F — enqueued, merge not landed — and ask one question: *did this plan's work merge?* Report the
  answer verbatim in the run report. The wording has failed, however complete it looks, unless the reader
  answers **no** or **cannot tell from this** — not "yes" and not "probably". Repeat the same cold read
  for the Branch B local-only message, whose current form renders `shipped as n/a (n/a)`.
- **Cold read of the gate's operator text (D5).** Give the same kind of reader a `blocked` verdict and an
  `error` verdict carrying one `unresolved[]` row of each kind, and ask what they would do next. The
  discriminator has failed if the reader cannot say whether the named path is a file they declared or a
  repository root the gate resolved.
- **Re-derive every count at the moment you claim it.** The counts written into this plan — six terminal
  call sites, three non-merging branches, eight `LANDING_REQUIRED_KEYS`, three gate subprocess seams, 25
  registered steps in the snapshot, and the step orders 20 / 70 / 990 / 1000 / 1100 — are **leads, not
  facts**. The clone this run executes in is not guaranteed to match the tree this plan was authored
  from. Re-derive each by reading the file at the moment of the claim, and report any that differ.
- **Regression suite.** Run the repository's Python verification gate per the lane contract's build gate
  (it is conditional on the change touching Python). Every test file named under Expected surface must be
  green, and the new tests in D1, D2, D4 and D5 must each be demonstrated **red before the fix** — record
  the failing output in the run report, because a test that was never red proves nothing about the defect
  it claims to pin.
- **Read-only check on the unchanged surfaces.** Confirm by reading that no change was made to the
  orchestrator drain's routing (`plan-orchestrator/workflow/analyze.md`) and that `archive-plan` gained no
  host-PR merge-state gate — both are out of scope, and a diff touching either is scope drift to report
  rather than to keep.

## Notes

- **This plan is the whole brief.** `.plan/` is git-ignored except for two tracked exceptions
  (`.plan/marshal.json` and `.plan/project-architecture/`, per `.gitignore:45-47`). Everything else under
  `.plan/` — plan directories, `status.json`, the orchestrator ledger, the epic **inbox** the landing
  message is written to, landing records, and the generated `.plan/execute-script.py` — **does not exist
  in this run's clone. Do not go looking for any of it.** The landing and inbox machinery is described
  here and in the source documents named above; that description is what the run works from. No
  deliverable requires running the finalize pipeline or writing a real landing message.
- **Detailed evidence, if you want it.** Every gap id in this plan is written up at length — file, line,
  reproduction, impact — in two git-tracked files that will be on `main`:
  `doc/plans/review-apparatus/080-landing-message-carries-the-outcome-post-merge/gaps.md` and
  `doc/plans/review-apparatus/020-a-foreign-task-reports-done-with-no-pr-anywhere/gaps.md`, each with a
  `verification.md` beside it. They are corroboration, not required reading: this plan restates
  everything the run needs.
- **No gap failed to reproduce.** Every defect named here was re-read at the head of this branch during
  authoring. One piece of supporting evidence needed **correcting**: the roster closure test's blindness
  is not caused by `.plan/marshal.json` being git-ignored — that file is one of two tracked exceptions
  (`.gitignore:45-47`). The defect stands for a different reason, stated in D0: the tracked snapshot is
  *stale* (25 steps, no `emit-landing`), so the invariant passes without covering the step. D0 is written
  against the corrected mechanism, and `080-G10` now states it that way too — so read D0, not the
  mechanism any earlier revision of that gap gave.
- **Why seven entries rather than a split.** The template's heuristic treats six or more deliverables as
  a signal to split. This plan carries seven, of which one is a gating derivation (D0) and one is a
  proposal record (D6) — five substantive changes. Splitting would separate D0 from the deliverables it
  gates, and separate the landing's claim (D1) from the facts that claim rests on (D2), which is exactly
  the seam the blocker runs through.
- **Sequencing.** D0 gates everything: D1 and D2 depend on the terminal-branch set, D5's enforcement test
  depends on the derived step order. D1 before D2 — the claim before the facts the claim rests on. D4
  before D5, because D5's seam tests assert the `--branch` argv D4 introduces. D6 last, so the proposals
  it records reflect what the run actually learned.
- **Two audits, one mechanism.** The gaps gathered here come from separate per-plan audits (080 on the
  landing message, 020 on the foreign-PR gate). They are one plan because they are one mechanism: an
  artefact emitted at plan completion that asserts more than the run positively read. Fixing either alone
  leaves the pattern intact in the other.
