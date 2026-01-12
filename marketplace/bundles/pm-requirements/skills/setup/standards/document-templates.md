# Document Templates

Standard templates for initial requirements documentation in CUI projects.

[[requirements-template]]
## Requirements.adoc Template

```asciidoc
= [Project Name] Requirements
:toc: left
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js

== Overview

This document outlines the requirements for [Project Name], a [brief description of what the project is and does].

Project prefix: `[PREFIX]-`

== General Requirements

[#PREFIX-1]
=== PREFIX-1: Project Overview

* [High-level project requirement 1]
* [High-level project requirement 2]
* [High-level project requirement 3]

[#PREFIX-2]
=== PREFIX-2: Core Functionality

* [Core functionality requirement 1]
* [Core functionality requirement 2]
* [Core functionality requirement 3]

== Functional Requirements

[#PREFIX-3]
=== PREFIX-3: [Feature/Component Name]

* [Specific functional requirement 1]
* [Specific functional requirement 2]

[#PREFIX-3.1]
==== PREFIX-3.1: [Sub-feature Name]

* [Detailed requirement 1]
* [Detailed requirement 2]

== Non-Functional Requirements

[#PREFIX-4]
=== PREFIX-4: Performance Requirements

* [Performance requirement 1]
* [Performance requirement 2]

[#PREFIX-5]
=== PREFIX-5: Security Requirements

* [Security requirement 1]
* [Security requirement 2]

[#PREFIX-6]
=== PREFIX-6: Logging Requirements

* [Logging requirement 1]
* [Logging requirement 2]
```

[[specification-template]]
## Specification.adoc Template

```asciidoc
= [Project Name] Specification
:toc: left
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js

== Overview
_See Requirement link:Requirements.adoc#PREFIX-1[PREFIX-1: Project Overview]_

This document provides the technical specification for implementing [Project Name].
For functional requirements, see link:Requirements.adoc[Requirements Document].

== Document Structure

This specification is organized into the following documents:

* link:specification/technical-components.adoc[Technical Components] - Core implementation details and architecture
* link:specification/configuration.adoc[Configuration] - Configuration properties and management
* link:specification/error-handling.adoc[Error Handling] - Error handling implementation and exception design
* link:specification/testing.adoc[Testing] - Unit and integration testing approach
* link:specification/security.adoc[Security] - Security considerations and implementation
* link:specification/integration-patterns.adoc[Integration Patterns] - Integration examples and patterns
* link:specification/internationalization.adoc[Internationalization] - i18n/l10n implementation

Additional documentation:

* link:LogMessages.adoc[Log Messages] - Logging standards and implementation
```

[[individual-specification-template]]
## Individual Specification Template

```asciidoc
= [Project Name] [Component Name]
:toc: left
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js

link:../Specification.adoc[Back to Main Specification]

== Overview
_See Requirement link:../Requirements.adoc#PREFIX-N[PREFIX-N: Requirement Title]_

This document specifies the [component name] implementation for [Project Name].

== [Section 1 Title]
_See Requirement link:../Requirements.adoc#PREFIX-N.1[PREFIX-N.1: Sub-requirement Title]_

[Content describing the specification details]

=== Design Approach

[High-level design approach and rationale]

=== Key Components

[Description of key components and their relationships]

=== Implementation Guidance

[Specific guidance for implementation]

== [Section 2 Title]
_See Requirement link:../Requirements.adoc#PREFIX-M[PREFIX-M: Another Requirement]_

[Additional specification content]
```

[[logmessages-template]]
## LogMessages.adoc Template

```asciidoc
= [Project Name] Log Messages
:toc: left
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js

link:Specification.adoc[Back to Main Specification]

== Overview
_See Requirement link:Requirements.adoc#PREFIX-6[PREFIX-6: Logging Requirements]_

This document defines the log messages for [Project Name] following CUI logging standards.

== Logging Standards

All log messages must follow the CUI logging standards:

* Use LogRecords pattern for structured logging
* Include appropriate log levels (ERROR, WARN, INFO, DEBUG, TRACE)
* Provide meaningful log keys and messages
* Support internationalization where appropriate

== Log Message Definitions

=== Error Messages

==== PREFIX_ERROR_001: [Error Description]

* *Level*: ERROR
* *Message*: [Error message template]
* *Usage*: [When this error is logged]
* *Parameters*: [Any dynamic parameters]

=== Warning Messages

==== PREFIX_WARN_001: [Warning Description]

* *Level*: WARN
* *Message*: [Warning message template]
* *Usage*: [When this warning is logged]
* *Parameters*: [Any dynamic parameters]

=== Info Messages

==== PREFIX_INFO_001: [Info Description]

* *Level*: INFO
* *Message*: [Info message template]
* *Usage*: [When this info is logged]
* *Parameters*: [Any dynamic parameters]
```
