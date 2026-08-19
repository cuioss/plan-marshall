# Gaps — 070-post-responses-retransmits-already-sent-replies

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis. Thirteen entries: 3 major, 10 minor, 0 blockers.

## G1 — Stamp the idempotency marker when the reply was sent but the resolve step failed

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:1644-1651`
  (and the stamp it skips at `:1662`); the same shape at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py:420-433`.
  The misleading rationale is the comment at `github_pr.py:1595-1605` (the "safe retry" sentence is at
  `:1603-1605`).
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
  that *was* delivered leaves no marker. Reproduced twice independently with a scratchpad probe against
  the real module and a real store, stubbing `run_graphql` to succeed on `THREAD_REPLY_MUTATION` and
  fail on `RESOLVE_THREAD_MUTATION`:

  ```text
  ROUND1: {'status': 'partial', 'count_responded': 0, 'count_skipped': 0, 'count_untransmitted': 1}
  MARKER AFTER ROUND 1: None
  ROUND2 skipped: []
  THREAD REPLIES TOTAL: 2
  ```

  The in-code comment claims the opposite — "a crash between send and mark leaves the finding eligible
  for a safe retry rather than silently dropped" — which is true for a one-step verb and false for this
  two-step one. `workflow-integration-github/SKILL.md:141` independently records that this state occurs
  in practice ("a thread-bearing disposition whose resolve-thread failed leaves an unresolved reply
  carrying arbitrary `resolution_detail` text").
- **Impact:** two-sided, and the second side is the one this plan cared most about.
  (1) The exact defect this plan was written to eliminate survives on the partial-failure branch: a
  duplicate reply lands on a third party's thread and, once a later round succeeds at the resolve step,
  it is counted in `count_responded` as work done.
  (2) On the failing round the disposition is recorded in `untransmitted[]` and counted in
  `count_untransmitted` — a count naming a reply that *did* reach the reviewer. That is the plan's
  defect #2 with the sign flipped: a confident negative over an action that did happen.
  Nothing bounds the repetition either — see G13.
- **Task:** split the transmit from the resolve in the marker's eyes. Stamp `mark_finding_responded`
  immediately after the successful thread reply (before the resolve mutation), and record the
  resolve-thread failure in a way that says *the disposition was transmitted, the thread was not
  resolved* — either a separate return list or a distinguishing `reason` prefix on `untransmitted[]`
  so a consumer can tell "never sent" from "sent but not resolved", with `count_untransmitted`'s
  documented meaning updated to match whichever is chosen. Apply the identical change to
  `gitlab_pr.py:425-429`. Rewrite the `github_pr.py:1595-1605` comment so it no longer asserts that
  every retry is safe.
- **Done when:** a test stubs a succeeding `THREAD_REPLY_MUTATION` and a failing `RESOLVE_THREAD_MUTATION`,
  runs `cmd_post_responses` twice, and asserts exactly one `THREAD_REPLY_MUTATION` call in total and an
  `already responded` skip on the second pass; a second assertion pins that the first round does not
  report the transmitted disposition under the same label as a never-sent one; the equivalent test
  exists for `gitlab_pr`.
- **Suggested grouping:** workflow-integration-github / workflow-integration-gitlab — respond-verb failure paths

## G2 — Delete the surviving "only a missing `resolution_detail` is skipped" claim in Step 8

- **Severity:** major
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md:243`
- **Evidence:** the sentence reads "… Only a finding with no `resolution_detail` is skipped — there is
  genuinely nothing to transmit:". Three other skip reasons exist in the same verb:
  `already responded` (`github_pr.py:1607`), `belongs_to_pr_<n>` and `pr_number_unrecorded`
  (`github_pr.py:1591`). The same sentence also still says the call "transmits every terminal-disposition
  finding carrying a `resolution_detail`", which the marker skip now contradicts. The corrected paragraph
  this plan wrote sits at `:265` of the same file. The report's Finding 6 records the cold read as
  passing — it was aimed at the new paragraph and did not read the surrounding section.
- **Impact:** a reader of Step 8 who stops at the invocation block — the natural stopping point, since the
  block is what they are there to run — is told the pre-fix skip taxonomy. It is also the specific
  sentence that made the plan's inverted-rationale finding survive three sightings, restated in a second
  place.
- **Task:** rewrite `verification-feedback.md:243` to stop enumerating skip reasons inline. Point at
  `workflow-integration-github/SKILL.md` § Workflow 2 step 4, which owns the complete six-row transmit
  table (`:160-165`), rather than restating a subset of it.
- **Done when:** `grep -rn "Only a finding with no" marketplace/bundles/` returns no hits, and Step 8
  contains no inline enumeration of `post_responses` skip reasons.
- **Suggested grouping:** plan-marshall workflow docs — RESPOND-loop prose

## G3 — Update the pr-doctor lifecycle's RESPOND description to the current skip taxonomy

- **Severity:** major
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md:135`
- **Evidence:** "For each terminal-disposition finding carrying a `thread_id` and `resolution_detail`,
  `post_responses` posts the stored `resolution_detail` as a thread-reply then resolves the thread;
  findings without a `thread_id` or `resolution_detail` are skipped, never guessed at". Wrong on two
  counts: a thread-bearing finding with no `thread_id` is `untransmitted`, not skipped
  (`github_pr.py:1630-1640`), and a genuinely threadless kind is batched rather than requiring a
  `thread_id` at all (`github_pr.py:1621`). Silent on the `already responded` skip this plan added.
- **Impact:** the second-most-read description of the RESPOND loop still describes the pre-fix,
  pre-kind-routing verb. An operator reading it will not expect a second run to be a no-op, which is the
  behaviour the plan set out to make legible.
- **Task:** replace the inline description at `:135` with a cross-reference to
  `workflow-integration-github/SKILL.md` § Workflow 2 step 4, following the same
  do-not-duplicate-the-table pattern the corrected Step 8 paragraph uses.
- **Done when:** `automated-review-lifecycle.md` § Step 4.5 states no skip taxonomy of its own and
  cross-references the owning table.
- **Suggested grouping:** workflow-pr-doctor / review-apparatus — respond-loop consumer contract

## G4 — Record the second `post_responses` invocation site, and give `threads_resolved` a source

- **Severity:** minor
- **Kind:** false-report-claim / incomplete
- **Where:** claim in `doc/plans/review-apparatus/070-post-responses-retransmits-already-sent-replies/report-01.md`
  § D0 ("**sole production invoker**"); the missed site is
  `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md:137-140`,
  and the unsourced field is `:157` (`threads_resolved: {N}`).
- **Evidence:** `automated-review-lifecycle.md` § "Step 4.5: RESPOND — transmit dispositions to the PR"
  carries its own invocation block:

  ```bash
  python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
    post_responses --pr-number {pr_number} --plan-id {plan_id}
  ```

  so "sole production invoker" is false. `grep -rn "post_responses --pr-number\|github_pr \\" marketplace/bundles/ --include=*.md`
  separates executable blocks from prose references and returns exactly two such blocks outside
  `workflow-integration-github/SKILL.md`'s own canonical-invocation catalogue: this one and
  `verification-feedback.md:246`. Separately, § Step 5 emits `threads_resolved: {N}` with no derivation
  anywhere — `grep -rn "threads_resolved" marketplace/ test/ .claude/` returns that single line, so
  nothing in the tree computes it and an agent executing the document must invent it.
  ⚠ `threads_resolved` is **not** a demonstrated reader of `count_responded`, and could not honestly be
  one: a batched disposition is counted in `count_responded` while resolving no thread. The defect is a
  missed invocation site plus an unsourced output field, not a fifth consumer of the count.
- **Impact:** no behavioural impact — no code reads `count_responded` — but the GATE deliverable's one
  job was the enumeration, and the next change to this field would inherit a derivation that stopped at
  the literal identifier.
- **Task:** give `threads_resolved` an explicit derivation in `automated-review-lifecycle.md` § Step 5 —
  the count of `responded[]` entries with `resolved_on_provider: true` is the honest one — and state that
  it names this round only. Record both invocation sites in the plan's consumer set. When re-deriving a
  field's consumer set in future, derive over invocation sites and their documented outputs as well as
  over the literal identifier.
- **Done when:** `automated-review-lifecycle.md` states the source expression for `threads_resolved`, and
  the consumer set recorded for `count_responded` names both invocation sites.
- **Suggested grouping:** workflow-pr-doctor / review-apparatus — respond-loop consumer contract

## G5 — Document `responded` / `responded_at` and `resolve`'s marker-clearing side effect in manage-findings

- **Severity:** minor
- **Kind:** omission / stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md`
  § Plan Finding Record (Required Fields table at `:72-80`, Optional Fields table at `:84-94`);
  `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md:322-329` (§ resolve).
- **Evidence:** `grep -rn "responded" marketplace/bundles/plan-marshall/skills/manage-findings/` returns
  hits in `.py` files only — zero in either document. `jsonl-format.md`'s Optional table lists `file_path`,
  `line`, `component`, `module`, `rule`, `author`, `kind`, `reviewed_commit_sha`, `bot_kind`, and the
  record example at `:51-68` carries `promoted` / `promoted_to`, but nothing names `responded` or
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

## G6 — Correct the stale marker prose on the Sonar surface and in `_findings_core`

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md:148`;
  `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py:705-716` (the
  `cmd_post_responses` docstring) and `:745-747` (the inline skip comment);
  `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:475`
- **Evidence:** the Sonar SKILL.md says "It is idempotent — a finding whose dismissal was already
  transmitted carries a `responded` marker and is skipped on a re-run, so re-invoking the verb never
  re-POSTs the same dismissal." After this plan that is incomplete: `_findings_core.py:476-481` clears the
  marker on a changed disposition, so a re-decided dismissal *does* re-POST — a real behaviour change to
  Sonar delivered without touching `sonar.py` and without updating its documentation. `sonar.py:745-747`
  restates the same over-claim in code ("Skip it so a re-run of `post_responses` never re-POSTs the same
  dismissal"), and the verb's docstring at `:705-716` documents no idempotency contract at all — unlike
  `github_pr.cmd_post_responses` (`:1533-1544`) and `gitlab_pr.cmd_post_responses` (`:356-367`), which each
  carry a full "Idempotent across rounds, keyed on (finding, disposition)" paragraph. Separately,
  `_findings_core.py:475` enumerates "every provider that reads the marker (GitHub, Sonar)", which the
  GitLab fix (`b19ef4a6`; `gitlab_pr.py:409`) made incomplete.
- **Impact:** the Sonar surface's documented contract under-describes its behaviour in the one direction
  that transmits to a third party, and says so twice — once to operators and once to the next reader of
  the code. The `_findings_core` comment misnames the set of readers a future change would have to
  consider.
- **Task:** extend `workflow-integration-sonar/SKILL.md:148` with the changed-disposition clause, matching
  the wording already used in `workflow-integration-github/SKILL.md:169` and
  `workflow-integration-gitlab/SKILL.md:74`; correct `sonar.py:745-747` and give
  `sonar.cmd_post_responses` the same docstring paragraph its two sibling verbs carry. Update
  `_findings_core.py:475` to name GitLab, or better, drop the enumeration and say "every provider respond
  verb".
- **Done when:** the Sonar SKILL.md and `sonar.py` both state that a re-decided dismissal re-transmits,
  and no comment or doc enumerates the marker's readers as a two-element set.
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
  finds only marker-persisted-after-success (`:409`), rerun-skips-already-responded (`:429`), and
  failed-post-does-not-mark (`:458`). No test re-resolves a Sonar finding to a different disposition and
  asserts it transmits again.
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
  and `:476-481`
- **Evidence:** `updates['resolution_detail'] = detail` is written only `if detail:`, while the clear at
  `:479` fires on `resolution_changed or detail_changed`. A `resolve` that changes the resolution without
  supplying a new `--detail` therefore clears the marker and leaves the old reply body. Probe against the
  real module and store:

  ```text
  after change -> responded: False | detail: 'Accepted: original words.' | resolution: rejected
  round2 count_responded: 1
  round2 body identical to round1: True
  ```

  The documented triage flow always passes `--detail` (`automated-review-lifecycle.md:131`, and every
  resolve block in `plan-marshall/workflow/triage.md` — `:203`, `:211`, `:228`, `:240`, `:258`), but the
  CLI makes it optional (`manage-findings/SKILL.md:325-327`), so a caller can reach this. The condition's
  two disjuncts are also never exercised separately: the only clear-on-change test
  (`test/plan-marshall/manage-findings/test_findings_store.py:623`) changes the resolution **and** the
  detail in one call.
- **Impact:** the reviewer receives the identical words twice — the plan's defect #1 in a narrower case —
  and the second send is counted in `count_responded` as a new disposition.
- **Task:** decide and implement one of: (a) clear the marker on a resolution change only when a new
  detail accompanies it, and reject a bare resolution change on an already-transmitted finding with a
  typed error naming the missing detail; or (b) keep the clear and have the respond verbs treat an
  unchanged `resolution_detail` as nothing-new-to-say. Option (a) is the smaller change and keeps the
  reviewer-facing text and the disposition in step. Record the choice in `jsonl-format.md` alongside G5.
- **Done when:** a test resolves a transmitted finding to a new resolution with no `--detail` and asserts
  the reviewer receives no duplicate body; a second test isolates the detail-only-change disjunct; and the
  chosen semantics are documented.
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
  key exists, so the vacuous-set guard guards nothing. `test/_shared/_dispatch_roster.py:25-63`, the
  pattern the plan named and the docstring cites, parses its population out of a document at test time
  (`section_lines` + `parse_roster_rows`) and raises when the heading is absent (`:47`). The plan's
  Verification section additionally demands "the consumer-population size published in the **test
  output**"; the size is published in `report-01.md`, and no test emits it.
- **Impact:** the guard that exists to prove the count-field family is fully covered proves only that two
  named keys hold two expected values — which the (a) test already proves. The test's remaining
  assertions are sound; it is the derivation framing that is not. The plan's anti-hand-list discipline was
  applied to the report and not to the test.
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
  `workflow-integration-github/SKILL.md:162`, `workflow-integration-gitlab/SKILL.md:74`,
  `workflow-integration-sonar/SKILL.md:148`; asserted in seven test sites
  (`test_github_pr.py:1645,1679,1732,1765-1766`, `test_gitlab_pr.py:382,414`,
  `test_fetch_findings.py:454`)
- **Evidence:** every other `skipped[].reason` in the GitHub verb is a snake_case token —
  `{'hash_id': hash_id, 'reason': 'no_resolution_detail'}` (`:1612`), and `'pr_number_unrecorded'` /
  `f'belongs_to_pr_{finding_pr}'` (`:1591`) — while the new one is the space-separated phrase
  `'already responded'`. The phrase was copied from Sonar, whose own vocabulary is mixed
  (`'no issue key in detail'` at `sonar.py:754`). `grep -n "'reason':" .../github_pr.py` shows these are
  the verb's only four `skipped[]` reasons; the prose strings in `untransmitted[]` are a different field.
- **Impact:** a consumer matching skip reasons as tokens (the shape every other GitHub reason invites)
  will not match this one. The inconsistency is inside a single `skipped[].reason` field.
- **Task:** rename to `already_responded` across the three providers, the three SKILL.md tables and all
  seven test assertions, in one change so the three providers keep a single vocabulary. Note this is a
  cross-provider rename with no production reader (verified by the same sweep that produced G4), so it is
  safe; do it together with G5's documentation so the field's contract is written down once, in its final
  form.
- **Done when:** `grep -rn "'already responded'" marketplace/bundles/ test/` returns no hits and the full
  test slice for the three providers passes.
- **Suggested grouping:** workflow-integration-github / gitlab / sonar — respond-verb return vocabulary

## G12 — Stop discarding `mark_finding_responded`'s error return

- **Severity:** minor
- **Kind:** bug (latent)
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:1662,1679`;
  `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py:433`;
  `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py:764`
- **Evidence:** all four call sites invoke `mark_finding_responded(plan_id, hash_id)` as a statement and
  ignore the result. `_findings_core.py:573-575` returns `{'status': 'error', 'message': …}` when the
  underlying write finds no record, and `jsonl_store.update_jsonl_in_dir` (`:110-123`) returns False
  exactly when no `*.jsonl` under the findings directory holds the hash. A failed stamp is therefore
  silent, and the disposition it failed to mark is re-transmitted on the next pass — the defect this plan
  closed, reopened by an unobserved write failure.
- **Impact:** latent today: the `hash_id` came from `query_findings` on the same plan within the same
  call, so the record exists under single-process use. The branch becomes live the moment a concurrent
  writer, a partial-write recovery, or a store-layout change can remove or relocate a record mid-pass —
  and it fails open, silently.
- **Task:** check the return at all four sites. On `status: error`, record the finding in the verb's
  failure channel with a reason naming the unstamped marker (so the operator learns the reply will be
  re-sent), and make the envelope `status` reflect it rather than reporting a clean `success`.
- **Done when:** a test forces `mark_finding_responded` to return the error status and asserts the verb's
  return names the unstamped finding rather than reporting an unqualified success.
- **Suggested grouping:** workflow-integration-github / gitlab / sonar — respond-verb failure paths

## G13 — The self-response bound named as C1's backstop cannot count a duplicated thread reply

- **Severity:** minor
- **Kind:** stale-doc / fail-open claim
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md:141`; the
  mechanism it names is `github_pr.py:1224-1225` (`current_cycle_self_response >= _SELF_RESPONSE_LOOP_BOUND`),
  `:393` (`_is_self_authored_response`), `:347` (`_SELF_RESPONSE_HEADING`)
- **Evidence:** SKILL.md:141 concedes that the self-response filter "cannot be complete — a thread-bearing
  disposition whose resolve-thread failed leaves an unresolved reply carrying arbitrary
  `resolution_detail` text and no transmission shape at all — so a bound backs it", and then explains the
  bound as "every turn of the cycle leaves one permanent response comment on the PR, so the PR's own
  comment list IS the iteration counter". But the counter only sees bodies that pass
  `body.lstrip().startswith(_SELF_RESPONSE_HEADING)` with `_SELF_RESPONSE_HEADING = '## Triage
  dispositions'` (`:347`), and that heading is written only by `_build_batched_response_body` (`:1473`).
  A thread reply posts the bare `resolution_detail` (`:1644`), so it matches nothing, never increments
  `count_self_response_current_cycle`, and never trips the bound.
- **Impact:** the one sentence in the bundle that acknowledges the C1 hole also asserts a backstop that
  cannot observe it. A reader who trusts it concludes the duplicate-reply loop is bounded when it is not,
  which is why the hole survived: the concession is present, the mitigation is not.
- **Task:** correct `SKILL.md:141` to state what the bound actually counts (batched self-response
  comments, recognised by the start-anchored heading) and that a repeated thread reply is outside its
  reach, cross-referencing G1 as the fix that removes the loop rather than bounding it. Do not widen the
  recognizer to match arbitrary `resolution_detail` bodies — the start anchor is deliberate and
  load-bearing (`:379-383`).
- **Done when:** `SKILL.md:141` no longer claims the bound backs the thread-reply case, and names the
  shape the bound does count.
- **Suggested grouping:** workflow-integration-github — self-response loop contract
