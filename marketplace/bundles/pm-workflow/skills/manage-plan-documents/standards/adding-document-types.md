# Adding New Document Types

## Overview

Adding a new document type requires **no Python code changes**. Create two files:
1. Document definition: `documents/{type}.toon`
2. Template: `templates/{type}.md`

---

## Step 1: Create Document Definition

Create `documents/{type}.toon` with this structure:

```toon
name: {type_name}
file: {physical_filename}
template: templates/{template_file}

fields[N]{name,type,required,default}:
{field_name},{field_type},{true|false},{default_value}
...

sections[N]{name,heading,order}:
{section_name},{markdown_heading},{display_order}
...
```

### Field Types

| Type | Description | Validation | Example |
|------|-------------|------------|---------|
| `string` | Single-line text | Non-empty if required | `title,string,true,` |
| `text` | Multi-line text | Non-empty if required | `body,text,true,` |
| `enum(a\|b\|c)` | Enumerated values | Must match one | `status,enum(draft\|final),true,` |
| `date` | ISO timestamp | Valid ISO format | `created,date,false,` |
| `list` | Pipe-separated values | Split on `\|` | `tags,list,false,` |

### Example: `documents/retrospective.toon`

```toon
name: retrospective
file: retrospective.md
template: templates/retrospective.md

fields[4]{name,type,required,default}:
summary,text,true,
went_well,list,false,
improvements,list,false,
actions,list,false,

sections[4]{name,heading,order}:
summary,## Summary,1
went_well,## What Went Well,2
improvements,## Areas for Improvement,3
actions,## Action Items,4
```

---

## Step 2: Create Template

Create `templates/{type}.md` with placeholders matching field names:

```markdown
# {document_title}: {plan_id}

created: {timestamp}

## Summary

{summary}

## What Went Well

{went_well}

## Areas for Improvement

{improvements}

## Action Items

{actions}
```

### Placeholder Rules

- Use `{field_name}` syntax
- Built-in placeholders: `{plan_id}`, `{timestamp}`
- Optional fields render as empty string if not provided
- List fields render as-is (pipe-separated input preserved)

---

## Step 3: Use It

The new document type is immediately available:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  retrospective create \
  --plan-id my-feature \
  --summary "Completed JWT implementation" \
  --went_well "Clean API design|Good test coverage" \
  --improvements "Documentation lag"
```

---

## Checklist

- [ ] Document definition created: `documents/{type}.toon`
- [ ] All required fields marked with `true`
- [ ] Field types match expected input format
- [ ] Template created: `templates/{type}.md`
- [ ] Template placeholders match field names
- [ ] Sections defined in logical order
