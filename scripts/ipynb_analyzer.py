"""
Analizador de notebooks .ipynb para extraer datos y clasificarlos como realtime/historical.

Este módulo:
- Encuentra todos los .ipynb en una carpeta
- Extrae URLs y código de lectura de datos
- Descarga CSVs de forma segura
- Detecta pd.DataFrame literales
- Clasifica datasets por timestamp
- Exporta a data/ con prefijo realtime_ o historical_
"""
import os
import re
import nbformat
import requests
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

NOTEBOOK_EXT = ".ipynb"
CACHE_DIR = Path("cache/ipynb_analyzer")
EXPORT_DIR = Path("data")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

URL_RE = re.compile(r"(https?://[^\s'\"\\)]+)")
PANDAS_READCSV_RE = re.compile(r"pd\.read_csv\(\s*([\"'])(?P<url>https?://[^\"']+)\1")

def find_notebooks(folder: str = ".") -> List[Path]:
    """Encuentra todos los archivos .ipynb en una carpeta recursivamente."""
    p = Path(folder)
    return [f for f in p.rglob(f"*{NOTEBOOK_EXT}")]

def extract_code_cells(nb_path: Path) -> List[str]:
    """Extrae todas las celdas de código de un notebook."""
    try:
        nb = nbformat.read(str(nb_path), as_version=4)
        cells = []
        for c in nb.cells:
            if c.cell_type == "code":
                cells.append(c.source)
        return cells
    except Exception as e:
        logger.warning(f"No se pudo leer notebook {nb_path}: {e}")
        return []

def extract_urls_and_sources(cells: List[str]) -> Dict[str, List[str]]:
    """Extrae URLs y candidatos de código que cargan datos."""
    urls = []
    candidates = []
    for src in cells:
        for m in URL_RE.finditer(src):
            urls.append(m.group(1))
        if "pd.read_csv" in src or "pd.DataFrame" in src:
            candidates.append(src)
    return {"urls": list(set(urls)), "candidates": candidates}

def safe_download_csv(url: str, timeout: int = 20) -> Optional[Path]:
    """Descarga CSV de forma segura desde una URL."""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        name = Path(url.split("?")[0]).name or "download.csv"
        dest = CACHE_DIR / f"{abs(hash(url))}_{name}"
        dest.write_bytes(r.content)
        logger.debug(f"CSV descargado: {url} -> {dest}")
        return dest
    except Exception as e:
        logger.debug(f"Fallo descarga de {url}: {e}")
        return None

def attempt_extract_dfs_from_code(cells: List[str], notebook_name: str) -> List[Tuple[pd.DataFrame, str]]:
    """
    Ejecuta solo cargas seguras detectadas:
    - pd.read_csv("http://...") -> descarga y lee con pandas
    - pd.DataFrame(<literal dict/list>) -> ast.literal_eval seguro
    """
    dfs = []
    for src in cells:
        # Detectar read_csv con URL
        for m in PANDAS_READCSV_RE.finditer(src):
            url = m.group("url")
            csv_path = safe_download_csv(url)
            if csv_path:
                try:
                    df = pd.read_csv(csv_path)
                    dfs.append((df, f"read_csv:{url}"))
                    logger.info(f"DataFrame cargado desde {url}: {len(df)} registros")
                except Exception as e:
                    logger.warning(f"No se pudo leer CSV {url}: {e}")
                    continue
        
        # Detectar pd.DataFrame({...}) literal
        if "pd.DataFrame" in src:
            try:
                tree = ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                        if func == "DataFrame":
                            if node.args:
                                arg = node.args[0]
                                if isinstance(arg, (ast.Dict, ast.List, ast.Tuple, ast.Constant)):
                                    try:
                                        literal = ast.literal_eval(arg)
                                        df = pd.DataFrame(literal)
                                        dfs.append((df, f"DataFrame_literal:{notebook_name}"))
                                        logger.info(f"DataFrame literal detectado: {len(df)} registros")
                                    except Exception:
                                        pass
            except Exception as e:
                logger.debug(f"Error parseando código en {notebook_name}: {e}")
                continue
    return dfs

def classify_df(df: pd.DataFrame) -> str:
    """
    Clasifica 'realtime' si el último timestamp está a <=2 horas de now,
    'historical' si es anterior, 'unknown' si no hay timestamps.
    """
    if df.empty:
        return "unknown"
    
    now = pd.Timestamp.now(tz=None)
    datetime_cols = [c for c in df.columns if any(k in c.lower() for k in ("date", "time", "timestamp"))]
    
    for c in datetime_cols:
        try:
            s = pd.to_datetime(df[c], errors="coerce")
            if s.notna().any():
                s = s.dropna()
                max_ts = s.max()
                delta_hours = (now - pd.to_datetime(max_ts)).total_seconds() / 3600.0
                if delta_hours <= 2:
                    return "realtime"
                else:
                    return "historical"
        except Exception:
            continue
    return "unknown"

def export_df(df: pd.DataFrame, origin: str, classification: str, notebook_name: str) -> Path:
    """Exporta DataFrame a CSV con prefijo de clasificación."""
    safe_name = f"{classification}_{notebook_name}_{abs(hash(origin))}.csv"
    dest = EXPORT_DIR / safe_name
    df.to_csv(dest, index=False)
    logger.info(f"DataFrame exportado: {dest}")
    return dest

def analyze_notebooks(folder: str = ".", execute_safe: bool = True) -> List[Dict]:
    """
    Recorre notebooks, extrae fuentes, intenta ejecución segura y exporta DataFrames.
    Retorna metadatos por notebook.
    """
    results = []
    notebooks = find_notebooks(folder)
    
    if not notebooks:
        logger.warning(f"No se encontraron notebooks en {folder}")
        return results
    
    for nb_path in notebooks:
        nb_name = nb_path.stem
        logger.info(f"Analizando notebook: {nb_path}")
        cells = extract_code_cells(nb_path)
        info = extract_urls_and_sources(cells)
        exported = []
        
        if execute_safe and cells:
            dfs = attempt_extract_dfs_from_code(cells, nb_name)
            for df, origin in dfs:
                cls = classify_df(df)
                out = export_df(df, origin, cls, nb_name)
                exported.append({
                    "origin": origin,
                    "classification": cls,
                    "path": str(out),
                    "rows": len(df),
                    "columns": list(df.columns)
                })
        
        results.append({
            "notebook": str(nb_path),
            "found_urls": info["urls"],
            "candidate_code_snippets": len(info["candidates"]),
            "exported": exported
        })
    
    return results

if __name__ == "__main__":
    import json
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Analiza notebooks y extrae datasets")
    parser.add_argument("--folder", default=".", help="Carpeta a analizar")
    parser.add_argument("--no-exec", action="store_true", help="No ejecutar pasos seguros")
    args = parser.parse_args()
    
    res = analyze_notebooks(args.folder, execute_safe=not args.no_exec)
    print(json.dumps(res, indent=2, ensure_ascii=False))