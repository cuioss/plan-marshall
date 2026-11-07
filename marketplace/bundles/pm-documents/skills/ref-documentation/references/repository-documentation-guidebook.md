# Repository Documentation Architecture and Changes Protocol

## Purpose

This guidebook defines the repository-wide documentation architecture, Single-Source-of-Truth (SSOT) layer boundaries, visual diagram selection and density criteria, historical-overhead pruning rules, and step-by-step execution protocol for auditing, restructuring, and release-hardening all documentation across a repository — from the root `README`, module and bundle `README`s (`{module}/README.*`, `{module}/doc/`, `marketplace/bundles/**`), to every directory of the central `doc/` tree and `.github/` templates.

It complements and references — without restating — the foundational standards in this bundle:

* **[documentation-core.md](documentation-core.md)** — Core principles, verifiable claims, and code/configuration placeholder rules
* **[tone-and-style.md](tone-and-style.md)** — Objective tone, marketing/filler elimination, and transitional-marker removal
* **[organization-standards.md](organization-standards.md)** — Single-aspect principle, file naming, and base size guidelines (`50–400` lines; `100–300` target range)
* **[ref-narrative-styles](../../ref-narrative-styles/SKILL.md)** — Voice, three-part structural arc, and heading-depth ceiling (`<= 3` section levels below the document title) for [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md), [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md), and [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md)
* **[ref-asciidoc](../../ref-asciidoc/SKILL.md)** — AsciiDoc header attributes, list/table formatting ([`asciidoc-formatting.md`](../../ref-asciidoc/references/asciidoc-formatting.md)), and module README layout ([`readme-structure.md`](../../ref-asciidoc/references/readme-structure.md))
* **[ref-svg-diagrams](../../ref-svg-diagrams/SKILL.md)** — SVG diagram types, theme handling, `image::` embedding, and mandatory visual verification
* **[manage-adr](../../../../plan-marshall/skills/manage-adr/SKILL.md)** — Canonical ADR metadata block, six-section template structure, and lifecycle rules

---

## 1. Repository-Wide Layer Taxonomy and Single-Source-of-Truth (SSOT) Boundaries

Cross-document duplication and drift occur when layers lack strict content boundaries — for example, when a configuration field reference embeds multi-page operator tutorials, when operator guides expose internal class names and build-step mechanics, or when contributor docs mirror user guides under identical filenames.

### 1.1 Surface Discovery and Layer Classification

Before auditing or restructuring a repository, inventory every documentation surface present in the tree (`README.*`, `{module}/README.*`, `{module}/doc/`, `doc/**`, `marketplace/bundles/**`, `.github/**`) and classify each discovered directory or file into its owning layer in the table below. Content owned by one layer must be cross-referenced (`xref:` or Markdown link) from other layers, never restated.

Per [`organization-standards.md`](organization-standards.md), individual documents target `100–300` lines with a `400`-line ceiling (`50`-line minimum); any file exceeding `400` lines requires split evaluation.

