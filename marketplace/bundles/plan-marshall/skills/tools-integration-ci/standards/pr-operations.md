# PR Operations

Pull request lifecycle operations: create, view, merge, auto-merge, safe-merge, merge-queue, close, ready, edit. Also covers the `branch delete` leaf, which supports post-merge remote branch cleanup, and the repo-level `repo merge-queue probe` / `repo merge-queue enable` provisioning verbs.

## Branch-Aware Operations: `--head BRANCH`

Several operations identify a PR by source branch, and the underlying `gh`/`glab` CLI derives that branch from `git symbolic-ref HEAD` in the cwd. When the Bash tool's cwd HEAD is not the branch the operation should target, cwd-based derivation picks the wrong branch and operations fail (e.g. `pr create` returns *"No commits between main and main"*).

To handle this, branch-aware operations accept an explicit `--head BRANCH` argument:

| Operation | `--head` semantic |
|-----------|--------------------|
| `pr create` | Source branch for the new PR (forwarded as `gh --head` / `glab --source-branch`) |
| `pr view` | Branch whose PR to view (gh accepts a branch positional; glab uses `mr view {branch}`) |
| `pr merge` | Branch identifying the PR to merge (alternative to `--pr-number`; glab resolves IID via `mr list --source-branch`) |
| `pr auto-merge` | Same as `pr merge` |
| `pr safe-merge` | Same as `pr merge` |
| `pr merge-queue` | Same as `pr merge` |
| `pr update-branch` | Same as `pr merge` |
| `checks status` | Same as `pr merge` |

Every operation in that table also declares `--pr-number`, and the two flags divide into **two** validation contracts:

| Contract | Operations | Behaviour |
|----------|------------|-----------|
| **Exactly one** required | `pr merge`, `pr auto-merge`, `pr safe-merge`, `pr merge-queue`, `pr update-branch`, `checks status` | Both → `status: error`, `specify exactly one of --pr-number or --head`. Neither → `status: error`, `specify either --pr-number or --head`. |
| **At most one** | `pr view` | Both → `status: error`, `specify exactly one of --pr-number or --head, not both`. Neither → the PR for the current cwd HEAD (the historical default). |

`pr create` is not in either row: its `--head` names the source branch of a PR that does not exist yet, so there is no `--pr-number` to choose between.

### `--head` is not a landing-poll selector

A poll that waits for a PR to reach a terminal state MUST key on `--pr-number`, never on `--head`. Under a required platform merge queue (GitHub) or merge train (GitLab), the platform **auto-deletes the head branch as it merges**. A `--head`-keyed lookup therefore stops resolving at exactly the moment the terminal state the poll exists to observe becomes observable, so the poll can never see `state: merged` — it can only time out or read an error. The PR number is stable across the branch deletion; the branch name is not.

Callers whose cwd HEAD does not match the operation target branch MUST pass `--head {branch}`. See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (worktree-isolated plans run from the main checkout against a feature branch and MUST always pass `--head {plan_branch}`).

---

## The corroborate-not-report contract (all merge-shaped verbs)

**A merge-shaped verb never derives its success claim from the CLI exit code alone.** This applies to every verb in the merge-shaped set — `pr merge`, `pr auto-merge`, `pr safe-merge`, `pr merge-queue` — on both providers, and it is stated once here rather than repeated in each verb's Process Result block.

A zero exit from `gh` / `glab` means only that the provider ACCEPTED the command. It does not mean the merge landed, that the PR joined a queue, or that the disposition the caller asked for is the one that occurred. Three observed shapes, all of which exited zero:

- `gh pr merge` on a base branch with a required merge queue **closes the PR unmerged** instead of merging it.
- `gh pr merge --auto` / `glab mr merge --when-pipeline-succeeds` **silently switch disposition** — enqueue vs plain auto-merge — depending on the base branch's (GitHub) or project's (GitLab) queue configuration, with no change to the exit code.
- A verb reported `merged: true` and deleted the head branch for a merge that never happened.

Each verb therefore establishes its own claim from a **re-read of provider state** and reports what it actually observed:

