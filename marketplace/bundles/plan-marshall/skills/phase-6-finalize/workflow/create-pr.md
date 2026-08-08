---
lane:
  class: core
  cost_size: M
name: default:create-pr
description: Create pull request
order: 20
mutates_source: false
default_on: true
presets:
  - standard
  - full
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Create PR

Pure executor for the `create-pr` finalize step. Creates a pull request for the feature branch.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `create-pr` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Inputs

- Branch has been pushed (handled by `push` earlier in the manifest list)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `ci` script invocations below MUST identify the worktree via either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override). The two flags are mutually exclusive. Examples below use the literal `--project-dir {worktree_path}` form; substitute `--plan-id {plan_id}` to use auto-resolution.

## Execution

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:tools-integration-ci"
```

```text
Skill: plan-marshall:tools-integration-ci
```

### Resolve branch context

Read the plan's branch and base-branch from `references.json`. This step grounds the `{base_branch}` placeholder used in every subsequent git diff and `ci pr create` call — do NOT improvise a branch-context read from any other source.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-context \
  --plan-id {plan_id}
```

Parse the returned TOON and bind:

- `{branch}` ← `branch` field (the feature branch, e.g. `feature/{plan_id}`)
- `{base_branch}` ← `base_branch` field (e.g. `main`)

Both fields are required. If `status: error` is returned, STOP and return an error TOON — the plan has no references context and the PR cannot be created.

### Check if PR already exists

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Inspect the returned TOON — branch on BOTH `status` AND `state` (an open PR is reusable; a merged/closed one is not):

- `status: success` AND `state == open` → an open PR already exists for this branch. Skip creation; reuse the returned `pr_number` for the automated review step (Mark Step Complete → Branch B).
- `status: success` AND `state ∈ {merged, closed}` → the returned PR is a **stale association**, not a reusable PR. This happens when the branch name is reused across runs (a deterministic `feature/{plan_id}` whose prior run already merged): `gh pr view <branch>` returns the most-recent PR for the branch name regardless of state when no open PR exists, so a merged/closed PR resolves here. The current branch's new commits need their own PR — do NOT reuse it. Proceed to create a fresh PR (Mark Step Complete → Branch A). Recipe plan_ids carry a `{yyyy-mm-dd-hh}` suffix (see `phase-1-init/SKILL.md` Step 2 "From recipe") precisely to avoid this branch-name reuse, but this state guard is the structural backstop if a collision ever occurs by another path.
- `status: error` → no PR exists, proceed to create one (Branch A).

### Generate PR body

Read the clarified request to ground the body description (the `clarified_request` section falls back to `original_input` automatically when no clarification round ran):

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section clarified_request
```

Use the path-allocate pattern: the script allocates the scratch path, the main
context writes the body with the Write tool, and `pr create` consumes the file.
No multi-line markdown crosses the shell boundary.

#### Step 1: Resolve the changed-file set

Before drafting any body content, ground the body against the actual diff so
file references cannot be fabricated. The diff is a local operation and is
resolved with `git` directly (the `tools-integration-ci` abstraction covers
provider-side operations such as PR creation, reviews, and threads — local
working-tree diffs are out of its scope):

```bash
git -C {worktree_path} fetch origin {base_branch}
```

```bash
git -C {worktree_path} diff --name-only origin/{base_branch}...HEAD
```

Read the returned file list as `{changed_files}`. This is the authoritative
diff scope for the body. Use `origin/{base_branch}...HEAD` (three dots) so
the comparison runs against the merge base — the same file set GitHub /
GitLab will show on the PR — rather than including unrelated changes that
have landed on `{base_branch}` since the feature branch diverged.

#### Step 2: Allocate the scratch body path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr prepare-body \
  --plan-id {plan_id}
```

Read the `path` field from the returned TOON — it is the canonical scratch
location bound to this plan. Do not invent a path of your own.

#### Step 3: Write the PR body

```text
Write({path from prepare-body}) with PR body markdown content
```

Use `templates/pr-template.md` as the format. Include issue link from references
(`Closes #{issue}` if `issue_url` was set).

**File-reference constraint**: Every file path mentioned in the PR body MUST
belong to `{changed_files}` from Step 1. Fabricating file references that are
not in the resolved diff scope is a workflow violation — it undermines the
reviewer trust model that the rest of the finalize pipeline is built on. If a
template section calls for a file that is not in `{changed_files}`, omit the
section rather than invent a reference.

#### Step 3.4: Compose the Intent section

