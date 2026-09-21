<!-- ORCHESTRATOR PROVENANCE — read before the plan body.

This spec was authored as a cloud-plan-lane plan and exported under
`.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/540-finalize-dispatch-and-blocking-boundary-observability.md`. It was ingested into this ledger on
2026-08-22 as `PLAN-CIS-052` and it will be EMITTED INTO THE PLAN-MARSHALL LIFECYCLE, not into the
cloud lane.

The exported file opened with a cloud-plan-lane FIRST INSTRUCTION block (`Skill: cloud-plan-lane`,
the merge gate, the run report, the closing self-check). That block has been REMOVED rather than
carried forward: it names a working contract that does not govern a `/plan-marshall` run, and
leaving it would inject a wrong lane instruction into every emitted copy. The plan lifecycle's own
phases supply the equivalents.

NORMALIZED 2026-08-24 (operator-directed), and again 2026-08-26 when the cloud plan lane was
RETIRED and its function incorporated into the orchestrators. The `doc/plans/` export tree no longer
exists, so this header no longer translates paths into it; the rows below remain NORMATIVE for the
cloud-lane TERMS the body still uses.

| Cloud-lane term in the body | What it means in a `/plan-marshall` run |
|---|---|
| "the run report", `report-NN.md` | THIS plan's own verification record: the phase-5 verification sweep output, the plan-retrospective artifact, and the PR body. A `Done when` that says "the run report carries X" is discharged when X appears in the PR body under a clearly-headed section AND in the plan's verification/findings artifacts. |
| "the merge gate" | phase-6-finalize's pre-merge barrier — the HEAD-bound merge authorization plus the pending-findings gate. |
| `./pw <target>` | `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "<target>"`. ⛔ Never invoke `./pw` directly; resolve via architecture. |
| "a sub-agent, per `cloud-plan-lane` § Step N" | a `plan-marshall:execution-context-{level}` dispatch under this plan's own dispatch rules. |
| A cloud-lane export path cited as EVIDENCE | the read-only archived copy under `cloud-runs/{plan}/…` in this epic's tree. ⛔ That tree is git-ignored: it is a local historical record and can NEVER be a deliverable or an Expected Surface entry. |
| "author / stage a successor plan file" | ⛔ NOT this plan's job. File an inbox message to the epic (`orchestrator inbox write --kind finding`) naming the carried-forward deliverables; the ORCHESTRATOR stages plans. A plan that stages plans inverts the prime directive. |

⛔ **This plan writes nothing outside its declared Expected Surface below.** The retired lane's
export tree is not a surface, is not reachable, and no remaining prose may be read as writing there.
-->

<!-- INGEST FACTS (from the 2026-08-22 landed-corpus audit)
gap_coverage: 24 gaps, 6 high
deliverables: 6
workstream: WS-07
wave: 5xx landed-corpus remediation
-->

# The finalize phase records every dispatch it makes, its blocking boundaries refuse audibly, and a dispatch that stops with work left is recorded as a stall

> ⚠ **RE-CUT 2026-09-12.** This spec now carries TEN deliverables (D1–D6 plus **D7–D10**). It absorbed
> the retired `PLAN-CIS-061` (`voluntary_checkpoint` is the modal dispatch termination, and it is a
> stall) on the operator's direction to build larger plans (ceiling twelve) grouped by shared target.
> The grouping is by mechanism: D1–D6 make the finalize dispatch record *what it did*, and D7–D10 make
> it record *why it stopped*. Both act on one dispatch loop, one boundary ledger and one termination
> vocabulary.
>
> ⛔ **Two absorptions in the same act, and both SHRINK the plan rather than growing it.** D1(a)–(d)
> are **STRUCK** — the dispatch-seam migration landed before HEAD `53ab7dd2e` and the skill-wide exit
> condition is met, leaving only D1(e). And the merged D8 is **re-scoped from the predicate to the
> threshold**: the emit site already consults `tasks_remaining`, so the retired spec's premise was
> refuted and its own verify-first clause pre-authorised the narrowing. Ten deliverables of which one
> is a single docstring fix and one is a threshold decision — the count is not the size.

**Epic:** code-intelligence-substrate
**Branch prefix:** fix — these are defects in shipped behaviour and in shipped claims about it

## Problem

The finalize phase has two jobs that this plan is about. It **dispatches** work to sub-agents, and it
is supposed to leave one machine-readable record per dispatch so a later audit can tell a step that
ran from a step that never did. And it **blocks** — on pending findings, on a stale executor, on an
unresolvable checkout — refusing to advance when a precondition fails. Both jobs are currently done
in a way that produces a record or a refusal that nobody can read.

**The dispatch seam has two sites that never joined it.** A prior plan moved finalize dispatch onto a
single emitter: the `effort resolve-target … --workflow … --plan-id … --caller …` call writes the
`[DISPATCH]` work-log line *and* its paired decision-log record, and hand-writing a separate
`manage-logging work "[DISPATCH]"` line is explicitly forbidden. Four sites in
`phase-6-finalize/SKILL.md` were migrated. Two were not.
`phase-6-finalize/standards/finalize-step-simplify.md` issues a bare `effort resolve-target --phase
phase-6-finalize` with no `--workflow`, then spawns a `Task:` — and because the emitter is gated on
`--workflow` being present, that spawn leaves **no record on either surface**.
`phase-6-finalize/workflow/pre-submission-self-review.md` issues the same bare resolve and then
hand-writes the `[DISPATCH]` line the standard forbids — an observable line with no paired decision
record. So for the phase as a whole, **dispatch count does not equal spawn count**, which is the one
property the seam exists to guarantee. Two further step documents,
`phase-6-finalize/workflow/lessons-capture.md` and `phase-6-finalize/workflow/adr-propose.md`, still
instruct the reader that "the dispatcher emits the standardized `[DISPATCH]` work-log line at the
call site" and print the hand-written command to prove it — shipped instructions to reintroduce the
double-emit the seam removed.

**The completion gate refuses, and the refusal is inaudible.** `manage-status archive` and
`manage-status transition --completed 6-finalize` both assert that no actionable finding is pending
before a plan may complete. The assertion fires: it emits a TOON carrying `error:
blocking_findings_present` and leaves the plan directory in place. It also exits **0** — which is
correct house behaviour, mandated by the output contract for operation failures, and is *not* the
defect. The defect is at the one production caller.
`phase-6-finalize/standards/archive-plan.md` § Archive issues the call, parses nothing, and then logs
`"[STATUS] … Plan archived: {plan_id}"` unconditionally — having already recorded the step
`--outcome done` one section earlier. On a real refusal the plan is not archived, the step says it
was, and the log says so too. The same document demonstrates the correct shape one section earlier:
its foreign-PR gate parses `status` and has an explicit `status: blocked` → *"STOP. Do NOT mark the
step done and do NOT archive."* branch.

**And the boundary that was armed is not the boundary the fix was aimed at.** The state assertion is
reached from the `archive-plan` step, which runs at `order: 1100`. The **merge** happens in
`branch-cleanup` at `order: 70` — 1030 order-units earlier — gated only by a `phase_handshake
findings-check` instruction in a markdown workflow whose verdict an LLM must issue and parse. The
plan that landed this work was written about a plan that *merged* with nineteen pending findings.
After the fix that merge is still possible; only the later archive is refused, which strands the plan
post-merge rather than preventing the bad merge.

Three more mechanisms in the same neighbourhood report success they did not achieve. The
**executor-refresh** verdict at the rebase seam (`git-workflow.py::_refresh_worktree_executor`)
decides "regenerated" from a *presence* check on the executor slot — and `prepare_execute` guarantees
that slot is always occupied in a real worktree, so a generation that wrote nothing still reports
`executor_regenerated: True` over stale bytes; the exit code is no backstop, because the generator
prints `status: error` and returns 0. The **Bucket B plan-id injection** in
`execute-task/scripts/inject_project_dir.py` cannot fire for half its declared population: two
whitelist entries name scripts that do not exist on disk, and a gate that requires the literal token
`run` after the notation excludes every notation that dispatches a verb directly — and the test
duplicates the same wrong list, so it is green and proves nothing. And the **fused completion
marker** emits `"Completed step: X"` for `outcome=loop_back`, a step the dispatcher is about to
re-fire, feeding a `completion_count` denominator whose ratio gates a confidence downgrade.

## Goal

Every dispatch the finalize phase makes leaves exactly one record written by the one emitter, and
every document in the phase describes that mechanism truthfully. Every boundary in the phase that is
supposed to block either blocks audibly at its production caller, or — where making it block requires
an architectural choice this run may not make — carries a written proposal the operator can decide
from. Every payload that reports on a refresh, an injection, or a completion says what actually
happened rather than what was attempted.

## Deliverables

**TEN deliverables** (D1–D10). D1–D6 own what the finalize dispatch RECORDS; D7–D10 (merged
2026-09-12 from the retired `PLAN-CIS-061`) own what it does when it STOPS. Each is independently
verifiable; none depends on another's landing to be
reviewable. **Every count in this plan is a lead, not a fact** — the tree will have moved. Re-derive
each one at the moment you rely on it, and report the figure you derived, not the figure written
here.

Three deliverables carry an item whose right answer is a genuine architectural judgement. Those items
are authored to **record a proposal for the operator, never to make the call** — there is no operator
in this run to ask. A proposal is recorded in two places, because the plan directory is deleted when
the orchestrator collects this epic: in the run report, **and** in a clearly-headed
`## Operator decision required` section of the pull request description, which survives the
collection.

---

