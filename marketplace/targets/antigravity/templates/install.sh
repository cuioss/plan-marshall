#!/usr/bin/env bash
# SPDX-License-Identifier: FSL-1.1-ALv2
set -euo pipefail

REPO="cuioss/plan-marshall"
DEFAULT_REF="dist-antigravity"
DEFAULT_GLOBAL_DIR="${HOME}/.gemini/config/plugins/plan-marshall"
DEFAULT_WORKSPACE_DIR="${PWD}/.agents/plugins/plan-marshall"

SCOPE="global"
TARGET_DIR=""
REF="${DEFAULT_REF}"
UNINSTALL=false
UPDATE=false
MODE=""
BUNDLES=""
WITHOUT_BUNDLES=""

show_help() {
  cat <<'EOF'
Plan Marshall - Google Antigravity Plugin Installer

Usage:
  curl -fsSL https://raw.githubusercontent.com/cuioss/plan-marshall/dist-antigravity/install.sh | bash
  ./install.sh [OPTIONS]

Options:
  -g, --global             Install globally to ~/.gemini/config/plugins/plan-marshall (default)
  -w, --workspace          Install locally to <cwd>/.agents/plugins/plan-marshall
  -t, --target-dir PATH    Install to a custom directory
  -r, --ref REF            Branch or tag to install (default: dist-antigravity)
  --all                    Install core and all domain bundles (default)
  --core-only              Install only mandatory core (plan-marshall)
  -b, --bundles <csv>      Comma-separated list of bundles or aliases to install
  --without-bundles <csv>  Exclude specific domain bundles or aliases
  -U, --update             Update installation preserving selection or applying changes
  -u, --uninstall          Remove the installed plugin (or use with -b to remove specific bundles)
  -h, --help               Show this help message

Aliases:
  all         All bundles present in distribution
  core        Mandatory core (plan-marshall)
  java        pm-dev-java, pm-dev-java-cui
  python      pm-dev-python
  frontend    pm-dev-frontend, pm-dev-frontend-cui
  oci         pm-dev-oci
  docs        pm-documents
  reqs        pm-requirements
  plugin-dev  pm-plugin-development
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -g|--global)
      SCOPE="global"
      shift
      ;;
    -w|--workspace)
      SCOPE="workspace"
      shift
      ;;
    -t|--target-dir)
      if [ -z "${2:-}" ]; then
        echo "Error: --target-dir requires an argument" >&2
        exit 1
      fi
      TARGET_DIR="$2"
      SCOPE="custom"
      shift 2
      ;;
    -r|--ref)
      if [ -z "${2:-}" ]; then
        echo "Error: --ref requires an argument" >&2
        exit 1
      fi
      REF="$2"
      shift 2
      ;;
    --all)
      MODE="all"
      shift
      ;;
    --core-only)
      MODE="core-only"
      shift
      ;;
    -b|--bundles)
      if [ -z "${2:-}" ]; then
        echo "Error: --bundles requires an argument" >&2
        exit 1
      fi
      MODE="bundles"
      BUNDLES="$2"
      shift 2
      ;;
    --without-bundles)
      if [ -z "${2:-}" ]; then
        echo "Error: --without-bundles requires an argument" >&2
        exit 1
      fi
      WITHOUT_BUNDLES="$2"
      shift 2
      ;;
    -U|--update)
      UPDATE=true
      shift
      ;;
    -u|--uninstall)
      UNINSTALL=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help >&2
      exit 1
      ;;
  esac
done

if [ "$UPDATE" = true ] && [ "$UNINSTALL" = true ]; then
  echo "Error: Cannot combine --update and --uninstall" >&2
  exit 1
fi