| Verb | Claim | Established from |
|------|-------|------------------|
| `pr merge` | `merged` | Post-merge PR/MR state re-read. GitHub: `state == MERGED` plus a parseable `mergedAt` (strategy `merge` / `rebase` additionally admit base-contains-head ancestry; `squash` does not, because a squashed commit is a new object). GitLab: `state == 'merged'` — `view_pr_data` exposes no `merged_at`, so state is the whole verdict. |
| `pr safe-merge` | `merged` | The delegated `pr merge` corroboration, asserted positively (`merged is True`), plus its own corroboration on the GitHub admin-fallback path. |
| `pr merge-queue` | `enqueued` | A pre-enqueue probe of the base branch's (GitHub) / project's (GitLab) queue configuration. |
| `pr auto-merge` | `disposition` | The same pre-call queue/train probe, reporting which of the two dispositions occurred. |

Two shape rules bind every corroboration above:

1. **Assert the value's meaning, never a key's presence.** A record carrying a `mergedAt` key whose value is `null`, empty, or unparseable is a NON-corroboration; probing for the key alone passes on a wrongly-shaped record and reintroduces the defect.
2. **Any parsed timestamp is timezone-aware.** A naive datetime raises the moment it is compared against an aware one, turning a corroboration check into a crash. Naive values are normalized to UTC.

Every corroboration **fails closed**: an unreadable state, a failed probe, or a malformed payload is a refusal, never a permissive default.

---

## Workflow: View PR (Current Branch, `--pr-number`, or `--head`)

**Pattern**: Provider-Agnostic Router

Get PR/MR details for the current branch, for an explicit PR number, or for a specific branch.

`gh pr view` / `glab mr view` take a number, a URL, or a branch name in the **same positional slot**, so `--pr-number` and `--head` are a selector choice rather than two code paths. Supply **at most one**; supplying neither views the PR for the current cwd HEAD. Poll on `--pr-number` — see *`--head` is not a landing-poll selector* above.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view [--pr-number {number} | --head {branch}]
```

### Step 2: Process Result

```toon
status: success
operation: pr_view
pr_number: 456
pr_url: https://github.com/org/repo/pull/456
state: open
title: Add feature X
head_branch: feature/add-x
base_branch: main
```

---

## Workflow: List PRs

**Pattern**: Provider-Agnostic Router

List pull requests with optional branch and state filters.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr list \
    [--head {branch}] [--state {open|closed|all}]
```

### Step 2: Process Result

```toon
status: success
operation: pr_list
total: 2
state_filter: open
head_filter: feature/my-branch

prs[2]{number,url,title,state,head_branch,base_branch}:
123	https://github.com/org/repo/pull/123	Add feature X	open	feature/my-branch	main
456	https://github.com/org/repo/pull/456	Fix bug Y	open	feature/my-branch	develop
```

---

## Workflow: Create PR

**Pattern**: Provider-Agnostic Router

Create a pull request using the three-step path-allocate pattern. The script
owns path allocation — callers never invent scratch paths. Markdown bodies are
written directly by the main context with its native Write tool, and the `pr
create` subcommand consumes the prepared file. No multi-line markdown crosses
the shell boundary, so the host platform's shell-heading heuristic never fires.

`--plan-id` is required on both `pr prepare-body` and `pr create`; the body store
is the **only** body channel. A caller with no plan is not an exception to the
three steps — it runs the identical sequence with `--plan-id NO_PLAN`, the
plan-less sentinel, which resolves to the shared plan-less body store and binds
to the main checkout. Use the sentinel only when the caller genuinely has no
plan; a `--plan-id` that failed to resolve must be corrected, not replaced with
the sentinel. See [`tools-integration-ci/SKILL.md`](../SKILL.md) § "The
`NO_PLAN` sentinel — one plan-less convention for every `--plan-id` verb".

### Step 1: Allocate Scratch Body Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body \
    --plan-id {plan_id}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the PR body, bound to this plan (or to the sentinel) and kind.

### Step 2: Write the PR Body

```text
Write({path from prepare-body}) with PR body markdown content
```

