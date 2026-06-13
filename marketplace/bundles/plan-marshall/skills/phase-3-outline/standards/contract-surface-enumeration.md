# Contract-Surface Enumeration for Contract/Semantic Changes

Outline-time procedure that ensures every *describe-side* surface asserting a script's old contract or semantic behavior is enumerated in the deliverable's `Affected files` list before phase-3-outline finalizes. The describe surface is the body of prose, docstrings, help strings, command tables, and Output examples that *describe* what a symbol does — as distinct from the call sites that *use* it. This standard exists to close a recurring failure mode in which a plan changes a script's output contract, seeding semantics, default-config behavior, or returned schema, the deliverable lists only the changed code's files, and the now-stale describe surface (sibling docstrings, the owning SKILL.md command table, an Output example, a cross-referencing data-model doc) is discovered late — typically during pre-submission self-review, after the affected-files set is already frozen.

> **Why this matters**: A contract change that updates the code but not the prose that describes the contract ships a self-contradicting component — the docstring promises the old payload key, the SKILL.md Output example shows the old schema, and the next reader (human or LLM) trusts the stale description. Enumerating the describe surface at outline time adds seconds of grep work and prevents a drift that otherwise surfaces after the deliverable is frozen.

## Separation of concerns: describe side vs. consume side

This standard is the **describe-side** sibling of [`consumer-sweep.md`](consumer-sweep.md). The two standards partition the symbol-change problem along an explicit boundary:

| Standard | Side | Owns |
|----------|------|------|
| [`consumer-sweep.md`](consumer-sweep.md) | **consume** | Structural symbol removals/renames — every *importer*, *caller*, and call site of a deleted or renamed public symbol. The failure it prevents is an `ImportError` / `AttributeError` / unresolved-notation breakage at a consuming site. |
| `contract-surface-enumeration.md` (this doc) | **describe** | Contract/semantic-change describe surface — every *docstring*, *help string*, *command table*, *Output example*, and *cross-referencing standards/data-model doc* that asserts the old contract or behavior. The failure it prevents is stale prose that contradicts the shipped code. |

The two are complementary, not overlapping: a single deliverable that both removes a symbol AND changes a contract triggers both standards. `consumer-sweep.md` enumerates the call sites that would break to compile/import; this standard enumerates the descriptive surfaces that would lie. Run both when both triggers fire — neither subsumes the other.

---

## 1. Trigger Heuristic

Contract-surface enumeration is **mandatory** when a deliverable changes a script's **contract** or **ownership** — that is, when the observable behavior or interface that downstream readers depend on shifts. Concretely, the trigger fires when a deliverable's `Change per file`, `Refactoring`, or title text changes any of the following:

| Contract dimension | Examples |
|--------------------|----------|
| **Output-payload keys** | rename/remove/add a key in a script's returned TOON/JSON; change a field's type or cardinality |
| **Seeding semantics** | change how a verb seeds, initializes, or derives state (e.g., per-module vs. monolithic layout, default seed values) |
| **Default-config behavior** | change a config field's default, the value an absent field resolves to, or the enum vocabulary a knob accepts |
| **Verb side-effects** | change what a subcommand writes/mutates, the files it touches, or the order of its effects |
| **Returned schema** | change the shape of a structured return (add/remove a nested block, change a list to a scalar, rename a status enum) |
| **Ownership transfer** | move a symbol's authoritative home from one module/skill to another, or split one symbol's responsibility across two |

**Scope qualifier**: The trigger applies to **observable contract/semantic surfaces** — the interface and behavior that a downstream reader or caller relies on. It does NOT apply to:

- Pure internal refactors that preserve the observable contract (e.g., extracting a private helper without changing the public return).
- Local variable renames or comment edits with no contract impact.
- Documentation-only changes that themselves *are* the describe surface being corrected (those are the output of this procedure, not a new trigger).

When the trigger fires, you MUST run the Required describe-surface enumeration (§2), apply the Grep-old-keys discipline (§3), and — when the contract change also removes or renames a symbol — apply the Consumer/test-file obligation (§4) before finalizing the deliverable. When the trigger does not match, this procedure is optional and may be skipped without a log entry.

---

## 2. Required Describe-Surface Enumeration

When the trigger fires, enumerate every describe-side surface that asserts the changed contract and add each as an explicit entry under the deliverable's `**Affected files:**` list. The required surfaces are:

1. **The changed function's own docstring** — the docstring/module-comment on the function, verb, or class whose contract changed. If it describes the old payload key, the old default, or the old behavior, it is now stale.

2. **Every sibling/caller docstring that asserts the old behavior** — docstrings on related functions in the same module (a `save_*` sibling to a changed `load_*`), and docstrings at caller sites that paraphrase the callee's old contract ("returns the legacy flat payload", "seeds the monolithic file"). A sibling docstring that restates the contract is a describe surface even when the sibling's own code did not change.

3. **Every affected argparse help string** — the `help=` text on any argument, subcommand, or the program description whose meaning shifted with the contract. A renamed output key, a changed default, or a new enum value almost always has a corresponding `--help` string that now misdescribes the surface.

4. **The owning SKILL.md command table + Output examples** — the command/verb table row and the `## Output` / Canonical-invocations example block in the skill that owns the changed script. A changed returned schema makes the Output example wrong; a renamed verb or flag makes the command table wrong.

