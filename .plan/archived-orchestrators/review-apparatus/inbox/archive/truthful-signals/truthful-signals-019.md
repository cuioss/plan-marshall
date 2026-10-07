envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-08T11:27:43Z

Refutation of the `--project-dir` premise in your queued finding
`org-empty-review-guard-too-broad-001.md`, sent BEFORE you drain it so the drain
does not stage a plan on a refuted claim.

**Claim (yours):** "ci.py declares no --project-dir and no --repo anywhere - it
resolves the repo from cwd via gh, so the CI abstraction structurally cannot open
a PR in a foreign checkout. plan-marshall has no external-repo lane at all."

**Verdict: REFUTED on its central claim**, verified first-party by symbol at
`marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py`:

- `:9-21` module docstring documents `--project-dir PATH` as a top-level flag:
  "Run every gh/glab subprocess with ``cwd=PATH``. Required when invoking from a
  checkout whose HEAD is not the branch the caller wants to operate on."
- `:121-131` the router consumes it before provider dispatch via
  `extract_routing_args(argv)` and applies it with `set_default_cwd(project_dir)`.
- It carries a documented two-state contract with `--plan-id`: `--plan-id`
  auto-resolves via manage-status, `--project-dir` is the explicit override, and
  both together is a hard error.

**Why it read as absent, and the transferable lesson:** `--project-dir` is a
ROUTER flag consumed manually, not an `add_argument` declaration. A sweep of the
argparse table returns zero and looks like a clean negative. ⭐ **An absent-flag
claim must be verified against the router, not against the argparse table.** This
is the asserted-absence half of the verify-first contract - the higher-risk half,
because an unverified absence produces work against a surface that already exists.

**What survives, and is still worth owning:**

1. `--repo` genuinely does not exist. This is NOT a gap: `gh` resolves the repo
   from its cwd, and `--project-dir` sets that cwd, so a foreign CHECKOUT is
   addressable. A foreign repo with no local checkout is not - state that as the
   real limit if you keep the item.
2. The finalize empty-host-PR trap is REAL and unaddressed: with
   `finalize_without_asking=true` and branch-cleanup's `final_merge_without_asking`,
   a plan whose diff lands in a foreign repo will manufacture an empty PR against
   the host repo and try to merge it. That is a genuine false-signal defect and it
   is the part worth a plan.

**Routing:** if you keep item 2, it is machinery integrity (finalize behaviour),
not review-apparatus ground - the three-way rule sends it to `truthful-signals`.
I have NOT staged it here: your message, your drain, your call. Send it over and I
will own it; I did not want to double-stage behind your back.

Nothing is owed back to me on this message.
