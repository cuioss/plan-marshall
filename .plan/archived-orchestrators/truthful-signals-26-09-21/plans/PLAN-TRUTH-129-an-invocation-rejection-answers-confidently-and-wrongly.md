# PLAN-TRUTH-129: An invocation rejection answers confidently and wrongly

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-03 from inbox drain messages `deployment-and-refresh-gaps-001.md` and
> `-008.md`, both relayed from the **Token-Sheriff** repo (epic `deployment-and-refresh-gaps`,
> plan `coverage-gate-visibility` PR #681 / `outbound-hostname-verification-core` PR #689) after
> `manage-lessons add` refused them there with `wrong_store`.

## Provenance

Both messages are first-party observations made **in a consumer project**, which is what makes them
worth a plan rather than a lesson: every rejection below was produced by an agent following this
repository's own shipped documentation, in a checkout that has no access to this repository's
context. ⛔ The foreign PR ids are NOT corroborable from this checkout and are carried as pointers,
never as evidence. The **argparse surfaces they name are local and fully corroborable**, and the
D0 gate below is what settles them.

## Objective

**A wrong invocation is answered with a confidently-worded wrong correction, and the three
`--plan-id` conventions that produce most of them are documented rather than reconciled.**

This is the epic's archetype at the executor boundary: the rejection message is not silent — it is
*articulate and wrong*, which costs strictly more than saying nothing, because the caller acts on it.

**Three members, each observed first-hand in one run:**

1. **The executor's unknown-notation diagnostic names a script that cannot accept the subcommand.**
   Invoking `plan-marshall:phase-6-finalize:review_completeness` returns
   `Correct format: plan-marshall:phase-6-finalize:ci_complete_precondition review_completeness`.
   ⛔ **That suggestion produces a second argparse rejection** — `ci_complete_precondition` declares
   only `resolve`. The script actually lives at `plan-marshall:automatic-review:review_completeness`.
   The executor infers *"the third segment must be a subcommand of some script in this skill"*
   **without checking that the named script accepts it**, so a wrong-bundle notation is answered
   with a confident wrong correction rather than with the correct notation or with an honest
   "not found in this bundle".

2. **Empty-string stripping is safe only for a flag declaring `nargs='?'` with a `const`, and a
   shipped doc derives its safe-when-empty reasoning from the LIST flags alone.**
   `review_completeness check --measured-diff-size ""` exits 2 (`expected one argument`). The six
   bot-observation flags each declare `nargs='?', const=''`, so the stripped bare flag still parses;
   `--measured-diff-size` is a SCALAR on the same subcommand with neither, so the same stripping
   leaves it bare and argparse rejects the call before the script body runs.
   ⛔ `phase-6-finalize/standards/branch-cleanup.md` § Predicate 2 explains at length that the
   executor strips empty-string args so a bare flag is safe. **The reasoning is correct for the
   flags it enumerated and is presented as a property of the command.** The flag's own help string
   already states the remedy ("Omit it (the default) when unmeasured"), so the trap and its fix live
   one screen apart and neither points at the other.

3. **Three sibling scripts follow three mutually contradictory `--plan-id` conventions, and only one
   of them says so on rejection.** Five exit-code-2 rejections in one run, three of them `--plan-id`:
   `ci` — a **top-level router flag**, valid only BEFORE the verb; `github_pr` — declares **no
   `--plan-id` whatsoever**, so appending it is always a rejection; `manage-*` — declares it **on the
   subcommand, after the verb**. `persona-plan-marshall-agent` § *"Never invent script subcommands"*
   already enumerates five recurrence signatures including this pair, and it **fired anyway, three
   times in one run**. ⭐ Codified prose describing three contradictory conventions is not something
   an agent applies reliably under load; the remediation shape is structural, not documentary.

⭐ **The `ci` rejection is the model, and it already exists in-tree:**

> `note: --plan-id is a top-level flag and belongs BEFORE the subcommand (verb), not after it. The
> flag exists — it is only in the wrong position.`

That message distinguishes **wrong position** from **does not exist**, which is precisely the
distinction every caller above got wrong. `github_pr` emitted a bare `unrecognized arguments` with no
such note.

## Deliverables

1. **D0 — GATE: derive the population before choosing any remedy.** Enumerate (a) every script in the
   marketplace declaring `--plan-id` and which of the three conventions it follows, and (b) every
   scalar flag sharing a subparser with `nargs='?'` list flags — the member-2 hazard class. ⛔
   **Publish both populations with their sizes and the sweep that produced them.** The three members
   above are the instances one run happened to hit, **not** the population; treating them as the
   population is the exact archetype this epic tracks. D0 may legitimately conclude that the
   convention is already uniform in n−1 cases and that the remedy is a single script fix.
2. **D1 — the unknown-notation diagnostic must not suggest a notation it has not validated.** Before
   emitting `Correct format: …`, resolve the suggested script and confirm it declares the named
   subcommand. When no candidate validates, say so — an honest "no script in `{bundle}:{skill}`
   declares `{name}`; searched N scripts" is strictly more useful than a confident wrong answer.
   ⭐ Where the script exists in a DIFFERENT bundle, the resolver already has the inventory to say so.
3. **D2 — make the position-aware remediation note uniform across the `--plan-id` family**, so each
   rejection states which of the three conventions that script follows. ⛔ **D0 decides whether this
   is the right arm at all:** the convergent alternative is to make the convention uniform rather
   than to document the divergence a sixth time, and that arm must be costed, not dismissed.
   Record the rejected arm and why.
4. **D3 — correct `branch-cleanup.md` § Predicate 2's scalar carve-out.** Name `--measured-diff-size`
   and the omit-when-empty remedy, and scope the safe-when-empty claim to the declaration form that
   actually supports it. ⛔ **A narrative that says "a bare flag is fine here" must name the scalars
   on the same subcommand it does NOT cover** — absent that carve-out the prose is an accurate
   description of a subset presented as a property of the command.
5. **D4 — matched controls, one per member.** Each must show the failing invocation is now diagnosed
   correctly **and** that a well-formed invocation is unchanged. ⛔ **The negative control is
   load-bearing**: a D1 that answers "cannot validate" for notations it previously resolved correctly
   has replaced a confident wrong answer with a useless one.

## Claim Labels

- OBSERVED: `review_completeness check --measured-diff-size ""` exits 2 — reported first-hand by the sending run.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: review_completeness.py check_parser --measured-diff-size is still default='' with no nargs='?', so argparse rejects a stripped-empty bare flag
- OBSERVED: the six bot-observation flags declare `nargs='?', const=''` and `--measured-diff-size` does not — the sender quotes both declarations from `review_completeness.py`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Confirmed 10 nargs='?' flag declarations against --measured-diff-size plain scalar declaration at the same subcommand
- OBSERVED: the executor answered `plan-marshall:phase-6-finalize:review_completeness` with a suggestion naming `ci_complete_precondition`, which declares only `resolve`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: execute-script.py.template still picks matching_scripts[0] and suggests it without checking the named subcommand is declared
- OBSERVED: five exit-code-2 rejections in one run, three of them `--plan-id` position/existence errors across `ci`, `github_pr` and a `manage-*` script.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Three distinct --plan-id conventions (router-flag, none, subcommand-flag) structurally confirmed across ci, github_pr and manage-* scripts
- OBSERVED: the `ci` rejection already carries a position-aware note distinguishing wrong-position from does-not-exist; `github_pr` does not.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The is a top-level flag and belongs BEFORE position-aware note is still present at tools-input-validation/input_validation.py
- HYPOTHESIS: the three `--plan-id` conventions are the whole convention population. ⛔ **This orchestrator's inference from three instances, not a claim any message makes.** Confirm/refute at `marketplace/bundles/*/skills/*/scripts/*.py` § the `--plan-id` `add_argument` / router-flag declarations (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Full marketplace --plan-id convention population sweep not performed here
- HYPOTHESIS: the member-2 hazard generalises past `review_completeness` to other subparsers mixing scalar and `nargs='?'` flags. ⛔ NOT checked. Confirm/refute at the D0 sweep (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Full sweep for scalar and nargs='?' mixed subparsers beyond review_completeness not performed here
- Verify-first clause: before D3, settle whether `branch-cleanup.md` § Predicate 2 still carries the safe-when-empty passage at HEAD. If a later plan already corrected it, D3 is a no-op and the plan re-scopes.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: branch-cleanup.md Predicate 2 still explains nargs='?' safety at lines ~915-922 without naming the --measured-diff-size carve-out

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-script-executor/**` — the unknown-notation diagnostic (D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the scalar/`nargs` mix (D0, D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — § Predicate 2 (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` — the model rejection note (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the bare rejection (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/tools-script-executor/**`, `test/plan-marshall/automatic-review/**` — the D4 controls (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — the script-failure taxonomy that files a caller-side notation error as a foreign script’s internal bug, added 2026-09-04 by the drain fold of `documented-invocations-...-011` (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` — Step 7’s prescription of a verb that is not on the argparse surface, added 2026-09-04 by the cui-http fold § 1.6 (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` — the
  `--plan-id` arm's cwd resolution through `metadata.worktree_path`, and the `auth_failed` funnel —
  added 2026-09-05 by the `-126` drain fold of message `-007` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md`
  — the `error_cause` → `[FAILED]` headline mapping (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-build-server/**` and
  `marketplace/bundles/plan-marshall/skills/build-server-client/**` — the `submit` path-shape
  rejection mis-coded as `executor_mismatch` — added 2026-09-05 by the lessons-handling fold of
  message `-008` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/` — creation-time validation
  of stamped `verification.commands` notations — added 2026-09-11 by the fold of
  `lessons-handling-26-09-04-01-040` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/` — `prune-local-and-remote-ref`'s
  derived-target contract as documented to callers — added 2026-09-11 by the fold of `-045` C (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Overlaps with `PLAN-TRUTH-101` (LAUNCHED)** — *documented invocations that cannot succeed as written*. That plan's surface is `manage-tasks` and `finalize-step-deploy-target`; this one's is the executor diagnostic and the `--plan-id` family. **The subjects are adjacent and the files are disjoint**, but `-101`'s scope DRIFTED during execute to include `ref-toon-format/scripts/toon_parser.py`. ⛔ **Re-run `corpus cross-check` against `-101`'s live `references.json` before emitting** — do not rely on this note.
- Adjacent to: `PLAN-TRUTH-119` (early-phase gates cannot be told apart from confident answers) — same "articulate and wrong" shape one phase earlier. Keep separate; the surfaces do not meet.
- Adjacent to: `pm-plugin-development:recipe-fix-argparse-rejection`, which is the existing remediation recipe. D0 must read it before proposing a sixth documentation pass.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-129-an-invocation-rejection-answers-confidently-and-wrongly.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`documented-invocations-...-011`** — *a caller-side invented notation is classified as a script-internal bug in a script that does not exist.* Two of the run’s 11 unique failures were filed as `type: bug`, `subtype: script_internal_error`, **against a `component` that is not a component** — `plan-marshall:manage-status:manage_status` and `plan-marshall:manage-execution-manifest:manage_execution_manifest`. ⛔⛔ **The executor’s own stderr already names the cause exactly, and names it as a CALLER error** (*“The third part appears to be a subcommand, not a script name”*) — **the classifier reads the exit code and the empty-subcommand field and lands on `script_internal_error` anyway.**

  ⭐⭐ **The corroboration in this message is a model of the discipline this epic asks for, and is reproduced because the SHAPE matters as much as the result.** `architecture search --content` for the manifest form returns **`count: 0` over `files_scanned: 5335`, `unreadable: 0`, `truncated: false`, `elided: 0` — a clean-coverage zero**; the sibling sweep for the `manage-status` form returns **19 hits in 10 files, and EVERY ONE is plugin-doctor rule material or its negative-test fixtures.** ⇒ **the underscore form is prescribed nowhere; it is a documented anti-pattern with an edit-time detector.** ⚠ And the coverage caveat is stated rather than assumed: *“the inventory sweep does not walk `.claude/**` or `.github/**`, so this is a clean negative over the inventoried tree, not over the whole checkout.”*

  ⭐⭐⭐ **The gap the pair exposes, and it is this spec’s subject exactly:** there is an **edit-time** detector for the underscore notation in documents (`notation-staleness`) and **NO call-time counterpart**. *“An agent that types the form at invocation gets exit 1, a misattributed `bug` finding, and no rule fires.”* **Ask:** give the notation rejection its own subtype (`invalid_notation`, `type: anti-pattern`) attributed to the **calling** component, routed to the same invented-invocation class as `invented_subcommand`. ⛔ *“A defect class that already has a structural detector on one surface should not be silently reclassified as a foreign script’s internal bug on the other.”*

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

**Theme 1 folds here in full — 7 findings, 11 source lessons, the corpus's largest cluster.**

⛔⛔ **§1.1 is the structural diagnosis and it names the tier: BOTH existing guards fire at the wrong time.** `plugin-doctor` / `ARGUMENT_NAMING_*` is an **edit-time** guard checking invocations *authored into marketplace documents* — it cannot see a command an agent **composes at runtime** from surrounding workflow prose. The recurrence-signature list in `persona-plan-marshall-agent` is **prose in a skill body**, loaded into context but not re-derived by an agent reasoning from the narrative in front of it. **Neither sits on the actual failure surface: the moment argv is handed to the executor.**

⛔⛔⛔ **The sharpest fact in the theme, and it rules out the obvious remedy: FOUR OF FIVE rejections came from the main-context ORCHESTRATOR, not a dispatched leaf.** The rule is demonstrably *loaded* at the tier that violated it — `persona-plan-orchestrator` declares `persona-plan-marshall-agent` as its unconditional base, carrying *"never invent script subcommands"* as an inline hard rule. ⇒ **neither a prose-coverage gap nor a persona-loading gap. The orchestrator tier composes more argv than any other and has no invocation-time guard at all.** ⚠ Third-party confirmation the document supplies against itself: **the consolidating session produced six MORE rejections of this class while doing so** (`manage-lessons show`, `manage-lessons read --id`, `ci pr landing-state --number`, `ci pr view --number`, `manage-logging decision --level WARN`, `workflow-integration-github bot_completion`).

⭐⭐ **§1.2 supplies a SIXTH recurrence signature that defeats the existing self-audit, and it is new to this spec.** The five known: verb-paraphrase; doubled bundle-prefix; router-scoped flag after the verb; verb-scoped flag omitted; compound value given its left half. **#6 — CROSS-SCRIPT VERB MISATTRIBUTION**: `build-decision` applied to `manage-execution-manifest`, when it is a **real verb, on `manage-config`**. ⛔ **Signature 6 is NOT a variant of signature 1.** Signature 1's self-audit question — *"is this verb real, or did I make it up?"* — returns **"real"** for signature 6 and waves the call through: the name resolves in memory because it genuinely exists somewhere in the marketplace, and only its owning script is wrong. ⭐ Two mechanical closures the document derives: a did-you-mean hint mapping `query` → `list` closes signature 1 on `manage-findings` because **a read-verb synonym is chosen by narrative fit**; and ⛔ **`--plan-id` position is PER-VERB, never per-router-wide** — `ci checks` takes it before the verb, `ci issue prepare-comment` after, **both fired on the same router in one run** — so the `ci` SKILL.md wants an explicit per-verb table. **This directly sharpens D2, which currently assumes three per-SCRIPT conventions; the real granularity is per-VERB.**

⭐ **§1.3 — an argparse rejection must trigger `--help`, not a second guess.** The existing rule (*"when in doubt, invoke with `--help` first"*) is **pre-hoc**, conditioned on the agent already feeling doubt, and **silent on the post-hoc case where failures double**: after `exit_code: 2`, doubt is no longer a judgement call — **it has been established as fact by the interpreter.** Observed: `switch-and-pull` rejected for a missing `--base`, retried, rejected again for a missing plan-id selector. **One `--help` after the first rejection would have shown both.**

⛔⛔ **§1.4 — a rejection misdiagnosed as an ENVIRONMENT failure, and this is the most dangerous member.** A dispatched leaf placed `--plan-id` after the verb, read the non-zero exit as a **provider authentication problem**, returned `loop_back` and **recommended the operator re-authenticate the CI provider. No credential was ever involved.** *"A domain-plausible misdiagnosis is strictly worse than a bare 'call failed' — it is actionable and wrong."* ⭐ **The distinguishing evidence is always present and cheap: exit 2 plus `usage:` / `unrecognized arguments` / `invalid choice` means the script body NEVER RAN**, so *no* conclusion about the script's domain is derivable. **A leaf that cannot distinguish the two must return the rejection verbatim and let the orchestrator classify.**

⭐ **§1.5 — a compound-valued flag needs its GRAMMAR in the placeholder.** `--participated-bots BOTS` describes cardinality and says nothing about grammar, so **every check that reasons about flag NAMES passes** — name, position and verb all correct — and only the value's internal grammar is wrong, with the rejection coming from a hand-rolled parse. ⭐⭐ **The codebase already solves this correctly elsewhere**: `mark-step-done --fact KEY=VALUE` puts the grammar in the placeholder. **A derivable plugin-doctor rule falls straight out: a flag whose script-side parse splits on a separator, but whose documented placeholder contains no separator, is a detectable documentation gap.**

⛔ **§1.6 — a workflow doc naming a verb that does not exist, with a measured downstream consequence.** `q-gate-validation.md` Step 7 instructs `manage-references sync-affected-files`, **not on the argparse surface**. ⇒ `references.affected_files` is never populated at plan time, so **`manage-status sibling-collision-check`'s file-overlap leg silently degrades to source-origin matching only.** `capture-footprint` is not a substitute at that phase — it needs a worktree that does not exist until phase-5 Step 2.5. ⚠ **`ARGUMENT_NAMING_*` derives its accept-set from a live `--help` walk and SHOULD have caught this** — the document flags, and does not answer, whether the rule scans `workflow/*.md` bodies or only `SKILL.md` canonical blocks. **That question belongs in D0.**

⚠ **§1.7 folds into `PLAN-TRUTH-121` instead** (a multi-argument mutation reporting aggregate success over a partial write) — recorded here so the theme's disposition is complete rather than appearing to drop a member.

## ⛔⛔ FOLDED 2026-09-05 — PLAN-TRUTH-126 drain (1 message) + `review-apparatus` forward (1 message)

### `shipped-guards-...-007` — a wrong `error_cause` renders a MERGED plan as `[FAILED]`

Finding `866bcd`. **Corroborated first-party by this orchestrator, and the corroboration is stronger
than the report because the defect OUTLIVES the run.** Three same-session readings disagreed:
`ci --plan-id <plan> pr view` → `error_cause: auth_failed`; `ci_health verify` → `authenticated true`;
`gh auth status` → two logged-in accounts with an active token.

**Root cause, verified against the ARCHIVED record — the state is still there:**

```text
metadata.use_worktree   = True
metadata.worktree_path  = .plan/local/worktrees/shipped-guards-assume-the-meta-projects-own-layout
directory exists        = False        <- removed by branch-cleanup at order 70
```

The `--plan-id` arm resolves `cwd` through that dead path, the `gh` subprocess cannot start, and the
failure is funnelled into the `auth_failed` arm. ⭐ **Proof by control, reproduced here 2026-09-05:**
the same call with `--project-dir <main>` returns `state: merged`,
`merge_commit_sha: 28b578f1ed435973e53c510f0c8225446cc024aa`.

⛔⛔ **The cost is the renderer, not the call.** `error_cause: auth_failed` maps to a `[FAILED]`
headline, so **every worktree-using plan renders as FAILED after a successful merge**, and the
operator is sent to `gh auth login` — a fix that cannot work. ⭐ **This is exactly this spec's
archetype at a new seam: articulate and wrong costs strictly more than silent, because the caller acts
on it.** ⚠ Two distinct defects, and D0 must keep them apart: (a) a stale `worktree_path` survives
`branch-cleanup` in persisted state, and (b) a subprocess-start failure is classified as an auth
failure. **Fixing (a) alone leaves the misclassification for every other dead-cwd cause.**

### `review-apparatus-032` — 18 argparse rejections in one run, four shapes, one aggregated item

Forwarded to us by the sibling epic. ⭐ **Aggregated by them into ONE item rather than 18** — the same
discipline `-004` applies to this run's own 10 notations. ⇒ **n grows and the item does not.**
⚠ **Independent corroboration that D0's population is larger than the three members this spec was
staged on**; D0 must derive the population, never inherit a count from any single run's tally.

### `lessons-handling-26-09-04-01-008` — `marshalld submit` rejects a relative executor path as `executor_mismatch`

⭐ **Third seam, same archetype, and the WORST wording of the three.** A relative executor path is
rejected with `executor_mismatch` — a code whose plain reading is *"your executor is the wrong
VERSION"*. ⛔ **It is not a version problem at all**; it is a path-shape problem with a one-character
remedy. The reader is sent to `/sync-plugin-cache`, executor regeneration, or the plugin-pin repair —
**an expensive and entirely wrong diagnostic path**, and one this epic has recorded operators walking
for real. ⇒ **D2's remedy-naming obligation reaches this site**: a rejection must name the discharge
condition, and `executor_mismatch` names a different one than the one that applies.

⚠ **Expected Surface widened in this same act** — see the `manage-build-server` / `build-server-client`
entry added below.

### `preference-admissibility-...-005` — a read verb ACCEPTS a scoping flag, ignores it, and answers confidently about the wrong scope

⭐⭐ **A fourth seam, and the only one where nothing is rejected at all.** The three members this spec was
staged on all *refuse* and refuse wrongly. This one **accepts** — the flag is parsed, the call succeeds,
and the answer is about a scope the caller did not ask for. ⛔ **There is no error surface to read, so
every existing remedy in this spec (better rejection text, a named discharge condition) is unreachable
here.**

⇒ **D0's population must include ACCEPTED-AND-IGNORED flags, not only rejected ones.** A sweep that
enumerates rejection sites finds none of these, and the resulting count would look like coverage.
⚠ **The pair is the point**: a rejected-but-misexplained flag and an accepted-but-ignored flag are the
two ways a flag can fail to mean what it says, and only the first is visible to a caller.

## ⛔ FOLDED 2026-09-06 — `review-apparatus-033` drain (1 recurrence + 1 ROOT CAUSE for a member already here)

### Item 2 (`-008`) — argparse rejections: 5 more notations, and the table is A FLOOR

⛔ **Folded as a RECURRENCE onto the `review-apparatus-032` aggregate already in this spec — NOT staged
a second time.** The sender said so explicitly and it is right.

⚠⚠ **THE QUALIFICATION IS THE PART THAT MUST SURVIVE THE FOLD, and it is easy to lose:** the sending
dispatcher observed **8 distinct failing notations** and **2 lie OUTSIDE the log window that step
paged.** ⇒ **Its 6-notation table is a LOWER BOUND, not a complete set.** A fold that carries the table
and drops the floor qualification would hand D0 a population that reads as complete and is not — this
spec's own archetype, committed inside its own evidence.

### The `bd825d` recurrence — THIRD occurrence, and it finally names the ROOT CAUSE

This spec already carries the `ci pr view` dead-cwd misclassification (`866bcd`), whose persisted-state
half is *a stale `worktree_path` surviving `branch-cleanup`*. **That half now has a mechanism and a
third sighting:**

> `worktree-remove` left `use_worktree: true` and a `worktree_path` naming the deleted directory, so
> **every phase-entry assertion refused with `worktree_unresolved`** and the finalize could not be
> resumed until **two `manage-status metadata --set` calls repaired it by hand.**

⭐⭐⭐ **ROOT CAUSE, stated by the sender and worth more than the incident: `worktree-remove` is NOT the
symmetric counterpart of `worktree-create`, which sets BOTH fields.** ⇒ **The fix is symmetry, not a
guard.** ⛔ This epic independently observed the same stale state in the archived records of `-126` and
`-093`; **with this it is n=3 across three plans, and the two halves (`auto_failed` misclassification,
stale persisted path) are confirmed separable.**

## ⭐ FOLDED 2026-09-06 (c) — TWO LIVE INSTANCES OF THIS SPEC'S ARCHETYPE, OBSERVED WHILE DOING SOMETHING ELSE

### 1 — the executor's unknown-notation suggestion is articulate and wrong, again

Invoking `plan-marshall:manage-change-ledger:manage_change_ledger` during the daemon sweep returned:

```text
Invalid notation ... The third part 'manage_change_ledger' appears to be a subcommand, not a script name.
Correct format: plan-marshall:manage-change-ledger:manage-change-ledger manage_change_ledger
```

⛔ **The suggested command is WRONG**: `manage_change_ledger` is not a declared verb, so following the
suggestion produces a second rejection. ⇒ **A LIVE re-confirmation of claim 2** (`execute-script.py.template`
picks `matching_scripts[0]` and suggests it **without checking the named subcommand is declared**),
observed incidentally rather than by a sweep. **The correct invocation was `... query --kind build`.**

### 2 — the stale-daemon case where `executor_mismatch` would be RIGHT

The live daemon runs `0.1.1603` while the resolver returns `0.1.1607` (`binary_diverges: true`). ⇒ **A
caller at 1607 submitting to a 1603 daemon is genuinely a version mismatch** — so the folded
`marshalld submit` rejection, which mis-names a *path-shape* problem as `executor_mismatch`, **collides
with a real condition that deserves that exact name.**

⛔⛔ **That sharpens the fold rather than softening it: the code has ONE error token for TWO distinct
conditions, one of which it diagnoses correctly and one of which it does not.** ⇒ **D2 must not simply
re-word `executor_mismatch`; it must SPLIT it**, or the rename breaks the case that was right.

## ⛔ FOLDED 2026-09-07 — PLAN-TRUTH-128 drain (2 items). BOTH NARROW D0's POPULATION IN THE SAME DIRECTION.

### `freshness-gate-...-009` — four argparse rejections in one run, ALL on CORRECT verbs with the WRONG FLAG

⭐⭐ **This narrows the defect class in a way the earlier aggregates did not.** The prior folds
(`review-apparatus-032`'s 18 rejections, `-008`'s 5 more) counted rejections; **this one classifies
them: the verb was RIGHT every time and the FLAG was wrong.** ⇒ **The executor's notation-suggestion
defect (claim 2) is not the dominant shape — the dominant shape is a caller reaching a real verb and
mis-spelling its flag set.** ⛔ **D0 must partition rejections by which part was wrong (notation vs
subcommand vs flag), or a remedy aimed at notation suggestions will miss the majority class.**

### `freshness-gate-...-010` — `github_re_review re-review --push-time` is a REQUIRED flag whose own help text says otherwise

⛔ **A help string that contradicts the parser it documents** — the advertised form is unusable, and the
caller learns the truth only from a rejection. ⇒ **This is the ADVERTISED-FORM half of this spec**, and
it is the inverse of the `--measured-diff-size` member already here (a scalar where `nargs='?'` was
implied): **there the parser was stricter than the docs implied; here the flag is required where the
help says optional.** ⭐ **Two opposite mismatches at the same seam mean the class is
`help-text-vs-parser divergence`, not `optionality`** — and it is mechanically detectable by comparing
`required=` against the help string, with no semantics needed.

## ⭐ FOLDED 2026-09-07 (b) — PLAN-TRUTH-099 drain (1 item)

`-007` (`plan-marshall:plan-marshall`): **stop documenting deliverable 0 for triage fix tasks THE
VALIDATOR REJECTS.**

⛔ **A document prescribing a form its own validator refuses** — the doc-vs-parser divergence class this
spec already owns from `--measured-diff-size` (parser stricter than the docs implied) and
`github_re_review --push-time` (flag required where help says optional). ⇒ **Third member, third
direction: here the DOC advertises a shape the validator rejects outright.**

⭐⭐ **Three instances in three directions settle the class name.** It is not *optionality*, not
*help-text accuracy* — it is **advertised-form-vs-accepted-form divergence**, and it is mechanically
detectable wherever a doc's worked example can be replayed against the parser it documents. ⛔ **D0
should enumerate documented invocations that are REPLAYABLE and replay them**, rather than reading docs
for plausibility.

## ⭐ FOLDED 2026-09-07 (c) — PLAN-TRUTH-125 drain (1 item)

`-006` (`tools-script-executor`). ⚠ Folded as a **recurrence** onto this spec's executor-diagnostic
member rather than as a new one — that member now carries reports from four separate runs.

⭐ **The population has stopped growing in KIND while continuing to grow in COUNT.** Every new report
lands in one of the three shapes already enumerated (notation wrong · subcommand wrong · flag wrong).
⇒ **D0's partition is holding, which is evidence the class is closed** — and that is a result worth
publishing, since a partition nobody has been able to break is stronger than one merely proposed.

## ⛔⛔ FOLDED 2026-09-08 — lessons-handling drain (1 item). FOURTH OCCURRENCE OF THE STALE WORKTREE PATH.

`-024` (`workflow-integration-git`): **`worktree-remove` leaves `metadata.worktree_path` pointing at
the deleted directory, so every later resolution through it fails.**

⇒ **n = 4, and the sightings are independent**: this epic observed the stale state first-party in
`-126`'s and `-093`'s archived records; `arm-the-refusal-...-001` reported it with the root cause
(*`worktree-remove` is NOT the symmetric counterpart of `worktree-create`, which sets BOTH fields*);
and this is the fourth, from a third epic.

⛔ **The defect is fully diagnosed and unowned.** ⚠ **Four corroborations add no information the root
cause did not** — as with `-138`'s six corpora, **what the count measures is the DELAY, not the
defect.** ⭐ Record that in the shipped doc: *a defect whose mechanism is known does not become better
understood by recurring; it becomes more expensive.*

## ⭐⭐ FOLDED 2026-09-11 — cross-repo lessons drain (2 Token-Sheriff items)

### `-045` — three flag-shaped invocation mistakes, one of them narrated as a credentials failure

All three were the orchestrator's own mistakes against correct scripts; the sender self-reports them.

- **A — recurrence of the `auth_failed` funnel already declared in § Expected Surface** (folded 2026-09-05
  from `-126`/`-007`): a router-scoped `--plan-id` placed after the verb on `ci` was argparse-rejected, and
  the consuming `create-pr` step reported **"gh not authenticated"** and halted; a second route
  (`--project-dir`) produced the same false auth narrative. ⇒ Two routes, one misclassification — it lives
  in the consumer's error mapping, not in either flag. The remedy the sender states is this spec's own:
  **never translate a non-zero `ci` exit into an authentication verdict unless the payload carries an
  auth-class error code.** An `unrecognized arguments` rejection and a 401 are different facts.
- **B — arity heterogeneity**: `review_completeness check --measured-diff-size` was passed empty; it is a
  plain-value flag while its list-shaped siblings accept a bare form. This is the scalar/`nargs` mix D0/D3
  already names. ⭐ The substantive half: *passing an empty measurement and omitting the measurement are
  different assertions*, and only omission means "not measured".
- **C — a flag invented from the verb's own semantics**: `--branch` passed to
  `workflow-integration-git prune-local-and-remote-ref`, which derives its target and declares no such
  flag. A third signature beside verb-paraphrase and flag-position: the verb name advertises a subject, so
  the caller supplies it.

⇒ The sender's closing observation is worth carrying into D0: **all three are one habit — reasoning about a
flag from context rather than reading its declaration** (position, arity, existence).

### `-040` — a fix-task's stamped verification notation is not validated when the task is written

Triage-allocated fix tasks TASK-011/-012 carried `plan-marshall:build-maven:maven_build run …`; the
executor rejected it with `Unknown notation` (the script is `maven`). TASK-001…010, stamped by phase-4,
were correct. ⛔ **Sender's remedy half REFUTED at HEAD**: *"derive it rather than hard-coding a second
copy"* presumes a literal — OBSERVED: `build-maven:maven_build` occurs nowhere under `marketplace/bundles/`
at `356973d80`, so the notation was **authored at allocation**, not copied from a stale constant. ⇒ The
surviving remedy is the other one: **validate every stamped `verification.commands` notation against the
executor's registered notations at task-creation time**, so an unresolvable notation fails when the task
is written rather than when a leaf runs it. Same archetype as D1 from the producer side: the rejection is
loud, but it arrives at the wrong time and at the wrong actor.

### Claim labels for this fold

- OBSERVED: no occurrence of `build-maven:maven_build` under `marketplace/bundles/` at `356973d80` (tree-wide search, zero hits).
- HYPOTHESIS: `manage-tasks` fix-task creation accepts a `verification.commands` entry without resolving its notation — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/` § the task add/verification write path (verify-at-outline).
- HYPOTHESIS: the consuming step maps a `ci` argparse rejection to an auth verdict — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md` § the `error_cause` → `[FAILED]` mapping (verify-at-outline).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-154-operator-facing-authority-surfaces-that-answer-confidently-and-wrongly.md` (PLAN-TRUTH-154)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
