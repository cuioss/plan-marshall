# Repository Documentation Architecture and Changes Protocol

## Purpose

This guidebook defines the repository-wide documentation architecture, Single-Source-of-Truth (SSOT) layer boundaries, visual diagram selection criteria, historical-overhead pruning rules, and step-by-step execution protocol for auditing, restructuring, and release-hardening all documentation across a repository — from the root `README`, module `README`s (`{module}/README.*` and `{module}/doc/`), to every directory of the central `doc/` module.

It complements and references — without restating — the foundational standards in this bundle:

* **[documentation-core.md](documentation-core.md)** — Core principles, verifiable claims, and code/configuration placeholder rules
* **[tone-and-style.md](tone-and-style.md)** — Objective tone, marketing/filler elimination, and transitional-marker removal
* **[organization-standards.md](organization-standards.md)** — Single-aspect principle, file naming, and base size guidelines
* **[ref-narrative-styles](../../ref-narrative-styles/SKILL.md)** — Voice, three-part structural arc, and heading-depth ceiling (`<= 3`) for [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md), [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md), and [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md)
* **[ref-asciidoc](../../ref-asciidoc/SKILL.md)** — AsciiDoc header attributes, list/table formatting ([`asciidoc-formatting.md`](../../ref-asciidoc/references/asciidoc-formatting.md)), and module README layout ([`readme-structure.md`](../../ref-asciidoc/references/readme-structure.md))
* **[ref-svg-diagrams](../../ref-svg-diagrams/SKILL.md)** — SVG diagram types, theme handling, `image::` embedding, and mandatory light/dark visual QA

---

## 1. Repository-Wide Layer Taxonomy and Single-Source-of-Truth (SSOT) Boundaries

Cross-document duplication and drift occur when layers lack strict content boundaries — for example, when a configuration field reference embeds multi-page operator tutorials, when operator guides expose internal Java class names and build-step mechanics, or when contributor docs mirror user guides under identical filenames.

Every document in a repository belongs to exactly one layer in the table below. Content owned by one layer must be cross-referenced (`xref:` or markdown link) from other layers, never restated.

