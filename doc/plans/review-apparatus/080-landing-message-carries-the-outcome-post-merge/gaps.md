# Gaps — 080-landing-message-carries-the-outcome-post-merge

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis. Eleven entries: one blocker, five major, five minor.

## G1 — Stop emitting a landing message for a run whose merge did not land

- **Severity:** blocker
- **Kind:** unsound-refutation (and the underlying bug)
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1756-1763`
    (Branch C), `:1765-1772` (Branch D), `:1790-1799` (Branch F), `:1068` (the loop-continues admission)
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:48`
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:720`, `:37`,
    `:1057`, `:592`
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md:45`
- **Evidence:** `branch-cleanup.md:1696` states *"each of the six `--outcome done` call sites below
  (**Branches A through F**)"*, and all six code blocks carry `--outcome done` (lines 1720, 1751, 1760,
  1769, 1782, 1796). Only Branches A and E record `merge_mechanism`, which `:1702` says is recorded iff
  *"the merge actually **landed** and was corroborated"*. Of the four that do not merge, three are the
  load-bearing ones: Branch C is *"declined by user… Nothing was rebased, merged, or cleaned up"*;
  Branch D is *"no PR found… exits before the rebase and before any merge"*; Branch F is *"enqueued,
  merge not yet landed… It records **no `merge_mechanism`**, because no merge landed"*. (The fourth,
  Branch B, is local-only mode, where *"PR creation and merging are handled outside this workflow"*
  (`:1594`) — `pr` and `merge_state` are `n/a` by design there, so its defect is the prose one in G2, not
  this one.) Because the step records a terminal `done`, the dispatch loop advances: the only per-outcome
  branching in the loop is the resumable re-entry check, whose general rule is *"IF outcome == "done":
  SKIP this step (continue to next iteration)"* (`SKILL.md:720`) — a skip of one step, never a stop — and
  `SKILL.md:37` closes the set with *"Never skip a step in the manifest list based on PR state, CI state,
  or earlier step outcomes. The ONLY valid skip condition is the resumable re-entry check."* The two
  timeout paths continue as well (`SKILL.md:1057`, `:592`). The one outcome that *does* divert the
  pipeline is `loop_back` (`SKILL.md:696`, `:722`), and none of Branches C / D / F records it. The loop
  therefore reaches `emit-landing` at `order: 1000`, which states *"the emission is unconditional when the
  step runs"* (`emit-landing.md:48`). Its only skip is the Step 0 non-orchestrated guard (`:100-121`); a
  grep of `emit-landing.md` for `supersede|inbox write|existing|idempot|second landing|already` returns
  exactly three lines — the `inbox write` call (`:204`), the error-handling row (`:236`), and one
  incidental *"already-resolved verdict"* phrase (`:68`) — no merge-state gate. `branch-cleanup` is inline
  (`dispatch-inline-split.md:45`), so the post-dispatch completion guard that halts on a missing record
  (`SKILL.md:1136`) never applies to it. **The document states the mechanism itself**:
  `branch-cleanup.md:1068` warns that settling a blocked path with a terminal `done` *"lets the FOR loop
  continue through to `archive-plan` — archiving the plan with the PR unmerged, the worktree unremoved,
  and the branch undeleted."* Confirmed by reading all six branches at both `6b923309` and HEAD.
- **Impact:** The report closed plan 080 partly on the claim *"a finalize that halts pre-merge never
  reaches order 991, so it emits **no** landing rather than a false one."* That claim is false. On the
  three non-merging branches the epic inbox receives a `kind: landing` message for a plan that did not
  land, and the drain's per-kind routing table sends every `kind: landing` to the full-ship branch
  (`plan-orchestrator/workflow/analyze.md:74`, *"Step 4 (full ship — landing report + full
  reconciliation)"*) — the wrong branch for a run that never merged. What stands between that and a false
  `shipped` stamp is a **prose obligation**, not a mechanism: `analyze.md:95` requires that the PR number,
  merge state and deliverable set be corroborated against git and the CI abstraction before the
  `queue --transition … --status shipped` call, and that obligation is pinned by
  `test/plan-marshall/plan-orchestrator/test_inbox_drain_contract.py:227-240`. So the harm is not an
  automatic false ledger write; it is that the channel emits a landing-shaped message for a non-landing,
  and the only guard is exactly the corroboration duty the plan's out-of-scope section says an enriched
  message must not make *more tempting to skip*. Compounding it, `archive-plan` (`order: 1100`) carries a
  refuse-to-archive gate for foreign deliverables (`archive-plan.md:38`) but none for the host PR's merge
  state, so the same run archives the plan with its PR unmerged.
