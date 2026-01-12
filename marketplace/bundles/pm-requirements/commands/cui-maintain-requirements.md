---
name: cui-maintain-requirements
description: Maintain and synchronize requirements and specifications with comprehensive validation
allowed-tools: Skill, Read, Write, Edit, Glob, Grep, Bash
---

# Requirements and Specifications Maintenance Command

Systematic workflow for maintaining requirements and specification documents to ensure continued accuracy, traceability, and alignment with implementation.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "cui-maintain-requirements", bundle: "pm-requirements"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **scope** - (Optional) Maintenance scope:
  - `full` - Complete requirements and specifications maintenance (default)
  - `requirements` - Focus on requirements documents only
  - `specifications` - Focus on specification documents only
  - `references` - Focus on cross-reference verification only
- **scenario** - (Optional) Specific maintenance scenario:
  - `new-feature` - Adding documentation for new functionality
  - `deprecation` - Handling deprecated or removed functionality
  - `refactoring` - Updating after code refactoring

## CRITICAL CONSTRAINTS

### Documentation Integrity

**MUST:**
- Document only existing or approved functionality
- Verify all code references resolve correctly
- Replace duplications with cross-references
- Maintain requirement ID stability (NEVER renumber)

**MUST NOT:**
- Document non-existent features (hallucinations)
- Copy content between documents
- Break cross-reference traceability
- Change requirement IDs

### Deprecation Handling Protocol

**Pre-1.0 projects:**
- Update requirements directly
- Simply remove or update outdated content
- No deprecation markers needed

**Post-1.0 projects - ASK USER:**
- STOP and use AskUserQuestion tool
- Present options: Deprecate (mark but keep) or Remove (delete)
- Wait for user decision
- Apply chosen approach

**Never remove post-1.0 requirements without user approval.**

## WORKFLOW

### Step 0: Parameter Validation

- If `scope` specified: Use specified scope
- If NO `scope`: Default to full maintenance
- If `scenario` specified: Tailor workflow accordingly

### Step 1: Load Requirements Standards

```
Skill: pm-requirements:requirements-maintenance
Skill: pm-requirements:requirements-documentation
Skill: pm-requirements:specification-documentation
```

This loads comprehensive requirements standards including:
- requirements-maintenance.md - Maintenance principles and integrity requirements
- requirements-documentation.md - Requirements creation patterns
- specification-documentation.md - Specification structure standards

**On load failure:** Report error and abort command.

### Step 2: Pre-Maintenance Discovery

**2.1 Identify Documents:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Locate requirements and specification documents
  prompt: |
    Locate all requirements and specification documents in project.
    Search for:
    - Requirements.adoc (typically in doc/)
    - Specification documents (typically in doc/specifications/)
    - Related documentation files

    Return structured list with paths.
```

**2.2 Load Maintenance Standards:**

Verify standards loaded from skills, confirm understanding of:
- SMART requirements principles
- Integrity requirements (no hallucinations, no duplications, verified links)
- Deprecation handling rules (pre-1.0 vs post-1.0)
- Traceability requirements

### Step 3: Requirements Analysis

**[If scope = "requirements" OR scope = "full"]**

**3.1 Analyze Requirements State:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Identify requirements maintenance needs
  prompt: |
    Analyze requirements documents for issues.
    Apply detection criteria from pm-requirements:requirements-maintenance skill:
    - Missing/incomplete requirements
    - Outdated references
    - Broken cross-references
    - Inconsistent terminology
    - Duplicate information
    - Integrity violations (hallucinations, unverified references)

    Return structured analysis by category with severity.
```

**3.2 Update Requirements:**

```
Task:
  subagent_type: Task
  description: Apply requirements updates
  prompt: |
    Update requirements following patterns from
    pm-requirements:requirements-documentation skill.

    Apply maintenance rules from pm-requirements:requirements-maintenance skill:
    - NEVER renumber requirement IDs
    - Ensure SMART compliance
    - Preserve rationale
    - Update status indicators
    - Maintain traceability

    CRITICAL: Document only existing or approved functionality.
```

