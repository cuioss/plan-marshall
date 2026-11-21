# Cross-Reference Maintenance

Standards for maintaining traceability links as implementation and specifications evolve.

## When Implementation Changes

If implementation significantly changes, follow this workflow:

1. **Update API documentation** with new behavior
   - Modify class/module and method/function documentation
   - Update code examples if present
   - Adjust implementation detail descriptions

2. **Review specification** for accuracy
   - Check if design assumptions still hold
   - Verify architectural guidance is current
   - Ensure links point to correct source files

3. **Update specification** if design changed
   - Document new architectural decisions
   - Update component relationships if needed
   - Adjust implementation guidance

4. **Verify tests** still cover requirements
   - Check test scenarios against new implementation
   - Identify gaps in coverage
   - Ensure requirement validation is complete

5. **Update test references** if tests changed
   - Update links in specification
   - Adjust coverage metrics
   - Document new test scenarios

## When Specifications Change

If specifications are updated, follow this workflow:

1. **Identify affected implementation**
   - Find all source files referenced in specification
   - Check for files implementing related requirements
   - Identify tests validating the specification

2. **Review implementation** for compliance
   - Verify code still meets updated specification
   - Check for conflicts with new requirements
   - Assess impact of specification changes

3. **Update implementation** if needed
   - Modify code to match new specification
   - Add features for new requirements
   - Remove obsolete functionality

4. **Update API documentation** with new references
   - Add new requirement IDs
   - Update specification links if file structure changed
   - Adjust implementation descriptions

5. **Update tests** to cover new requirements
   - Add test cases for new scenarios
   - Update test documentation
   - Recalculate coverage metrics

## Regular Maintenance

Periodically verify traceability integrity:

### Link Validation
- All specification links point to correct files
- All API documentation references are accurate
- Test references are complete
- No broken links exist

### Status Accuracy
- Implementation status indicators are current
- Status matches actual implementation state
- PLANNED/IN PROGRESS/IMPLEMENTED is correct
- Test coverage matches reported metrics

### Content Quality
- No redundant content exists
- Information is in appropriate location (spec vs API docs)
- Documentation provides value
- Cross-references are bidirectional

## Refactoring Impact

### When Moving/Renaming Source Files

**Actions required**:
1. Update specification links to new file locations
2. Verify API documentation relative paths still work
3. Update test references
4. Check for broken cross-references

**Tool support**:
- Use IDE refactoring tools when possible
- Validate links after refactoring
- Run link checker if available

### When Restructuring Specifications

**Actions required**:
1. Update all API documentation links to specifications
2. Update internal cross-references in specs
3. Verify requirement ID references are current
4. Check test file specification links

**Best practices**:
- Update links immediately after restructuring
- Don't defer link updates to later
- Test navigation paths after changes

## Maintenance Rules

Run this checklist quarterly or after major changes:

**Specification Review**:
- All IMPLEMENTED specifications have source file links
- All IMPLEMENTED specifications have test links
- Status indicators match implementation state
- Coverage metrics are current

**Code Review**:
- All implementation files have specification references
- All test files reference specifications
- Requirement IDs are accurate
- Relative paths are correct

**Link Validation**:
- Run link checker on documentation
- Manually verify critical links
- Check for 404s or moved files
- Validate bidirectional navigation
