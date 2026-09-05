# End-of-Run Landing Cycle

The landing-cycle procedure the steward's uniform end-of-run hook loads when a
steward run has left uncommitted plan-marshall artifacts. It offers to land those
changes — commit → push → `skip-bot-review`-labelled PR → merge-queue-aware merge
→ switch to the base branch → pull — so a steward pass never silently leaves the
working tree dirty. It fires from BOTH steward modes at their natural end (the
menu-mode "Quit" path and the end of the wizard flow); see [`../SKILL.md` §
"End-of-Run Landing Cycle"](../SKILL.md#end-of-run-landing-cycle) for the firing
contract.

`{repo_root}` below is the main-checkout repository root the steward is running
against. All git invocations use the explicit `git -C {repo_root} …` form (never
`cd {repo_root} && git …`), and all CI/PR operations go through the
`tools-integration-ci:ci` abstraction (never `gh`/`glab` directly).

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `ci` and `git-workflow` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Step 1: Detect an uncommitted plan-marshall artifact diff

```bash
git -C {repo_root} status --porcelain
```

- **Empty output** → no uncommitted changes → the hook is a **silent no-op**. Do
  NOT prompt; the steward run ends normally.
- **Non-empty output** → uncommitted changes are present. Continue to Step 2,
  carrying the porcelain output as the change summary to show the user.

## Step 2: Offer to land the changes

Present the uncommitted paths, then gate the whole cycle behind a single
`AskUserQuestion`:

```text
AskUserQuestion:
  question: "The steward run left uncommitted plan-marshall changes. Land them now?"
  header: "Landing Cycle"
  options:
    - label: "Yes, land now"
      description: "Commit, push, open a skip-bot-review PR, merge, and switch back to the base branch"
    - label: "No, leave uncommitted"
      description: "Leave the changes in the working tree for manual handling"
  multiSelect: false
```

- **No, leave uncommitted** → emit a clear "uncommitted steward changes" summary
  (the Step 1 porcelain list) so the user knows exactly what is pending, then end
  the run. This is the leave-uncommitted exit.
- **Yes, land now** → continue to Step 3.

## Step 3: Branch selection (base-branch-conditional)

Detect the current branch:

```bash
git -C {repo_root} rev-parse --abbrev-ref HEAD
```

- **On the base branch** (`main` / `master`): never commit steward artifacts
  directly to the base. Create a new working branch with a `chore/` prefix (the
  closed CI-triggered prefix set per CLAUDE.md § "Branch Naming" — `chore/` is the
  correct prefix for steward-maintenance changes; `docs/` is retired). Derive a
  short slug (e.g. `chore/steward-landing-{short-slug}`):

  ```bash
  git -C {repo_root} checkout -b chore/{slug}
  ```

- **Already on a non-base working branch** (a `chore/` or `feature/` branch):
  confirm reuse before committing onto it:

  ```text
  AskUserQuestion:
    question: "Reuse the current branch {branch} for these steward changes?"
    header: "Landing Cycle — Branch"
    options:
      - label: "Yes, reuse {branch}"
        description: "Commit the steward changes onto the current working branch"
      - label: "No"
        description: "Leave the changes uncommitted"
    multiSelect: false
  ```

  - **Yes** → keep the current branch and continue to Step 4.
  - **No** → take the leave-uncommitted exit (emit the summary and end).

Record `{branch}` (the created or reused branch name) and `{base}` (the repo
default branch) for the later steps.

## Step 4: Commit and push

Commit the uncommitted plan-marshall artifacts using the `workflow-integration-git`
commit flow in its plan-less `git -C {repo_root}` mode (a conventional
`chore(steward): …` message), then push the branch to `origin`.

```text
Skill: plan-marshall:workflow-integration-git
  Parameters:
    - message: conventional chore(steward) commit describing the landed artifacts
    - push: true
```

The commit workflow honours the artifact-cleanup and conventional-commit contract
documented in `workflow-integration-git/SKILL.md`. Confirm the push succeeded
before continuing.

## Step 5: Ensure the label, open the PR, merge via the queue, switch back

**(a) Ensure the `skip-bot-review` label exists** (idempotent — create-if-missing):

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci repo label ensure \
  --label skip-bot-review
```

See the `tools-integration-ci` Canonical invocations (`repo` → `label ensure`) for
the verb shape. This guarantees the label exists so the labelled PR create below
does not fail on a missing label.

**(b) Create the PR via the plan-less `NO_PLAN` sentinel**, labelled
`skip-bot-review`. The steward has no plan directory, so it passes the sentinel
as its `--plan-id` and uses the ordinary prepare → write → create body-store
sequence — the sentinel resolves to the shared plan-less body store and is
materialized on first use:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body \
  --plan-id NO_PLAN --slot steward-landing
```

Read the `path` field from the returned TOON and author the PR body to it with
the `Write` tool (the path is under `.plan/`, pre-approved via
`Edit(.plan/**)`), then create the PR:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
  --title "chore(steward): land steward-maintained artifacts" \
  --plan-id NO_PLAN --slot steward-landing \
  --label skip-bot-review --base {base} --head {branch}
```

See the `tools-integration-ci` Canonical invocations (`pr`) for the verb shape,
and [`tools-integration-ci/SKILL.md`](../../tools-integration-ci/SKILL.md) § "The
`NO_PLAN` sentinel — one plan-less convention for every `--plan-id` verb" for the
sentinel contract. `--plan-id` is required on both verbs and the body store is
the only body channel; `NO_PLAN` is what makes that single channel serve a
plan-less caller like the steward.

**(c) Merge via the platform merge queue** — WITHOUT `--delete-branch`. The
required merge queue rejects `--delete-branch`, so branch cleanup is left to the
queue:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue \
  --head {branch}
```

⛔ **This dispatch requires an already-provisioned merge queue — it enqueues, it never
provisions.** Both providers probe eligibility *before* the enqueue call and report
`enqueued: true` only against a queue or train that actually exists. Every other
eligibility value returns `status: error`, and the verb never falls back to an immediate merge —
so on an unprovisioned repository the PR is left open and the landing cycle stops here rather
than landing outside the queue. The **operator remedy is to provision the queue** — run
`/marshall-steward` → Configuration → Merge Queue (the probe→ask→configure flow in
[`merge-queue-setup.md`](merge-queue-setup.md)) — and then re-run the landing cycle. The error
also names a second remedy, disabling a plan's `use_merge_queue` step param and merging via `ci
pr safe-merge`; that one is for plan-bound callers and has no counterpart here, because the
steward lands plan-lessly and always routes through the queue. See
[`tools-integration-ci/standards/pr-operations.md`](../../tools-integration-ci/standards/pr-operations.md)
§ "Workflow: Merge-Queue PR" for the corroboration contract behind both.

**(d) Switch back to the base branch and pull** so the local checkout reflects the
merged result:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull \
  --project-dir {repo_root} --base {base}
```

See the `workflow-integration-git` Canonical invocations (`switch-and-pull`) for
the verb shape.

## Step 6: Bot skip-label honoring matrix

The `skip-bot-review` label fully suppresses **CodeRabbit** and **PR-Agent** today. Surface
this matrix to the operator so they understand what the label does — the values
come from the per-bot `honors_skip_label` fields in the `automatic-review`
registry docs (`standards/{bot_kind}.md`); no registry edits are needed:

| Bot | `honors_skip_label` | Behaviour with `skip-bot-review` |
|-----|---------------------|----------------------------------|
| CodeRabbit | `true` | Honored via central `cuioss/coderabbit` config — a PR labelled `skip-bot-review` is skipped. |
| Sourcery | `false` | No central label skip. Honored per-repo only by adding `github.ignore_labels: [skip-bot-review]` to the repo's `.sourcery.yaml`. |
| PR-Agent | `true` | Honored — but enforced by the reusable `reusable-pr-agent-review.yml` workflow's job-level `if:` guard, not by bot config. An explicit `/review` comment overrides the label on purpose. |

So the `skip-bot-review` label suppresses CodeRabbit and PR-Agent; Sourcery only
when the repo's `.sourcery.yaml` opts in.

After the switch-and-pull settles, the landing cycle is complete — return control
to the steward's end-of-run flow.
