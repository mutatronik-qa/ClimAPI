import sys  
sys.path.insert(0, r'E:\\GIT\\ClimAPI')  
try:  
    import data_sources.open_meteo as om  
    print('OK', om.__file__)  
except Exception as e:  
    import traceback  
    traceback.print_exc()  
