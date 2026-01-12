# ASCII Diagram Patterns

This document provides patterns for creating ASCII diagrams in solution outlines.

## Purpose of Diagrams

The Overview diagram provides:
- Visual orientation for reviewers
- Component relationship overview
- Dependency direction clarity
- Before/after comparison (for refactoring)

## Box Drawing Characters

Use Unicode box-drawing characters for clean diagrams:

| Character | Name | Use |
|-----------|------|-----|
| `─` | Horizontal line | Horizontal connections |
| `│` | Vertical line | Vertical connections |
| `┌` | Top-left corner | Box corners |
| `┐` | Top-right corner | Box corners |
| `└` | Bottom-left corner | Box corners |
| `┘` | Bottom-right corner | Box corners |
| `├` | Left tee | Branching left |
| `┤` | Right tee | Branching right |
| `┬` | Top tee | Branching up |
| `┴` | Bottom tee | Branching down |
| `┼` | Cross | Intersections |
| `▶` / `◀` | Arrows | Direction indicators |
| `▼` / `▲` | Arrows | Vertical direction |

## Pattern: Component Diagram

Use for **feature implementations** showing class/component relationships:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Component Name                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │ ConfigClass      │─────▶│ ServiceClass     │                 │
│  │                  │      │                  │                 │
│  │ • property1      │      │ • method1()      │                 │
│  │ • property2      │      │ • method2()      │                 │
│  └──────────────────┘      └────────┬─────────┘                 │
│                                     │                            │
│                                     ▼                            │
│                            ┌──────────────────┐                  │
│                            │ ExistingClass    │                  │
│                            │ (dependency)     │                  │
│                            └──────────────────┘                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Package: com.example.feature                                    │
│  New files: ConfigClass.java, ServiceClass.java                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Elements**:
- Outer box provides context (module/package)
- Inner boxes for individual components
- Arrows show dependencies
- Label existing vs new components
- Footer shows file locations

## Pattern: Before/After Comparison

Use for **refactoring tasks** showing transformation:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Refactoring Overview                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE                              AFTER                       │
│  ══════                              ═════                       │
│                                                                  │
│  ┌─────────────────────┐            ┌─────────────────────┐     │
│  │ MonolithClass       │            │ OrchestratorClass   │     │
│  │ (all in one)        │            │ (coordinates)       │     │
│  │                     │            │                     │     │
│  │ • methodA()         │    ───▶    │ • orchestrate()     │     │
│  │ • methodB()         │            └──────────┬──────────┘     │
│  │ • methodC()         │                       │                 │
│  │ • methodD()         │         ┌─────────────┼─────────────┐  │
│  └─────────────────────┘         │             │             │  │
│                                  ▼             ▼             ▼  │
│                           ┌───────────┐ ┌───────────┐ ┌───────────┐
│                           │ServiceA   │ │ServiceB   │ │ServiceC   │
│                           │• methodA  │ │• methodB  │ │• methodC  │
│                           │• methodD  │ │           │ │           │
│                           └───────────┘ └───────────┘ └───────────┘
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Elements**:
- Side-by-side BEFORE/AFTER
- Show method movement
- Transformation arrow (───▶)
- New dependency structure

## Pattern: Problem/Solution

Use for **bugfix tasks** showing the issue and fix:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Race Condition Fix                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PROBLEM: Concurrent token refresh                               │
│  ════════════════════════════════                                │
│                                                                  │
│  Thread A         Thread B         TokenStore                    │
│     │                │                 │                         │
│     │─── check() ───▶│                 │                         │
│     │◀── expired ────│                 │                         │
│     │                │─── check() ────▶│                         │
│     │                │◀── expired ─────│                         │
│     │─── refresh() ─▶│                 │  ← Both refresh!        │
│     │                │─── refresh() ──▶│                         │
│                                                                  │
│  SOLUTION: Lock-based coordination                               │
│  ═════════════════════════════════                               │
│                                                                  │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │ TokenManager     │─────▶│ RefreshLock      │                 │
│  │                  │      │ (new)            │                 │
│  │ • getToken()     │      │ • tryAcquire()   │                 │
│  │ • refresh()      │      │ • release()      │                 │
│  └──────────────────┘      └──────────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Elements**:
- Problem section shows failure scenario
- Sequence diagram for timing issues
- Solution section shows fix architecture
- Highlight new components

## Pattern: File Structure

Use for **documentation tasks** showing file organization:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Documentation Structure                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  docs/                                                           │
│  ├── README.md            ← Project overview                     │
│  ├── getting-started.md   ← New user guide                       │
│  ├── api/                                                        │
│  │   ├── overview.md      ← API introduction                     │
│  │   ├── endpoints.md     ← Endpoint reference                   │
│  │   └── authentication.md← Auth details                         │
│  ├── guides/                                                     │
│  │   ├── configuration.md ← Config guide                         │
│  │   └── troubleshooting.md← Problem solutions                   │
│  └── architecture/                                               │
│      ├── diagrams/        ← PlantUML sources                     │
│      │   └── *.puml                                              │
│      └── decisions/       ← ADRs                                 │
│          └── ADR-*.md                                            │
│                                                                  │
│  Cross-references:                                               │
│  README.md ────────▶ getting-started.md                          │
│  getting-started.md ─▶ api/overview.md                           │
│  api/*.md ──────────▶ guides/configuration.md                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Elements**:
- Tree structure for file hierarchy
- Annotations explaining purpose
- Cross-reference arrows
- Group related files

## Pattern: Integration Flow

Use for **plugin/integration tasks** showing data flow:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Build Cache Integration                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐             │
│  │ PRE-BUILD  │───▶│   BUILD    │───▶│ POST-BUILD │             │
│  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘             │
│        │                 │                 │                     │
│        ▼                 ▼                 ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Check Cache │  │ Execute     │  │ Store Cache │              │
│  │             │  │ Build       │  │             │              │
│  │ • hash deps │  │ • compile   │  │ • artifacts │              │
│  │ • lookup    │  │ • test      │  │ • metadata  │              │
│  └──────┬──────┘  └─────────────┘  └──────┬──────┘              │
│         │                                  │                     │
│         └──────────────────────────────────┘                     │
│                         │                                        │
│                         ▼                                        │
│                  ┌─────────────┐                                 │
│                  │ Cache Store │                                 │
│                  │ .cache/     │                                 │
│                  └─────────────┘                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Elements**:
- Phase boxes showing workflow
- Data flow arrows
- Component details
- Storage/state representation

## Simple Flow Patterns

For straightforward tasks, use minimal diagrams:

**Linear Flow**:
```
Request → Analyze → Implement → Verify → Done
```

**Branching Flow**:
```
Input ──┬── Path A ──┬── Output
        └── Path B ──┘
```

**Cycle**:
```
Start → Process → Check ─┬─ Pass → Done
                         └─ Fail → Process
```

## Tips for Clear Diagrams

1. **Consistent spacing**: Use fixed-width alignment
2. **Label everything**: Don't assume readers know context
3. **Show direction**: Arrows indicate data/control flow
4. **Distinguish new vs existing**: Use labels or notes
5. **Keep it simple**: Omit unnecessary detail
6. **Use outer box**: Provides visual boundary and context
7. **Add footer**: Package/file information helps navigation