| Repository Surface | Target Audience | Narrative Style | Canonical Content Owned (SSOT) | Explicitly Forbidden Content | Target Size (`<= 400` lines) |
|--------------------|-----------------|-----------------|-------------------------------|------------------------------|------------------------------|
| **Root `README.adoc` / `README.md`** | Evaluators, operators, new contributors | [`readme-structure.md`](../../ref-asciidoc/references/readme-structure.md) & [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) (with concise [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) purpose lead) | System purpose, high-level request/process overview SVG, capability summary table with links into `doc/`, complete build-reactor module list (100% parity with root build file), quick-start entry point, and active operational boundaries | Deep subsystem configuration tables, historical migration/upgrade notes, internal class inventories, or incomplete module lists | 150–250 lines |
| **Module `{module}/README.*`, `{module}/doc/`, & Bundle/Skill Docs (`marketplace/bundles/**`)** | Users and maintainers of that specific module, bundle, or skill | [`readme-structure.md`](../../ref-asciidoc/references/readme-structure.md), [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md), & [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md) | Module or skill role, coordinates, scoped build/run commands, canonical CLI/workflow invocations, and links to sub-guides or reference files | Repeating root system architecture, duplicating sibling module/skill instructions, or copying central `doc/` guides | 100–250 lines (`README`); 100–400 lines (sub-guides / skill docs) |
| **`doc/README.adoc` (Documentation Hub)** | All readers | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | Audience-routed navigation map (SVG + tables) covering all present `doc/` subdirectories, non-goals/positioning summary, and compact ADR index table (`ADR`, `Title`, `Status`) | Multi-paragraph summaries of each ADR, duplicate status disclaimers, or orphaned feature prose | 150–220 lines |
| **`doc/Requirements.adoc`, `doc/requirements/`, & `doc/specifications/`** | Architects, contributors, and auditors | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) (per `pm-requirements:requirements-authoring`) | Testable functional and non-functional requirement specifications with stable requirement IDs and traceability links | Implementation walkthroughs, operator tutorials, or duplicated YAML schema tables | 150–400 lines per file |
| **`doc/configuration.adoc` & `doc/configuration/*.adoc`** | Operators looking up schema keys | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | Canonical skeleton exhibit, field dictionary (key, type, default, allowed values, boot validation rule, 1-sentence behavior), and cross-links to `doc/user/` | Multi-page operator tutorials, architectural motivation essays, internal test-class references, or repeated policy tables across sections | Hub 150–350 lines; domain child files 200–400 lines |
| **`doc/user/*.adoc` (Operator & User Guides)** | Operators and users deploying or running the system | [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md) (procedures) & [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) (troubleshooting tables) | Task-oriented configuration recipes, operational procedures, certificate/key setup, troubleshooting tables (`Symptom` → `Cause` → `Fix`), and observable log codes | Internal class/method names, bytecode/framework build-step internals, unit test names, or inert placeholder keys in starter templates | 150–400 lines (extract shared setup to `{topic}-common.adoc`) |
| **`doc/variants/*.adoc` (Deployment Postures)** | Operators comparing reference topologies | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | 1-page posture datasheet: variant topology/sequence SVG, minimal configuration delta over base posture, security/operational property summary, and links to `doc/user/` | Re-explaining protocol mechanics already covered in `doc/user/`, source code snippets, or historical CI benchmark logs | 120–250 lines per variant |
| **`doc/architecture/*.adoc`, `doc/concepts/*.adoc`, & `doc/technical_aspects.adoc`** | Architects and reviewers | [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) | Runtime component boundaries, request/event pipeline stages, conceptual models, cross-cutting technical mechanisms, threading/execution model, trust-boundary enforcement, and design invariants | Line-by-line source code walkthroughs, class/method inventories that belong in API docs, or full configuration option tables that belong in `doc/configuration/` | Hub 150–250 lines; topic files 150–350 lines |
| **`doc/security-threat-model.adoc` & Conformance Matrices (`doc/fapi_status.adoc`)** | Security auditors and operators | [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) (threat analysis) & [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) (conformance tables) | Threat catalogue (`Attack Vector` → `Structural Control` → `Residual Boundary`) and requirement conformance matrices reconciled with current implementation | Test-method inventories, kernel/container debugging lab notebooks, or stale partial statuses for mitigated threats | 200–400 lines per file (split by domain when exceeding 400 lines) |
| **`doc/LogMessages.adoc`** | Operators and incident responders | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | Complete log record table (`ID`, `Level`, `Message Template`, `1–3 sentence trigger & operator action`) | Multi-paragraph architecture essays or call-chain narrations inside table cells | 1–3 sentences per row (`< 250` chars/cell) |
| **`doc/development/*.adoc` & `doc/developer/*.adoc` (Contributor Guides)** | Contributors extending code, skills, or test harnesses | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) & [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md) (with [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) for design rationale) | Extension SPIs, build/test-lane boundaries, integration-test topologies, fitness-function contracts, and release/build-gate rules | Parallel re-explanations of `doc/user/` or `doc/architecture/` topics, completed multi-pass audit tables, or review diaries | 150–400 lines |
| **`doc/adr/*.adoc` (Decision Records)** | Contributors and architects | [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) | Point-in-time architectural decisions following the canonical [`plan-marshall:manage-adr`](../../../../plan-marshall/skills/manage-adr/SKILL.md) structure (`// adr-metadata` block + `Status`, `Context`, `Decision`, `Consequences`, `Alternatives Considered`, `References`) | Full configuration reference manuals, implementation class inventories, or non-architectural conventions (e.g., test-naming rules, which belong in `doc/development/` or `doc/developer/`) | 80–250 lines (hard cap `<= 400` lines; split or trim exhibits if larger) |
| **`.github/` Templates & Workflow Docs** | Contributors and maintainers | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | Concise PR/issue checklists (`PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/**`) and workflow usage notes | Duplicated contributor guides or stale checklist items for retired processes | 50–150 lines |

