"""
Script de inicio para el backend FastAPI
"""

import uvicorn
import os
import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

from app.config import settings

def main():
    """
    Inicia el servidor FastAPI
    """
    print("=" * 60)
    print("🚀 Clima Dashboard Backend - FastAPI")
    print("=" * 60)
    print(f"🌐 Servidor iniciado en: http://{settings.HOST}:{settings.PORT}")
    print(f"📖 Documentación Swagger: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"📖 Documentación ReDoc: http://{settings.HOST}:{settings.PORT}/redoc")
    print(f"🔍 Health Check: http://{settings.HOST}:{settings.PORT}/api/v1/health")
    print(f"💾 Caché TTL: {settings.CACHE_TTL_MINUTES} minutos")
    print(f"📊 Modo {'desarrollo' if settings.DEBUG else 'producción'}")
    print("=" * 60)
    
    # Iniciar servidor
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

if __name__ == "__main__":
    main()