| Repository Surface | Target Audience | Narrative Style | Canonical Content Owned (SSOT) | Explicitly Forbidden Content | Target Size |
|--------------------|-----------------|-----------------|-------------------------------|------------------------------|-------------|
| **Root `README.adoc` / `README.md`** | Evaluators, operators, new contributors | [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) | System purpose, high-level request/process overview SVG, capability summary table with links into `doc/`, complete build-reactor module list (100% parity with root build file), quick-start entry point, and active operational boundaries | Deep subsystem configuration tables, historical migration/upgrade notes, internal class inventories, or incomplete module lists | 150–250 lines |
| **Module `{module}/README.adoc` & `{module}/doc/`** | Users/contributors of that specific module | [`readme-structure.md`](../../ref-asciidoc/references/readme-structure.md) & [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md) | Module role, coordinates, module-scoped build/run commands (e.g., benchmark harness, E2E suite, demo client), and links to `{module}/doc/` sub-guides | Repeating root system architecture, duplicating sibling module instructions, or copying central `doc/` guides | 100–250 lines (`README`); 150–400 lines (sub-guides) |
| **`doc/README.adoc` (Documentation Hub)** | All readers | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | Audience-routed navigation map (SVG + tables) covering *Operator Guides*, *Configuration & Security Reference*, *Architecture & ADRs*, and *Contributor Guides*; non-goals/positioning summary; compact ADR index table (`ADR`, `Title`, `Status`) | Multi-paragraph summaries of each ADR, duplicate alpha disclaimers, or orphaned feature prose | 150–220 lines |
| **`doc/configuration.adoc` & `doc/configuration/*.adoc`** | Operators looking up schema keys | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | Canonical skeleton exhibit, field dictionary (key, type, default, allowed values, boot validation rule, 1-sentence behavior), and cross-links to `doc/user/` | Multi-page operator tutorials, architectural motivation essays, internal test-class references, or repeated policy tables across sections | Hub `<= 450` lines; domain child files 300–550 lines |
| **`doc/user/*.adoc` (Operator Guides)** | Operators deploying and configuring the system | [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md) & [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) | Task-oriented configuration recipes, operational procedures, PEM/key setup, troubleshooting tables (`Symptom` → `Cause` → `Fix`), and observable log codes | Internal class/method names, bytecode/framework build-step internals, JUnit test names, or `# INERT` placeholder keys in starter templates | 250–650 lines (extract shared setup to `{topic}-common.adoc`) |
| **`doc/variants/*.adoc` (Deployment Postures)** | Operators comparing reference topologies | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | 1-page posture datasheet: variant topology/sequence SVG, minimal YAML delta over base posture, security/operational property summary, and links to `doc/user/` | Re-explaining protocol mechanics (OIDC, PAR, DPoP, TLS) already covered in `doc/user/`, Java code snippets, or historical CI benchmark logs | 120–250 lines per variant |
| **`doc/architecture/*.adoc`** | Architects and reviewers | [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) | Runtime component boundaries, request/event pipeline stages, threading/execution model, trust-boundary enforcement, and design invariants | Line-by-line source code walkthroughs, class/method inventories that belong in Javadoc, or full YAML option tables that belong in `doc/configuration/` | Hub `<= 250` lines; topic files 150–350 lines |
| **`doc/security-threat-model.adoc` & Status Matrices (`doc/fapi_status.adoc`)** | Security auditors and operators | [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) | Threat catalogue (`Attack Vector` → `Structural Control` → `Residual Boundary`) and requirement conformance matrices reconciled with current implementation | JUnit test-method inventories, kernel/container debugging lab notebooks, or stale `PARTIAL` statuses for mitigated threats | 250–600 lines per file (split by domain if `> 1,500` lines) |
| **`doc/LogMessages.adoc`** | Operators and incident responders | [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) | Complete log record table (`ID`, `Level`, `Message Template`, `1–3 sentence trigger & operator action`) | Multi-paragraph architecture essays or Java call-chain narrations inside table cells | 1–3 sentences per row (`< 250` chars/cell) |
| **`doc/development/*.adoc` (Contributor Guides)** | Contributors extending code or test harnesses | [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) | Extension SPIs, test-lane boundaries, integration-test container topologies, fitness-function contracts, and release/build-gate rules | Parallel re-explanations of `doc/user/` or `doc/architecture/` topics, completed multi-pass audit tables, or PR review diaries | 150–650 lines |
| **`doc/adr/*.adoc` (Decision Records)** | Contributors and architects | [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) | Point-in-time architectural decisions following the 4-section ADR skeleton (`Status`, `Context`, `Decision`, `Trade-offs and Limitations`; see `plan-marshall:manage-adr`) | Full YAML reference manuals, implementation class inventories, or non-architectural conventions (e.g., test-naming rules, which belong in `doc/development/`) | Target 80–250 lines (hard cap `<= 500` lines) |

---

## 2. Structural Consolidation and Splitting Rules

Beyond the general size guidelines in [`organization-standards.md`](organization-standards.md), apply these structural patterns across the repository:

### 2.1 Splitting Monolithic Reference Manuals (`> 1,000` lines)

When a reference document (such as `doc/configuration.adoc` or `doc/user/endpoint-routes.adoc`) grows past 1,000 lines:

1. **Keep an entry-point hub** (`doc/configuration.adoc` or `doc/configuration/README.adoc`) containing the top-level structural overview, canonical minimal/skeleton exhibit, and navigation table.
2. **Split domain sections into cohesive child files** (`doc/configuration/tls-and-egress.adoc`, `authentication-and-oidc.adoc`, `routing-and-forwarding.adoc`, `security-and-edge-hardening.adoc`, `validation-rules.adoc`).
3. **Flatten deep heading hierarchies**: Enforce the `:toclevels: 3` (`===`) ceiling from [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) and [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md). Any `====` or `=====` heading indicates either an unsplit sub-topic or an enumeration that belongs in a table or definition list.