### 1.2 Cross-Cutting Topic Ownership (SSOT Mapping)

When a technical topic spans multiple audiences, enforce these canonical ownership boundaries so each fact is stated once:

| Cross-Cutting Topic | Canonical Owner (SSOT) | Permitted Content in Other Layers |
|---------------------|------------------------|-----------------------------------|
| **Configuration keys, defaults, types, & boot validation rules** | `doc/configuration.adoc` & `doc/configuration/*.adoc` | `doc/user/` and `doc/variants/` show task-specific YAML snippets and link to `doc/configuration/` for field definitions |
| **Step-by-step operator setup, key generation, & troubleshooting** | `doc/user/*.adoc` (with shared setup in `{topic}-common.adoc`) | `doc/configuration/` links to `doc/user/` for operational setup; `doc/variants/` shows only the posture delta |
| **Runtime pipeline stages, threading model, & trust boundaries** | `doc/architecture/*.adoc` & `doc/concepts/*.adoc` | `doc/user/` describes externally observable behavior only; `doc/development/` / `doc/developer/` links to `doc/architecture/` |
| **Why a design was chosen over rejected alternatives** | `doc/adr/*.adoc` (`== Decision`, `== Consequences`, `== Alternatives Considered`) | `doc/architecture/` and `doc/development/` state the active design invariant and cross-reference the ADR |
| **Threat vectors, mitigations, & residual operational boundaries** | `doc/security-threat-model.adoc` | `README` and `doc/user/` link to the threat model rather than restating threat matrices |
| **Log message IDs, levels, & operator remediation actions** | `doc/LogMessages.adoc` | `doc/user/` troubleshooting tables cite the log ID and link to `doc/LogMessages.adoc` |
| **Build profiles, test lanes, & fitness-function contracts** | `doc/development/*.adoc` / `doc/developer/*.adoc` | Root `README` lists only the top-level quick-start build command and links to contributor docs |

---

## 2. Structural Consolidation and Splitting Rules

Beyond the general size guidelines in [`organization-standards.md`](organization-standards.md), apply these structural patterns across the repository:

### 2.1 Splitting Oversized Documents (`> 400` lines) and Monolithic Manuals (`> 1,000` lines)

Per [`organization-standards.md`](organization-standards.md), evaluate any document exceeding `400` lines for splitting. When a reference manual or guide grows past `400` lines (and mandatorily when a monolithic manual exceeds `1,000` lines):

1. **Keep an entry-point hub** (`doc/configuration.adoc` or `doc/configuration/README.adoc`, `150–350` lines) containing the top-level structural overview, canonical minimal/skeleton exhibit, and navigation table.
2. **Split domain sections into cohesive child files** (`200–400` lines each, such as `doc/configuration/tls-and-egress.adoc`, `authentication-and-oidc.adoc`, `routing-and-forwarding.adoc`, `security-and-edge-hardening.adoc`, `validation-rules.adoc`).
3. **Enforce the 3-level section depth ceiling**: In AsciiDoc (`=` document title, `==` level 1, `===` level 2, `====` level 3; see [`asciidoc-formatting.md`](../../ref-asciidoc/references/asciidoc-formatting.md)), `:toclevels: 3` includes up to `====` in the table of contents, and [`ref-narrative-styles`](../../ref-narrative-styles/SKILL.md) caps section hierarchy at 3 levels (`====`). Note that `:toclevels: 3` only controls TOC rendering and `asciidoc validate` does not enforce heading depth — explicitly scan for and eliminate `=====` (level 4+) headings by converting deep subsections into tables, definition lists, or split child documents.

