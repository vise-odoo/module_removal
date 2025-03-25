import json
from helpers import (
    remove_unwanted_version_folders,
    analyze_migration_scripts,
    load_installed_modules
)
from mock_classes import (
    MockCr,
    MockUtil,
)

with open('config.json', 'r') as f:
    config = json.load(f)

PATH_TO_MIGRATIONS = config['paths']['migrations']
MODULES_CSV = config['paths']['modules_csv']
SOURCE_VERSION = config['versions']['source']
DESTINATION_VERSION = config['versions']['destination']

# Watch out.
# Scripts from Odoo 9.0 include symlinks to Odoo 8.0
# Scripts from Odoo 12.0 include symlinks to Odoo 9.0
# Scripts from Odoo 14.0 include symlinks to Odoo 13.0
# -> If upgrading from Odoo 9.0 (resp. 12.0), SOURCE_VERSION should be 8.0 (resp. 9.0) 
# TODO: Keep files from previous versions, where a symlinked file exists in the wanted versions?

if __name__ == "__main__":
    installed_modules = load_installed_modules(MODULES_CSV)
    initial_installed_modules = installed_modules.copy()

    cr = MockCr()
    util = MockUtil(cr, installed_modules)

    remove_unwanted_version_folders(PATH_TO_MIGRATIONS, SOURCE_VERSION, DESTINATION_VERSION)
    analyze_migration_scripts(PATH_TO_MIGRATIONS, util, cr)

    print("\n### Summary ###")
    print(f"Initially installed modules: {len(initial_installed_modules)}")
    print(f"Final installed modules (simulated): {len(util.installed_modules)}")
    print(f"Added modules: {set(util.installed_modules) - set(initial_installed_modules)}")
    print(f"Removed modules: {set(initial_installed_modules) - set(util.installed_modules)}")
    print("Finished!")