### 2.2 Extracting Shared Prerequisite Guides (`{topic}-common.adoc`)

When two or more sibling guides (for example, stateful `bff-session.adoc` and stateless `bff-cookie.adoc`, or multiple `demo-client` guides) repeat the same prerequisite setup (IdP discovery, PEM certificates, client authentication, token refresh, container startup):

1. Extract the shared procedures into a single canonical guide (e.g., `doc/user/bff-oidc-common.adoc`).
2. Slim each sibling guide to cover only its differentiating mechanics (`mode: server` session store vs. `mode: cookie` AEAD sealing) and link to the common guide.

### 2.3 Eliminating Parallel Shadow Files Across `doc/user/`, `doc/variants/`, and `doc/development/`

When the same filename appears in both `doc/user/` and `doc/development/` (e.g., `tls-edge.adoc`, `compose-sample.adoc`, `bff-cookie.adoc`, `bff-session.adoc`):

* Verify whether `doc/development/<name>.adoc` has genuine contributor-only SPI/harness content.
* Strip any runtime architecture explanations (which belong in `doc/architecture/`) and operator configuration walkthroughs (which belong in `doc/user/`) from `doc/development/<name>.adoc`.
* If no contributor-specific content remains after deduplication, retire the shadow file and link to the canonical owner.

### 2.4 Merging Fragmented Status + Next-Steps Pairs

Never split a single conformance or feature topic into separate `*_status.adoc` and `*_next_steps.adoc` files (such as `fapi_status.adoc` and `fapi_next_steps.adoc`). They inevitably duplicate the requirement matrix and drift out of sync. Maintain a single status document with a concise concluding section for open gaps.

---

## 3. Historical Overhead and Release-Readiness Pruning Catalogue

In addition to the prohibited marketing, superlative, and empty filler patterns ("Floskeln" such as *"simply"*, *"it is worth noting"*, *"seamlessly"*) defined in [`tone-and-style.md`](tone-and-style.md) and [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md), release-ready documentation must be purged of seven categories of historical and developmental overhead:

1. **Pre-Release / Historical Migration & Tombstone Prose**:
   * Delete sections explaining removed YAML keys, deleted properties, renamed flags, or upgrade paths between pre-1.0 snapshots (`"Previously..."`, `"Moved from X to Y"`, `"==== Deleted Quarkus properties"`).
   * Remove inert or unimplemented keys (`# INERT today`) from copy-pasteable starter configuration blocks.
2. **Completed Multi-Pass Audit Ledgers & Drained Backlogs**:
   * When a contributor note (`test-corpus-integrity.adoc`, `declared-limit-assertion-coverage.adoc`) records a multi-pass codebase sweep, retain **only** the enduring engineering rules and the contract-tested invariant tables.
   * Delete Pass 1/2/3 historical finding tables, commit-by-commit mutation logs, combinatorial math essays explaining how the sweep was scored, and drained backlog sections (`"None — drained"`).
3. **Frozen Point-in-Time Quality Snapshot Directories**:
   * Retire static snapshot directories (`doc/quality-report/*.adoc` tied to a historical commit SHA) once automated CI gates and architecture tests enforce the invariants.
4. **Debugging Lab Notebooks & Chronological Investigation Diaries**:
   * Delete dated OS/kernel/container debugging logs (e.g., `2026-09-01` hypothesis → `2026-09-23` refutation, `orbstack` packet traces, pre-merge/post-merge CI rollout diaries). State only the confirmed root cause, the active mitigation or configuration rule, and the residual operational limit.
5. **Self-Review & PR Disposition Logs Inside Documentation**:
   * Delete trailing sections that record PR review turn-by-turn history (`"=== Diagram check for the ... change"`, `"=== PR #408 dispositions"`, `"=== What the sweep did not find"`, `"=== Verified on <commit>"`).
