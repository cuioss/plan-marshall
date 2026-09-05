# Specification-to-Code Linking Standards

Standards for linking from specification documents to implementation code, providing bidirectional navigation.

> **Format note**: Link syntax examples below use AsciiDoc. For AsciiDoc link and cross-reference syntax, see `pm-documents:ref-asciidoc` → `references/asciidoc-formatting.md`. The linking concepts (status tracking, bidirectional navigation) apply regardless of document format.

## Linking Format

**Source file references**:
```asciidoc
link:../src/main/java/com/example/TokenValidator.java[TokenValidator]
link:../src/token_validator.py[token_validator]
link:../src/components/TokenValidator.ts[TokenValidator]
```

**Package/module references**:
```asciidoc
link:../src/main/java/com/example/jwt/[jwt package]
link:../src/jwt/[jwt module]
```

**Test references**:
```asciidoc
link:../src/test/java/com/example/TokenValidatorTest.java[TokenValidatorTest]
link:../tests/test_token_validator.py[test_token_validator]
link:../src/__tests__/TokenValidator.test.ts[TokenValidator.test]
```

Adapt paths to match the project's language and directory conventions.

## Status Section Template

Use this template in specification documents to link to implementing code:

```asciidoc
== [Component Name]
_See Requirement link:../Requirements.adoc#REQ-ID[REQ-ID: Title]_

=== Status: [PLANNED|IN PROGRESS|IMPLEMENTED]

[For IMPLEMENTED] This specification is implemented in:
* link:../path/to/ImplementingFile[ClassName/ModuleName] - Brief description

For detailed behavior, refer to the API documentation of implementing classes/modules.

=== Verification
* link:../path/to/TestFile[TestName]
```

## Status Indicators

**PLANNED**:
- Specification exists but no implementation started
- Contains detailed design and expected API

**IN PROGRESS**:
- Implementation has started
- Add links to implementing files as they are created
- Update with implementation decisions

**IMPLEMENTED**:
- Full implementation complete
- Links to all implementing files
- Links to verification tests
- Remove redundant code examples
- Keep architectural guidance and standards

**DEPRECATED**:
- Requirement no longer applicable
- Mark with `[DEPRECATED]` heading and reason
- Keep for historical traceability