# Detect whether running locally or remotely
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -z "$TARGET_DIR" ]; then
  if [ -n "$SCRIPT_DIR" ] && ([ -f "$SCRIPT_DIR/.install-manifest.json" ] || [ -f "$SCRIPT_DIR/plugin.json" ]) && ([ "$UNINSTALL" = true ] || [ "$UPDATE" = true ]); then
    TARGET_DIR="$SCRIPT_DIR"
  elif [ "$SCOPE" = "workspace" ]; then
    TARGET_DIR="${DEFAULT_WORKSPACE_DIR}"
  else
    TARGET_DIR="${DEFAULT_GLOBAL_DIR}"
  fi
fi

# Full uninstall shortcut for Antigravity (preserves prior behaviour)
if [ "$UNINSTALL" = true ] && [ -z "$BUNDLES" ]; then
  if [ -d "$TARGET_DIR" ]; then
    echo "Uninstalling Plan Marshall Antigravity plugin from: $TARGET_DIR"
    rm -rf "$TARGET_DIR"
    echo "Uninstallation complete."
  else
    echo "No installation found at: $TARGET_DIR"
  fi
  exit 0
fi

# Interactive bundle selection prompt if no bundle flags provided
INTERACTIVE=false
if [ -z "${CI:-}" ] && [ -z "${PLAN_MARSHALL_NON_INTERACTIVE:-}" ] && [ -z "${DEBIAN_FRONTEND:-}" ]; then
  if [ -t 0 ] || ( [ -t 1 ] && ( : </dev/tty ) 2>/dev/null ); then
    INTERACTIVE=true
  fi
fi

if [ -z "$MODE" ] && [ -z "$BUNDLES" ] && [ -z "$WITHOUT_BUNDLES" ] && [ "$UPDATE" = false ] && [ "$UNINSTALL" = false ]; then
  if [ "$INTERACTIVE" = true ]; then
    echo "Plan Marshall Bundle Selection:" >/dev/tty
    echo "  Core: plan-marshall [MANDATORY]" >/dev/tty
    echo "  Available domain aliases: java, python, frontend, oci, docs, reqs, plugin-dev" >/dev/tty
    read -r -p "[A]ll (default), [C]ore only, or comma-separated bundles/aliases: " USER_INPUT </dev/tty || USER_INPUT=""
    case "$USER_INPUT" in
      ""|[Aa]|[Aa][Ll][Ll])
        MODE="all"
        ;;
      [Cc]|[Cc][Oo][Rr][Ee])
        MODE="core-only"
        ;;
      *)
        MODE="bundles"
        BUNDLES="$USER_INPUT"
        ;;
    esac
  else
    MODE="all"
  fi
fi

CLEANUP_TMP=false
TMP_DIR=""

if [ "$UNINSTALL" = true ] && [ -n "$BUNDLES" ]; then
  if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: No installation found at: $TARGET_DIR" >&2
    exit 1
  fi
  if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/bundle-components.json" ]; then
    SOURCE_DIR="$SCRIPT_DIR"
  elif [ -f "$TARGET_DIR/bundle-components.json" ]; then
    SOURCE_DIR="$TARGET_DIR"
  else
    SOURCE_DIR="$TARGET_DIR"
  fi
elif [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/plugin.json" ] && [ -d "$SCRIPT_DIR/skills" ] && [ ! -f "$SCRIPT_DIR/.install-manifest.json" ]; then
  SOURCE_DIR="$SCRIPT_DIR"
  echo "Installing Plan Marshall Antigravity plugin from local source: $SOURCE_DIR"
else
  TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'plan-marshall-antigravity')"
  CLEANUP_TMP=true
  trap 'if [ "$CLEANUP_TMP" = true ] && [ -d "$TMP_DIR" ]; then rm -rf "$TMP_DIR"; fi' EXIT

  if [[ "$REF" =~ ^v[0-9] ]]; then
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/tags/antigravity/${REF}.tar.gz"
  elif [[ "$REF" =~ ^antigravity/v ]]; then
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/tags/${REF}.tar.gz"
  else
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/heads/${REF}.tar.gz"
  fi

  echo "Downloading Plan Marshall (${REF}) from ${ARCHIVE_URL}..."
  curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$TMP_DIR" --strip-components=1
  SOURCE_DIR="$TMP_DIR"