- **Task:** Gate the landing's CLAIM on a positively-substantiated merge. Read `branch-cleanup`'s
  recorded facts and, when `merge_mechanism` is absent, emit the D1 never-merges message — a distinct,
  explicitly non-landing shape — instead of the landing. ⛔ **Do not implement this as a step skip**:
  `SKILL.md:37` states *"Never skip a step in the manifest list based on PR state, CI state, or earlier
  step outcomes. The ONLY valid skip condition is the resumable re-entry check"*, so the "emit no
  message" arm is barred by the dispatcher contract and the remedy must change what is emitted, not
  whether the step runs. State the failure mode of the arm not chosen, as D1 required.
- **Done when:** A run taking `branch-cleanup` Branch C, D, or F produces no message whose payload or
  prose asserts a landing, and the behaviour is pinned by a test that fails against the current
  unconditional emission.
- **Suggested grouping:** `phase-6-finalize` / landing emission

## G2 — Make the landing's prose claim conditional on `merge_state`

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:175`,
  `:169-186` (the worked example block)
- **Evidence:** The only worked example of the landing body is *"**An optional one-line narrative
  headline** under a `## What landed` heading — e.g. `{plan_id} shipped as {pr} ({merge_state}).`"* The
  heading and the verb *shipped* are fixed; the only variable is the parenthesised `merge_state`. The
  plan's ⛔ observation 1 states the remedy explicitly: *"**Appending a correct `outcome:` field beside a
  false sentence leaves the false sentence there.** The fix must change the message's **claim**, not only
  append an outcome."* The template is labelled *optional* and *e.g.*, which softens it to guidance
  rather than a mandate — but it is the only body guidance the producer gives, and the worked example
  block shows only the merged case.
- **Impact:** Even once G1 is fixed for the non-merging branches, any reader or drain that reads the
  narrative half rather than the fenced facts block sees a landing assertion. On a Branch F run today the
  two halves of one message contradict each other, and the prose half is the one a human reads first. The
  local-only lane (Branch B) is affected by this entry rather than by G1: its facts are honestly `n/a`,
  but the headline renders `shipped as n/a (n/a)`.
- **Task:** Replace the single worked headline with a merge-state-conditioned pair (or a table): a
  landing-asserting form usable only when a merge is substantiated, and a non-landing form for every other
  state — including the local-only `n/a` case. Keep the claim labelled as the plan's own report, per the
  plan's out-of-scope constraint.
- **Done when:** `emit-landing.md` contains no unconditional landing-asserting headline template, and a
  worked example exists for the non-merged case.
- **Suggested grouping:** `phase-6-finalize` / landing emission

## G3 — Guarantee one landing per plan, not merely one per finalize run

- **Severity:** major
- **Kind:** incomplete
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:890-982`
    (`cmd_inbox_write`), `:721-749` (`allocate_message_path`)
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:201`
  - `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md:97`
