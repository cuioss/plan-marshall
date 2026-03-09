# General Development Principles

Cross-cutting development standards bundle providing language-agnostic principles for testing, documentation, and code quality.

## Purpose

This bundle extracts general development principles that apply across all technology stacks. Technology-specific bundles (pm-dev-java, pm-dev-frontend) focus on language-specific APIs and tooling, referencing these general skills for foundational principles.

## Architecture

```
pm-dev-general/
└── skills/                  # 3 reference skills
    ├── dev-testing/         # Testing methodology, AAA, coverage
    ├── dev-documentation/   # Code documentation principles
    └── dev-code-quality/    # SRP, CQS, complexity, error handling
```

## Components

### Skills (3 reference skills)

**dev-testing** — Testing methodology and coverage
- AAA pattern (Arrange-Act-Assert)
- Test organization (at least one per production class, splitting thresholds)
- Test reliability (no branching, no fixed delays, determinism)
- Coverage requirements (80% line/branch minimum)
- Corner case strategies and boundary testing

**dev-documentation** — Code documentation principles
- Mandatory documentation requirements
- Clarity (WHAT and WHY, not implementation)
- Completeness (parameters, returns, exceptions)
- Anti-patterns (stating the obvious, outdated docs)

**dev-code-quality** — Code quality and maintenance
- Single Responsibility Principle, Command-Query Separation
- Complexity thresholds (method length, cyclomatic complexity)
- Refactoring triggers and prioritization framework
- Error handling philosophy and patterns
- Secure coding principles

## Profile Integration

General skills integrate via the two-tier profile system. Domain extensions add general skills to their profile defaults:

```
core profile:        [domain:core-skill, pm-dev-general:dev-code-quality]
implementation:      [pm-dev-general:dev-code-quality, pm-dev-general:dev-documentation]
module_testing:      [domain:test-skill, pm-dev-general:dev-testing]
```

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-general/
