"""Script para convertir E1_base_corregida.md a formato Word (.docx) profesional."""

from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DIR_RAIZ = Path(__file__).resolve().parent.parent
RUTA_MD = DIR_RAIZ.parent / "E1_correccion" / "E1_base_corregida.md"
RUTA_DOCX = DIR_RAIZ.parent / "E1_correccion" / "E1_base_corregida.docx"


def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def set_table_borders(table):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
        f'<w:left w:val="none"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="1F497D"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def generar_docx():
    doc = Document()

    # Configurar márgenes
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Estilo base
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Calibri'
    style_normal.font.size = Pt(11)
    style_normal.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    with open(RUTA_MD, "r", encoding="utf-8") as f:
        lineas = [l.rstrip() for l in f.readlines()]

    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()

        if not linea:
            i += 1
            continue

        # Encabezado nivel 1
        if linea.startswith("# "):
            texto = linea[2:].strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(texto)
            run.font.name = 'Calibri'
            run.font.size = Pt(20)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)  # Azul institucional
            i += 1
            continue

        # Encabezado nivel 2
        if linea.startswith("## "):
            texto = linea[3:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(texto)
            run.font.name = 'Calibri'
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)
            i += 1
            continue

        # Encabezado nivel 3
        if linea.startswith("### "):
            texto = linea[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
            run = p.add_run(texto)
            run.font.name = 'Calibri'
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
            i += 1
            continue

        # Separador horizontal
        if linea.startswith("---"):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run("―" * 45)
            run.font.color.rgb = RGBColor(0xBD, 0xD7, 0xEE)
            i += 1
            continue

        # Tablas Markdown
        if linea.startswith("|") and i + 1 < len(lineas) and "---" in lineas[i + 1]:
            # Procesar tabla completa
            filas_tabla = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                if "---" in lineas[i]:
                    i += 1
                    continue
                partes = [c.strip() for c in lineas[i].strip().strip("|").split("|")]
                filas_tabla.append(partes)
                i += 1

            if filas_tabla:
                n_cols = max(len(r) for r in filas_tabla)
                t = doc.add_table(rows=len(filas_tabla), cols=n_cols)
                t.alignment = WD_TABLE_ALIGNMENT.CENTER
                set_table_borders(t)

                for r_idx, fila in enumerate(filas_tabla):
                    for c_idx in range(n_cols):
                        val = fila[c_idx] if c_idx < len(fila) else ""
                        cell = t.cell(r_idx, c_idx)
                        cell.text = val
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_before = Pt(3)
                        p.paragraph_format.space_after = Pt(3)
                        p.paragraph_format.line_spacing = 1.05

                        if r_idx == 0:
                            # Encabezado de tabla
                            set_cell_background(cell, "1F497D")
                            for run in p.runs:
                                run.font.bold = True
                                run.font.size = Pt(9.5)
                                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                        else:
                            # Filas alternas
                            if r_idx % 2 == 1:
                                set_cell_background(cell, "F2F5F9")
                            for run in p.runs:
                                run.font.size = Pt(9.0)
                doc.add_paragraph()  # Espacio tras tabla
            continue

        # Viñetas
        if linea.startswith("* ") or linea.startswith("- "):
            texto = linea[2:].strip()
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            # Procesar negritas simples
            partes = texto.split("**")
            for idx_p, trozo in enumerate(partes):
                run = p.add_run(trozo)
                if idx_p % 2 == 1:
                    run.font.bold = True
            i += 1
            continue

        # Párrafo normal
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        partes = linea.split("**")
        for idx_p, trozo in enumerate(partes):
            run = p.add_run(trozo)
            if idx_p % 2 == 1:
                run.font.bold = True
        i += 1

    doc.save(RUTA_DOCX)
    print(f"Documento Word guardado exitosamente en: {RUTA_DOCX}")


if __name__ == "__main__":
    generar_docx()
