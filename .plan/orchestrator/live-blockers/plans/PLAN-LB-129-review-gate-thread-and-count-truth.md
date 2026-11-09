# PLAN-LB-129: `review-gate` reads a resolved thread by its last bot comment, counts a section by its declared count, and refuses placeholder evidence

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-129-review-gate-thread-and-count-truth.md` and is queued as one row file, `queue/PLAN-LB-129.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-09 as the fix plan for the PLAN-LB-116 major (#1940, `5eb2f9d9d`,
> `landings/PLAN-LB-116.md` L3-1) with the fold candidates that the leaf verified at `main` `9cd644892` as false passes on observed
> shapes. Not carried, with reason: the marker-vocabulary inversion (a bot's last comment counts as handled only with a declared
> acknowledgment literal) fails closed but blocks bot chit-chat, and the live wording is not stored; the prose-only review body and the
> `issue_comment` parse-to-zero are real false passes on shapes the required reviewer does not post (re-graded to minor in the
> landing); both stay on the Watch. Ruling check: D1 is a false pass of the merge gate in normal use (blocking). **Each deliverable
> is its own outline deliverable, and each Done-when is its own success criterion. Do not merge them.** Every Done-when below fails
> at `9cd644892` unless it says "holds at". No Sonar. No token or measurement work.

## Objective

The runbook lane's `review-gate` verb decides whether the merge is allowed. A resolved thread whose last comment is the lane's reply
reads handled even when the bot's restated concern sits one comment above it, a CodeRabbit section titled `Nitpick comments: 3` is
counted as one finding so one disposition clears three, and a disposition of `— TBD` counts as a disposition. This plan makes the
gate read those three the way the spec said.

## Deliverables