1. **D1 — One emitter for every finalize dispatch, and documents that say so**

   ⛔⛔ **SUB-ITEMS (a)–(d) ARE STRUCK 2026-09-12 — THE MIGRATION HAS LANDED. Do not implement them.**
   The 2026-09-05 re-grounding refuted rows 0/1/2, and the refutation is confirmed first-party at
   HEAD `53ab7dd2e`: `grep -rn -- '--message "\[DISPATCH\]'` over
   `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` returns **nothing**, which is (a)–(d)'s
   own skill-wide exit condition, met. Per file: `finalize-step-simplify.md:110` and
   `pre-submission-self-review.md:197` both now carry the full seam form (`--workflow`, `--plan-id`,
   `--caller plan-marshall:phase-6-finalize`) and both explicitly instruct *"Do NOT hand-write a
   separate `[DISPATCH]` line"*; `lessons-capture.md:54` and `adr-propose.md:42` both already state
   that the resolve seam emits the line and its paired decision-log record per firing, and neither
   carries a `manage-logging work` block. **Four of this deliverable's five sub-items are therefore
   dead work**, and the *Done when* clauses (i)–(iii) below are already satisfied at HEAD.

   ⇒ **D1 is re-scoped to sub-item (e) alone**, which is still live: `_decision_line_shapes.py`'s
   module docstring still enumerates `unresolved_ask_provider_drop`, `scope_gated_finalize`,
   `ceremony_finalize_selection` and the `*_inactive` pre-filter line as gates that *"carry no
   `[STATUS]` tag"* — a four-item list presented as the set. Re-derive (e) at outline and fix it by
   property, not by list.

   ⭐ **Keep (a)–(d) in the document rather than deleting them.** They are the record of what was
   refuted and of the exit condition that proves it, and a future reader who finds only (e) cannot
   tell a completed migration from a forgotten one. What follows is retained as that record:

   *Historical statement (STRUCK — landed before HEAD `53ab7dd2e`):* four dispatch-shaped defects in
   `phase-6-finalize`, plus one code comment of the same class elsewhere. All five were a *claim about
   which line gets written by what*, and each was wrong.

   a. `standards/finalize-step-simplify.md` — the bare `effort resolve-target --phase
      phase-6-finalize` (near `:113`, re-derive) becomes the canonical seam form used by the migrated
      sites in `SKILL.md`: `--workflow
      plan-marshall:phase-6-finalize/standards/finalize-step-simplify.md --plan-id {plan_id}
      --caller plan-marshall:phase-6-finalize`. **The `--caller` is load-bearing** and must not be
      dropped as noise: without it the resolver falls back to a different caller key, and the
      dispatch-audit detector counts finalize lines *by that caller*, so a migration without
      `--caller` still leaves the line uncounted. State in the document, as `SKILL.md` does, that the
      resolve and the spawn are one indivisible pair.
   b. `workflow/pre-submission-self-review.md` — the bare resolve (near `:194`) takes the same seam
      form with this file's own `--workflow` path, and the hand-written `--message "[DISPATCH] …"`
      block below it (near `:204`) is **deleted**, replaced by the "the same seam call has already
      written the line" sentence used in `SKILL.md`. ⚠ Leave the inline-gate instruction further up
      the file (near `:168`, *"do NOT emit a `[DISPATCH]` log line"*) **intact** — it stays correct
      once the emission rides the resolve, because the inline branch performs no resolve at all.
   c. `workflow/lessons-capture.md` — delete the `[DISPATCH]`-log-line section and its
      `manage-logging work` command block, and rewrite the sentence that claims the dispatcher emits
      the line at the call site to say the emission rides the dispatcher's `effort resolve-target …
      --workflow` seam call, per firing.
   d. `workflow/adr-propose.md` — the identical defect in a second file, edited independently.
   e. `manage-execution-manifest/scripts/_decision_line_shapes.py` — the module's scope comment
      claims that gates rendering their own drop lines "carry no `[STATUS]` tag". At least one such
      gate renders its line **with** a `[STATUS]` tag and is still matched by nothing (the shared
      pattern additionally requires a trailing reason separator it does not carry), and at least one
      further own-shape drop line is unnamed by the four-item enumeration. Restate the clause **by
      property, not by list**: the module owns the `phase_6.steps` subtraction record; lines that
      drop from other lists, or render their own shape, are matched individually. Name live examples
      as examples, not as the set.

   *Done when:* (i) `grep -n 'Task: ' finalize-step-simplify.md` shows every spawn preceded by a
   resolve carrying `--workflow`, `--plan-id` and `--caller plan-marshall:phase-6-finalize`;
   (ii) `grep -n -- '--message "\[DISPATCH\]' pre-submission-self-review.md` returns nothing;
   (iii) `grep -n '\[DISPATCH\]' lessons-capture.md adr-propose.md` returns only seam-descriptive
   prose with no `manage-logging work` command; (iv) the `_decision_line_shapes` clause makes no
   claim about `[STATUS]` tags that any own-shape drop line in
   `manage-execution-manifest.py` falsifies, and presents no enumeration as exhaustive — verify by
   listing every own-shape drop line in that module and checking each against the clause;
   (v) the cold read in § Verification returns "the seam writes it" for all four documents.

   ⚠ The *skill-wide* condition — no `--message "[DISPATCH]"` anywhere under `skills/phase-6-finalize/`
   — is reachable only when (b), (c) and (d) have **all** landed. Treat it as the deliverable's exit
   condition, not as a blocker on any one item.

2. **D2 — The `manage-status` write path records what actually happened**
   Three places where a write reports something the write did not achieve.

   a. **The fused completion marker fires for `loop_back`.** `manage-status/scripts/_cmd_mark_step.py
      ::_emit_completion_marker` inspects only `suppress` and the phase; neither it nor its two call
      sites inspects `outcome`. Driving `cmd_mark_step_done` with `phase='6-finalize'`,
      `outcome='loop_back'` returns a work log containing exactly `[STEP] (plan-marshall:
      phase-6-finalize) Completed step: {step}` — for a step the dispatcher will re-fire, and which
      emits a *second* line when it finally settles. **This plan makes the call, so the run does not
      have to: suppress the emission when `outcome == 'loop_back'`.** The reasons are on the record
      and are not re-litigated mid-run: the governing principle in `phase-6-finalize/SKILL.md`
      ("the `defer` branch records nothing — the step did not settle, so it owes no completion"), the
      `manage-status` description of the emission as riding the terminal write, and the plain fact
      that no reading makes "Completed step: X" true of a step that did not settle. Make code,
      `manage-status/SKILL.md` § "Fused completion emission", and `phase-6-finalize/SKILL.md` item 7
      state the same rule.
      ⚠ **Do not chase the threshold.** Suppression lowers `completion_count` for looped runs, which
      moves the dispatch-audit `dispatch_line_count / completion_count` ratio *upward* against a
      sparse-ratio threshold. Whether that threshold is still defensible can only be re-read against
      a real archived corpus, which is machine-local under `.plan/` and **invisible from this
      clone — do not go looking for it.** Record the threshold re-read as a named residue item in the
      report; do not adjust the constant.
   b. **The start half of the marker pair is still prose.** `phase-6-finalize/SKILL.md` item 2 emits
      `[STEP] … Executing step:` by instructing the dispatcher to log it, so a missing start line
      remains indistinguishable from a step that never ran — the original defect, half-closed. The
      symmetric fix (emitting the start marker from a shared write, e.g. a `mark-step-start`
      handshake) is a new verb on a lifecycle contract and a population change for every consumer
      that counts those lines. **This run does not make that change.** It takes the documented arm:
      state the declined symmetry, with its reason, in *both* `phase-6-finalize/SKILL.md` item 2 and
      `manage-status/SKILL.md` § "Fused completion emission", and add a test pinning that item 2 is
      the sole start emitter. **Record the fusion as a proposal** (both places named above), carrying
      the concrete shape and the consumer-population cost.
   c. **A pre-list plan's legacy `session_id` is unreachable after the first append.**
      `platform-runtime/scripts/claude_runtime.py::_manage_status_read_session` prefers `session_ids`
      whenever the list exists, and `manage-status/scripts/_status_query.py::_cmd_metadata_append`
      creates the list without seeding it — so for a plan spanning the change, the original identity
      survives in `status.json` and in nothing any consumer reads. Seed the list with the legacy
      scalar on the **first** append when the scalar is present and the list is absent, leaving the
      scalar in place for the shim. The one condition that would forbid the seeding is a consumer
      that treats the first element of `session_ids` as the *current* session rather than the
      earliest; check that by reading every reader of the field before writing the change, and if one
      exists, record the deliberate non-migration and that reader's name in the shim block instead.

   *Done when:* (a) `test/plan-marshall/manage-status/test_mark_step_completion_emission.py` carries a
   `loop_back` case that is **red against the current code** and green after, and the two SKILL.md
   sections state the same rule as the code; (b) a test asserts that no start marker is produced by
   any write path — i.e. that item 2's prose instruction is the sole emitter — and both documents
   carry the declined-symmetry rationale, with the fusion proposal recorded in the report and the PR
   body; (c) appending to a plan carrying only the legacy scalar yields `session_ids == ['<legacy>',
   '<new>']`, pinned by a test that is red before the change, **and** the seeding is idempotent — a
   second append to a plan whose list already exists must not reinsert the retired identity.

3. **D3 — The completion boundary refuses audibly; the merge boundary's arming is proposed**

   a. **Make the refusal observable at its one production caller.** Amend
      `phase-6-finalize/standards/archive-plan.md` § Archive to parse the returned TOON `status`
      *before* the "Plan archived" log, with an explicit `error: blocking_findings_present` branch
      modelled on the foreign-PR gate earlier in the same document: route the pending findings back
      through the verification-feedback / loop-back path, do **not** emit the archive log, and do
      **not** leave the step recorded `done`. The `mark-step-done` call currently precedes the
      archive; it must still land **before** the move (archive invalidates the live plan path), so
      the ordering change is "do not record `done` on a refused archive", not "move the record after
      the archive". Add a test that drives `manage-status archive` through `main()` with a pending
      actionable finding and asserts the emitted TOON carries `status: error` /
      `error: blocking_findings_present`.
      ⛔ **Do not "fix" this by making the CLI exit non-zero.** Exit 0 for an operation failure is
      mandated by `pm-plugin-development:plugin-script-architecture/standards/output-contract.md`;
      the adversarial review of the source audit corrected this gap's original remedy for exactly
      this reason, and following the uncorrected version would send this run against a shipped
      contract. If a non-zero exit is wanted as a second signal, it is a **documented deviation**
      of the same kind the `transition` drift arm already is — and that is a contract change, so it
      is **recorded as a proposal**, not shipped.
   b. **Propose the state-arming of the merge boundary; do not build it.** The merge is gated by a
      `phase_handshake findings-check --phase 6-finalize` instruction in `branch-cleanup.md` that an
      LLM must issue and parse. Making the merge *unable to proceed* without the predicate having
      been evaluated has two defensible shapes, and choosing between them is an architecture
      decision with a stated cost: (i) have `findings-check` persist a HEAD-bound clean-attestation
      row and thread a `--plan-id` / `--require-findings-attestation` pair into the `ci pr
      safe-merge` and `ci pr merge-queue` verbs — which are today **deliberately plan-agnostic**, so
      this couples the provider-generic CI abstraction to plan state; or (ii) interpose a single
      `phase_handshake pre-merge-assert` executor that performs the attestation check and the merge
      dispatch as one step, leaving the CI verbs untouched. **Write the proposal, comparing both
      shapes, naming the coupling cost, and naming the failure mode each must avoid** — an
      unevaluable findings store must route to the existing "UNKNOWN disposition" path, not to a hard
      halt, or a degraded store strands a merge. Do not implement either shape.

   *Done when:* (a) a test drives `manage-status archive` through `main()` against a pending
   actionable finding and asserts the refusal TOON — **red before the deliverable only if a
   pre-existing test does not already cover the CLI surface, so first re-derive whether one does**;
   `archive-plan.md` § Archive contains a `blocking_findings_present` branch that suppresses both the
   archive log and the `done` outcome; and the cold read in § Verification, given the amended §
   Archive and asked "what does this document tell you to do when the archive call returns
   `blocking_findings_present`?", answers *stop, do not log, do not mark done* — not *log and
   continue*. (b) A proposal document exists in the run report and in the PR body's `## Operator
   decision required` section, naming both shapes, the coupling cost, and the unevaluable-store
   disposition; **no production file implements either**.

   ⛔ **Boundary with an adjacent plan:** the completion boundary's *unevaluable-query* disposition
   (the `blocking is None` fail-open in `manage-status/scripts/_cmd_lifecycle.py`) is a separate gap
   owned by a sibling 5xx plan. Do **not** change that branch here, in either direction.

4. **D4 — The rebase-seam executor refresh reports the truth, never crashes the rebase, and is heard**
   All three items are `workflow-integration-git/scripts/git-workflow.py` and its one unwired caller.

   a. **The success verdict cannot distinguish a new executor from a stale one.**
      `_refresh_worktree_executor` decides `executor_regenerated: True` from `executor_landed(…)`, a
      presence check (`is_file() and not is_symlink() and st_size > 0`). Presence is guaranteed
      independently: `prepare_execute` generates the worktree executor at phase-5 move-in and
      self-heals it when missing, so by the time a finalize rebase runs, the slot is occupied and the
      `not landed` branch is effectively unreachable in production — it fires only in the test
      fixture, whose cloned worktree never had an executor at all. The exit code is not a fallback
      either: `generate_executor.py`'s `main` prints the TOON and returns 0 unconditionally, so a
      `cmd_generate` returning `{'status': 'error'}` still exits 0. Fix: require **both** that the
      generator's own TOON reports `status: success` — parse `gen_out` the way the drift probe
      already parses its stdout — **and** that the slot is occupied; report the generator's `error`
      text in `executor_detail` when it does not.
      ⛔ **Do not implement this as a byte comparison** (hashing the slot before and after): a
      legitimate regeneration that happens to produce identical output would be misreported as a
      failure.
   b. **`_run_generate_executor` does not honour its "never raises" contract.** Its docstring says
      *"never raises"* and `_refresh_worktree_executor`'s says *"Every failure mode is reported in
      the return value and none is raised"*, but it catches exactly `FileNotFoundError` and
      `subprocess.TimeoutExpired`. `subprocess.run` can raise other `OSError` subclasses, and neither
      `_refresh_worktree_executor` nor the call site in `cmd_worktree_rebase_to` has a handler — so an
      exotic failure turns a rebase that **already succeeded and moved HEAD** into a crash reported
      to the caller, which is verbatim the outcome the code's own comment argues must be prevented.
      Widen the `subprocess.run` handler to `except OSError as exc:` (which subsumes both
      `FileNotFoundError` and `PermissionError`), keep `TimeoutExpired` as its own arm, preserve the
      distinct return codes that are already meaningful, and put the exception text in the third
      tuple element so it reaches `executor_detail`. Keep the handler scoped to the `subprocess.run`
      call only — a broader arm would mask programming errors that surface loudly today.
   c. **The payload is discarded on one of its three documented consumers.**
      `automatic-review/SKILL.md`'s refusal-recovery path dispatches `git-workflow worktree-rebase-to`
      and proceeds straight to `force-push-with-lease`, parsing neither `executor_drift` nor
      `executor_regenerated` nor `executor_detail`. Both sibling callers
      (`phase-6-finalize/standards/finalize-step-sync-baseline.md` and `.../branch-cleanup.md`) emit a
      `[STATUS]` work-log line carrying all three, and the `worktree-handling.md` standard names all
      three callers as a roster. Add the same emission immediately after the call, matching the
      sync-baseline wording.

   *Done when:* (a) a test seeds the worktree executor slot with a pre-existing file **before** the
   rebase, drives a `drift` verdict with a generation that exits 0 without writing (or whose TOON
   carries `status: error`), and asserts `executor_regenerated is False` with the generator's failure
   named in `executor_detail` — and the existing test asserting that a zero-exit generation which
   lands no file is not success still passes; (b) a test monkeypatches
   `git_workflow.subprocess.run` to raise `PermissionError`, invokes `cmd_worktree_rebase_to` on a
   rebase that replayed commits, and asserts `result['status'] == 'success'`,
   `result['executor_regenerated'] is False`, and a non-empty `result['executor_detail']` — this test
   must be **red against the current `except` clauses**; (c) `automatic-review/SKILL.md`'s recovery
   path emits a line naming all three fields.

   ⚠ Deliverable (b)'s test is also the subject of a gap in the sibling test-integrity plan (see
   Notes). Land it here — it is this deliverable's own *Done when* — and say so in the report so the
   sibling plan does not author a second one.

5. **D5 — `pre-submission-self-review.md` executes correctly when read in document order**
   One file, four defects, one mechanism: an executor works this workflow as a numbered step
   sequence, and each defect is something the sequence does not reach or actively contradicts.

   a. **Step 4 never learns the self-seeding classification is owed.** The § "Round-loop termination"
      section states the obligation — a `manage-logging decision --level WARNING` naming the round
      self-seeding, "so the classification is an auditable record rather than merely narrative" — but
      Step 4 Branch B, the only place a non-clean round is handled, emits the `qgate add` loop, a
      `git rev-parse`, and `mark-step-done --outcome failed`, and mentions self-seeding nowhere. The
      reference direction is one-way. Insert a classification sub-step in Branch B immediately before
      the `mark-step-done` block, with the runnable `manage-logging decision --level WARNING` command
      block, and cross-reference § "Round-loop termination" **by section name**. State the
      doc-claim/delta-scope predicate **by reference** to that section rather than restating it — a
      loose restatement would add a WARNING line to ordinary non-clean rounds.
   b. **The Step 4 remediation sentence contradicts the section below it.** The closing operator
      sentence prescribes *"amend the diff: rename, tighten regex, rewrite wording, delete duplicate
      section, fix contract drift"* — three of which author new prose — while § "Round-loop
      termination" says *"Resolve a self-seeding finding by deletion, not correction. … Rewriting
      authors the next round's finding; deletion ends the class."* Append a carve-out clause naming
      the self-seeding exception and linking the section, **gated on the classification** rather than
      on the defect class, so deletion is not over-applied to ordinary doc-claim findings.
   c. **The delta round's evidence set can be computed across an upstream advance.** The resolve
      sub-step diffs `{since_ref}..HEAD`, where `{since_ref}` is the previous round's
      `head_at_completion`. Two steps rebase the feature branch onto a freshly-fetched base —
      `finalize-step-sync-baseline` (full preset only) and `branch-cleanup` (**every** preset) — so
      the exposure is preset-independent: a loop-back issued from the pre-merge barrier reaches a
      delta round whose anchor was already rewritten. `git diff A..B` is an endpoint comparison, so
      the diff then carries every file the upstream advance touched into `--changed-path`, and the
      resolver marks the matching pending finding `fixed` with detail *"evidenced by landed change …
      touching …"* — a finding marked fixed with no landed change of ours, which the source plan
      itself calls strictly worse than one left pending. There is no ancestry check anywhere in the
      file. Gate the resolve sub-step on `git -C {worktree_path} merge-base --is-ancestor {since_ref}
      HEAD` succeeding; when it fails, **skip the resolution for that round and say so**, leaving the
      findings pending, with an operator message explaining why.
   d. **The anchor diff has no documented failure branch.** The same sub-step issues `git diff
      --name-only {since_ref}..HEAD` and `git rev-parse HEAD` with no stated handling for a non-zero
      exit; the surfacer's own `since_ref_unresolvable` refusal applies to a later call. State that a
      failed anchor diff skips the resolve sub-step and proceeds to the surface call, which owns the
      halt. This folds into (c) — one branch, two entry conditions.

   *Done when:* Steps 1–4 read **in document order** produce the classification, the WARNING command
   block, the ancestry precondition, and the skip branch, with no forward reference an executor must
   discover on its own; the two normative statements about how to resolve a finding no longer
   disagree; and a worked example or test shows a post-rebase round leaving prior findings `pending`
   rather than resolving them. The interpretation half is settled by the cold read in § Verification,
   which must be given Steps 1–4 **without** § "Round-loop termination" and must still report that a
   self-seeding round owes a classification and a WARNING log, and that a rewritten anchor skips
   resolution.

6. **D6 — Guards and signals at the finalize seams that cannot fire, or cannot be heard**
   Six independent defects sharing one shape: a mechanism that declares a population, an input, or an
   output it does not actually have.

   a. **Bucket B plan-id injection cannot fire for half its whitelist.**
      `execute-task/scripts/inject_project_dir.py` carries a frozenset of notations that receive an
      injected `--plan-id`, and **two independent blockers make roughly half of it inert** (re-derive
      the fraction — the audit measured 4 of 8):
      *Blocker 1 — two entries name no script.* `…:workflow-integration-git:git` and
      `…:workflow-pr-doctor:pr-doctor` are matched by exact string comparison, but the on-disk
      scripts are `git-workflow.py` and `pr_doctor.py`, and every real invocation uses the on-disk
      spelling. Replace the two entries with `plan-marshall:workflow-integration-git:git-workflow`
      and `plan-marshall:workflow-pr-doctor:pr_doctor`.
      *Blocker 2 — the gate requires the literal token `run`.* Only the `build-*` notations are
      invoked that way; `ci`, `sonar`, `git-workflow` and `pr_doctor` all dispatch verbs directly
      (`ci pr create`, `sonar fetch_findings`, `git-workflow locate-plan-checkout`, `pr_doctor
      track-attempt`). **This plan takes the relax arm**: injection applies to any subcommand token,
      with `--plan-id` inserted immediately after the subcommand. The alternative the gap offers —
      keeping `run`-only and deleting the five notations that never use it — is rejected here because
      it shrinks the guard to the four build notations, which is the opposite of what the guard is
      for. Before widening, **verify per notation that the target script accepts a router-level
      `--plan-id`**; any notation whose script does not is left out of the widened set with the
      reason stated in the module docstring. That is a derivation, not a judgement — read each
      script's argument surface.
      *And the test locks the defect in.* `test/plan-marshall/execute-task/test_inject_project_dir.py`
      re-declares the same wrong whitelist as a literal list and asserts injection for each using a
      synthesised `{notation} run --command-args "verify"` command no production caller writes.
      Replace the duplicated list with an import of the module's own frozenset, and parametrise each
      notation with the subcommand its own SKILL.md documents.
      *Done when:* `inject_project_dir` returns injected for
      `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow
      locate-plan-checkout` and for `python3 .plan/execute-script.py
      plan-marshall:workflow-pr-doctor:pr_doctor track-attempt --category build --current 0`; the
      test file imports the whitelist instead of restating it; and no test asserts injection through
      a command shape no production caller writes.
   b. **A finalize step reads a footprint key that no longer exists.**
      `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` Step 1 runs `manage-references get
      --plan-id {plan_id} --field modified_files`. The key was removed from the references ledger;
      the read therefore returns not an empty list but `status: error` / `error: field_not_found`
      (exit 0, by the house output contract), and **no row in the step's Error Handling table covers
      `field_not_found`** — the one row that names `modified_files` is about a missing retrospective
      report and prescribes the dead key as the remedy. Since the retrospective report is also
      normally absent at this step's order, both of the step's outcome inputs are unusable and it
      classifies lessons against `request.md` alone. Change Step 1 to read the realized footprint,
      noting that the footprint capture happens later in the phase, so a same-run read must use the
      live worktree diff (`manage-references compute-footprint`) rather than the capture; update the
      classification-input sentence and the Error Handling row to name the source actually read.
      *Done when:* the Step 1 command returns `status: success` rather than `field_not_found` for a
      plan created after the ledger removal — demonstrate this by driving the underlying
      `cmd_get` / `compute-footprint` handler over a references document that carries no
      `modified_files` key, since a cloud clone has no `.plan/` plans to run against — and the
      fallback text and the Error Handling row name that same source.
   c. **The finalize 5c gate excludes a cause the table it classifies into defines.** The gate fires
      only when the step ran as a Task agent and did **not** time out, while the cause it classifies
      into is defined as *"cut short by a session restart, harness cancellation, or the per-agent
      timeout budget firing"* — one of whose three sub-cases the gate structurally excludes. A
      further value in the cause table is missing from the brace-form value list in the invocation.
      **This plan takes the redefinition arm**: redefine the cause to the case the gate can actually
      observe (remove the timeout wording), and reconcile the invocation's value list with the cause
      table in whichever direction the writer's own `choices` enum permits — read the enum, do not
      guess it. The other arm (recording a boundary row on the timeout path) is **deliberately not
      taken here**, because it would add a `record-dispatch-boundary` call on an error path where
      the usage block is unavailable, which is coupled to a fabricated-zero defect owned by a
      sibling 5xx plan. Record that arm as a named residue item in the report.
      *Done when:* every cause named in the 5c cause table is writable under the gate as that gate is
      worded; no sub-case in a cause's definition names a condition the gate excludes; and the
      brace-form value list contains exactly the causes the table defines, all of which the writer's
      enum accepts.
   d. **The one plan-directed message stream is never told to name its target.** The inbox
      deliverability guard refuses a write aimed at a running plan — but only when `--target-plan` is
      supplied, and nothing supplies it: the argument is `required=False, default=None` with no env
      or config fallback, and the verb has no programmatic caller. Of the write sites in the bundles,
      three are self-addressed by message kind (a landing, and own-run candidate lessons) and the
      canonical synopsis already shows the flag; **exactly one** — `lessons-capture.md`'s
      `--kind {kind}` block, where the doc resolves *"every candidate lesson and every finding rides
      as `candidate-lesson`"* — can carry content aimed at another plan. Add the obligation **there
      and only there**: when an emitted item is aimed at a named plan, the write MUST pass
      `--target-plan {plan_id}`, shown in the command block; add the matching sentence to the
      write-side deliverability section of the inbox envelope standard naming `lessons-capture` as
      the site that owes it.
      ⛔ Do **not** touch the other write sites — their messages are self-addressed and the flag is
      meaningless there. ⛔ If a payload-side detector is ever preferred over an obligation, it MUST
      exclude the sender's own plan id: a landing payload names the sender's plan, whose queue row
      still reads `running` at finalize time, so an unqualified payload scan refuses **every** landing
      write. The source audit's original remedy did exactly that and was corrected; do not
      reintroduce it.
      *Done when:* the `lessons-capture` command block shows `--target-plan {plan_id}` with a stated
      condition for supplying it, the envelope standard names the owing site, and a test drives the
      refusal through the argv shape that documented block produces.
   e. **The same guard's fail-open is invisible.** When the epic queue cannot be read as a queue, the
      running-plan set is empty and the guard cannot fire. The fail-open is the right default — and
      is documented as intentional — but the caller cannot distinguish *"target is not running"* from
      *"I could not tell"*. Keep the fail-open; emit an advisory field (e.g.
      `target_plan_check: indeterminate`) on the success TOON when `--target-plan` was supplied and
      the status document was unreadable. Check first that no consumer asserts an exact key set on
      that output.
      *Done when:* a `--target-plan` write against an epic with a missing **and** with a malformed
      status document succeeds and carries the indeterminate marker, pinned by a test covering both.

      ⚠⚠ **CROSS-EPIC ORDERING CONSTRAINT ON d AND e — folded in 2026-08-24 from inbox
      `truthful-signals-044`. Read before implementing either.** The sibling epic has staged
      `PLAN-TRUTH-100-the-inbox-has-no-delivery-path-to-a-running-plan`, whose D1 **re-scopes the very
      guard d and e are built on**: a message aimed at a *running* plan becomes **delivered**, not
      refused, and § Write-side deliverability of `inbox-envelope.md` — the section d edits — is
      rewritten. ⭐ **Both readings of today's code are correct and they are not in conflict**: d/e's
      premise is that the guard is UNDER-REACHED (verified first-party here — `orchestrator.py:2700`
      confirms `--target-plan` is `required=False, default=None`, so the refusal rarely fires); theirs
      is that the refusal blocks a mid-run channel. **This epic wants the guard reached more often;
      they want its answer changed.**
      - ✅ **Nothing blocks this plan.** `TRUTH-100` is sequenced AFTER `CIS-052` in their ledger as a
        hard ordering constraint, and is itself blocked behind three of their launched plans. Emit
        `CIS-052` whenever the hold lifts.
      - ⛔ **d's envelope sentence MUST be worded as the OBLIGATION, not the CONSEQUENCE.** Write *"a
        write aimed at a named plan MUST pass `--target-plan`"* — **not** *"…and will be refused if
        that plan is running."* The obligation survives their re-scope; the consequence does not.
        Costs nothing now and saves a rewrite later. This is the one actionable item from that message.
      - ⭐ **e is preserved, not obsoleted.** "I could not tell whether the target is running" still
        matters after their change — it selects DELIVERY versus drain-queueing rather than refusal
        versus write. They have written that into their spec so a later reader does not retire the
        advisory field as dead.
      - ⚠ **Their offer, recorded and NOT taken**: this epic could own the whole guard including the
        delivery re-scope. **An offer is not a transfer** — the default stands that they keep it. Raise
        it with the operator if this plan's implementer wants the whole surface.
   f. **A cross-ledger reconciliation verb exists with no caller.** `manage-metrics
      reconcile-ledgers` is registered, documented and unit-tested, and a whole-tree search finds
      **zero workflow call sites** — so on every real plan a cross-ledger disagreement is still
      silent, which is precisely what the plan that built it set out to end. The natural call site is
      the finalize metrics step, after the existing end-phase → enrich → generate sequence,
      read-only and never blocking the archive, logging `union_rows` and `findings_count` and
      surfacing a `[WARN]` when `findings_count > 0`.
      ⚠ **This item is stop-condition gated, and the gate is the first thing to run.** Wiring the
      verb makes a contained recursion defect live: the row-pairing routine in
      `manage-metrics/scripts/_ledger_reconciliation.py` recurses per candidate row and raises
      `RecursionError` around ~1 000 same-timestamp rows per side — the exception escapes as a
      traceback rather than as a TOON error block, and a phase that recorded ~1 000 dispatches is
      exactly the phase most in need of reconciling. That defect is owned by a **sibling 5xx plan,
      not this one**. So: write a throwaway check that drives the pairing routine over ~1 200
      identical-timestamp rows per side. **If it raises, do not wire the call** — record the wiring
      as a ready-to-apply proposal naming the recursion blocker and the plan that owns it, in the
      report and in the PR body. **If it returns**, the blocker has already landed: wire the call.
      Either way, report which branch was taken and the figure you measured.
      ⛔ Whether these findings should feed `manage-findings` rather than the work log is the scoping
      the previous run declined to make, and this run does not make it either: routing them into
      `manage-findings` would make a cross-ledger disagreement a *blocking* finding at the completion
      boundary D3 governs, which is a behaviour change too large to take unasked. **Work-log
      observation only**, with the `manage-findings` routing recorded as a proposal.
      *Done when:* either the finalize metrics step carries a `reconcile-ledgers` invocation whose
      work-log line names `union_rows` and `findings_count`, with a test driving the step over a
      disagreeing corpus and observing the line; **or** the recursion check raised, no call was
      wired, and the proposal plus the measured figure are recorded in the report and the PR body.

---

### Folded from the 2026-08-25 inbox drain (PLAN-CIS-059 / PR #1348)

**(N1) An `error`-severity finding filed AFTER the metrics close stays `pending` past merge, and the
plan archives around it.** Folded from inbox `-007`. This extends this plan's blocking-boundary
subject directly: the boundary arms on a gate that no longer exists.
⭐ OBSERVED, first-party from the run: Q-Gate finding `8d44fd` — severity `error`, phase `6-finalize` —
was filed at `2026-08-25T20:22:22Z`. By then PR #1348 had **already merged** (`9aaf22d8f`),
`branch-cleanup` had recorded `done`, and the `6-finalize` metrics row had closed at `19:52:24Z`,
**30 minutes earlier**. `manage-findings qgate list --phase 6-finalize --resolution pending` returns
exactly **1 of 10**; `manage-findings list --resolution pending` returns **0 of 10** plan-level
findings. That one pending record is the **most serious finding filed in the entire run**.
⛔ **Root shape**: `pending_findings_blocking_count` gates phase TRANSITIONS, so a finding filed after
the last transition has no gate ahead of it and `error` severity **buys nothing**. ⛔ It compounded
with an assertion: the retrospective's own dispatch brief stated all nine findings were resolved —
**asserted rather than read back from the store** — which is exactly how a pending error stays
invisible. That is this epic's *vacuous-authority* archetype, recurring inside the run that reported it.
⭐ The fail-closed precedent already exists in the tree: `delete-plan`'s lesson carry-back **veto**
refuses a terminal action that would strand a record.
*Done when:* either finalize re-reads the findings store after `branch-cleanup` and routes any
still-pending `error` finding into the epic inbox as an explicit carry-out, **or** archiving refuses
while a plan holds a pending `error`-severity finding (the `delete-plan` veto shape); and a test drives
a finding filed after the metrics close and observes it is not stranded. ⛔ A claim that findings are
resolved MUST be read back from the store, never asserted.

⚠ **Surface addition**, declared in the same pass as the fold:
`marketplace/bundles/plan-marshall/skills/manage-findings/` (the pending-`error` read-back) — this
plan already declares `phase-6-finalize/standards/archive-plan.md`, which N1 extends.

### Folded from the 2026-08-26 inbox drain (PLAN-CIS-060 / PR #1355)

Five `candidate-lesson` messages from `verdict-field-read-and-write-integrity`. All five are
first-party from a single run's retrospective, and four of the five are the SAME instrument —
`pre-submission-self-review` — seen from four angles. ⛔ **Scope note**: these are folded as sub-items
of existing deliverables, NOT as new deliverables; this spec's deliverable count is unchanged and its
recorded scope-bloat rationale still holds.

**(N2) The finalize dispatch ledger cannot see a re-dispatch INSIDE an already-entered step, and the
hole is ~36% of the phase that dominates plan spend.** Folded from inbox `-001`. ⭐ OBSERVED: seven
`pre-submission-self-review` rounds produced **2** `[DISPATCH]` lines, **2** `effort resolve-target`
records and **2** dispatch-boundary rows. `6-finalize` records `total_tokens: 2448626` against
`dispatch_boundary_total: 1555736` — **892 890 tokens, 0.36 of the phase, carried by no boundary row**,
in the phase that is 52% of the plan's spend.
⛔ **Root shape, and it is the reason three "independent" channels failed together: all three hang off
STEP ENTRY.** They are meant to be independent evidence sources; they share one blind spot because
they share one trigger. ⭐ The envelope's own completion marker
(`(plan-marshall:execution-context.{name}) Complete`) DID observe 6 of the 7 rounds — it is the only
channel that saw the re-dispatches — but it is a *completion* witness, not a *dispatch* witness, so it
cannot substitute for the fix. ⛔ **Even it under-counted by one**: no channel inside the plan
directory can reproduce the true round count; only the session transcript can.
*Done when:* `[DISPATCH]` emission and its paired boundary-row registration move from the step-entry
path to the seam that actually opens the envelope; and the fix is validated **against a step known to
re-fire** — a single-firing fixture cannot distinguish the two and would pass over this defect.

**(N3) A round that SUPPRESSES findings it actually identified still reports `clean`.** Folded from
inbox `-004`. ⭐ OBSERVED: round 6 closed clean while holding two real contradictions in the diff's own
added lines, which it had identified and which the surface-only rule barred it from filing — a
`# pragma: no cover` on a branch a named test demonstrably covers, and a docstring claiming the
pre-fix parser told three forms apart when it told **none** apart. ⛔ **Both are exactly the defect
class this plan's sibling was written to remove: a claim that reads as measured while nothing measured
it.** They landed only because an operator was shown a gate and chose to spend a seventh round.
⛔ **"Clean" and "nothing found" are different states rendered identically, and the step reports the
wrong one.** The final `display_detail` was `"self-review clean: 59 candidates examined, no check
matched"` — true of the last round, false of the loop, and the only trace a later reader gets.
⛔ **Do NOT simply widen the surface**: that trades a false-clean for an unbounded loop, and the seven
rounds already paid are the argument against it. The head-dependence makes the incentive perverse —
filing a finding advances HEAD and re-fires the whole surface, so the rule that suppresses
out-of-surface findings is also the rule that keeps the loop short.
*Done when:* a suppressed-but-identified finding is reported in a distinct, NON-BLOCKING
`observed_out_of_surface[]` list whose count reaches the `mark-step-done` `display_detail`, so a round
that suppressed two findings can never be reportable as `self-review clean`.