### Step 3: Create PR

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Add feature X" --plan-id {plan_id} --base main [--head feature/x]
```

The subcommand reads the body from the prepared scratch file, creates the PR,
and deletes the scratch on success. See *Branch-Aware Operations: `--head BRANCH`* above for when `--head` is required.

### Step 4: Process Result

```toon
status: success
operation: pr_create
pr_number: 456
pr_url: https://github.com/org/repo/pull/456
```

---

## Workflow: Merge PR

**Pattern**: Provider-Agnostic Router

Merge a pull request immediately.

### Merge-queue / merge-train refusal

`pr merge` runs the **same** platform-queue preflight `pr safe-merge` carries (see *Safe-Merge PR* → *Platform-queue preflight* below for the provider-shaped pair and the fail-closed contract) and **refuses** rather than merging when the platform requires the queue:

- **GitHub** — the PR's own base branch has a required merge queue (`eligible_configured`). An immediate merge there closes the PR unmerged.
- **GitLab** — the project has merge trains enabled. An immediate merge bypasses the train the project requires.

The refusal returns `status: error` naming BOTH remedies: route through the queue via `ci pr merge-queue`, or reconcile the plan's `use_merge_queue` step param via `/marshall-steward`. It never falls back to an immediate merge.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge \
    (--pr-number 123 | --head feature/x) [--strategy merge|squash|rebase] [--delete-branch]
```

Supply exactly one of `--pr-number` or `--head`. See *Branch-Aware Operations: `--head BRANCH`* above for when `--head` is required.

### Step 2: Process Result

```toon
status: success
operation: pr_merge
pr_number: 123
strategy: squash
merged: true
merge_corroboration: "state=MERGED, merged_at=2026-01-01T00:00:00+00:00"
```

`merged` is the verb's success claim and is **corroborated**, per the *corroborate-not-report contract* above: it is set only from a post-merge state re-read, and only ever to `true` — a merge that cannot be corroborated returns `status: error` instead. `merge_corroboration` carries the evidence the verdict rests on, so a reader never has to re-derive it.

Two properties of `merged` that callers previously could not rely on:

- It is reported on **every** successful merge. It used to be set only inside the `--delete-branch` branch, so a merge without that flag reported no merge verdict at all.
- It is established **before** the branch-delete follow-up runs. A non-corroborated merge therefore deletes nothing — the head branch is never taken down by a merge that did not happen.

`--delete-branch` still adds the compound-result keys on the delete path (`branch_deleted` / `already_gone`, or `branch_delete_error` with `merged: true` retained when the delete fails after a corroborated merge). The merge is never retried on a branch-delete failure.

---

## Workflow: Auto-Merge PR

**Pattern**: Provider-Agnostic Router

Schedule a pull request to merge without waiting — it merges once the platform's own preconditions are satisfied.

### One command, two dispositions

The underlying call (`gh pr merge --auto` on GitHub, `glab mr merge {iid} --when-pipeline-succeeds [--squash]` on GitLab) has **two** dispositions, and which one occurs is decided by the platform, not by the caller:

| Provider | Queue/train NOT configured | Queue/train configured |
|----------|----------------------------|------------------------|
| GitHub | plain auto-merge is enabled on the PR | the PR is **enqueued** into the base branch's merge queue |
| GitLab | a plain when-pipeline-succeeds merge is scheduled | the MR is placed on the project's **merge train** |

The exit code is identical in both columns. The verb therefore probes the platform state **before** the call — GitHub: the PR's own base branch; GitLab: the project's `merge_trains_enabled` flag — and reports which disposition actually occurred. The probe runs first rather than after because on the unconfigured path the call itself has a side effect (a scheduled merge) that the caller did not ask for; establishing state before acting keeps the failure path clean. The probe **fails closed**: an unresolvable queue/train state returns `status: error` rather than a guessed disposition.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr auto-merge \
    (--pr-number 123 | --head feature/x) [--strategy merge|squash|rebase]