1. **A resolved thread's concern remains when its last BOT comment carries a concern marker, whoever replied after it.**
   - `_thread_concern_remains` (`runbook_lane.py` L2617-2630) tests `thread[-1]` and only when a bot wrote it. The rule is: the
     concern remains if and only if the thread has at least one bot-authored comment (`_bot_of` non-empty) and the LAST bot-authored
     comment carries a concern marker. A lane or human reply after it never discharges it; a later bot comment without a marker (the
     bot's own acknowledgment) does. Change: `last = next((c for c in reversed(thread) if _bot_of(c)), None)` and return false when
     it is `None`.
   - Do not adopt "handled when the last bot comment is followed by a lane reply": it accepts exactly the failing thread. The opener
     stays eligible (a single resolved bot opener that says "still applies" is refused today and stays refused). The `outdated` flag
     is ignored by the rule, so it fails closed.

   *Done when:* each of these fails at `9cd644892`, in `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py`:
   - the resolved thread `[coderabbitai opener, octocat "fixed in abc1234", coderabbitai "This still applies: the guard is unchanged.", octocat "done"]` gives `merge_allowed: false` with reason `thread_concern_remains` (it is `true` at `9cd644892`); the case joins the `_only_unresolved_threads_stub` parametrization (L434-453).

   These hold at `9cd644892` and must keep holding: the same thread with a fifth `coderabbitai` comment "Addressed in commit def5678."
   is allowed; L190-204, L206-216 (bot acknowledgment, then human), L407-422 and L440.

2. **A section's findings are counted from its declared count, and an undeclared count is not read as one.**
   - CodeRabbit's observed title is `<summary>Nitpick comments: 1</summary>` (`_github_pr_fixtures.py` L425-442, #1939).
     `_TRAILING_COUNT_RE` (L2326) requires `(N)`, and `_normalise_section_title` drops the colon, so the declared count is `None` and
     `_count_section_findings` (L2441-2459) returns 1 for any prose span: `Nitpick comments: 3` counts as 1 and one disposition clears
     three. The same regex feeds the fail-closed arm at L2519, so `Potential issues: 2` escapes it.
   - The count also reads a trailing `:\s*N` from the raw title before normalisation. When no count is declared, the findings are the
     per-row `<!-- cr-comment:v1:` markers in the span (an observed row marker), then nested per-file blocks, then prose as one.
   - A counted title with no section keyword (`<summary>Potential issues (2)</summary>`) that matches neither a recognised section
     nor a declared non-finding label (`files selected for processing`, `files ignored due to path filters`, `review details`, to be
     completed from a captured body) is undecidable and refuses the gate; it is not skipped silently (L2517-2521 refuse only when a
     trailing count AND a section keyword are present). Verify against a captured live body that `Additional comments (N)` and the
     other observed titles do not become false blocks.

   *Done when:* each of these fails at `9cd644892`: a review body with `<summary>Nitpick comments: 3</summary>` and three row markers
   counts three findings; `<summary>Nitpick comments: 3</summary>` with one disposition keeps the gate closed; `<summary>Potential
   issues: 2</summary>` and `<summary>Potential issues (2)</summary>` are undecidable. And these hold at `9cd644892`: a clean body
   (`LGTM`, `test_a_clean_pull_request_admits_the_merge` L425-431) reads zero; a recognised `(N)` section counts N.

3. **A disposition's evidence is a real commit or a real reason.**
   - `_DISPOSITION_RE` (L2407-2409) accepts any `\S.*` after the dash, so `— TBD`, `— -` and `— n/a` count as disposed. Evidence is
     a hex sha `[0-9a-f]{7,40}` or a reason outside a placeholder set (`tbd`, `todo`, `n/a`, `na`, `-`, `?`, `none`, `later`, `wip`,
     `pending`; case-insensitive, punctuation stripped); otherwise the line goes into `refused` and the reason is
     `disposition_unparsable`.

   *Done when:* each of these fails at `9cd644892`: a progress-file line `finding: coderabbit nitpick-1 — TBD` (and `— -`, `— n/a`)
   does not dispose the finding; `— fixed in a1b2c3d` and `— declined: the call is deliberate and documented` do.

Split guard: three deliverables, all in the `review-gate` verb of `runbook_lane.py` and `test_runbook_lane_review_gate.py`. D2 is the
largest (it needs captured live bodies for the label list) and splits off first.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The gate fails closed: an unreadable shape refuses; no change makes it more permissive.
- One reader: the lane reuses the producer's predicates for noise, refusal and acknowledgment (`github_pr` helpers) rather than copying them.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture, are shown red where a Done-when says so, and use captured live body shapes or label them CONSTRUCTED.
- Executor regeneration is owed only if a verb or flag changes; the landing says so.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `_thread_concern_remains` (`marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` L2617-2630) reads `thread[-1]` only and requires a bot author; `_review_thread_rows` (L2633-2649); `_CONCERN_REMAINS_MARKERS` (L2315-2323); `_review_gate_verdict` (L2721-2836)
- OBSERVED: the observed CodeRabbit title is `<summary>Nitpick comments: 1</summary>` (`test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py` L425-442); `_TRAILING_COUNT_RE` (L2326) requires `(N)`; `_count_section_findings` (L2441-2459) returns 1 for any prose span when the count is `None`; the fail-closed arm at L2517-2521 needs a trailing count and a keyword from `_SECTION_KEYWORDS` (L2303)
- OBSERVED: `_DISPOSITION_RE` (L2407-2409) accepts any `\S.*` evidence
- OBSERVED: `_body_findings` (L2462-2530) mints findings only from recognised `<summary>` sections plus the status line; `issue_comment` is in `_RECORD_KINDS` (L2397) but only `review_body` is parsed (L2795-2797) — recorded as Watch items, not carried
- HYPOTHESIS: the provider does not publish an `outdated` flag the gate could use — the rule ignores it either way (verify-at-outline, D1)
- HYPOTHESIS: a live CodeRabbit review body carries `Additional comments (N)` or other counted titles that are not findings — capture a body and declare the non-finding labels from it, so D2 introduces no false block (verify-at-outline, D2)
- Verify-first clause (D1): reproduce the four-comment thread as a fixture at `9cd644892` before editing.
- Verify-first clause (D2): capture a live review body through the CI abstraction first; no label is invented.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_thread_concern_remains`, `_TRAILING_COUNT_RE`, `_normalise_section_title`, `_count_section_findings`, `_body_findings`, `_DISPOSITION_RE` (D1, D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — the `review-gate` section (L173-210) and §6 step 4, only if a documented rule changes (verify-at-outline)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py` (D1, D2, D3)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py` — read, edited only to share a captured body (verify-at-outline) (D2)

## Dependencies and Sequencing

- Depends on: PLAN-LB-116 (shipped, `5eb2f9d9d`).
- Overlaps with: PLAN-LB-137 (lane recipes) on `runbook-lane/SKILL.md`; PLAN-LB-138 D3 if it lifts the declaration reader out of `runbook_lane.py` (sequence PLAN-LB-138 after this plan). PLAN-LB-128 shares the captured CodeRabbit bodies, not a file.
- Adjacent to: `workflow-integration-github/scripts/github_pr.py` (the producer predicates, read not edited).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-129-review-gate-thread-and-count-truth.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