**If scenario = "new-feature":** Follow new-feature documentation pattern from requirements-documentation skill.

**If scenario = "deprecation":** Apply deprecation handling protocol (check version, ask user for post-1.0).

**3.3 Verify Specification Alignment:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Check specification links
  prompt: |
    Verify requirements link to specifications correctly.
    Apply verification patterns from pm-requirements:requirements-maintenance skill:
    - Check xref: links resolve
    - Verify specifications exist
    - Confirm bidirectional traceability
    - Validate implementation references

    Return list of broken or missing links.
```

### Step 4: Specification Maintenance

**[If scope = "specifications" OR scope = "full"]**

**4.1 Analyze Specifications:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Identify specification maintenance needs
  prompt: |
    Analyze specification documents for issues.
    Apply detection criteria from pm-requirements:requirements-maintenance skill:
    - Alignment with requirements
    - Accurate implementation references
    - Complete behavioral descriptions
    - Valid cross-references

    Return structured analysis with locations.
```

**4.2 Update Specifications:**

```
Task:
  subagent_type: Task
  description: Apply specification updates
  prompt: |
    Update specifications following patterns from
    pm-requirements:specification-documentation skill.

    Apply maintenance rules:
    - Maintain linkage to requirements
    - Update implementation details
    - Preserve specification IDs
    - Keep examples current and valid

    CRITICAL: Verify all code references exist.
```

**If scenario = "refactoring":** Update implementation references following refactoring patterns from requirements-maintenance skill.

### Step 5: Cross-Reference Verification

**[If scope = "references" OR scope = "full"]**

**5.1 Verify Document Links:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Validate all xref: links
  prompt: |
    Verify all cross-references resolve correctly.
    Check:
    - xref: links point to existing sections
    - Paths are current after restructuring
    - Section IDs are correct
    - No references to deleted documents

    Return list of broken links with suggested fixes.
```

**5.2 Validate Code References:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Verify implementation references
  prompt: |
    Validate all code references in documentation.
    Use Grep to verify:
    - Referenced classes exist
    - Method signatures correct
    - Package names current
    - Line numbers accurate (if specified)

    Pattern: de\.cuioss\.[a-zA-Z.]+

    Return list of invalid references with corrections.
```

**CRITICAL:** All code references must resolve to existing code.

### Step 6: Integrity Verification

**6.1 Check for Hallucinations:**

```
For each requirement and specification:

1. Verify feature exists in code OR is in approved roadmap
2. Flag unverified documentation:
   - Requirements without implementation
   - Specifications describing non-existent behavior
   - Code references to non-existent elements

3. If unverified content found:
   - STOP maintenance process
   - Document the unverified content
   - ASK USER: "Is this documented feature planned or should it be removed?"
   - WAIT for user decision
```

**6.2 Eliminate Duplications:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Detect duplicate content
  prompt: |
    Identify duplicate information across documents.
    Apply detection patterns from pm-requirements:requirements-maintenance skill.

    For each duplication:
    - Identify canonical location
    - Suggest cross-reference replacement

    Return structured list of duplications with canonical sources.
```

Replace duplicates with xref: links to canonical location.

**6.3 Final Link Verification:**

Checklist:
- [ ] All xref: links resolve
- [ ] All code references verified
- [ ] All external links accessible
- [ ] No broken references remain

### Step 7: Quality Verification

Run comprehensive quality checklist from pm-requirements:requirements-maintenance skill:

```
Quality Verification:

- [ ] Cross-References Validated (all links work)
- [ ] No Duplicate Information (cross-references used)
- [ ] Consistent Terminology (same terms for same concepts)
- [ ] Clear Traceability Maintained (complete requirement-to-implementation chain)
- [ ] No Hallucinated Functionality (all features verified)
- [ ] Integrity Maintained (documentation reflects reality)
```

**If ANY check fails:** Document failure, fix issue, re-run verification.

### Step 8: Scenario-Specific Finalization

**[If scenario parameter provided]**

**If scenario = "new-feature":**
- Verify new requirements follow SMART principles
- Confirm specifications link to requirements
- Ensure traceability matrix updated

**If scenario = "deprecation":**
- Verify deprecation markers applied (if post-1.0 and user chose deprecate)
- OR confirm removals complete (if user chose remove)
- Check all references updated

**If scenario = "refactoring":**
- Verify all package/class name updates applied
- Confirm method signatures current
- Ensure examples compile with new structure

### Step 9: Commit Changes

**9.1 Review Changes:**

```
Bash: git status
Bash: git diff
```

Verify all changes are intentional and requirements-related.

**9.2 Create Commit:**

```
Bash: git add {affected files}
Bash: git commit -m "$(cat <<'EOF'
docs(requirements): [brief description of changes]