6. **Rejected Design Debates in Operator or Contributor Guides**:
   * Alternative designs that were evaluated and rejected belong concisely in the relevant ADR's `== Decision` / `== Trade-offs and Limitations` section — never as a 150-line debate inside `doc/user/` or `doc/development/`.
7. **Leaked Agent, Prompt, or Template Meta-Instructions**:
   * Strip internal skill/plugin identifiers (`pm-documents:ref-svg-diagrams`), prompt references (`"Per Clarification 1..."`), and leftover template comments (`// Maintain the metadata block...`) from committed repository documentation.

### Sentence-Level Anti-Chattiness and Genre-Voice Compression Rules

Even after deleting historical sections and cross-file duplicates, surviving paragraphs remain 35–40% too verbose when every document is written as an argumentative essay. Enforce these five micro-level compression rules on all kept prose:

1. **Match the Style to the Layer (Stop Applying `engineering-narrative` to Specs and Tutorials)**:
   * [`engineering-narrative.md`](../../ref-narrative-styles/styles/engineering-narrative.md) (problem → structural response → honest limit) belongs **only** in motivating design prose (`doc/architecture/`, `doc/adr/`, `doc/security-threat-model.adoc`).
   * [`reference-spec.md`](../../ref-narrative-styles/styles/reference-spec.md) belongs in `doc/configuration/`, `doc/variants/`, and `doc/LogMessages.adoc`: state the key, type, default, valid set, and failure condition flatly without philosophical preambles.
   * [`tutorial-walkthrough.md`](../../ref-narrative-styles/styles/tutorial-walkthrough.md) belongs in `doc/user/`: state the prerequisite, the ordered action, and the observable checkpoint.
2. **Eliminate Rhetorical Lecturing and Negative Preambles ("X is Y, not a licence to Z")**:
   * Delete dramatic framing that lectures the reader on why an invalid configuration is bad (`"Plain HTTP is something you declare, never something the gateway infers... What the opt-in declares is the posture of a coherent deployment, not a licence to..."`). State the positive rule and the exact boot/runtime refusal condition in one direct sentence.
3. **Strip Provenance and Test-Harness Chatter from Operator Prose**:
   * Never explain inside `doc/configuration/` or `doc/user/` *how* a table was compiled (`"This enumeration is re-derived from source..."`) or how an internal ArchUnit test (`EgressTlsPostureArchTest`) scans AST call sites.
4. **Replace Patch-by-Patch Archaeology with the Present Invariant**:
   * Delete chronological accounts of how a control evolved across past bugs or ADRs (`"The coverage exception was first written path-geometrically... Before ADR-0047 they were not..."`). State only the invariant that holds today.
5. **Convert Multi-Clause Refusal Prose into Flat Tables**:
   * Whenever a paragraph lists three or more validation refusals, flag interactions, or input constraints separated by semicolons, replace the prose paragraph with a 3-column table (`Condition` | `Behavior / Refusal` | `Log ID`).

---

## 4. Visual Comprehension and Diagram Selection Protocol

Diagrams are primary comprehension anchors for human readers, not decorative illustrations. When authoring or reviewing visual assets across `README.adoc`, `doc/`, and module docs, apply [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md) together with these selection rules:

1. **Prefer Behavioral & Process Diagrams Over Static Block Diagrams**:
   * Prioritize **sequence**, **flow**, **swim-lane / process**, **state**, and **decision** diagrams ([`diagram-type-sequence.md`](../../ref-svg-diagrams/standards/diagram-type-sequence.md), [`diagram-type-flow.md`](../../ref-svg-diagrams/standards/diagram-type-flow.md), [`diagram-type-state.md`](../../ref-svg-diagrams/standards/diagram-type-state.md), [`diagram-type-deployment.md`](../../ref-svg-diagrams/standards/diagram-type-deployment.md)) over static structural block diagrams ([`diagram-type-block.md`](../../ref-svg-diagrams/standards/diagram-type-block.md)).
   * *Rationale*: Static block diagrams often restate package or class names that are already obvious from the file tree, whereas sequence, flow, swim-lane, and state diagrams make multi-actor protocols, trust-boundary crossings, precedence resolution chains, concurrency/single-flight coordination, and error/rejection paths immediately understandable.