fi

if [ "$UNINSTALL" = false ] && [ ! -f "$SOURCE_DIR/plugin.json" ]; then
  echo "Error: plugin.json not found in source directory ($SOURCE_DIR)." >&2
  exit 1
fi

ACTION="install"
if [ "$UNINSTALL" = true ]; then
  ACTION="uninstall"
elif [ "$UPDATE" = true ]; then
  ACTION="update"
fi

python3 - "$SOURCE_DIR" "$TARGET_DIR" "$ACTION" "antigravity" "$SCOPE" "$REF" "$MODE" "$BUNDLES" "$WITHOUT_BUNDLES" << 'EOF_PYTHON'
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ALIASES = {
    'all': None,
    'core': ['plan-marshall'],
    'java': ['pm-dev-java', 'pm-dev-java-cui'],
    'python': ['pm-dev-python'],
    'frontend': ['pm-dev-frontend', 'pm-dev-frontend-cui'],
    'oci': ['pm-dev-oci'],
    'docs': ['pm-documents'],
    'reqs': ['pm-requirements'],
    'plugin-dev': ['pm-plugin-development'],
}

DEPENDENCIES = {
    'pm-dev-java-cui': 'pm-dev-java',
    'pm-dev-frontend-cui': 'pm-dev-frontend',
}

def load_bundle_components(source_dir: Path, target_name: str) -> dict:
    comp_file = source_dir / 'bundle-components.json'
    if comp_file.is_file():
        try:
            data = json.loads(comp_file.read_text(encoding='utf-8'))
            return data.get('bundles', {})
        except Exception:
            pass
    alt_file = source_dir / '.plan-marshall-components.json'
    if alt_file.is_file():
        try:
            data = json.loads(alt_file.read_text(encoding='utf-8'))
            return data.get('bundles', {})
        except Exception:
            pass
    bundles: dict[str, dict[str, list[str]]] = {}
    skill_dir_name = 'skill' if target_name == 'opencode' else 'skills'
    agent_dir_name = 'agent' if target_name == 'opencode' else 'agents'
    cmd_dir_name = 'command' if target_name == 'opencode' else 'commands'

    skills_root = source_dir / skill_dir_name
    if skills_root.is_dir():
        for d in sorted(skills_root.iterdir()):
            if not d.is_dir():
                continue
            skill_md = d / 'SKILL.md'
            bundle = None
            if skill_md.is_file():
                try:
                    for line in skill_md.read_text(encoding='utf-8').splitlines():
                        if line.strip().startswith('bundle:'):
                            bundle = line.split(':', 1)[1].strip().strip('"\'')
                            break
                except Exception:
                    pass
            if not bundle:
                parts = d.name.split('-')
                bundle = '-'.join(parts[:-1]) if len(parts) >= 2 else 'plan-marshall'
            if bundle not in bundles:
                bundles[bundle] = {'skills': [], 'agents': [], 'commands': []}
            bundles[bundle]['skills'].append(f'{skill_dir_name}/{d.name}')

    agents_root = source_dir / agent_dir_name
    if agents_root.is_dir():
        for f in sorted(agents_root.iterdir()):
            if not f.is_file() or not f.name.endswith('.md'):
                continue
            matched_bundle = 'plan-marshall'
            for b in sorted(bundles.keys(), key=len, reverse=True):
                if f.name.startswith(b):
                    matched_bundle = b
                    break
            if matched_bundle not in bundles:
                bundles[matched_bundle] = {'skills': [], 'agents': [], 'commands': []}
            bundles[matched_bundle]['agents'].append(f'{agent_dir_name}/{f.name}')

    cmd_root = source_dir / cmd_dir_name
    if cmd_root.is_dir():
        for f in sorted(cmd_root.iterdir()):
            if not f.is_file() or not f.name.endswith('.md'):
                continue
            matched_bundle = 'plan-marshall'
            for b in sorted(bundles.keys(), key=len, reverse=True):
                if f.name.startswith(b):
                    matched_bundle = b
                    break
            if matched_bundle not in bundles:
                bundles[matched_bundle] = {'skills': [], 'agents': [], 'commands': []}
            bundles[matched_bundle]['commands'].append(f'{cmd_dir_name}/{f.name}')

    return bundles

