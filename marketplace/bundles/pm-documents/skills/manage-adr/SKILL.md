---
name: manage-adr
description: Manage Architectural Decision Records (ADRs) with CRUD operations, automatic numbering, and AsciiDoc formatting
user-invocable: false
---

# ADR Management Skill

## Enforcement

**Execution mode**: Select workflow and execute immediately using documented script commands.

**Prohibited actions:**
- Do not invoke scripts with arguments other than those documented in workflow steps
- Do not skip confirmation steps for delete operations
- Do not create ADRs without automatic numbering via the create workflow

**Constraints:**
- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr ...`
- Always validate ADR format after creation or update using ref-asciidoc
- ADRs must be stored in `doc/adr/` directory

---

Manage Architectural Decision Records (ADRs) stored in `doc/adr/` directory.

## Purpose

Provide structured management of architectural decisions:

- **Create** ADRs with automatic numbering and template
- **Read** ADR content by number
- **Update** ADR status through lifecycle
- **Delete** ADRs when necessary
- **List** all ADRs with optional filtering
- **Validate** ADR format using ref-asciidoc

## Available Workflows

| Workflow | Purpose | Script Used |
|----------|---------|-------------|
| **list-adrs** | List all ADRs with optional filtering | `manage-adr.py list` |
| **create-adr** | Create new ADR from template | `manage-adr.py create` |
| **read-adr** | Read ADR content | `manage-adr.py read` |
| **update-adr** | Update ADR status | `manage-adr.py update` |
| **delete-adr** | Delete ADR (with confirmation) | `manage-adr.py delete` |
| **validate-adr** | Validate ADR format | ref-asciidoc workflows |

## Workflow: list-adrs

List all ADRs with optional status filtering.

### Parameters

- `status` (optional): Filter by status (Proposed, Accepted, Deprecated, Superseded)

### Steps

**Step 1: Execute List**

```bash
python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr list [--status {status}]
```

**Step 2: Parse Output**

Parse TOON output containing ADR list with metadata.

### Output

```toon
status: success
operation: list
count: 2
adrs[2]{number,title,status,path}:
1,Use PostgreSQL,Accepted,doc/adr/001-Use_PostgreSQL.adoc
2,Adopt Quarkus,Proposed,doc/adr/002-Adopt_Quarkus.adoc
```

## Workflow: create-adr

Create a new ADR with automatic numbering.

### Parameters

- `title` (required): ADR title
- `status` (optional, default: "Proposed"): Initial status

### Steps

**Step 1: Create ADR**

```bash
python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr create --title "{title}" [--status "{status}"]
```

**Step 2: Parse Output**

Extract created file path from TOON output.

**Step 3: Open for Editing**

Read the created file and inform user to fill in content sections.

**Step 4: Validate Format**

```
Skill: pm-documents:ref-asciidoc
Execute workflow: validate-format
Parameters:
  target: {created_path}
```

### Output

```
ADR Created: doc/adr/004-{title}.adoc
Number: ADR-004
Status: Proposed

Next steps:
1. Edit doc/adr/004-{title}.adoc to fill in:
   - Context
   - Decision
   - Consequences
   - Alternatives
2. Update status to "Accepted" when approved
```

## Workflow: read-adr

Read ADR content by number.

### Parameters

- `number` (required): ADR number (1, 2, 3, etc.)

### Steps

**Step 1: Read ADR**

```bash
python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr read --number {number}
```

**Step 2: Display Content**

Show ADR metadata and content to user.

## Workflow: update-adr

Update ADR status through lifecycle.

### Parameters

- `number` (required): ADR number
- `status` (required): New status (Proposed, Accepted, Deprecated, Superseded)

### Steps

**Step 1: Update ADR**

```bash
python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr update --number {number} --status {status}
```

**Step 2: Confirm Update**

Report updated status to user.

## Workflow: delete-adr

Delete ADR with confirmation.

### Parameters

- `number` (required): ADR number
- `force` (required): Must be true to confirm deletion

### Steps

**Step 1: Delete ADR**

```bash
python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr delete --number {number} --force
```

**Step 2: Confirm Deletion**

Report deletion to user.

## Workflow: validate-adr

Validate ADR format using ref-asciidoc skill.

### Parameters

- `number` (required): ADR number to validate

### Steps

**Step 1: Find ADR Path**

Use list-adrs workflow to get ADR path by number.

**Step 2: Validate Format**

```
Skill: pm-documents:ref-asciidoc
Execute workflow: validate-format
Parameters:
  target: {adr_path}