2. **High-Value Diagram Placements Across the Repository**:
   * **Root `README.adoc` & `doc/README.adoc`**: End-to-end request/process pipeline swim-lane (`gateway-overview.svg`) and reader navigation decision map (`documentation-map.svg`).
   * **`doc/configuration/` & `doc/user/`**: Policy scope inheritance & YAML anchor merge precedence flowcharts, multi-leg TLS topology & trust-profile decision trees, OIDC/BFF login/PAR/DPoP sequences, key-rotation state timelines, and 3-class environment override precedence flows.
   * **`doc/security-threat-model.adoc`**: Swim-lane trust-boundary crossing diagram and pipeline-stage threat-control mapping.
   * **`doc/development/` & `benchmarks/`**: Build-gate profile decision flow, release-pipeline gate sequence, and benchmark harness topology.
3. **Replace Legacy ASCII Boxes and Embed Orphaned SVGs**:
   * Replace inline ASCII box diagrams in user-facing and architectural `.adoc` files with theme-aware SVGs stored in `doc/resources/diagrams/`.
   * Audit `doc/resources/diagrams/*.svg` against `image::` directives across `doc/`: reuse and embed existing diagrams in `doc/user/` and `doc/architecture/` whenever they illustrate the operator or runtime flow being discussed.
4. **Mandatory Dual-Theme Visual Verification**:
   * Follow Step 4 of [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md) without exception: rasterize every new or modified SVG against both `#ffffff` (light) and `#0d1117` (dark) backgrounds using `rsvg-convert` and visually inspect the rendered PNGs for clipping, label collisions, contrast, and arrow termination before committing.

---

## 5. Protocol for Repository-Wide Documentation Reviews and Changes

When executing a documentation review or restructuring campaign across a repository, follow this five-phase protocol to prevent contract-test breakage, dangling cross-references, and unreviewable diffs.

### Phase 1: Contract-Test and CI Gate Inventory (Mandatory First Step)

Many repositories enforce documentation-to-code parity via JUnit/pytest contract tests and CI scripts that parse `.adoc` or `.md` files directly. Before editing, splitting, or deleting any documentation file:

1. Search the test tree and `.github/workflows/` for references to `.adoc`, `.md`, `doc/`, `README`, `AGENTS.md`, or `CLAUDE.md` (e.g., `*ContractTest*`, `*ArchTest*`, `*WiringTest*`, `*Docs*Test*`).
2. Extract every asserted constraint into a **Contract-Test Constraint Matrix**:
   * Exact string anchors (`"== Gateway Configuration"`, `"The mode set is exactly"`, `"switches every one of them off..."`)
   * Bounded text slices (`START_ANCHOR` .. `END_ANCHOR`)
   * AsciiDoc tag regions (`// tag::inventory[]` .. `// end::inventory[]`)
   * Table structures (`|===` column indices matched against Java validators or schemas)
   * File-existence, ordinal-uniqueness, and line-length caps (e.g., ADR `<= 500` lines, required `== Status` heading)
3. Record for each test whether the target anchor will remain in-place or whether the test's file-path constant must be updated in the same commit as a document split.

### Phase 2: Baseline Automated Scan and Cross-Corpus Audit

1. Run format validation and link verification across the entire documentation surface (`README.adoc`, `{module}/README.adoc`, `{module}/doc/`, and `doc/`) using [`pm-documents:ref-asciidoc`](../../ref-asciidoc/SKILL.md):
   ```bash
   python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path doc
   python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory doc --recursive
   ```