5. **Cross-referencing standards/data-model docs** — any `standards/*.md`, data-model doc, or reference guide (in the owning bundle or in a cross-referencing bundle) that documents the old payload key, the old schema, or the old behavior. These are the surfaces most easily missed because they live outside the changed code's directory.

Each enumerated surface becomes a flat bullet under `**Affected files:**`, following the same flat-list convention as `consumer-sweep.md` §3. For each entry, the deliverable's `**Change per file:**` field MUST describe the describe-surface update explicitly — not "update docs", but "rewrite the `load_module_derived` docstring to describe the per-module return; update the `manage-architecture` SKILL.md Output example to show the nested `modules[]` block instead of the flat `entries` list".

---

## 3. Grep-Old-Keys Discipline

Structured enumeration (§2) covers the surfaces you can name from the change description. The grep-old-keys discipline catches the surfaces you cannot name in advance — the cross-referencing doc three bundles away, the help string you forgot, the test fixture that hard-codes the old key. Before finalizing `affected_files`, grep the codebase for the old contract's fingerprints and treat every hit outside the changed code as a doc-surface obligation.

For each changed contract element, derive its fingerprints and grep for them:

- **Old payload key** — the literal key string being renamed/removed:

  ```bash
  grep -rn "{old_payload_key}" marketplace/bundles/
  ```

- **Old behavior phrase** — the prose phrase that paraphrases the old behavior (e.g., `"monolithic derived-data"`, `"flat payload"`, `"defaults to off"`):

  ```bash
  grep -rn "{old_behavior_phrase}" marketplace/bundles/
  ```

- **Removed element** — the removed default value, enum member, or schema field name:

  ```bash
  grep -rn "{removed_element}" marketplace/bundles/
  ```

Each grep is a separate Bash invocation (one command per call — never combined with `&&`, `;`, or pipes). Run `architecture find --pattern "{symbol}"` first for module-level matches; the grep calls exist to reach sub-module describe surfaces (help strings inside script files, prose inside `standards/*.md`, Output examples inside SKILL.md) that the structured query elides.

**Disposition rule**: For every grep hit:

- A hit **inside the changed code** is already in scope by definition — discard it.
- A hit **outside the changed code** that describes or asserts the old contract is a doc-surface obligation — add the containing file to `affected_files` with explicit `Change per file` text describing the correction.
- A hit that is **coincidental** (the same string used in an unrelated context) is discarded after inspection — but the inspection is mandatory; do not discard a hit unexamined.

Discard `__pycache__` paths and vendored dependencies before triaging hits.

---

## 4. Consumer/Test-File Obligation for Symbol Removals

When the contract change **removes or renames a symbol** (not merely changes its behavior in place), the describe-surface enumeration is not sufficient on its own — the call sites and their tests must also be enumerated. For each removed/renamed symbol, enumerate into `affected_files`:

- **Every importer/caller** of the removed/renamed symbol — the consume-side sites that would fail to import or resolve. This obligation is the same one `consumer-sweep.md` owns; this section names it here so that a contract change that *also* removes a symbol does not let the consume-side sweep fall through a gap when the deliverable was filed primarily as a contract change. Run the `consumer-sweep.md` Sweep Procedure (§2 there) to discover these sites.
- **The test file of every enumerated importer/caller** — the unit/integration test that imports the symbol, asserts against its old return, or constructs a fixture using the old contract. A symbol removal that updates production callers but leaves a test importing the removed name produces a collection-time `ImportError` that the production sweep alone does not surface. Every consumer file added under this obligation pulls its corresponding `test/.../test_*.py` file into `affected_files` alongside it.

The boundary with `consumer-sweep.md`: that standard owns the *discovery procedure* for structural removals/renames (the architecture-find + grep sweep, the cross-bundle/same-bundle distinction, the worked `load_derived_data` example). This section's obligation is to make sure that a deliverable filed as a *contract change* still runs that procedure and pulls the matching **test files** into scope — test files being the surface most often dropped when the deliverable's mental model is "I changed a contract" rather than "I removed a symbol".

---

## 5. Cross-References

- [`consumer-sweep.md`](consumer-sweep.md) — The consume-side sibling. Owns the discovery procedure for structural symbol removals/renames (every importer/caller of a deleted/renamed public symbol). Run alongside this standard when a contract change also removes or renames a symbol (§4).
- [`outline-workflow-detail.md`](../outline-workflow-detail.md) — Step 7 (Simple Track) and Step 10 (Complex Track) apply this standard before deliverable finalization when the trigger heuristic (§1) fires.
- [`change-feature.md`](../change-feature.md) and [`change-tech_debt.md`](../change-tech_debt.md) — discovery sub-sections cross-reference this standard for contract/semantic changes.
- `plan-marshall:phase-3-outline/SKILL.md` — `## Related` section carries a one-line cross-reference pointing here, parallel to the `consumer-sweep.md` entry.
- Rationale: contract/semantic changes that update code but not the describe surface ship self-contradicting components; the stale prose is discovered late (after deliverable finalization) during pre-submission self-review. Enumerating the describe surface before finalization prevents the drift.
