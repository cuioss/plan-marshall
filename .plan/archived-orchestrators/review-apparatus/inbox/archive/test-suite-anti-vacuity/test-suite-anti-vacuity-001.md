envelope_version=1
sender_type=plan
sender_id=test-suite-anti-vacuity
epic=review-apparatus
kind=finding
created=2026-09-07T11:19:34Z

# Two automated-review detector defects observed on PR #1430

Both were reproduced repeatedly across five `automatic-review` FIND passes on
plan `test-suite-anti-vacuity` (PR #1430). Both are live on main.

## 1. `ci pr wait-for-comments` cannot see an in-place refusal edit

`wait-for-comments` returned `rate_limited_bots[]` carrying **only sourcery**
while CodeRabbit was in a quota refusal on the same HEAD. The refusal was
absent from that channel altogether.

Mechanism: the detector samples each bot's **newest** comment. CodeRabbit's
refusal arrives as an in-place **edit of its oldest** issue comment (the
persistent summary comment, created at PR open). `movement_matched_bots[]`
was likewise empty. Only `github_pr fetch_findings`, which reads comment
BODIES, caught it.

Consequence: a consumer that trusts `wait-for-comments` alone concludes no
rate limit is in effect and proceeds to merge on an unreviewed HEAD. The
standing operator rule *"a CodeRabbit refusal can also arrive as an in-place
edit — READ THE COMMENT BODY"* exists precisely because the tool does not do
it.

Site: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py`

## 2. `rate_limit_eta_patterns` misses a fourth ETA phrasing

Four distinct CodeRabbit ETA phrasings have now gone unparsed on this one PR:
`"36 minutes"`, `"2 minutes"`, `"57 minutes"`, and
`"Next included review available in 50 minutes."`

The last pass localised the gap precisely: `unrecognised_refusal[]` and
`refusal_pattern_drift[]` were **both empty**, so a declared `refusal_patterns`
arm DID match the notice. The failure is specifically in
`rate_limit_eta_patterns`, not in refusal detection.

An unparsed ETA means the awaitable-window branch cannot size its own wait and
the operator gets no bound.

Four phrasings on a single PR suggests pattern enumeration is the wrong shape:
derive the duration from a general number+unit match rather than adding a
fifth literal.

Site: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`

## Provenance

Finding hash ids in the originating plan's store: `a8a081` (1), `dda827` (2).
Routed here per the three-way finding-routing rule: PR/review-apparatus
defects come to this epic.
