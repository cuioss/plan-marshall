# Run report — 190-split-and-complete-the-user-configuration-doc (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/user-config-doc-split-d37w8m` (harness-assigned, kept)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (the working contract — loaded first).
- `plan-marshall:ref-code-quality` (read from bundle path).
- `pm-documents:ref-asciidoc` (read from bundle path — its scripts require the git-ignored `.plan/execute-script.py`, absent in this cloud clone, so link/format verification is done manually via Read/Grep per the contract).
- `pm-plugin-development:plugin-script-architecture` ("Always" per the contract; the plan touches no scripts, so its script-standards content is not exercised — recorded for completeness).

GitHub access path: **GitHub MCP server** (cloud path). Branch form: **harness-assigned `claude/*`** (kept as-is per contract; not run-created).

## Deliverables

### D1 — GATE: derive the population, settle the split (mutates nothing)

**STOP CONDITION verdict: does NOT fire — the population is derivable and bounded.**

The plan's STOP CONDITION halts if the `data-model.md` standard "is itself a sample." Finding: `data-model.md` **aspires to completeness** ("## Complete Structure", exhaustive per-section field tables) but has **drifted** — it omits two real seeded knobs (`plan.phase-1-init.auto_route_recipe`, `auto_route_recipe_threshold`) that the code seed (`DEFAULT_PLAN_INIT`, `_config_defaults.py:605,613`) carries and that `configuration.adoc` §recipe-routing already documents. It is **not** "a sample" in the STOP-CONDITION sense (a deliberate representative subset of an unknowable population); it is a completeness-aspiring reference with minor drift. The plan's own D1 instruction — "derive the knob population from `data-model.md`, **cross-checked against the code-side defaults**" — is exactly the cross-check that patches this drift.

**The authoritative, complete population source is the code:** `get_default_config()` (`_config_defaults.py:1272`) returns the complete seeded default config, is self-validated at seed time, and is guarded by structural seed-completeness tests (see the `ORCHESTRATOR_KNOWN_KEYS` rationale). Non-seeded settable knobs (`build.map` entries, `skill_domains` inclusion keys, per-element `lane` overrides, non-seeded step params) are enumerable from `data-model.md` + the standards it points to. The population is therefore knowable and bounded; coverage is derived against it, not against `data-model.md` alone → the STOP CONDITION's harm (a false completeness claim against a partial population) does not obtain.

`data-model.md` is **read-only** per the plan's Expected surface, so its drift (missing `auto_route_recipe`/`auto_route_recipe_threshold`) is a **reported finding**, not fixed here (see Findings).

**Population coverage diff (a LIST, not a count).** Derived from `get_default_config()` + non-seeded documented knobs, diffed line-by-line against `configuration.adoc` and its cross-referenced siblings. Absences confirmed by targeted grep (asserted absences are the higher-risk half).

*Covered on the page (representative — not exhaustive):* `project.{default_base_branch, working_prefixes, pr_strategy, pr_compact_max_changed_files}` (§project-branch-naming); `orchestrator.{parallelization_scope, effort}` (§orchestrator-knobs); the four review gates + `finalize_without_asking`/`loop_back_without_asking` (§review-gates); `deep_lane`/`escalation`/`revalidation` + finalize run-at-all gates (§run-at-all-gates); `q_gate_validation` (§q-gate-validation); `auto_route_recipe`/`auto_route_recipe_threshold` (§recipe-routing); `lane_selection`/`lane_prune_thresholds`/per-element `lane` (§execution-profile-lane-selection); `commit_and_push`/`per_deliverable_build` (§commit-and-build-depth); `cost_size_token_table`/`per_envelope_budget_tokens` (§per-envelope-packing-budget); the `default:branch-cleanup` merge params + `use_merge_queue` (§merge-strategy/§merge-queue); `review_bot_buffer_seconds` + the re-review params (§automated-review); `preference_min_recurrence` (§preference-learning); `open_in_ide` (§open-in-ide); `finding_raw_input_max_bytes` (§Findings quarantine cap); `checks_wait_timeout_seconds`/`ce_wait_timeout_seconds` + 4 retention knobs (§retention-and-ci); `skill_domains.*` incl. `always_on`/`file_globs` (§skill-domains); `build.map` (§build-map); `branch_strategy`/`use_worktree` (§worktrees); effort (§effort-and-models → efforts.adoc).

*Covered by a SIBLING page (cross-ref present or to be added):* `build.queue.{max_slots, max_retries, upper_limit_seconds}` — documented in `parallelism-and-locking.adoc` §Knobs; **configuration.adoc did NOT cross-reference it** → D4 adds the pointer.

