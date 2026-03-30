# JSDoc Violation Analysis Workflow

Analyzes JavaScript files for JSDoc compliance violations and returns structured results.

**When to use**: To identify missing or incomplete JSDoc documentation across files or directories.

## Steps

### 1. Run violation analysis script

Script: `pm-dev-frontend:javascript` -> `jsdoc.py`

```bash
# Analyze entire directory
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze --directory src/

# Analyze single file
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze --file src/utils/formatter.js

# Analyze only for missing JSDoc (skip syntax checks)
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze --directory src/ --scope missing

# Analyze only JSDoc syntax issues
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze --directory src/ --scope syntax
```

### 2. Process violation results

Review violations categorized by severity:
- **CRITICAL**: Exported/public API without JSDoc
- **WARNING**: Internal function without JSDoc, missing @param/@returns
- **SUGGESTION**: Missing optional tags (@example, @fileoverview)

Note `fix_suggestion` for each violation.

### 3. Prioritize fixes

- Fix CRITICAL violations first (exported functions/classes)
- Address WARNING violations next
- SUGGESTION items are optional improvements

## TOON Output Contract

```toon
status: violations_found

data:
  violations[1]{file,line,type,severity,target,message,fix_suggestion}:
  src/utils/validator.js,45,missing_jsdoc,CRITICAL,function validateEmail,Exported function missing JSDoc documentation,Add JSDoc block with @param and @returns tags
  files_analyzed[1]:
  - src/utils/validator.js

metrics:
  total_files: 15
  files_with_violations: 6
  critical: 5
  warnings: 12
  suggestions: 3
  total_violations: 20
```

## Violation Types

- `missing_jsdoc` - Function/class entirely missing JSDoc
- `missing_class_doc` - Class without documentation
- `missing_constructor_doc` - Constructor with parameters undocumented
- `missing_param` - @param tag missing for parameter
- `missing_param_type` - Type annotation missing in @param
- `missing_returns` - @returns tag missing for return value
- `missing_fileoverview` - No @fileoverview at file level

## Scope Options

- `all` - Check for missing JSDoc and syntax issues (default)
- `missing` - Only check for missing JSDoc documentation
- `syntax` - Only check JSDoc syntax and completeness
