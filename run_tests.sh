#!/bin/bash
# Ejecución de Tests - ClimAPI
# ============================================

# NOTA: Ejecutar desde la raíz del proyecto (E:\GIT\ClimAPI)

echo "========================================"
echo "🧪 ClimAPI Test Suite"
echo "========================================"
echo ""

# Activar entorno virtual (Windows)
if [ -d "venv" ]; then
    echo "📦 Activando entorno virtual..."
    source venv/Scripts/activate 2>/dev/null || true
fi

# ------------------------------------------------
# EJECUTAR TODOS LOS TESTS
# ------------------------------------------------
echo "1. Ejecutando todos los tests..."
pytest tests/ -v

# Solo si el anterior éxito
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Todos los tests pasaron!"
fi

echo ""
echo "========================================"
echo " Comandos individuales"
echo "========================================"

# Unit tests (sin red)
echo ""
echo "2. Tests unitarios (sin red)..."
pytest tests/test_transform.py tests/test_storage.py -v

# Tests de API FastAPI
echo ""
echo "3. Tests de API FastAPI..."
pytest tests/test_api_endpoints_v2.py -v --ignore=tests/test_api_endpoints.py

# Tests del Dashboard
echo ""
echo "4. Tests del Dashboard (funciones auxiliares)..."
pytest tests/test_dashboard.py -v

# Tests de transformación
echo ""
echo "5. Tests de transformación..."
pytest tests/test_transform.py -v

# Tests de storage
echo ""
echo "6. Tests de storage..."
pytest tests/test_storage.py -v

# Tests con coverage
echo ""
echo "7. Tests con coverage..."
pytest tests/ --cov=. --cov-report=term-missing 2>/dev/null || echo "Install coverage: pip install pytest-cov"

echo ""
echo "========================================"
echo "✅ Suite de tests completada"
echo "========================================"