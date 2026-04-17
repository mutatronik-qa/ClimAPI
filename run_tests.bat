@echo off
REM Ejecucion de Tests - ClimAPI (Windows)
REM ============================================
REM NOTA: Ejecutar desde la raíz del proyecto (E:\GIT\ClimAPI)

echo ========================================
echo 🧪 ClimAPI Test Suite
echo ========================================
echo.

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM ----------------------------------------
REM EJECUTAR TODOS LOS TESTS
REM ----------------------------------------
echo 1. Ejecutando todos los tests...
pytest tests/ -v
echo.

REM Unit tests (sin red)
echo 2. Tests unitarios (sin red)...
pytest tests/test_transform.py tests/test_storage.py -v
echo.

REM Tests de API FastAPI
echo 3. Tests de API FastAPI...
pytest tests/test_api_endpoints_v2.py -v
echo.

REM Tests del Dashboard
echo 4. Tests del Dashboard...
pytest tests/test_dashboard.py -v
echo.

REM Tests de transform
echo 5. Tests de transformacion...
pytest tests/test_transform.py -v
echo.

REM Tests de storage
echo 6. Tests de storage...
pytest tests/test_storage.py -v
echo.

echo ========================================
echo ✅ Suite de tests completada
echo ========================================
pause