# Documentation Update Workflow

Traceability-specific guidance for updating documentation through implementation lifecycle phases.

For the complete lifecycle model (PLANNED → IN PROGRESS → IMPLEMENTED → DEPRECATED), see `pm-requirements:requirements-authoring` → `standards/documentation-lifecycle-management.md`.

## Traceability Updates by Phase

### Pre-Implementation (PLANNED)
- Write comprehensive specification with design and expected API
- No implementation links yet — spec defines "what" and "how"

### During Implementation (IN PROGRESS)
- Add implementation links as classes are created
- Add JavaDoc with specification references (see `code-to-specification-linking.md`)
- Document implementation decisions and library choices
- Update status indicator

### Post-Implementation (IMPLEMENTED)
- Complete all traceability links (spec → code → tests)
- Add test references in Verification section
- Remove redundant code examples that duplicate implementation
- Keep architectural guidance and design rationale
- Refer readers to JavaDoc for detailed API behavior

## Separation of Concerns

| Document | Contains | Does NOT Contain |
|----------|----------|------------------|
| Specification | What and why | Implementation details |
| JavaDoc | How and when | Architecture decisions |
| Tests | Validation and coverage | Design rationale |

Use cross-references instead of duplicating information across these layers. Update links immediately when classes are created.
