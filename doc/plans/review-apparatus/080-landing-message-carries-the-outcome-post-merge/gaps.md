# Gaps — 080-landing-message-carries-the-outcome-post-merge

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Stop emitting a landing message for a run whose merge did not land

- **Severity:** blocker
- **Kind:** unsound-refutation (and the underlying bug)
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1756-1763`
    (Branch C), `:1765-1772` (Branch D), `:1790-1799` (Branch F)
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:47-49`
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1057`, `:592`
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md:45`
- **Evidence:** `branch-cleanup.md:1696` states *"each of the six `--outcome done` call sites below
  (**Branches A through F**)"*, and all six code blocks carry `--outcome done` (lines 1720, 1751, 1760,
  1769, 1782, 1796). Branch C is *"declined by user… Nothing was rebased, merged, or cleaned up"*;
  Branch D is *"no PR found… exits before the rebase and before any merge"*; Branch F is *"enqueued,
  merge not yet landed… It records **no `merge_mechanism`**, because no merge landed"*. Because the step
  records a terminal `done`, the dispatch loop advances (`SKILL.md:1057` *"continue to the next step"*;
  no halt-on-`done` exists anywhere in the loop), reaching `emit-landing` at `order: 1000`, which states
  *"the emission is unconditional when the step runs"* (`emit-landing.md:48`). `branch-cleanup` is inline
  (`dispatch-inline-split.md:45`), so the post-dispatch completion guard that halts on a missing record
  (`SKILL.md:1136`) never applies to it. Confirmed by reading all six branches at both `6b923309` and
  HEAD.
- **Impact:** The report closed plan 080 partly on the claim *"a finalize that halts pre-merge never
  reaches order 991, so it emits **no** landing rather than a false one."* That claim is false. On the
  three non-merging branches the epic inbox receives a `kind: landing` message for a plan that did not
  land, and a drain reconciling against it records a shipped outcome that did not happen — the exact
  failure the plan's D1 and D5(b) were written to prevent.
- **Task:** Gate the landing on a positively-substantiated merge. Either (a) give `emit-landing` a
  precondition that reads `branch-cleanup`'s recorded facts and, when `merge_mechanism` is absent, emits a
  distinct non-landing message (or no message plus a recorded reason) instead of the landing; or (b)
  define the never-merges message D1 asked for and route the three branches to it. Whichever arm is
  chosen, state the other's failure mode, as D1 required.
- **Done when:** A run taking `branch-cleanup` Branch C, D, or F produces no message whose payload or
  prose asserts a landing, and the behaviour is pinned by a test that fails against the current
  unconditional emission.
- **Suggested grouping:** `phase-6-finalize` / landing emission

## G2 — Make the landing's prose claim conditional on `merge_state`

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:175`
- **Evidence:** The only worked example of the landing body is *"**An optional one-line narrative
  headline** under a `## What landed` heading — e.g. `{plan_id} shipped as {pr} ({merge_state}).`"* The
  heading and the verb *shipped* are fixed; the only variable is the parenthesised `merge_state`. The
  plan's ⛔ observation 1 states the remedy explicitly: *"**Appending a correct `outcome:` field beside a
  false sentence leaves the false sentence there.** The fix must change the message's **claim**, not only
  append an outcome."*
- **Impact:** Even once G1 is fixed for the non-merging branches, any reader or drain that reads the
  narrative half rather than the fenced facts block sees a landing assertion. On a Branch F run today the
  two halves of one message contradict each other, and the prose half is the one a human reads first.
- **Task:** Replace the single worked headline with a merge-state-conditioned pair (or a table): a
  landing-asserting form usable only when a merge is substantiated, and a non-landing form for every other
  state. Keep the claim labelled as the plan's own report, per the plan's out-of-scope constraint.
- **Done when:** `emit-landing.md` contains no unconditional landing-asserting headline template, and a
  worked example exists for the non-merged case.
- **Suggested grouping:** `phase-6-finalize` / landing emission

## G3 — Guarantee one landing per plan, not merely one per finalize run

- **Severity:** major
- **Kind:** incomplete
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:890-980`
    (`cmd_inbox_write`)
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:200-208`
  - `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md:92`
