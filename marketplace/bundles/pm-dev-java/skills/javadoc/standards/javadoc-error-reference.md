# Javadoc Error Reference

Quick reference guide for identifying and fixing common Javadoc build errors and warnings.

## Purpose

This reference provides guidance for fixing Javadoc errors that appear during Maven builds, focusing on minimal fixes that preserve content and correct only formatting, references, and tag issues.

## Error Resolution Principles

### Content Preservation Rules

**DO:**
- Fix ONLY Javadoc errors and warnings from build
- Make minimal modifications necessary
- Focus on formatting, references, and tags
- Preserve existing documentation content

**DO NOT:**
- Alter or improve documentation content
- Modify any code
- Rewrite documentation for style
- Make changes beyond error fixes

## Common Javadoc Errors and Fixes

### Missing Parameter Documentation

**Error Pattern:**
```
warning: @param argument "<param-name>" is not a parameter name
warning: no @param for <param-name>
```

**Fix:**
- Add `@param` tags for all undocumented parameters
- Use parameter name exactly as in method signature
- Add minimal description based on parameter name
- Do not modify existing parameter documentation

**Example Fix:**
```java
// BEFORE (error: no @param for userId)
/**
 * Retrieves user information.
 * @return user data
 */
public User getUser(String userId) { ... }

// AFTER (fixed)
/**
 * Retrieves user information.
 * @param userId the user identifier
 * @return user data
 */
public User getUser(String userId) { ... }
```

### Invalid References

**Error Pattern:**
```
warning: reference not found: ClassName
warning: invalid @link reference
error: unknown tag: link
```

**Fix:**
- Fix `{@link}` references to non-existent classes/methods
- Update references to renamed elements
- Remove references to deleted elements
- Replace with appropriate alternative references
- Use fully qualified names if needed

**Example Fix:**
```java
// BEFORE (error: reference not found: OldClassName)
/**
 * See {@link OldClassName} for details.
 */

// AFTER (fixed - class was renamed)
/**
 * See {@link NewClassName} for details.
 */

// OR (if class was deleted, remove reference)
/**
 * Processes user authentication.
 */
```

### HTML Formatting Issues

**Error Pattern:**
```
warning: unclosed tag: <p>
warning: malformed HTML
error: bad HTML entity
```

**Fix:**
- Close unclosed HTML tags
- Fix malformed HTML elements
- Correct improper nesting of HTML tags
- Ensure proper escaping of special characters

**Example Fix:**
```java
// BEFORE (error: unclosed tag <p>)
/**
 * <p>This method processes data.
 * It returns the result.
 */

// AFTER (fixed)
/**
 * <p>This method processes data.
 * It returns the result.</p>
 */

// BEFORE (error: bad HTML entity &)
/**
 * Handles input & output operations.
 */

// AFTER (fixed)
/**
 * Handles input &amp; output operations.
 */
```

### Missing Return Documentation

**Error Pattern:**
```
warning: no @return
warning: @return tag has no description
```

**Fix:**
- Add `@return` tags for undocumented return values
- Provide minimal description based on method name
- Do not modify existing return documentation
- For void methods, no `@return` tag is needed

**Example Fix:**
```java
// BEFORE (error: no @return)
/**
 * Calculates total amount.
 * @param items the items to sum
 */
public BigDecimal calculateTotal(List<Item> items) { ... }

// AFTER (fixed)
/**
 * Calculates total amount.
 * @param items the items to sum
 * @return the total amount
 */
public BigDecimal calculateTotal(List<Item> items) { ... }
```

### Missing Exception Documentation

**Error Pattern:**
```
warning: no @throws for <ExceptionType>
warning: exception not thrown: <ExceptionType>
```

**Fix:**
- Add `@throws` tags for undocumented exceptions
- Document conditions that trigger exceptions
- Do not modify existing exception documentation
- Ensure exceptions in `@throws` tags match method signature
- Remove `@throws` for exceptions no longer thrown

