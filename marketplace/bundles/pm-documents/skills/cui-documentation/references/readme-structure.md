# README Structure Standards

## Purpose
Standard structure for module README.adoc files in CUI projects to ensure consistency and completeness.

## Structure Requirements

### Title and Brief Description

* Module name as title (level 1 heading)
* Concise description of purpose and key functionality
* High-level overview of module's role in the system

### Maven Coordinates

* Must be placed immediately after description
* Complete dependency block in XML format
* Include group and artifact IDs

```xml
<dependency>
    <groupId>group.id</groupId>
    <artifactId>artifact-id</artifactId>
</dependency>
```

### Core Concepts

* Key architectural components
* Main features and capabilities
* Integration points
* Each concept with bullet points for details
* Links to source files where appropriate

### Detailed Component Documentation

* Each major component with its own section
* Links to source code files (Java, JavaScript, etc.): `link:path/to/file.java[ComponentName]`
* Links to AsciiDoc documentation files: `xref:path/to/file.adoc[Title]`
* Feature lists and capabilities
* Technical details and requirements
* Implementation considerations

### Usage Examples

* Complete, working code examples
* Common use cases
* Configuration examples
* Best practice implementations
* Each example must have:
  * Clear purpose explanation
  * Complete code snippet
  * Configuration if required
  * Expected outcome

### Configuration

* Available configuration options
* Property examples
* Configuration hierarchy
* Default values and fallbacks
* Environment-specific configurations

### Best Practices

* Implementation guidelines
* Performance considerations
* Security aspects
* Common pitfalls to avoid
* Recommended patterns

### Technical Details

* Thread safety considerations
* Memory impact
* Performance characteristics
* Implementation notes
* Dependencies and requirements

### Related Documentation

* Links to specifications
* Related projects
* Additional resources
* External documentation

## Style Guidelines

### Formatting

* Use asciidoc syntax consistently
* Maintain proper heading hierarchy
* Use code blocks with language specification
* Include line breaks between sections

### Code Examples

For complete code example requirements, see **documentation-core.md** section "Code Example Requirements".

README-specific considerations:
* Keep examples concise and focused on the feature being demonstrated
* Show configuration where relevant

### Links

* Use relative paths for internal links
* Use absolute URLs for external resources
* Link to source code files (.java, .js, etc.) using `link:` syntax
* Link to AsciiDoc files (.adoc) using `xref:` syntax
* Verify all links are valid

### Configuration Examples

* Show all relevant properties
* Include default values
* Demonstrate override patterns
* Document configuration hierarchy

## Example Structure

```asciidoc
= Module Name

Concise description of the module's purpose and key features.

== Maven Coordinates

[source, xml]
----
<dependency>
    <groupId>group.id</groupId>
    <artifactId>artifact-id</artifactId>
</dependency>
----

== Core Concepts

=== Feature One

* Capability details
* Integration points
* Key benefits

== Usage Examples

=== Basic Usage
[source,java]
----
// Complete code example
----

== Configuration

=== Property Configuration
[source,properties]
----
# Configuration examples
----

== Best Practices

* Guideline one
* Guideline two

== Technical Details

* Thread safety notes
* Performance characteristics

== Related Documentation

* link:url[External Resource]
```

## Table of Contents Guidelines

### AsciiDoc TOC Configuration

* Use the built-in AsciiDoc TOC mechanism instead of manual TOC creation
* README files use `:toc: macro` for manual TOC placement
* Add required attributes to document header:

```asciidoc
= Document Title
:toc: macro
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js
```

* Place the TOC macro `toc::[]` after introduction sections and before main content

### Excluding Sections from TOC

* Use the `[.discrete]` attribute for sections that should not appear in the TOC

```asciidoc
[.discrete]
== Status

Project status badges and links
```

* Typically exclude status badges, build information, and other metadata sections

### TOC Structure Best Practices

* Limit TOC to 3 levels for readability
* Use section numbering only for main content sections
* Ensure logical grouping of related topics
* Place Migration Guide and similar reference sections at the end
* Keep TOC focused on substantive documentation sections

## References

* [documentation-core.md](documentation-core.md) - Core documentation principles
* [asciidoc-formatting.md](asciidoc-formatting.md) - AsciiDoc formatting standards
* [tone-and-style.md](tone-and-style.md) - Professional tone requirements
* [organization-standards.md](organization-standards.md) - Organization and structure
