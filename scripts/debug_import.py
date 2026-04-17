import os
import sys
import importlib.util
import traceback

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
print('root =', root)
sys.path.insert(0, root)
print('sys.path[0] =', sys.path[0])
p = os.path.join(root, 'tests', 'unit', 'data_sources', 'test_open_meteo.py')
print('test file =', p)

spec = importlib.util.spec_from_file_location('test_mod', p)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    print('import module success')
except Exception:
    traceback.print_exc()
