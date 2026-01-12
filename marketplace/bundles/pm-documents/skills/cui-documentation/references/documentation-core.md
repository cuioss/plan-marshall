# Documentation Core Standards

## Purpose

Comprehensive standards for all documentation across CUI projects, including general documentation rules and principles. This document serves as the foundation for all CUI documentation standards.

## Documentation Standards Overview

The CUI documentation standards are organized into focused documents covering specific aspects:

* **[documentation-core.md](documentation-core.md)** (this document) - Core principles, terminology, and code examples
* **[tone-and-style.md](tone-and-style.md)** - Professional tone, neutral language, prohibited patterns, and writing style
* **[organization-standards.md](organization-standards.md)** - File organization, naming conventions, size guidelines, and review processes
* **[asciidoc-formatting.md](asciidoc-formatting.md)** - AsciiDoc formatting, grammar, cross-references, and validation
* **[readme-structure.md](readme-structure.md)** - Standard structure for README files

**When to Use Which Document:**

* **Creating/editing any documentation** → Start with this document (documentation-core.md)
* **Reviewing tone and language** → Use [tone-and-style.md](tone-and-style.md)
* **Organizing/restructuring documents** → Use [organization-standards.md](organization-standards.md)
* **Formatting AsciiDoc files** → Use [asciidoc-formatting.md](asciidoc-formatting.md)
* **Creating README files** → Use [readme-structure.md](readme-structure.md)

## Key Principles

1. **Consistency**: All documentation follows the same patterns and conventions
2. **Completeness**: Documentation covers all necessary aspects of the code
3. **Clarity**: Documentation is clear and understandable
4. **Maintainability**: Documentation is easy to update and maintain

## Core Documentation Standards

### Tone and Style Requirements

**See tone-and-style.md for complete guidance** on:
* Professional tone and neutral language requirements
* Marketing language detection and prohibited patterns
* Writing style and analysis guidelines

### General Principles

* Only document existing code elements - no speculative or planned features
* All references must be verified to exist
* Use linking instead of duplication
* Code examples must come from actual unit tests
* Use consistent terminology across all documentation
* All public APIs must be documented
* All changes require successful documentation build

### Terminology Standards

* Maintain consistent technical terminology across all documentation types
* Follow project glossary and naming conventions

### Code Example Requirements

#### Technical Requirements

* Must be complete and compilable
* Include all necessary imports
* Show proper error handling
* Follow project coding standards
* Be verified by unit tests

#### Structure Requirements

* Start with setup/configuration
* Show main functionality
* Include error handling
* Demonstrate cleanup if needed
* Use clear variable names
* Include comments for complex steps

#### Configuration Examples - Placeholder Identification

**Requirements**:
* ALL placeholders must be clearly identified
* Use inline comments to mark placeholders
* Provide example values alongside placeholders

**Example (GOOD)**:
```properties
# Replace with your issuer URL
oauth.issuer=https://your-auth-server.com  # Placeholder: your actual auth server
oauth.audience=your-api-id                  # Placeholder: your API identifier
```

**Example (BAD)**:
```properties
oauth.issuer=https://your-auth-server.com
oauth.audience=your-api-id
```

## Documentation Quality

### Review Checklist

- [ ] Professional tone maintained
- [ ] No marketing language
- [ ] All references verified
- [ ] Code examples complete
- [ ] Consistent terminology
- [ ] Public APIs documented
- [ ] Documentation builds successfully

## References

See "Documentation Standards Overview" section at the top of this document for complete list of related standards files and their purposes.