Automated reviewers judge the diff on generic correctness plus this repo's `CLAUDE.md` rules. None of
them knows **what the change was supposed to do** — and implementation-vs-intent divergence
(doc-contract drift, vacuous guards, a predicate that does not do what the outline specified) is this
project's most recurring defect archetype. The PR description is the only channel that reaches every
reviewer, so the plan's intent goes there.

**Distil, do not paste.** Write a short statement covering exactly three things:

1. **The problem** — what was wrong, in the reviewer's terms.
2. **The chosen approach** — the shape of the fix and why that shape.
3. **Explicit non-goals** — what this change deliberately does NOT do, so a reviewer does not report
   a scoped-out concern as a gap.

**OMIT the deliverable list and the task breakdown.** Both are already visible in the diff and the
commit series; restating them spends the budget on what the reviewer can already see, at the cost of
the intent they cannot.

Write the distillation to a scratch draft path with the `Write` tool, then invoke the renderer:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:pr_intent_section render \
  --plan-id {plan_id} --draft-path {draft_path} --body-path {path from prepare-body}
```

**You MUST NOT count characters, measure the draft against a budget, or truncate the draft
yourself.** The character budget and its truncation are owned by the script, deterministically —
that is what makes the outcome reproducible and keeps a clip from happening silently. Write the
distillation at its natural length and let the renderer decide.

Read `omitted`, `truncated`, and `chars_written` from the returned TOON and branch:

- **`omitted: true`** — the plan has no outline intent (no `solution_outline.md`, or its `summary`
  and `overview` sections are both absent or empty). The body file is left byte-identical, with **no
  heading and no placeholder** — an empty `## Intent` would imply the intent was considered and found
  vacuous. This is a normal outcome for outline-less plans, not a failure. Record it:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:create-pr) Intent section omitted — {reason}"
  ```

- **`truncated: true`** — the draft exceeded the budget and was cut at a word boundary, with the
  truncation marker rendered INSIDE the budget so the loss is visible to the reviewer. Record it so
  a recurring truncation is visible as a signal that the distillations are running long:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:create-pr) Intent section truncated to {chars_written} of {budget} chars — distillation ran long"
  ```

- **`truncated: false`, `omitted: false`** — the section was rendered whole. No decision entry needed.

On `status: error` (`draft_unreadable` / `empty_draft`) the renderer refused rather than emitting an
empty heading. Fix the draft and re-invoke; do not proceed with a body carrying a hollow section.

> **What this section is NOT.** A stated intent makes a fluent, agreeable, diff-blind review *cheaper*
> to reach — a reviewer can now echo the intent back without reading the diff. That is why the
> participation predicate treats an intent-echoing review as `participated_but_empty` rather than a
> discharged review obligation, and why its verdict must be identical-or-stricter on an
> Intent-bearing PR.
>
> `participated_but_empty` is one member of a **closed seven-member** non-participation taxonomy —
> `absent`, `not_triggered`, `in_progress`, `refused_awaitable`, `refused_hard`,
> `participated_but_empty`, `participated_stale` — whose complement is `participated`. It is the ONLY
> member that is accounted-for rather than blocking, which is exactly why an intent-echo lands there
> rather than on a blocking member: the bot did run and did say something. The enumeration is recorded
> here so the parity requirement above reads against the real member set rather than an implied
> smaller one. See
> [`../../automatic-review/standards/bot-participation-contract.md`](../../automatic-review/standards/bot-participation-contract.md)
> § "Participation is not review quality" for the parity obligation and § "Failure taxonomy" for the
> members themselves.

#### Step 3.5: Resolve the PR title from the persisted status field

Ground the PR title against the deterministic source authored at phase-2-refine Step 13 and persisted to `status.metadata.pr_title` — mirroring the `{base_branch}` grounding bind above. Do NOT improvise a title from `request.md` or the commit log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field pr_title
```

Bind `{pr_title}` ← the returned `value`. An empty or missing `pr_title` here is an error — the `pr_title_present` phase-handshake invariant should already have blocked the `2-refine`+ boundary, so reaching this step with no title means the invariant was bypassed. STOP and return an error TOON rather than improvising a title.

#### Step 3.6: Resolve the bot-participation skip-label

Read the `required_bots` / `optional_bots` participation lists — the config that governs which reviewer bots are expected on this plan's PR. Both are `configurable:` params owned by the `plan-marshall:automatic-review` finalize step (their single source-of-truth seeds live in that skill's frontmatter, both `default: ""`), read here from the plan-local execution-manifest step-params snapshot:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id plan-marshall:automatic-review
```

