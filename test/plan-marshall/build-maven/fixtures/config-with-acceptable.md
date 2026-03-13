# Run Configuration

Project-specific build configuration.

## Build Settings

Default goals: clean install
Profile: pre-commit

## Acceptable Warnings

### Transitive Dependency Warnings

These warnings are from dependencies outside our control:

- `[WARNING] The POM for com.example:transitive-dep:jar:1.0.0 is missing`
- `[WARNING] Using platform encoding UTF-8`

### Plugin Compatibility

Known plugin compatibility issues:

- `[WARNING] maven-compiler-plugin.*source value 11`

## Other Settings

Timeout: 120000
