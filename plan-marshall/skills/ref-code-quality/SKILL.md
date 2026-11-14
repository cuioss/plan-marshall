---
name: ref-code-quality
description: Language-agnostic code quality principles covering SRP, CQS, complexity thresholds, refactoring triggers, error handling, and documentation standards, plus the code-review spine — the cross-cutting review categories and review rules every code review cites
user-invocable: false
mode: knowledge
implements: ref
---

# Code Quality and Documentation Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Language-agnostic code quality and documentation principles applicable across all technology stacks. Covers design principles, complexity management, refactoring triggers, error handling, and API documentation. The `## Review Categories` and `## Review Rules` sections at the end are the code-review spine: the language-neutral categories and rules a code review applies to any change, whatever domains it touches.

## Workflow

### Step 1: Load Code Organization Standards

**Important**: Load this standard for any implementation or refactoring work.

```text
Read: standards/code-organization.md
```

Covers SRP, CQS, parameter objects, package structure, immutability, refactoring triggers, complexity thresholds, and maintenance prioritization.

### Step 2: Load Additional Standards (As Needed)

**Error Handling** (load for error/exception work):
```text
Read: standards/error-handling.md
```

Use when: Designing error handling, exception hierarchies, or recovery patterns, or when writing a classifier, gate, or status derivation that must fail closed rather than emit an unsubstantiated clean verdict.

**Documentation Principles** (load for API documentation work):
```text
Read: standards/documentation-principles.md
```

Use when: Writing or reviewing public API documentation, updating docs during code changes.

## Related

- `pm-dev-java:java-core` — Java-specific patterns and features
- `pm-dev-java:java-maintenance` — Java maintenance prioritization
- `pm-dev-java:javadoc` — JavaDoc tag syntax and Java-specific patterns
- `pm-dev-frontend:javascript` — JavaScript-specific patterns including JSDoc

## Code Examples

### Single Responsibility — Before
```python
class UserService:
    def create_user(self, data):
        # validates, saves to DB, sends email, logs audit
        ...
```

### Single Responsibility — After
```python
class UserService:
    def __init__(self, repo, notifier):
        self._repo = repo
        self._notifier = notifier

    def create_user(self, data):
        user = self._repo.save(data)
        self._notifier.welcome(user)
        return user
```

## Standards Reference

| Standard | Purpose |
|----------|---------|
| code-organization.md | SRP, CQS, package structure, refactoring triggers, complexity, maintenance |
| error-handling.md | Exception philosophy, propagation, recovery, fail-closed classification discipline |
| documentation-principles.md | What/when/how to document public APIs |

## Review Categories

The cross-cutting categories of the code-review spine: the kinds of defect a reviewer looks for in every change, whatever its language. The block follows the harvestable block contract — see [`review-rubric.md` § 10 "Harvestable review-rule blocks"](../phase-6-finalize/standards/review-rubric.md) for its rules, which are not restated here.

- **Correctness** — the changed code computes a wrong result, selects the wrong set of inputs, or loses an entry on an input a caller can actually supply.
- **Error handling and fail-closed behaviour** — a failure at a boundary (an unreadable file, a non-zero subprocess exit, a malformed document) is swallowed, read as an empty or clean result, or lets a gate pass that exists to stop it.
- **Resource lifecycle** — a file, process, lock or temporary artifact is acquired without a release on every exit path, or shared state is read, changed and written back while another writer can change it in between.
- **Complexity and duplication** — one contract, constant or rule is stated in more than one place, so an edit to one copy leaves the others stating something different.
- **Naming and documentation accuracy** — a name, count, ordinal, comment or user-facing string states something the code or document no longer does, or admits a reading that leads its reader to a wrong action.
- **Test quality including negative cases** — a test cannot fail while it claims to guard a behaviour, or exercises only the input the change was written for and never the input that must be refused.
- **Contract and doc drift between code and its governing documents** — code and the document that governs it (a schema, a description, a worked example, a documented detection rule) disagree, so a reader who follows the document gets behaviour the code does not have.

## Review Rules

