# Documentation Sources

Priority order for documentation sources when analyzing project architecture.

## Project-Level Sources

Sources for understanding overall project structure and purpose.

| Priority | Source | Path Pattern | Content Type |
|----------|--------|--------------|--------------|
| 1 | Project README | `README.md`, `README.adoc` | Project overview, getting started |
| 2 | Architecture docs | `doc/architecture/*.adoc` | Architectural decisions, design |
| 3 | Module overview | `doc/modules.adoc` | Module relationships |
| 4 | ADR documents | `doc/adr/*.adoc` | Design decisions |

## Module-Level Sources

Sources for understanding individual module purpose and implementation.

| Priority | Source | Path Pattern | Content Type |
|----------|--------|--------------|--------------|
| 1 | Module README | `{module}/README.md` | Module overview |
| 2 | Package info | `{module}/src/main/java/**/package-info.java` | Package JavaDoc |
| 3 | Main class | Entry point class(es) | Implementation patterns |
| 4 | Test classes | `{module}/src/test/**/*Test.java` | Usage examples |

## Reading Strategy

### Project-Level Analysis

1. Start with `README.md` - often has architecture overview
2. Check `doc/` directory for detailed documentation
3. Review ADRs for design decisions that affect structure

### Module-Level Analysis

1. Check module README first - quickest understanding
2. Read `package-info.java` for Java modules
3. Sample 2-3 main source files for actual patterns
4. Check test files for usage examples

## Missing Documentation Handling

When documentation is absent:

| Missing Source | Fallback Strategy |
|----------------|-------------------|
| Module README | Analyze source code directly |
| package-info.java | Use directory structure and class names |
| All docs | Infer from: parent module context, imports, annotations |

## Content Extraction

### From README Files

Look for:
- First paragraph (module purpose)
- "Overview" or "Description" section
- Code examples (show usage patterns)

### From package-info.java

Look for:
- Package-level JavaDoc comment
- @see references to related packages
- Links to documentation

### From Source Files

Look for:
- Class-level JavaDoc
- Framework annotations (`@Path`, `@Processor`, etc.)
- Import statements (show dependencies)
- Method signatures (show capabilities)

## Output Integration

Documentation findings feed into `llm-enriched.json`:

| Documentation Finding | Target Field |
|----------------------|--------------|
| Module purpose statement | `modules.{name}.responsibility` |
| Module classification | `modules.{name}.purpose` |
| Package descriptions | `modules.{name}.key_packages.{pkg}.description` |
| Important dependencies | `modules.{name}.key_dependencies` |
| Framework/library usage | `modules.{name}.skills_by_profile` |

See [architecture-persistence.md](architecture-persistence.md) for complete schema.