```

Supply exactly one of `--pr-number` or `--head`.

### Step 2: Process Result

```toon
status: success
operation: pr_auto_merge
pr_number: 123
base_branch: main
disposition: enabled
disposition_detail: no merge_queue rule on branch
```

`disposition` is the verb's claim and reports what actually happened:

| Value | Meaning |
|-------|---------|
| `enabled` | Plain auto-merge (GitHub) / when-pipeline-succeeds merge (GitLab) was scheduled — no queue or train is configured. |
| `enqueued` | The platform placed the PR on its merge queue (GitHub) or merge train (GitLab). |

`disposition_detail` carries the probe evidence behind the value. `base_branch` is GitHub-only — the queue is a base-branch property there, whereas a GitLab merge train is project-scoped and has no per-branch value to report.

The former exit-code-derived `enabled: true` key is **removed with no alias**: it reported "auto-merge enabled" for a PR that had actually joined a queue, which is precisely the claim the verb cannot make from an exit code. Callers that read `enabled` must read `disposition` and branch on the two values above — a truthiness check on `disposition` is not a migration, because both values are truthy.

---

## Workflow: Safe-Merge PR

**Pattern**: Provider-Agnostic Router

Poll the PR's mergeability until it is ready, then merge — hardening the merge against post-force-push `mergeable_state: blocked` staleness, where GitHub reports a PR as not-mergeable while it recomputes mergeability after a push.

On **GitHub only**, when readiness stays `blocked` past the poll timeout AND `--admin-merge-on-stuck-state` is set AND every active ruleset requirement is provably met (required checks all SUCCESS on the head SHA, branch not behind base, required approving reviews met, no required unresolved conversations), the verb falls back to `gh pr merge --admin`. The stuck-state gate fails closed: any unmet or unverifiable requirement refuses the admin merge. On **GitLab** there is no admin equivalent — `--admin-merge-on-stuck-state` is accepted for API uniformity but ignored, and a stuck-past-timeout MR returns an error rather than force-merging.

### Platform-queue preflight (both providers, provider-shaped)

Before polling readiness, `safe-merge` probes the platform's queue configuration and refuses when the platform requires it. The preflight exists on **both** providers; what differs is its **scope**, because the platform feature it probes is scoped differently — the shape follows the provider, not a GitHub-only carve-out:

| Provider | Feature | Probe scope | What is read |
|----------|---------|-------------|--------------|
| GitHub | merge queue | **base-branch-scoped** | The PR's **own** base branch (`baseRefName` from the PR view), so a PR merging into a developer branch is evaluated against **that** branch, not the repository default. |
| GitLab | merge train | **project-scoped** | The project's `merge_trains_enabled` flag. Merge trains are a per-project setting, so there is no branch argument to pass and inventing one would fabricate a distinction GitLab does not make. |

Both probes map onto the shared merge-queue eligibility discriminators (see *Workflow: Repo Merge-Queue Probe / Enable* below):

- **`eligible_configured`** — the platform **requires** the queue/train. On GitHub an immediate merge here would close the PR unmerged (the PR #866 failure mode); on GitLab it would bypass the train the project requires. `safe-merge` **refuses immediately** with an actionable error naming both remedies: route through the queue via `ci pr merge-queue`, or reconcile the plan's `use_merge_queue` step param via `/marshall-steward`. It does **not** attempt the immediate merge.
- **`eligible_unconfigured` / `ineligible` / `unsupported`** — no required queue or train; `safe-merge` proceeds unchanged.

The preflight **fails closed** on both providers: an unresolvable base branch (empty `baseRefName`, or a `pr view` that does not succeed), an inability to resolve the repository owner/name or project path, or a probe failure (missing auth scope/permission, a non-404 API error, or a malformed response) all return `status: error` rather than falling back to an immediate merge.

The identical preflight also guards `pr merge` (see *Workflow: Merge PR* above), which reaches the same platform state by the same route. What remains **GitHub-only** here is the `--admin-merge-on-stuck-state` fallback, not the preflight.

### Post-merge corroboration guard

In the `polled_clean` path, `safe-merge` asserts **positively** that the delegated merge was corroborated (`merged is True`, established by `pr merge` from a post-merge state re-read) before reporting success. The previous guard probed only for the single known-bad `state == closed`, so every *other* non-merged state — a PR left `open`, a state the provider newly introduces, an unreadable one — passed as a merge. A non-corroborated merge returns `status: error` carrying the corroboration evidence, and advises routing the PR via `ci pr merge-queue` instead of an immediate merge.

On the GitHub-only `admin_fallback` path the admin merge does not go through `pr merge`, so it carries its own corroboration — identically established, and before the branch-delete follow-up can influence it.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr safe-merge \
    (--pr-number 123 | --head feature/x) [--strategy merge|squash|rebase] [--delete-branch] \
    [--admin-merge-on-stuck-state] [--poll-timeout SECONDS] [--poll-interval SECONDS]
```