def map_component_path(src_rel: str, target_name: str) -> tuple[str, str]:
    if target_name == 'opencode':
        if src_rel.startswith('skill/'):
            return src_rel, 'skills/' + src_rel[6:]
        if src_rel.startswith('agent/'):
            return src_rel, 'agents/' + src_rel[6:]
        if src_rel.startswith('command/'):
            return src_rel, 'commands/' + src_rel[8:]
    return src_rel, src_rel

def resolve_selection(
    mode: str,
    bundles_csv: str | None,
    without_bundles_csv: str | None,
    available_bundles: set[str],
    core_bundles: set[str],
    prior_bundles: list[str] | None = None,
) -> list[str]:
    if mode == 'core-only':
        selected = set(core_bundles)
    elif mode == 'bundles' or (bundles_csv and not mode):
        selected = set(core_bundles)
        tokens = [t.strip() for t in (bundles_csv or '').split(',') if t.strip()]
        for token in tokens:
            if token == 'all':
                selected.update(available_bundles)
            elif token == 'core':
                selected.update(core_bundles)
            elif token in ALIASES and ALIASES[token]:
                selected.update(b for b in ALIASES[token] if b in available_bundles)
            elif token in available_bundles:
                selected.add(token)
            else:
                sys.stderr.write(f"Error: Unknown bundle or alias: '{token}'\n")
                sys.stderr.write(f"Available aliases: {', '.join(sorted(ALIASES.keys()))}\n")
                sys.stderr.write(f"Available bundles: {', '.join(sorted(available_bundles))}\n")
                sys.exit(2)
    elif mode == 'all':
        selected = set(available_bundles)
    else:
        if prior_bundles is not None:
            selected = set(prior_bundles)
        else:
            selected = set(available_bundles)

    if without_bundles_csv:
        without_tokens = [t.strip() for t in without_bundles_csv.split(',') if t.strip()]
        for token in without_tokens:
            if token == 'core' or token in core_bundles:
                sys.stderr.write(f"Error: Cannot exclude mandatory core bundle: '{token}'\n")
                sys.exit(2)
            elif token == 'all':
                sys.stderr.write("Error: Cannot exclude 'all' bundles; core is mandatory\n")
                sys.exit(2)
            elif token in ALIASES and ALIASES[token]:
                for m in ALIASES[token]:
                    selected.discard(m)
            elif token in available_bundles:
                selected.discard(token)
            else:
                sys.stderr.write(f"Error: Unknown bundle or alias in --without-bundles: '{token}'\n")
                sys.exit(2)

        for child, parent in DEPENDENCIES.items():
            if child in selected and parent not in selected:
                sys.stderr.write(
                    f"Error: Cannot exclude base bundle '{parent}' while dependent child '{child}' is kept.\n"
                    f"Exclude '{child}' as well or use alias covering both.\n"
                )
                sys.exit(2)

    for child, parent in DEPENDENCIES.items():
        if child in selected and parent in available_bundles:
            selected.add(parent)

    selected.update(core_bundles & available_bundles)
    selected = selected & available_bundles
    return sorted(selected)

