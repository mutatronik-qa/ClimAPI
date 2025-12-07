"""
Pruebas unitarias para el analizador de notebooks.
"""
import os
import json
import nbformat
import pandas as pd
import tempfile
import requests
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from scripts.ipynb_analyzer import (
    find_notebooks,
    extract_code_cells,
    extract_urls_and_sources,
    classify_df,
    attempt_extract_dfs_from_code,
    analyze_notebooks
)

class FakeResponse:
    """Mock para requests.Response"""
    def __init__(self, content, status_code=200):
        self.content = content if isinstance(content, bytes) else content.encode("utf-8")
        self.status_code = status_code
        self.text = content if isinstance(content, str) else content.decode("utf-8")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"Status {self.status_code}")

    def json(self):
        import json as _json
        return _json.loads(self.text)

@pytest.fixture
def tmp_notebook_dir(tmp_path):
    """Crea directorio temporal con notebooks de prueba."""
    # Notebook 1: con DataFrame literal y read_csv
    nb1 = nbformat.v4.new_notebook()
    nb1.cells.append(nbformat.v4.new_code_cell(
        "import pandas as pd\n"
        "df = pd.DataFrame({'date':['2025-01-01','2025-01-02'], 'value':[1,2]})"
    ))
    nb1.cells.append(nbformat.v4.new_code_cell(
        "import pandas as pd\n"
        "df2 = pd.read_csv('http://example.com/data.csv')"
    ))
    
    p1 = tmp_path / "test_notebook1.ipynb"
    nbformat.write(nb1, str(p1))
    
    # Notebook 2: sin datos cargables
    nb2 = nbformat.v4.new_notebook()
    nb2.cells.append(nbformat.v4.new_code_cell("print('Hello World')"))
    
    p2 = tmp_path / "test_notebook2.ipynb"
    nbformat.write(nb2, str(p2))
    
    yield str(tmp_path)

def test_find_notebooks(tmp_notebook_dir):
    """Prueba que find_notebooks encuentra .ipynb"""
    nbs = find_notebooks(tmp_notebook_dir)
    assert len(nbs) >= 2
    assert any("test_notebook1.ipynb" in str(n) for n in nbs)

def test_extract_code_cells(tmp_notebook_dir):
    """Prueba extracción de celdas de código."""
    nbs = find_notebooks(tmp_notebook_dir)
    nb = nbs[0]
    cells = extract_code_cells(nb)
    assert len(cells) > 0
    assert "import pandas" in cells[0] or "import pandas" in str(cells)

def test_extract_urls_and_sources():
    """Prueba extracción de URLs y patrones de código."""
    cells = [
        "import pandas as pd\ndf = pd.read_csv('http://example.com/data.csv')",
        "url = 'https://api.example.com/data'",
        "df2 = pd.DataFrame({'a':[1,2]})"
    ]
    result = extract_urls_and_sources(cells)
    assert "http://example.com/data.csv" in result["urls"]
    assert "https://api.example.com/data" in result["urls"]
    assert len(result["candidates"]) >= 2

@pytest.mark.parametrize("temp_data,expected_class", [
    # realtime: fecha reciente
    ({"date": ["2025-01-07", "2025-01-07"], "value": [1, 2]}, "realtime"),
    # historical: fecha antigua
    ({"date": ["2020-01-01", "2020-01-02"], "value": [1, 2]}, "historical"),
    # unknown: sin columna datetime
    ({"value": [1, 2], "name": ["a", "b"]}, "unknown")
])
def test_classify_df(temp_data, expected_class):
    """Prueba clasificación de DataFrames."""
    df = pd.DataFrame(temp_data)
    result = classify_df(df)
    assert result == expected_class

def test_classify_df_empty():
    """Prueba clasificación de DataFrame vacío."""
    df = pd.DataFrame()
    result = classify_df(df)
    assert result == "unknown"

@patch("requests.get")
def test_attempt_extract_dfs_from_code(mock_get):
    """Prueba extracción segura de DataFrames desde código."""
    # Mock descarga CSV
    mock_get.return_value = FakeResponse("date,value\n2025-01-01,10\n2025-01-02,12\n")
    
    cells = [
        "import pandas as pd\ndf = pd.read_csv('http://example.com/data.csv')",
        "df2 = pd.DataFrame({'a':[1,2], 'b':[3,4]})"
    ]
    
    dfs = attempt_extract_dfs_from_code(cells, "test_nb")
    assert len(dfs) > 0
    # Verificar que el primer df tiene datos
    assert isinstance(dfs[0][0], pd.DataFrame)

@patch("requests.get")
def test_analyze_notebooks(mock_get, tmp_notebook_dir):
    """Prueba análisis completo de notebooks."""
    # Mock requests
    mock_get.return_value = FakeResponse("date,value\n2025-01-01,10\n2025-01-02,12\n")
    
    results = analyze_notebooks(folder=tmp_notebook_dir, execute_safe=True)
    assert len(results) > 0
    assert "notebook" in results[0]
    assert "found_urls" in results[0]
    assert "exported" in results[0]

def test_analyze_notebooks_no_execute(tmp_notebook_dir):
    """Prueba análisis sin ejecutar cargas de datos."""
    results = analyze_notebooks(folder=tmp_notebook_dir, execute_safe=False)
    assert len(results) > 0
    # sin execute_safe, no debería haber exported
    for r in results:
        assert r["exported"] == []

def test_extract_urls_from_multiple_cells():
    """Prueba extracción de URLs desde múltiples celdas."""
    cells = [
        "url1 = 'https://api.example.com/data1'",
        "url2 = 'https://api.example.com/data2'",
        "url1_duplicado = 'https://api.example.com/data1'",  # duplicado
    ]
    result = extract_urls_and_sources(cells)
    # debe haber 2 URLs únicas
    assert len(result["urls"]) == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])