Supply exactly one of `--pr-number` or `--head`. The `--admin-merge-on-stuck-state` admin fallback is GitHub-only.

### Step 2: Process Result

```toon
status: success
operation: pr_safe_merge
pr_number: 123
strategy: squash
merge_path: polled_clean
polls: 1
duration_sec: 0
merged: true
merge_corroboration: "state=MERGED, merged_at=2026-01-01T00:00:00+00:00"
```

`merge_path` is `polled_clean` when the PR became mergeable within the poll window and merged via the normal path, or `admin_fallback` when the GitHub-only stuck-state `--admin` merge was used.

`merged` and `merge_corroboration` carry the same corroborated meaning as on `pr merge`, on **both** `merge_path` values — see *Workflow: Merge PR* → *Step 2* and the *corroborate-not-report contract* above.

---

## Workflow: Merge-Queue PR

**Pattern**: Provider-Agnostic Router

Enqueue the PR into the **platform merge queue** so the platform re-tests-and-merges it against the latest base branch. Unlike `pr safe-merge` (which merges immediately once the current PR is ready), `pr merge-queue` hands the merge to the platform's serialization mechanism, closing the residual staleness gap a truly-external commit (e.g. a dependabot merge to the base) opens — such a commit never acquires the session-scoped merge mutex, so only the platform queue can serialize against it. It composes with the widened merge mutex: the mutex guards the pre-enqueue rebase/force-push window; the merge queue serializes the merge itself.