**(N4) `cohort_size` is round-scoped, so a class recurring across rounds reads as a closed cohort every
time.** Folded from inbox `-007`. ⭐ OBSERVED: `contract_drift` fired in **four consecutive rounds**
for a cumulative **7** findings, while the largest figure any record publishes is **2**. Read per
round the counter is correct every time; read across the loop it is wrong every time.
⛔ **It produces exactly the indistinguishability it was added to prevent** — the field exists to
separate *a real cohort of one* from *a cohort whose other members were never looked for*, and the
seventh instance of a six-times-fired class renders identically to a genuine singleton.
⭐ **The data is already in hand and simply not read**: Step 1 already reads its own prior record and
already enumerates the prior round's Q-Gate findings, so the cumulative count is a group-by over
records the step has loaded — no new read, no new store.
*Done when:* `cohort_size_cumulative` rides beside `cohort_size` with BOTH populations named in the
rendered token; a class whose cumulative count exceeds its round count is visible in the step's
verdict; and the regression fixture **spans more than one round** — a single-round fixture cannot tell
the two apart.

**(N5) Clause-deletion fixes at one line re-flag that same line round after round.** Folded from inbox
`-008`. ⭐ OBSERVED: of 9 findings, **6 are in one file and 5 at two lines of it** — `orchestrate.md:77`
produced findings in three separate rounds, `:71` in two. **Five of the seven rounds were spent
re-flagging two lines**, each round's fix recorded as convergent and complete.
⛔ **Mechanism**: deleting the offending clause stops the sentence asserting the specific false thing
this round found, without re-deriving the sentence against the contract it describes — so whatever
else it over-claims survives, *next to a neighbourhood the fix just rewrote*, which is what re-surfaces
it. The round-5 finding names the coupling outright: the `:71` defect was "six lines above the two that
`839d106b3` fixed and missed by that commit's sweep" **and** contradicted line 77 *as rewritten by that
same commit*.
⛔ **The class-closure obligation's stated answer did NOT hold**: the sweep is bounded to every other
*surfaced* candidate, so a sibling line the surfacer never surfaced is outside it no matter how close
it sits — and same-file, same-paragraph siblings are precisely where this defect class clusters.
*Done when:* a finding whose file and line (within a small window) match a PRIOR round's finding is
marked `repeat_site: true` with the count surfaced in the step's return — a line on its third finding
is not converging and today nothing says so; and a remedy that DELETES a clause from a normative
sentence requires the remaining clauses to be re-checked against the contract source and stated as
checked. ⚠ A third option — letting the sweep re-read the enclosing paragraph of a filed finding — is a
genuine widening of the surface-only rule and **must not be taken on this run's evidence alone**;
measure first.

