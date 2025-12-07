from pathlib import Path
# ...existing imports...
# Insertar import seguro del analizador
try:
    from scripts.ipynb_analyzer import analyze_notebooks  # type: ignore
except Exception:
    analyze_notebooks = None

def main():
    # ...existing code...
    # Analizar notebooks y exportar datasets (opcional)
    if analyze_notebooks is not None:
        try:
            print("🔎 Analizando notebooks (ejecución segura)...")
            nb_results = analyze_notebooks(folder=".", execute_safe=True)
            for r in nb_results:
                print(f" - {Path(r['notebook']).name}: urls={len(r['found_urls'])}, exported={len(r['exported'])}")
        except Exception as e:
            print(f"⚠️ Error en el analizador de notebooks: {e}")

    # ...resto del main...