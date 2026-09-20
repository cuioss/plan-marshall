# Manifest Cross-Check Rules

Cross-check rules that compare the per-plan execution manifest (`execution.toon` written by `plan-marshall:manage-execution-manifest`) against the plan's realized footprint. Each rule maps one-to-one to a row in the seven-rule manifest decision matrix and emits one finding per violation.

## Sources

- **Manifest** (`execution.toon`): produced by `manage-execution-manifest compose` during phase-3-outline. Captures `phase_5.early_terminate`, `phase_5.verification_steps`, `phase_6.steps`, plus the `rule_fired` field that names which decision matrix row applied (logged in `decision.log` rather than the manifest body itself).
- **Decision log** (`decision.log`): captures the rule that fired, with the `(plan-marshall:manage-execution-manifest:compose)` caller tag — load these alongside the manifest to present the WHY behind each WHAT.
- **Realized footprint**: resolved through the **shared whole-chain resolver** (`scripts/_footprint_resolver.py`, `resolve_footprint`), which walks its declared `RESOLVING_TIERS` in order and then reports its unresolvable sentinel. That list is authoritative and is deliberately not enumerated here. An explicit `--diff-file` bypasses the chain and is caller-supplied evidence.
- **Forwarded set comparison**: the `affected_files_exact_match` block of the `artifact-consistency` fragment (`work/fragment-artifact-consistency.toon`), which that aspect downgrades and marks `forwarded_to_manifest: true` whenever a manifest exists. Rule M6 is its receiver.

⛔ **The footprint is NOT a private `git diff {base}...HEAD` taken by this script**, and the difference is why this aspect exists in its current form. It runs at finalize `order: 995`, after `default:branch-cleanup` has merged, so that range structurally spans nothing: the call succeeded, returned no path, and rule M4 reported "no implementation file changed" for plans that had shipped a real footprint. Routing through the shared chain is what gives this aspect the post-merge tiers (realized capture, merge-commit, PR-landing) its sibling footprint consumers already had.

## Footprint degradation verdict

When **no** tier of the chain resolves, the footprint is unresolvable and no rule may verdict on it. The aspect then publishes a **degradation** verdict rather than a confident empty-footprint claim:

- Every affected check takes the status `inconclusive`, naming the reason and the chain it tried.
- The aspect-level `footprint_resolution` block carries `status: inconclusive`, the reason, and `chain` (the tiers consulted).
- Rule M4 reports `inconclusive` and **never** reaches its `raw_files_total == 0` wording, which asserts that the footprint resolved to no path — precisely what did not happen.

⛔ `inconclusive` is deliberately **not** `indeterminate`, and the two must not be merged. `inconclusive` is a member of `retro_sections.FOOTPRINT_DEGRADED_TOKENS`, and `compile-report._declares_degraded` matches it by **equality against a verdict field** (`status` / `comparison`) — so emitting it is what lets the plan-level footprint-derivation aggregate count this aspect as degraded. It is also what makes `manifest-decisions` a legitimate member of `retro_sections.FOOTPRINT_CONSUMING_ASPECTS`: a producer with no degraded verdict reads as resolved on every run and would render that aggregate incapable of firing. `indeterminate` is not in that vocabulary. The two also mean different things: `indeterminate` is *the footprint resolved and the filter left too little of it*; `inconclusive` is *no footprint resolved at all*.

**The resolving tier is published beside the verdict.** `footprint_resolution.tier` names which tier of the chain supplied the footprint (or `unresolved`), and `diff.evidence_tier` carries the same value; the post-merge tiers additionally attach `footprint_resolution.caveat`, so a verdict graded over landing-commit evidence states its evidence tier rather than reading as a live-worktree verdict.

## Cross-Check Matrix

Each row is one rule. The script emits exactly one finding when the rule's expected outcome is contradicted by the actual diff.

### Rule M1: docs-only manifest implies docs-only diff

**Manifest signal**: `phase_5.verification_steps == []` AND `phase_5.early_terminate == false` (the docs-only and verification-no-files rules from the matrix produce this shape).

**Expected diff**: All file paths must match one of the docs-only patterns:
- `*.md`
- `*.adoc`
- Path contains `/references/` segment
- Path contains `/templates/` segment

**Finding (when violated)**: `severity=warning`, `code=docs_only_diff_violation`, `message="phase_5.verification_steps is empty but diff includes non-docs files: {culprits[:5]}"`, with full culprit list under `details.culprits`.

### Rule M2: early-terminate manifest implies empty implementation diff

**Manifest signal**: `phase_5.early_terminate == true`.

