# Crossing Inventory — PLAN-08

Every place `permission_common.py`, `permission_doctor.py`, and `permission_fix.py`
either import `claude_runtime` directly or render/parse a permission-DSL string,
with the intent each site expresses.

Generated before any code changes (D1 stop condition).

---

## permission_common.py — Direct `claude_runtime` imports (6 symbols)

| # | File | Symbol | Intent |
|---|------|--------|--------|
| C1 | permission_common.py:33 | `_claude_global_settings_path` | Select which settings file to read/write for global scope |
| C2 | permission_common.py:34 | `_claude_project_settings_path` | Select which settings file to write for project scope |
| C3 | permission_common.py:35 | `_claude_project_settings_read_path` | Select which settings file to read for project scope |
| C4 | permission_common.py:36 | `_load_settings` | Load settings data from a JSON file |
| C5 | permission_common.py:37 | `_save_settings` | Persist settings data to a JSON file |
| C6 | permission_common.py:40 | `ensure_default_permissions` | Ensure the default permission set and prune retired rules |

No DSL rendering or parsing in this file.

## permission_doctor.py — Direct `claude_runtime` imports (3 symbols)

| # | File | Symbol | Intent |
|---|------|--------|--------|
| D1 | permission_doctor.py:28 | `_load_marshal_config` | Load and parse marshal.json configuration |
| D2 | permission_doctor.py:29 | `_extract_project_steps` | Enumerate project:{skill} step references from marshal config |
| D3 | permission_doctor.py:30 | `_skill_permission_covered` | Check if a skill is covered by an allow rule |

## permission_doctor.py — DSL parsing sites (3 functions, 25+ regex sites)

| # | File:Line | Symbol | Intent |
|---|-----------|--------|--------|
| P1 | permission_doctor.py:59 | `is_marketplace_permission` (Skill/ prefix) | Classify a permission as marketplace vs. project-local |
| P2 | permission_doctor.py:63 | `is_marketplace_permission` (SlashCommand/ prefix) | Classify a SlashCommand permission |
| P3 | permission_doctor.py:65 | `re.match(r'^SlashCommand\(/([^)]+)\)$')` | Extract command name from SlashCommand DSL form |
| P4 | permission_doctor.py:82 | `extract_permission_parts` | Split permission DSL into type and pattern components |
| P5 | permission_doctor.py:88-107 | `is_covered_by_wildcard` | Check if a specific permission is subsumed by a broader wildcard |
| P6 | permission_doctor.py:193-318 | `SUSPICIOUS_PATTERNS` (25 regexes) | Match rendered DSL strings against anti-pattern rules |
| P7 | permission_doctor.py:344 | `re.match(pattern_info['pattern'], permission)` | Apply DSL-matching patterns to actual rules |

## permission_fix.py — No direct `claude_runtime` imports (reaches via permission_common)

## permission_fix.py — DSL rendering sites (6 sites)

| # | File:Line | Symbol | Intent |
|---|-----------|--------|--------|
| R1 | permission_fix.py:66 | `EXECUTOR_PERMISSION` constant | Represent the executor permission rule |
| R2 | permission_fix.py:67 | `OVERLY_BROAD_PYTHON` constant | Represent the overly-broad Python permission |
| R3 | permission_fix.py:352-367 | `generate_wildcard` | Render a timestamp-consolidated wildcard permission |
| R4 | permission_fix.py:477-498 | `generate_required_wildcards` | Render Skill(bundle:*) and SlashCommand(/bundle:*) wildcards |
| R5 | permission_fix.py:715 | `f'Skill({entry["skill"]})'` in `cmd_apply_project_step_permissions` | Render a project-step Skill permission |
| R6 | permission_fix.py:775-799 | `generate_skill_wildcards`, `generate_command_bundle_wildcards`, `generate_command_shortform_permissions` | Render Skill and SlashCommand wildcards from marketplace inventory |

## permission_fix.py — DSL parsing sites (4 sites)

| # | File:Line | Symbol | Intent |
|---|-----------|--------|--------|
| Q1 | permission_fix.py:82-83 | `TIMESTAMP_PATTERN`, `DATE_PATTERN` regexes | Parse timestamp and date components from permission strings |
| Q2 | permission_fix.py:91-104 | `normalize_path_perm` | Parse and normalize a permission path (strip trailing slash) |
| Q3 | permission_fix.py:304-349 | `parse_timestamped_permission` | Extract type, path, base name, timestamp, extension from DSL |
| Q4 | permission_fix.py:1028-1030 | `is_individual_script_permission` | Check if a permission matches the individual-script pattern |

---

**Total: 9 direct `claude_runtime` imports (6 + 3), 6 DSL rendering sites, 11 DSL parsing sites (7 in doctor + 4 in fix).**
