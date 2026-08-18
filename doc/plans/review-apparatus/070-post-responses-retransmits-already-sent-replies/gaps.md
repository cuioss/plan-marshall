# Gaps — 070-post-responses-retransmits-already-sent-replies

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Stamp the idempotency marker when the reply was sent but the resolve step failed

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:1644-1651`
  (and the stamp it skips at `:1662`); the same shape at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py:420-433`.
  The misleading rationale is the comment at `github_pr.py:1600-1604`.
- **Evidence:** the verb transmits the reply first and resolves the thread second:

  ```python
  rc, _data, err = _github.run_graphql(THREAD_REPLY_MUTATION, {'threadId': thread_id, 'body': reply_body})
  if rc != 0:
      untransmitted.append({'hash_id': hash_id, 'reason': f'thread-reply failed: {err}'})
      continue
  rc2, _data2, err2 = _github.run_graphql(RESOLVE_THREAD_MUTATION, {'threadId': thread_id})
  if rc2 != 0:
      untransmitted.append({'hash_id': hash_id, 'reason': f'resolve-thread failed: {err2}'})
      continue
  ```

  The `rc2` branch `continue`s past `mark_finding_responded(plan_id, hash_id)` at `:1662`, so a reply
  that *was* delivered leaves no marker. Reproduced with a scratchpad probe against the real module and
  the real store (`plan_context` sandbox), stubbing `run_graphql` to succeed on
  `THREAD_REPLY_MUTATION` and fail on `RESOLVE_THREAD_MUTATION`:

  ```text
  MARKER AFTER ROUND 1: None
  THREAD REPLIES TOTAL AFTER ROUND 2: 2
  ROUND2 skipped: []
  ```

  The in-code comment claims the opposite — "a crash between send and mark leaves the finding eligible
  for a safe retry rather than silently dropped" — which is true for a one-step verb and false for this
  two-step one. `workflow-integration-github/SKILL.md:141` independently records that this state occurs
  in practice ("a thread-bearing disposition whose resolve-thread failed leaves an unresolved reply
  carrying arbitrary `resolution_detail` text").
- **Impact:** the exact defect this plan was written to eliminate survives on the partial-failure branch:
  a duplicate reply lands on a third party's thread and, once round 2 succeeds at the resolve step, it is
  counted in `count_responded` as work done. A thread whose resolve keeps failing re-replies on every
  round, which is one of the loops `_SELF_RESPONSE_LOOP_BOUND` exists to bound.
- **Task:** split the transmit from the resolve in the marker's eyes. Stamp `mark_finding_responded`
  immediately after the successful thread reply (before the resolve mutation), and record the
  resolve-thread failure in `untransmitted` as a *resolve* failure rather than an untransmitted
  disposition — the disposition was transmitted. If the return contract must keep the failure visible in
  `untransmitted`, add a distinguishing reason prefix so a consumer can tell "never sent" from "sent but
  not resolved". Apply the identical change to `gitlab_pr.py:425-429`. Rewrite the
  `github_pr.py:1600-1604` comment so it no longer asserts that every retry is safe.
- **Done when:** a test stubs a succeeding `THREAD_REPLY_MUTATION` and a failing `RESOLVE_THREAD_MUTATION`,
  runs `cmd_post_responses` twice, and asserts exactly one `THREAD_REPLY_MUTATION` call in total and an
  `already responded` skip on the second pass; the equivalent test exists for `gitlab_pr`.
- **Suggested grouping:** workflow-integration-github / workflow-integration-gitlab — respond-verb failure paths

## G2 — Complete the `count_responded` consumer enumeration: the pr-doctor lifecycle is a second invoker

- **Severity:** major
- **Kind:** false-report-claim / incomplete
- **Where:** claim in `doc/plans/review-apparatus/070-post-responses-retransmits-already-sent-replies/report-01.md`
  § D0 ("**sole production invoker**", "**Production readers of the field: none.**"); the missed sites are
  `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md:135-140`
  (the second `post_responses` invocation) and `:157` (`threads_resolved: {N}`).
- **Evidence:** `automated-review-lifecycle.md` § "Step 4.5: RESPOND — transmit dispositions to the PR"
  carries its own invocation block:

  ```bash
  python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
    post_responses --pr-number {pr_number} --plan-id {plan_id}
  ```

  and its § Step 5 return summary emits `threads_resolved: {N}` with no documented derivation anywhere:
  `grep -rn "threads_resolved" marketplace/bundles/ --include=*.md --include=*.py` returns that single
  line. An agent executing the document fills it from the respond return. D0's method — grep for the
  literal string `count_responded` — structurally cannot find a consumer that renames the value, which is
  the failure mode the plan's ⛔ "a list of call sites is a sample, not an enumeration" named.
- **Impact:** the GATE deliverable's sole job was the enumeration, and D2's "the migration (or the
  decision not to migrate) is stated per consumer" was satisfied against an incomplete set. The
  behavioural impact of the narrowing on this consumer is benign (`threads_resolved` becomes more
  truthful), but the derivation's authority does not survive, and the next change to this field will
  inherit the same blind spot.
