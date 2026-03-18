# pm-dev-frontend-cui

CUI-specific JavaScript project standards bundle providing opinionated patterns for CUI Open Source projects.

## Overview

This bundle contains CUI project-specific standards that complement the general JavaScript standards in `pm-dev-frontend`. Use this bundle when developing CUI projects that use Maven + npm dual build systems.

## Skills

### cui-javascript-project
JavaScript project structure, package.json configuration, dependency management, and Maven integration standards.

**Key patterns:**
- Directory layouts for Maven-based JavaScript projects
- frontend-maven-plugin integration
- SonarQube configuration for JavaScript
- Quarkus DevUI and NiFi project types

**Script**: `pm-dev-frontend-cui:cui-javascript-project` -> `npm-output.py` (npm build output parser)

### plan-marshall-plugin
Domain manifest declaring the `javascript-cui` domain for plan-marshall workflow integration.

## Usage

Load skills based on project needs:

```yaml
# CUI JavaScript project
skills:
  # General (from pm-dev-frontend)
  - pm-dev-frontend:javascript
  - pm-dev-frontend:js-enforce-eslint
  # CUI-specific (from this bundle)
  - pm-dev-frontend-cui:cui-javascript-project
```

## Dependencies

This bundle complements `pm-dev-frontend` and should be used together with it:
- General JavaScript standards: `pm-dev-frontend`
- CUI-specific standards: `pm-dev-frontend-cui` (this bundle)
