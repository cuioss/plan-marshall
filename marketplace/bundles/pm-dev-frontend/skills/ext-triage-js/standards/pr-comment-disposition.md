# JavaScript / Frontend PR Comment Disposition

Decision criteria for disposing of automated PR review comments (gemini-code-assist, Copilot, Sonar, CodeRabbit, ESLint-bot, Stylelint-bot, etc.) on JavaScript and CSS code. Comments reach this disposition step **after** the validity check from `dev-general-practices` (PR review hard rule): if a suggestion contradicts the plan's stated intent or driving lesson, reply-and-resolve immediately. Use this document when the suggestion is plan-compatible and you must decide between FIX, REPLY-AND-RESOLVE, or ESCALATE.

## Disposition Outcomes

| Outcome | Meaning | Required Output |
|---------|---------|-----------------|
| **FIX** | Apply the suggested change in a follow-up commit | Code change + thread reply linking commit |
| **REPLY-AND-RESOLVE** | Decline the suggestion; explain rationale; mark thread resolved | Reply with template; resolve thread |
| **ESCALATE** | Ambiguous; ask the user via AskUserQuestion before acting | AskUserQuestion call; record decision in lessons |

## FIX-Eligible Categories

Concrete violations of frontend standards (see `pm-dev-frontend:javascript`, `pm-dev-frontend:css`, `pm-dev-frontend:lint-config`, `pm-dev-frontend:jest-testing`). Always FIX when the comment identifies one of these.

| Category | Example Findings | Authoritative Standard |
|----------|------------------|------------------------|
| ES module hygiene | CommonJS `require()` in ES module, default-export when named-export is convention | `javascript` (ES Modules) |
| Async correctness | Unhandled `Promise`, missing `await`, `async` function returning sync value | `javascript` (Async) |
| Equality bug | `==` instead of `===`, truthy check on object existence when `!= null` is intended | `javascript` |
| Array/object mutation | `Array.sort()` on shared array without copy, mutating prop in React-style consumer | `javascript` |
| DOM lifecycle | Event listener not removed on teardown, observer not disconnected, leaked timer | `javascript`, `jest-testing` (DOM tests) |
| Web component contract | Missing `connectedCallback`/`disconnectedCallback` cleanup, attribute setter without `attributeChangedCallback` | `javascript` |
| ESLint `error` rule | `no-unused-vars`, `no-undef`, `no-redeclare`, `no-prototype-builtins` | `lint-config` |
| ESLint security rule | `no-eval`, `no-implied-eval`, `no-new-func` | `lint-config` |
| JSDoc gaps | Public function missing `@param`/`@returns`, documented type drift from runtime | `javascript` (JSDoc) |
| CSS native nesting misuse | `&` selector outside nesting context, `@nest` syntax (deprecated) | `css` (Native Nesting) |
| Cascade layer order | `@layer` declared but not ordered, layer leakage across modules | `css` (Cascade Layers) |
| Container query syntax | `@container` without `container-type` declared on parent | `css` (Container Queries) |
| Custom property fallback | `var(--x)` without fallback for required tokens | `css` |
| Accessibility | Missing `alt`, `aria-label` on interactive element, focus trap broken | `css`, `javascript` |
| Stylelint `error` | Invalid property, duplicate selector, !important in non-utility layer | `lint-config` |
| Jest test correctness | Missing `expect.assertions(N)` on async test, `done` callback misuse, snapshot drift not reviewed | `jest-testing` |
| Mock leakage | `jest.fn()` not reset between tests, global `fetch` patched without restore | `jest-testing` |

## REPLY-AND-RESOLVE Categories

Decline the suggestion with the corresponding template. Always reply before resolving — never resolve silently.

### False Positive

| Trigger | Reply Template |
|---------|----------------|
| Bot flags `==` as bug but it is the intentional `== null` idiom (matches both `null` and `undefined`) | `False positive: `== null` is the documented idiom for null-or-undefined check (see lint-config eqeqeq config — allows null).` |
| Bot suggests removing `!important` from CSS reset / utility layer | `False positive: declaration is in `@layer utilities`; `!important` is the documented escape hatch for utility-layer overrides (see css.md cascade layers).` |
| Bot suggests `Array.from()` over spread, but spread preserves prototype-aware iteration | `False positive: spread preserves the iterable's prototype-aware iteration; `Array.from` would coerce to plain Array and break the consumer.` |
| Stylelint flags duplicate selector on intentional `:focus`/`:focus-visible` pair | `False positive: dual rule supports browsers without `:focus-visible`; collapsing breaks the documented progressive-enhancement pattern.` |

### Plan-Intent Contradiction

