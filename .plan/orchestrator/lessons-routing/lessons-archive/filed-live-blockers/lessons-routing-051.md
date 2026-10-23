# Review-bot registry: refusals are filed as findings, and participation is mis-credited

Severity: high. Bundle: **plan-marshall** (`automatic-review` bot registry and participation checks, `phase-6-finalize` create-pr/merge path). Filed under RULING 2026-10-09 (a).

Recurrence of `lessons-routing-030` (Sourcery budget refusal), which this filing extends with new instances and two further bot-interface defects.

## Sources

- corpus `2026-10-12-05-002`, `2026-10-13-14-001`, `2026-10-13-14-003`
- inbox `pm-mcp-core-m2-m4-309`, `-323`, `-353`, `-365`, `-384`

## Consolidated statement

Four bot-interface defects, all of which turn a non-review event into either a false finding or an avoidable operator prompt:

1. **Sourcery's review-budget notice is not a registered refusal.** The wording ("has used its review budget of 2,500,000 diff characters for the last 7 days … another review is possible in about 16h27m via @sourcery-ai review") leaves `refused_bots[]`, `unrecognised_refusal[]` and `refusal_pattern_drift` empty, so the producer files it as an ordinary `pr-comment` finding and unified triage must recognise and accept it by hand — three separate plans hit this.
2. **An optional bot's budget decline stops the run.** With `re_review_on_timeout: ask`, trigger-B routes the same notice into the timeout sub-block and raises `escalate_ask` although both required bots were satisfied at the HEAD; the operator answered "Merge anyway - proceed unreviewed". A budget refusal should be recorded once per PR (or rate window, through the review-bot rate-window claim) as `declined: budget`, inherited by later heads without asking again.
3. **A required bot's structural refusal is not escalated.** On a 198-file PR, CodeRabbit (required) answered "Review skipped: 198 files exceed the limit of 100". The reply was filed as an ordinary finding and automatic-review took a plain participation loop_back twice instead of `escalate_ask{reason: refusal_structural}`, because the refusal branch keys on the comment wait's rate-limit list rather than the participation check's `refused_structural` state; CodeRabbit's `refusal_patterns` also miss that wording. The PR was finally rebuilt as a 5-PR stack: ~4.1M tokens.
4. **Participation is credited from an edited comment, and trigger-B reads other PRs' findings.** CodeRabbit was credited `participated_but_empty` from a pre-existing issue comment that had been edited in place (probably an earlier skip notice), while no new review object appeared; and trigger-B treated a bot finding carrying PR #1753's `reviewed_commit_sha` as evidence that PR #1759's reviews were stale.

Further: create-pr never compares the diff against the declared size caps of the **required** bots (`review_completeness size-caps` already knows CodeRabbit's 100-file cap), so the incompatibility is discovered only after CI and a review round; and the `automatic-review`/`lessons-housekeeping` `display_detail` templates are 87 characters with an em dash against an 80-ASCII contract that `mark-step-done` does not enforce.

## What is asked

- Add the Sourcery budget wording (with its ETA) as a `quota` refusal pattern, and make `refusal_pattern_drift` fire for a refusal-shaped comment with no code content.
- Record a budget/rate refusal once per PR or rate window as `declined: budget`, inherit it for later heads, and never escalate an optional bot's decline to an operator prompt.
- Route a required bot whose participation state is `refused_structural` into the refusal branch; add the "files exceed the limit" wording to the CodeRabbit registry; filter trigger-B's staleness input to findings of the current PR.
- Apply the bot's completion evidence (verdict marker, head SHA, or a review object after the trigger) to participation credit, and surface the credited comment's classification.
- Before `ci pr create`, read the required bots' size caps and stop with a prompt-required envelope (split / accept-gap) when the changed-file count exceeds one.
- Shorten the `display_detail` templates to 80 ASCII and have `mark-step-done` enforce the constraint; add a doc-contract test rendering each template at its longest plausible values.

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