*UNCOVERED — not documented anywhere on the page (confirmed by grep):*
- `plan.phase-2-refine.confidence_threshold`
- `plan.phase-2-refine.compatibility`
- `plan.phase-2-refine.simplicity`
- `plan.phase-5-execute.max_iterations`
- `plan.phase-6-finalize.max_iterations`
- `plan.coverage.thoroughness`
- `plan.coverage.scope`
- `project.merge_queue_managed_externally`
- `system.retention.no_plan_body_days`
- `system.retention.build_results_days`
- `system.retention.plugin_cache_keep_versions`
- `system.retention.plugin_cache_keep_days`
- `steps['plan-marshall:automatic-review'].required_bots`
- `steps['plan-marshall:automatic-review'].optional_bots`
- `steps['plan-marshall:automatic-review'].bot_lists_provenance`
- `steps['default:sonar-roundtrip'].touched_file_cleanup`
- `steps['default:sonar-roundtrip'].do_transition`
- `build.queue.*` (cross-ref only — see above)

*MENTIONED-but-undocumented (named only in the stale line-49 parenthetical, pointed to `data-model.md`, not actually documented):* `confidence_threshold`, `compatibility`, `simplicity`, `max_iterations`, `touched_file_cleanup`, `do_transition` (⇒ subset of the UNCOVERED list above), and `orchestrator.auto_emit` (named in §orchestrator-knobs prose, full reference deferred to `data-model.md`).

*Out-of-population (registration/runtime, not tunable knobs):* `providers[]`, `credentials_config` (managed by `manage-providers`, not the config page), `system.provisioned_version`/`config_seed_fingerprint` (runtime provenance stamps, never operator-set).

**The line-49 parenthetical is confirmed STALE (the drift the epic predicts):** it lists as "everything else / undocumented" many knobs the page now DOES document (`branch_strategy`, `use_worktree`, `commit_and_push`, `per_deliverable_build`, `cost_size_token_table`, `per_envelope_budget_tokens`, the flat phase-6 auto-continuation knobs, `open_in_ide`, most `system.retention.*`, `checks_wait_timeout_seconds`, `review_bot_buffer_seconds`, `pr_merge_strategy`, `final_merge_without_asking`, `auto_rebase_threshold`, `ce_wait_timeout_seconds`, the `project.*` branch-naming knobs). A hand-maintained "everything else" list, exactly as the plan warned. **D4 replaces it with a pointer** to `data-model.md` (never a new prose list).

**Reference-link question (finding 3) — SETTLED: the `marketplace/bundles/` links are NOT broken for their audience; the meta-project work is a MOVE/eviction, not a re-pointing.**
- Distribution is plugin-only (`/plugin marketplace add cuioss/plan-marshall@dist-claude` installs the generated `target/claude/` bundle tree). The published tree "contains only the marketplace files the generator produced" (`distribution.adoc:72`) — `doc/` is not generated into it.
- There is **no rendered docs site** — `installation.adoc:110` states explicitly "no tarballs, no GitHub Pages".
- Therefore `doc/user/configuration.adoc` is **only ever read inside the `cuioss/plan-marshall` repository** (GitHub blob view or a local clone), where `marketplace/bundles/` is always present. Every `link:../../marketplace/bundles/...` resolves for its audience. Finding 3's hypothesis (a consumer lacking the tree) is **refuted**. The links stay; D5 is a content eviction into `doc/developer/`.

