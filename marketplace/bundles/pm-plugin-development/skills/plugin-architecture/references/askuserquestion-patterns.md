# AskUserQuestion Patterns

Guide for using the `AskUserQuestion` tool effectively in marketplace components.

## Concept

The `AskUserQuestion` tool provides structured user interaction with predefined options. It automatically adds an "Other" option for free-text input.

### Tool Characteristics

| Aspect | Behavior |
|--------|----------|
| Options | 2-4 predefined options required |
| "Other" option | Automatically added by UI (not customizable) |
| "Other" label | Fixed as "Type something." (hardcoded) |
| Multi-select | Supported via `multiSelect: true` |
| Header | Max 12 characters |

### Schema

```typescript
interface AskUserQuestionTool {
  questions: Question[];      // 1-4 questions (required)
}

interface Question {
  question: string;           // Complete question text (required)
  header: string;             // Max 12 characters (required)
  multiSelect: boolean;       // Allow multiple selections (required)
  options: Option[];          // 2-4 options (required)
}

interface Option {
  label: string;              // 1-5 words, concise (required)
  description: string;        // Explanation of choice (required)
}
```

## Patterns

### Pattern 1: Selection with Free-Text Alternative

When you need users to either select from options OR provide custom input.

**Use Case**: Plan selection where user can also create new plan.

**Question Design**: Make it clear that "Type something" is for custom input.

```markdown
Question: "Select a plan, or use 'Type something' to enter a new task description:"
Options:
1. existing-plan-1 - [5-execute] in_progress
2. existing-plan-2 - [3-outline] pending
3. Cleanup completed plans - Remove finished plans
[Auto-added: Type something.]
```

**Handling Response**:
- If option selected: Execute corresponding action
- If "Type something" used: Treat input as task_description

### Pattern 2: Confirmation with Customization

When confirming a configuration but allowing modifications.

**Use Case**: Confirm detected settings before proceeding.

```markdown
Question: "Proceed with this configuration? Use 'Type something' to specify changes:"
Options:
1. Yes - Create plan with shown configuration
2. No - Cancel plan creation
[Auto-added: Type something.]
```

**Handling Response**:
- "Yes": Proceed with defaults
- "No": Exit workflow
- "Type something": Parse input for specific change requests

### Pattern 3: Type Selection

When user must choose between distinct types/modes.

**Use Case**: Select domain or execution mode.

```markdown
Question: "What type of plan for this task?"
Options:
1. Simple - 3-phase workflow (init, execute, finalize)
2. Implementation - 6-phase workflow with verification
[Auto-added: Type something.]
```

**Handling Response**:
- Map selection directly to domain
- "Type something" rarely used but could specify hybrid needs

### Pattern 4: Multi-Select Features

When users can enable multiple options simultaneously.

**Use Case**: Select which checks to run.

```markdown
Question: "Which validations should be performed?"
multiSelect: true
Options:
1. Syntax - Check file syntax
2. Links - Verify cross-references
3. Structure - Validate document structure
4. Completeness - Check for missing sections
[Auto-added: Type something.]
```

**Handling Response**:
- Collect all selected options
- Execute each validation type

## Anti-Patterns

### Anti-Pattern 1: Redundant "Create New" Option

**Problem**: Adding explicit "Create new" option when "Type something" serves that purpose.

```markdown
# BAD - Redundant options
Question: "Select a plan or action:"
Options:
1. existing-plan - Current plan
2. Create new plan - Start a new plan    <- Redundant!
3. Cleanup - Remove plans
[Auto-added: Type something.]
```

**Why It's Wrong**: "Create new plan" and "Type something" serve the same purpose, confusing users.

**Solution**: Remove "Create new plan", let "Type something" handle new task input.

```markdown
# GOOD - Clear purpose for each option
Question: "Select a plan, or use 'Type something' to enter a new task description:"
Options:
1. existing-plan - Current plan
2. Cleanup completed plans - Remove plans
[Auto-added: Type something.]
```

### Anti-Pattern 2: Follow-Up Questions After Selection

**Problem**: Asking redundant follow-up questions that contradict user's choice.

```markdown
# User selects "Create new plan"
# BAD - Contradicts their choice
Question: "How would you like to define the new plan?"
Options:
1. Continue existing - Resume existing plan   <- Contradicts!
2. Enter task description - Type description
```

**Why It's Wrong**: User already chose to create new, offering "Continue existing" is confusing.

**Solution**: Execute the action directly or ask only relevant follow-up.

### Anti-Pattern 3: Expecting Customizable "Other" Label

**Problem**: Documenting that "Other" label can be changed.

```markdown
# BAD - This doesn't work
- The automatic "Other" option becomes "Enter task description" contextually
```

**Why It's Wrong**: The "Type something." label is hardcoded in the UI and cannot be changed via the tool.

**Solution**: Acknowledge the fixed label and design questions to provide context.

```markdown
# GOOD - Acknowledge limitation
- Note: The "Type something" option is auto-added by AskUserQuestion for free-text input
```

### Anti-Pattern 4: Single Option Questions

**Problem**: Trying to use AskUserQuestion with only one meaningful option.

```markdown
# BAD - Doesn't meet minimum options requirement
Question: "Enter task description:"
Options:
1. Enter custom task - Type your description
```

**Why It's Wrong**: Tool requires 2-4 options minimum. Single option defeats purpose.

**Solution**: Use plain text prompt for pure free-text input, or add meaningful alternatives.

## Best Practices

### 1. Question Text Provides Context

Since "Type something." cannot be customized, make the question text explain what free-text input is for:

```markdown
# GOOD - Question explains purpose of "Type something"
"Select a plan, or use 'Type something' to enter a new task description:"
```

### 2. Direct Flow After Selection

Execute actions directly based on selection. Avoid intermediate confirmation questions.

```markdown
# User selects option → Execute immediately
# User types in "Other" → Use input directly
```

### 3. Options Should Be Mutually Exclusive

Each option should represent a distinct, non-overlapping choice.

```markdown
# GOOD - Each option is distinct
Options:
1. Java project - Uses Maven/Gradle
2. JavaScript project - Uses npm/npx
3. Mixed project - Both Java and JavaScript
```

### 4. Descriptions Should Clarify Consequences

Help users understand what happens when they select each option.

```markdown
Options:
1. Simple - 3-phase workflow (init, execute, finalize) - for quick tasks
2. Implementation - 6-phase workflow with build verification - for code changes
```

### 5. Handle "Type something" Gracefully

Always implement handling for free-text input, even if unexpected.

```python
if response == "Type something":
    # User provided custom input
    custom_text = get_custom_input()
    # Route to appropriate workflow based on content
else:
    # User selected predefined option
    execute_option(response)
```

## Known Limitations

| Limitation | Status | Workaround |
|------------|--------|------------|
| "Type something." label fixed | Cannot change | Use question text to provide context |
| No placeholder customization | Not supported | Document expected input in question |
| Multi-line input display issues | Known bug | First line only visible during input |
| Cannot remove "Other" option | By design | Always handle "Other" in workflow |
| Documentation missing | Acknowledged | Use community resources |

## References

- GitHub Issue #10346: Missing AskUserQuestion documentation
- GitHub Issue #10258: Cannot disable interactive question tool
- GitHub Issue #10848: Multi-line text input display issues
