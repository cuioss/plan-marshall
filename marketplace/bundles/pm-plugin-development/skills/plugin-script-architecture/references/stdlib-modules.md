# Allowed Python Standard Library Modules

## Core Modules

| Module | Purpose |
|--------|---------|
| `json` | JSON parsing/generation |
| `argparse` | CLI argument parsing |
| `pathlib` | Path manipulation |
| `re` | Regular expressions |
| `sys` | System-specific parameters |
| `os` | Operating system interface |
| `datetime` | Date/time handling |
| `shutil` | File operations |
| `subprocess` | Process spawning |
| `tempfile` | Temporary files |
| `textwrap` | Text wrapping |
| `collections` | Container datatypes |
| `typing` | Type hints |
| `dataclasses` | Data classes |
| `functools` | Higher-order functions |
| `itertools` | Iterator utilities |
| `contextlib` | Context managers |
| `io` | I/O streams |
| `hashlib` | Hashing |
| `base64` | Base64 encoding |
| `urllib.parse` | URL parsing |
| `difflib` | Diff utilities |
| `unittest` | Unit testing framework |
| `time` | Time utilities |
| `copy` | Shallow/deep copy |
| `logging` | Logging facility |
| `string` | String constants |
| `enum` | Enumerations |
| `uuid` | UUID generation |
| `glob` | Filename pattern matching |
| `fnmatch` | Unix filename matching |

## Prohibited

Any module requiring `pip install`:

| Module | Why Prohibited |
|--------|----------------|
| `yaml` / `PyYAML` | External dependency |
| `requests` | External dependency |
| `numpy` | External dependency |
| `pandas` | External dependency |
| `toml` (Python < 3.11) | External dependency |
| Any third-party package | Portability requirement |

## Rationale

Scripts must work on any system with Python 3 installed, without requiring package installation. This ensures:

1. **Portability** - Scripts run anywhere
2. **No setup** - No `pip install` required
3. **Reproducibility** - Same behavior across environments
4. **Security** - No supply chain risks from dependencies

## PyYAML Replacement

For simple YAML frontmatter parsing, use custom parser:

```python
def parse_simple_yaml(content: str) -> dict:
    """Parse simple YAML frontmatter (key:value pairs only)."""
    result = {}
    for line in content.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    return result
```

See `standards/python-implementation.md` for complete pattern.
