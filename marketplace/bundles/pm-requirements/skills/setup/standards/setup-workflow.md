# Setup Workflow

Step-by-step workflow for establishing requirements documentation in new CUI projects.

## Setup Process

### Step 1: Create Directory Structure

```bash
mkdir -p doc/specification
```

See [Directory Structure Standards](directory-structure.md) for complete directory layout standards.

### Step 2: Select Requirement Prefix

- Analyze project domain
- Choose from recommended prefixes or create custom
- Document prefix selection

See [Prefix Selection Standards](prefix-selection.md) for detailed prefix selection guidance.

### Step 3: Create Requirements.adoc

- Start from template
- Replace `[Project Name]` with actual project name
- Replace `PREFIX` with selected prefix
- Fill in initial requirements based on project scope

See [Requirements Template](document-templates.md#requirements-template) for template.

### Step 4: Create Specification.adoc

- Start from template
- Update project name and prefix
- Adjust specification document list based on project needs
- Add backtracking links to requirements

See [Specification Template](document-templates.md#specification-template) for template.

### Step 5: Create Individual Specification Documents

- Create files in `doc/specification/`
- Use template structure
- Add backtracking links to requirements
- Fill in specification details as available

See [Individual Specification Template](document-templates.md#individual-specification-template) for template.

### Step 6: Create LogMessages.adoc

- Start from template
- Define initial log message structure
- Reference logging standards

See [LogMessages Template](document-templates.md#logmessages-template) for template.

### Step 7: Verify Structure

- Check all files are in correct locations
- Verify all cross-references work
- Ensure consistent prefix usage
- Test document navigation

See [Quality Checklist](quality-checklist.md) for complete verification checklist.

## Common Setup Issues

### Incorrect Paths in Cross-References

**Problem**: Links break when documents are in subdirectories

**Solution**: Use correct relative paths:
- From `doc/specification/`: `../Requirements.adoc#REQ-1`
- From `doc/`: `Requirements.adoc#REQ-1`

### Inconsistent Prefix Usage

**Problem**: Requirements use different prefixes within same document

**Solution**: Establish single prefix at project start, use consistently

### Missing Backtracking Links

**Problem**: Specification sections don't reference requirements

**Solution**: Add backtracking link to every major specification section

### Skipping Initial Documentation

**Problem**: Starting implementation without requirements and specifications

**Solution**: Create at least minimal requirements and specification structure before coding