**Expected diff**: Empty (no source files touched). Lessons-learned and `.plan/` artifact updates are filtered out before evaluation because they are produced post-implementation by phase-6-finalize, not by the analysis itself.

**Finding (when violated)**: `severity=warning`, `code=early_terminate_diff_nonempty`, `message="phase_5.early_terminate=true but diff includes implementation files: {culprits[:5]}"`.

### Rule M3: tests-only verification implies tests-only diff

**Manifest signal**: `phase_5.verification_steps` denotes module-tests and nothing else (the `tests_only` rule from the matrix).

The comparison is made on NORMALIZED step names, not on the raw list. On the marshal.json compose path — the one every real plan takes — the composer emits each built-in verify step as a canonical-verify id, `default:verify:{canonical}`, boundary-normalized to the bare `verify:{canonical}` form (`DEFAULT_PHASE_5_STEPS` is itself `('verify:quality-gate', 'verify:module-tests')`), so `verification_steps` reads `['verify:module-tests']`. A rule comparing the raw list against an unprefixed name cannot fire on a manifest composed that way.

The bare `{canonical}` form is **not impossible**, which is why this is a normalization and not a rewrite: the `--phase-5-steps` CSV fallback (callers without a marshal.json, notably tests) forwards its argument verbatim, and archived manifests predating the canonical-verify step id carry bare names. Normalization strips the optional `default:` prefix and then the `verify:` prefix, so `default:verify:module-tests`, `verify:module-tests`, and a bare `module-tests` all denote `module-tests`.

**Expected diff**: All non-docs file paths must look like test files — path contains `/test/`, `/tests/`, or filename matches `test_*.py`, `*_test.py`, `*Test.java`, `*Spec.java`, `*.test.js`, `*.spec.js`.

**Finding (when violated)**: `severity=warning`, `code=tests_only_diff_violation`, `message="phase_5 manifest is tests-only but diff includes non-test source files: {culprits[:5]}"`.

### Rule M4: Phase 6 includes branch-cleanup implies branch present at base

This is a soft consistency check — the script does not query git for branch state. Instead it asserts that `phase_6.steps` containing `branch-cleanup` is paired with at least one implementation-shaped diff entry (so there is something to clean up).

**M4 is the only diff-fed rule that fails on the survivor set being EMPTY** rather than on a culprit present within it, which makes the filter the thing that can produce its failing state. Three input states reach it, and each gets its own wording because they are different facts:

- **No tier resolved** — the rule reports `inconclusive` with `code=branch_cleanup_footprint_unresolved` at `severity=warning`, naming the chain it tried. Whether an implementation file changed is UNMEASURABLE. ⛔ This branch must never fall through to either wording below; both assert something about a footprint that was actually observed.
- **Footprint resolved, named no path** — a measured empty footprint. The finding says the observed footprint was empty, which it may say only here.
- **Footprint resolved non-empty, every entry filtered** — the filter produced the emptiness, so the finding names the reduction instead. Saying "the footprint is empty" in this branch would state the opposite of what was observed.

**Finding (the two resolved branches)**: `severity=info`, `code=branch_cleanup_without_changes`, `message="phase_6.steps includes branch-cleanup but no implementation file changed — all N diff entries classified as bookkeeping (plan state, the plan report, or a build-config route)"` (reduction branch), or the resolved-empty wording for the other.

The verdict is substantiated in both resolved branches because every drop category is a *positive* classification: an empty survivor set means every supplied path was positively identified as non-implementation.

⛔ The finding stops at what it knows and draws no conclusion about the push. Every drop category can contain tracked files that really did change on the branch — a `report` or `config` entry plainly, and `runtime_state` too, since `.plan/` is only partly git-ignored.

### Rule M5: Manifest version recognized

**Manifest signal**: `manifest_version` field present and equals the version known to this script.

**Finding (when violated)**: `severity=error`, `code=manifest_version_unknown`, `message="manifest_version={value} not recognized by check-manifest-consistency"`.

### Rule M6: Declared-vs-realized set comparison is received

**Source**: the `affected_files_exact_match` block of the `artifact-consistency` fragment — **not** the footprint. This is the receiving half of a forward: when an `execution.toon` exists, `check-artifact-consistency` downgrades its own `warn` to `info`, sets `forwarded_to_manifest: true`, and tells the reader the drift is handled here. Nothing read that flag, so the finding was not re-routed — it was **dropped**, on every manifest-bearing plan. A forward with no receiver loses more than the duplicate reporting the downgrade was introduced to avoid.

**Two sets, two severities**, because they mean different things:

| Set | Meaning | Severity |
|-----|---------|----------|
| `outline_only` | declared with a modification intent, absent from the realized footprint — a declaration the run did not honour | `warning` |
| `references_only` | realized but never declared — ordinary discovery on most plans | `info` |