On **GitHub**, the verb engages the merge queue via `gh pr merge --auto` (the PR is added to the queue configured on the target branch's protection rules). On **GitLab**, the verb performs a real **merge-train** enqueue via `POST /projects/:id/merge_trains/merge_requests/:iid`. The merge train is a Premium/Ultimate-tier feature enabled per-project; when the project/tier does not offer it (HTTP 403/404 from the merge-train API) the GitLab handler returns the actionable ineligible error rather than silently falling back to an immediate merge.

### The enqueue is corroborated

`enqueued: true` is a **corroborated** claim, per the *corroborate-not-report contract* above. Corroboration is provider-shaped, and the GitHub path is where it had to be added:

- **GitHub** — `gh pr merge --auto` exits zero whether or not the base branch has a queue: with no queue it quietly enables **plain auto-merge**, which is a different disposition entirely. The verb therefore probes the PR's own base branch **before** the call and returns `enqueued: true` only when that branch actually has a configured queue. On any other eligibility value it returns `status: error` naming both remedies — run `/marshall-steward` → Configuration → Merge Queue to provision the queue, or disable the plan's `use_merge_queue` step param to merge immediately via `ci pr safe-merge`. The probe runs before the call because on an unconfigured base the call would otherwise leave the PR scheduled to merge **outside** the queue the caller asked for.
- **GitLab** — the enqueue is a dedicated merge-train endpoint that only succeeds against a real train, and the handler reads the returned train car back as `merge_train_car_id`. That read-back is the corroboration shape the GitHub path was brought to; it is unchanged.

`enqueued: true` means the PR **reached the queue** — it is emphatically **not** a merge. A caller that needs the merge itself must wait for the platform to land it and confirm that separately.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue \
    (--pr-number 123 | --head feature/x)
```

Supply exactly one of `--pr-number` or `--head`. `pr merge-queue` takes **no** `--strategy` or `--delete-branch` flag — that is unchanged: the platform merges queued PRs with the merge method configured on the queue itself, GitHub rejects `--delete-branch` when a merge queue is enabled, and the platform auto-deletes the head branch after the queue merge. The queue's configured method is not an independent knob, though: `repo merge-queue enable` provisions it from — and reconciles it against — the configured `pr_merge_strategy` (see the Repo Merge-Queue Probe / Enable workflow below), and `repo merge-queue probe` surfaces the active value as `merge_method` so residual drift is observable.

### Step 2: Process Result

```toon
status: success
operation: pr_merge_queue
pr_number: 123
base_branch: main
enqueued: true
enqueue_corroboration: merge_queue rule active on branch
```

`enqueue_corroboration` carries the probe evidence behind the claim. `base_branch` is GitHub-only — the queue is a base-branch property there, whereas a GitLab merge train is project-scoped.

On GitLab a successful enqueue returns the same `enqueued: true` envelope with `provider: gitlab` and a `merge_train_car_id` when the API surfaces the train car id. When the project/tier is not merge-train-eligible the invocation returns `status: error, operation: pr_merge_queue` with the actionable ineligible message — surfaced explicitly (never a silent immediate-merge fallback) so cross-provider callers notice the mismatch.

---

## Workflow: Repo Merge-Queue Probe / Enable

**Pattern**: Provider-Agnostic Router

Probe and configure the **platform merge queue** at the repository/project level
(distinct from `pr merge-queue`, which enqueues a specific PR). These verbs back
the `marshall-steward` merge-queue provisioning step and the `use_merge_queue`
set-time validation: `probe` reports whether the platform merge queue is
available and already configured, and `enable` configures it idempotently.

### Step 1: Probe eligibility

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci repo merge-queue probe
```

```toon
status: success
operation: repo_merge_queue_probe
provider: github
eligibility: eligible_unconfigured
detail: no merge_queue rule on branch
```

`eligibility` is one of the shared discriminators:

| Value | Meaning |
|-------|---------|
| `eligible_configured` | The platform merge queue is available AND already configured (`enable` re-runs only reconcile drift). |
| `eligible_unconfigured` | Available but not yet configured — `enable` will configure it. |
| `ineligible` | The platform gates the feature off (GitLab merge trains need Premium/Ultimate; a GitHub org policy or missing Administration scope disallows it). |
| `unsupported` | Reserved — the abstraction cannot probe/enable the feature. |

On GitHub an `eligible_configured` probe additionally carries `merge_method` —
the queue rule's configured merge method in the ruleset spelling (`SQUASH` /
`MERGE` / `REBASE`). The field is absent on GitLab, on an unconfigured queue,
and when the parameter is absent/malformed.

On GitHub an `eligible_configured` result — for **both** `probe` and `enable` —
also carries `externally_managed`: `true` when the queue is configured under a
ruleset plan-marshall does not own, `false` when plan-marshall owns it. The
field is **absent** (never `false`) on every other eligibility value, on
GitLab, and when ownership cannot be determined. plan-marshall never creates,
reconciles, renames, or deletes a ruleset it did not create, so an
`externally_managed: true` result is reported without any mutation.

