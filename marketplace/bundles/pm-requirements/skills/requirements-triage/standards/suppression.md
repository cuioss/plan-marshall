# Requirements Suppression Syntax

How to suppress various types of findings in requirements documents.

## AsciiDoc Comment Suppression

The primary mechanism for suppressing warnings in AsciiDoc requirements documents.

### Inline Comments

```asciidoc
// asciidoc-lint-disable: rule-name
[REQ-001] This requirement has an intentional format exception.
```

### Block Comments

```asciidoc
////
asciidoc-lint-disable-block: rule-name
Reason: Legacy format from imported requirements
////
[REQ-LEGACY-001]:: Imported requirement with non-standard format
```

## Link Check Suppression

For external links that should not be validated:

```asciidoc
// skip-link-check: internal-only
See internal documentation at link:internal://docs/spec[Internal Spec]
```

## Traceability Exception

When a requirement intentionally lacks traceability:

```asciidoc
[REQ-META-001]
.Meta-Requirement (No Implementation Traceability)
****
This requirement describes documentation standards, not system behavior.
No implementation traceability required.
****
```

## Best Practices

### Always Include Justification

```asciidoc
// Good - explains why suppression is appropriate
// asciidoc-lint-disable: heading-format - Legacy import, tracked in REQ-MIGRATE-001
= Non-Standard Heading

// Bad - no explanation
// asciidoc-lint-disable: heading-format
= Non-Standard Heading
```

### Scope Minimally

Apply suppression to specific requirements, not entire documents:

```asciidoc
// Good - scoped to single requirement
// asciidoc-lint-disable: format-check
[REQ-LEGACY-001]:: Legacy format requirement

// Less ideal - document-wide suppression
:asciidoc-lint-disable-all: true
```

## When NOT to Suppress

- Missing required fields (fix instead)
- Broken internal references (fix instead)
- Duplicate requirement IDs (fix instead)
- Acceptance criteria without testable conditions (fix instead)