**(N6) `worktree-remove` reports a 60 s git timeout using the dirty-tree hint.** Folded from inbox
`-003`. ⭐ OBSERVED in source: `git_provider.py` carries `_DEFAULT_TIMEOUT_SECONDS = 60` and maps
`TimeoutExpired` to rc **124**; `git-workflow.py::cmd_worktree_remove` calls `run_git` with **no
timeout override** and branches on `rc != 0` **once**, attaching "Pass `--force` only after verifying
the worktree is clean" to rc 124, rc 127, and a genuine dirty-tree refusal alike. **The return code
that would separate them is already in hand and simply not read.**
⛔ **The failure is self-worsening**: a timeout leaves the worktree PARTIALLY removed — this run found
exactly four unstaged deletions that were the timed-out removal's own work — so the retry then reads
dirty *for a reason the first attempt caused*, and the misleading hint appears to be confirmed.
**Fired twice on this plan**, and on a checkout this size the timeout is the expected path, not an edge
case.
*Done when:* the payload branches on `rc` — 124 names a timeout, states the budget, and says plainly
that `--force` does not address it; 127 names git-not-on-PATH; anything else keeps the existing
dirty-tree hint, which is correct for the case it was written for. Consider an explicit `timeout=`
above 60 s at this call site.

⚠ **Surface additions**, declared in the same pass as the fold:
`.../skills/workflow-integration-git/scripts/git_provider.py` (N6) — `git-workflow.py` is already
declared. `phase-6-finalize/workflow/pre-submission-self-review.md` is already declared and is extended
by N3, N4 and N5.

