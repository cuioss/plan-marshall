envelope_version=1
sender_type=plan
sender_id=plan-13-finalize-mechanism-defects
epic=process-compliance
kind=finding
created=2026-09-27T16:05:26Z

# Process-rule issues observed at the outline boundary (plan-13-finalize-mechanism-defects)

## 1. "ONE batched AskUserQuestion" cannot carry more than 4 questions

`planning-outline.md` § Post-return `outline_prompt` requires the orchestrator to "fire ONE batched
`AskUserQuestion` covering EVERY question in the envelope". The phase-3-outline leaf returned 6 questions.
`AskUserQuestion` accepts at most 4 questions per call, so the rule cannot be met as written. This run used
two calls (4 + 2) and logged the split. The same rule is stated for `refine_prompt` in `planning.md`. The
leaf contract should cap `outline_prompt` / `refine_prompt` at 4 questions, or the orchestrator rule should
say how to paginate (as phase-1-init Step 5c already does for recipe options).

## 2. planning.md and planning-outline.md disagree on how outline runs

`planning.md` § Action: outline says the 3-outline phase is "loaded directly in main context". But
`planning-outline.md` Step 2, which is the detailed workflow, dispatches phase-3-outline as an
`execution-context-{level}` Task. This run followed `planning-outline.md`. One of the two statements is stale.

## 3. The handshake exempts orchestrator inbox writes, the porcelain assertion does not (addendum to -002 item 2)

`phase_handshake verify --phase 2-refine` returned `main_dirty` as informational, with
`main_dirty_exempted: ['.plan/orchestrator/process-compliance/inbox/plan-12-tool-triage-006.md']`. So the
handshake already knows that orchestrator inbox writes are exempt. The `git -C . status --porcelain`
assertions in `planning.md` / `planning-outline.md` have no such exemption, and they stopped this run with
`refine_contract_violation` on exactly that class of file. The two guards should share one exemption set.

## 4. Leaf-reported gaps in the phase-3-outline dispatch (subagent's own report, not independently verified)

- `change-type-heuristic` was ambiguous (feature 2 vs bug_fix 1), and the documented LLM fallback
  `detect-change-type` is a dispatch the leaf cannot make. `planning-outline.md` has no return signal for it
  (its Metrics section even mentions an "LLM fallback dispatched from change-type-heuristic" that no step
  triggers). The leaf applied the rules inline and logged that.
- The plugin-dev `bug_fix` outline rule demands exactly 2 deliverables. The request has 5 independent defects,
  so the leaf produced 5 and logged the deviation. The rule has no multi-defect branch.
- The leaf reported Grep/Glob as unavailable in its step, and `architecture search --content` does not cover
  `.claude/**` or `~/.cache/plan-marshall/sessions/`. That left the deliverable-5 by-cwd question as an
  unreported coverage gap. The execution-context agent definition lists Glob and Grep, so either the tools were
  withheld at runtime or the leaf misreported. Needs a check.
- The leaf repeated the `not_orchestrated` transition-probe contradiction from message -002 item 1.
