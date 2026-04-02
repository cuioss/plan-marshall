---
name: dev-general-module-testing
description: Language-agnostic testing methodology covering AAA pattern, test structure, organization, coverage, property-based testing, test doubles, and determinism
user-invocable: false
---

# Testing Methodology Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Language-agnostic testing principles applicable across all technology stacks. Covers test structure, organization, coverage requirements, property-based testing, test doubles, and reliability patterns.

## Workflow

### Step 1: Load Testing Methodology

**Important**: Load this standard for any testing work.

```
Read: standards/testing-methodology.md
```

Covers AAA pattern, test categories (happy path, parameter variants, corner cases, error conditions), test class organization, naming, data generation, property-based testing, test doubles taxonomy, reliability, and anti-patterns.

### Step 2: Load Coverage Standards (As Needed)

```
Read: standards/testing-coverage.md
```

Use when: Analyzing test coverage, defining corner cases, improving coverage metrics, or boundary value analysis.

## Related Skills

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
| testing-methodology.md | AAA pattern, test structure, naming, organization, property-based testing, test doubles, determinism |
| testing-coverage.md | Coverage requirements, corner cases, boundary testing |
