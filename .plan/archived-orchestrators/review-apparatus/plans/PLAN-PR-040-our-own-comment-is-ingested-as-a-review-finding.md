# PLAN-PR-040: Our own comment is ingested as a review finding

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-059` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; its four deliverables and its 2026-09-04 D-FOLD are carried there as D6–D9.
> ⛔ **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of every
> deliverable body, and `PLAN-PR-059` points here rather than retyping it.

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Drained from inbox message `truthful-signals-030.md` (2026-08-23) and corroborated
> FIRST-PARTY against this repository before staging.

## Objective

The producer's self-response filter decides whether a PR comment is *ours* by testing whether the
body **starts with a heading literal**. Any comment we author that opens with anything else is not
recognised as ours and is ingested as a review finding — so the epic that exists to measure our
reviewers mis-measures them with our own text. Replace the start-anchored heading test with an
**author-identity** test, and keep the heading test only as a secondary signal.

This is a false-POSITIVE defect: a comment enters the finding set that should never have been a
candidate. It is the mirror of PLAN-PR-029 D1, which is a false-NEGATIVE (a genuine finding dropped
by the noise filter) in a different function with a different failure mode — which is why it is
staged here rather than folded there.

## Deliverables

1. **Key the self-response filter on author identity.** The viewer/App login is already reachable in
   this module — `_github_pr.py` resolves `viewer_login` and compares against it at another site. Use
   that, not the body text, as the primary test.
   - ⛔ **AMENDED 2026-08-29 (drained `truthful-signals-040.md`, corroborated first-party at HEAD
     `a1cae6102`): D1 must NAME THE TRADE IT MAKES, not inherit it.** An author-identity primary key
     buys robustness against a renamed heading at the cost of DETECTION: a batch comment an agent
     hand-authored instead of routing through `post_responses` is then *recognised as ours and
     silently swallowed* — the bypass becomes invisible rather than merely mis-filed. The source
     report names this trade against its own variant ("it makes the filter tolerant of bypasses
     rather than surfacing them, so it trades detection for robustness"). This is NOT an argument
     that D1 is wrong; it is a requirement that the spec choose the trade explicitly.
   - ⛔ **A SECOND, FIRST-PARTY limb the drained message did not name.** The recognizer's own
     docstring (`github_pr.py`:390-394) states the start anchor is the FALSE-POSITIVE BOUNDARY and is
     load-bearing: a human comment that quotes the heading is real reviewer feedback and MUST still
     be filed. The repo-owner account is BOTH the emitter identity and a genuine review-comment
     author — on PR #1361 alone `cuioss-oliver` authored 8 `inline` + 2 `issue_comment` rows. A naive
     author-identity primary key therefore swallows the operator's own genuine review comments. D1
     MUST preserve that boundary; an identity test alone does not.
2. **Keep the heading test as a secondary signal, never the sole one**, so a comment authored by us
   is recognised whatever it opens with, and a comment authored by someone else that merely quotes
   our heading is not swallowed.
   - ⭐ **THIRD ARM, drained 2026-08-29 and compatible with an author-identity primary test.** On
     fetch, an `issue_comment` authored by the PR actor that carries the batch's STRUCTURAL SIGNATURE
     — the emitter builds it at `github_pr.py`:1967-1968, rendering `### In reply to comment_id:
     \`{id}\`` (or `comment_id: _(unrecorded)_`) — but
     does NOT start with `_SELF_RESPONSE_HEADING` is almost certainly a hand-authored emitter bypass.
     Filing THAT as a `triage` finding surfaces the defect at its source instead of laundering it
     into the next round's work list. This is what preserves detection under D1's re-key.
   - ⭐ **The cheapest arm, addressing the OBSERVED cause directly:** state at the call site that
     every thread-less disposition batch is transmitted via `github_pr post_responses`, and that an
     agent must not compose the comment body itself. The observed incident (API-Sheriff PR #230) was
     exactly this bypass — the filter did its job; nothing detects a caller that never uses the
     emitter at all.
3. **A test that fails on the current code**: a self-authored comment whose body opens with something
   other than `## Triage dispositions` is not ingested as a finding. ⛔ The test must be seen to fail
   before the fix — the reported instance opened `## Non-goals (restored)`.
4. **Re-derive the count of already-mis-ingested comments in this repository's findings corpus** and
   record it in the run report. It is a measurement correction, not a code change, and it belongs to
   this plan because this plan establishes the mechanism that produced it.
   - ⛔ **NAME THE INSTRUMENT, and state its coverage as a derived figure.** D4 ATTRIBUTES the 43
     `cuioss-oliver` `issue_comment` records by author, so it must declare which population its
     instrument returns and publish the denominator alongside the count. A zero from an instrument
     whose coverage was not stated is a *could-not-look* zero, not a refutation.
   - ⚠ **A RELAYED DIAGNOSIS OF THIS ITEM IS REFUTED — do not adopt it.** The drained message
     (`truthful-signals-040.md` § 3) warned that `ci pr comments` "structurally excludes the comment
     class it is counting" because its help reads *"Get PR inline code comments"*
     (`ci_base.py`:1095, corroborated). **The help string is narrower than the behaviour.** Run
     first-party against PR #1361 at HEAD `a1cae6102`, `ci pr comments` returned THREE kinds —
     `inline`, `review_body`, AND `issue_comment` (≥6 `issue_comment` rows, of which 2 `cuioss-oliver`
     and 2 `cuioss-review-bot`). ⇒ The instrument does NOT exclude `issue_comment`, and D4 may use
     it. What remains genuinely UNEXPLAINED is the observation that prompted the warning: the same
     verb run against a FOREIGN repo (`--project-dir …/API-Sheriff`, PR #230) returned `total: 48`
     with ZERO `issue_comment` rows. That is an open question about the FOREIGN-TARGETING path, not
     about the verb's population — D4 must not inherit the refuted framing, and must validate
     coverage on whatever repo it actually measures.

Four deliverables, comfortably inside the split guard.

### D-fold — The filter is keyed on BODY SHAPE, not AUTHOR, and that makes the error SELF-AMPLIFYING

⭐⭐ **Folded from `truthful-signals-053.md` item 1 on 2026-09-08** (their `-019`, relayed from the
`lessons-handling-26-09-04-01` drain).

**The word to keep is *self-amplifying*.** A filter that recognises the pipeline's own replies by what
they **LOOK LIKE** rather than by **WHO WROTE THEM** mis-classifies any third-party comment sharing the
shape — **and each mis-classification produces another comment of that shape.**

⇒ ⛔ **The error rate is not constant; it feeds itself.** That is the difference between this and an
ordinary false-positive class, and it is why the keying matters more than the accuracy of the pattern.

⚠ **The loop half may already be closed.** This meets the shipped
`self-ingested-reply-is-a-non-terminating-barrier-loop` work. **D0 must establish whether that loop is
closed and the filter is STILL shape-keyed** — if so, **the residue is the KEYING, not the loop**, and
this fold adds one deliverable rather than re-opening shipped work. ⛔ Do not re-stage the loop.

*Done when:* self-recognition is keyed on **author identity**, and any residual shape heuristic is a
secondary confirmation that cannot promote a third-party comment on its own.

## Claim Labels

- OBSERVED: the filter is start-anchored on a heading literal — read at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`:404,
  `return body.lstrip().startswith(_SELF_RESPONSE_HEADING)`, with
  `_SELF_RESPONSE_HEADING = '## Triage dispositions'` at :358.
  ⚠ **LINE DRIFT CORRECTED 2026-08-29** (was :393 / :347; re-derived at HEAD `a1cae6102`). The
  PREDICATE and the CONSTANT are unchanged — only their line numbers moved.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD (was 19453cb). Intersection over 5 declared paths: 3 hits - github_pr.py, _github_pr.py, test_github_pr.py. Both script diffs READ: github_pr.py is router plan-id re-injection only; _github_pr.py is a single hunk adding _SHA_TOKEN and bot_claimed_sha_matches_head. Neither touches the self-response filter. Premise intact.
- OBSERVED: an author-identity comparison already exists in the sibling module — read at
  `_github_pr.py`:1211, `(n.get('author') or {}).get('login') == viewer_login`, resolved by
  `get_viewer_login()` at :1121 and called at :1182. The identity is therefore reachable, and
  deliverable 1 is a re-key rather than new plumbing.
  ⚠ **LINE DRIFT CORRECTED 2026-08-29** (was :982; re-derived at HEAD `a1cae6102`). This drift was
  NOT named by the drained message and is the load-bearing one of the three — D1 depends on this site
  being a usable identity comparison, so a stale citation here is worse than a stale predicate cite.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded FIRST-PARTY at HEAD (was a1cae6102). Mechanism holds - get_viewer_login and the author-identity comparison survive, so D1 remains a re-key rather than new plumbing. LINE DRIFT, DERIVED NOT GUESSED: _github_pr.py received exactly one hunk in this window, 25 inserted lines at line 317, so every coordinate below 318 shifts by exactly +25. The cited sites 1121/1182/1211 now read 1146/1207/1236. The recorded caveat is unchanged and still load-bearing: an author-identity primary key would swallow the operator own genuine review comments.
- OBSERVED: the module's own docstring already concedes "the self-response filter cannot be
  complete" (`github_pr.py`:17) and carries a bounded `(self-response-loop)` guard for the case it
  misses. ⭐ The incompleteness is DOCUMENTED and not CORRECTED — the same shape as the pr-agent
  `issue_comment` bucketing this epic already tracks.
- OBSERVED: the corpus carries **43 `cuioss-oliver` records, every one an `issue_comment`** — read
  from the 2026-08-23 corpus pass in `findings/2026-08-23-pr-agent-vs-coderabbit-corpus.md`. They
  were excluded from that analysis's bot comparison as author records, which was correct there and
  is the population deliverable 4 re-derives here. ⚠ **Not every one of the 43 is necessarily a
  mis-ingestion** — some are legitimate author comments a reviewer replied to. Deliverable 4 must
  ATTRIBUTE them, not assume them.
- HYPOTHESIS: the reported instance (`## Non-goals (restored)`, 1 of 10 findings on a foreign
  machine's run) is an instance of exactly this mechanism — confirm/refute at the same filter
  (verify-at-outline). The MECHANISM is corroborated first-party above; the INCIDENCE is a lead, and
  the originating plan archive is machine-local and unreachable from here.
- ⛔ **REFUTED FRAMING — DO NOT RE-ENTER (recorded 2026-08-29, drained `truthful-signals-040.md`).**
  A diagnosis that travelled onward from an older forwarded narrative claimed: *"the producer's filter
  is start-anchored on `## Review responses`, but `post_responses` emits other headings, so the tool
  re-ingests its own output as a fresh finding each round."* **BOTH halves are false**, re-verified
  first-party at HEAD `a1cae6102`:
  - `## Review responses` has **0 hits over the whole inventoried tree** (`architecture search
    --content`, 5268 files scanned, 0 unreadable, not truncated — a clean-coverage derived zero).
  - The emitter and the recognizer read **one shared constant**: `_SELF_RESPONSE_HEADING` at :358, the
    recognizer at :404, the emitter at :1965, and the comment at :352-357 states the shared-constant
    design in as many words. **There is no emitter/recognizer drift and no version skew.**
  ⇒ Acting on that diagnosis would have "fixed" working code. ⭐ **This spec never carried the refuted
  framing** — its OBSERVED claim above names `## Triage dispositions` and re-corroborates at HEAD. The
  note exists solely to stop the withdrawn version re-entering; the spec is otherwise unaffected by it.
- OBSERVED (added 2026-08-29): **nothing detects an emitter bypass.** The filter excludes what the
  sanctioned emitter produces and makes no claim about arbitrary text an agent invents, so the
  shared-constant guarantee is ONE-DIRECTIONAL — it prevents a *rename* from reopening the loop, but
  cannot bind a caller that never uses the emitter at all. Corroborated by reading the fetch path: the
  recognizer at :404 is the only self-response test, and no author or structural-signature check
  exists beside it. This gap is what deliverable 2's third arm addresses.
- Verify-first clause: whether the App posts as the same login the viewer resolves to must be settled
  before scoping — if the response comment is authored by a different identity than the one
  `viewer_login` returns, deliverable 1 needs that identity instead and the fix is not a one-line
  re-key.

### D-FOLD 2026-09-04 — the filter must key on *"a comment this workflow wrote"*, not on author or reply relationship

⭐ **Folded from `truthful-signals-045.md` §2.8** (relayed from cui-http — ⛔ a foreign LEAD; the named
plan-marshall surfaces are local and corroborable, the cui-http evidence is not).

`@coderabbitai` / `/review` comments **the orchestrator posts to invoke a reviewer** are ingested as
findings and dismissed one by one at triage. ⛔ The filter keys on **author or reply relationship**; the
correct criterion is **provenance — a comment this workflow wrote**. Pure recurring tax, and it inflates
the pending-findings count with our own output.

*Done when:* a trigger comment this workflow authored is excluded at ingestion by provenance, and the
exclusion is reported (how many, and why) rather than silently applied. **Matched negative control
required:** a genuine bot comment that happens to quote a trigger string is still ingested.


## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`:358,:404 —
  `_SELF_RESPONSE_HEADING`, the filter predicate (re-derived at HEAD `a1cae6102`; was :347,:393)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`:1950-1971 —
  `_build_batched_response_body`, the EMITTER. Added 2026-08-29: deliverable 2's third arm keys on the
  structural signature this function renders, so the emitter is in scope, not merely the recognizer.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`:1121,:1182,:1211 —
  `viewer_login`, the identity source (re-derived at HEAD `a1cae6102`; was :982)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — the
  transmit/ingest contract, if the filter's basis is documented there (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⛔ Overlaps with FIVE staged specs on `github_pr.py` / `_github_pr.py` / `test_github_pr.py` —
  **PLAN-PR-024, PLAN-PR-025, PLAN-PR-029, PLAN-PR-034, PLAN-PR-035** — making this the SIXTH claimant
  of that file family. Derived from `corpus cross-check`, not counted by hand: an earlier draft of this
  spec said "three staged specs / fourth claimant" and was wrong, because PR-034 and PR-035 claim it
  too. This spec must never run concurrently with any of the five.
- ✅ **No LIVE-plan collision.** Every one of PLAN-PR-040's cross-check overlaps is `corpus_spec`; none
  is `live_plan`. It is emittable on the disjointness test today — the contention above is with STAGED
  siblings, which is a sequencing constraint, not a block.
- ⛔ **Corrupts PLAN-PR-035's denominator.** PR-035 measures "13 of 43 observed findings unanswered".
  If some of those 43 were our own comments mis-ingested by this filter, the denominator is wrong and
  the ratio with it. PR-035's D0 attributes the thirteen before anything is fixed — **that
  attribution must account for this mechanism**, whichever plan runs first. Recorded on both specs.
- Adjacent to: PLAN-PR-029 D1 (`_is_obvious_noise`, the shared `ignore.low` layer). Same file, same
  broad area, OPPOSITE direction — D1 drops genuine findings, this admits non-findings. Deliberately
  not merged: D1's Done-when is entirely about noise-drop behaviour, and PR-029 already sits at six
  deliverables.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-040-our-own-comment-is-ingested-as-a-review-finding.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
