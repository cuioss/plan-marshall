# Status Tracking Standards

Standards for task status indicators, task details, implementation notes, and task lifecycle management.

## Status Indicators

Use standard checkbox notation to track task status:

- `[ ]` - Task not started or in progress
- `[x]` - Task completed
- `[~]` - Task partially completed
- `[!]` - Task blocked or has issues

## Status Usage Examples

### Not Started / In Progress

Use `[ ]` for tasks that are pending or currently being worked on:

```asciidoc
* [ ] Implement token validation
* [ ] Add signature verification
```

### Completed

Use `[x]` for tasks that are fully completed:

```asciidoc
* [x] Implement token parsing
* [x] Add claim extraction
```

### Partially Completed

Use `[~]` for tasks that are partially done with a note explaining what remains:

```asciidoc
* [~] Implement error handling (basic errors done, need edge cases)
```

### Blocked

Use `[!]` for tasks that are blocked, with a note explaining the blocker:

```asciidoc
* [!] Add Redis caching (waiting for Redis infrastructure)
```

## Task Details

Add notes and context to provide helpful information:

```asciidoc
* [ ] Implement JWT validation
  ** Must support RS256 and HS256 algorithms
  ** Need to decide on key rotation strategy
* _Note: Key rotation design needs review with security team_
* _Important: This blocks API authentication implementation_
```

## Implementation Notes

### Note Types

Use different note patterns for different purposes:

**General notes**:
```asciidoc
* _Note: Consider caching validated tokens for performance_
```

**Important information**:
```asciidoc
* _Important: This must be completed before phase 2 can start_
```

**Blockers**:
```asciidoc
* _Blocked: Waiting for security review approval_
```

**Dependencies**:
```asciidoc
* _Depends on: Completion of task XYZ in section ABC_
```

**Decisions needed**:
```asciidoc
* _Decision needed: Choose between Redis and Hazelcast for caching_
```

## Task Lifecycle

### Adding Tasks

1. Identify the appropriate section
2. Link to relevant requirement or specification
3. Provide clear, actionable description
4. Mark with appropriate status
5. Add notes for context if needed

### Completing Tasks

1. Change status from `[ ]` to `[x]`
2. Verify implementation meets requirements
3. Update related specifications if needed
4. Don't remove completed tasks - leave for project history

### Refactoring Tasks

1. Break down tasks that are too large
2. Merge tasks that are too granular
3. Reorganize sections as understanding improves
4. Maintain traceability links throughout

## See Also

- [Document Structure Standards](document-structure.md) - Overall planning document structure
- [Task Organization Standards](task-organization.md) - Hierarchical task organization
- [Maintenance Standards](maintenance.md) - Keeping planning documents current