**Finding (when either set is non-empty)**: `code=declared_vs_realized_set_mismatch`, severity per the table above (`warning` whenever `outline_only` is non-empty, else `info`), with the union of both sets under `culprits`.

**Both set sizes are published beside the verdict**, and so is the population they were taken over (`declared_vs_realized.outline_only_count` / `references_only_count`, plus the upstream status and the `forwarded_to_manifest` flag the block carried). A zero from this rule is exactly the kind that needs attribution.

⛔ **An unread fragment reports `inconclusive` and publishes NO counts.** When the artifact-consistency fragment is absent, unparseable, or carries no `affected_files_exact_match` block, the comparison was never received — `declared_vs_realized.received` is `false` with a reason and the count keys are **omitted**, never sent as two zeros. A zero from a comparison that ran and a zero from a comparison that never arrived are otherwise indistinguishable, which is the defect this whole aspect reports on.

## Rules That Are Intentionally NOT Checked

- The two surgical-bug_fix / surgical-tech_debt rule rows from the matrix produce the same Phase 5 verification step set as the default row (`['verify:quality-gate', 'verify:module-tests']`). Cross-checking them against the diff would produce no actionable finding because both rule outcomes accept any non-empty source-code diff. The `rule_fired` value carried in the decision log is the only artifact that tells them apart, and that asymmetry is by design.
- The recipe rule produces a Phase 5 step list that is a subset of the default. Same reasoning applies.

## Diff Path Filtering Rules

Before evaluating any rule, the script drops the diff entries that are bookkeeping side-effects produced by phase-6-finalize rather than implementation work. **The classification is the build map's, not the script's** — `build.map` in marshal.json is the declared file-to-build oracle, and every `{glob, role, build_class}` entry says which kind of file a path is. The script consults it through the shared `_footprint_classification` module that `check-routing-decisions.py` also uses, so the two resolve any given path to the same category. What each check then *does* with that category is its own policy — this one drops three of them, the routing check treats two as production — but neither reaches that policy from a private idea of what the path is.

A path is dropped when it falls in one of exactly three categories:

- `runtime_state` — a path beginning with `.plan/` (plan state, lessons drafts, archive moves). This is the one prefix still decided in code, because this tooling's own per-plan working state is not a file type any build system routes, so it appears in no build map and there is no oracle answer to defer to. ⛔ Not because it is git-ignored — it partly is not: `marshal.json` (which holds `build.map` itself) and every `project-architecture/**/enriched.json` are tracked. Trackedness is a different question with a different owner (`script-shared`'s `_plan_state_exemption`); this classifier answers what kind of file a path is, never whether an edit to it would be pushable.
- `report` — the plan's own `quality-verification-report*.md` files.
- `config` — a path the **oracle** routes with role `config`.

