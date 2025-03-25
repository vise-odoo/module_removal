import logging
import json
import re

with open('config.json', 'r') as f:
    config = json.load(f)

HAS_ENTERPRISE = config['settings']['has_enterprise']
DESTINATION_VERSION = config['versions']['destination']

# --- Mock Classes ---
# Here most of the Odoo classes are recreated as Mock classes to avoid errors when running the scripts.
class MockModules:
    def get_modules():
        return []

class MockDomains:
    def _get_domain_fields(self, cr):
        return []

class MockMany2many:
    def update_db(self, model, columns):
        pass

class MockCnx:
    server_version = 0

class MockCr:
    def __init__(self):
        self._cnx = MockCnx()
        self.results = []
        self.rowcount = 0

    def execute(self, query, params=None):
        if "SELECT model, array_agg(name)" in query:
            self.results = []
        elif "SELECT indexname FROM pg_indexes" in query:
            self.results = []
        elif "ALTER TABLE ir_translation RENAME" in query:
            pass
        elif "DROP CONSTRAINT" in query:
            pass
        self.rowcount = len(self.results)

    def fetchall(self):
        return self.results

    def fetchone(self):
        return [0]
        
    def dictfetchall(self):
        return self.results

    def commit(self):
        return True

    def dbname(self):
        return ""

    def executemany(self, query, params=None):
        self.results = []

class MockField:
    def __init__(self, name, store=True, translate=False, index=None, manual=False, column_type=None):
        self.name = name
        self.store = store
        self.translate = translate
        self.index = index
        self.manual = manual
        self.column_type = column_type
        self.unaccent = False

class MockRecord:
    def __init__(self, model):
        self.model = model
        self.id = 0
        self.ids = []
        if self.model not in  ["res.groups", "implied_ids", "all_implied_ids"]:
            self.group_ids = MockRecord(model="res.groups")
        if self.model == "res.groups":
            self.implied_ids = MockRecord(model="implied_ids")
        if self.model == "implied_ids":
            self.all_implied_ids = MockRecord(model="all_implied_ids")
    
    def __sub__(self, other):
        return MockRecord(model="unknown")

    def __add__(self, other):
        return MockRecord(model="unknown")

    def write(self, vals):
        pass

class MockModel:
    def __init__(self, model_name, fields, auto=True, _abstract=False):
        self.name = model_name
        self._table = model_name.replace('.', '_')
        self._fields = {field.name: field for field in fields}
        self._auto = auto
        self._abstract = _abstract

    def _toggle_group_multi_currency(self):
        pass

    def with_context(self, *args, **kwargs):
        return self

    def with_company(self, company):
        return self

    def search(self, args, offset=0, limit=None, order=None, count=False):
      return []

    def browse(self, id):
        return MockRecord(model=self.name)

    def _update_user_groups_view(self):
        pass

    def clear_caches(self):
        pass

class MockModels:
    def __init__(self):
        self.Model = MockModel("unknown", [])

class MockRegistry(dict):
    def check_indexes(self, cr, model_names):
        pass

    def __getitem__(self, item):
        if item not in self:
            self[item] = MockModel(item, [])
        return super().__getitem__(item)

class MockEnv:
    def __init__(self, cr):
        self.cr = cr
        self.registry = MockRegistry()
        self.context = {} 
        ir_model_fields_model = MockModel('ir.model.fields', [])

        self.registry['ir.model.fields'] = ir_model_fields_model
        # Add more models here if needed

        self.values = lambda: self.registry.values()

    def __getitem__(self, key):
        if key not in self.registry:
            self.registry[key] = MockModel(key, [])
        return self.registry[key]

    def __getattr__(self, name):
      return MockModel("unknown")

class MockTools:
    config = {}

    def __getattr__(self, name):
        def default_util_function(*args, **kwargs):
            pass
        return default_util_function

class MockHelpers:
    def __getattr__(self, name):
        def default_util_function(*args, **kwargs):
            pass
        return default_util_function

    def _dashboard_actions(self, cr, pattern):
        return []

class MockColumns:
    def using(self, alias):
        pass

class MockView:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def xpath(self, path):
        return []

class MockImage:
    IMAGE_MAX_RESOLUTION = 0
 