7. **D7 — A standing completion instruction that survives a dispatch boundary**

   ⚠ **MERGED IN 2026-09-12 from `PLAN-CIS-061` (retired) D1.** On `PLAN-CIS-051` the operator's
   opening instruction — *"continue as defined to the end of finalize. DO only stop on issue."* — did
   not survive a dispatch boundary, and **six of that run's nine operator turns existed only to
   re-issue it**. Establish where such an instruction can live and make the dispatch prompt carry it.

   ⭐ **The absence is measured, not assumed** (corroborated at `28b578f1e` over a stated population):
   a content search for `standing_instruction|run_to_completion|completion_instruction` returned
   `count: 0` over 5357 files scanned, 0 unreadable, no truncation, and `manage-status/SKILL.md:73`
   lists only `change_type` / `confidence` / `domain` / `use_worktree` / `worktree_path` /
   `worktree_branch` / `session_ids`. Plan `status.json` metadata is the candidate carrier, and it
   genuinely carries nothing of the kind today.

   ⭐ This deliverable belongs beside D1–D6 because it is the **same dispatch prompt** those items make
   truthful about its own logging: the seam that emits the `[DISPATCH]` record is the seam that would
   carry the standing instruction.

8. **D8 — Raise the bar `voluntary_checkpoint` clears — the CLASSIFICATION, not the predicate**

   ⚠ **MERGED IN 2026-09-12 from `PLAN-CIS-061` D2, AND RE-SCOPED IN THE SAME ACT.** ⛔⛔ **The
   retired spec's premise is REFUTED and must not be carried forward.** It read *"`voluntary_checkpoint`
   is emitted at a site that does not consult `tasks_remaining`"*. At HEAD the emit site **does**
   consult it: `plan-marshall/workflow/execution.md:199` defines `voluntary_checkpoint` as firing when
   a non-error payload returns while pending tasks remain, and `execution.md:221-243` together with
   `phase-5-execute/SKILL.md:1173-1181` (B7) already reclassify a no-progress subclass to `error`
   using `in_progress_count` and `completed_tasks_delta`. `git log -S` dates that machinery to
   #349/#714/#730/#842 — all older than #1370 — so it predates `PLAN-CIS-051` and is not a post-hoc
   fix. ⭐ The retired spec's own verify-first clause pre-authorised exactly this re-scope, and it
   fires: **the predicate exists; what is wrong is the THRESHOLD it clears.**

   *Deliver:* a termination with `tasks_remaining > 0` and no `blocked_*` cause is a **stall**. Decide
   from the existing machinery whether the correct move is to tighten the reclassification threshold
   (B7's `in_progress_count` / `completed_tasks_delta` bar), to auto-resume rather than returning to
   the operator, or both — and record which, with the evidence. ⛔ Do NOT add a second predicate
   beside the one that already reads `tasks_remaining`; that is how a vocabulary grows two answers to
   one question, which is this epic's own recurring archetype.

   *Done when:* the run report states the threshold before and after, names the population of
   terminations it was re-derived over, and shows a fixture that classified as a clean checkpoint
   under the old bar and as a stall under the new one.

9. **D9 — Publish the stall rate as a first-class figure**

   ⚠ **MERGED IN 2026-09-12 from `PLAN-CIS-061` D3.** `analyze-logs` already partitions terminations
   by cause; surface `voluntary_checkpoint` **with `tasks_remaining > 0`** as its own count, so the
   stall rate is trackable across plans instead of re-derived by hand from one run's transcript. The
   observed shape it must make legible: `PLAN-CIS-051`'s 14-row phase-5 boundary ledger split
   `voluntary_checkpoint` 10 / `budget_yield` 3 / `clean_exit_queue_empty` 1.

   ⛔ **Surface contention, recorded rather than scheduled around.** This deliverable touches
   `manage-metrics.py`, `data-format.md` and `analyze-logs.py`, which `PLAN-CIS-050` also declares
   (`analyze-logs.py` was already this plan's read-only surface). Under `parallelization_scope = 1`
   nothing runs concurrently, so the contention is a **sequencing** constraint: whichever of the two
   lands first moves those files under the other, and the survivor is re-grounded before it is
   emitted. ⭐ This is the one contention the 2026-09-12 re-cut did NOT dissolve — `PLAN-CIS-050` is
   already at eleven deliverables, so absorbing D7–D10 there would have breached the operator's
   twelve-deliverable ceiling. The trade is recorded so the choice is visible rather than inferred.

10. **D10 — A test that pins the stall classification**

    ⚠ **MERGED IN 2026-09-12 from `PLAN-CIS-061` D4.** A termination fixture with a non-empty queue and
    no blocking cause must not classify as a clean checkpoint. ⛔ **Per the epic's standing rule the
    guard must be population-derived and publish the population it scored** — a check that can return
    "0 stalls" from an empty termination set is the vacuous-guard archetype this epic has now recorded
    at n≥6, repeatedly introduced BY a fix for it. A matched negative control is required: a genuine
    `clean_exit_queue_empty` termination must still classify clean.

## Out of scope

Each exclusion names its reason, because there is no operator in this run to ask.

- **Widening the seam-pairing detector in `test/plan-marshall/phase-6-finalize/
  test_dispatch_roster_closure.py` beyond its current one-section population**, and the two other
  test-population defects in the same file. They are gaps in a sibling 5xx plan whose subject is test
  vacuity. ⚠ **Sequencing consequence, stated in Notes:** that plan's widened detector is written to
  fail while D1's two sites are unmigrated, so it must not land before this plan. Do not pre-empt it
  by widening the detector here — two plans editing the same sweep concurrently is worse than the
  ordering.
- **Deleting or rewriting `test_finalize_dispatch_emits_one_line_per_spawn`**, the test whose comments
  claim to pin the finalize per-spawn property while passing against the very defect D1 fixes. Same
  sibling plan, same file family.
  ⛔ **Do not claim D1's landing changes whether that vacuity reproduces.** The demonstration in
  `180-finalize-dispatch-manifest-observability/gaps.md#G7` is a *deliberate* mutation of
  `phase-6-finalize/SKILL.md` applied by the tester, and what it shows is that the test **reads no
  finalize document at all** — so it reproduces whether or not D1 has landed, because D1 migrates two
  other sites and does not touch that mutation's reachability. An earlier draft of this bullet said
  the mutation stops reproducing after D1 and used it to argue an ordering; that was wrong on the
  mechanism and is withdrawn.
- **Correcting the source plans' run reports** (`report-NN.md` under
  `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/*/`). Report corrections are a documentation-truthfulness
  bucket owned by another 5xx plan, and a report is a dated record of one execution: the correct
  method is an *appended* correction note, never a rewrite, which is a different editing discipline
  from everything in this plan.
- **Consolidating the four private copies of the canonical-verify step-id prefix into one shared
  normalizer** (`manage-config/scripts/_cmd_quality_phases.py`,
  `pm-plugin-development:tools-marketplace-inventory/scripts/_dep_detection.py`,
  `manage-execution-manifest/scripts/_manifest_core.py`,
  `plan-retrospective/scripts/check-manifest-consistency.py`, plus a fifth partial copy in
  `manage-config/scripts/_config_defaults.py`). The audit measured the copies as **behaviourally in
  agreement today**, so nothing is currently wrong; the change is a cross-bundle refactor whose real
  risk is widening one consumer's accepted forms while unifying them (the four differ in what else
  they strip and which bare forms they accept), which would need each consumer's current behaviour
  pinned by test first. That is a plan of its own, and it shares no mechanism with the dispatch and
  boundary work here.