- **Task:** give `threads_resolved` an explicit derivation in `automated-review-lifecycle.md` § Step 5 —
  state which field of the `post_responses` return it is computed from (the count of `responded[]`
  entries with `resolved_on_provider: true` is the honest one, since a batched disposition resolves no
  thread) and that it names this round only. Add the site to the plan's recorded consumer set. When
  re-deriving a field's consumer set in future, derive over *meaning* (invocation sites and the fields
  their documented outputs cannot otherwise source), not over the literal identifier.
- **Done when:** `automated-review-lifecycle.md` states the source expression for `threads_resolved`, and
  the consumer set recorded for `count_responded` names both invocation sites.
- **Suggested grouping:** workflow-pr-doctor / review-apparatus — respond-loop consumer contract

## G3 — Delete the surviving "only a missing `resolution_detail` is skipped" claim in Step 8

- **Severity:** major
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md:243`
- **Evidence:** the sentence reads "… Only a finding with no `resolution_detail` is skipped — there is
  genuinely nothing to transmit:". Three other skip reasons exist in the same verb:
  `already responded` (`github_pr.py:1607`), `belongs_to_pr_<n>` and `pr_number_unrecorded`
  (`github_pr.py:1602-1603`). The corrected paragraph this plan wrote sits at `:265` of the same file and
  contradicts it directly. The report's Finding 6 records the cold read as passing — it was aimed at the
  new paragraph and did not read the surrounding section.
- **Impact:** a reader of Step 8 who stops at the invocation block — the natural stopping point, since the
  block is what they are there to run — is told the pre-fix skip taxonomy. It is also the specific
  sentence that made the plan's inverted-rationale finding survive three sightings, restated in a second
  place.
- **Task:** rewrite `verification-feedback.md:243` to stop enumerating skip reasons inline. Point at
  `workflow-integration-github/SKILL.md` § Workflow 2 step 4, which owns the complete four-row transmit
  table (`:160-165`), rather than restating a subset of it.
- **Done when:** `grep -n "Only a finding with no" marketplace/bundles/` returns no hits, and Step 8
  contains no inline enumeration of `post_responses` skip reasons.
- **Suggested grouping:** plan-marshall workflow docs — RESPOND-loop prose

## G4 — Update the pr-doctor lifecycle's RESPOND description to the current skip taxonomy

- **Severity:** major
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md:135`
- **Evidence:** "For each terminal-disposition finding carrying a `thread_id` and `resolution_detail`,
  `post_responses` posts the stored `resolution_detail` as a thread-reply then resolves the thread;
  findings without a `thread_id` or `resolution_detail` are skipped, never guessed at". Wrong on two
  counts: a thread-bearing finding with no `thread_id` is `untransmitted`, not skipped
  (`github_pr.py:1636-1642`), and a genuinely threadless kind is batched rather than requiring a
  `thread_id` at all (`github_pr.py:1620-1622`). Silent on the `already responded` skip this plan added.