2. Audit the corpus in four logical groups (using parallel research passes for large repositories):
   * **Group 1 — Root & Top-Level Reference Docs**: `README.adoc`, `doc/README.adoc`, `doc/configuration*`, `doc/security-threat-model.adoc`, `doc/technical_aspects.adoc`, conformance status docs, `doc/LogMessages.adoc`, and any legacy `doc/quality-report/` snapshots.
   * **Group 2 — Operator Guides & Deployment Variants**: `doc/user/*.adoc` and `doc/variants/*.adoc`.
   * **Group 3 — Contributor Guides & Module Docs**: `doc/development/*.adoc` and `{module}/README.adoc` + `{module}/doc/*.adoc`.
   * **Group 4 — Architectural Decision Records**: `doc/adr/*.adoc` and ADR index parity in `doc/README.adoc` (verify status parity, bidirectional `supersedes` / `amended by` links, 4-section skeleton compliance, and deep-link `[[_...]]` anchors).
3. Trace **cross-document duplication clusters** across all four groups and assign a single canonical owner (SSOT) per cluster using the Layer Taxonomy in Section 1.
4. When requested to plan before modifying, persist actionable per-group review reports (`doc/quality-reports/README.adoc` + `01..04-*.adoc`) containing quantitative line/diagram targets, the Contract-Test Constraint Matrix, the Cross-Document Duplication Matrix, and checkable task IDs (`TASK-G1-01`, etc.).

### Phase 3: Wave-Based Execution Discipline

Execute changes in bounded waves aligned with the four groups (keeping each pull request well below 150 changed files):

* **Splitting files**: Create the child files, keep or update contract-tested exhibits, and update every inbound `xref:` / `link:` across `doc/`, `README.adoc`, and module docs in the same wave.
* **Retiring obsolete files**: First fold any enduring invariant (such as a 6-row test-lane boundary table or a 20-line non-goals table) into its canonical SSOT target, then `git rm` the obsolete file and remove all inbound links from `README.adoc` / index tables.
* **Slimming ADRs and Threat Models**: Preserve every explicit anchor (`[[_...]]`, `[#...]`) targeted by other documents. Replace duplicated YAML schemas and architecture tables with cross-links to `doc/configuration/` and `doc/architecture/`.

### Phase 4: Verification Gate Before Commit

Every documentation wave must pass all four checks before committing:

1. **AsciiDoc List Formatting & Structural Validation (`0 errors, 0 warnings`)**:
   ```bash
   python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc format --path doc --type lists --no-backup
   python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path doc
   ```
   *Watch for accidental level-0 titles*: Never start a continuation line inside a paragraph or equation at column 0 with `= ...`, which AsciiDoc parses as a duplicate document title.
2. **Cross-Reference & Anchor Verification (`0 broken links`)**:
   ```bash
   python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory doc --recursive
   ```
   *Watch for literal `<<...>>` in prose*: Link verifiers parse `<<anchor>>` even inside single backticks; refer to anchor names in prose without raw `<<...>>` brackets unless creating an actual internal link.
3. **SVG Visual QA**:
   Confirm every new or edited `.svg` has passed light (`#ffffff`) and dark (`#0d1117`) PNG inspection per [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md).
4. **Contract-Test Verification**:
   * If any contract-tested document anchor was touched or a contract-test path constant was updated, run the affected `*ContractTest` / `*ArchTest` unit tests to confirm green status.
   * For pure documentation waves that do not alter code or contract-tested anchors, follow the repository's configured doc-landing policy.

---

## References

* [Documentation Core Standards](documentation-core.md)
* [Tone and Style Standards](tone-and-style.md)
* [Documentation Organization Standards](organization-standards.md)
* [Narrative Styles (`engineering-narrative`, `reference-spec`, `tutorial-walkthrough`)](../../ref-narrative-styles/SKILL.md)
* [AsciiDoc Formatting Standards](../../ref-asciidoc/references/asciidoc-formatting.md)
* [Module README Structure Standards](../../ref-asciidoc/references/readme-structure.md)
* [SVG Diagram Standards and Visual QA](../../ref-svg-diagrams/SKILL.md)
* [Documentation PR Comment Disposition](../../ext-triage-docs/standards/pr-comment-disposition.md)