**Example Fix:**
```java
// BEFORE (error: no @throws for IllegalArgumentException)
/**
 * Validates user input.
 * @param input the input to validate
 */
public void validate(String input) throws IllegalArgumentException { ... }

// AFTER (fixed)
/**
 * Validates user input.
 * @param input the input to validate
 * @throws IllegalArgumentException if input is null or empty
 */
public void validate(String input) throws IllegalArgumentException { ... }
```

### Malformed Tags

**Error Pattern:**
```
warning: no description for @param
warning: malformed @tag
error: unknown tag: @customtag
```

**Fix:**
- Add descriptions to tags that require them
- Fix tag syntax errors
- Remove or replace unknown/custom tags
- Use standard Javadoc tags only

**Example Fix:**
```java
// BEFORE (error: no description for @param)
/**
 * @param userId
 */
public void process(String userId) { ... }

// AFTER (fixed)
/**
 * Processes user data.
 * @param userId the user identifier
 */
public void process(String userId) { ... }
```

### Incorrect Tag Order

**Error Pattern:**
```
warning: tag out of order: @return before @param
```

**Fix:**
- Reorder tags to follow standard order:
  1. Description
  2. `@param`
  3. `@return`
  4. `@throws`
  5. `@see`
  6. `@since`
  7. `@deprecated`

**Example Fix:**
```java
// BEFORE (error: tag out of order)
/**
 * Retrieves user.
 * @return user object
 * @param userId user identifier
 */

// AFTER (fixed)
/**
 * Retrieves user.
 * @param userId user identifier
 * @return user object
 */
```

### Code Block Formatting Issues

**Error Pattern:**
```
warning: malformed <pre> tag
error: unclosed <code> tag
```

**Fix:**
- Properly close all code tags
- Use correct nesting: `<pre><code>...</code></pre>`
- Use `{@code}` for inline code instead of `<code>` when possible
- Escape special characters within code blocks

**Example Fix:**
```java
// BEFORE (error: unclosed <code> tag)
/**
 * Example: <code>user.getName()
 */

// AFTER (fixed)
/**
 * Example: {@code user.getName()}
 */

// BEFORE (error: malformed <pre> tag)
/**
 * <pre>
 * User user = new User();
 * </pre
 */

// AFTER (fixed)
/**
 * <pre><code>
 * User user = new User();
 * </code></pre>
 */
```

### Empty Documentation

**Error Pattern:**
```
warning: no description
warning: no main description
```

**Fix:**
- Add minimal description for documented elements
- Focus on purpose and behavior
- Keep description concise
- Avoid stating the obvious

**Example Fix:**
```java
// BEFORE (error: no description)
/**
 * @param input
 * @return result
 */

// AFTER (fixed)
/**
 * Processes the input data.
 * @param input the data to process
 * @return the processed result
 */
```

## Verification Steps

After fixing Javadoc errors:

1. **Run local Javadoc check:**
   ```bash
   ./mvnw javadoc:javadoc
   ```

2. **Run pre-commit build:**
   ```bash
   ./mvnw -Ppre-commit clean verify -DskipTests
   ```

3. **Verify all warnings resolved** in build output

4. **Ensure no content changes** - only formatting, references, and tags fixed

## Special Cases

### Framework-Required Documentation

Some frameworks require specific Javadoc patterns. Check framework documentation before "fixing" these:

- JPA entities may have empty Javadoc intentionally
- Spring beans may use Javadoc for configuration
- Serializable classes may have version documentation requirements

### Legacy Code

When fixing Javadoc in legacy code:
- Fix errors as documented above
- Do not attempt to improve documentation quality
- Do not add missing documentation beyond what build requires
- Leave improvement for dedicated documentation work

### Generated Code

Skip Javadoc fixes in generated code:
- Do not modify generated files
- Configure build to skip Javadoc for generated sources
- Fix generator configuration instead

## Related Standards

For writing NEW JavaDoc documentation (not fixing errors):
- javadoc-core.md - Core principles and requirements
- javadoc-class-documentation.md - Class-level documentation
- javadoc-method-documentation.md - Method-level documentation
- javadoc-code-examples.md - Code examples and formatting
