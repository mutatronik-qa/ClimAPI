# tests/test_cache.py
from processing.storage import CacheManager
import pandas as pd
from datetime import datetime, timedelta

def test_cache_operations():
    cache = CacheManager(ttl_minutes=15)
    test_data = pd.DataFrame({'test': [1, 2, 3]})
    
    # Test set y get
    cache.set_processed_data(6.244, -75.581, 'America/Bogota', test_data)
    cached_data = cache.get_processed_data(6.244, -75.581, 'America/Bogota')
    
    assert cached_data is not None
    assert len(cached_data) == 3