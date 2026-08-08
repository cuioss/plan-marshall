# Documentation Suppression Syntax

How to suppress various types of findings in documentation files.

## AsciiDoc Suppression

### Inline Comment Suppression

```asciidoc
// asciidoc-lint-disable: rule-name
This line has an intentional format exception.
```

### Block Suppression

```asciidoc
////
asciidoc-lint-disable-block: multiple-rules
Reason: Code example with intentional formatting
////
[source,java]
----
// Example code that triggers lint rules
----
```

### Attribute-Based Suppression

```asciidoc
:asciidoc-lint-skip: heading-format,list-indent
```

## Link Check Suppression

### Single Link

```asciidoc
// skip-link-check: reason
link:internal://private-docs[Internal Only]
```

### Block of Links

```asciidoc
// skip-link-check-start: external links to partner sites
* link:https://partner1.example.com[Partner 1]
* link:https://partner2.example.com[Partner 2]
// skip-link-check-end
```

## Markdown Suppression

### Single Rule

```markdown
<!-- markdownlint-disable MD001 -->
# Heading that intentionally skips a level
<!-- markdownlint-enable MD001 -->
```

### Multiple Rules

```markdown
<!-- markdownlint-disable MD001 MD013 -->
Content with intentional format exceptions.
<!-- markdownlint-enable MD001 MD013 -->
```

### File-Level

Add to the top of the file:

```markdown
<!-- markdownlint-disable-file MD001 -->
```

## ADR Format Exceptions

For ADRs with legacy or non-standard format:

```asciidoc
= ADR-042: Legacy Decision
:status: Accepted
:date: 2020-01-15
:format-exception: Pre-standard ADR, imported from wiki

== Context
...
```

## Best Practices

### Always Include Justification

```asciidoc
// Good - explains why
// asciidoc-lint-disable: heading-format - Legacy import from wiki, tracked in DOC-123

// Bad - no explanation
// asciidoc-lint-disable: heading-format
```

### Prefer Fixing to Suppressing

Fix issues when:
- The fix is low effort
- The document is actively maintained
- The issue affects readability

### Scope Minimally

```asciidoc
// Good - inline suppression for single line
// asciidoc-lint-disable: list-format
* Non-standard list item

// Less ideal - file-wide suppression
:asciidoc-lint-skip-all: true
```

## Cross-Reference Exceptions

For intentionally broken cross-references (e.g., future documents):

```asciidoc
// Future document - skip validation
See xref:planned/future-spec.adoc[Future Specification] (planned for v2.0)
```

## When NOT to Suppress

- Broken internal xref links (fix the reference or remove it)
- Missing required ADR sections (fix the ADR)
- Unparseable AsciiDoc syntax (fix the syntax)
- Duplicate anchor IDs (rename one)
