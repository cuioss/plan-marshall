# Planning Document Maintenance Standards

Standards for keeping planning documents current, managing task lifecycle, and ensuring quality.

## Living Documentation Principle

Planning documents are dynamic and must reflect current project state:

- Updated frequently as work progresses
- Tasks are added, completed, and refined
- Status indicators change as implementation evolves
- Not archived - remains active throughout project

## Keeping Documents Current

### Update Frequency

Update planning documents whenever:

- Tasks are completed
- New tasks are discovered
- Tasks are blocked or unblocked
- Implementation priorities change

### Regular Reviews

Review planning documents:

- At start of each development sprint/cycle
- When major milestones are reached
- When project scope changes

## Archive Strategy

**Don't archive** planning documents - they serve as project history.

**Completed tasks** remain in place with `[x]` status to provide:

- Historical record of what was implemented
- Context for future work
- Reference for similar projects

**New features** get new sections or documents rather than replacing existing content.

## Quality Standards

### Clarity

- Tasks are clear and actionable
- Status indicators are current and accurate
- Notes provide helpful context
- Organization is logical and navigable

### Completeness

- All implementation areas are covered
- Testing is comprehensively planned
- Documentation tasks are included
- Dependencies are identified

### Traceability

- Every task group links to requirements or specifications
- Navigation between documents is seamless
- Related tasks are grouped together
- Blockers and dependencies are explicit

### Maintainability

- Document is updated as work progresses
- Completed tasks are marked
- Structure adapts to project evolution
- Remains a useful reference throughout project lifecycle

## Common Anti-Patterns to Avoid

### Overly Detailed Tasks

**Bad**: Breaking tasks down to individual method implementations

```asciidoc
* [ ] Create getUserById() method
* [ ] Create getUserByEmail() method
* [ ] Create saveUser() method
```

**Good**: Grouping related work into cohesive tasks

```asciidoc
* [ ] Implement UserRepository interface with CRUD operations
```

### Missing Traceability

**Bad**: Task lists without links to requirements

```asciidoc
==== User Management
* [ ] Add user validation
* [ ] Create user service
```

**Good**: Every task group references its source requirement

```asciidoc
==== User Management
_See Requirement USR-1: User Management in link:Requirements.adoc[Requirements]_

* [ ] Add user validation
* [ ] Create user service
```

### Stale Status

**Bad**: Leaving planning document unchanged for weeks despite active development

**Good**: Updating status as work progresses, reflecting current reality

### Implementation Details

**Bad**: Including code snippets and detailed algorithms in planning document

```asciidoc
* [ ] Implement validation using:
  ** Regex pattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
  ** Check domain against blacklist
  ** Verify MX records exist
```

**Good**: Referencing specifications for implementation guidance

```asciidoc
* [ ] Implement email validation per link:specification/validation.adoc[Validation Specification]
```

## See Also

- [Document Structure Standards](document-structure.md) - Planning document structure
- [Status Tracking Standards](status-tracking.md) - Task lifecycle management
- [Traceability Standards](traceability.md) - Linking to requirements
