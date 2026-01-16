# Workflow Overview Diagram

Visual summary of the phase-2-outline workflow for human reference.

```
┌──────────────────────────────────────────────────────────────────┐
│                ARCHITECTURE-DRIVEN WORKFLOW                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: Load architecture context                               │
│          → architecture info                                     │
│                                                                  │
│  Step 2: Load and understand requirements                        │
│          → manage-plan-documents read --type request             │
│                                                                  │
│  Step 2.5: Load outline extension (if domain has one)            │
│          → resolve-workflow-skill-extension --type outline       │
│          → Extensions implement protocol with defined sections   │
│                                                                  │
│  Step 3: Assess complexity via extension protocol                │
│          → Call extension's ## Assessment Protocol               │
│          → Returns: simple|complex, conditional standards        │
│                                                                  │
│  Step 4: Execute workflow via extension protocol                 │
│          → Call ## Simple Workflow or ## Complex Workflow        │
│          → Use ## Discovery Patterns for file enumeration        │
│                                                                  │
│  Step 5: Determine package placement (for module-based domains)  │
│          → architecture module --name X --full                   │
│                                                                  │
│  Step 6: Create deliverables with Profiles list                  │
│          → One deliverable per module                            │
│          → Profiles list (implementation, testing as needed)     │
│                                                                  │
│  Step 7: Create IT deliverable (optional)                        │
│          → architecture modules --command integration-tests      │
│          → Separate deliverable targeting IT module              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Extension Protocol Interaction

```
phase-2-outline                           ext-outline-{domain}
═══════════════                           ════════════════════

Step 1-2: Load architecture, requirements
              │
              ▼
Step 2.5: Load extension ────────────────► SKILL.md loaded
              │
              ▼
Step 3: ┌─────────────────────────────┐
        │ Call: ## Assessment Protocol │
        │                              │────► Evaluates criteria
        │ "Which workflow applies?"    │      Returns: simple|complex
        └─────────────────────────────┘
              │
              ▼
Step 4: ┌─────────────────────────────┐
        │ Call: ## Simple/Complex      │
        │ Workflow (based on Step 3)   │────► Loads path-single or
        └─────────────────────────────┘      path-multi workflow
              │
              ▼
Step 4b: ┌─────────────────────────────┐
         │ Use: ## Discovery Patterns   │────► Provides Glob/Grep
         │ "Find affected files"        │      for file enumeration
         └─────────────────────────────┘
              │
              ▼
Step 5+: Load conditional standards
Step 8:  Write solution document
```