- **Impact:** the second-most-read description of the RESPOND loop still describes the pre-fix,
  pre-kind-routing verb. An operator reading it will not expect a second run to be a no-op, which is the
  behaviour the plan set out to make legible.
- **Task:** replace the inline description at `:135` with a cross-reference to
  `workflow-integration-github/SKILL.md` § Workflow 2 step 4, following the same
  do-not-duplicate-the-table pattern the corrected Step 8 paragraph uses.
- **Done when:** `automated-review-lifecycle.md` § Step 4.5 states no skip taxonomy of its own and
  cross-references the owning table.
- **Suggested grouping:** workflow-pr-doctor / review-apparatus — respond-loop consumer contract

## G5 — Document `responded` / `responded_at` and `resolve`'s marker-clearing side effect in manage-findings

- **Severity:** minor
- **Kind:** omission / stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md`
  § Plan Finding Record (Required table at `:70-79`, Optional table at `:130-140`);
  `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md:322-329` (§ resolve).
- **Evidence:** `grep -rn "responded" marketplace/bundles/plan-marshall/skills/manage-findings/` returns
  hits in `.py` files only — zero in either document. `jsonl-format.md`'s Optional table lists `file_path`,
  `line`, `component`, `module`, `rule`, `author`, `kind`, `reviewed_commit_sha`, `bot_kind`, and the
  record example at `:56-67` carries `promoted` / `promoted_to`, but nothing names `responded` or
  `responded_at`. `git log -S'responded' -- .../jsonl-format.md` returns no commits, so the field has
  never been documented there. `SKILL.md` § resolve documents the verb's arguments with no mention that
  it now writes `responded: false` / `responded_at: null` when a disposition changes.
- **Impact:** the store's owning skill does not describe a persisted field that three provider scripts
  read and that `resolve` now mutates as a side effect. A future change to `resolve` has no documented
  contract to preserve, and the fields' lifecycle is discoverable only by reading three provider
  SKILL.md files.
- **Task:** add `responded` (bool) and `responded_at` (ISO 8601 UTC or null) to the Optional Fields table
  in `jsonl-format.md`, with a one-line statement that they are the RESPOND-verb idempotency key set by
  `mark_finding_responded` and cleared by `resolve` when a finding's resolution or reply body changes.
  Add the same clearing rule to `manage-findings/SKILL.md` § resolve.
- **Done when:** both fields appear in the `jsonl-format.md` field table and the § resolve documentation
  states the clear-on-change behaviour.
- **Suggested grouping:** manage-findings — store schema documentation

## G6 — Correct the two stale provider enumerations around the marker

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md:148`;
  `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:475`
- **Evidence:** the Sonar SKILL.md says "It is idempotent — a finding whose dismissal was already
  transmitted carries a `responded` marker and is skipped on a re-run, so re-invoking the verb never
  re-POSTs the same dismissal." After this plan that is incomplete: `_findings_core.py:476-481` clears the
  marker on a changed disposition, so a re-decided dismissal *does* re-POST — a real behaviour change to
  Sonar delivered without touching `sonar.py` and without updating its documentation. Separately,
  `_findings_core.py:475` enumerates "every provider that reads the marker (GitHub, Sonar)", which the
  GitLab fix (`b19ef4a6`; `gitlab_pr.py:409`) made incomplete.
- **Impact:** the Sonar surface's documented contract now under-describes its behaviour in the one
  direction that transmits to a third party. The `_findings_core` comment misnames the set of readers a
  future change would have to consider.
- **Task:** extend `workflow-integration-sonar/SKILL.md:148` with the changed-disposition clause, matching
  the wording already used in `workflow-integration-github/SKILL.md:169` and
  `workflow-integration-gitlab/SKILL.md:74`. Update `_findings_core.py:475` to name GitLab, or better,
  drop the enumeration and say "every provider respond verb".
- **Done when:** the Sonar SKILL.md states that a re-decided dismissal re-transmits, and no comment or doc
  enumerates the marker's readers as a two-element set.
