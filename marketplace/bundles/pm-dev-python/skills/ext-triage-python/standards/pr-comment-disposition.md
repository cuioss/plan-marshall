# Python PR Comment Disposition

Decision criteria for disposing of automated PR review comments (gemini-code-assist, Copilot, Sonar, CodeRabbit, ruff-bot, etc.) on Python code. Comments reach this disposition step **after** the validity check from `dev-general-practices` (PR review hard rule): if a suggestion contradicts the plan's stated intent or driving lesson, reply-and-resolve immediately. Use this document when the suggestion is plan-compatible and you must decide between FIX, REPLY-AND-RESOLVE, or ESCALATE.

## Disposition Outcomes

| Outcome | Meaning | Required Output |
|---------|---------|-----------------|
| **FIX** | Apply the suggested change in a follow-up commit | Code change + thread reply linking commit |
| **REPLY-AND-RESOLVE** | Decline the suggestion; explain rationale; mark thread resolved | Reply with template; resolve thread |
| **ESCALATE** | Ambiguous; ask the user via AskUserQuestion before acting | AskUserQuestion call; record decision in lessons |

## FIX-Eligible Categories

Concrete violations of Python standards (see `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`). Always FIX when the comment identifies one of these.

| Category | Example Findings | Authoritative Standard |
|----------|------------------|------------------------|
| Type-checker error | Mypy `error:` (assignment, return-value, arg-type, no-untyped-def) | `python-core` (Type Annotations) |
| Resource leak | File/socket opened without context manager; bare `open()` left dangling | `python-core` (Resource Management) |
| Mutable default arg | `def f(x=[])` / `def f(x={})` | `python-core` |
| Bare `except` | `except:` or `except Exception:` without re-raise/log | `python-core` (Error Handling) |
| Async correctness | `await` missing on coroutine, sync I/O in async function, blocking call without `to_thread` | `python-core` (Async Patterns) |
| Path handling | String concatenation for paths instead of `pathlib.Path` | `python-core` |
| Pytest correctness | `assert True`, missing assertion, `time.sleep` in tests, fixture order coupling | `pytest-testing` |
| Mocking misuse | Patching wrong import path, mock leaks across tests, `MagicMock` where `Mock` would suffice | `pytest-testing` |
| Ruff `E`/`F` rule | Syntax error, undefined name, unused import in production module | `python-core` |
| Ruff `B` (bugbear) | `B008` mutable default, `B904` raise from `e`, `B017` blanket `pytest.raises` | `python-core` |
| Dataclass/Pydantic misuse | Missing `field(default_factory=...)`, `@dataclass(frozen=True)` mutated, Pydantic v1 syntax in v2 module | `python-core` |
| Pattern matching | `match`/`case` with overlapping patterns or unreachable case | `python-core` |
| Coverage drop | New public function lacks any test | `pytest-testing` |

## REPLY-AND-RESOLVE Categories

Decline the suggestion with the corresponding template. Always reply before resolving — never resolve silently.

### False Positive

| Trigger | Reply Template |
|---------|----------------|
| Mypy bot flags `Any` return on dynamic `json.loads()` consumer | `False positive: return type depends on caller-provided JSON shape; `# type: ignore[no-any-return]` with rationale is the documented pattern (see suppression.md).` |
| Bot suggests `Optional[X]` is unsafe but `if x is None: return` guard exists on prior line | `False positive: `{var}` is narrowed at line {N} via `is None` check; mypy already accepts the flow.` |
| Ruff `E501` on a help-string URL or pytest `parametrize` ID that cannot be split | `False positive: line is a non-splittable URL/parametrize id. `# noqa: E501` with justification is the documented exception.` |
| Bot flags "magic number" for HTTP status / well-known port | `False positive: `{value}` is a protocol constant (RFC/IANA). Promotion to a named constant adds noise without semantic gain.` |

### Plan-Intent Contradiction

| Trigger | Reply Template |
|---------|----------------|
| Suggestion reintroduces a deprecation/migration target the plan is removing | `Suggestion contradicts plan intent: this PR removes `{pattern}` per `{plan_id}/{lesson_id}`. Reverting would restore the anti-pattern the plan explicitly eliminates.` |
| Suggestion adds backward-compat shim on a `breaking` plan | `Plan compatibility strategy is `breaking` (see phase-2-refine compatibility field). Backward-compat shim is intentionally out of scope.` |
| Bot proposes JSON output where plan migrated to TOON | `Plan migrates output from JSON to TOON (see `ref-toon-format`). Reverting the script to `json.dumps` contradicts the migration intent.` |
| Bot suggests `print()` over CuiLogger / structured logging | `Module standard requires structured logging (see `cui-logging` for CUI modules). `print()` is acceptable only for CLI user-facing output, not diagnostics.` |