- **The `--reason` bypass on the completion gate, the unevaluable-query fail-open at the completion
  boundary, and the entry-guard/completion-guard constant split.** All three are `_cmd_lifecycle.py` /
  `_invariants.py` gaps owned by sibling 5xx plans. D3 touches the same neighbourhood, so the
  exclusion is load-bearing: changing those branches here would collide with another plan's diff.
- **Adjusting the dispatch-audit sparse-ratio threshold** after D2(a) changes `completion_count`.
  The threshold can only be judged against a real archived corpus, which lives under the git-ignored
  `.plan/` and is **not visible from this clone**. Recorded as residue instead.
- **Implementing either shape of the merge-boundary state arming (D3b), the start-marker fusion
  (D2b), or the `manage-findings` routing of reconciliation findings (D6f).** Each is an
  architectural or contract decision with a stated cost and two defensible answers; a run with no
  operator records the proposal and does not choose.

## Expected Surface

Files this plan is expected to touch. Re-derive the list against the tree you have — paths move, and
a file that is absent is a finding, not a licence to improvise.

**Bundle documents (finalize phase)**

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` — D1a
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — D1b, D5
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md` — D1c, D6d
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/adr-propose.md` — D1d
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md` — D3a
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — D2a (item 7), D2b (item 2), D6c (the 5c gate and its cause table)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md` — D6f, only if the stop condition clears
- `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` — D6b

**Bundle documents (other skills)**

- `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — D2a, D2b
- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — D4c
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md` — D6d

**Production scripts**

- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` — D2a
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py` — D2c
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py` — D2c (read; change only if the seeding belongs on the read side)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — D4a, D4b
- `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py` — D6a
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — D6e
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_decision_line_shapes.py` — D1e

**Tests**

- `test/plan-marshall/manage-status/test_mark_step_completion_emission.py` — D2a
- `test/plan-marshall/manage-status/test_manage_status_metadata.py` — D2c
- `test/plan-marshall/workflow-integration-git/test_worktree_rebase_executor_refresh.py` — D4a, D4b
- `test/plan-marshall/execute-task/test_inject_project_dir.py` — D6a
- `test/plan-marshall/plan-marshall/` and `test/plan-marshall/manage-status/` — new tests for D3a and D6d/D6e; place each beside the existing tests for the handler it drives rather than inventing a new directory


**Added by the 2026-08-31 inbox drain (PLAN-CIS-051 / PR #1370).**

Seven paths this plan did not previously declare, each named by the folded signal that adds it. The
same-act rule applies: these landed in the SAME edit that appended § Folded-in signals below.

- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py`,
  `.../scripts/_freshness_crosscheck.py`, `.../scripts/manage-tasks.py` and `.../SKILL.md` — F-001(1),
  the canonical-blind freshness gate that guards the 5→6 transition, and F-001(obs) the missing
  step-retarget verb.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py`,
  `.../scripts/retro_sections.py` and `.../references/report-structure.md` — F-007 and F-001(4), the
  Phase Dispatch Boundaries trigger resolved against a key no producer publishes.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` — F-007, read
  only: it is the sole producer of `dispatch_boundaries` and writes it NESTED inside the
  `log-analysis` fragment. ⚠ This file is also declared by `PLAN-CIS-050`; the two plans must not run
  concurrently, and this row is recorded so the disjointness gate can see the contention.

**Added by the 2026-09-12 re-cut (absorbing `PLAN-CIS-061`, D7–D10).**

The retired spec's surface was itself derived from a `grep -rln voluntary_checkpoint` sweep over
`marketplace/bundles/` and `.claude/` at `7845a4b9a`; these are the files it expected to CHANGE.

- `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — **D7, D8**: the dispatch loop,
  its termination contract, and the B7 reclassification at `:1173-1181` D8 re-scopes to.
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — **D7, D8**: the
  `voluntary_checkpoint` definition at `:199` and the no-progress reclassification at `:221-243`.
- `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md` — **D8**:
  the resume path a stall would take, if the auto-resume branch is chosen.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — **D9**:
  `record-dispatch-boundary` and the termination-cause vocabulary. ⛔ Contended with `PLAN-CIS-050`.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — **D9**.
  ⛔ Contended with `PLAN-CIS-050`.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` — **D9**: the
  cause-class partition that already computes the counts. ⭐ Already declared above as READ-ONLY for
  D1–D6; **the merge promotes it to a WRITE surface**, which is a real change to this plan's footprint
  and is stated here rather than left to be discovered. ⛔ Contended with `PLAN-CIS-050`.
