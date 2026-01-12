# Existing Guide

This guide covers best practices and common pitfalls.

## Best Practices

- Always validate input
- Use appropriate error handling
- Document your code
- Write tests

## Common Pitfalls

- Forgetting to handle edge cases
- Not validating user input
- Missing error handling
- Inconsistent naming conventions

## Examples

### Example 1

```javascript
function validate(input) {
  if (!input) throw new Error('Input required');
  return input.trim();
}
```