### 2.2 Extracting Shared Prerequisite Guides (`{topic}-common.adoc`)

When two or more sibling guides (for example, stateful `bff-session.adoc` and stateless `bff-cookie.adoc`, or multiple module guides) repeat the same prerequisite setup (IdP discovery, PEM certificates, client authentication, token refresh, container startup):

1. Extract the shared procedures into a single canonical guide (`150–350` lines, e.g., `doc/user/bff-oidc-common.adoc`).
2. Slim each sibling guide to cover only its differentiating mechanics and link to the common guide.

### 2.3 Eliminating Parallel Shadow Files Across `doc/user/`, `doc/variants/`, and `doc/development/`

When the same filename appears in both `doc/user/` and `doc/development/` or `doc/developer/` (e.g., `tls-edge.adoc`, `compose-sample.adoc`, `bff-cookie.adoc`, `bff-session.adoc`):

* Verify whether the contributor file has genuine contributor-only SPI/harness content.
* Strip any runtime architecture explanations (which belong in `doc/architecture/`) and operator configuration walkthroughs (which belong in `doc/user/`) from the contributor file.
* If no contributor-specific content remains after deduplication, retire the shadow file and link to the canonical owner.

### 2.4 Merging Fragmented Status + Next-Steps Pairs

Never split a single conformance or feature topic into separate `*_status.adoc` and `*_next_steps.adoc` files (such as `fapi_status.adoc` and `fapi_next_steps.adoc`). They inevitably duplicate the requirement matrix and drift out of sync. Maintain a single status document (`<= 400` lines, or split by domain if larger) with a concise concluding section for open gaps.

---

## 3. Historical Overhead and Release-Readiness Pruning Catalogue

In addition to the prohibited marketing, superlative, and empty filler patterns ("Floskeln" such as *"simply"*, *"it is worth noting"*, *"seamlessly"*) defined in [`tone-and-style.md`](tone-and-style.md) and [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md), release-ready documentation must be purged of seven categories of historical and developmental overhead:

1. **Historical Migration & Tombstone Prose**:
   * Delete sections explaining removed configuration keys, deleted properties, renamed flags, or upgrade paths between earlier snapshots (`"Previously..."`, `"Moved from X to Y"`, `"==== Deleted properties"`).
   * Remove inert or unimplemented keys (`# INERT`) from copy-pasteable starter configuration blocks.
2. **Completed Multi-Pass Audit Ledgers & Drained Backlogs**:
   * When a contributor note (`test-corpus-integrity.adoc`, `declared-limit-assertion-coverage.adoc`) records a multi-pass codebase sweep, retain **only** the enduring engineering rules and the contract-tested invariant tables.
   * Delete historical pass-by-pass finding tables, commit-by-commit mutation logs, scoring-formula essays explaining how the sweep was calculated, and drained backlog sections (`"None — drained"`).
3. **Frozen Point-in-Time Quality Snapshot Directories**:
   * Retire static snapshot directories (`doc/quality-report/*.adoc` tied to an older commit SHA) once automated CI gates and architecture tests enforce the invariants.
4. **Debugging Lab Notebooks & Chronological Investigation Diaries**:
   * Delete chronological OS/kernel/container debugging logs (hypothesis → refutation narratives, raw packet traces, pre-merge/post-merge CI rollout diaries). State only the confirmed root cause, the active mitigation or configuration rule, and the residual operational limit.
5. **Self-Review & PR Disposition Logs Inside Documentation**:
   * Delete trailing sections that record review turn-by-turn history (`"=== Diagram check for the ... change"`, `"=== PR review dispositions"`, `"=== What the sweep did not find"`, `"=== Verified on <commit>"`).
6. **Rejected Design Debates in Operator or Contributor Guides**:
   * Alternative designs that were evaluated and rejected belong concisely in the relevant ADR's `== Alternatives Considered` and `== Consequences` sections (per [`plan-marshall:manage-adr`](../../../../plan-marshall/skills/manage-adr/SKILL.md)) — never as a multi-page debate inside `doc/user/` or `doc/development/`.