```

**Step 3: Report Results**

Report validation results to user.

## Integration with ref-asciidoc

This skill integrates with `ref-asciidoc` for:

- **Format validation**: Ensures AsciiDoc formatting compliance
- **Link verification**: Validates cross-references
- **Content review**: Reviews ADR content quality

## ADR Lifecycle

```
Proposed → Accepted → [Deprecated | Superseded]
```

| Status | Meaning |
|--------|---------|
| Proposed | Under discussion, not yet approved |
| Accepted | Approved and active |
| Deprecated | No longer relevant or applicable |
| Superseded | Replaced by another ADR |

## ADR Template Structure

Each ADR contains these sections:

1. **Status** - Current lifecycle status
2. **Context** - Problem context and background
3. **Decision** - The architectural decision made
4. **Consequences** - Positive, negative outcomes and risks
5. **Alternatives Considered** - Options that were not chosen
6. **References** - Related documents and links

## Authoring Discipline

ADRs are **durable architectural statements**, not incident write-ups. An ADR should still read as a standalone decision record years after the PR that introduced it has scrolled out of memory and the lessons file referenced at write-time has been pruned. CLAUDE.md's project-wide rules — "no version history", "no timestamps", "no duplication", "current state only" — apply to ADR content in the section-specific shapes below.

### Context

- Describe the architectural problem **as a class**, not as an incident narrative.
- State the failure modes the architecture has to handle and the structural choice point those failure modes create. Do NOT recount "PR #N introduced X, the AST walker missed Y" — that's incident history, not the class of problem.
- A reader who has never seen the originating bug should still understand why the question this ADR settles is worth settling.

### Decision

- State the principle in plain language; if a one-line statement of the principle exists, lead with it.
- Describe the mechanisms that realise the decision. Name the concrete artefacts (skills, scripts, rules) but describe them in terms of the contract they enforce, not the commit that introduced them.

### Consequences

- Phrase consequences as **properties of the resulting architecture**, not as "what changed in PR #N".
- "Positive / Negative / Risks" describe the steady-state behaviour the decision produces, including the residual failure modes the decision deliberately accepts.

### Alternatives Considered

- Each alternative describes the **architectural option on its merits** — what shape the alternative would impose, what it would solve, what it would cost.
- The "Rejected because" prose explains the architectural failure of the alternative, not which option shipped when.
- A summary paragraph at the end may state the principle that unifies why the alternatives fall in one class.

### Generalisation (optional)

- When the decision is an instance of a broader pattern, a Generalisation section may state the pattern independently of this codebase: name the underlying abstraction, the diagnostic question, the place each answer belongs.
- The generalisation must not name project-internal artefacts. A reader from a different project should be able to apply it.

### References

- Link to **other ADRs**, durable architecture docs, and the canonical skill / standards files the decision affects.
- Do NOT link to PR numbers, commit SHAs, or lesson IDs.
  - PRs and commits are git-history artefacts; the durable address of the change is the artefact it produced (the skill, the script, the rule), not the merge commit.
  - Lessons (`.plan/local/lessons-learned/...`) are ephemeral recurrence-detectors and may be pruned, retired, or superseded; an ADR that cross-references a specific lesson ID can develop a dangling reference. When the lesson is the recurrence-detector that ENFORCES the ADR's principle at retrospective time, link the durable artefact (the retrospective rule, the plugin-doctor check) instead.
- Date-free phrasing: the ADR's own header carries the decision date implicitly via the ADR number's position in the sequence; section bodies should not restate or anchor to dates.

### What goes into a lesson instead

Lessons capture **the recurrence pattern the ADR's principle defends against** — the diagnostic signature a future maintainer might see that should remind them of the ADR's guidance. Lessons are explicitly ephemeral; ADRs are durable. If a piece of prose is "we hit this bug, watch for the pattern", it belongs in a lesson. If it's "the architecture is X because alternatives Y/Z fail in ways A/B", it belongs in the ADR.

## File Naming Convention

ADRs follow this naming pattern:

```
doc/adr/{NNN}-{Title_With_Underscores}.adoc
```

Examples:
- `doc/adr/001-Use_PostgreSQL_for_Persistence.adoc`
- `doc/adr/002-Adopt_Quarkus_Framework.adoc`
- `doc/adr/003-Implement_CQRS_Pattern.adoc`

## Scripts

Script: `pm-documents:manage-adr` → `manage-adr.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List all ADRs with optional status filtering |
| `create` | Create new ADR from template with automatic numbering |
| `read` | Read ADR content by number |
| `update` | Update ADR status through lifecycle |
| `delete` | Delete ADR (requires --force) |

**Usage Examples:**
```bash
# List all ADRs
python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr list

# Create new ADR
python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr create --title "Use PostgreSQL"

# Update ADR status
python3 .plan/execute-script.py pm-documents:manage-adr:manage-adr update --number 1 --status Accepted
```

## Related Skills

- `pm-documents:ref-asciidoc` - Format validation