- **Suggested grouping:** workflow-integration-sonar / manage-findings — marker contract prose

## G7 — Cover the failure paths' marker semantics with tests on the GitHub verb

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/workflow-integration-github/test_github_pr.py` — the failure-path tests at
  `:1502` (`test_post_responses_batch_post_failure_untransmits_whole_batch`) and `:1579`
  (`test_post_responses_thread_reply_failure_is_untransmitted`)
- **Evidence:** `grep -n "^def test_post_responses" test/plan-marshall/workflow-integration-github/test_github_pr.py`
  lists 14 tests; neither failure-path test inspects the stored `responded` field, and no test asserts
  what a second pass does after a failure. Sonar has exactly this test —
  `test/plan-marshall/workflow-integration-sonar/test_fetch_findings.py:458`
  (`test_failed_post_does_not_mark_responded`, asserting `stored.get('responded') is not True`) — and the
  GitHub provider, which copied the pattern, did not copy the test. G1 lives in this untested region.
- **Impact:** the marker's failure semantics — the half of the contract that decides whether a retry
  duplicates or recovers — are asserted only by a code comment.
- **Task:** add two tests to `test_github_pr.py`: (a) a failed batched post leaves every batch member
  unmarked and a second pass re-attempts them; (b) a failed thread reply leaves the finding unmarked and a
  second pass re-attempts it. Add the G1 test alongside them once G1 is fixed.
- **Done when:** both tests exist, read the stored finding through `_findings_core.get_finding`, and pass.
- **Suggested grouping:** workflow-integration-github — respond-verb failure paths

## G8 — Cover Sonar's changed-disposition re-transmit

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/workflow-integration-sonar/test_fetch_findings.py` (the marker tests at
  `:409`, `:429`, `:458`)
- **Evidence:** `report-01.md` § D1 claims the design "gives Sonar the same changed-disposition
  correctness for free without touching `sonar.py`". `grep -rn "responded" test/plan-marshall/workflow-integration-sonar/*.py`
  finds only marker-persisted-after-success, rerun-skips-already-responded, and failed-post-does-not-mark.
  No test re-resolves a Sonar finding to a different disposition and asserts it transmits again.
- **Impact:** a behaviour the plan claims to have delivered to a second provider is unprotected; a future
  narrowing of the `resolve_finding` clear would break Sonar with a green suite.
- **Task:** add a test mirroring
  `test/plan-marshall/workflow-integration-github/test_github_pr.py:1656`
  (`test_post_responses_retransmits_a_changed_disposition`) against `sonar.cmd_post_responses`: dismiss
  once, re-run to confirm zero, `resolve_finding` to a different resolution and detail, re-run and assert
  one `do_transition` POST with the new transition.
- **Done when:** the test exists and passes, and fails if `_findings_core.py:479-481` is removed.
- **Suggested grouping:** workflow-integration-sonar — marker contract tests

