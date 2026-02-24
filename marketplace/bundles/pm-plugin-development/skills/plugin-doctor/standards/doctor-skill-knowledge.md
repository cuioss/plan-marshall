# Doctor Skill Knowledge Workflow

Review knowledge skill content quality — complements doctor-skills (structural compliance) and doctor-skill-content (file organization) by analyzing semantic content correctness, consistency, and LLM fitness.

## Parameters

- `skill-path` (required): Path to skill directory to review
- `focus` (optional): Single dimension — `correctness`, `consistency`, `structure`, `llm-optimization`. Default: all.
- `--no-fix` (optional): Diagnosis only, no fixes

## Scope boundary with plugin-doctor

Skip what other doctor workflows cover: frontmatter format, enforcement blocks, tool declarations, Rule 9/10a/11 compliance. Step 4 of the review runs plugin-doctor for those.

## Phase 1: Load Prerequisites

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
Read references/llm-optimization-guide.md
```

## Phase 2: Inventory and Read

1. Glob all files in the skill directory: `**/*.md`, `**/*.toon`, `**/*.json`
2. Read SKILL.md first (entry point and index of all content)
3. Read all files in standards/, references/, and other subdirectories
4. Build a corpus map: file → sections → topics covered

## Phase 3: Review Content Quality

Apply four review dimensions to the full corpus. Each finding needs: severity (high/medium/low), `file:line` location, concrete recommendation.

### 3.1: Correctness and Completeness

- **Stale content**: APIs, flags, classes, or script notations that are deprecated or renamed. Cross-check tool names, parameter names, and notations against actual files (Glob/Grep to verify existence).
- **Broken references**: File paths, skill names (`bundle:skill`), script notations (`bundle:skill:script`) pointing to non-existent targets. Verify with Glob.
- **Incomplete guidance**: Rules stated positively ("do X") without the exception ("except when Y"). Patterns shown without failure modes. Workflows missing error/abort paths.
- **Example quality**: Code examples that would fail if followed literally — missing imports, wrong method signatures, outdated syntax. Only flag copy-pasteable examples; conceptual illustrations are fine.
- **Gap detection**: Compare stated scope (frontmatter description, "What This Skill Provides") against actual content. If it claims to cover topic X but no document addresses X, that's a gap.

**Not in scope**: Frontmatter correctness, enforcement block presence, whether examples represent "best practice" (only flag if they're wrong).

### 3.2: Consistency and Duplication

- **Term drift**: Same concept called different names across documents (e.g., "script notation" vs "3-part notation" vs "executor notation"). Collect all terms for key concepts and flag divergence.
- **Contradictory rules**: Two documents giving opposite guidance. One must be wrong.
- **Internal contradictions**: Within a single document, earlier sections contradicting later ones (common in incrementally updated documents).
- **Redundant content**: Same information in multiple files without cross-referencing. Acceptable: a brief summary in SKILL.md pointing to detail in standards/. Unacceptable: full explanations repeated verbatim.
- **Scope overlap**: Two documents covering the same topic without clear division of authority.

**Judgment**: Cross-skill duplication (content repeated from another skill in the same bundle) is higher severity than within-skill duplication.

### 3.3: Structural Coherence

- **Hierarchy violations**: SKILL.md should be the entry point; standards files should be self-contained within their topic. If a standards file refers back to SKILL.md for essential context, the split is wrong.
- **Missing cross-references**: Documents that logically depend on each other but don't reference each other. The LLM would not know to load both.
- **Orphaned documents**: Files in standards/, references/, or assets/ not referenced from SKILL.md or any sibling document.
- **Wrong directory placement**: Prescriptive rules in references/ (should be standards/), background/explanatory material in standards/ (should be references/), templates not in templates/.
- **Section ordering**: Actionable information should come first. Flag: 200 lines of background before the actual rules.
- **Granularity mismatch**: One standards file covering 5 unrelated topics while another covers a single narrow aspect. Suggest splitting or merging.

**Reordering format**: When recommending reorder, state current order (by section heading), proposed order, and why.

### 3.4: LLM Optimization

Apply criteria from `llm-optimization-guide.md`:
- Flag motivational text, history/changelog, redundant emphasis
- Flag obvious checklists (>50% of items are things the LLM would do without being told)
- Flag verbose examples (multiple examples of the same pattern)
- Flag rationale sections that don't influence LLM behavior
- Flag human-targeted content not separated into companion files (see llm-optimization-guide.md)
- Verify decision tables and explicit constraints are used where appropriate

## Phase 4: Report Findings

Report format:

```
Skill: {name}
Documents: {count} ({total_lines} lines)
Assessment: {STRONG | ADEQUATE | NEEDS WORK}

## Findings

### Correctness and completeness
{findings or "No issues"}

### Consistency and duplication
{findings}

### Structural coherence
{findings}

### LLM optimization
{findings}

## Top recommendations (max 5)
1. ...
```

Each finding: severity, `file:line` location, dimension, description, recommendation.
Group by dimension, then by severity within each dimension.

## Phase 5: Plugin-Doctor Structural Check

Run `/pm-plugin-development:plugin-doctor skills skill-name={skill-name}` and append structural findings under a separate heading in the report.

## Phase 6: Apply Fixes

Skip if `--no-fix`.

**Safe fixes** (auto-apply):
- Broken file path references (when correct path can be determined)
- Term drift (when canonical term is clear from context)

**Risky fixes** (require confirmation):
- Content removal (redundant content, low-value patterns)
- File reorganization (wrong directory placement)
- Content consolidation (merging overlapping documents)

## Differentiation from Other Doctor Workflows

| Workflow | Focus |
|----------|-------|
| doctor-skills | Structural compliance (frontmatter, tools, enforcement blocks) |
| doctor-skill-content | File organization (classification, directory placement) |
| **doctor-skill-knowledge** | Semantic content quality (correctness, consistency, LLM fitness) |
