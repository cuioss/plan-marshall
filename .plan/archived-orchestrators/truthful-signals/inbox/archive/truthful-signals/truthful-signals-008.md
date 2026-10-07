envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-07-29T19:11:38Z

## Review-apparatus work that no plan in this repo can carry

### Why this message exists

PLAN-115 (launched), PLAN-116 (staged, six participation shapes) and PLAN-119 (staged) between them
own the plan-marshall side of the automated-review reliability work. This message records the part
that is **outside this repository**, so that those three landing is not mistaken for the apparatus
being fixed.

### The trap

PLAN-116 Shape F fixes how a stale review is **named** — a reporting-fidelity change. The thing that
**causes** the staleness is org-side and untouchable from here:

- after #1053, pr-agent subscribes to `opened` / `reopened` / `ready_for_review` only, so a rebase is
  invisible to it;
- `finalize-step-sync-baseline` rebases and force-pushes on every finalize, *after* the PR-open review.

So when PLAN-116 lands, the label becomes honest and the merge candidate still goes unreviewed. A
truthful `stale` reads as solved in a way a false `absent` did not. **Do not close the review-apparatus
theme on PLAN-116 alone.**

### The three items, none of them plannable here

1. **`cuioss-organization/.github/workflows/reusable-pr-agent-review.yml`** — narrow the fail-closed
   empty-review guard to the events pr-agent actually reviews, THEN set
   `github_action_config.handle_push_trigger` and `push_commands = ["/review"]`. Order matters: the
   runner legitimately returns no output on unchanged-SHA, merge-commit and bot-commit pushes
   (`github_action_runner.py:128-146`), so enabling the trigger first reproduces the failure on a
   subset of pushes instead of all of them. Carries the ~21-repo consumer release fan-out.
   ⛔ Rejected remedy, do not adopt as a shortcut: downgrading empty-review to a warning. The runner
   exits 0 when every model call fails, and this guard is the only thing separating "reviewed, found
   nothing" from "never reviewed". That ambiguity already cost a real misread on #1024.
2. **`cuioss/pr-agent-settings` #13** — the security-weighted charter is unverified. Oracle: a
   `/review` on plan-marshall#1042. Pass condition is **shaped, not counted** — if only Major-severity
   findings come back, the severity clause did not take. A finding count says nothing.
3. **plan-marshall#1059** — post-merge revisit still owed. It merged with no bot review of its final
   HEAD `cf634762`: pr-agent reviewed `acbdcecf3` 75 minutes earlier, CodeRabbit was genuinely
   rate-limited (body carries `rate limit`), Sourcery hard-refused.

### Ask

Route 1 and 2 to the operator as org-repo work rather than staging them. Item 3 falls under the
standing post-merge-revisit rule and belongs with the other four already owed (#1055, #1057, #1058,
#1061).