- **Evidence:** The invariant every source states is scoped per **run** — `inbox-envelope.md:92`,
  *"Exactly one per orchestrated finalize run"*; `emit-landing.md:200`, *"Exactly ONE `kind: landing`
  message per orchestrated finalize run"*. The defect the plan reported was three landings for one
  **plan**, across successive outcomes, and its D3 says so: *"Delaying the message until post-merge is
  necessary but NOT sufficient — a run that believes it finished three times still emits three."*
  `cmd_inbox_write` validates slug, sender id, sender type, kind, epic existence, target-plan
  deliverability and payload non-emptiness, and never checks for an existing landing from the same
  sender; `allocate_message_path` takes the next free sequence. `cmd_inbox_supersede` exists but is a
  manual verb — `grep -n "supersede"` over `emit-landing.md` returns nothing.
- **Impact:** Two landings from one plan both queue as live, both validate, and both reach the drain with
  nothing marking either as superseded — the append-only invariant then guarantees the stale one survives.
  A drain consuming the earlier one reconciles against a superseded outcome.
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
  `:133-139`, `:194-211`
- **Evidence:** `_run_outline_read` returns `{}` on `OSError`, on a non-zero exit, and on an unparseable
  envelope (lines 115-123). `has_outline_intent` skips any payload whose `status` is not `success`
  (line 135, `continue`) and returns `False` (line 139). `cmd_render` then prints
  `'omitted': True` with `reason: 'no outline intent: solution_outline.md absent, or its summary and
  overview sections are both absent or empty'` (lines 203-205) and exits 0. The module docstring states
  the intent openly: *"A non-zero exit, an unparseable envelope, or a non-success status all degrade to an
  empty dict — 'no outline content' — because every one of those means the same thing for this script's
  purposes."* No test covers the reader-error path: `test/plan-marshall/phase-6-finalize/
  test_pr_intent_section.py` covers absent, empty, present, over-budget, unbreakable-token and
  missing-draft only.
- **Impact:** A transient reader failure silently removes the entire `## Intent` section from the PR body
  — problem statement, approach and Non-goals together — and records the removal as a substantive fact
  about the plan. Nothing in the rendered body indicates a section was intended, which is precisely the
  undetectable-loss shape the plan's D0 identified for the PR body.
- **Task:** Distinguish the three degradations. Return a `status: error` (or an `omitted: true` carrying a
  distinct `reason: outline_unreadable`) when the reader exits non-zero or returns an unparseable
  envelope, and reserve the absence reason for a reader that succeeded and reported empty sections.
- **Done when:** A reader failure produces an outcome distinguishable from a genuinely intent-less plan,
  and a test asserts the two are not conflated.
- **Suggested grouping:** `phase-6-finalize` / create-pr

## G5 — Put the HEAD stamp in the `review-retrospective.md` artifact, not only in the step record

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:388-425` (Step 4 composition),
  `:94` (the claim), `:427-446` (Step 5, where the stamp actually goes)
- **Evidence:** Step 4 enumerates everything the artifact must contain — the deterministic metrics table,
  `## Review-versus-Gate Delta`, `## Qualitative Quality Assessment`, `## Comparative Verdict` — and never
  a HEAD stamp. The stamp is forwarded to `mark-step-done --head-at-completion {sha}` in Step 5, i.e. into
  `.plan/` step state. Yet line 94 claims *"the artifact this step persists is a verdict about a specific
  tree, and the stamp is what ties it to that tree for anyone reading the retrospective later."* The
  plan's D4 governing formulation is *"A persisted artifact describing external state must carry **the
  HEAD it describes**"*, and it names this artifact as the case where *"staleness is invisible on
  inspection."*
- **Impact:** A reader of the archived `review-retrospective.md` still cannot tell which tree the verdict
  is about without locating the step record. The concrete staleness the plan observed is cured by the
  step's post-merge order, so this is a durability/auditability gap rather than a live mis-scoring risk.
- **Task:** Add the resolved `{sha}` to the artifact body as an explicit as-of line, alongside the two
  tree SHAs the `## Review-versus-Gate Delta` section already carries, and correct the line-94 claim to
  name where the stamp actually lands.