## G9 — Stop re-sending a byte-identical reply when only the resolution changed

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:463-464`
  and `:477-481`
- **Evidence:** `updates['resolution_detail'] = detail` is written only `if detail:`, while the clear at
  `:479` fires on `resolution_changed or detail_changed`. A `resolve` that changes the resolution without
  supplying a new `--detail` therefore clears the marker and leaves the old reply body. Probe against the
  real module and store:

  ```text
  after change -> responded: False | detail: 'Accepted: original words.'
  round2 count_responded: 1
  round2 body identical to round1: True
  ```

  The documented triage flow always passes `--detail` (`automated-review-lifecycle.md:131`,
  `plan-marshall/workflow/triage.md:198`), but the CLI makes it optional
  (`manage-findings/SKILL.md:325-327`), so a caller can reach this.
- **Impact:** the reviewer receives the identical words twice — the plan's defect #1 in a narrower case —
  and the second send is counted in `count_responded` as a new disposition.
- **Task:** decide and implement one of: (a) clear the marker on a resolution change only when a new
  detail accompanies it, and reject a bare resolution change on an already-transmitted finding with a
  typed error naming the missing detail; or (b) keep the clear and have the respond verbs treat an
  unchanged `resolution_detail` as nothing-new-to-say. Option (a) is the smaller change and keeps the
  reviewer-facing text and the disposition in step. Record the choice in `jsonl-format.md` alongside G5.
- **Done when:** a test resolves a transmitted finding to a new resolution with no `--detail` and asserts
  the reviewer receives no duplicate body, and the chosen semantics are documented.
- **Suggested grouping:** manage-findings — marker lifecycle

## G10 — Make D3(c)'s population a real derivation, or drop the derivation framing

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/workflow-integration-github/test_github_pr.py:1724`
- **Evidence:** the "derived" population is

  ```python
  responded_family = {key: value for key, value in result.items() if key in ('count_responded', 'responded')}
  assert responded_family, 'the return must expose a responded-count family'
  ```

  a hard-coded two-key literal filtered against the return. The non-empty assert cannot fail while either
  key exists, so the vacuous-set guard guards nothing. `test/_shared/_dispatch_roster.py:26-63`, the
  pattern the plan named and the docstring cites, parses its population out of a document at test time
  (`section_lines` + `parse_roster_rows`) and raises when the heading is absent. The plan's Verification
  section additionally demands "the consumer-population size published in the **test output**"; the size
  is published in `report-01.md`, and no test emits it.
- **Impact:** the test that exists to prove the count-field family is fully covered proves only that two
  named keys hold two expected values — which the (a) test already proves. The plan's anti-hand-list
  discipline was applied to the report and not to the test.
- **Task:** either derive the family from the return contract's own documented shape (parse the
  `skipped[]` / `responded[]` / `count_*` row set out of `workflow-integration-github/SKILL.md` §
  Workflow 2 step 4 the way `_dispatch_roster.py` parses a roster, and assert every derived member is
  covered), or delete the derivation framing from the test and its docstring and let it be what it is — a
  count-semantics assertion. Whichever is chosen, print the population size so the plan's
  publish-in-test-output demand is met.
- **Done when:** the test either parses its population from a substrate and fails when that substrate is
  absent, or no longer claims to derive one; and the population size appears in the test output.
- **Suggested grouping:** workflow-integration-github — respond-verb test discipline

## G11 — Bring the `already responded` skip reason into the provider's reason vocabulary

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:1607`;
  mirrored at `gitlab_pr.py:410`, `sonar.py:749`; documented at
  `workflow-integration-github/SKILL.md:162` and asserted in four tests
  (`test_github_pr.py:1645,1679,1733,1765`)
- **Evidence:** every other GitHub skip reason is a snake_case token —
  `{'hash_id': hash_id, 'reason': 'no_resolution_detail'}` (`:1611`), `'pr_number_unrecorded'` and
  `f'belongs_to_pr_{finding_pr}'` (`:1602-1603`) — while the new one is the space-separated phrase
  `'already responded'`. The phrase was copied from Sonar, whose own vocabulary is mixed
  (`'no issue key in detail'` at `sonar.py:757`).
- **Impact:** a consumer matching skip reasons as tokens (the shape every other GitHub reason invites)
  will not match this one. The inconsistency is inside a single `skipped[].reason` field.
- **Task:** rename to `already_responded` across the three providers, the SKILL.md tables
  (`workflow-integration-github/SKILL.md:162`, `workflow-integration-gitlab/SKILL.md:74`,
  `workflow-integration-sonar/SKILL.md:148`) and the test assertions, in one change so the three
  providers keep a single vocabulary. Note this is a cross-provider rename with no production reader
  (verified by the same sweep that produced G2), so it is safe; do it together with G5's documentation so
  the field's contract is written down once, in its final form.
- **Done when:** `grep -rn "'already responded'" marketplace/bundles/ test/` returns no hits and the full
  test slice for the three providers passes.
- **Suggested grouping:** workflow-integration-github / gitlab / sonar — respond-verb return vocabulary