def get_bundle_managed_files(
    bundle_components: dict,
    installed_bundles: list[str],
    source_dir: Path,
    target_name: str,
) -> tuple[list[tuple[Path, str]], list[str]]:
    items: list[tuple[Path, str]] = []
    managed_files: list[str] = []

    for b in installed_bundles:
        comp = bundle_components.get(b, {})
        for skill in comp.get('skills', []):
            src_skill = source_dir / skill
            _, dst_skill_rel = map_component_path(skill, target_name)
            if src_skill.is_dir():
                for root, _, files in os.walk(src_skill):
                    for file in files:
                        fp = Path(root) / file
                        sub_rel = fp.relative_to(src_skill).as_posix()
                        target_rel = f"{dst_skill_rel}/{sub_rel}"
                        items.append((fp, target_rel))
                        managed_files.append(target_rel)
            elif src_skill.is_file():
                target_rel = f"{dst_skill_rel}/SKILL.md"
                items.append((src_skill, target_rel))
                managed_files.append(target_rel)

        for agent in comp.get('agents', []):
            src_agent = source_dir / agent
            _, dst_agent_rel = map_component_path(agent, target_name)
            if src_agent.is_file():
                items.append((src_agent, dst_agent_rel))
                managed_files.append(dst_agent_rel)

        for cmd in comp.get('commands', []):
            src_cmd = source_dir / cmd
            _, dst_cmd_rel = map_component_path(cmd, target_name)
            if src_cmd.is_file():
                items.append((src_cmd, dst_cmd_rel))
                managed_files.append(dst_cmd_rel)

    if target_name == 'antigravity':
        if (source_dir / 'README.adoc').is_file():
            items.append((source_dir / 'README.adoc', 'README.adoc'))
            managed_files.append('README.adoc')
        if (source_dir / 'install.sh').is_file():
            items.append((source_dir / 'install.sh', 'install.sh'))
            managed_files.append('install.sh')
        if (source_dir / 'bundle-components.json').is_file():
            items.append((source_dir / 'bundle-components.json', 'bundle-components.json'))
            managed_files.append('bundle-components.json')
        managed_files.append('plugin.json')
    elif target_name == 'opencode':
        if (source_dir / 'README.adoc').is_file():
            items.append((source_dir / 'README.adoc', 'plan-marshall-README.adoc'))
            managed_files.append('plan-marshall-README.adoc')
        if (source_dir / 'install.sh').is_file():
            items.append((source_dir / 'install.sh', 'plan-marshall-install.sh'))
            managed_files.append('plan-marshall-install.sh')
        if (source_dir / 'bundle-components.json').is_file():
            items.append((source_dir / 'bundle-components.json', '.plan-marshall-components.json'))
            managed_files.append('.plan-marshall-components.json')

    return items, sorted(set(managed_files))

def tailor_config(
    target_dir: Path,
    source_dir: Path,
    target_name: str,
    installed_bundles: list[str],
    bundle_components: dict,
):
    if target_name == 'antigravity':
        plugin_src = source_dir / 'plugin.json'
        if not plugin_src.is_file():
            plugin_src = target_dir / 'plugin.json'
        plugin_data = {}
        if plugin_src.is_file():
            try:
                plugin_data = json.loads(plugin_src.read_text(encoding='utf-8'))
            except Exception:
                pass
        plugin_data['bundles'] = sorted(installed_bundles)
        (target_dir / 'plugin.json').write_text(json.dumps(plugin_data, indent=2) + '\n', encoding='utf-8')
    elif target_name == 'opencode':
        opencode_path = target_dir / 'opencode.json'
        if opencode_path.is_file():
            try:
                data = json.loads(opencode_path.read_text(encoding='utf-8'))
                if 'agent' in data and isinstance(data['agent'], dict):
                    allowed_stems = set()
                    for b in installed_bundles:
                        for a in bundle_components.get(b, {}).get('agents', []):
                            allowed_stems.add(Path(a).stem)
                    data['agent'] = {k: v for k, v in data['agent'].items() if k in allowed_stems}
                    opencode_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
            except Exception:
                pass