7. **Leaked Authoring Prompts or Template Meta-Instructions**:
   * Strip incidental authoring meta-instructions, prompt scaffolding (`"Per Clarification 1..."`, `"Generated using skill..."`), and leftover template comments (`// Maintain the metadata block...`) from committed documentation.
   * **Preserve product-surface identifiers**: Never strip skill, plugin, command, or configuration identifiers (such as `plan-marshall:automatic-review` in configuration docs or `plan-marshall:manage-config:manage-config` in CLI examples) when those identifiers are the documented subject matter, configuration keys, or executable commands of the repository.

### Sentence-Level Anti-Chattiness and Genre-Voice Compression Rules

Even after deleting historical sections and cross-file duplicates, surviving paragraphs remain 35–40% too verbose when every document is written as an argumentative essay. Enforce these five micro-level compression rules on all kept prose:

1. **Match the Style to the Layer (Consistent with Section 1.1)**:
   * [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) (problem → structural response → honest limit) belongs in motivating design and threat prose (`doc/architecture/`, `doc/concepts/`, `doc/technical_aspects.adoc`, `doc/adr/`, `doc/security-threat-model.adoc`, and concise purpose leads).
   * [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) belongs in `doc/configuration/`, `doc/variants/`, `doc/LogMessages.adoc`, `doc/Requirements.adoc`, `doc/README.adoc`, and reference sections of contributor/skill docs: state the key, type, default, valid set, and failure condition flatly without philosophical preambles.
   * [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md) belongs in procedural sections of `doc/user/`, module guides, and contributor workflow guides: state the prerequisite, the ordered action, and the observable checkpoint.
2. **Eliminate Rhetorical Lecturing and Negative Preambles ("X is Y, not a licence to Z")**:
   * Delete dramatic framing that lectures the reader on why an invalid configuration is bad (`"Plain HTTP is something you declare, never something the gateway infers... What the opt-in declares is the posture of a coherent deployment, not a licence to..."`). State the positive rule and the exact boot/runtime refusal condition in one direct sentence.
3. **Strip Provenance and Test-Harness Chatter from Operator Prose**:
   * Never explain inside `doc/configuration/` or `doc/user/` *how* a table was compiled (`"This enumeration is re-derived from source..."`) or how an internal architecture test scans AST call sites.
4. **Replace Patch-by-Patch Archaeology with the Present Invariant**:
   * Delete chronological accounts of how a control evolved across past bugs or ADRs (`"The coverage exception was first written path-geometrically... Before the earlier ADR they were not..."`). State only the invariant that holds today.
5. **Convert Multi-Clause Refusal Prose into Flat Tables**:
   * Whenever a paragraph lists three or more validation refusals, flag interactions, or input constraints separated by semicolons, replace the prose paragraph with a 3-column table (`Condition` | `Behavior / Refusal` | `Log ID`).

---

## 4. Visual Comprehension and Diagram Selection Protocol

Diagrams are primary comprehension anchors for human readers, not decorative illustrations. When authoring or reviewing visual assets across `README.*`, `doc/`, and module docs, apply [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md) together with these selection and density rules:

1. **Prefer Behavioral & Process Diagrams Over Static Block Diagrams**:
   * Prioritize **sequence**, **flow**, **swim-lane / process**, **state**, and **decision** diagrams ([`diagram-type-sequence.md`](../../ref-svg-diagrams/standards/diagram-type-sequence.md), [`diagram-type-flow.md`](../../ref-svg-diagrams/standards/diagram-type-flow.md), [`diagram-type-state.md`](../../ref-svg-diagrams/standards/diagram-type-state.md), [`diagram-type-deployment.md`](../../ref-svg-diagrams/standards/diagram-type-deployment.md)) over static structural block diagrams ([`diagram-type-block.md`](../../ref-svg-diagrams/standards/diagram-type-block.md)).
   * *Rationale*: Static block diagrams often restate package or class names that are already obvious from the file tree, whereas sequence, flow, swim-lane, and state diagrams make multi-actor protocols, trust-boundary crossings, precedence resolution chains, concurrency/single-flight coordination, and error/rejection paths immediately understandable.