- **Evidence:** The invariant every source states is scoped per **run** — `inbox-envelope.md:97`,
  *"Exactly one per orchestrated finalize run, emitted unconditionally by the `emit-landing` terminal
  step"*; `emit-landing.md:201`, *"Exactly ONE `kind: landing` message per orchestrated finalize run"*.
  The defect the plan reported was three landings for one **plan**, across successive outcomes, and its
  D3 says so: *"Delaying the message until post-merge is necessary but NOT sufficient — a run that
  believes it finished three times still emits three."* `cmd_inbox_write` validates slug, sender id,
  sender type, kind, epic existence, target-plan deliverability and payload non-emptiness, and never
  checks for an existing landing from the same sender; `allocate_message_path` takes the next free
  sequence via an exclusive create. Confirmed by execution: two successive `--kind landing` writes from
  `sender_id=plan-080` both returned `status: success`, allocating `plan-080-001.md` and
  `plan-080-002.md`. `cmd_inbox_supersede` exists (`_orchestrator_inbox.py:1516`, added by PR #1198) but
  is a manual verb — `grep -n "supersede"` over `emit-landing.md` returns nothing. No test asserts the
  uniqueness either: `grep -rn "landing"` over `test_inbox_channel_contract.py` and
  `test_inbox_message_state.py` returns only ordering, enumeration and state-field cases, and the channel
  contract's own docstring (`:11`) describes *"a second write landing at"* the next sequence as expected
  behaviour.
- **Impact:** Two landings from one plan both queue as live, both validate, and both reach the drain with
  nothing marking either as superseded — the append-only invariant then guarantees the stale one survives.
  A drain consuming the earlier one reconciles against a superseded outcome. Note the scope of the live
  exposure: within one finalize entry `emit-landing` runs once, and at re-entry the resumable re-entry
  check skips an already-`done` step, so the reachable multi-emission paths are a re-entry that re-fires
  the step (a `loop_back` or `failed` record) and any caller filing a landing outside the step — not an
  ordinary second finalize entry.
- **Task:** Either refuse a second `--kind landing` from the same `sender_id` at the write boundary with a
  named error, or have `emit-landing` resolve an existing landing and call `inbox supersede --by` before
  filing the new one. Prefer the first — the plan's D3 ⚠ says a supersession marker leaves the drain to
  reconcile a sequence, which the channel exists to avoid.
- **Done when:** A second landing write from the same sender is either refused or automatically linked as
  the successor, pinned by a test over the multi-emission shape (D3's *Done when*).
- **Suggested grouping:** `plan-orchestrator` / inbox channel

## G4 — Report a failed outline read as an error, not as "the plan has no intent"

- **Severity:** major
- **Kind:** bug
- **Where:**
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py:115-123`,
  `:133-139`, `:194-211`;
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:169-178`
- **Evidence:** `_run_outline_read` returns `{}` on `OSError` (`:115-116`), on a non-zero exit
  (`:117-118`), and on an unparseable envelope (`:121-122`). `has_outline_intent` skips any payload whose
  `status` is not `success` (`:135-136`, `continue`) and returns `False` (`:139`). `cmd_render` then
  prints `'omitted': True` with `reason: 'no outline intent: solution_outline.md absent, or its summary
  and overview sections are both absent or empty'` (`:203-204`) and exits 0. The function's own docstring
  states the intent openly (`:95-97`): *"A non-zero exit, an unparseable envelope, or a non-success status
  all degrade to an empty dict — 'no outline content' — because every one of those means the same thing
  for this script's purposes."* **The conflation is restated at the consuming site, so it is a contract
  rather than a slip**: `create-pr.md:169-172` tells the agent that `omitted: true` means *"the plan has
  no outline intent (no `solution_outline.md`, or its `summary` and `overview` sections are both absent or
  empty)… This is a normal outcome for outline-less plans, not a failure"*, and the decision-log line at
  `:174-178` interpolates the script's `{reason}`, so a reader failure is logged **as** the absence claim.
  Only one of the three degradations is exercised by a test: the absent-outline fixture
  (`test/plan-marshall/phase-6-finalize/test_pr_intent_section.py:67-68`) returns `status: error /
  error: not_found` through a `_Completed` stand-in that always carries `returncode=0` and parseable
  output (`:54-59`, `:89-93`), i.e. the non-success-status path. The `OSError`, non-zero-exit and
  unparseable-envelope paths — the three that mean something other than "no outline" — are reached by no
  test in the file.
- **Impact:** A reader failure removes the entire `## Intent` section from the PR body — problem
  statement, approach and Non-goals together — and records the removal as a substantive fact about the
  plan, in both the script's `reason` and the plan's decision log. Nothing in the rendered body indicates
  a section was intended, which is precisely the undetectable-loss shape the plan's D0 identified for the
  PR body.
- **Task:** Distinguish the three degradations. Return a `status: error` (or an `omitted: true` carrying a
  distinct `reason: outline_unreadable`) when the reader raises `OSError`, exits non-zero, or returns an
  unparseable envelope, and reserve the absence reason for a reader that succeeded and reported empty or
  not-found sections. Correct `create-pr.md`'s branch table to route the new reason to a failure
  disposition rather than to "normal outcome".
- **Done when:** A reader failure produces an outcome distinguishable from a genuinely intent-less plan,
  a test asserts the two are not conflated, and no document describes a reader failure as normal.
- **Suggested grouping:** `phase-6-finalize` / create-pr

## G5 — Branch F's documented recovery cannot fire, because its own `done` record suppresses it

- **Severity:** major
- **Kind:** bug
- **Where:**
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1801`,
  `:1796` (the Branch F `--outcome done`), `:1068`; frontmatter `:1-13`;
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:720`, `:37`, `:549`
- **Evidence:** Branch F closes with *"Re-entering finalize once the queue merge lands takes the
  `state == merged` path, which performs the deferred local cleanup"* (`:1801`), while recording
  `--outcome done` (`:1796`). The dispatcher's general re-entry rule for every step outside the
  head-dependent and `push` special cases is *"IF outcome == "done": SKIP this step (continue to next
  iteration)"* (`SKILL.md:720`), and the prohibition that closes the set is *"Never skip a step in the
  manifest list based on PR state, CI state, or earlier step outcomes. The ONLY valid skip condition is
  the resumable re-entry check (skip if already marked `done` from a previous invocation)"*
  (`SKILL.md:37`). The one escape from that skip is a `head_dependent: true` declaration
  (`SKILL.md:549`), and `branch-cleanup`'s frontmatter declares `order: 70` and `mutates_source: false`
  only — `grep -n "head_dependent"` over the whole document returns two hits, both prose about
  *`automatic-review`'s* declaration (`:125`, `:689`), never its own. The same document already knows
  this: `:1068` warns that *"an already-`done` `branch-cleanup` is SKIPPED by the resumable re-entry
  check, so the very remedies the message names… would point at a pass that never runs."*
- **Impact:** A merge-queue landing timeout takes Branch F, which emits the G1 landing, lets the loop run
  on, and archives the plan with the PR unmerged — and then names a recovery that the step's own `done`
  record makes unreachable. The two statements inside one document contradict each other, and the one a
  reader is most likely to trust (the Branch F closing sentence, adjacent to the payload they are about
  to emit) is the false one.
- **Task:** Settle which is true. Either record Branch F with an outcome the re-entry check re-fires
  (`loop_back` or `failed`, as `:1068` prescribes for the structurally-blocked path), or declare
  `branch-cleanup` `head_dependent: true` so the re-entry comparison can re-arm it, or delete the
  re-entry sentence and state plainly that Branch F's cleanup is deferred to an operator action. Do not
  leave `:1801` asserting a recovery `:1068` says cannot happen.
- **Done when:** A Branch F run's deferred cleanup is reachable by the mechanism its own document names,
  and no sentence in `branch-cleanup.md` claims a re-entry that the resumable re-entry check suppresses.
- **Suggested grouping:** `phase-6-finalize` / merge gate

## G6 — The drain-completeness check passes a landing that carries no facts

- **Severity:** major
- **Kind:** vacuous-guard
- **Where:**
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:859-887`
  (`check_landing_completeness`), `:811-820` (`LANDING_REQUIRED_KEYS`);
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:235`;
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md:84`;
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md:322`
- **Evidence:** The check's completeness test is `missing = [key for key in LANDING_REQUIRED_KEYS if not
  facts.get(key)]` (`:886`) — presence and non-emptiness only. The producer's Error Handling table
  instructs the opposite of an empty value on failure: *"A fact read … returns an error | Write that field
  as `n/a` in the fenced block (key still present) and continue"* (`emit-landing.md:235`). `'n/a'` is
  non-empty, so every degraded field passes. Confirmed by execution: a `landing-facts` block whose every
  required value is `n/a` returns `(True, [])`, and so does one carrying
  `merge_state=totally-merged-trust-me`. The payload spec fixes a vocabulary for that key — *"(`merged` /
  `open` / `n/a`)"* (`landing-payload-spec.md:84`) — that nothing validates and that the producer never
  restates as a rule. The check's stated purpose makes the gap load-bearing: it *"lets the orchestrator
  turn 'the queue is empty' into 'nothing material is outstanding' — the two coincide only when every
  drained landing was complete"* (`SKILL.md:322`). The test named for the shared-source invariant does not
  test it — `test/plan-marshall/plan-orchestrator/test_landing_completeness.py:137-141` asserts three
  membership facts about `LANDING_REQUIRED_KEYS` and never reads the producer.
- **Impact:** A run whose fact reads failed emits a landing that is *structurally* complete and
  *substantively* empty, and the orchestrator concludes nothing material is outstanding from it. Combined
  with G1, a Branch F landing can pass the check while asserting a merge that never happened — the
  validator cannot tell a truthful `merge_state` from an invented one.
- **Task:** Add a value-level arm: reject `n/a` for the keys where absence is a real gap (or report a
  `degraded_keys` list beside `missing_keys` so the drain can record it as an Open Defect), and validate
  `merge_state` against the spec's declared vocabulary. Give the shared-constant test a real assertion —
  parse `emit-landing.md`'s required-key list and compare it against `LANDING_REQUIRED_KEYS`.
- **Done when:** An all-`n/a` landing is not reported `complete: true`, an out-of-vocabulary `merge_state`
  is named as a defect, and the shared-source test fails when producer and validator diverge.
- **Suggested grouping:** `plan-orchestrator` / landing payload

## G7 — Put the HEAD stamp in the `review-retrospective.md` artifact, not only in the step record

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:388-425` (Step 4 composition),
  `:94` (the claim), `:427-445` (Step 5, where the stamp actually goes)
