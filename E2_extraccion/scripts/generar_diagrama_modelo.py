"""Genera el diagrama conceptual bipartito (UML-RDF) y sincroniza el notebook (.ipynb) y el reporte (.html)."""

import base64
import json
import re
import sys
from pathlib import Path

dir_base = Path(__file__).resolve().parent.parent
if str(dir_base / "src") not in sys.path:
    sys.path.insert(0, str(dir_base / "src"))

import matplotlib
matplotlib.use("Agg")

from bcn_kg.diagrama import dibujar_modelo


def main() -> None:
    ruta_png = dir_base / "modelo" / "modelo_datos.png"
    ruta_ipynb = dir_base / "notebooks" / "E2_extraccion_limpieza.ipynb"
    ruta_html = dir_base / "notebooks" / "E2_extraccion_limpieza.html"

    # 1. Generar el PNG con la notación bipartita de cátedra
    dibujar_modelo(ruta_png)
    b64_png = base64.b64encode(ruta_png.read_bytes()).decode("ascii")
    print(f"Diagrama PNG generado: {ruta_png} ({ruta_png.stat().st_size} bytes)")

    # 2. Actualizar la salida embebida en E2_extraccion_limpieza.ipynb
    nb = json.loads(ruta_ipynb.read_text(encoding="utf-8"))
    actualizado_nb = False
    for c in nb["cells"]:
        if c.get("cell_type") == "code" and "dibujar_modelo" in "".join(c.get("source", [])):
            c["outputs"] = [
                {
                    "data": {
                        "image/png": b64_png,
                        "text/plain": ["<Figure size 2960x1840 with 1 Axes>"]
                    },
                    "metadata": {},
                    "output_type": "display_data"
                }
            ]
            actualizado_nb = True
            break

    if actualizado_nb:
        ruta_ipynb.write_text(json.dumps(nb, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Notebook .ipynb sincronizado con el nuevo diagrama bipartito.")

    # 3. Actualizar la imagen base64 en E2_extraccion_limpieza.html
    html_text = ruta_html.read_text(encoding="utf-8")
    patron = r'(<div class="jp-Cell jp-CodeCell jp-Notebook-cell" id="cell-id=diag-code-01">.*?<img alt="[^"]*" class="" src="data:image/png;base64,)([^"]+)("/>)'
    nuevo_html, n_reemplazos = re.subn(patron, rf"\g<1>{b64_png}\g<3>", html_text, count=1, flags=re.DOTALL)
    if n_reemplazos > 0:
        ruta_html.write_text(nuevo_html, encoding="utf-8")
        print("Reporte .html sincronizado con el nuevo diagrama bipartito.")
    else:
        print("Aviso: no se encontró el marcador cell-id=diag-code-01 en el HTML.")


if __name__ == "__main__":
    main()
