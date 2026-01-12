# Specification-to-Code Linking Standards

Standards for linking from specification documents to implementation code, providing bidirectional navigation.

## Linking Format

**Java class references**:
```asciidoc
link:../src/main/java/com/example/TokenValidator.java[TokenValidator]
```

**Package references**:
```asciidoc
link:../src/main/java/com/example/jwt/[jwt package]
```

**Test references**:
```asciidoc
link:../src/test/java/com/example/TokenValidatorTest.java[TokenValidatorTest]
```

## Status Section Template

Use this template in specification documents to link to implementing code:

```asciidoc
== [Component Name]
_See Requirement link:../Requirements.adoc#REQ-ID[REQ-ID: Title]_

=== Status: [PLANNED|IN PROGRESS|IMPLEMENTED]

[For IMPLEMENTED] This specification is implemented in:
* link:../src/main/java/path/ClassName.java[ClassName] - Brief description

For detailed behavior, refer to the JavaDoc of implementing classes.

=== Verification
* link:../src/test/java/path/ClassNameTest.java[ClassNameTest]
```

## Status Indicators

**PLANNED**:
- Specification exists but no implementation started
- Contains detailed design and expected API

**IN PROGRESS**:
- Implementation has started
- Add links to implementing classes as they are created
- Update with implementation decisions

**IMPLEMENTED**:
- Full implementation complete
- Links to all implementing classes
- Links to verification tests
- Remove redundant code examples
- Keep architectural guidance and standards