### Scope Out of Bounds

| Trigger | Reply Template |
|---------|----------------|
| Suggestion proposes refactoring a function untouched by this PR | `Out of scope: `{function}` is not modified in this PR. Refactor request belongs in a dedicated maintenance plan.` |
| Bot requests new tests for unchanged production code | `Out of scope: line is unchanged by this PR. Coverage gap predates this change; tracked separately, not a merge blocker.` |
| Bot proposes type-stub additions for a third-party dep without typing | `Out of scope: typing third-party dependency requires a separate stub-package decision; tracking as future work.` |
| Bot proposes adopting a new dependency (pendulum, attrs, structlog) | `Out of scope: dependency additions go through `dev-general-practices` dependency-management workflow, not inline in PR review.` |

### Out of Domain

| Trigger | Reply Template |
|---------|----------------|
| Bot flags a `.pyi` stub file with a runtime-only rule | `Out of domain: file is a `.pyi` stub; `{rule_id}` applies to runtime modules only.` |
| Bot suggests JS/TS-style pattern (`async/await` chaining as `.then`) on Python code | `Out of domain: suggestion is JavaScript pattern. Python equivalent (`asyncio.gather`, `await`) is already in use at line {N}.` |
| Bot flags `pyproject.toml` issue inside a Python code review thread | `Out of domain for this thread (Python code review). Build configuration findings are triaged via `plan-marshall:build-python` workflow.` |
| Bot complains about indentation/formatting that ruff-format owns | `Out of domain: formatting is owned by ruff-format; bot rule overlaps. Formatter output is the source of truth; suggestion would diverge from `ruff format` baseline.` |

## Escalation Triggers

Use `AskUserQuestion` when the comment falls into any row below. Do NOT silently FIX or RESOLVE.

| Ambiguity | Why It Needs Escalation |
|-----------|------------------------|
| Suggestion changes a public function signature (positional → keyword-only, etc.) without a deprecation path declared in the plan | Breaking-API decisions require explicit user confirmation per compatibility strategy |
| Suggestion conflicts between two automated reviewers (mypy says A, ruff says B; gemini vs Copilot) | Cannot satisfy both; user must pick a direction |
| Suggestion proposes a security-sensitive change (auth, crypto, deserialization, subprocess) outside this PR's stated scope | Security delta in unrelated code requires explicit go/no-go |
| Suggestion swaps `multiprocessing` ↔ `asyncio` ↔ `threading` on hot-path code without benchmark | Concurrency model change is architectural; needs maintainer call |
| Suggestion contradicts a project-specific lesson (e.g., "no shell polling loops", "no PYTHONPATH smoke tests") but the lesson is not referenced in the plan | Verify the lesson still applies before accepting or rejecting |
| Bot proposes Python version uplift (3.10→3.12 syntax) | Toolchain change requires maintainer confirmation; affects CI matrix |
| Bot suggests `cd && pytest <file>` style targeted runs as a "shortcut" | Hard rule violation per `feedback_no_pw_or_cd_chains.md`; verify lesson before accepting |

## Disposition Flow

```
Bot comment received
  ↓
Plan-intent check (dev-general-practices PR review rule)
  Contradicts plan? → REPLY-AND-RESOLVE (Plan-Intent Contradiction)
  ↓
Match FIX category from table above?
  Yes → FIX (apply change, reply with commit link)
  ↓
Match REPLY-AND-RESOLVE category?
  Yes → reply with template, mark resolved
  ↓
Match Escalation Trigger?
  Yes → AskUserQuestion, record decision in lessons
  ↓
Default → ESCALATE (do not silently fix or resolve unknown categories)
```

## Reply Quality Rules

| Rule | Rationale |
|------|-----------|
| Always cite the rule code (`E501`, `B008`, mypy error code) or PEP / standard line | Reviewers can verify rationale without context-switching |
| Never reply "won't fix" without a category from this document | Untraceable rejections invite repeated bot suggestions on future PRs |
| Use the closing token expected by the CI provider (GitHub `Resolve conversation`; GitLab `Resolve thread`) only after the reply is posted | Resolving without a reply leaves no audit trail |
| Keep replies under 4 lines unless citing multiple standards | Long replies are skipped by reviewers; structured one-liners scale |

## Related Standards

- [severity.md](severity.md) — Severity-to-action mapping for Python findings
- [suppression.md](suppression.md) — `# noqa`, `# type: ignore`, pytest skip/xfail syntax
- `pm-dev-python:python-core` — Core Python patterns referenced in FIX-eligible categories
- `pm-dev-python:pytest-testing` — Pytest correctness baseline
- `plan-marshall:dev-general-practices` — PR review hard rule (validate bot suggestions against plan intent)