[Detailed description of maintenance performed]

- [Specific change 1]
- [Specific change 2]
- [Specific change 3]

Affected requirements: [list requirement IDs]
[Optional: Affected specifications: list spec IDs]
[Optional: Structural changes: describe]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Step 10: Display Summary

```
╔════════════════════════════════════════════════════════════╗
║       Requirements Maintenance Summary                     ║
╚════════════════════════════════════════════════════════════╝

Scope: {scope parameter value}
Scenario: {scenario parameter value if provided}

Requirements Reviewed: {count}
Requirements Updated: {list of IDs}
New Requirements Added: {count if any}
Requirements Deprecated/Removed: {count if any}

Specifications Reviewed: {count}
Specifications Updated: {list}
Implementation References Corrected: {count}

Cross-References Fixed:
- Broken document links: {count}
- Broken code references: {count}
- New cross-references added: {count}

Integrity Checks:
- Hallucinations resolved: {count}
- Duplications removed: {count}
- Links verified: {total count}

Quality Verification: All checks passed ✓
Commit Created: {commit hash} ✓

Time Taken: {elapsed_time}
```

## STATISTICS TRACKING

Track throughout workflow:
- `requirements_reviewed` / `requirements_updated` - Requirements processing
- `specifications_reviewed` / `specifications_updated` - Specifications processing
- `broken_links_fixed` - Cross-reference repairs
- `hallucinations_found` / `hallucinations_resolved` - Integrity issues
- `duplications_removed` - Content deduplication
- `scenario_specific_actions` - Scenario workflow steps
- `elapsed_time` - Total execution time

Display all statistics in final summary.

## ERROR HANDLING

**Unverified Documentation Found:**
1. Stop maintenance process
2. Document unverified content details
3. Ask user: "Is this documented feature planned or should it be removed?"
4. Wait for user decision
5. Proceed based on user choice

**Broken Links Cannot Be Fixed:**
1. Document broken link
2. Try to locate moved content
3. If found: Update link
4. If not found: Ask user for guidance
5. Remove link only with user approval

**Conflicting Information:**
1. Document both versions
2. Identify most authoritative source
3. Ask user which version is correct
4. Update to correct version
5. Replace duplicates with cross-references

## USAGE EXAMPLES

```
# Complete maintenance
/cui-maintain-requirements scope=full

# Requirements only
/cui-maintain-requirements scope=requirements

# New feature documentation
/cui-maintain-requirements scope=full scenario=new-feature

# Handle deprecation (will ask user for post-1.0)
/cui-maintain-requirements scope=full scenario=deprecation

# After refactoring
/cui-maintain-requirements scope=specifications scenario=refactoring
```

## ARCHITECTURE

Orchestrates agents and skills:
- **pm-requirements:requirements-maintenance skill** - Maintenance standards and integrity rules
- **pm-requirements:requirements-documentation skill** - Requirements creation patterns
- **pm-requirements:specification-documentation skill** - Specification structure standards
- **Explore agent** - Document analysis and issue identification
- **Task agent** - Requirements and specification updates
- **Grep** - Code reference verification

## RELATED

- `pm-requirements:requirements-maintenance` skill - Maintenance principles
- `pm-requirements:requirements-documentation` skill - Requirements patterns
- `pm-requirements:specification-documentation` skill - Specification patterns
- `/orchestrate-workflow` command - End-to-end issue implementation
- `/pr-handle-pull-request` command - PR workflow including documentation review
