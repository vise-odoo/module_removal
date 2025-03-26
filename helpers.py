import os
import re
import shutil
import glob
import csv
from packaging.version import parse
from mock_classes import (
    MockTools,
)
import json

with open('config.json', 'r') as f:
    config = json.load(f)

SKIP_VERSIONS = tuple(config['settings']['skip_versions'])
EXTRA_LOGS = config['settings']['extra_logs']
REPLACEMENTS = config['replacements']

# --- Helper Functions ---
def file_open(path):
    if path == "addons/base/data/res.country.state.csv":
        return open("csv_parse_35.csv")
    else:
        return open("xml_parse.xml")

def load_installed_modules(csv_file):
    modules = []
    try:
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                modules.extend(row)
    except FileNotFoundError:
        print(f"ERROR: File {csv_file} not found.")
        exit(1)
    return modules

def _parse_version(version_str):
    """Parses a version string, handling  'saas~' prefixes & combined prefixes like '9.saas~11.1'."""
    match = re.match(r'^(?:(\d+)\.)?(saas~)?(.*)$', version_str)
    if not match:
        raise ValueError(f"Invalid version string: {version_str}")

    prefix_part, saas_prefix, main_version_part = match.groups()

    if prefix_part:
        # For older versions 9.saas~x.y.z, construct the new version string:  saas~9.x.y.z
        new_version_str = prefix_part.rstrip('.') + "." + main_version_part
    else:
        new_version_str = main_version_part
    parsed_version = parse(new_version_str)
    return (saas_prefix or "", parsed_version)

def remove_unwanted_version_folders(migrations_path, src_version, dest_version):
    print(f"### Removing unwanted version folders below {src_version} and above {dest_version} ###")
    src_version = parse(src_version)
    dest_version = parse(dest_version)

    for module_folder in glob.glob(os.path.join(migrations_path, "*")):

        if not os.path.isdir(module_folder):
            continue

        for version_folder in glob.glob(os.path.join(module_folder, "*")):
            if not os.path.isdir(version_folder):
                continue

            version_str = os.path.basename(version_folder)
            if version_str in SKIP_VERSIONS:
                continue

            try:
                _, version = _parse_version(version_str)
                if not (src_version <= version <= dest_version):
                    shutil.rmtree(version_folder)
            except Exception as e:
                print(f"  Invalid version folder (skipping) {version_folder}: {e}")

    for module_folder in glob.glob(os.path.join(migrations_path, "*")):
        if os.path.isdir(module_folder) and not os.listdir(module_folder):
            try:
                shutil.rmtree(module_folder)
                print(f"  Removed (empty module folder): {module_folder}")
            except OSError as e:
                print(f"  ERROR removing {module_folder}: {e}")

def is_module_script(content):
    target_functions = [
        "new_module",
        "merge_module",
        "force_install_module",
        "new_module_dep",
        "remove_module_deps",
        "module_deps_diff",
        "module_auto_install",
        "rename_module",
        "uninstall_module",
        "remove_module",
    ]
    pattern = r"\b(" + "|".join(re.escape(name) for name in target_functions) + r")\b"

    if re.search(pattern, content):
        return True
    else:
        return False

def analyze_migration_scripts(migrations_path, util_instance, cr):
    """This is the big chunk of the program. It goes through the /base migration scripts in version order,
    and executes each one of them, while simulating the evolution of the installed modules. It also removes
    the version folders for all the other modules that are not installed at the tracked point.
    """
    print("\n### Analyzing migration scripts ###")

    version_folders = []
    for base_version in os.listdir(os.path.join(migrations_path, 'base')):
        version_path = os.path.join(migrations_path, 'base', base_version)
        if not os.path.isdir(version_path):
            continue

        if base_version in ('tests', '0.0.0'):
            print(f"  Skipping version: {base_version}")
            continue

        try:
            version_tuple = _parse_version(base_version)
            version_folders.append((version_tuple, version_path, base_version))
        except Exception as e:
            print(f"  Invalid version folder (skipping) {version_path}: {e}")
            continue

    version_folders.sort(key=lambda x: (x[0][1], x[0][0]))

    for (base_prefix, base_version_parsed), version_path, base_version in version_folders:
        print(f"--- Processing version: {base_version}")

        script_files = []
        for script_name in os.listdir(version_path):
            if not script_name.endswith('.py'):
                continue

            script_conditions = [
                # Here scripts can be manually skipped
            ]

            if (script_name, base_version) in script_conditions:
                print(f"  Skipping script: {script_name}")
                continue
            script_path = os.path.join(version_path, script_name)
            script_files.append((script_name, script_path))

        script_files.sort()

        # Execute each migration script, using the patched functions and mock objects.
        for script_name, script_path in script_files:
            with open(script_path, 'r') as script_file:
                script_content = script_file.read()
                if not is_module_script(script_content):
                    # print(f"    Skipping non-module script: {script_name}")
                    continue
                print(f"  Analyzing script: {script_name}")
                script_content += f"\nmigrate(cr, version)\n"
                try:
                    for old_import, new_import in REPLACEMENTS.items():
                        script_content = script_content.replace(old_import, new_import)
                    exec(script_content, {
                        'util': util_instance,
                        'cr': cr,
                        'version': str(base_version_parsed),
                        "tools": MockTools,
                    })
                except Exception as e:
                    print(f"    ERROR executing {script_name}: {e}")

        # At the end of each base_version, remove the version folder for all the other modules that are not installed at this point.
        for other_module in glob.glob(os.path.join(migrations_path, "*")):
            if not os.path.isdir(other_module):
                continue
            other_module_name = os.path.basename(other_module)
            if other_module_name != 'base' and other_module_name not in util_instance.installed_modules:
                found_matching_version = False
                for other_version in os.listdir(other_module):
                    other_version_path = os.path.join(other_module, other_version)
                    if not os.path.isdir(other_version_path):
                        continue
                    if other_version in ('tests', '0.0.0'):
                        continue

                    try:
                        other_prefix, other_version_parsed = _parse_version(other_version)
                        if (base_prefix == other_prefix and
                            base_version_parsed.major == other_version_parsed.major and
                            base_version_parsed.minor == other_version_parsed.minor):

                            shutil.rmtree(other_version_path)
                            print(f"  Removed version folder: {other_version_path} {other_module_name} (module not installed)")
                            found_matching_version = True
                            break
                    except Exception as e:
                        print(f"  Error processing version folder {other_version_path}: {e}")

                if not found_matching_version and EXTRA_LOGS:
                    print(f"  Could not find matching version folder for {base_version} in {other_module_name}")

    for module_folder in glob.glob(os.path.join(migrations_path, "*")):
        if os.path.isdir(module_folder) and not os.listdir(module_folder):
            try:
                shutil.rmtree(module_folder)
                print(f"  Removed (empty module folder): {module_folder}")
            except OSError as e:
                print(f"  ERROR removing {module_folder}: {e}")