- **Done when:** The composed `review-retrospective.md` carries the HEAD it describes, and `SKILL.md:94`
  no longer attributes that property to the step record.
- **Suggested grouping:** `finalize-step-review-retrospective`

## G6 — Classify `default:emit-landing` in the dispatched/inline roster

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md`
  (both rosters), `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:178`,
  `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py:213-217`
- **Evidence:** `dispatch-inline-split.md` declares itself *"the single source of truth"* and states the
  closure invariant *"Every step in the authoritative registry carries **exactly one** classification…
  never both and never neither"*, adding *"Adding a new finalize step without classifying it here turns
  the guarding regression red."* `grep -n "emit-landing"` over that document returns nothing, while
  `SKILL.md:178` registers `default:emit-landing` and describes it as inline, and `SKILL.md:772` / `:883`
  name it among the inline consumers. The guarding test derives its registry from
  `_MARSHAL_JSON = PROJECT_ROOT / '.plan' / 'marshal.json'` (line 86), which is git-ignored; the local
  snapshot predates the step, so the test passes (run locally, exit 0) without covering it.
- **Impact:** The document that governs whether a step dispatches or runs inline is silent about the
  step that emits the landing, and the invariant meant to catch that is blind because its population comes
  from an untracked file.
- **Task:** Add `default:emit-landing` to the `## Inline steps` roster. Separately, decide whether the
  closure test's registry source should fall back to the discovered built-in set when `.plan/marshal.json`
  is absent, so the invariant is enforceable in a fresh clone.
- **Done when:** `emit-landing` appears in exactly one roster, and the closure test fails when a
  registered step is unclassified regardless of whether `.plan/marshal.json` exists.
- **Suggested grouping:** `phase-6-finalize` / step roster

## G7 — Resolve the dangling `failed_outcome_strategy` reference

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:533`
- **Evidence:** The line reads *"The ci_failure precondition already blocks the consumer step (the step
  records `failed` outcome and the dispatcher honours `failed_outcome_strategy`)"*. A repo-wide search
  (`grep -rn "failed_outcome_strategy"` over the whole tree, excluding `.git`) returns that single line —
  no definition in any skill doc, script, config schema or test.
- **Impact:** The sentence justifies not double-blocking on a `triage` finding by pointing at a mechanism
  that does not exist, and it is the only place the document describes what bounds a failed step. That
  matters directly for G1: the question "does a non-merging `branch-cleanup` stop the pipeline?" resolves
  against a named strategy nobody implemented.
- **Task:** Either implement and document the strategy, or rewrite the sentence to name the mechanism that
  actually governs a `failed` outcome (the item-1 resumable-re-entry retry and the item-5 continue-to-next
  behaviour).
- **Done when:** No source in the repository cites `failed_outcome_strategy` without a definition.
- **Suggested grouping:** `phase-6-finalize` / dispatcher

## G8 — Carry the commit SHA in the landing facts

- **Severity:** minor
- **Kind:** omission
- **Where:**
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:806-821`
  (`LANDING_REQUIRED_KEYS`),
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:169-186`
- **Evidence:** The required set is `schema, plan_id, pr, merge_state, deliverables_total,
  deliverables_done, total_tokens, steps`. `grep -n -i "sha"` over `emit-landing.md` and
  `landing-payload-spec.md` returns no commit-SHA field. The plan's D2 requires *"Merge state and commit
  SHA"* and D5(a) requires *"A landing message emitted for a merged PR carries the SHA."*
- **Impact:** A drain can corroborate the PR number but not the tree that landed, so the message names an
  outcome it cannot anchor to a commit. This is the one D2 element the later landing-payload work did not
  pick up.
- **Task:** Add a `merge_sha` (or equivalently named) key to `LANDING_REQUIRED_KEYS`, to the payload spec's
  mechanisable table, and to the producer's fact assembly, sourced from the merge the `branch-cleanup`
  facts substantiate. Keep it labelled as the step's own recorded claim, per the plan's out-of-scope
  constraint.
- **Done when:** A landing emitted for a merged PR carries the merged commit SHA and
  `check_landing_completeness` reports it missing when absent.
- **Suggested grouping:** `plan-orchestrator` / landing payload
