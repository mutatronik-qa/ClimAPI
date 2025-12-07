import os
import re
import nbformat
import requests
import tempfile
import ast
from pathlib import Path
import pandas as pd
from typing import List, Dict, Tuple, Optional

NOTEBOOK_EXT = ".ipynb"
CACHE_DIR = Path("cache/ipynb_analyzer")
EXPORT_DIR = Path("data")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

URL_RE = re.compile(r"(https?://[^\s'\"\\)]+)")
PANDAS_READCSV_RE = re.compile(r"pd\.read_csv\(\s*([\"'])(?P<url>https?://[^\"']+)\1")

def find_notebooks(folder: str = ".") -> List[Path]:
    p = Path(folder)
    return [f for f in p.rglob(f"*{NOTEBOOK_EXT}")]

def extract_code_cells(nb_path: Path) -> List[str]:
    nb = nbformat.read(nb_path, as_version=4)
    cells = []
    for c in nb.cells:
        if c.cell_type == "code":
            cells.append(c.source)
    return cells

def extract_urls_and_sources(cells: List[str]) -> Dict[str, List[str]]:
    urls = []
    candidates = []
    for src in cells:
        for m in URL_RE.finditer(src):
            urls.append(m.group(1))
        if "pd.read_csv" in src or "pd.DataFrame" in src:
            candidates.append(src)
    return {"urls": list(set(urls)), "candidates": candidates}

def safe_download_csv(url: str, timeout: int = 20) -> Optional[Path]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        name = Path(url.split("?")[0]).name or "download.csv"
        dest = CACHE_DIR / f"{abs(hash(url))}_{name}"
        dest.write_bytes(r.content)
        return dest
    except Exception:
        return None

def attempt_extract_dfs_from_code(cells: List[str], notebook_name: str) -> List[Tuple[pd.DataFrame, str]]:
    """
    Ejecuta solo cargas seguras detectadas:
    - pd.read_csv("http://...") -> descarga + pandas.read_csv
    - pd.DataFrame(<literal dict/list>) -> ast.literal_eval seguro
    """
    dfs = []
    for src in cells:
        for m in PANDAS_READCSV_RE.finditer(src):
            url = m.group("url")
            csv_path = safe_download_csv(url)
            if csv_path:
                try:
                    df = pd.read_csv(csv_path)
                    dfs.append((df, f"read_csv:{url}"))
                except Exception:
                    continue
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
                                    literal = ast.literal_eval(arg)
                                    df = pd.DataFrame(literal)
                                    dfs.append((df, f"DataFrame_literal:{notebook_name}"))
            except Exception:
                continue
    return dfs

def classify_df(df: pd.DataFrame) -> str:
    """
    Clasifica 'realtime' si el último timestamp está a <=2 horas de now,
    'historical' si es anterior, 'unknown' si no hay timestamps.
    """
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
    safe_name = f"{classification}_{notebook_name}_{abs(hash(origin))}.csv"
    dest = EXPORT_DIR / safe_name
    df.to_csv(dest, index=False)
    return dest

def analyze_notebooks(folder: str = ".", execute_safe: bool = True) -> List[Dict]:
    """
    Recorre notebooks, extrae fuentes, intenta ejecución segura y exporta DataFrames.
    Retorna metadatos por notebook.
    """
    results = []
    for nb_path in find_notebooks(folder):
        nb_name = nb_path.stem
        cells = extract_code_cells(nb_path)
        info = extract_urls_and_sources(cells)
        exported = []
        if execute_safe:
            dfs = attempt_extract_dfs_from_code(cells, nb_name)
            for df, origin in dfs:
                cls = classify_df(df)
                out = export_df(df, origin, cls, nb_name)
                exported.append({"origin": origin, "classification": cls, "path": str(out)})
        results.append({
            "notebook": str(nb_path),
            "found_urls": info["urls"],
            "candidate_code_snippets": len(info["candidates"]),
            "exported": exported
        })
    return results

if __name__ == "__main__":
    import json, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", default=".")
    parser.add_argument("--no-exec", action="store_true", help="No ejecutar pasos seguros")
    args = parser.parse_args()
    res = analyze_notebooks(args.folder, execute_safe=not args.no_exec)
    print(json.dumps(res, indent=2, ensure_ascii=False))