def do_selective_uninstall(
    target_dir: Path,
    source_dir: Path,
    target_name: str,
    bundles_csv: str,
):
    manifest_name = '.install-manifest.json' if target_name == 'antigravity' else '.plan-marshall-manifest.json'
    manifest_path = target_dir / manifest_name
    if not manifest_path.is_file():
        sys.stderr.write(f"Error: No installation manifest found at {manifest_path}\n")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    installed_bundles = list(manifest.get('installed_bundles', []))
    comps = load_bundle_components(source_dir, target_name)
    available_bundles = set(comps.keys()) | set(installed_bundles)
    core_bundles = {'plan-marshall'} | ({f'plan-marshall-{target_name}'} & available_bundles)

    tokens = [t.strip() for t in bundles_csv.split(',') if t.strip()]
    to_remove = set()
    for token in tokens:
        if token == 'core' or token in core_bundles:
            sys.stderr.write("Error: Cannot uninstall mandatory core bundle 'plan-marshall'\n")
            sys.exit(2)
        elif token == 'all':
            sys.stderr.write("Error: For full uninstall, omit --bundles\n")
            sys.exit(2)
        elif token in ALIASES and ALIASES[token]:
            to_remove.update(b for b in ALIASES[token] if b in available_bundles)
        elif token in available_bundles:
            to_remove.add(token)
        else:
            sys.stderr.write(f"Error: Unknown bundle or alias: '{token}'\n")
            sys.exit(2)

    if any(c in to_remove for c in core_bundles):
        sys.stderr.write("Error: Cannot uninstall mandatory core bundle 'plan-marshall'\n")
        sys.exit(2)

    remaining_bundles = set(installed_bundles) - to_remove
    for child, parent in DEPENDENCIES.items():
        if parent in to_remove and child in remaining_bundles:
            sys.stderr.write(
                f"Error: Cannot uninstall base bundle '{parent}' while dependent child '{child}' remains installed.\n"
                f"Include '{child}' in removal list or use alias covering both.\n"
            )
            sys.exit(2)

    files_to_remove = set()
    dirs_to_check = set()
    for b in to_remove:
        comp = comps.get(b, {})
        for skill in comp.get('skills', []):
            _, skill_rel = map_component_path(skill, target_name)
            skill_d = target_dir / skill_rel
            if skill_d.is_dir():
                dirs_to_check.add(skill_d)
                for root, _, files in os.walk(skill_d):
                    for file in files:
                        files_to_remove.add((Path(root) / file).relative_to(target_dir).as_posix())
        for agent in comp.get('agents', []):
            _, agent_rel = map_component_path(agent, target_name)
            files_to_remove.add(agent_rel)
        for cmd in comp.get('commands', []):
            _, cmd_rel = map_component_path(cmd, target_name)
            files_to_remove.add(cmd_rel)

    for rel in files_to_remove:
        p = target_dir / rel
        if p.is_file():
            p.unlink()

    for d in sorted(dirs_to_check, key=lambda p: len(p.parts), reverse=True):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)

    for prefix in ('skills', 'skill', 'agents', 'agent', 'commands', 'command'):
        root_d = target_dir / prefix
        if root_d.is_dir():
            for d in sorted((p for p in root_d.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                try:
                    d.rmdir()
                except OSError:
                    pass

    new_installed = [b for b in installed_bundles if b not in to_remove]
    old_managed = manifest.get('managed_files', [])
    new_managed = [f for f in old_managed if (target_dir / f).is_file()]
    manifest['installed_bundles'] = new_installed
    manifest['managed_files'] = new_managed
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    tailor_config(target_dir, source_dir, target_name, new_installed, comps)
    print(f"Successfully uninstalled bundles: {', '.join(sorted(to_remove))}")
    print(f"Remaining bundles: {', '.join(sorted(new_installed))}")

def do_opencode_full_uninstall(target_dir: Path, source_dir: Path):
    manifest_path = target_dir / '.plan-marshall-manifest.json'
    files_to_delete = set()

    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding='utf-8'))
            files_to_delete.update(data.get('managed_files', []))
        except Exception:
            pass

    comps = load_bundle_components(source_dir, 'opencode')
    for b, comp in comps.items():
        for skill in comp.get('skills', []):
            skill_name = Path(skill).name
            for prefix in ('skills', 'skill'):
                skill_d = target_dir / prefix / skill_name
                if skill_d.is_dir():
                    for root, _, files in os.walk(skill_d):
                        for file in files:
                            files_to_delete.add((Path(root) / file).relative_to(target_dir).as_posix())
        for agent in comp.get('agents', []):
            agent_name = Path(agent).name
            for prefix in ('agents', 'agent'):
                files_to_delete.add(f'{prefix}/{agent_name}')
        for cmd in comp.get('commands', []):
            cmd_name = Path(cmd).name
            for prefix in ('commands', 'command'):
                files_to_delete.add(f'{prefix}/{cmd_name}')

    files_to_delete.add('plan-marshall-README.adoc')
    files_to_delete.add('plan-marshall-install.sh')
    files_to_delete.add('.plan-marshall-components.json')
    files_to_delete.add('.plan-marshall-manifest.json')

    for rel in files_to_delete:
        f = target_dir / rel
        if f.is_file():
            f.unlink()

    for prefix in ('skills', 'skill', 'agents', 'agent', 'commands', 'command'):
        root_dir = target_dir / prefix
        if root_dir.is_dir():
            for d in sorted((p for p in root_dir.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                try:
                    d.rmdir()
                except OSError:
                    pass
            try:
                root_dir.rmdir()
            except OSError:
                pass

    if manifest_path.is_file():
        manifest_path.unlink(missing_ok=True)
    print("Plan Marshall components uninstalled cleanly (non-Plan Marshall components preserved).")

def perform_atomic_write(
    target_dir: Path,
    source_dir: Path,
    target_name: str,
    scope: str,
    ref: str,
    installed_bundles: list[str],
    items_to_copy: list[tuple[Path, str]],
    new_managed_files: list[str],
    old_manifest: dict | None,
    manifest_path: Path,
    bundle_components: dict,
):
    backup_dir = target_dir / f'.backup-{os.getpid()}'
    if backup_dir.exists():
        shutil.rmtree(backup_dir, ignore_errors=True)
    backup_dir.mkdir(parents=True, exist_ok=True)

    dist_manifest = source_dir / 'dist-manifest.json'
    dist_manifest_sha = 'unknown'
    if dist_manifest.is_file():
        dist_manifest_sha = hashlib.sha256(dist_manifest.read_bytes()).hexdigest()

    try:
        if old_manifest and 'managed_files' in old_manifest:
            for rel in old_manifest['managed_files']:
                f = target_dir / rel
                if f.is_file():
                    dest = backup_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(f, dest)

        cfg_name = 'plugin.json' if target_name == 'antigravity' else 'opencode.json'
        if (target_dir / cfg_name).is_file():
            shutil.copyfile(target_dir / cfg_name, backup_dir / cfg_name)
        if manifest_path.is_file():
            shutil.copyfile(manifest_path, backup_dir / manifest_path.name)

        new_managed_set = set(new_managed_files)
        if old_manifest and 'managed_files' in old_manifest:
            for rel in old_manifest['managed_files']:
                if rel not in new_managed_set:
                    p = target_dir / rel
                    if p.is_file():
                        p.unlink()

        for src_file, rel_dest in items_to_copy:
            dst = target_dir / rel_dest
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_file, dst)
            if dst.name.endswith('.sh'):
                dst.chmod(0o755)

        tailor_config(target_dir, source_dir, target_name, installed_bundles, bundle_components)

        manifest_data = {
            'schema_version': 1,
            'target': target_name,
            'scope': scope,
            'installed_ref': ref,
            'dist_manifest_sha': dist_manifest_sha,
            'core': 'plan-marshall',
            'installed_bundles': sorted(installed_bundles),
            'managed_files': sorted(new_managed_files),
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2) + '\n', encoding='utf-8')

        for prefix in ('skills', 'agents', 'commands'):
            root_d = target_dir / prefix
            if root_d.is_dir():
                for d in sorted((p for p in root_d.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                    try:
                        d.rmdir()
                    except OSError:
                        pass

        shutil.rmtree(backup_dir, ignore_errors=True)

    except Exception as err:
        sys.stderr.write(f"Error during install/update: {err}\nRolling back from backup snapshot...\n")
        for rel in new_managed_files:
            if not (backup_dir / rel).is_file():
                p = target_dir / rel
                if p.is_file():
                    p.unlink(missing_ok=True)
        for root, _, files in os.walk(backup_dir):
            for file in files:
                src = Path(root) / file
                rel = src.relative_to(backup_dir)
                dest = target_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
                if dest.name.endswith('.sh'):
                    dest.chmod(0o755)
        shutil.rmtree(backup_dir, ignore_errors=True)
        sys.exit(1)

def main():
    source_dir = Path(sys.argv[1]).resolve()
    target_dir = Path(sys.argv[2]).resolve()
    action = sys.argv[3]
    target_name = sys.argv[4]
    scope = sys.argv[5]
    ref = sys.argv[6]
    mode = sys.argv[7]
    bundles_csv = sys.argv[8] if len(sys.argv) > 8 and sys.argv[8] else None
    without_bundles_csv = sys.argv[9] if len(sys.argv) > 9 and sys.argv[9] else None

    if action == 'uninstall':
        if bundles_csv:
            do_selective_uninstall(target_dir, source_dir, target_name, bundles_csv)
        else:
            if target_name == 'opencode':
                do_opencode_full_uninstall(target_dir, source_dir)
            else:
                if target_dir.is_dir():
                    shutil.rmtree(target_dir)
        sys.exit(0)

    bundle_components = load_bundle_components(source_dir, target_name)
    available_bundles = set(bundle_components.keys())
    core_bundles = {'plan-marshall'} | ({f'plan-marshall-{target_name}'} & available_bundles)

    manifest_name = '.install-manifest.json' if target_name == 'antigravity' else '.plan-marshall-manifest.json'
    manifest_path = target_dir / manifest_name

    old_manifest = None
    if manifest_path.is_file():
        try:
            old_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except Exception:
            old_manifest = None

    prior_bundles = old_manifest.get('installed_bundles') if old_manifest else None

    installed_bundles = resolve_selection(
        mode=mode,
        bundles_csv=bundles_csv,
        without_bundles_csv=without_bundles_csv,
        available_bundles=available_bundles,
        core_bundles=core_bundles,
        prior_bundles=prior_bundles if action == 'update' else None,
    )

    items_to_copy, new_managed_files = get_bundle_managed_files(
        bundle_components=bundle_components,
        installed_bundles=installed_bundles,
        source_dir=source_dir,
        target_name=target_name,
    )

    target_dir.mkdir(parents=True, exist_ok=True)
    perform_atomic_write(
        target_dir=target_dir,
        source_dir=source_dir,
        target_name=target_name,
        scope=scope,
        ref=ref,
        installed_bundles=installed_bundles,
        items_to_copy=items_to_copy,
        new_managed_files=new_managed_files,
        old_manifest=old_manifest,
        manifest_path=manifest_path,
        bundle_components=bundle_components,
    )

if __name__ == '__main__':
    main()
EOF_PYTHON

if [ "$UNINSTALL" = false ]; then
  echo "Plan Marshall Antigravity plugin successfully installed at: $TARGET_DIR"
  echo ""
  echo "Antigravity automatically discovers installed plugins."
  echo "You can verify the installation in Antigravity via Settings -> Plugins or in chat."
fi
