envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=finding
created=2026-09-15T08:26:54Z

component=plan-marshall:tools-integration-ci
category=improvement

# No CI verb takes a commit sha, so a post-merge main-branch run is unreadable through the abstraction — the one defect in this batch that nothing tracks

⛔ **ROUTED FROM API-SHERIFF'S EPIC LEDGER.** An Open Defects group from the
`deployment-configurability` epic (`cuioss/API-Sheriff`), opened 2026-09-03 and locally closed
2026-09-11 with a `gh` workaround. Filed here by operator direction on 2026-09-15. ⚠ **Locally solved
is not upstream fixed**: the epic's entry is settled because a workaround exists, and the missing verb
is what is being reported.

## The obligation it blocks

The consuming repo's `CLAUDE.md` § Git Workflow step 8 assigns the ORCHESTRATOR the post-merge
main-branch run for the merge commit. That run is the **only** place `deploy-snapshot` ever executes —
`maven.yml` skips it on pull requests and runs it on `push: main` — so a snapshot-deployment failure
appears solely in the Maven Build run for the merge commit on `main`, addressable by **commit**, never
by PR number.

## Verification at plan-marshall `origin/main` 7a028157e (read-only, 2026-09-15)

**STILL-VALID, and NOT TRACKED anywhere.**

- `tools-integration-ci/standards/leaf-command-reference.md:107` — `checks status | exactly one of
  --pr-number or --head`; `:174` — "The branch flag is `--head`, **not** `--branch`". Both resolve a
  branch to a PR, so `--head <sha>` returns *"no pull requests found for branch <sha>"*.
- `checks pull-request-runs | --pr-number` only;
  `workflow-integration-github/scripts/github_ops.py:1819-1821` `cmd_checks_pull_request_runs` →
  `pull_request_runs_result(args.pr_number)`, and `:1791` errors with `'PR carries no head branch'` —
  PR-keyed throughout.
- `git grep -- '--commit'` across `tools-integration-ci` and `workflow-integration-github`: **zero
  hits.** No verb accepts a sha.
- Duplicate search over all five epics' `plans/*.md`, every live inbox, every archive and
  `lessons-learned/` for `gh run list`, `--commit`, `no pull requests found`: **no match.**

## The workaround the epic uses today, and why it is not the fix

```text
gh run list --repo <owner/repo> --commit <merge-sha> --json workflowName,status,conclusion,event
```

It works, and the consuming repo's own `CLAUDE.md` permits `gh` — but the orchestrator persona forbids
reaching for `gh`/`glab` directly and mandates the CI abstraction, so the sanctioned seat cannot perform
a step its own workflow doc requires. **The fix is a commit-addressed read in `tools-integration-ci`**
(a `--commit <sha>` form on `checks status`, or a `checks commit-runs` verb), returning the push-event
runs for that sha with the same shape the PR-keyed verbs already return.

---

## The retired API-Sheriff ledger entries, verbatim (resolution first, then the original defect)

- ✅ **SOLVED 2026-09-11 — THE MISSING READ IS ONE COMMAND, AND IT WORKS TODAY.**
  `gh run list --repo cuioss/API-Sheriff --commit <merge-sha> --json workflowName,status,conclusion,event`
  returns the main-branch (`event: push`) runs keyed by MERGE COMMIT — exactly the lookup the CI
  abstraction cannot express. Used it to discharge **both** outstanding post-merge checks in one pass:
  `7fce677` (PLAN-08) — Maven Build, Integration Tests, Demo Client E2E and Scorecard **all success**,
  closing the gap this entry recorded as unverifiable; and `6ee4a55` (PR #290) — the same four, all
  success.
  ⛔ **So the defect is NOT structural, it is a missing verb**: `ci checks status` takes
  `--pr-number` / `--head` and resolves both to a PR. **The fix is a commit-addressed read in
  `tools-integration-ci`**, and it belongs upstream in plan-marshall. Until it lands, the sanctioned
  route for a post-merge check is `gh run list --commit`, which CLAUDE.md already permits
  (*"Allways use gh tool to access github"*). Prior entry:

- ⛔ ~~**RECURRENCE 2026-09-11, and now MEASURED.**~~ Corroborating PLAN-08 needed the main-branch run
  for merge commit `7fce677`. `ci checks status` takes `--pr-number` or `--head`, and **both resolve
  a branch to a PR** — `--head 7fce677` returns *"no pull requests found for branch 7fce677"*. There
  is no read verb in the abstraction that takes a merge commit, so the main-branch half of the
  obligation is **unreachable**, exactly as this entry predicted. ✅ The PR-attached half DID resolve
  (`Run Integration Benchmarks` SUCCESS on PR #286), so the two halves now have different, verified
  statuses rather than one unknown.

- ⛔ **The epic cannot discharge its own post-merge verification obligation through the sanctioned
  tooling.** CLAUDE.md § Git Workflow step 8 assigns the orchestrator the main-branch run for the
  merge commit — the only place `deploy-snapshot` ever runs, since it is skipped on pull requests.
  But every `plan-marshall:tools-integration-ci:ci` verb is PR-keyed: `checks status` accepts only
  `--pr-number` / `--head`, `--head main` returns `no pull requests found for branch "main"`, and no
  verb reads a push-triggered run by commit. The small-ops carve-out forbids reaching for `gh`
  directly, so the lookup is **structurally unperformable from this seat** and PR #254's snapshot
  deployment is recorded as an UNVERIFIED LEAD rather than as green. ⚠ This is not specific to
  PLAN-06 — it applies to every landing this epic will ever analyze. Unowned; a tooling-level gap. —
  source: `ci checks status --head main`, `ci --help` verb enumeration at HEAD `6ba8879`.