The language-neutral review rules of the code-review spine. Each rule is tagged with the spine category above it belongs to, so a finding that cites the rule also names its category. The block follows the same harvestable block contract as `## Review Categories`.

- **Correctness** — A function pair that saves and restores, enters and exits, or opens and closes state where one side sets, captures or resets a field the other side omits, so a round trip leaves that field stale or unset.
- **Correctness** — A regex or glob whose boundary is wider or narrower than the inputs it is meant to select (a missing anchor, an unescaped metacharacter, a substring match where a whole token is meant), so a real input is selected that should be rejected or rejected that should be selected.
- **Correctness** — A collection keyed by a caller-supplied identity (a map, a registry, a uniqueness set) that inserts a validated key without a duplicate-key disposition, so two inputs claiming the same key collapse into one entry and one of them silently wins.
- **Correctness** — A changed function whose result is wrong for an input its callers can supply, found by reading the whole function, including the branches the diff did not touch, instead of the changed lines alone.
- **Error handling and fail-closed behaviour** — A subprocess call or file read or write at a real boundary with no exit-status check and no enclosing handler, so a failed call is followed by code that treats its absent output as a valid result.
- **Error handling and fail-closed behaviour** — An input that could not be read (missing, unreadable, or of the wrong type) treated the same as an input that was read and found empty, so a gate or classifier reports a clean verdict for something it never examined.
- **Error handling and fail-closed behaviour** — A function that reports success, a complete result or an empty finding list after it skipped, dropped or failed part of its work.
- **Error handling and fail-closed behaviour** — A guard fed by a key derived by first-match scanning over a decomposed value instead of indexing a fixed position from a known root, so every input whose leading segments happen to match collapses to the same key and the guard's refusal path can never be taken.
- **Error handling and fail-closed behaviour** — A loop branch that drops an item with a bare `continue` or `break` inside a function that owns a report channel for suppressed items, so the function returns success with an empty report after discarding items.
- **Resource lifecycle** — A file or record that is read, modified and written back while another process can write it in between, with no lock and no atomic replace, so one writer's change is lost.
- **Resource lifecycle** — A handle, lock, subprocess or temporary file acquired with no release on the error path, so a failure leaves it held, running or on disk.
- **Complexity and duplication** — Two sections of one document that give different instructions for the same situation, so a reader who follows one does what the other forbids or omits.
- **Complexity and duplication** — A constant, enumeration or rule declared in two places that are meant to agree, where the change updated one declaration and left the other holding the old value.
- **Naming and documentation accuracy** — A user-facing string, message or prompt that admits two readings, one of which leads its reader to a wrong action.
- **Naming and documentation accuracy** — A new normative statement (MUST, NEVER, ALWAYS) that contradicts an existing normative statement in the same document, so the two cannot both be followed.
- **Naming and documentation accuracy** — A count in prose ("three verbs", "five gates") that no longer equals the number of items it counts after the change added or removed one.
- **Naming and documentation accuracy** — A hard-coded ordinal reference ("step 4", "item 3") into a numbered list the change renumbered, so the reference now names a different item or points past the end of the list.
- **Test quality including negative cases** — A test that cannot fail for the defect it is named for: it passes the value it claims to check as the default, asserts only that no exception was raised, or exercises one half of a paired operation and asserts the state the other half should have set.
- **Test quality including negative cases** — A refusal, guard or error branch the change adds with no test supplying an input that reaches it, so the branch can break without any test turning red.
- **Contract and doc drift between code and its governing documents** — Code that emits, accepts or enforces something different from the schema, table or detection rule its governing document states: a missing, renamed or extra output field, or a match looser than the documented one.
- **Contract and doc drift between code and its governing documents** — An output field, status value or key the change produces that no consumer reads where a control-flow contract expects a branch on it, so the signal it carries is lost.
- **Contract and doc drift between code and its governing documents** — A worked example whose good case branches on a different predicate than the rule it illustrates requires, so a reader who copies the example reproduces the shape the rule forbids.
- **Contract and doc drift between code and its governing documents** — A description or summary line (frontmatter, docstring, module header) that still advertises behaviour, a mode or a component the body no longer implements.