- `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — **D7**, only if the standing
  instruction lands in plan metadata. ⭐ Already declared above for D2.
- `test/plan-marshall/manage-metrics/` and `test/plan-marshall/plan-retrospective/` — **D10**, the
  population-derived stall-classification guard and its matched negative control.

⛔ **The four-file contention with `PLAN-CIS-050` (`manage-metrics.py`, `data-format.md`,
`analyze-logs.py`, `phase-5-execute/SKILL.md`) is REAL and is NOT dissolved by this re-cut.** It is a
sequencing constraint under `parallelization_scope = 1`, not a concurrency block: whichever plan lands
first moves those files under the other, and the survivor is re-grounded before emit.

## Claim Labels
- verdict: contradicted | checked_at: 7a028157eab86d5c5e9c8ee181671c6093ac5963 | by: code-intelligence-substrate/cleanup | rescoped: yes | evidence: RE-GROUNDED 2026-09-15 at HEAD 7a028157e (previous stamp 53ab7dd2e). SCOPE STATED: this spec has the HEAVIEST exposure of the three staged - 13 of its 37 declared surface entries were touched by the 334 files changed since the previous stamp, including pre-submission-self-review.md and phase-6-finalize/SKILL.md, both moved by #1488 (correct declared surfaces and self-review gate), plus manage-status/SKILL.md, _status_query.py, execution.md, archive-plan.md, record-metrics.md, lessons-capture.md, automatic-review/SKILL.md, claude_runtime.py and _orchestrator_inbox.py. The re-derivation targeted the load-bearing claims on those files; claims on the other 24 entries retain their previous verdicts and were NOT re-executed. FINDINGS: (1) ROW 17 RE-CONFIRMED LIVE ON A FILE THAT MOVED, which is the whole point of re-grounding a spec after a landing - phase-6-finalize/SKILL.md item 5c (:1096) still gates the record-dispatch-boundary call on the step having did NOT time out, while the cause table at :1105 still defines blocked_session_restart to INCLUDE the per-agent timeout budget firing. So a timed-out finalize step still writes no boundary row at all, and the two statements still contradict each other inside one document. (2) D1 sub-item (e) was re-checked and is UNCHANGED at HEAD: _decision_line_shapes.py's module docstring still presents unresolved_ask_provider_drop, scope_gated_finalize, ceremony_finalize_selection and the *_inactive pre-filter line as the closed set of gates carrying no [STATUS] tag. That file was NOT in the changed set, so this is a re-read rather than a re-derivation. (3) No evidence was found that #1488 regressed the already-struck D1(a)-(d): the skill-wide exit condition still holds - a grep for the hand-written --message [DISPATCH] form over skills/phase-6-finalize/ returns nothing.

Every premise below is a claim about the tree, carried from a ground-truth audit that was then
**adversarially re-reviewed**. Where the two disagree, the review wins and this plan follows the
review — the places where that changed the prescribed action are marked ⚠ in the deliverables. Every
artifact named here is git-reachable from a fresh clone; none is under `.plan/`.

**Failure modes the source audits were found to have, and how this plan handles them.** (i) A
proposed fix that breaks the suite — where a remedy was measured unsafe, this plan says so inline
(D3a's exit-code prohibition, D4a's byte-comparison prohibition, D6d's payload-scan prohibition).
(ii) An unsatisfiable *Done when* — several source gaps had one; each is replaced above with a
condition a single run can settle, and the replacement is noted. (iii) A measurement that was a
timing artifact — **none of the claims in this bucket rests on a duration or a throughput figure**, so
no lead here needs re-measurement for that reason. Counts still do, per the standing rule.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `finalize-step-simplify.md` issues a bare `effort resolve-target --phase phase-6-finalize` and spawns a `Task:` with no dispatch record on either surface | OBSERVED | The file itself: `grep -n 'resolve-target\|Task: '` returns exactly the bare resolve and the spawn, and no `--message "[DISPATCH]"` anywhere in it |
| `pre-submission-self-review.md` issues a bare resolve and then hand-writes the `[DISPATCH]` line the standard forbids | OBSERVED | The file itself, plus the prohibition stated verbatim in `ref-workflow-architecture/standards/dispatch-logging.md` § Emission contract and restated in `phase-6-finalize/SKILL.md` |
| `lessons-capture.md` and `adr-propose.md` each carry a section asserting the dispatcher emits the line at the call site, with a hand-written `manage-logging work` command | OBSERVED | Both files; contradicted by `dispatch-logging.md` and by the migrated sites in `phase-6-finalize/SKILL.md` |
| The `_decision_line_shapes` scope comment's four-item enumeration is not the set, and its `[STATUS]`-tag claim is falsified by at least one own-shape drop line | OBSERVED | `_decision_line_shapes.py` header comment against every own-shape drop line in `manage-execution-manifest.py` — enumerate them and check each |
| `_emit_completion_marker` inspects no `outcome`, so a `loop_back` write emits `Completed step: X` | OBSERVED (executed) | Drive `cmd_mark_step_done` with `phase='6-finalize'`, `outcome='loop_back'` and read the work log back — the audit's re-run returned exactly one `Completed step:` line |
| The `[STEP] … Executing step:` start marker is emitted only by a prose instruction, not by any shared write | OBSERVED | `phase-6-finalize/SKILL.md` item 2, and the absence of any start-marker emission in `_cmd_mark_step.py` — verify the absence by reading the module, not by grepping for a name |
| A pre-list plan's legacy `session_id` becomes unreachable once `session_ids` exists | OBSERVED | `test/plan-marshall/manage-status/test_manage_status_metadata.py` — the existing resume test asserts the post-resume list holds only the new id while the retired scalar still holds the original |
| `manage-status archive` emits `blocking_findings_present` and exits 0, and `archive-plan.md` § Archive parses nothing before logging "Plan archived" | OBSERVED (executed) | Drive `main()` in-process for `archive` with a pending actionable finding; read `archive-plan.md` § Archive for the unconditional log. ⚠ Exit 0 is contract-conformant per `output-contract.md`; the defect is the unparsed status |
| The state-armed boundary is the completion boundary (`archive-plan`, `order: 1100`) while the merge happens in `branch-cleanup` (`order: 70`), gated only by a workflow-doc call | OBSERVED | The two step documents' frontmatter `order:` values, and the pre-merge gate paragraph in `branch-cleanup.md` |
| The executor-refresh verdict is a presence check that a real worktree always satisfies, and the generator exits 0 on `status: error` | OBSERVED (measured) | `git-workflow.py::_refresh_worktree_executor` + `_executor_slot.py::executor_landed`; `prepare_execute.py`'s generate-and-self-heal paths; `generate_executor.py`'s unconditional `return 0`. The audit reproduced it by seeding the fixture slot and re-running the landed-check scenario |
| `_run_generate_executor` catches only `FileNotFoundError` and `TimeoutExpired`, against a docstring promising it never raises | OBSERVED | The `except` clauses in `git-workflow.py`, and the two docstrings |
| An escaping `OSError` from that seam turns a successful rebase into a caller-visible crash | HYPOTHESIS | D4b's own new test: monkeypatch `git_workflow.subprocess.run` to raise `PermissionError` and drive `cmd_worktree_rebase_to` over a rebase that replayed commits. It must be **red before** the widening — if it is green, the escape claim is refuted and D4b reduces to a docstring correction; report that outcome |
| `automatic-review/SKILL.md`'s recovery path parses none of the three executor fields, while both sibling callers do | OBSERVED | The three step documents, and the `worktree-handling.md` roster naming all three callers |
| Roughly half the Bucket B whitelist is inert — two entries name no on-disk script, and the `run` gate excludes every notation that dispatches a verb directly | OBSERVED | `inject_project_dir.py`'s frozenset and its exact-match comparison; a directory listing of `workflow-integration-git/scripts/` and `workflow-pr-doctor/scripts/`; the invocation forms in each target skill's SKILL.md. **Re-derive the fraction** |
| `test_inject_project_dir.py` duplicates the same wrong whitelist and asserts injection through a synthetic `run` command no production caller writes | OBSERVED | The test file |
| `manage-references get --field modified_files` returns `field_not_found` rather than an empty list, and no Error Handling row in the housekeeping step covers it | HYPOTHESIS | `_references_crud.cmd_get`'s missing-field return, driven directly over a references document with no `modified_files` key; and the step's own Error Handling table. Settle by executing the handler — the read has not been executed against a live plan, and this clone has none |
| The finalize 5c gate excludes the timeout sub-case of a cause whose definition names it, and one table value is missing from the invocation's value list | OBSERVED | The gate sentence, the cause table, and the brace-form value list in `phase-6-finalize/SKILL.md`, read together |
| A timed-out finalize step therefore writes no boundary row at all | HYPOTHESIS | A cold read of `phase-6-finalize/SKILL.md` items 5, 5b and 5c end to end, asked "which row does a timed-out Task-agent step write?" — this is a claim about prose, so a reader is the instrument. If the cold read finds a path that writes one, drop the claim and keep only the gate/table reconciliation |
| Exactly one bundle write site can carry plan-directed inbox content, and nothing supplies `--target-plan` | OBSERVED | Re-enumerate every `orchestrator inbox write` block in `marketplace/bundles/` and classify each by `--kind`; then read the argument declaration (`required=False, default=None`) and confirm the verb has no programmatic caller. ⚠ This is an asserted absence — verify it as you would a presence |
| An unreadable epic queue silently disables the deliverability guard with no signal on the success TOON | OBSERVED | `_orchestrator_inbox.py`'s running-plan reader, its intentional-fail-open comment, and the envelope standard's row saying the write proceeds |
| `reconcile-ledgers` has zero workflow call sites | OBSERVED | A whole-tree search for the verb name excluding caches: hits should be its own SKILL.md, its own script, its unit test, and the generated executor's surface registry — nothing in a workflow document. ⚠ Asserted absence: re-derive it, and if a call site now exists, D6f is already discharged |
| The reconciliation row-pairing routine raises `RecursionError` near ~1 000 same-timestamp rows per side | HYPOTHESIS (reproduced twice by the source audits, not by this plan) | D6f's own stop-condition check: drive the pairing routine over ~1 200 identical-timestamp rows per side and record whether it raises. This check **gates** D6f — it is not optional |

| **[merged from `PLAN-CIS-061`]** Phase-5 terminations on `PLAN-CIS-051` were `voluntary_checkpoint` 10 / `budget_yield` 3 / `clean_exit_queue_empty` 1 across a 14-row boundary ledger | CORROBORATED at `28b578f1e` | Verbatim at `inbox/archive/detector-and-auditor-integrity/detector-and-auditor-integrity-011.md:18-24`. D9 |
| **[merged from `PLAN-CIS-061`]** Six of nine operator turns on that run existed only to restart a halted dispatch | CORROBORATED at `28b578f1e`, from an INDEPENDENT source (the transcript, not the ledger) | Quoted verbatim at the same message, `:28-38`, together with the operator's first-message instruction. D7 |
| **[merged from `PLAN-CIS-061`]** No plan-state field carries a standing completion instruction across a dispatch | CORROBORATED at `28b578f1e` over a STATED population | Content search for `standing_instruction\|run_to_completion\|completion_instruction` → `count: 0` over 5357 files, 0 unreadable, no truncation; `manage-status/SKILL.md:73` lists seven metadata keys and none of them. D7 |
| **[merged from `PLAN-CIS-061`]** ~~`voluntary_checkpoint` is emitted at a site that does not consult `tasks_remaining`~~ | **REFUTED-AND-ABSORBED 2026-09-12** — the emit site DOES consult it, so D8 is re-scoped from the predicate to the THRESHOLD | `execution.md:199` (the definition), `execution.md:221-243` + `phase-5-execute/SKILL.md:1173-1181` (the B7 no-progress reclassification on `in_progress_count` / `completed_tasks_delta`); `git log -S` dates it to #349/#714/#730/#842, all older than #1370. The retired spec's verify-first clause pre-authorised this narrowing |
| **[absorbed 2026-09-12]** ~~The finalize dispatch-seam migration is outstanding (D1a–D1d)~~ | **REFUTED — STRUCK at HEAD `53ab7dd2e`** | `grep -rn -- '--message "[DISPATCH]'` over `skills/phase-6-finalize/` returns nothing — the deliverable's own skill-wide exit condition. `finalize-step-simplify.md:110` and `pre-submission-self-review.md:197` carry the full seam form and both say "Do NOT hand-write a separate `[DISPATCH]` line"; `lessons-capture.md:54` and `adr-propose.md:42` state the seam emits per firing, with no `manage-logging work` block. D1 survives as (e) only |
| **[still live, half-resolved]** Row 16 is COMPOUND and only half closed: the brace-form invocation list now carries all five table causes, but `SKILL.md` item 5c still gates on did-NOT-time-out while the cause table defines `blocked_session_restart` to include the timeout-budget firing | PARTLY CORROBORATED — the surviving half is row 17: **a timed-out finalize step still writes no boundary row at all** | Re-derive both halves at outline and fix only the half that is still open; do not re-close the invocation list |

## Verification

Beyond each deliverable's own *Done when*:

**The suite.** ⚠ **CORRECTED 2026-08-24** — this read "run the full Python verify through the direct
wrapper (`./pw verify`) per the lane's build gate, gated on the lane's git-derived Python-change
check". Neither the direct wrapper nor the git-derived gate exists here: resolve the command through
the executor and run it unconditionally —
`python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"`
(Bash timeout ≥ 600000 ms), reading the result TOON `status`/`errors[]` because **the wrapper exits 0
even on failure**. Report the outcome verbatim, and
report the module-scoped runs for every test file this plan touches. A green suite is necessary and
not sufficient — several of the defects here are *guarded by tests that pass against the defect*, so
"the suite is green" proves nothing about them on its own.

**Red-before-green, named.** Six of this plan's tests must be red against the current tree and green
after: D2a's `loop_back` case, D2c's legacy-scalar append, D3a's CLI-surface refusal (only if no
pre-existing test covers that surface — establish which, first), D4a's seeded-slot verdict, D4b's
raising-seam non-fatality, and D6a's per-notation injection through the documented subcommand. For
each, report the failure message observed **before** the fix, not merely "it now passes". A test that
was green before the fix is a finding: it means the defect is elsewhere or already closed, and the
plan should say so rather than claim a fix.

**Cold reads — four, dispatched independently, each reported with the reading it took.** Four
deliverables are text whose entire value is what a later reader *does* with it; "implemented as
specified" cannot verify them. Give each reader only the named text, with no framing from this plan:

1. **D1 (c) and (d), plus (a) and (b)** — ask: *"When this step dispatches, who writes the
   `[DISPATCH]` work-log line, and what must this document's own commands do about it?"* The
   required reading is **the resolve seam writes it; this document hand-writes nothing.** Any answer
   naming a `manage-logging work` command is a failed wording, however complete the diff looks.
2. **D3a** — give the reader the amended `archive-plan.md` § Archive and ask: *"The archive call
   returns `status: error, error: blocking_findings_present`. What do you do next?"* The required
   reading is **stop; do not log the archive; do not leave the step recorded done.** An answer that
   logs and continues means the branch is present but unreadable.
3. **D5** — give the reader Steps 1–4 of `pre-submission-self-review.md` **without** the §
   "Round-loop termination" section, and ask what a non-clean round owes and what to do when the
   round's anchor no longer resolves. The required reading names the self-seeding classification, the
   WARNING log, and the skip-resolution branch. This is the whole point of D5: the defect is that the
   obligations live past where the executor stops reading.
