---
name: plan-marshall-persona-module-tester
description: Language-agnostic testing methodology covering AAA pattern, test structure, organization, coverage, property-based testing, test doubles, determinism, fixture-level neutralization of state-dependent branch selection (default-on inheritance, location carve-out plus registered marker, matched positive/negative control), constructed-argv assertion at the lowest subprocess primitive, and real-resolver E2E testing for path-resolver/create side effects
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Testing Methodology Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Language-agnostic testing principles applicable across all technology stacks. Covers test structure, organization, coverage requirements, property-based testing, test doubles, and reliability patterns.

## Workflow

### Step 1: Load Testing Methodology

**Important**: Load this standard for any testing work.

```text
Call the `read` tool with `{ filePath: "standards/testing-methodology.md" }` before continuing.
```

Covers AAA pattern, test categories (happy path, parameter variants, corner cases, error conditions), test class organization, the 400-line module budget and behaviour-cluster splitting, naming, docstring content, data generation and the universal-contract / literal-is-the-contract discriminator, property-based testing, one-layer-per-contract, test doubles taxonomy, reliability, and anti-patterns.

### Step 2: Load Coverage Standards (As Needed)

```text
Call the `read` tool with `{ filePath: "standards/testing-coverage.md" }` before continuing.
```

Use when: Analyzing test coverage, defining corner cases, improving coverage metrics, boundary value analysis, or testing a classifier whose verdict depends on more than one input axis.

## Related

- `pm-dev-java:junit-core` — JUnit 5 testing patterns
- `pm-dev-frontend:jest-testing` — Jest testing patterns
- `pm-dev-java-cui:cui-testing` — CUI test generator framework

## Code Examples

### AAA Pattern
```python
def test_discount_applied_for_premium_user():
    # Arrange
    user = User(tier="premium")
    cart = Cart(items=[Item(price=100)])

    # Act
    total = cart.checkout(user)

    # Assert
    assert total == 90  # 10% premium discount
```

## Standards Reference

| Standard | Purpose |
|----------|---------|
| testing-methodology.md | AAA pattern, test structure, naming, organization, property-based testing, test doubles, determinism, foundation-utility CLI testing, constructed-argv assertion at the lowest subprocess primitive, real-resolver E2E testing for path-resolver/create side effects (cross-references plugin-doctor test-conventions rules) |
| testing-coverage.md | Coverage requirements, corner cases, boundary testing, classifier input matrices (cross-product over the axes rather than the diagonal, and the error-result input that discriminates a fail-closed unit) |

## House-Style Rules

| Rule | Threshold | Standard section |
|------|-----------|------------------|
| Module line budget | 400 lines; split by behaviour cluster into `test_{unit}_{cluster}.py` | testing-methodology.md § "Module Budget: 400 lines" |
| Docstring content | States the invariant in the present tense; no plan/deliverable id, PR number, lesson id, or superseded behaviour | testing-methodology.md § "Test Docstring Content" |
| Generated vs literal data | Generate where the contract is universal; exact literal where the literal *is* the contract | testing-methodology.md § "Test Data Principles → The discriminator" |
| Property-based testing | Scoped to universal contracts (parsers, validators, normalisers, round-trip encoders) | testing-methodology.md § "Property-Based Testing" |
| One layer per contract | In-process test is authoritative; subprocess collapses to one CLI-plumbing smoke, with two exceptions | testing-methodology.md § "One Layer Per Contract" |

**Who enforces these rules depends on the project.** In the plan-marshall
marketplace repository — and only there — the structural half is enforced by the
`pm-plugin-development:plugin-doctor` `test-conventions` scope (see its
[standards doc](../../../pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md)).
Plugin-doctor is a marketplace-authoring tool: it ships in that repository, it is
not installed into a consumer project, and a consumer is not expected to carry an
equivalent.

Everywhere else these are **house-style rules a reviewer applies by reading** —
no tool reports a violation. Read the table above as the standard to meet, not as
a gate that will catch you missing it, and do not cite plugin-doctor as the
verification for a test deliverable in a project that does not have it.
