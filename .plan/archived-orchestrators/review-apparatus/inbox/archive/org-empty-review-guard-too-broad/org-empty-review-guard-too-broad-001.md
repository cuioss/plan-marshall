envelope_version=1
sender_type=plan
sender_id=org-empty-review-guard-too-broad
epic=review-apparatus
kind=landing
created=2026-08-08T11:08:06Z

## Landing — PLAN-PR-002 (org empty-review guard too broad)

**Shipped as `cuioss/cuioss-organization` PR #235** (OPEN, base `main`, head
`fix/pr-agent-empty-review-guard-scope`, commit `75de9ac`, 3 files:
`.github/workflows/reusable-pr-agent-review.yml`, `docs/Workflows.adoc`,
`test/workflow/test_pr_agent_review_guard.py`). No plan-marshall file was touched —
the host worktree diff was empty at every point, by the plan's own design, so the
plan-marshall-side finalize was scoped to bookkeeping only and NO empty host PR was
created. There is no plan-marshall PR for this plan, and none should be expected.

### What landed

The guard's `pull_request` arm now mirrors the runner's own
`GITHUB_ACTION_CONFIG.PR_ACTIONS` allow-list via
`contains(fromJSON('["opened","reopened","ready_for_review","review_requested"]'),
github.event.action)`. The `issue_comment` + `/review` arm and the step body are
untouched: `exit 1` on an empty `REVIEW_OUTPUT` is byte-for-byte unchanged and was
never downgraded to a warning (the PROHIBITED remedy). A new `EXCLUDED` comment block
enumerates every legitimately-empty population with the reason each is excluded.
`docs/Workflows.adoc` § PR Agent Review → Verification moved in lockstep.

### Four spec claims were REFUTED at outline — two change the framing

1. **The defect is LATENT, not live.** No caller subscribes to an action outside the
   allow-list today, so the gate never evaluates on the push population. The
   false-failure fan-out was a future consequence of step (2), not a present one. The
   spec's sequencing insistence was right; its urgency framing was not.
2. **The spec's own "synchronize framing is moot" exclusion is WRONG.** `#1053`
   reverted a PR, not the mechanism: `handle_push_trigger` is reachable ONLY from the
   `pull_request` branch under `action == "synchronize"`. Step (2) therefore
   NECESSARILY means adding `synchronize` to callers' `types:`. Honouring that
   exclusion literally would have produced a fix that cannot be enabled. **Any sibling
   plan carrying forward that exclusion should drop it.**
3. **The runner exposes NO discriminator.** `github_action_output(data, 'review')` is
   called from `PRReviewer._prepare_pr_review()`, reachable only after a successful
   prediction — so every skip path, legitimate or failed, leaves `outputs.review`
   empty. The spec's "if refuted, re-scope before implementation" branch fired: the
   discriminator is derived from the runner's ACTION ALLOW-LIST, not from runner
   output. No push-reason field is re-derived in YAML, so the stated prohibition holds.
4. **`docs/automatic-review/pr-agent.md` does NOT document the guard.** The hypothesised
   file was out of scope; `docs/Workflows.adoc` § Verification was in scope and was the
   one asserting the now-imprecise "covers both paths that produce review output".

Two populations the spec did not name are live TODAY on the `pull_request` path —
"PR has no files" and "empty post-filter diff" — and remain inside the gated set as an
enumerated, accepted residual.

### Open residual the operator accepted (R1)

Once step (2) lands, a `synchronize` run whose every model call failed will be
UNGATED, and claim 3 establishes there is no runner state to fix that. Operator
decision: **accept the residual** — the `/review` comment path (what automation depends
on) stays fully gated, and the workflow documents the gap in-file. A follow-up plan
owns step (2): set `handle_push_trigger` + `push_commands = ["/review"]` in
`cuioss/pr-agent-settings` AND add `synchronize` to callers' `types:`. Do not enable
the trigger without re-reading R1.

### Finding for the epic — plan-marshall cannot target a foreign checkout

`ci.py` declares NO `--project-dir` and NO `--repo` at any level; it resolves the repo
from cwd via `gh`, so the CI abstraction structurally CANNOT open a PR in a foreign
checkout. The spec's "use the CI abstraction's `--project-dir` form for this repo"
premise is FALSE. plan-marshall also implements no external-repo lane at all. This plan
worked around it with a dedicated landing deliverable using `git -C {checkout}` +
`gh -R`, declared in-deliverable. Left unclosed here because the spec forbids touching
plan-marshall. **This is a real gap worth its own plan**: every consumer-repo plan will
re-derive the same workaround, and the phase-6 finalize flow will keep offering to
manufacture an empty host PR (guarded here only by an operator prompt).

### Sibling slices of the PLAN-116 split — unaffected

PLAN-PR-001 (Defect A), PLAN-PR-005 (C+E), PLAN-PR-006 (D), PLAN-PR-007 (F) were not
absorbed and are not touched by this landing.