| Trigger | Reply Template |
|---------|----------------|
| Suggestion reintroduces CommonJS / `require()` on a plan migrating to ES modules | `Suggestion contradicts plan intent: this PR migrates module syntax to ES modules per `{plan_id}`. Reverting to `require()` would restore the anti-pattern the plan explicitly removes.` |
| Suggestion adds backward-compat shim on a `breaking` plan | `Plan compatibility strategy is `breaking` (see phase-2-refine compatibility field). Backward-compat shim is intentionally out of scope.` |
| Bot suggests jQuery / lodash where plan migrated to vanilla / native | `Plan removes `{lib}` per `{plan_id}/{lesson_id}`. Native `{api}` is the migration target; reverting reintroduces the dependency.` |
| Bot suggests SCSS/LESS feature on a project migrated to native CSS | `Plan migrates styles to native CSS (nesting, layers, custom properties). SCSS-only features are intentionally out of scope.` |

### Scope Out of Bounds

| Trigger | Reply Template |
|---------|----------------|
| Suggestion proposes refactor of a file untouched by this PR | `Out of scope: `{file}` is not modified in this PR. Refactor request belongs in a dedicated maintenance plan.` |
| Bot requests new test coverage for unchanged production code | `Out of scope: line is unchanged by this PR. Coverage gap predates this change; tracked separately, not a merge blocker.` |
| Bot proposes adopting a new framework or build tool (Vite, esbuild swap, React introduction) | `Out of scope: tooling/framework changes go through a separate plan and ADR; not in this PR's stated scope.` |
| Bot proposes accessibility audit of unrelated components | `Out of scope: A11y audit on unmodified components is tracked as a maintenance plan, not a merge blocker for this PR.` |

### Out of Domain

| Trigger | Reply Template |
|---------|----------------|
| Bot flags TypeScript-specific suggestion on plain `.js` file | `Out of domain: file is plain JavaScript (JSDoc-typed). TypeScript-only patterns (`interface`, `as const`) do not apply.` |
| Bot suggests Java/Python convention (PascalCase variables, `snake_case`) | `Out of domain: project uses ES module conventions (`camelCase` for variables, `PascalCase` only for classes/components).` |
| Bot flags `package.json` / Maven `pom.xml` issue inside JS code review thread | `Out of domain for this thread (JS code review). Build configuration findings are triaged via `cui-javascript-project` (CUI bundles) or the project's build owner.` |
| Bot complains about formatting that Prettier owns | `Out of domain: formatting is owned by Prettier; bot rule overlaps. Prettier output is the source of truth.` |

## Escalation Triggers

Use `AskUserQuestion` when the comment falls into any row below. Do NOT silently FIX or RESOLVE.

| Ambiguity | Why It Needs Escalation |
|-----------|------------------------|
| Suggestion changes a public component API (custom-element attribute, exported function signature) without deprecation declared in the plan | Breaking-API decisions require explicit user confirmation per compatibility strategy |
| Suggestion conflicts between two automated reviewers (ESLint says A, Sonar says B; gemini vs Copilot) | Cannot satisfy both; user must pick a direction |
| Suggestion proposes a security-sensitive change (CSP, sanitization, auth flow) outside this PR's stated scope | Security delta in unrelated code requires explicit go/no-go |
| Suggestion swaps event delegation strategy or virtual-DOM library on hot-path code | Architectural change; affects bundle size and runtime, needs maintainer call |
| Suggestion contradicts a project-specific lesson (CUI Quarkus DevUI, NiFi integration) but the lesson is not referenced in the plan | Verify the lesson still applies before accepting or rejecting |
| Bot proposes browser-support floor change (drop ES2020, require ES2024) | Compatibility matrix change; affects users, requires maintainer confirmation |
| Bot suggests CSS-in-JS / utility-CSS framework adoption | Styling architecture change requires ADR; never accept inline in PR review |

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
| Always cite the ESLint/Stylelint rule id or CSS spec section that justifies the disposition | Reviewers can verify rationale without context-switching |
| Never reply "won't fix" without a category from this document | Untraceable rejections invite repeated bot suggestions on future PRs |
| Use the closing token expected by the CI provider (GitHub `Resolve conversation`; GitLab `Resolve thread`) only after the reply is posted | Resolving without a reply leaves no audit trail |
| Keep replies under 4 lines unless citing multiple standards | Long replies are skipped by reviewers; structured one-liners scale |

## Related Standards

- [severity.md](severity.md) — Severity-to-action mapping for JS/CSS findings
- [suppression.md](suppression.md) — `eslint-disable`, `stylelint-disable` syntax
- `pm-dev-frontend:javascript` — Core JavaScript standards
- `pm-dev-frontend:css` — CSS standards (nesting, layers, container queries)
- `pm-dev-frontend:lint-config` — ESLint / Stylelint / Prettier configuration
- `pm-dev-frontend:jest-testing` — Jest test correctness baseline
- `plan-marshall:dev-general-practices` — PR review hard rule (validate bot suggestions against plan intent)
