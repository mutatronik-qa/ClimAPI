from config.settings import settings
try:
    from data_sources.siata import SIATAClient
    print("✓ SIATAClient imported (root path)")
except ImportError:
    try:
        from src.data_sources.siata import SIATAClient
        print("✓ SIATAClient imported (src path)")
    except ImportError:
        print("❌ SIATAClient import failed")

try:
    from processing.storage import CacheManager
    print("✓ CacheManager imported")
except ImportError:
    print("❌ CacheManager import failed")

print("✓ Basics verified")
