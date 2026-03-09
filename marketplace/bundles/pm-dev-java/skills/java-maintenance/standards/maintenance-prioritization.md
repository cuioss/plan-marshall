# Maintenance Prioritization Framework

For general prioritization principles (high/medium/low priority categories, decision tree), see `pm-dev-general:dev-code-quality` refactoring-triggers.md. This document covers Java-specific maintenance priorities.

## Java-Specific High Priority

### API Contract Issues (Java-Specific)

- Missing `@NonNull` / `@Nullable` annotations on public APIs (see `pm-dev-java:java-null-safety`)
- Inconsistent null safety patterns (`@NullMarked` package-level config)
- Missing or wrong `@throws` declarations in JavaDoc

## Java-Specific Medium Priority

### Modern Java Adoption

**Characteristics**:
- Code works but uses outdated patterns
- Opportunities for simplification
- Improve code clarity
- Reduce boilerplate

**Examples**:
- Legacy switch statements (should use switch expressions)
- Verbose object creation patterns (should use records)
- Missing use of records for data carriers
- Underutilized stream operations

**Why Medium Priority**:
- Non-breaking improvements
- Incremental adoption possible
- Improve readability
- Reduce maintenance burden

### Code Cleanup

- Unused private fields and methods
- Dead code elimination (with user approval)
- Commented-out code removal

## Workflow Integration

After identifying violations:

1. **Categorize** by violation type (general via `pm-dev-general:dev-code-quality`, Java-specific here)
2. **Assign priority** using this framework and general prioritization
3. **Execute** systematically within each priority band
4. **Verify** using compliance-checklist.md

## Related Standards

- refactoring-triggers.md - Java-specific detection criteria
- compliance-checklist.md - Verification after fixes applied
- `pm-dev-general:dev-code-quality` - General prioritization and refactoring triggers
