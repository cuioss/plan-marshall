# Reference: the two central config repos

Knowledge extracted from the live configuration at epic init, so no plan re-derives it. Machine
pointers are in `references.json`; this file carries the reasoning a plan needs before touching either
repo. **Both configs are self-documenting** — every setting carries its rationale as a comment,
including the evidence that produced it. Read the file before changing it; the comment usually already
answers the question.

## `cuioss/pr-agent-settings` — `/Users/oliver/git/pr-agent-settings`

At init: on `main`, clean, at `765e23f` (#13). Discovery is by FIXED repo name, root of the DEFAULT
BRANCH. Merged BENEATH any repo-local `.pr_agent.toml`, so a repo overriding one key keeps the rest.

### Settled facts — do not re-derive

| Fact | Value / consequence |
|---|---|
| Provider | **Vertex AI** (`vertex_ai/…`), NOT AI Studio (`gemini/…`). Keyless via WIF; no Google credential in GitHub. |
| Model | `vertex_ai/gemini-3.6-flash`, falling back 3.5-flash → 2.5-flash → 2.5-pro |
| `custom_model_max_tokens` | `1048576` — **REQUIRED**, not tuning. 3.6-flash is absent from the pinned image's `MAX_TOKENS`, and `get_max_tokens()` RAISES on an unregistered model. Delete only when the image registers it. |
| `temperature` | `1.0` — REQUIRED by the Gemini 3 generation. Upstream's 0.2 default reached the model on every review this org ever ran. |
| `max_model_tokens` | `256000` (upstream 32000). Sized at 2× the largest real diff observed. |
| `max_description_tokens` | `2000` (upstream 500) |
| `num_max_findings` | **`12`** — raised from 5 by #13 |
| `publish_output_no_suggestions` | `true` — a clean review MUST be visible |
| `final_update_message` | `false` |
| `persistent_comment` | `true` |

### The three traps

1. **`ignore_pr_*` is dead config in GitHub Action mode.** `ignore_pr_labels` / `_authors` / `_title` /
   `_{source,target}_branches` are consumed only by `should_process_pr_logic()`, which exists in the
   webhook servers and NOT in `github_action_runner.py`. Setting them here silently reviews everything.
   The org skip rules live as job-level `if:` guards in
   `cuioss-organization/.github/workflows/reusable-pr-agent-review.yml`. The file says this is the
   single most important thing to know about the setup.
2. **A clipped diff reads as a complete one to the model.** Above `max_model_tokens`, `large_patch_policy
   = "clip"` truncates before the model sees it — and this manufactures CONFIDENT WRONG findings, not
   merely missed ones. API-Sheriff#118 logged `total tokens over limit: 128000` and reported an
   "Uncompleted Future Hang" while quoting the opening of the very `finally` block that refutes it.
   The "over limit" log line is the ONLY signal. **A review published above the limit must be read as
   INCONCLUSIVE, not clean.** Raising the ceiling makes clipping rarer, never detectable.
3. **`repo_context_from_default_branch = true` is a security control, not a convenience.** A document
   committed on the PR branch is invisible to the reviewer by design; pointing it at the head would let
   PR content rewrite the reviewer's own instructions. Do not "fix" the invisibility.

### The charter — read before touching `extra_instructions`

Review depth is governed by this text, **not by the model**. Measured: across five PRs, four models and
diffs from 5k to 57k tokens, every published review was byte-identical at 242 bytes — zero findings. A
result invariant under model swap is not a model result.

- ⛔ **Never reintroduce withholding language.** "Do not duplicate the other reviewers", "only when you
  can name the concrete input", "prefer one well-evidenced finding" — these three stacked on top of
  upstream's already-conservative field description and resolved to zero. Overlap costs one duplicate
  comment; suppression costs the finding.
- ⛔ **Do not "promote to pro" as a remedy for thin reviews.** Wrong twice: 3.x *pro* ids 404 on this
  project (verified on #1031), and depth is charter-governed anyway.
- The residual suppressor is **not reachable from configuration**: `pr_reviewer_prompts.toml:150`
  describes `key_issues_to_review` as "A concise list (0-{{num_max_findings}} issues)… Only include
  issues you are confident about… An empty list is acceptable." Four suppressors in one sentence.
  `extra_instructions` is appended as a separate block and argues *alongside* it, never replaces it.
  This is why #13 contests the empty-list permission directly rather than adding categories.
- 🔒 **The anti-fabrication clause is load-bearing.** Pressure to report more produces invented
  mechanisms — this reviewer did exactly that on API-Sheriff#103. Loosening the severity bar while
  HOLDING the substantiation bar is the whole design.

### Why this matters to the participation machinery

`persistent_comment = true` plus `final_update_message = false` means pr-agent **edits one comment in
place and posts nothing new** on re-review. That is the config-level cause of the `_github_pr.py:710`
count-vs-row defect: there is no new row to count, by design and correctly so. The fix belongs in the
detector, never here.

## `cuioss/coderabbit` — `/Users/oliver/git/coderabbit`

Checkout is on `main` at `a97b64f`, clean, no open PRs. (At init it sat on an unmerged falsified branch;
that was cleaned up the same day — see the branch-state rule at the bottom of this file, which is why the
check is worth repeating rather than assuming.) A repo-level `.coderabbit.yaml` FULLY overrides this file
unless it sets `inheritance: true` — the opposite of pr-agent-settings' merge-beneath behaviour.

### Settled facts

- `profile: chill`; nitpicks are treated as signal.
- `enable_prompt_for_ai_agents: **false**` and `finishing_touches.autofix.enabled: false` — set by #3
  (`a97b64f`). ⚠ **This reversed the previous config comment**, which said to KEEP the block because it
  "is the machine-readable payload plan-marshall ingests". #3's rationale is the opposite: nothing
  consumes it, plan-marshall's automatic-review standards strip it before reasoning and forbid executing
  it, so it only adds a prompt-injection surface — evidenced on plan-marshall#1038, where the block
  carried three instructions that would have reversed a settled design decision (TASK-6 `1f439c`) if
  followed. **The two claims are mutually exclusive and only one can be true.** Merged on operator
  decision; see the Watches entry in `epic.md` for the verification still owed.
- Skips: `labels: ["!skip-bot-review"]`, `ignore_usernames: [dependabot[bot], cuioss-release-bot[bot]]`.
  **CodeRabbit is the only bot that honours the skip label centrally via its own config** — pr-agent
  honours it via the workflow guard instead. The distinction is the thing a reader gets wrong.
- `path_instructions` is scoped to `**/*` **on purpose**: it targets the archetype where a claim and the
  mechanism that would implement it live in different files and only one is in the diff (API-Sheriff#123
  — two benchmark goals documented as "deliberately skipped" while both remained unconditional in an
  untouched `pom.xml`; every automated reviewer returned clean). Narrowing the glob reintroduces the
  blind spot on whichever surface is left out. It also carries the hardcoded-mirror-list rule and the
  **guard-predicate-cannot-fire** rule — the same vacuous-guard archetype this project keeps shipping.

### PR disposition (settled 2026-07-29)

| PR | State | Outcome |
|---|---|---|
| #3 | **MERGED** (`a97b64f`) | Drop the AI-agent prompt block and autofix. Operator decision. Verification owed — see Watches. |
| #4 | **CLOSED, not merged** | **FALSIFIED by plan-marshall#1043** — its own final commit says so. Notes remain readable on the closed PR. ⛔ Never revive as a fix. |

## Cross-repo working rules

- Neither config repo is covered by plan-marshall's `.plan/` tooling. Use `git -C {checkout}` and the CI
  abstraction's `--project-dir` — never `gh` directly.
- **Always confirm the checkout's branch before reading config as live.** The coderabbit checkout was on
  an unmerged falsified branch at init; this is the same trap that once had `required_bots` read from a
  shared checkout sitting on another branch.
- A change to `cuioss-organization` fans out to ~21 consumer repos through an org release tag. A change
  to either config repo takes effect on the next review with no release step — `pr-agent-settings` is
  fetched per invocation in CI mode (no 15-minute webhook cache).