**Split boundaries — SETTLED.** One extraction, into the plan-named existing target page:
- **Extract §merge-strategy + §merge-queue → `parallelism-and-locking.adoc`** (the operator guide the plan's Expected surface names as an extraction target; it is explicitly "the merge-to-`main` boundary" page). Lowest cross-reference risk: **no external file references `#merge-strategy` or `#merge-queue`** (confirmed by repo-wide grep) — those anchors are referenced only internally from §automated-review. Pointer stubs are left at the origin preserving both anchors, in the demonstrated §effort-and-models style.
- Load-bearing external anchors that MUST be preserved (referenced from `doc/concepts/`, `doc/user/`): `#recipe-routing`, `#per-envelope-packing-budget`, `#build-systems`, `#review-gates`, `#worktrees`, `#micro-lane-fast-path` — none is extracted.
- More aggressive atomisation was considered and **deferred**: additional extractions multiply inbound-cross-reference risk for little gain, and the plan's own framing puts the value in D1/D4/D5, not in shrinking line-count. `efforts.adoc` and `terminal-title.adoc` (the other named targets) are already extracted; `parallelism-and-locking.adoc` is this run's.

**`lane` vocabulary — CONFIRMED (D2 blocker settled).** See D2.

### D2 — Document the `lane` configuration

Independent code investigation (sub-agent, read-only) settled the value sets. They are **different-but-coherent**, not an accidental contradiction:

| Surface | Accepted set | Source |
|---|---|---|
| Per-element override value space (reader/validator) | `off, minimal, standard, full, ask` | `VALID_LANE_OVERRIDE` `_config_defaults.py:481`; twin `LANE_OVERRIDES` `_manifest_lanes.py:20` (identical) |
| `finalize-steps set-lane` verb (operator writer) | `off, standard, full` | `_RESOLVED_ASK_LANE_VALUES` `_cmd_finalize_steps.py:68`; argparse `choices` `manage-config.py:710`; runtime guard `:314` |
| Tier lattice (postures) | `minimal, standard, full` | `LANE_TIERS` `_manifest_lanes.py:19`; `off`/`ask` are dispositions, not tiers (`ext-point-lane-element.md`) |

The narrow `off/standard/full` is the **deliberate, documented** writer subset — the answers the ask-resolution dialogue produces (`No`/`Yes`/`Yes-always`); `minimal`/`ask` are seed/frontmatter values, not `set-lane` writes (documented as intentional in `_cmd_finalize_steps.py:298-305`, `api-reference.md:321`, and the `--lane` help text). The `off/minimal/standard` occurrences are descriptive of the ceremony-gate mapping (`off→never`, `minimal→always`, `standard/absent→auto`), not a validation constant.

**Decision:** the set IS settleable, so D2 documents it accurately (Option A), NOT "leave undocumented". `configuration.adoc` line 247 already correctly states the override value space `off|minimal|standard|full|ask`; D2 adds a clarifying note that `set-lane` writes only `off|standard|full` (with the reason) and disambiguates the two unrelated "lane" concepts (planning lane `light`/`deep` vs. the finalize-step `lane`). The residual friction — `set-lane` rejects `minimal`/`ask`, which are valid override values — is **reported as a finding** (a code-level divergence that "belongs in its own change" per Out-of-scope), not fixed here.

### D3 — Split, with pointer stubs

_See D1 split boundaries. Execution status below (Findings/commits)._

### D4 — Close the coverage gap

_Document the UNCOVERED list above; replace the line-49 parenthetical with a `data-model.md` pointer (never a prose list); add the `build.queue` sibling cross-ref._

### D5 — Evict meta-project content

Sweep (`meta-project`, `sync-plugin-cache`, `deploy-target`, `target/claude`, `derived-state`) hits in `configuration.adoc`:
- **Line 236** — "and the meta-project derived-state steps" embedded in the `minimal` posture description → the prose-embedded mention (finding 3); removed (a consumer's minimal floor has no derived-state steps).
- **Lines 252–255** — the "Meta-project derived-state caveat" NOTE → moved to `doc/developer/marketplace-build.adoc` § Plugin cache sync (meta-project only).
- **Line 294** — `project:finalize-step-deploy-target` used as a generic `project:` example → genericised (removes the meta-project-specific name from the consumer page).
- **Line 509** — "a meta-project's own domain (e.g. `plan-marshall-plugin-dev`)" → **kept**: this is a legitimate use-case illustration for the `always_on` knob (relevant to any consumer who maintains a meta-project), not meta-project-only noise. Recorded as a deliberate keep.

### D6 — Verification

_Cross-reference integrity across the split (incl. from outside `doc/user/`) + documentation lint. Status below._

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` verdict: **no Python changes** (documentation-only: `.adoc` + the report `.md`). Build skipped — the docs-only path (confirmed from git evidence, per the plan's Verification note). The merge-queue `merge_group` run verifies docs-only changes before landing.

## Findings

| # | Source | Description | Disposition |
|---|---|---|---|
| 1 | D1 cross-check | `data-model.md` (the claimed population authority) omits two real seeded knobs — `plan.phase-1-init.auto_route_recipe` and `auto_route_recipe_threshold` (`_config_defaults.py:605,613`) — that `configuration.adoc` §recipe-routing already documents. The population authority has drifted behind the code seed. | **Reported, not fixed** — `data-model.md` is read-only per the plan's Expected surface; belongs in its own change (documentation-standard fix to `data-model.md`). |
| 2 | D2 investigation | `finalize-steps set-lane` validates `--lane` against `off/standard/full` (`_cmd_finalize_steps.py:68`), rejecting `minimal` and `ask` — both valid per-element override values (`VALID_LANE_OVERRIDE`). A user who sets a per-element lane via `set-lane --lane minimal` is rejected, though `minimal` is a documented override value. Intentional/documented as a writer-subset, but a real user-facing divergence. | **Reported, not fixed** — code defect surfaced by a docs plan; belongs in its own change (per Out-of-scope). Documented accurately (disambiguated) rather than encoding a contradiction. |

_(Verification-sub-agent, CI, and PR-review findings appended as they arrive.)_

## Reviewer participation

_Pending PR._

## Cost

- **Tokens:** not separately available to the agent in this session.
- **Wall-clock:** single interactive cloud session; see run timestamps.
- **Population:** this single Claude Code cloud session's usage — NOT comparable to a plan-marshall `metrics.toon` dispatch-tree total.

## Contract check (Step 9)

_Appended at finalize._

## What have we learned (Step 9)

_Appended at finalize._

## Residue

_Appended at finalize._