2. **Diagram Density and Readability Limits**:
   * **Node and lane ceiling**: Keep each diagram to `<= 12–15` primary nodes/boxes and `<= 4–6` swim-lanes or sequence participants so a reader can parse the flow in one glance.
   * **Label brevity**: Limit node labels to `<= 4–6` words and edge labels to `<= 3–4` words; keep detailed field schemas, property names, and error catalogs in surrounding prose tables rather than crowding SVG boxes.
   * **When to split a dense diagram**: If representing a workflow requires more than `15` nodes, crosses more than `6` participants, or forces font sizes below the minimums in [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md), split it into one end-to-end overview diagram plus focused per-stage or per-sub-flow diagrams.
3. **High-Value Diagram Placements Across the Repository**:
   * **Root `README` & `doc/README.adoc`**: End-to-end request/process pipeline swim-lane (`gateway-overview.svg`) and reader navigation decision map (`documentation-map.svg`).
   * **`doc/configuration/` & `doc/user/`**: Policy scope inheritance & anchor merge precedence flowcharts, multi-leg TLS topology & trust-profile decision trees, authentication/BFF sequences, key-rotation state timelines, and environment override precedence flows.
   * **`doc/security-threat-model.adoc`**: Swim-lane trust-boundary crossing diagram and pipeline-stage threat-control mapping.
   * **`doc/development/` / `doc/developer/` & `benchmarks/`**: Build-gate profile decision flow, release-pipeline gate sequence, and benchmark harness topology.
4. **Replace Legacy ASCII Boxes and Embed Orphaned SVGs**:
   * Replace inline ASCII box diagrams in user-facing and architectural `.adoc` files with theme-aware SVGs stored in `doc/resources/diagrams/`.
   * Audit `doc/resources/diagrams/*.svg` against `image::` directives across `doc/`: reuse and embed existing diagrams in `doc/user/` and `doc/architecture/` whenever they illustrate the operator or runtime flow being discussed.
5. **Mandatory Visual Verification**:
   * Execute Step 4 ("Mandatory Visual Verification") of [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md) for every new or modified SVG before committing.

---

## 5. Protocol for Repository-Wide Documentation Reviews and Changes

When executing a documentation review or restructuring campaign across a repository, follow this five-phase protocol to prevent contract-test breakage, dangling cross-references, and unreviewable diffs.

> **Execution-Lane Note (`execute-script.py` vs. Standalone Plan Lane)**: The `python3 .plan/execute-script.py ...` commands below apply in standard local checkouts where the generated executor is present. When executing a plan under `doc/plans/` in the standalone plan lane (`cloud-plan-lane`, where `.plan/execute-script.py` and `.plan/local/` do not exist), skip `.plan/execute-script.py` calls and perform discovery and verification using `Glob`/`Grep`/`Read` and the repository's native build wrapper (e.g., `./pw verify`) per the `cloud-plan-lane` contract.

### Phase 1: Contract-Test and CI Gate Inventory (Mandatory First Step)

Many repositories enforce documentation-to-code parity via unit/architecture contract tests and CI scripts that parse `.adoc` or `.md` files directly. Before editing, splitting, or deleting any documentation file:

1. Search the test tree and `.github/workflows/` for references to `.adoc`, `.md`, `doc/`, `README`, `AGENTS.md`, or `CLAUDE.md` (e.g., `*ContractTest*`, `*ArchTest*`, `*WiringTest*`, `*Docs*Test*`).
2. Extract every asserted constraint into a **Contract-Test Constraint Matrix**:
   * Exact string anchors (`"== Gateway Configuration"`, `"The mode set is exactly"`, `"switches every one of them off..."`)
   * Bounded text slices (`START_ANCHOR` .. `END_ANCHOR`)
   * AsciiDoc tag regions (`// tag::inventory[]` .. `// end::inventory[]`)
   * Table structures (`|===` column indices and cell contents matched against code validators or schemas)
   * File-existence, ordinal-uniqueness, and line-length caps (e.g., required `== Status` heading, maximum line counts)
3. Record for each test whether the target constraint will remain in-place or whether the test's file-path constant must be updated in the same commit as a document split.

