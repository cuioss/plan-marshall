# Extension Point: Finalize Step

> **Type**: Phase-6 Step Doc Extension | **Hook Method**: `implements:` frontmatter on each step doc | **Implementations**: 25 | **Status**: Active

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
| `order` | int | Yes | Integer execution order. The seed and the discovery query both sort by this value, so the on-disk `phase-6-finalize.steps` order is deterministic. |
| `default_on` | bool | Yes | `true` ⇒ the step is included in the default seed (`_seed_finalize_steps()` filters to `default_on == true`). `false` ⇒ the step is discoverable but opt-in (it is added to a project's `phase-6-finalize.steps` only by an explicit preset or hand-registration). |
| `presets` | list[str] | Yes | The named presets this step belongs to — a (possibly empty) subset of `[local, standard, full]`. The preset builder derives "step S belongs to preset P" as `P ∈ S.presets`. An empty list `[]` means the step is in no named preset. |
| `description` | str | Yes | The human-readable discovery description (shown by `list-finalize-steps` and the wizard). This is the single source of the per-step description, replacing the removed `*_DESCRIPTIONS` maps. |
| `mutates_source` | bool | Conditional | `true` means the step edits tracked source at runtime; such a step MUST be ordered before `default:branch-cleanup`, per [phase-6-finalize/standards/source-edit-pushability.md](../../phase-6-finalize/standards/source-edit-pushability.md). Declaring this field is **mandatory** for any step whose `order` is at or after the dynamically-resolved merge gate (`default:branch-cleanup`) and optional for a step ordered below it. |
| `head_dependent` | bool | Conditional | `true` means the step's verdict is computed against a specific worktree HEAD, so a recorded `done` is only valid for the SHA it was computed against. Such a step MUST persist `--head-at-completion {sha}` on its terminal `done` record — an obligation that is **enforced, not merely stated**: `manage-status mark-step-done` REFUSES a `done` record from a `head_dependent: true` step that carries no SHA (see [The fail-closed anchor obligation](#the-fail-closed-anchor-obligation) below). The dispatcher's re-entry check re-fires the step when HEAD has advanced (a loop-back commit, a force-push, or a rebase). The governing discriminator, applied verbatim so classification is reproducible: **"would this verdict change if HEAD changed?"** Declaring this field is **mandatory** for a step matching either of two shapes — (1) it records a pass/fail verdict over tracked source or over the remote state of that source, or (2) it is a settle-stage step whose edits land directly in the worktree (its edits were computed against the HEAD it read, so a HEAD advance supersedes them) — and optional (defaulting to `false`) otherwise. A step matching **neither** shape — one that records *an action performed* (rebase, push, PR created, archive written) and leaves no edits of its own — has no verdict to go stale and is not head-dependent. |
| `advances_main_via_rebase` | bool | Conditional | `true` means a successful non-noop run of the step replays the worktree's history onto a newly-fetched base tip, advancing it. This is the fact that arms the dispatcher's **post-rebase step-doc re-resolution contract** (see [phase-6-finalize/SKILL.md](../../phase-6-finalize/SKILL.md) § "Post-rebase step-doc re-resolution contract"): every subsequent step's authoritative doc is re-read from the just-rebased worktree at dispatch time rather than trusting the session-start-loaded copy. Declaring this field is **mandatory** for any step that performs a rebase or merge capable of advancing the worktree's history, and optional (defaulting to `false`) otherwise. |
| `records_facts` | list[str] | Conditional | The structured fact keys the step's terminal `mark-step-done` call sites persist **between them** via `--fact KEY=VALUE` — a step-level declaration over a multi-branch step, NOT a per-branch mandate (see [Structured step facts](#structured-step-facts-records_facts) for the reconciliation rule that fixes its exact per-branch force). The governing discriminator, applied verbatim so classification is reproducible: **"what question would a retrospective or audit ask about this step that its prose summary cannot answer?"** Every declared key MUST be justified by such a consumer question, so the obligation set is derived per step rather than imposed as a uniform template. Declaring this field is **mandatory** for a step that has at least one such consumer question — including, unconditionally, any step matching the `work_performed` trigger below — and the field stays **absent** for a step whose action is fully described by its `outcome` (absence means "no obligation", not "obligation not yet written"). |
| `post_run_review` | bool | Conditional | `true` means the step looks back over the finished run and reports on it. The governing discriminator is **two predicates, both of which must hold**, applied verbatim so classification is reproducible without re-deriving it: **P1 — backward-looking output.** The step's output is a *record, assessment, or derived artifact about the just-finished run*. A step that performs or gates part of the run (a rebase, a lint gate, a push, a merge, a corpus edit, an archival move) fails P1 even when it reads the run's history as input. **P2 — post-merge evidence dependency.** At least one input the step reads is only determined **at or after** the merge gate `default:branch-cleanup` — the merge outcome, the post-merge base-branch state, the branch-cleanup re-review barrier's bot comments, or the triage dispositions that barrier produces. `post_run_review := P1 ∧ P2`. **Mutual exclusion with `mutates_source` is a consequence of P2, not a separate axiom:** a step that reads post-merge-determined evidence necessarily runs once the feature branch is already gone, so it cannot produce a pushable source edit — therefore no step may declare both `post_run_review: true` and `mutates_source: true`. Given that exclusion, such a step MUST be ordered **after** the dynamically-resolved merge gate (`default:branch-cleanup`), and MUST declare `mutates_source: false` **explicitly** rather than relying on absence — an omitted declaration at or after the merge gate is the `mutates_source_declaration_missing` finding, whose rule is owned by the `mutates-source-step-post-merge-order` plugin-doctor analyzer — enforced at quality-gate time, not by the manifest composer — and is not restated here. A step that derives an architecture hint but is ordered post-merge routes it through the discover-after-merge follow-up-artifact path in [phase-6-finalize/standards/source-edit-pushability.md](../../phase-6-finalize/standards/source-edit-pushability.md). Declaring this field is **mandatory** for any step satisfying `P1 ∧ P2`, and optional (defaulting to `false`) otherwise. |

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

The two levels are genuinely different, and conflating them is what makes a naive reading of this field unimplementable. Frontmatter is step-level — there is exactly one block per step doc — but a step doc has multiple terminal `mark-step-done` call sites with deliberately different honest fact sets (`branch-cleanup.md` has four `--outcome done` branches plus a `loop_back` call; `sonar-roundtrip.md` has three `--outcome done` branches plus an `--outcome failed` call). The delta rule between the levels is set-valued, in both directions:

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
| `default:branch-cleanup` | Watch-entry anchor | `action`, `upstream_commit_count`, `merge_mechanism`, `work_performed` | `action` / `upstream_commit_count` are carried only by a terminal call site whose path actually reached "Rebase Branch onto Base" and parsed its `worktree-rebase-to` TOON. `merge_mechanism` only by a path that actually merged. | The same rebase pair as above, plus `merge_mechanism` — *"which merge mechanism landed this plan?"* (`pr safe-merge` vs the `use_merge_queue` enqueue), unanswerable from prose once `use_merge_queue` made it a two-way branch. |
| `default:sonar-roundtrip` | operator-added — NOT a Watch-entry member | `count_status`, `new_code_issue_count`, `issues_fetched`, `work_performed` | The three scan facts are carried only by the call sites that actually scanned. The no-scan branch records `work_performed=false` alone. | `count_status` — *"was the count confirmed or undecidable?"* `new_code_issue_count` — *"how many new-code issues did the confirmed scan find?"* `issues_fetched` — *"how many findings did this producer actually hand to the unified triage?"*, the question that distinguishes a confirmed non-zero count from the findings that reached the triage store, and whose disagreement with `new_code_issue_count` is itself a producer defect. |

The three scan facts on `default:sonar-roundtrip` are already computed from the `sonar-scan-summary.jsonl` marker and already declared in that step's `## Output` TOON — they are discarded at the record boundary today, which is what wiring them fixes.

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
| `default:architecture-refresh` | built-in | 9 | true | `[]` |
| `default:finalize-step-security-audit` | built-in | 9 | true | `[]` |
| `default:push` | built-in | 10 | true | `[local, standard, full]` |
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
| `default:archive-plan` | built-in | 1000 | true | `[local, standard, full]` |

Project steps carry `default_on: false` and `presets: []` because they are hand-registered in the meta-project's `phase-6-finalize.steps` array (presets ship to consumer projects, which do not have the meta-project's project-local finalize-step skills). The `plan-marshall:automatic-review` step is a default-on bundle step (`default_on: true`, member of the `standard` and `full` presets). The bundle-optional `plan-marshall:plan-retrospective` step is opt-in (`default_on: false`) and a member of the `full` preset only.

## Related Specifications

- [ext-point-domain-bundle.md](ext-point-domain-bundle.md) — Domain-bundle manifest extension point (same `implements:` identification model)
- [ext-point-recipe.md](ext-point-recipe.md) — Recipe extension point (same `implements:` identification model)
- [marshal-json-reference.md](marshal-json-reference.md) — Central marshal.json path reference, including `phase-6-finalize.steps`