- **Evidence:** Step 4 enumerates everything the artifact must contain — the deterministic metrics table,
  `## Review-versus-Gate Delta`, `## Qualitative Quality Assessment`, `## Comparative Verdict` — and never
  the step's own resolved HEAD. That stamp is forwarded to `mark-step-done --head-at-completion {sha}` in
  Step 5, i.e. into `.plan/` step state. Yet line 94 claims *"the artifact this step persists is a verdict
  about a specific tree, and the stamp is what ties it to that tree for anyone reading the retrospective
  later."* The artifact is not wholly unanchored: the `## Review-versus-Gate Delta` section carries
  `gate_head_sha` and `reviewed_head_sha` (`:342`, `:344`, `:402`), so the reviewer half of the verdict is
  tied to a tree — but only inside that one section, and never as the completion HEAD line 94 describes.
- **Impact:** A reader of the archived `review-retrospective.md` cannot tell from the artifact alone which
  tree the step recorded its verdict against without locating the step record. The concrete staleness the
  plan observed is cured by the step's post-merge order, so this is a durability/auditability gap rather
  than a live mis-scoring risk.
- **Task:** Add the resolved `{sha}` to the artifact body as an unconditional as-of line, alongside the
  two tree SHAs the delta section already carries, and correct the line-94 claim to name where the stamp
  actually lands.