### Phase 2: Baseline Automated Scan and Cross-Corpus Audit

1. **Discover all documentation surfaces and run baseline validation**:
   * Discover every `.adoc` and `.md` surface across the repository (`README.*`, `{module}/README.*`, `{module}/doc/`, `doc/**`, `marketplace/bundles/**`, `.github/**`):
     ```bash
     python3 .plan/execute-script.py plan-marshall:manage-files:manage-files discover --root . --glob "**/*.adoc" --include-files
     ```
   * Run AsciiDoc format validation and link verification across `doc/` and every discovered AsciiDoc surface outside `doc/` (root `README.adoc`, `{module}/README.adoc`, `{module}/doc/`) using [`pm-documents:ref-asciidoc`](../../ref-asciidoc/SKILL.md):
     ```bash
     python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path doc
     python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory doc --recursive --report target/asciidoc-link-verifier/links.md
     ```
     *(Repeat `--path` / `--file` / `--directory` for root `README.adoc` and each `{module}/README.adoc` or `{module}/doc/` directory present in the repository.)*
   * Complete Steps 5–6 of the `verify-links` workflow in [`pm-documents:ref-asciidoc`](../../ref-asciidoc/SKILL.md): inspect `unchecked_link_classes` and `unreadable` entries, and manually verify reported `broken_links` via `Read` to separate real broken links from false positives.
   * For Markdown surfaces (`README.md`, `{module}/README.md`, `marketplace/bundles/**/*.md`, `.github/**/*.md`) — which `ref-asciidoc` does not parse — verify Markdown formatting and resolve relative `[text](target)` links across discovered `.md` files.
   * Record any pre-existing validation errors in untouched files as baseline findings so each wave knows which existing issues belong to its target group.
2. **Audit the corpus in four logical groups** (using parallel research passes for large repositories, ensuring every discovered documentation directory is assigned to a group):
   * **Group 1 — Root, Requirements & Top-Level Reference Docs**: `README.*`, `doc/README.adoc`, `doc/Requirements.adoc` (`doc/requirements/`, `doc/specifications/`), `doc/configuration*`, `doc/security-threat-model.adoc`, `doc/technical_aspects.adoc`, `doc/concepts/*`, conformance status docs, `doc/LogMessages.adoc`, and any legacy `doc/quality-report/` snapshots.
   * **Group 2 — Operator Guides & Deployment Variants**: `doc/user/*.adoc` and `doc/variants/*.adoc`.
   * **Group 3 — Contributor Guides, Module Docs & Bundle/Template Docs**: `doc/development/*.adoc`, `doc/developer/*.adoc`, `{module}/README.*` + `{module}/doc/*`, `marketplace/bundles/**`, and `.github/**`.
   * **Group 4 — Architectural Decision Records**: `doc/adr/**` and ADR index parity in `doc/README.adoc` (verify status parity, bidirectional `supersedes` / `amended by` links, canonical [`plan-marshall:manage-adr`](../../../../plan-marshall/skills/manage-adr/SKILL.md) six-section template + `// adr-metadata` compliance, and deep-link `[[_...]]` anchors).
3. **Trace cross-document duplication clusters** across all four groups and assign a single canonical owner (SSOT) per cluster using Section 1.1 and Section 1.2.
4. When requested to plan before modifying, persist actionable per-group review reports (`doc/quality-reports/README.adoc` + `01..04-*.adoc`) containing quantitative line/diagram targets, the Contract-Test Constraint Matrix, the Cross-Document Duplication Matrix, and checkable task IDs (`TASK-G1-01`, etc.).

### Phase 3: Wave-Based Execution Discipline

Execute changes in bounded waves aligned with the four groups (keeping each pull request well below 150 changed files):

