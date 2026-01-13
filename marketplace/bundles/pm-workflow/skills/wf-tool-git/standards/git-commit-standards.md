# Git Commit Standards

Standardized git commit format for all CUI LLM projects following conventional commits.

## Commit Message Format

```text
<type>(<scope>): <subject>

<body>

<footer>
```

### Required Components

* **Type**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`
* **Subject**: Imperative, present tense, no capital, no dot, max 50 chars

### Optional Components

* **Scope**: Component/module affected (e.g., `auth`, `config`, `security`)
* **Body**: Motivation and context, wrap at 72 chars
* **Footer**: Breaking changes (`BREAKING CHANGE:`), issue refs (`Fixes #123`)

## Commit Types

### Feature Development

* **feat**: New feature for the user
* **perf**: Performance improvement

### Code Maintenance

* **fix**: Bug fix for the user
* **refactor**: Code change that neither fixes a bug nor adds a feature
* **style**: Changes that don't affect code meaning (formatting, whitespace)

### Supporting Changes

* **docs**: Documentation only changes
* **test**: Adding or correcting tests
* **chore**: Changes to build process or auxiliary tools

## Examples

### Basic Commit

```text
fix(auth): resolve token validation error

Updated to use RS256 consistently across all validation methods.

Fixes #234
```

### Task-Based Commit

```text
refactor: C1. Document Bouncy Castle Usage

Add comprehensive JavaDoc comments and update README with
dependency information for cryptographic operations.
```

### Breaking Change

```text
feat(api): update authentication endpoint structure

BREAKING CHANGE: Authentication response now returns object with
`accessToken`, `refreshToken`, and `metadata` properties.

Migration: Update client code to access token via response.accessToken
```

### Multiple Changes

```text
fix(security): address multiple security vulnerabilities

- Update dependency versions to patch CVEs
- Add input validation for user-supplied data
- Implement rate limiting on authentication endpoints

Fixes #456, #457, #458
```

## Key Practices

### Atomic Commits

* **One logical change per commit** - Each commit should represent a single, coherent change
* **Complete and functional** - Code should compile and tests should pass after each commit
* **Independent changes** - Separate formatting, refactoring, and feature changes into different commits

### Meaningful Messages

* **Clear and descriptive subjects** - Reader should understand the change without reading code
* **Imperative mood** - Use "add feature" not "added feature" or "adds feature"
* **Concise but complete** - 50 char subject is ideal, 72 char absolute max
* **Explain why, not what** - Body should explain motivation and context

### Reference Issues

* **Link to relevant tasks/issues** - Use `Fixes #123`, `Closes #456`, `Refs #789`
* **Use proper keywords** - GitHub recognizes: fixes, closes, resolves (case-insensitive)
* **Multiple references** - List all related issues: `Fixes #123, #456`

## Subject Line Guidelines

### Do's

* Start with lowercase (after type/scope)
* Use imperative mood: "add", "fix", "update"
* Be specific: "fix null pointer in user login" not "fix bug"
* Omit trailing period

### Don'ts

* Don't capitalize first word after colon
* Don't use past tense: "added", "fixed"
* Don't be vague: "update code", "fix issue"
* Don't exceed 72 characters total

## Body Guidelines

### When to Include

* **Complex changes** - Explain multi-step changes or non-obvious solutions
* **Breaking changes** - Always include migration guide
* **Context needed** - Provide background for why change was necessary
* **Multiple files** - Explain how changes across files relate

### Format

* Wrap at 72 characters
* Use bullet points for multiple items
* Separate paragraphs with blank lines
* Include relevant technical details

### What to Explain

* **Motivation** - Why was this change needed?
* **Approach** - What solution did you choose and why?
* **Alternatives** - What other approaches were considered?
* **Side effects** - What else might this affect?

## Footer Guidelines

### Breaking Changes

```text
BREAKING CHANGE: Brief description of breaking change

Detailed explanation of what breaks and why.

Migration: Step-by-step guide to update existing code.
```

### Issue References

* `Fixes #123` - Closes issue when commit is merged
* `Closes #456` - Same as Fixes
* `Resolves #789` - Same as Fixes
* `Refs #321` - References issue without closing
* `See also #654` - Informal reference

### Multiple Footers

```text
feat(api): add new authentication endpoint

BREAKING CHANGE: Old /auth endpoint deprecated

Migration: Use /api/v2/authenticate instead

Fixes #123
Refs #456
```

## Scope Guidelines

### When to Use Scope

* **Large projects** - Multiple modules or components
* **Clear boundaries** - Well-defined areas of responsibility
* **Team clarity** - Helps team members find relevant changes quickly

### Common Scopes

* **Module names**: `auth`, `database`, `api`, `ui`
* **Component names**: `user-service`, `payment-handler`
* **Technology areas**: `docker`, `ci`, `security`

### When to Omit Scope

* **Small projects** - Single module or component
* **Cross-cutting changes** - Affects multiple areas equally
* **Unclear boundaries** - Change doesn't fit one scope

## Anti-Patterns

### Avoid These

```text
❌ Updated stuff
❌ Fixed bug
❌ WIP
❌ Checkpoint
❌ asdfasdf
❌ minor changes
❌ Merge branch 'feature-x'
```

### Instead Use

```text
✅ feat(auth): add JWT token validation
✅ fix(api): handle null response in user endpoint
✅ refactor(database): extract connection pooling logic
✅ docs(readme): add installation instructions
✅ test(auth): add unit tests for token validation
```

## Verification Checklist

Before committing, verify:

- [ ] Type is appropriate and from approved list
- [ ] Subject is imperative, lowercase, no period
- [ ] Subject is descriptive and specific
- [ ] Subject is ≤ 50 characters (72 absolute max)
- [ ] Body explains "why" not "what"
- [ ] Body is wrapped at 72 characters
- [ ] Footer includes issue references if applicable
- [ ] Breaking changes are clearly documented
- [ ] Code compiles and tests pass
- [ ] Commit is atomic (single logical change)

## References

* Conventional Commits: https://www.conventionalcommits.org/
* Git Commit Best Practices: https://cbea.ms/git-commit/
* Angular Commit Guidelines: https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit
