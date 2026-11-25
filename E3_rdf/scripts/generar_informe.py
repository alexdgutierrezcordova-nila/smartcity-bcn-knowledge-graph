"""Genera el gráfico de nodos por clase y convierte el informe Markdown a Word.

Las capturas de GraphDB se colocan en E3_rdf/informe/capturas/ con los nombres que
cita el informe; si falta alguna, el .docx muestra un recuadro indicando cuál falta.

Uso:
    uv run --no-project --with rdflib --with pandas --with matplotlib --with python-docx \
        python E3_rdf/scripts/generar_informe.py
"""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Inches, Pt, RGBColor  # noqa: E402

import generar_rdf as gen  # noqa: E402

DIR_INFORME = gen.RAIZ / "E3_rdf" / "informe"
RUTA_MD = DIR_INFORME / "Informe_proyecto.md"
RUTA_DOCX = DIR_INFORME / "Informe_proyecto.docx"
DIR_CAPTURAS = DIR_INFORME / "capturas"


def grafico_nodos() -> None:
    """Dibuja el total de nodos por clase a partir de los .ttl generados."""
    g = gen.nuevo_grafo()
    for f in ("bicing.ttl", "calidad_aire.ttl"):
        g.parse(gen.DIR_SALIDA / f)
    tabla = gen.nodos_por_clase(g).sort_values("Nodos")
    fig, ax = plt.subplots(figsize=(8, 4))
    barras = ax.barh(tabla["Clase"], tabla["Nodos"], color="#3b6ea5")
    ax.bar_label(barras, padding=3)
    ax.set_xlabel("Número de nodos (instancias)")
    ax.set_title("Nodos por clase en el grafo RDF generado")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    DIR_CAPTURAS.mkdir(parents=True, exist_ok=True)
    fig.savefig(DIR_CAPTURAS / "nodos_por_clase.png", dpi=200)
    plt.close(fig)


def texto_con_formato(parrafo, texto: str) -> None:
    """Añade texto interpretando **negrita** y `código`."""
    for parte in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", texto):
        if parte.startswith("**") and parte.endswith("**"):
            parrafo.add_run(parte[2:-2]).bold = True
        elif parte.startswith("`") and parte.endswith("`"):
            run = parrafo.add_run(parte[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif parte:
            parrafo.add_run(parte)


def agregar_tabla(doc: Document, lineas: list[str]) -> None:
    filas = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lineas]
    filas = [f for f in filas if not all(re.fullmatch(r":?-+:?", c) for c in f)]
    tabla = doc.add_table(rows=len(filas), cols=len(filas[0]))
    tabla.style = "Light Grid Accent 1"
    for i, fila in enumerate(filas):
        for j, valor in enumerate(fila):
            celda = tabla.cell(i, j)
            celda.text = ""
            texto_con_formato(celda.paragraphs[0], valor)
            for run in celda.paragraphs[0].runs:
                run.font.size = Pt(9)
                run.bold = run.bold or i == 0
    doc.add_paragraph()


def agregar_imagen(doc: Document, alt: str, ruta_rel: str) -> None:
    ruta = (DIR_INFORME / ruta_rel).resolve()
    if ruta.exists():
        doc.add_picture(str(ruta), width=Inches(6.2))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p = doc.add_paragraph()
        run = p.add_run(f"[Insertar captura: {ruta.name}]")
        run.bold = True
        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pie = doc.add_paragraph(alt)
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pie.runs[0].italic = True
    pie.runs[0].font.size = Pt(9)


def convertir() -> list[str]:
    """Convierte el Markdown a .docx y devuelve las capturas que faltan."""
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    lineas = RUTA_MD.read_text(encoding="utf-8").splitlines()
    faltantes, i = [], 0
    while i < len(lineas):
        ln = lineas[i]
        if ln.startswith("|"):
            bloque = []
            while i < len(lineas) and lineas[i].startswith("|"):
                bloque.append(lineas[i])
                i += 1
            agregar_tabla(doc, bloque)
            continue
        imagen = re.fullmatch(r"!\[(.*)\]\((.*)\)", ln.strip())
        if imagen:
            agregar_imagen(doc, *imagen.groups())
            if not (DIR_INFORME / imagen.group(2)).exists():
                faltantes.append(imagen.group(2))
        elif ln.startswith("#"):
            nivel = len(ln) - len(ln.lstrip("#"))
            doc.add_heading(ln.lstrip("#").strip(), level=nivel - 1 if nivel > 1 else 0)
        elif ln.startswith("- "):
            texto_con_formato(doc.add_paragraph(style="List Bullet"), ln[2:])
        elif ln.strip():
            texto_con_formato(doc.add_paragraph(), ln)
        i += 1
    doc.save(RUTA_DOCX)
    return faltantes


if __name__ == "__main__":
    grafico_nodos()
    faltan = convertir()
    print("Informe generado:", RUTA_DOCX.relative_to(gen.RAIZ))
    for f in faltan:
        print("  Falta captura:", f)
