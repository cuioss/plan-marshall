# agents.md

This is a Claude Code Marketplace repository providing development standards, automation tools, and AI-assisted workflows for CUI (Common User Interface) Open Source projects. It contains 8 production bundles with 95 components (skills, agents, and commands).

## Dev Environment Tips

### Project Structure

This is a documentation-only repository with no build system, compilation, or testing framework to execute.

```
plan-marshall/
├── marketplace/                    # Claude Code marketplace system
│   ├── .claude-plugin/
│   │   └── marketplace.json        # Master marketplace configuration
│   └── bundles/                    # 8 production bundles
├── test/                           # Python pytest tests for scripts
├── .plan/                          # Planning and temp files (gitignored)
└── .claude/                        # Project-level Claude Code configuration
```

### The 8 Production Bundles

| Bundle | Purpose |
|--------|---------|
| **pm-dev-java** | Java development standards, CDI/Quarkus, JUnit 5, logging |
| **pm-dev-frontend** | JavaScript, CSS, Jest, Cypress, ESLint/Prettier |
| **pm-dev-builder** | Maven/Gradle/npm unified build automation |
| **pm-documents** | AsciiDoc, ADRs, interface specifications |
| **plan-marshall** | Utilities, permissions, file operations |
| **pm-plugin-development** | Plugin creation, quality diagnosis |
| **pm-requirements** | Requirements authoring and traceability |

### Component Model

Each bundle contains three types of components:

- **Skills** (28 total): Domain knowledge and standards loaded before work begins
- **Agents** (28 total): Autonomous task executors with focused responsibilities
- **Commands** (39 total): User-invokable slash commands orchestrating workflows

### Bundle Structure

```
bundle-name/
├── .claude-plugin/
│   └── plugin.json         # Bundle manifest
├── agents/                 # Specialized agents (*.md)
├── commands/               # Slash commands (*.md)
├── skills/                 # Development standards
│   └── skill-name/
│       ├── SKILL.md        # Skill definition
│       ├── standards/      # Detailed documents
│       ├── scripts/        # Python/Bash scripts
│       └── templates/      # Document templates
└── README.md
```

### File Formats

- **Skills/Commands/Agents**: Markdown with YAML frontmatter
- **Standards documents**: Markdown (some AsciiDoc templates)
- **Scripts**: Python and Bash in `skills/*/scripts/`
- **Configuration**: JSON for plugin.json, marketplace.json

### Naming Conventions

- Files and commands: `kebab-case` (e.g., `java-implement-code.md`)
- Bundles: Descriptive names with domain prefix (e.g., `pm-dev-java`)
- Skills: Domain-specific names (e.g., `cui-java-core`, `plan-refine`)

## Testing Instructions

See [test/README.md](test/README.md) for full documentation.

```bash
python3 test/run-tests.py                                          # all tests
python3 test/run-tests.py test/planning/                           # directory
python3 test/run-tests.py test/planning/plan-files/test_parse_plan.py  # single file
```

### Quality Checks

Use the plugin doctor command to diagnose quality issues:

```bash
/plugin-doctor
```

Quality scores should be ≥75/100 for all components.

## PR Instructions

### Title Format

Use conventional commit format:
- `feat(bundle): description` - New features
- `fix(bundle): description` - Bug fixes
- `docs(bundle): description` - Documentation changes
- `refactor(bundle): description` - Code refactoring

### Pre-Submission Checklist

1. All Python tests pass (`pytest test/`)
2. Plugin doctor shows no critical issues
3. No duplicate information across documents
4. Cross-references use proper `xref:` syntax (AsciiDoc) or markdown links
5. No version history, changelogs, or timestamps in documents

### Documentation Standards

- Document current state only, not transitional information
- Use cross-references instead of duplicating content
- Ensure blank line before lists in AsciiDoc
- Use `.plan/temp/` for generated or temporary files

## Tool Usage

### Preferred Tools

- **File operations**: Use Edit, Read, Write tools (not shell commands)
- **File search**: Use Glob tool (not `find` or `ls`)
- **Content search**: Use Grep tool (not `grep` or `rg` commands)
- **GitHub access**: Use `gh` CLI tool (not GitHub MCP)
- **Temporary files**: Use `.plan/temp/` for ALL temp files (covered by `Write(.plan/**)` permission - avoids permission prompts)

### Agent Coordination

Commands orchestrate agents using the Task tool. Agents:
- Have focused, single responsibilities
- Return structured JSON with status, data, and metrics
- Use haiku model for read-only/analysis tasks
- Use sonnet model for implementation tasks

## Integration Points

- **Git**: Standard workflow on main branch
- **Build Systems**: None (documentation-only)
- **IDE**: IntelliJ MCP for diagnostics (file must be active in editor)
- **GitHub**: Via `gh` CLI for issue/PR management