Everything else is kept: `production` and `test` (the oracle's implementation roles), `documentation`, and `unclassified`.

Two categories are resolved by convention rather than by the oracle, because the oracle cannot answer for them.

- **`documentation`** — the build_map role vocabulary deliberately has **no** documentation role (documentation has no build-system owner), so an unrouted path is recognised as `documentation` by **file suffix alone** (`.md` / `.adoc`). ⛔ The directory tokens (`references/`, `templates/`) are deliberately NOT part of this rung: a `.py` file under a `references/` directory is source, and classifying it as documentation would let a consumer that reads documentation as "not production" exonerate a real source change. Those tokens belong to the wider rule-side predicate below.
- **`test`** — a project whose `build.map` declares no `test` route would leave every test file unrouted, so test-ness is recognised by filename/directory convention where the oracle is silent. Without it a tests-only footprint would fall to `unclassified`, which the routing check treats as possible production.

A routed path always keeps the role the project declared; the conventions fire only where the oracle has no answer, and the `test` rung sits behind the `documentation` rung.

**The rules keep a wider docs predicate than the classifier does, and the difference is safe by position.** M1 and M3 test a *surviving* path for docs-shapedness using the wider suffix-OR-directory-token set they always used. That can never remove a path from view: the filter retains `documentation` and `unclassified` alike, so a wider recognition inside a rule only moves a path from culprit to non-culprit within an already-retained set. The narrow rung, by contrast, decides a *category* that a consumer may read as "not production" — which is why only it is suffix-only.

⛔ These convention sets are **these checks' own**. They are not imported from, and not identical to, `manage-execution-manifest`'s change-footprint classifier (`_manifest_core._DOC_SUFFIXES` also carries `.asciidoc` and has no directory concept). Do not describe them as that classifier's set.

⚠ And do not describe them as carried over unchanged from the pre-oracle code — that is true of one half only:

- **The documentation sets did not move.** Both retired copies used the same `.md` / `.adoc` suffixes; the directory tokens were the manifest copy's alone and, after the split described above, remain the manifest copy's alone. Neither consumer's docs behaviour changed.
- **The test sets moved, in both directions.** The name pattern gained `*Spec.java`, which only the manifest copy carried — for the routing check that is an **exonerating** change (a footprint of only `src/FooSpec.java` counted as production before and is `test` now), deliberate because a spec file is a test, and bounded to the case where the oracle is silent, the basename matches, and the path lies outside `test/`/`tests/`. The directory tokens lost the routing copy's bare `test/`/`tests/` forms, which were matched unanchored and so also hit `latest/`, `contest/` and `mytest/` — a substring defect, and dropping it is **fail-closed** (those paths now read as possible production).

**`unclassified` is kept, and that is deliberate.** A path no declared route covers is one the oracle has no opinion about — a could-not-classify, not a classified-as-unimportant. Dropping it would put a private guess back in charge of the question, so it is retained and counted instead, which can only widen what a rule examines.

This replaces a private prefix tuple that declared a project-local dotfile tree to be bookkeeping. A build extension may route such a tree as `production` — on the Claude target the project-local skill root `.claude/skills/*.py` is routed exactly that way — and wherever it did, the filter discarded production source as bookkeeping and every downstream rule evaluated the remainder.

Pure-deletion diff entries (e.g., a removed file) are kept because deletion is still implementation activity.

## Reporting a Reduced Input Set

Filtering happens before any rule sees the diff, so a rule can be evaluated against a small fraction of the supplied footprint and still emit a clean pass. That pass reads in every downstream summary exactly like a substantiated one. Two obligations close it, both applied after every evaluator so no rule can forget one:

- Every diff-fed check (`docs_only_diff`, `early_terminate_diff`, `tests_only_diff`, `branch_cleanup_changes`, `declared_vs_realized_set`) that ran against a reduced input set carries the reduction in its message. The membership is the script's single `_DIFF_FED_RULES` dispatch registry, which both the evaluation loop and the reduction report read — a rule added there is automatically evaluated AND automatically subject to this report; the list above restates that registry and is not a second source for it. `manifest_version_recognized` is exempt: it reads the manifest body alone, so no amount of filtering affects it.
- A check that would otherwise emit a bare clean `pass` while the **majority** of the supplied footprint was discarded (`files_filtered > files_kept`) takes the status `indeterminate` instead, and its message names the withheld verdict.

A `fail` is never downgraded, for a reason that differs by rule shape — the blanket rationale "a reduced input can only have hidden more violations" covers only one of the two:

- Rules that fail on a culprit **present** in the survivors (M1 / M2 / M3) draw their culprits from the filtered set, so a smaller input yields fewer of them: a culprit that survived is real.
- The rule that fails on the survivors being **empty** (M4) is the case that rationale does not cover, since the filter is what empties the set. Its verdict is substantiated by a different argument — every drop category is a *positive* classification, so an empty survivor set means every supplied path was positively identified as non-implementation — and it says exactly that rather than claiming the diff was empty. See [Rule M4](#rule-m4-phase-6-includes-branch-cleanup-implies-branch-present-at-base).

A `skip` is never downgraded either: the rule did not apply, which the filtering did not decide.

There is a third obligation with the same purpose and a different cause. A rule that would emit a bare clean `pass` while **no footprint reached it at all** — no `--diff-file`, and no tier of the shared chain resolved — takes `inconclusive`, the degradation token (see [Footprint degradation verdict](#footprint-degradation-verdict)), rather than `indeterminate`. The filtering logic cannot see this case: nothing was discarded, so the reduction is empty, yet the rule evaluated an empty footprint it never received.

⛔ An ABSENT observation and a RESOLVED empty one are different states and must not be inferred from the same `len(files) == 0`. A footprint that resolved to no path means the run really did change nothing — a rule may pass on it. The loader therefore reports evidence-availability directly, read through the resolver's own `footprint_resolved` predicate rather than by testing emptiness, so the distinction is never guessed downstream.

The `diff` block publishes the evidence: `evidence_tier` (which tier answered, or `unresolved`), `filtered_by_category` (one count per category, always present even at zero), `oracle_available` (whether the build map answered at all), `majority_discarded`, and `diff_available`.

## TOON Fragment Shape

The script emits this fragment for `compile-report` to render under the "Manifest Decisions" section:

```toon
aspect: manifest-decisions
status: success | skipped
plan_id: {plan_id}
manifest_present: true | false
manifest:
  manifest_version: 1
  phase_5:
    early_terminate: false
    verification_steps[*]: ['verify:quality-gate', 'verify:module-tests']
  phase_6:
    steps[*]: ['push', ...]
decision_log_entries[*]: ['(plan-marshall:manage-execution-manifest:compose) Rule default fired — ...']
footprint_resolution:
  status: resolved | inconclusive     # inconclusive IS the degradation token
  tier: {resolving tier that answered, 'diff_file', or 'unresolved'}
  base: {label of the evidence the tier supplied}
  chain[*]: {the RESOLVING_TIERS consulted}
  caveat: "{post-merge evidence caveat, empty for live tiers}"
declared_vs_realized:
  received: true | false
  # present ONLY when received: true — omitted, never zeroed, when it is false
  upstream_status: {the forwarded block's own status}
  forwarded_to_manifest: true | false
  outline_only_count: N
  references_only_count: N
  # present ONLY when received: false
  reason: "{why no set sizes were measured}"
diff:
  base: {label of the evidence supplied, or 'unresolved'}
  evidence_tier: {same tier value as footprint_resolution.tier}
  evidence_caveat: "{post-merge caveat, empty for live tiers}"
  files_total: N
  files_filtered: M
  files_kept: K
  filtered_by_category:
    runtime_state: N
    report: N
    production: N
    test: N
    config: N
    documentation: N
    unclassified: N
  oracle_available: true | false
  majority_discarded: true | false
checks[*]{name,status,message}:
  - manifest_version_recognized,pass,'manifest_version=1 recognized'
  - docs_only_diff,skip,'rule M1 not applicable — verification_steps non-empty or early_terminate=true'
  - early_terminate_diff,skip,'rule M2 not applicable — early_terminate=false'
  - tests_only_diff,skip,'rule M3 not applicable — verification_steps does not denote module-tests only'
  - branch_cleanup_changes,indeterminate,'... — VERDICT WITHHELD: M of N supplied paths were filtered as bookkeeping before evaluation'
  - declared_vs_realized_set,pass,'declared modification-intent set and realized footprint agree — received from check-artifact-consistency ...'
findings[*]{severity,code,message,culprits}:
  - warning,docs_only_diff_violation,'...',['src/a.py']
summary:
  passed: N
  failed: N
  skipped: N
  indeterminate: N
  inconclusive: N
  findings: N
```

`indeterminate` is a status distinct from both `skip` (the rule did not apply) and `pass` (the rule applied and was satisfied): it says the rule applied but saw too little of the supplied input for its verdict to mean anything. See [Reporting a Reduced Input Set](#reporting-a-reduced-input-set).

`inconclusive` is distinct from all three and is the **degradation** token: the rule applied and its input could not be obtained at all — no footprint tier resolved, or (for M6) the forwarded comparison was never received. See [Footprint degradation verdict](#footprint-degradation-verdict).

When `manifest_present == false`, the script emits `status: skipped` with an empty `checks` and `findings` list — the orchestrator should skip the aspect entirely in this case.

## LLM Interpretation Rules

- All findings emitted by this script MUST surface in the report under the "Manifest Decisions" section.
- The decision log entries pair WHAT (manifest) with WHY (rule that fired). Always render both.
- `manifest_version_unknown` is a hard error — it implies the manifest schema has drifted ahead of the cross-check engine. Surface as `error` and recommend updating the script.
- A clean run (all checks `pass` or `skip`, zero findings) is the expected outcome. The aspect's value comes from catching drift.
- An `indeterminate` check is **not** a clean result and MUST NOT be rendered as one. It reports that the rule saw only a minority of the supplied footprint, so it is surfaced with the reduction its message names — a withheld verdict, not a satisfied one.
- An `inconclusive` check is **not** a clean result either, and is a stronger statement than `indeterminate`: the rule's input could not be obtained at all. Surface it naming the unobtainable input — the unresolved footprint (with the chain that was tried) or the unreceived forwarded comparison — and never infer a figure for it. The usual cause of an unresolved footprint is a worktree the merge gate already deleted on a plan that recorded neither a realized-footprint capture nor a landing SHA, so the repair is to the measurement's evidence, not to the plan's declared files.

## Cross-References

- `references/artifact-consistency.md` — peer aspect; `affected_files_exact_match` forwards to this matrix when a manifest exists, and [Rule M6](#rule-m6-declared-vs-realized-set-comparison-is-received) is the rule that receives it.
- `plan-marshall:manage-execution-manifest` — the API that produces the manifest; see its `standards/decision-rules.md` for the authoritative rule definitions.