- **Done when:** The composed `review-retrospective.md` carries the HEAD it describes regardless of which
  optional sections are present, and `SKILL.md:94` no longer attributes that property to the step record.
- **Suggested grouping:** `finalize-step-review-retrospective`

## G8 — Anchor the PR body to the HEAD it describes, or recompose it after a loop-back

- **Severity:** minor
- **Kind:** incomplete
- **Where:**
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:1-16` (frontmatter),
  `:71` (the existing-PR branch), `:100-108` (the diff-scope resolution), `:120-134`, `:136-165`;
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:720`, `:219`
- **Evidence:** D4's *Done when* quantifies over **every** D0 member — *"every D0 member either carries a
  HEAD stamp or regenerates, with the choice justified per member"* — and the PR body is one of the three
  the plan named. Neither arm holds for it. `create-pr` frontmatter declares `order: 20` and
  `mutates_source: false` with **no** `head_dependent:`, so an already-`done` record takes the general
  re-entry rule *"IF outcome == "done": SKIP this step (continue to next iteration)"* (`SKILL.md:720`);
  and even on a re-fire its own branch for an open PR reads *"Skip creation; reuse the returned
  `pr_number`"* (`create-pr.md:71`), recomposing nothing. The body's file references are bound to the
  diff resolved once at `order: 20` (`:100-108`, `git diff --name-only origin/{base_branch}...HEAD`,
  with the constraint at `:129-134` that every path mentioned must belong to that set), while the
  wait region deliberately absorbs later HEAD mutations (`SKILL.md:219`, the *"bounded re-settle
  mutation-fixpoint"*). No other finalize step rewrites the body: `grep -rn "pr edit"` over
  `phase-6-finalize/` and `.claude/skills/` returns only `architecture-refresh.md:277`, `:305`, `:550`,
  which append a re-enrichment note. Nothing in the rendered body states the HEAD it was composed against.
- **Impact:** After a loop-back, the PR body's Intent and file references describe a narrower diff than
  the PR carries, and the mismatch is invisible to the reviewer reading it — the same undetectable-loss
  shape D0 identified for the dropped Non-goals paragraph, arriving by a different route. The report's D0
  table records the PR body's "staleable?" cell as resolved on the truncation question, which answers the
  content criterion and not D0's third criterion (*"is not regenerated after a loop-back"*).
- **Task:** Choose per D4's instruction and justify it: either add an as-of line to the composed body
  naming the HEAD the diff scope was resolved at, or declare `create-pr` `head_dependent: true` and give
  its existing-PR branch a body-recompose path through `ci pr prepare-body --for edit` + `pr edit`. ⚠ The
  regeneration arm re-spends the Intent distillation on every loop-back; the stamp arm does not. Do not
  default to regeneration.
- **Done when:** The PR body either states the HEAD its diff scope was resolved against, or is recomposed
  when finalize re-enters after a loop-back, with the choice recorded.
- **Suggested grouping:** `phase-6-finalize` / create-pr

## G9 — Carry the merge SHA, and the two remaining D2 fields, in the landing facts

- **Severity:** minor
- **Kind:** omission
- **Where:**
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:811-820`
  (`LANDING_REQUIRED_KEYS`),
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md:79-91`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:169-186`
- **Evidence:** The required set is `schema, plan_id, pr, merge_state, deliverables_total,
  deliverables_done, total_tokens, steps`. `grep -n -i "sha"` over `emit-landing.md` and
  `landing-payload-spec.md` returns only incidental substring matches (*shared*, *shape*) — no commit-SHA
  field in either. The plan's D2 requires *"Merge state and commit SHA"* and D5(a) requires *"A landing
  message emitted for a merged PR carries the SHA."* Two further D2 elements are also absent from the
  fact set and from the optional-key list: **cost against the anchor** (the payload carries a raw
  `total_tokens` and no comparison), and **what was deliberately left unchanged** (D2's parenthetical,
  *"including what was deliberately left unchanged"*).
- **Impact:** A drain can corroborate the PR number but not the tree that landed, so the message names an
  outcome it cannot anchor to a commit. The SHA is the one D2 element that D5(a) pins as a test, which
  makes it the required half; the other two are the residual the later landing-payload work did not pick
  up.
- **Task:** Add a `merge_sha` (or equivalently named) key to `LANDING_REQUIRED_KEYS`, to the payload
  spec's mechanisable table, and to the producer's fact assembly, sourced from the merge the
  `branch-cleanup` facts substantiate. Decide explicitly whether the cost-against-anchor comparison and
  the left-unchanged statement belong as optional keys or as residue prose, and record the choice. Keep
  every added field labelled as the step's own recorded claim, per the plan's out-of-scope constraint.
- **Done when:** A landing emitted for a merged PR carries the merged commit SHA,
  `check_landing_completeness` reports it missing when absent, and the disposition of the other two D2
  fields is stated in `landing-payload-spec.md`.
- **Suggested grouping:** `plan-orchestrator` / landing payload

## G10 — Classify `default:emit-landing` in the dispatched/inline roster

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md:9`
  (the closure invariant) and its two rosters,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:178`,
  `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py:86`, `:213-217`
- **Evidence:** `dispatch-inline-split.md:3` declares the document *"the single source of truth"* and
  `:9` states the closure invariant *"Every step in the authoritative registry … carries **exactly one**
  classification: it appears in either the dispatched roster or the inline roster, never both and never
  neither"*, adding at `:11` *"Adding a new finalize step without classifying it here turns the guarding
  regression red."* `grep -n "emit-landing"` over that document returns nothing, while `SKILL.md:178`
  registers `default:emit-landing` and describes it as *"(inline; composed OUT of a non-orchestrated plan
  at compose time)"*; `SKILL.md:772` names it among *"the inline consumers"* and `:848` names it as the
  owner of the run's one landing. The guarding test
  derives its registry from `_MARSHAL_JSON = PROJECT_ROOT / '.plan' / 'marshal.json'` (`:86`, read in
  `_registered_steps` at `:213-217`). That file is **tracked** — one of the two exceptions at
  `.gitignore:45-47` — so the blindness is not a missing file but a **stale** one: the committed
  snapshot holds 25 steps and does not include `emit-landing`, so the test passes (run locally:
  21 passed) without covering it.
- **Impact:** The document that governs whether a step dispatches or runs inline is silent about the step
  that emits the landing, and the invariant meant to catch that is blind because its population comes
  from a tracked snapshot nothing keeps current.
- **Task:** Add `default:emit-landing` to the `## Inline steps` roster. Separately, decide whether the
  closure test's registry source should fall back to the discovered built-in set when the tracked
  `.plan/marshal.json` snapshot is stale or absent, so the invariant is enforceable in a fresh clone.
- **Done when:** `emit-landing` appears in exactly one roster, and the closure test fails when a
  registered step is unclassified regardless of the state of `.plan/marshal.json`.
- **Suggested grouping:** `phase-6-finalize` / step roster

## G11 — Resolve the dangling `failed_outcome_strategy` reference

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:533`
- **Evidence:** The line reads *"The ci_failure precondition already blocks the consumer step (the step
  records `failed` outcome and the dispatcher honours `failed_outcome_strategy`)"*. A repo-wide search
  (`grep -rn "failed_outcome_strategy" . --exclude-dir=.git`) returns that single line plus this
  review's own two documents — no definition in any skill doc, script, config schema or test.
- **Impact:** The sentence justifies not double-blocking on a `triage` finding by pointing at a mechanism
  that does not exist, and it is the only place the document describes what bounds a failed step. That
  matters directly for G1: the question "does a non-merging `branch-cleanup` stop the pipeline?" resolves
  against a named strategy nobody implemented.
- **Task:** Either implement and document the strategy, or rewrite the sentence to name the mechanism that
  actually governs a `failed` outcome (the resumable-re-entry retry at `SKILL.md:721` and the
  continue-to-next-step behaviour at `:1057` / `:592`).
- **Done when:** No source in the repository cites `failed_outcome_strategy` without a definition.
- **Suggested grouping:** `phase-6-finalize` / dispatcher