### Step 2: Enable (idempotent)

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci repo merge-queue enable
```

```toon
status: success
operation: repo_merge_queue_enable
provider: github
eligibility: eligible_configured
changed: true
detail: merge_queue ruleset created
```

On GitHub, `enable` creates a `merge_queue` ruleset on the default branch whose
merge method is the mapped `pr_merge_strategy` (`squash` → `SQUASH`, `merge` →
`MERGE`, `rebase` → `REBASE`, default `SQUASH`); on GitLab it sets the
per-project `merge_trains_enabled` flag. On an already-configured GitHub repo,
`enable` reconciles the named ruleset's merge method against the same mapped
value. A method drift is corrected via a partial `PUT` and returned as
`changed: true` with the reconcile detail (e.g. `merge queue already
configured; merge_method reconciled to SQUASH`).

`changed: false` covers **two distinct states**, discriminated by
`externally_managed`:

| Result | Meaning |
|--------|---------|
| `changed: false`, `externally_managed: false` | Genuine idempotent no-op — plan-marshall owns the ruleset and everything already matches. |
| `changed: false`, `externally_managed: true` | The queue is owned by a foreign ruleset. Nothing was compared or corrected, and no mutation was issued. |

Read `externally_managed` rather than inferring "everything already matches"
from `changed: false` alone. On an `ineligible` probe
`enable` refuses with the actionable ineligible error; on an auth-scope
failure both verbs return the actionable remedy (naming the required
scope/permission), never a stack trace.

On GitHub, `enable` additionally refuses on an `eligible_unconfigured` repo
whose `.github/workflows` carry **no `merge_group` CI trigger** — returning
`status: error` with an actionable message rather than creating the ruleset.
This is the bricks-main footgun: a merge queue with no workflow that triggers on
`merge_group` stalls the queue and blocks **all** merges to the default branch,
because every queued PR forms a merge group that never receives a required
status check. The message names the remedy — add a `merge_group:` trigger to a
`.github/workflows/*.yml` (alongside `push` / `pull_request`) before enabling
the merge queue. This refusal is distinct from the `ineligible` / auth-scope
refusals above: the platform allows the feature and auth is sufficient, but
provisioning the queue anyway would brick the default branch. It is GitHub-only
(GitLab merge trains carry no equivalent `merge_group` trigger requirement).

---

## Workflow: Close PR

**Pattern**: Provider-Agnostic Router

Close a pull request without merging.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr close \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_close
pr_number: 123
```

---

## Workflow: Mark PR Ready

**Pattern**: Provider-Agnostic Router

Mark a draft PR as ready for review.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr ready \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_ready
pr_number: 123
```

---

## Workflow: Edit PR

**Pattern**: Provider-Agnostic Router

Edit a pull request title and/or body. Use the path-allocate pattern when
updating the body. Title-only edits skip Steps 1-2.

### Step 1 (optional): Allocate scratch path for new body

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body \
    --plan-id {plan_id} --for edit
```

### Step 2 (optional): Write the new body

```text
Write({path from prepare-body}) with new PR body markdown content
```

### Step 3: Execute the edit

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr edit \
    --pr-number 123 --plan-id {plan_id} [--title "T"]
```

Omit `--title` to update only the body; omit Steps 1-2 to update only the
title. At least one of `--title` or a prepared body must be supplied — the
script rejects calls that change nothing.

### Step 4: Process Result

```toon
status: success
operation: pr_edit
pr_number: 123
```

---

## Workflow: Delete Remote Branch

**Pattern**: Provider-Agnostic Router (REST API)

Delete a branch from the remote. This leaf is the canonical replacement for
direct `git push origin --delete {branch}` calls in post-merge cleanup and
other remote-only branch disposal scenarios. Local branch management stays in
`git -C {path} branch` territory and is intentionally out of scope.

Under the hood:

| Provider | API call |
|----------|----------|
| GitHub | `DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}` via `gh api` |
| GitLab | `DELETE /projects/{id}/repository/branches/{branch}` via `glab api` (project path is URL-encoded as the `{id}`) |

The `--remote-only` flag is **required**: it is an explicit acknowledgement
from the caller that any needed local cleanup has already been handled and
that this call targets only the remote ref. Omitting the flag fails argparse
validation before any network call.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci branch delete \
    --remote-only --branch {branch_name}
```

When the cwd's remote configuration does not match the target, bind subprocesses to a different checkout via the standard router flags: prefer `--plan-id <plan>` (resolves the worktree through `file_ops.resolve_plan_context`, which owns the single `manage-status get-worktree-path` invocation), or fall back to the legacy `--project-dir <path>` escape hatch. `--plan-id NO_PLAN` binds to the main checkout. The two flags are mutually exclusive — see `tools-integration-ci/SKILL.md` § "Worktree-Aware Invocation" for the full routing contract and `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific path convention.

### Step 2: Process Result

```toon
status: success
operation: branch_delete
branch: feature/old-branch
remote_only: true
already_gone: false
```

When the branch is already gone remotely (HTTP 404 from either provider, or
HTTP 422 from GitHub when the ref has just been removed), the script still
returns `status: success` but with `already_gone: true`. Deletion is
idempotent by design: callers can invoke this leaf safely without needing a
prior existence check.

On other failures (e.g. insufficient permissions, non-idempotent API errors),
the script returns `status: error` with `operation: branch_delete` and a
`message`/`context` pair carrying the underlying `gh`/`glab` stderr — no
retries are attempted.