* **Splitting files**: Create the child files (`<= 400` lines each), keep or update contract-tested exhibits, and update every inbound `xref:` / `link:` / Markdown link across `doc/`, `README.*`, and module/bundle docs in the same wave.
* **Retiring obsolete files**: First fold any enduring invariant (such as a test-lane boundary table or a non-goals table) into its canonical SSOT target, then `git rm` the obsolete file and remove all inbound links from `README.*` and index tables.
* **Slimming ADRs and Threat Models**: Preserve the `// adr-metadata` block, the six canonical ADR sections (`Status`, `Context`, `Decision`, `Consequences`, `Alternatives Considered`, `References`), and every explicit anchor (`[[_...]]`, `[#...]`) targeted by other documents. Replace duplicated configuration schemas and architecture tables with cross-links to `doc/configuration/` and `doc/architecture/`.

### Phase 4: Verification Gate Before Commit

Every documentation wave must pass all four checks before committing:

1. **Formatting, Structural Validation & Heading-Depth Check**:
   * Run AsciiDoc list formatting and validation on every touched AsciiDoc surface (`doc/`, root `README.adoc`, `{module}/README.adoc`, `{module}/doc/`):
     ```bash
     python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc format --path doc --type lists --no-backup
     python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path doc
     ```
   * Require `0 errors, 0 warnings` on all files created or modified in the wave (and across the entire corpus once all waves complete; if an untouched file in another group has a pre-existing baseline validation issue recorded in Phase 2, either fix it in-place or scope `--path` to the wave's target paths until that group's wave runs).
   * Verify heading depth independently of `:toclevels: 3`: confirm no modified `.adoc` file contains `=====` (level 4+) headings.
   * *Watch for accidental level-0 titles*: Never start a continuation line inside a paragraph or equation at column 0 with `= ...`, which AsciiDoc parses as a duplicate document title.
2. **Cross-Reference, Unchecked-Link & Manual Link Verification**:
   * Run `verify-links` across `doc/` and any modified root or module AsciiDoc surfaces:
     ```bash
     python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory doc --recursive --report target/asciidoc-link-verifier/links.md
     ```
   * Complete Steps 5–6 of the `verify-links` workflow in [`pm-documents:ref-asciidoc`](../../ref-asciidoc/SKILL.md):
     * Manually verify every reported `broken_links` item via `Read`/path resolution to confirm whether it is a genuine broken link (must be fixed) or a tool false positive (must be documented/dispositioned).
     * Inspect and disposition every entry in `unchecked_link_classes` (external URLs, absolute paths, attribute-bearing `link:` targets, fragments on non-AsciiDoc targets, and `code-span` / listing-block macros with `[subs="+macros"]`) and resolve any `unreadable` targets.
   * Verify relative links in any modified Markdown files (`README.md`, `{module}/README.md`, `marketplace/bundles/**/*.md`).
   * *Watch for literal `<<...>>` in prose*: Link verifiers parse `<<anchor>>` even inside single backticks; refer to anchor names in prose without raw `<<...>>` brackets unless creating an actual internal link.
3. **SVG Visual Verification**:
   Confirm every new or edited `.svg` has completed Step 4 ("Mandatory Visual Verification") of [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md).
4. **Contract-Test Verification**:
   * Whenever a wave touches **any file or constraint** recorded in the Phase 1 Contract-Test Constraint Matrix — including exact anchors, bounded text slices, tag regions, asserted table cells/columns, file-existence rules, ordinal numbering, line-count caps, or test path constants — run the affected `*ContractTest` / `*ArchTest` / documentation tests to confirm green status before committing.
   * For waves that touch no file or constraint in the Contract-Test Constraint Matrix, follow the repository's configured doc-landing policy.

---

## References

* [Documentation Core Standards](documentation-core.md)
* [Tone and Style Standards](tone-and-style.md)
* [Documentation Organization Standards](organization-standards.md)
* [Narrative Styles (`engineering-narrative`, `reference-spec`, `tutorial-walkthrough`)](../../ref-narrative-styles/SKILL.md)
* [AsciiDoc Formatting Standards](../../ref-asciidoc/references/asciidoc-formatting.md)
* [Module README Structure Standards](../../ref-asciidoc/references/readme-structure.md)
* [SVG Diagram Standards and Visual QA](../../ref-svg-diagrams/SKILL.md)
* [ADR Management Standards](../../../../plan-marshall/skills/manage-adr/SKILL.md)
* [Documentation PR Comment Disposition](../../ext-triage-docs/standards/pr-comment-disposition.md)
