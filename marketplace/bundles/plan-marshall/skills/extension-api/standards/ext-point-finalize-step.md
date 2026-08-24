# Extension Point: Finalize Step

> **Type**: Phase-6 Step Doc Extension | **Hook Method**: `implements:` frontmatter on each step doc | **Implementations**: 26 | **Status**: Active

## Overview

A finalize step is one unit of work in the phase-6-finalize pipeline — push, create-pr, lessons-capture, sonar-roundtrip, archive-plan, and so on. Each step is an LLM-driven body doc (a `workflow/*.md` or `standards/*.md` file under `phase-6-finalize`, an opt-in bundle `SKILL.md`, or a project-local `.claude/skills/finalize-step-*/SKILL.md`) whose `---`-fenced frontmatter declares the step's identity, execution order, default-seed membership, and named-preset memberships.

This extension point names that step-doc archetype so finalize steps are identified by an `implements:` frontmatter declaration — the same identification model every other archetype already uses (domain-bundle, build, triage, recipe, outline, self-review) — rather than by hand-maintained registry constants. The declaration IS the membership marker: a step doc that carries `implements: plan-marshall:extension-api/standards/ext-point-finalize-step` is a finalize step; one that does not is not. There is no `finalize_step: true` marker, no second discovery structure, and no per-source glob.

