envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=finding
created=2026-07-30T11:51:28Z

## Finding — PR #1067 was reviewed by 1 of 3 configured bots; the finalize still read green

**Type**: review-coverage gap
**PR**: #1067 (`feature/resolver-ext-point-seam`, head `405b05f069141ccb8367da57d90e958f89668a51`)
**Status**: not remediated — recorded so the epic can decide whether #1067 needs a
re-review pass and whether `review_rate_window_await` should be flipped.

## Observed

Three review bots are configured for this repository. On #1067:

| Bot | Outcome | Saw the diff? |
|-----|---------|:-------------:|
| pr-agent | reviewed | yes |
| coderabbit | `refused_awaitable` (rate-limited) | **no** |
| sourcery | `refused_hard` / `hard_quota` | **no** |

Both refusals were **detected and correctly classified** by the tooling — this is not a
silent failure of the bot-completion detector. The gap is what happened next: because
`review_rate_window_await=false`, an awaitable refusal settles as an ordinary
(non-blocking) outcome rather than parking the gate until the rate window reopens. The
`automatic-review` step therefore recorded `outcome=done` / "1 comment(s) found", and
`project:finalize-step-review-retrospective` recorded "1 reviewer compared, 0 actionable
comments (2 refused)".

Net effect: the finalize output reads green, and a reader who does not open the
retrospective's parenthetical would conclude the diff had been reviewed by the configured
reviewer set. It had not — two thirds of the configured reviewers never received it.

## Why this is worth the epic's attention

1. **The green is truthful about the step and untruthful about the coverage.** Every
   individual signal is accurate; the composite reads as review coverage that does not
   exist. That is precisely the confident-signal-hides-a-caveat shape, arriving from the
   review surface rather than from the build surface.
2. **`refused_awaitable` is, by name, the case where waiting would have worked.**
   coderabbit's refusal was rate-window-bounded and self-clearing. With
   `review_rate_window_await=false` the run declined a retry that was known to be viable.
   `sourcery`'s `hard_quota` refusal is genuinely unrecoverable in-run and is a separate
   question (quota, not timing).
3. **A refusal count in a `display_detail` parenthetical is not a gate.** "2 refused" is
   carried as narration alongside `outcome=done`. Nothing in the pipeline consumes the
   refusal count as a coverage signal.

## Suggested dispositions (epic decides)

- **For #1067 specifically**: schedule a post-merge revisit. coderabbit's window will have
  reopened; a late review on this PR should be read as a recurrence of the coverage gap,
  not as an incident.
- **For the tooling**: consider whether an `refused_awaitable` outcome should (a) engage
  `review_rate_window_await` by default, or (b) at minimum surface a distinct non-`done`
  outcome so a partially-reviewed PR does not present the same `display_detail` shape as a
  fully-reviewed one. The distinction the pipeline currently lacks is
  *reviewed-and-clean* vs *not-reviewed*.

## Standing rule this instance confirms

A green finalize is not evidence that the configured review bots saw the diff. Only the
per-reviewer participation record is. Two of three reviewers on this PR are on record as
having refused.