4. **D2b** — give the reader `phase-6-finalize/SKILL.md` item 2 and `manage-status/SKILL.md`
   § "Fused completion emission" and ask whether the start and completion markers are produced the
   same way. The required reading is **no — the asymmetry is deliberate and stated**, not *"both are
   fused"*. A reader who cannot tell means the declined-symmetry rationale failed and should be
   rewritten, not merely lengthened.

**Proposal completeness.** Three proposals are owed: the merge-boundary state arming (D3b), the
start-marker fusion (D2b), and the `manage-findings` routing of reconciliation findings (D6f) — plus
a fourth, the reconcile-ledgers wiring itself, **if and only if** its stop condition fired. Each must
appear in the run report **and** in the pull request body under a single `## Operator decision
required` heading, because the plan directory is deleted when the orchestrator collects this epic and
the report goes with it. A proposal that exists only in the plan directory is a proposal that will not
survive to be decided.

**Coverage against the bucket.** Confirm at the end that every gap in § Gap coverage is either
discharged by a landed deliverable or named in § Out of scope, and report any that is neither. That
check is the plan's own anti-drift guard: with no operator watching, an unaccounted gap is invisible.

## Notes

**Where the evidence lives.** Every defect above was filed by a ground-truth audit of a landed plan
in this epic, and each audit was then adversarially re-reviewed. The gap entries are git-tracked at
`.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/{plan}/gaps.md` with the supporting analysis in
`verification.md` beside them, and § Gap coverage below cites each by path and gap id. **Treat those
files as corroboration, not as required reading** — a landed cloud plan's directory is deleted when
the orchestrator collects it, so some may be gone by the time this runs. Everything a run needs is
restated in this plan on purpose.

**Machine-local state this run must not look for.** The orchestrator ledger, the plan specs, the
landing records, the archived-run corpus, and the generated executor all live under `.plan/`, which
is git-ignored and therefore **absent from this clone**. Two deliverables name it only to say so:
D2a's sparse-ratio re-read and D6b's live-plan read both require a corpus that is not here, and both
are authored to be settled by driving the handler directly instead.

**Sequencing against the sibling 5xx plans.** Four constraints, all real:

1. **This plan SHOULD land before the test-integrity plan — a preference, not a block.** That plan
   (`550-test-suite-anti-vacuity`) widens the finalize seam-pairing sweep to every `.md` under
   `skills/phase-6-finalize/`, which is red while D1's two sites are unmigrated. Landing D1 first
   means the widened sweep lands green in one step.
   ⛔ **It is NOT a prerequisite, and must not be reported as one.** `550` § Notes states it is
   *"order-independent by construction"* and *"must not be read as blocked on any sibling"*: the six
   items whose production fix belongs elsewhere — this one among them — run through its D1
   prerequisite probe, which holds the test with its body recorded when the sibling has not landed
   and lands it green when it has. So `550` running first does **not** put a red detector on `main`.
   An earlier draft of this entry claimed it did, and claimed the vacuous test only looks vacuous
   because D1's defect exists; both are withdrawn — see the § Out of scope entry for that test.
2. **D4b's raising-seam test overlaps a gap in that same plan.** It is required here by D4b's own
   *Done when*, so land it here and say so in the report; the sibling plan should find it already
   present rather than author a second.
3. **Do not touch `_cmd_lifecycle.py` / `_invariants.py` branches owned elsewhere** — the `--reason`
   bypass, the unevaluable-query fail-open, and the entry/completion constant split are three gaps in
   two other 5xx plans, in files D3 works next to. The § Out of scope entry is the boundary.
4. **D6c and D6f each stop short of an arm owned by the measurement/cost plan.** D6c takes the
   cause-redefinition arm rather than the record-a-row-on-timeout arm because the latter is coupled to
   a fabricated-zero defect that plan owns; D6f is stop-condition gated on a recursion defect that
   plan owns. Both are authored to complete without it, and to report the arm not taken.

Otherwise this plan is independent: it shares no file with the documentation-truthfulness bucket's
report corrections, and its bundle edits are in step documents the other plans do not open — with one
exception worth watching in review, `phase-6-finalize/SKILL.md`, which D2 and D6c both edit here in
different sections and which two sibling plans may also touch. Keep those edits section-local and
review the merge-time diff of that file specifically.

**A note on effort shape.** Fourteen of this plan's twenty-three in-scope items are documentation or
comment edits to shipped bundle text; six are small production changes with a named test each; three
are proposals that ship no code. The plan is wide rather than deep on purpose — the mechanism is
shared even where the files are not.

## Gap coverage

Every gap in this plan's bucket, mapped to the deliverable that discharges it. Cited as
`{source-plan}/gaps.md#{id}` under `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/`.

| Gap | Sev | Deliverable |
|---|---|---|
| `180-finalize-dispatch-manifest-observability/gaps.md#G1` | high | D1a |
| `180-finalize-dispatch-manifest-observability/gaps.md#G2` | high | D1b |
| `180-finalize-dispatch-manifest-observability/gaps.md#G3` | medium | D1c |
| `180-finalize-dispatch-manifest-observability/gaps.md#G4` | medium | D1d |
| `290-auditor-detector-integrity/gaps.md#G4` | low | D1e |
| `180-finalize-dispatch-manifest-observability/gaps.md#G8` | high | D2a |
| `180-finalize-dispatch-manifest-observability/gaps.md#G6` | medium | D2b (documented-asymmetry arm + fusion proposal) |
| `330-retrospective-report-sections-structurally-dead/gaps.md#G13` | low | D2c |
| `110-blocking-boundary-arms-on-a-call-not-a-state/gaps.md#G1` | high | D3a |
| `110-blocking-boundary-arms-on-a-call-not-a-state/gaps.md#G2` | medium | D3b (proposal only — architectural choice) |
| `190-frozen-manifest-diverges-from-live-config/gaps.md#G15` | high | D4a |
| `190-frozen-manifest-diverges-from-live-config/gaps.md#G4` | medium | D4b |
| `190-frozen-manifest-diverges-from-live-config/gaps.md#G6` | low | D4c |
| `100-self-review-surfacing-integrity/gaps.md#G2` | medium | D5a |
| `100-self-review-surfacing-integrity/gaps.md#G3` | medium | D5b |
| `110-blocking-boundary-arms-on-a-call-not-a-state/gaps.md#G5` | medium | D5c |
| `110-blocking-boundary-arms-on-a-call-not-a-state/gaps.md#G14` | low | D5d |
| `230-validate-precision/gaps.md#G5` | high | D6a |
| `050-post-run-band-contract-and-ordering-residue/gaps.md#G5` | medium | D6b |
| `070-dispatch-spend-on-dispatches-that-produced-nothing/gaps.md#G3` | medium | D6c (redefinition arm) |
| `100-self-review-surfacing-integrity/gaps.md#G1` | medium | D6d |
| `100-self-review-surfacing-integrity/gaps.md#G9` | low | D6e |
| `340-token-ledgers-disagree-and-the-smallest-is-named-actual/gaps.md#G4` | medium | D6f (stop-condition gated) |
| `320-manifest-cross-check-discards-production-tree/gaps.md#G11` | low | **Out of scope** — see § Out of scope, "Consolidating the four private copies…" |

Twenty-four gaps: six high, twelve medium, six low. Twenty-three are carried by a deliverable; one
low gap is excluded with its reason. All six high gaps are carried (D1a, D1b, D2a, D3a, D4a, D6a).

## Folded-in signals — 2026-08-31 inbox drain (PLAN-CIS-051 / PR #1370)

Three signals folded here. All three are this plan's own subject — a boundary that is supposed to
block or to record, and does neither audibly.

**F-001(1) — `pre-commit-verify-freshness` is canonical-blind, and it guards the 5→6 transition**
(`manage-tasks`, qgate `3e7381`, severity **error**). Observed live at worktree_sha
`0b31f4466ee1dfd0f6f6159a75345c9dbda0ef73e2300eeb151ebacf77f36e61`: a `module-tests plan-marshall`
run against that exact tree returned `status: timeout` / `exit_code: -1` after 722s, producing **no
suite verdict**. The gate nonetheless reported `status: fresh`, matching the **test-compile** success
row from the same sha, and stated *"Gate permitted on corroborated evidence"*.
⛔⛔ **The mechanism: every pyproject canonical shares ONE notation
(`plan-marshall:build-pyproject:pyproject_build`), so a compile-only run satisfies a gate a reader
takes as "this tree was verified end to end".** It can admit an unverified tree to finalize — and it
is the gate the plan that found it was itself relying on.
*Candidate remedy:* record the canonical COMMAND on the `kind=build` ledger row and require a row
whose canonical actually exercises tests — or publish which canonical corroborated the verdict so the
caller can judge.

**F-001(4) / F-007 — the Phase Dispatch Boundaries section is triggered on a key no producer
publishes at bundle top level** (`plan-retrospective`, warning; filed twice, folded once).
`should_emit` resolves the trigger with `fragments.get('dispatch_boundaries')` — a TOP-LEVEL lookup —
while the only producer, `analyze-logs`, nests that block inside the `log-analysis` fragment. No
bundle key exists, `_dispatch_boundaries_has_present_phase` receives `None`, and the section is
omitted on a run whose fragment carried three phases all `present: true` holding 33 rows with
termination causes, token totals, tool uses and durations. Because the inspected fragment is also
absent, `_renders_usable_body` is False and the section takes `omitted` rather than `dropped` — **the
loudness machinery is intact and looking at the wrong object.**
⛔ **What was lost is not incidental: the omitted table is the one carrying the dispatch-termination
distribution — 10 of 14 phase-5 terminations `voluntary_checkpoint`, the finding that explains six of
the nine operator turns. The single most behaviourally significant table in the retrospective was
dropped and reported as "nothing to lose".**
A content sweep for `dispatch_boundaries` returns 38 hits across 19 files with exactly one producer.
*Two options, recorded not decided* — **A:** register `dispatch_boundaries` as a top-level aspect so
the dedicated table renders, at the cost of publishing the same data twice; **B:** delete the row and
`report-structure.md` item 6. **The originating plan recommended A**, because the per-phase table is
the only place the terminal-error versus retryable dispatch-spend split appears as a table and the
duplication is bounded to one fragment.
*Rule:* a trigger key must be resolved against the shape the producer actually writes. A structural
test that registers the REAL producer output and asserts the section appears in `sections_written`
would have caught this; a test that hand-builds a top-level key cannot.

**F-001(obs) — `manage-tasks` has no verb to retarget a step, and `finalize-step` closes a task
before its verification runs.** `update-step` changes intent only, so a step whose declared target
turns out to be the wrong file can only be recorded as diverged, never corrected. Separately, on the
last step `finalize-step` marks the task `done`, which auto-closed tasks 11 and 12 while their
`module-tests` gate was unrun — **the `module_testing` profile forbids exactly that, so the seam and
the profile disagree.** Both are boundary-observability defects in this plan's sense: a step's real
state and its recorded state diverge with nothing saying so.
