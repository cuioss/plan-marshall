# Error Handling

> These error types are referenced by the wizard, menu, and healthcheck flows. Each error includes a recovery action that the steward skill should execute.

Common error types and recovery guidance.

---

## Missing Executor

```toon
status: error
error: missing_executor
message: .plan/execute-script.py not found
recovery: Run first-run wizard to generate executor
```

**Resolution**: Run `/marshall-steward --wizard` or select "Full Reconfigure" from Configuration menu.

---

## Invalid Marshal.json

```toon
status: error
error: invalid_config
message: Failed to parse marshal.json
recovery: Delete and re-run wizard, or fix JSON syntax
```

**Resolution**:
1. Check `.plan/marshal.json` for JSON syntax errors
2. Or delete the file and run `/marshall-steward --wizard`

---

## Script Not Found

```toon
status: error
error: script_not_found
message: Script notation not found in executor
recovery: Regenerate executor via Maintenance menu
```

**Resolution**: Select "Maintenance" -> "Regenerate Executor" from Main Menu.

---

## Permission Denied

```toon
status: error
error: permission_denied
message: Cannot write to {path}
recovery: Check file permissions or run with appropriate access
```

**Resolution**: Check file system permissions for the target path.

---

## Build System Not Detected

```toon
status: error
error: no_build_system
message: No supported build system found (Maven/Gradle/npm)
recovery: Ensure project contains pom.xml, build.gradle, or package.json
```

**Resolution**: Verify project structure includes a supported build configuration file.

---

## Plugin Root Not Found

```toon
status: error
error: plugin_root_missing
message: ${PLUGIN_ROOT} not set or invalid
recovery: Ensure skill invoked via /marshall-steward command
```

**Resolution**: Use the `/marshall-steward` command to invoke this skill properly.

---

## Script Execution Timeout

```toon
status: error
error: timeout
message: Script execution exceeded timeout
recovery: Check for infinite loops or increase timeout
```

**Resolution**: The script took too long. Check for build system hangs, network issues, or increase the timeout via `--timeout` flag.

---

## JSON Parse Error in Script Arguments

```toon
status: error
error: invalid_arguments
message: Failed to parse JSON argument
recovery: Check argument format matches expected JSON structure
```

**Resolution**: Verify CLI arguments contain valid JSON. Check for unquoted strings or missing brackets.

---

## Extension Discovery Failed

```toon
status: error
error: extension_error
message: Extension {bundle} failed during discovery
recovery: Check extension.py in the failing bundle
```

**Resolution**: The extension's `discover_modules()` or `get_skill_domains()` raised an error. Check the bundle's `extension.py` for bugs. Non-failing extensions continue normally.