Read `required_bots`, `optional_bots`, and `bot_lists_provenance` off the returned `params` object (defaults: `""`, `""`, `never_asked`). Each list is a comma-joined string split at read time — bind `{participating_set}` to the union of the non-empty, whitespace-trimmed tokens from BOTH lists. When the `plan-marshall:automatic-review` step is not present in the manifest (e.g. a plan whose preset excludes it), do NOT apply the skip-label.

- **`{participating_set}` is non-empty** (the common case — at least one bot classified): do NOT apply the skip-label. Bind `{label_args}` to the empty string.
- **`{participating_set}` is empty AND `bot_lists_provenance` is `never_asked`**: do NOT apply the skip-label. Bind `{label_args}` to the empty string. **A never-asked posture does NOT mean "skip review"** — it means the operator has not yet been asked, and defaulting an unanswered question into review-suppression would silently disable review on every fresh project. Fail toward being reviewed.
- **`{participating_set}` is empty AND `bot_lists_provenance` is `answered` or `migrated`**: the operator explicitly classified no bots at all. Bind `{label_args}` to `--label skip-bot-review`, applying the shared `skip-bot-review` label on the created PR as a suppression signal.

**Why the label now carries the whole weight.** Under the two-list model the participation knobs classify rather than admit: a comment from a bot in neither list is still INGESTED (the warn-but-ingest rule — see [`../../automatic-review/standards/bot-participation-contract.md`](../../automatic-review/standards/bot-participation-contract.md)). Empty lists therefore no longer suppress anything at the producer boundary, so the `skip-bot-review` label is the ONLY suppression signal on this path — not, as before, a secondary layer over an authoritative producer gate. That matters because the bots honor the label asymmetrically: CodeRabbit honors it centrally, PR-Agent via its reusable workflow's job-level `if:` guard, and Sourcery only via a per-repo `.sourcery.yaml`. Expect a bot without label support to review anyway; its comments will be ingested and reported as unclassified. Applying a remote PR label is not a source mutation, so this step's `mutates_source` stays `false`.

#### Step 3.7: Consult `pr_strategy` for ride-vs-split

marshall-steward-owned artifact changes (executor regeneration, marshal.json migrations) and in-plan follow-up work produced during this plan **ride THIS PR** rather than opening a separate one when the `pr_strategy` policy says so. Consult the first-class decision verb to resolve the ride-vs-split verdict against the `{changed_files}` set already resolved in Step 1:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config project pr-decision \
  --changed-files {N}
```

`{N}` is the total changed-file count of `{changed_files}`. Read `decision` off the returned TOON:

- **`decision: ride`** — the steward artifacts and in-plan follow-up work ride THIS PR; do not open a separate one.
- **`decision: split`** — the `pr_strategy` is `distinct`, or the changed-file count exceeds the compact ceiling; those changes belong in their own separate PR.

Reference the verb by its canonical invocation (see `manage-config` Canonical invocations → `project pr-decision`) rather than restating the strategy/ceiling comparison here. This is a read-only consultation note — the step still always creates the plan's own PR — so `mutates_source` stays `false`.

#### Step 4: Create PR via CI abstraction

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr create \
  --title "{pr_title}" --plan-id {plan_id} --base {base_branch} {label_args}
```

The `pr create` subcommand reads the body from the prepared scratch file, creates
the PR, and deletes the scratch on success. `{label_args}` is either empty or the
`--label skip-bot-review` fragment resolved in Step 3.6; the `--label` flag is a
repeatable passthrough to `gh pr create --label`.

Read `pr_number` and `pr_url` from the TOON output.

### Log PR creation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-6-finalize) Created PR #{pr_number}: {pr_url}"
```

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the PR outcome. The payload differs by branch:

**Branch A — new PR created** (from "Create PR via CI abstraction"): `{pr_number}` is the PR number returned by `pr create`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step create-pr --outcome done \
  --display-detail "#{pr_number}"
```

**Branch B — existing PR re-used** (from "Check if PR already exists"): `{pr_number}` is the PR number returned by `pr view`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step create-pr --outcome done \
  --display-detail "existing PR #{pr_number}"
```

Note: there is no "skipped" branch — when the manifest excludes `create-pr`, the dispatcher does not run this document at all, so no step record is written. The renderer treats absent records as "not configured" rather than "skipped".

## Output

```toon
status: success | error
display_detail: "<#{pr_number} or 'existing PR #{pr_number}'>"
pr_number: {pr_number}
branch: {branch}
```

The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded verbatim via `mark-step-done --display-detail` above; it is the same string the orchestrator surfaces.