class MockSavepoint:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockUtil:
   
    def __init__(self, cr, installed_modules):
        self.installed_modules = installed_modules
        self.tables = {}
        self.columns = MockColumns()
        self.helpers = MockHelpers()
        self.domains = MockDomains()
        self.ENVIRON = {"s125_image_mixin_recompute": {"all": [], "512": []}}
        self.NEARLYWARN = 1
        self._logger = logging.getLogger(__name__)

    def __getattr__(self, name):
        def default_util_function(*args, **kwargs):
            pass
        return default_util_function

    # Mandatory patched methods
    # These methods, if not patched, will cause the scripts to fail
    def import_script(self, path, name=None):
        def update_rules(cr, registry):
            pass
        self.update_rules = update_rules
        return self

    def edit_view(self, cr, xml_id=None, view_id=None, skip_if_not_noupdate=True):
        return MockView()

    def column_exists(self, cr, table, column):
        return True

    def splitlines(self, s):
        return (stripped_line for line in s.splitlines() for stripped_line in [line.split("#", 1)[0].strip()] if stripped_line)

    def savepoint(self, cr):
        return MockSavepoint()

    def expand_braces(self, xml_id):
        return []

    def has_enterprise(self):
        return HAS_ENTERPRISE

    def get_fk(self, cr, table):
        return []

    def log_progress(self, *args, **kwargs):
        return "Progress"

    def get_columns(self, cr, table_name, ignore=None):
        return self.columns

    def env(self, cr):
      return MockEnv(cr)

    def version_gte(self, version):
        return self.parse_version(DESTINATION_VERSION) >= self.parse_version(version)

    def format_query(self, cr, query, **kwargs):
        return ""

    def parse_version(self, s):
        "Taken as is, from Odoo's code"
        component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
        replace = {'pre':'c', 'preview':'c','-':'final-','_':'final-','rc':'c','dev':'@','saas':'','~':''}.get
        def _parse_version_parts(s):
            for part in component_re.split(s):
                part = replace(part,part)
                if not part or part=='.':
                    continue
                if part[:1] in '0123456789':
                    yield part.zfill(8)
                else:
                    yield '*'+part

            yield '*final'

        parts: list[str] = []
        for part in _parse_version_parts((s or '0.1').lower()):
            if part.startswith('*'):
                if part<'*final':
                    while parts and parts[-1]=='*final-': parts.pop()
                while parts and parts[-1]=='00000000':
                    parts.pop()
            parts.append(part)
        return tuple(parts)

    # Custom methods
    # These method are used by the scripts to keep track of the installed modules and their dependencies
    def new_module(self, cr, module_name, deps=(), auto_install=False, category=None):
        deps = deps if isinstance(deps, (list, tuple)) else [deps]
        if auto_install:
            if all(dep in self.installed_modules for dep in deps):
                if module_name not in self.installed_modules:
                    self.installed_modules.append(module_name)
                    print(f"  [NEW_MODULE] {module_name} (added - auto_install)")
            else:
                print(f"  [NEW_MODULE] {module_name} (skipped - deps not met)")
        else:
            print(f"  [NEW_MODULE] {module_name} (skipped - auto_install=False)")

    def merge_module(self, cr, module1, module2, update_dependers=True):
        if module1 in self.installed_modules and module2 not in self.installed_modules:
            self.installed_modules.append(module2)
            print(f"  [MERGE_MODULE] {module2} (added - merged from {module1})")

    def force_install_module(self, cr, module_name, if_installed=None):
        if_installed = if_installed if isinstance(if_installed, (list, tuple)) else [if_installed] if if_installed else []
        if if_installed:
            if all(dep in self.installed_modules for dep in if_installed):
                if module_name not in self.installed_modules:
                    self.installed_modules.append(module_name)
                    print(f"  [FORCE_INSTALL] {module_name} (added - deps met)")
            else:
                print(f"  [FORCE_INSTALL] {module_name} (skipped - deps not met)")
        else:
            if module_name not in self.installed_modules:
                self.installed_modules.append(module_name)
                print(f"  [FORCE_INSTALL] {module_name} (added)")
            else:
                print(f"  [FORCE_INSTALL] {module_name} (skipped - already installed)")

    def new_module_dep(self, cr, module_name, new_dep):
        if module_name in self.installed_modules and new_dep not in self.installed_modules:
            self.installed_modules.append(new_dep)
            print(f"  [NEW_MODULE_DEP] Added dependency {new_dep} (due to {module_name})")

    def remove_module_deps(self, cr, module_name, dependency):
        # Nothing to do here
        pass

    def module_deps_diff(self, cr, module, plus=(), minus=()):
        if module in self.installed_modules:
            for added_module in plus:
                if added_module not in self.installed_modules:
                    self.installed_modules.append(added_module)
                    print(f"  [MODULE_DEPS_DIFF] {added_module} (added - plus)")
            for removed_module in minus:
                print(f"  [MODULE_DEPS_DIFF] {removed_module} (ignored - minus)")

    def module_auto_install(self, cr, module_name, auto_install):
        auto_install = auto_install if isinstance(auto_install, (list, tuple)) else [auto_install] if auto_install else []
        if auto_install is True:
            self.installed_modules.append(module_name)
            print(f"  [AUTO_INSTALL] {module_name} (added - auto_install=True)")
        elif auto_install:
            if all(dep in self.installed_modules for dep in auto_install):
                if module_name not in self.installed_modules:
                    self.installed_modules.append(module_name)
                    print(f"  [AUTO_INSTALL] {module_name} (added - deps met)")
            else:
                print(f"  [AUTO_INSTALL] {module_name} (skipped - auto_install is a list/tuple, but deps not met)")
        else:
            print(f"  [AUTO_INSTALL] {module_name} (skipped - auto_install=False)")

    def rename_module(self, cr, old_name, new_name):
        if old_name in self.installed_modules:
            self.installed_modules.remove(old_name)
            self.installed_modules.append(new_name)
            print(f"  [RENAME_MODULE] {old_name} -> {new_name}")

    def uninstall_module(self, cr, module_name):
        if module_name in self.installed_modules:
            self.installed_modules.remove(module_name)
            print(f"  [UNINSTALL_MODULE] {module_name} (removed)")

    def remove_module(self, cr, module_name):
        self.uninstall_module(cr, module_name)
