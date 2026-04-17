import sys
import os
import importlib

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root)
print('root', root)
print('sys.path[0]', sys.path[0])
try:
    import data_sources
    print('data_sources.__file__', data_sources.__file__)
    print('data_sources.__path__', list(data_sources.__path__))
    import pkgutil
    print('modules in data_sources:', [m.name for m in pkgutil.iter_modules(data_sources.__path__)])
    import data_sources.open_meteo
    print('imported open_meteo', data_sources.open_meteo.__file__)
except Exception as e:
    import traceback; traceback.print_exc()