Discovery routes exclusively through the canonical extension-discovery machinery. The reusable `extension_discovery.find_implementors(...)` query (see [Resolution](#resolution)) enumerates every step doc that declares this interface and returns each step's frontmatter as a structured record. The finalize-step registry, the named-preset builder, and every cross-bundle consumer CONSUME that one query; none of them carries a parallel list.

## Implementor Requirements

### Implementor Frontmatter

All finalize-step docs must include in their frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
```

A step doc that already declares another interface (e.g. `ext-point-execution-context-workflow`, which the `workflow/*.md` step bodies carry) declares both in YAML block-sequence (list) form:

```yaml
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
```

**Frontmatter is the sole source of truth for finalize-step discovery.** The `find_implementors()` scanner reads the `implements:` declaration from each candidate step doc and selects every doc whose declaration includes the canonical value above. The scanner does **not** read the markdown body for a discovery signal, and it does **not** identify a step by a directory-name or filename heuristic. A step doc whose frontmatter omits the declaration is not discovered.

Beyond the `implements:` declaration, each finalize-step doc carries the frontmatter contract in the table below, whose `Required` column is the authoritative statement of which fields are required and which are conditional. These fields replace the removed `BUILT_IN_FINALIZE_STEPS` / `OPTIONAL_BUNDLE_FINALIZE_STEPS` lists and the `*_DESCRIPTIONS` maps as the per-step source of truth:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | Yes | The step id. `default:{bare}` for a built-in phase-6-finalize step (e.g. `default:push`), `{bundle}:{skill}` for an opt-in bundle step (e.g. `plan-marshall:plan-retrospective`), `project:finalize-step-{bare}` for a project-local step (e.g. `project:finalize-step-deploy-target`). |
| `order` | int | Yes | Integer execution order. The seed and the discovery query both sort by this value, so the on-disk `phase-6-finalize.steps` order is deterministic. **Choose the value from the banded allocation contract in [finalize-step-order-bands.md](finalize-step-order-bands.md)** — it states the bands, the ranges reserved for project-local / third-party steps versus the shared bundle, and the reserved insertion gaps. **No two finalize-step docs may share an `order`** (the collision rule; enforced by the step-discovery test). |
| `default_on` | bool | Yes | `true` ⇒ the step is included in the default seed (`_seed_finalize_steps()` filters to `default_on == true`). `false` ⇒ the step is discoverable but opt-in (it is added to a project's `phase-6-finalize.steps` only by an explicit preset or hand-registration). |
| `presets` | list[str] | Yes | The named presets this step belongs to — a (possibly empty) subset of `[local, standard, full]`. The preset builder derives "step S belongs to preset P" as `P ∈ S.presets`. An empty list `[]` means the step is in no named preset. |
| `description` | str | Yes | The human-readable discovery description (shown by `list-finalize-steps` and the wizard). This is the single source of the per-step description, replacing the removed `*_DESCRIPTIONS` maps. |
| `mutates_source` | bool | Conditional | `true` means the step edits tracked source at runtime; such a step MUST be ordered before `default:branch-cleanup`, per [phase-6-finalize/standards/source-edit-pushability.md](../../phase-6-finalize/standards/source-edit-pushability.md). Declaring this field is **mandatory** for any step whose `order` is at or after the dynamically-resolved merge gate (`default:branch-cleanup`) and optional for a step ordered below it. |
| `head_dependent` | bool | Conditional | `true` means the step's verdict is computed against a specific worktree HEAD, so a recorded `done` is only valid for the SHA it was computed against. Such a step MUST persist `--head-at-completion {sha}` on its terminal `done` record — an obligation that is **enforced, not merely stated**: `manage-status mark-step-done` REFUSES a `done` record from a `head_dependent: true` step that carries no SHA (see [The fail-closed anchor obligation](#the-fail-closed-anchor-obligation) below). The dispatcher's re-entry check re-fires the step when HEAD has advanced (a loop-back commit, a force-push, or a rebase). The governing discriminator, applied verbatim so classification is reproducible: **"would this verdict change if HEAD changed?"** Declaring this field is **mandatory** for a step matching either of two shapes — (1) it records a pass/fail verdict over tracked source or over the remote state of that source, or (2) it is a settle-stage step whose edits land directly in the worktree (its edits were computed against the HEAD it read, so a HEAD advance supersedes them) — and optional (defaulting to `false`) otherwise. A step matching **neither** shape — one that records *an action performed* (rebase, push, PR created, archive written) and leaves no edits of its own — has no verdict to go stale and is not head-dependent. |
| `verdict_inputs` | list[str] | Optional | The fnmatch globs naming the tracked paths whose **content** the step's verdict reads — the surface a HEAD advance must touch to be capable of changing the recorded answer. Meaningful only alongside `head_dependent: true`. The governing discriminator, applied verbatim so classification is reproducible: **"if the tree differs from the recorded SHA ONLY outside these paths, would re-running this step produce a different verdict?"** — a declaration is admissible only when the honest answer is *no*, and every glob must be substantiated by a named arm or read in the step's own doc rather than guessed. Globs follow the `build.map` convention: matched with `fnmatch` against the full repo-relative path, single-`*` (never recursive `**`), because `fnmatch`'s `*` spans `/`. **The declaration MUST be a superset of what the step reads**, verified against the step's own arms rather than against what it obviously cares about — a missed input silently skips a gate that needed to run, which is a correctness defect, not a cost one. **Absence is the fail-closed default and is never read as "matches nothing"** — a step that declares no surface keeps the unconditional re-fire-on-any-HEAD-advance behaviour, so adoption is opt-in per step and silence never buys a skip. Declare **what determines the TRUTH of the recorded claim, not what determines the step's future behaviour**: a file that redefines what the verdict *means* (the matcher a sentinel check is stated relative to) is an input; the step's own procedural doc — its staging list, its detail wording — governs what it does next time and cannot falsify a verdict already recorded about the tree, so it is not. Two families MUST NOT declare a surface at all. **(a) A verdict over the REMOTE state of the tree** (a CI, review-bot, or Sonar verdict against the pushed HEAD), because any advance that reaches the remote re-stales it regardless of which paths moved. **(b) A body that executes something open-ended over the repository**, where no proper subset satisfies the superset bar and a whole-tree declaration would be an inert lever wearing the shape of a real one. **The disqualifying shapes of family (b), and which step exhibits which, are owned by [phase-6-finalize/standards/verdict-currency.md](../../phase-6-finalize/standards/verdict-currency.md) § "The classification" — read the shapes there.** This row deliberately keeps no copy of that list: an enumeration restated here would be a second source to drift from the owner, which is exactly how the qualifier distinguishing a link-checker's *resolution base* from its *containment boundary* was lost once already. Where a step refuses for reason (b), record the refusal and its evidence in the step's own doc, so the absence is legible as a decision rather than an omission. Consumed by [phase-6-finalize/standards/verdict-currency.md](../../phase-6-finalize/standards/verdict-currency.md) at the dispatcher's re-entry check, at the same **per-step** granularity as `head_dependent`. |
| `advances_main_via_rebase` | bool | Conditional | `true` means a successful non-noop run of the step replays the worktree's history onto a newly-fetched base tip, advancing it. This is the fact that arms the dispatcher's **post-rebase step-doc re-resolution contract** (see [phase-6-finalize/SKILL.md](../../phase-6-finalize/SKILL.md) § "Post-rebase step-doc re-resolution contract"): every subsequent step's authoritative doc is re-read from the just-rebased worktree at dispatch time rather than trusting the session-start-loaded copy. Declaring this field is **mandatory** for any step that performs a rebase or merge capable of advancing the worktree's history, and optional (defaulting to `false`) otherwise. |
| `records_facts` | list[str] | Conditional | The structured fact keys the step's terminal `mark-step-done` call sites persist **between them** via `--fact KEY=VALUE` — a step-level declaration over a multi-branch step, NOT a per-branch mandate (see [Structured step facts](#structured-step-facts-records_facts) for the reconciliation rule that fixes its exact per-branch force). The governing discriminator, applied verbatim so classification is reproducible: **"what question would a retrospective or audit ask about this step that its prose summary cannot answer?"** Every declared key MUST be justified by such a consumer question, so the obligation set is derived per step rather than imposed as a uniform template. Declaring this field is **mandatory** for a step that has at least one such consumer question — including, unconditionally, any step matching the `work_performed` trigger below — and the field stays **absent** for a step whose action is fully described by its `outcome` (absence means "no obligation", not "obligation not yet written"). |
| `post_run_review` | bool | Conditional | `true` means the step looks back over the finished run and reports on it. The governing discriminator is **two predicates, both of which must hold**, applied verbatim so classification is reproducible without re-deriving it: **P1 — backward-looking output.** The step's output is a *record, assessment, or derived artifact about the just-finished run*. A step that performs or gates part of the run (a rebase, a lint gate, a push, a merge, a corpus edit, an archival move) fails P1 even when it reads the run's history as input. **P2 — post-merge evidence dependency.** At least one input the step reads is only determined **at or after** the merge gate `default:branch-cleanup` — the merge outcome, the post-merge base-branch state, the branch-cleanup re-review barrier's bot comments, or the triage dispositions that barrier produces. `post_run_review := P1 ∧ P2`. **Mutual exclusion with `mutates_source` is a consequence of P2, not a separate axiom:** a step that reads post-merge-determined evidence necessarily runs once the feature branch is already gone, so it cannot produce a pushable source edit — therefore no step may declare both `post_run_review: true` and `mutates_source: true`. This exclusion is **not a dead-end** for a step that genuinely needs both: the *need* is representable by a **split** — a post-merge classify pass (`post_run_review: true`, `mutates_source: false`) that records its verdict durably, and a settle-band apply pass (`mutates_source: true`) that reads that verdict and makes the pushable edit — see [phase-6-finalize/standards/source-edit-pushability.md](../../phase-6-finalize/standards/source-edit-pushability.md) § "The both-sides need is representable — by a split". Given that exclusion, such a step MUST be ordered **after** the dynamically-resolved merge gate (`default:branch-cleanup`), and MUST declare `mutates_source: false` **explicitly** rather than relying on absence — an omitted declaration at or after the merge gate is the `mutates_source_declaration_missing` finding, whose rule is owned by the `mutates-source-step-post-merge-order` plugin-doctor analyzer — enforced at quality-gate time, not by the manifest composer — and is not restated here. A step that derives an architecture hint but is ordered post-merge routes it through the discover-after-merge follow-up-artifact path in [phase-6-finalize/standards/source-edit-pushability.md](../../phase-6-finalize/standards/source-edit-pushability.md). Declaring this field is **mandatory** for any step satisfying `P1 ∧ P2`, and optional (defaulting to `false`) otherwise. |
| `requires_prompt_fields` | list[str] | Conditional | The **step-specific** prompt-body fields — beyond the exempt set (the generic dispatch contract `name`, `plan_id`, `skills[]`, one of `workflow`/`instructions`, `WORKTREE`; the 6th-field extension `caller_phase`; and the dispatcher-supplied runtime inputs `iteration`, `producer`, `session_id`) — that the step needs and the dispatcher MUST forward. Carriage is either the step's own dispatch `prompt:` block or the generic template's declared-field slot; both are supported. These are the workflow-specific runtime inputs the step body reads as `{placeholder}` tokens (e.g. `default:pre-submission-self-review`'s `candidates`). The governing discriminator, applied verbatim so classification is reproducible: **"would the dispatch send a silently-wrong prompt body if this field were dropped?"** Declaring this field is **mandatory** for a step whose dispatch body carries any field beyond the generic contract, and the field stays **absent** for a step dispatched through the generic template with no step-specific field (absence means "generic dispatch", not "obligation not yet written"). The declaration is enforced against THREE surfaces — the step's own dispatch body in both directions where it has one, and its input table for every step — see [Step-specific prompt-body fields](#step-specific-prompt-body-fields-requires_prompt_fields). |
| `reads` | list[str] | Optional | Named run artifacts the step consumes as input (shared vocabulary, e.g. `metrics`, `worktree`, `plan-directory`). A step declaring `reads: [X]` is only correctly ordered **after** the step that produces `X`, and mis-ordered if it runs after a step that `destroys: [X]`. The declared fact lets the ordering key express a data dependency a bare `order` cannot. See [finalize-step-order-bands.md](finalize-step-order-bands.md) § "`reads` and `destroys`". Absence means "no declared read dependency". |
| `destroys` | list[str] | Optional | Named run artifacts the step renders unavailable to every later step (same vocabulary as `reads`). `default:branch-cleanup` declares `destroys: [worktree]`; `default:archive-plan` declares `destroys: [plan-directory]`. A step that `reads` an artifact another step `destroys` must be ordered before the destroyer. See [finalize-step-order-bands.md](finalize-step-order-bands.md) § "`reads` and `destroys`". Absence means "destroys no shared artifact". |

**Consuming `head_dependent` — per-step call sites vs whole-set call sites.** The fact is declared per step, and a consumer MUST consume it at the granularity its question actually has:

| Call site | Granularity | Contract |
|-----------|-------------|----------|
| The dispatcher's re-entry check ([phase-6-finalize/SKILL.md](../../phase-6-finalize/SKILL.md) § "Step 3: Execute Step Pipeline") | **per-step** | Resolves the `head_dependent` fact for the ONE step it is about to re-enter — a membership test, never a set materialisation. This keeps the derivation exactly as lazy as the hand-maintained literal it replaced. |
| The derivation test guard | **whole-set** | Materialises the full head-dependent set through `find_implementors()` and asserts over it. Eagerness is the point here: the guard exists to enumerate every implementor, so a step added later is covered automatically. |

A per-step call site that materialises the whole set on every loop iteration is a defect, not an implementation detail — it widens a lazy contract into an eager one for no gain.

#### The fail-closed anchor obligation

**A `head_dependent: true` implementor MUST supply `--head-at-completion {sha}` on every terminal `done` record, and its absence is REFUSED rather than tolerated.** `manage-status mark-step-done` derives the declaring step's `head_dependent` fact through this ext-point's own discovery path and, on `--outcome done` with no `--head-at-completion`, returns `status: error, error: missing_head_at_completion` and **writes nothing**. There is no `--force` override for this branch: `--force` governs outcome conflicts, not the record's own well-formedness.

The refusal exists because the SHA carries two independent loads, and a missing anchor breaks both silently:

1. **Staleness detection.** The dispatcher's re-entry check compares the live HEAD against the recorded SHA. With no SHA there is nothing to compare, so a `done` record stands as green for a diff no check ever ran against — the exact defect `head_dependent` was introduced to close. A declaration without a persisted anchor buys nothing.
2. **Delta anchoring.** A step that re-fires across loop-back rounds scopes each round against the previous round's recorded SHA (`default:pre-submission-self-review` passes it to its surfacer as `--since-ref`). An unanchored record leaves the following round unable to define its delta, so it silently degrades to a full re-sweep — a correctness-preserving but cost-inflating failure that no signal would otherwise report.

Because a refusal is only as good as the derivation behind it, the failure mode is asymmetric by design: when the frontmatter derivation cannot resolve AT ALL (the discovery machinery is unavailable, or it discovers no implementors), the record IS written and carries a `warning` field naming the unresolved derivation. An unresolvable derivation must not manufacture an unsubstantiated refusal — but it must not pass silently either, so the diagnosable-WARNING idiom applies rather than a fail-open silence. A step simply absent from the finalize-step population is a RESOLVED answer (not head-dependent), not an unresolved derivation, and raises no warning — `mark-step-done` records steps for every phase, and a phase-5 step legitimately matches no finalize-step implementor.

Implementors that record a **non-`done`** outcome MAY also forward the anchor even where the dispatcher does not need it for its own retry decision — `default:pre-submission-self-review` forwards it on its `failed` branch precisely because the NEXT round reads that record as its delta anchor. (`failed` is a terminal outcome, as `assert-step-recorded --require-terminal` treats it; "non-`done`" here names the outcome value, not the record's terminality.) Forwarding on a non-`done` outcome is permitted and unrefused; the obligation above binds `done` alone.

**`post_run_review` is consumed at the same two granularities**, under the table above rather than a second contract of its own. The dispatcher's effort-role resolution reads the ONE step it is about to dispatch to decide whether that step resolves under the `post-run-review` sub-key — a per-step membership test, never a whole-set materialisation. The derivation guard materialises the full `post_run_review` set through `find_implementors()` and asserts the ordering and mutual-exclusion invariants over it. Deriving the role key from the declared fact is what keeps the ordering obligation and the dispatch sub-key on one source instead of two hand-maintained step lists.

### Structured step facts (`records_facts`)

A step record persists its outcome as `outcome` plus a free-text `display_detail`. Prose is not queryable: a retrospective cannot ask "did this rebase replay anything?" of a sentence. `records_facts` names the structured keys a step persists through `mark-step-done --fact KEY=VALUE` so `display_detail` becomes a **rendering** of recorded facts rather than their sole record.

#### Declaration is step-level, obligation is per-branch-conditional

The two levels are genuinely different, and conflating them is what makes a naive reading of this field unimplementable. Frontmatter is step-level — there is exactly one block per step doc — but a step doc has multiple terminal `mark-step-done` call sites with deliberately different honest fact sets (`branch-cleanup.md` has eight terminal branches — A through E, plus F1/F2/F3 for the three observations its queue landing gate distinguishes — of which seven record `--outcome done` and F1 records `--outcome loop_back`, terminal for its dispatch and carrying facts like the rest; three further `loop_back` sites in the pre-merge barrier record none; `sonar-roundtrip.md` has three `--outcome done` branches plus an `--outcome failed` call). The delta rule between the levels is set-valued, in both directions:

- **Declaration = UNION.** `records_facts` declares the union over the step's terminal call sites of the fact keys the step *can* record. A declared key is NOT a per-branch mandate — declaring `action` for `branch-cleanup` does not oblige a branch that performed no rebase to invent one.
- **Each branch records the honest SUBSET.** A terminal call site MUST record key `K` when that path actually performed the action or computation that produces `K`, and MUST NOT record `K` when it did not. Absence of a key on a branch is itself the honest signal that the branch has no value for it.
- **No orphan declaration (∃-direction).** Every declared key MUST be recorded by at least one terminal call site in that doc. This is what catches a declared-but-unwired obligation.
- **No undeclared record (∀-direction).** Every `--fact {key}=` wired at any terminal call site MUST appear in that doc's `records_facts` declaration. This is what catches wiring that drifts past the contract.

These two quantified directions are the ONLY declaration-vs-wiring detector scope. A conformance test asserts these two and no third scope.

#### `work_performed` — one named cross-cutting fact

`work_performed` (boolean) is **exactly one fact with a fixed key**, deliberately NOT a per-step template: every other fact key stays per-step-derived from its own consumer question, and a step with a single `done` path does not declare this one either.

- **Conditional trigger.** A step MUST declare `work_performed` when at least one of its `--outcome done` branches is reachable **without the step having performed its characteristic work**.
- **Consumer question.** *"Did this step actually do its job, or did it record `done` having done nothing?"* — the question `outcome` alone cannot answer, because a `done` that scanned and found nothing and a `done` that never scanned are the same record.
- **The one deliberate exception to the honest-subset rule.** For a step that declares it, EVERY `--outcome done` call site records `work_performed` — `true` or `false`, never omitted. The exception is load-bearing rather than cosmetic: for every other key, absence on a branch honestly means "this branch has no such value", but `work_performed` is *precisely* the fact whose absence would be ambiguous between "the branch did no work" and "the wiring forgot the fact" — which is the ambiguity the fact exists to remove.
- **Exception scope.** The `∀ done-branches` obligation is scoped to `--outcome done` call sites only. An `--outcome failed` record is already unambiguous about non-completion via its outcome, so recording `work_performed` there is permitted (and instructed where honest) but not obligatory.

#### Two-source answer contract for "did this step run?"

The question decomposes into two halves with two different sources, and **neither source answers both**:

| Half of the question | Authoritative source |
|----------------------|----------------------|
| *Was the step selected at all?* | `manifest.phase_6.steps`, persisted per-plan in `execution.toon`. A step absent from that list was never entered, and no step record exists to carry any fact. |
| *Did the step that ran perform its work?* | `work_performed` on the step record. |

The dispatcher's log marker (`[STEP] ... Executing step:`) is a source for **neither** half. Its absence is ambiguous across three distinct states — a never-selected step, a re-entry SKIP that deliberately emits no line, and a step that ran — so it can neither confirm nor refute either half. A consumer MUST NOT read marker absence as evidence that a step did not run.

#### Declared obligations

Each row is the step-level **union** per the reconciliation rule above — NOT a per-branch mandate. The **Provenance** column keeps the two Watch-entry-named steps distinguishable from the operator-added third, so a coverage assertion tests against the real Watch-entry anchor rather than against whatever the obligation set happens to contain.

| Step | Provenance | Union of fact keys | Per-call-site carriers | Consumer question earning each key |
|------|-----------|--------------------|------------------------|------------------------------------|
| `default:finalize-step-sync-baseline` | Watch-entry anchor | `action`, `upstream_commit_count`, `work_performed` | `action` / `upstream_commit_count` are carried by the branch that actually rebased. The Skipped branch performs no rebase and records `work_performed=false` alone. | `action` — *"did this rebase replay anything, or was it a no-op?"* `upstream_commit_count` — *"how far behind was the branch?"* |
| `default:branch-cleanup` | Watch-entry anchor | `action`, `upstream_commit_count`, `merge_mechanism`, `merge_state`, `work_performed` | `action` / `upstream_commit_count` are carried only by a terminal call site whose path actually reached "Rebase Branch onto Base" and parsed its `worktree-rebase-to` TOON. `merge_mechanism` only by a path that actually merged. | The same rebase pair as above, plus `merge_mechanism` — *"which merge mechanism landed this plan?"* (`pr safe-merge` vs the `use_merge_queue` enqueue), unanswerable from prose once `use_merge_queue` made it a two-way branch. `merge_state` — *"what state is the PR in, as this step recorded it?"* Distinct from `merge_mechanism`, which records HOW a merge landed and is absent wherever none did: every branch determines a merge state, across five values (`merged` on the two that landed one; `open` where a live PR is left unmerged; `closed` where the queue dequeued it without merging; `unknown` where the PR state could not be read, asserting only that nothing was observed; `n/a` where no PR exists), so it is recorded at all eight terminal call sites — the seven `--outcome done` sites plus F1's `--outcome loop_back`, which is terminal for its dispatch and carries facts like the rest. The authoritative enumeration is the step document's own § "Structured facts recorded here"; this row summarises it and must not drift from it. Its consumer is `default:emit-landing`'s required `merge_state` landing key. |
| `default:sonar-roundtrip` | operator-added — NOT a Watch-entry member | `count_status`, `new_code_issue_count`, `issues_fetched`, `work_performed` | The three scan facts are carried only by the call sites that actually scanned. The no-scan branch records `work_performed=false` alone. | `count_status` — *"was the count confirmed or undecidable?"* `new_code_issue_count` — *"how many new-code issues did the confirmed scan find?"* `issues_fetched` — *"how many findings did this producer actually hand to the unified triage?"*, the question that distinguishes a confirmed non-zero count from the findings that reached the triage store, and whose disagreement with `new_code_issue_count` is itself a producer defect. |
| `default:record-metrics` | operator-added (plan 302) — NOT a Watch-entry member | `total_tokens`, `total_wall_seconds`, `any_phase_missing_end_time` | All three carried at the single `--outcome done` call site (this step has one terminal branch). | `total_tokens` — *"what did this run cost?"* (the token-total-disagreement finding the terminal landing must make drainable); `total_wall_seconds` — *"how long did it take?"*; `any_phase_missing_end_time` — *"is the token total a floor because a phase boundary was dropped?"*. |
| `default:create-pr` | operator-added (plan 510) — NOT a Watch-entry member | `pr_number` | Both `--outcome done` branches record it — the new-PR branch and the existing-PR-reused branch. There is no `skipped` branch. | `pr_number` — *"which PR did this run open or reuse?"* The consumer is `default:emit-landing`'s required `pr` landing key, which otherwise has to re-parse the number out of a `display_detail` string the two branches word differently. |
| `default:emit-landing` | operator-added (plan 510) — NOT a Watch-entry member | `work_performed` | The Step 4 success path records `work_performed=true`; the Error Handling branch that marks `done` after a failed `orchestrator inbox write` records `work_performed=false`. Both `--outcome done` call sites carry it, per the `work_performed` exception. | `work_performed` — *"did this run actually emit a landing?"* The step has an `--outcome done` branch reachable without having emitted one (the inbox write errored and the step marked `done` anyway, because a failed landing write never blocks finalize), so `outcome` alone cannot distinguish a landing that reached the epic from one that did not. |

The three scan facts on `default:sonar-roundtrip` are already computed from the `sonar-scan-summary.jsonl` marker and already declared in that step's `## Output` TOON — they are discarded at the record boundary today, which is what wiring them fixes. The three `default:record-metrics` facts are the same shape: `generate` already computes `total_tokens` / `total_wall_seconds` / `any_phase_missing_end_time` for the step's output contract, and wiring them as `--fact` is what lets the terminal `default:emit-landing` step carry the run's cost into the epic landing as machine-readable data rather than a re-parsed prose row.

### Step-specific prompt-body fields (`requires_prompt_fields`)

The generic dispatch contract carries five prompt-body fields — `name`, `plan_id`, `skills[]`, exactly one of `workflow`/`instructions`, and `WORKTREE`. Its authoritative statement is the dispatcher agent's prompt-body table (see [`../../../agents/execution-context.md`](../../../agents/execution-context.md) § "Input — Prompt-Body Contract", whose catch-all `*` row carries the workflow-specific runtime inputs), and the ext-point contract [`ext-point-execution-context-workflow.md`](ext-point-execution-context-workflow.md) § "Input Contract — what the implementor can rely on" states the same rule in prose: *workflow-specific runtime inputs … flow through additional prompt-body fields the implementor declares in its own input table*. A finalize step that needs MORE than the five declares each extra field here and states it in its own input table.

**The generic dispatch template DOES carry a declared field.** Its `<plus every step-specific field the step declares in requires_prompt_fields>` slot exists for exactly that, and the paragraph beside it instructs the dispatcher to forward every declared field (see [`../../phase-6-finalize/SKILL.md`](../../phase-6-finalize/SKILL.md) § "Interface Contract for External Steps"). So a step declaring a step-specific field does **not** thereby need a dispatch body of its own: a step that keeps one carries its extras there, and a step dispatched through the generic template lets the template carry them. Both are supported, and the declaration is what makes either work.

#### The producerless-contract gap this closes

The declaration (a field the step's input table marks Required) and the carriage (that field in the step's dispatch body) are two edits in two places, and **nothing at runtime fails when they disagree**: a step could declare a Required field its dispatch body never sends, or send a field it never declared, and the dispatcher would forward a silently-wrong prompt body. This is the same producer-without-consumer shape `records_facts` closes for `--fact` wiring, applied to the prompt body.

`requires_prompt_fields` closes it with a conformance guard over **three** scopes — two over a step's own dispatch body, and one over the input table this document names as the declaration site:

- **No orphan declaration (∃-direction, conditional).** For a step that HAS its own dispatch `prompt:` block, every field in `requires_prompt_fields` MUST appear in that block: a step keeping its own body is responsible for carrying what it declares there. The direction is **conditional** because a step dispatched through the generic template has no own block for the field to appear in, and the template carries the declared field regardless — an unconditional form would reject the template's extension slot.
- **No undeclared field (∀-direction).** Every field a step's dispatch `prompt:` body carries beyond the exempt set MUST appear in `requires_prompt_fields`. This catches carriage that has drifted past the declaration. It shares the ∃-direction's reach: a step with no own block carries nothing here, so this direction says nothing about such a step.
- **Input-table agreement.** For **every** discovered step, the non-exempt keys its prompt-body-field input table marks `Required` MUST equal its `requires_prompt_fields`. This is the only direction that reaches a generic-template-dispatched step, and most implementors are dispatched that way — so it is where the contract is actually held, not a supplement to the other two.

`test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py` asserts all three scopes, deriving the step population from `find_implementors()` and each obligation from the step's own frontmatter — so a step that declares `requires_prompt_fields` later is covered with no edit to the test. It also **asserts how far each scope reaches**, because the first two quantify over a small minority of the implementor set and a bare "∀ over every step" would otherwise read as whole-population coverage.

##### Identifying the input table — the header convention is normative

The Input-table-agreement direction quantifies over "the step's prompt-body-field input table", so the direction is only as well-defined as the rule that picks that one table out of a step doc that may carry several. That rule is a **literal first-header-cell match**, and it is stated here as a requirement rather than left to the guard to imply:

> A markdown table in a step doc is that step's **prompt-body-field input table** if and only if its **first header cell**, stripped of markdown emphasis and lowercased, is `prompt-body field`.

**What "stripped of markdown emphasis" means, exactly.** Emphasis is a **matched pair of delimiters wrapping the whole cell**, and markdown spells that pair with either character: `*Prompt-body field*`, `_Prompt-body field_`, `**Prompt-body field**`, and `__Prompt-body field__` are all the same header cell and all match. Both characters count — a rule that honoured only one would let a table whose header is emphasised the other way satisfy this prose while going unselected, which is the silence described below wearing a conformant header. Only a matched pair is stripped: an unpaired delimiter is part of the cell text, so a header cell reading `_prompt-body field` (one leading underscore, no closing one) is a different string and does **not** match.

A step doc **MUST** title its input table's first column `Prompt-body field` for its declaration to be enforced. The consequence of not doing so is silence, not failure: a step whose input table is headed anything else is not matched by the Input-table-agreement direction at all, its `Required` rows bind nothing, and the step passes the conformance guard while declaring whatever it likes. Because that direction is the only one reaching a generic-template-dispatched step — and most implementors are dispatched that way — an unmatched header removes the step from the only scope that actually holds it.

**Why the discriminator is the header and not the `Required` column.** The obvious-looking alternative — "any table with a `Required` column is the input table" — is wrong, and wrong in the expensive direction. A step doc's **CLI parameter table** carries a `Required` column too, for exactly the same honest reason: some flags are required and some are not. Folding those tables into the scope would make the guard read every documented command-line flag as an undeclared prompt-body field and demand it appear in `requires_prompt_fields`, flagging conformant steps en masse. The `Required` column is a property shared by several kinds of table in these docs; the first header cell is what names which kind a table is. That is why the header carries the discrimination.

**The exempt set — the field names a step never has to declare.** It has three parts, and it is ONE set with ONE definition (`_EXEMPT_FIELDS` in the guard module); a second, competing list is what let this contract and the workflow contract disagree about `caller_phase`:

| Part | Names | Why exempt |
|------|-------|------------|
| The generic dispatch contract | `name`, `plan_id`, `skills`, `workflow`, `instructions`, `WORKTREE` | Every dispatch carries them. The contract requires **exactly one** of `workflow`/`instructions`, so a step carrying `instructions` in place of `workflow` (e.g. `default:finalize-step-simplify`) is dispatching generically and declares nothing for it. |
| The 6th-field extension | `caller_phase` | [`ext-point-execution-context-workflow.md`](ext-point-execution-context-workflow.md) already declares it the optional **6th-field extension** of the canonical 5-field contract. Treating it as step-specific would contradict a contract that names it generic. |
| Dispatcher-supplied runtime inputs | `iteration`, `producer`, `session_id` | The dispatcher fills these from its own run state **at the dispatch site** — the loop iteration, the producer that raised the round, the session under analysis. A step never carries a dispatcher-inserted field in its own body, so a declaration naming one could not satisfy the ∃-direction, which looks for the field exactly there. |

A prompt-body field outside that set — carried in a step's own block, or marked `Required` in its input table — is a step-specific field the step MUST declare.

### Addressing Surface

A finalize-step declaration is discovered from exactly these locations:

| Location | Step kind | Resolver precedence |
|----------|-----------|---------------------|
| `phase-6-finalize/workflow/*.md` | Built-in (`default:{bare}`) | Wins on name collision with a `standards/` doc of the same bare name. |
| `phase-6-finalize/standards/*.md` | Built-in (`default:{bare}`) | Yields to a `workflow/` doc of the same bare name. |
| Opt-in bundle `skills/*/SKILL.md` | Bundle-optional (`{bundle}:{skill}`) | n/a — full bundle:skill name is unique. |
| Project-local `.claude/skills/finalize-step-*/SKILL.md` | Project (`project:finalize-step-{bare}`) | n/a — project namespace is unique. |

The `workflow/` ⇒ `standards/` precedence rule mirrors `configurable_contract.resolve_step_doc_path`: when a built-in step has both a `workflow/{name}.md` and a `standards/{name}.md`, the `workflow/` doc is the canonical body and carries the frontmatter declaration. (In practice each built-in step has exactly one of the two; `push`, for example, lives only at `standards/push.md` with `name: default:push`, so no precedence conflict arises.)

### Excluded Supporting Docs

Not every `.md` file under `phase-6-finalize/{workflow,standards}/` is a finalize step. Supporting docs — shared templates, validation rules, and cross-cutting references consumed by the step bodies — MUST NOT declare this interface. The known supporting docs that are explicitly excluded:

| Doc | Role |
|-----|------|
| `output-template.md` | Shared finalize-summary output template. |
| `validation.md` | Cross-step validation rules. |
| `required-steps.md` | Documents which steps are mandatory; not itself a step. |
| `disposition-to-hint-routing.md` | Disposition → architecture-hint routing reference. |
| `lessons-integration.md` | Lessons-capture integration reference. |
| `adr-integration.md` | ADR-proposal integration reference. |

A supporting doc that erroneously declared `implements: ...ext-point-finalize-step` would be wrongly seeded as a runnable step. The exclusion is enforced by NOT adding the declaration to these docs; the discovery query only surfaces docs that opt in via frontmatter.

## Hook API

A finalize step is not a Python hook method on `ExtensionBase` — it IS a frontmatter declaration on a step body doc. Discovery flows through the reusable `extension_discovery.find_implementors()` query:

```python
def find_implementors(ext_point: str) -> list[dict]:
    """Enumerate every component that declares implements: {ext_point}.

    For ext-point-finalize-step, scans:
      - every bundle's skills/*/SKILL.md (opt-in bundle steps)
      - phase-6-finalize/workflow/*.md + standards/*.md (built-in steps,
        workflow/ winning on name collision)
      - project-local .claude/skills/finalize-step-*/SKILL.md (project steps)

    Each implementor record carries:
      {name, order, default_on, presets, canonicals, description,
       source, path}

    where source is one of: built-in, bundle-optional, project.

    The record is deliberately NOT the whole frontmatter — it carries the
    fields the seeding/preset consumers need, not every declared key. The
    conditional obligation fields — every field the table above marks
    Conditional — are NOT on this record; a consumer that needs one reads
    it from the step doc's frontmatter directly (see
    extension_discovery._read_frontmatter_fields).

    Resolves both the source structure
    (marketplace/bundles/{bundle}/skills/...) and the versioned cache
    structure (cache/.../{version}/skills/...) via the cache-aware
    configurable_contract doc-root primitives, so consumer projects with
    no marketplace/ source tree resolve through the installed plugin cache.
    """
```

The query reuses the cache-aware doc-root primitives from `configurable_contract.py` (`resolve_step_doc_path`, `_phase_6_skill_dir`, `_extract_frontmatter_lines`, `_coerce_scalar`) for the phase-6 doc surface, and the existing bundles-root + cache-root resolution from `extension_discovery.py` for the `skills/*/SKILL.md` surface. It is the canonical enumeration that `_seed_finalize_steps()`, `_discover_all_finalize_steps()`, and the `FinalizeStepPresets` builder consume; there is no parallel glob.

## Resolution

Finalize-step discovery is exposed both as a library function and as a CLI verb. The CLI verb emits the implementor records as TOON:

```bash
# Enumerate every component implementing the finalize-step interface
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery \
  implementors --ext-point plan-marshall:extension-api/standards/ext-point-finalize-step
```

The finalize-step registry surfaces the resolved universe through the existing `manage-config` CLI, which consumes the discovery query internally:

```bash
# List every discovered finalize step with name / description / source / order
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
```

There is **no parallel glob and no second discovery structure**. The `find_implementors(...)` query is the sole discovery path; the seed (default-on filter), the discovery surface, and the preset builder all read its records.

## Current Implementations

Every step doc that declares the finalize-step interface. Built-in steps live under `phase-6-finalize/{workflow,standards}/`; bundle steps ship under their bundle's `skills/`; project steps are meta-project-local under `.claude/skills/`. Rows are listed in the discovery order `manage-config list-finalize-steps` emits (ascending `order`, then `name`), so the table diffs against that output row for row.

| Name | Source | Order | default_on | presets |
|------|--------|-------|:----------:|---------|
| `default:finalize-step-sync-baseline` | built-in | 3 | true | `[full]` |
| `project:finalize-step-lessons-housekeeping` | project | 4 | false | `[]` |
| `default:pre-push-quality-gate` | built-in | 5 | true | `[full]` |
| `project:finalize-step-plugin-doctor` | project | 6 | false | `[]` |
| `default:pre-submission-self-review` | built-in | 7 | true | `[]` |
| `default:finalize-step-simplify` | built-in | 8 | true | `[full]` |
| `default:finalize-step-security-audit` | built-in | 9 | true | `[]` |
| `default:architecture-refresh` | built-in | 10 | true | `[]` |
| `default:push` | built-in | 11 | true | `[local, standard, full]` |
| `default:create-pr` | built-in | 20 | true | `[standard, full]` |
| `project:finalize-step-era-stamp-fill` | project | 21 | false | `[]` |
| `default:ci-verify` | built-in | 22 | true | `[standard, full]` |
| `plan-marshall:automatic-review` | bundle | 30 | true | `[standard, full]` |
| `default:sonar-roundtrip` | built-in | 40 | true | `[full]` |
| `default:adr-propose` | built-in | 62 | false | `[]` |
| `default:branch-cleanup` | built-in | 70 | true | `[local, standard, full]` |
| `project:finalize-step-deploy-target` | project | 81 | false | `[]` |
| `project:finalize-step-sync-plugin-cache` | project | 85 | false | `[]` |
| `project:finalize-step-review-retrospective` | project | 990 | false | `[]` |
| `default:lessons-capture` | built-in | 991 | true | `[local, standard, full]` |
| `default:finalize-step-preference-emitter` | built-in | 992 | true | `[]` |
| `plan-marshall:plan-retrospective` | bundle-optional | 995 | false | `[full]` |
| `default:record-metrics` | built-in | 998 | true | `[local, standard, full]` |
| `default:finalize-step-print-phase-breakdown` | built-in | 999 | true | `[]` |
| `default:emit-landing` | built-in | 1000 | true | `[local, standard, full]` |
| `default:archive-plan` | built-in | 1100 | true | `[local, standard, full]` |

Project steps carry `default_on: false` and `presets: []` because they are hand-registered in the meta-project's `phase-6-finalize.steps` array (presets ship to consumer projects, which do not have the meta-project's project-local finalize-step skills). The `plan-marshall:automatic-review` step is a default-on bundle step (`default_on: true`, member of the `standard` and `full` presets). The bundle-optional `plan-marshall:plan-retrospective` step is opt-in (`default_on: false`) and a member of the `full` preset only.

## Related Specifications

- [finalize-step-order-bands.md](finalize-step-order-bands.md) — The banded `order` allocation contract: bands, reserved gaps, reserved ranges, the collision rule, and the `reads` / `destroys` declared facts
- [ext-point-domain-bundle.md](ext-point-domain-bundle.md) — Domain-bundle manifest extension point (same `implements:` identification model)
- [ext-point-recipe.md](ext-point-recipe.md) — Recipe extension point (same `implements:` identification model)
- [marshal-json-reference.md](marshal-json-reference.md) — Central marshal.json path reference, including `phase-6-finalize.steps`
