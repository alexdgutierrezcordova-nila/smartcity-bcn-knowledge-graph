"""Recorrido guiado por GraphDB y capturas para el informe.

Abre un navegador VISIBLE (para seguir la demostración en pantalla) y recorre el
repositorio `bcn-kg` paso a paso. Antes de cada captura muestra un cartel que
explica qué se está viendo; el cartel se quita antes de guardar la imagen.

Capturas generadas en E3_rdf/informe/capturas/:
    graphdb_importacion.png      Graphs overview: un solo grafo con el modelo y las 3 fuentes
    graphdb_nodos_por_clase.png  Consulta 01: nodos por clase
    graphdb_grafo.png            Consulta 04 en Visual graph: una estación con todas sus conexiones
    graphdb_jerarquia.png        Visual graph de un distrito: barrios → distrito → Barcelona
    graphdb_grafo_enlace.png     Visual graph de una celda CAMS: el nodo puente con el aire
    graphdb_integracion.png      Consulta 06: tabla de integración movilidad + calidad del aire

Requisito: GraphDB en marcha (docker compose up -d) con el repositorio cargado (cargar_graphdb.py).

Uso:
    uv run --no-project --with playwright python E3_rdf/scripts/capturar_graphdb.py [--oculto]
    (la primera vez: uv run --no-project --with playwright playwright install chromium)
"""

from __future__ import annotations

import argparse
import urllib.parse
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
DIR_SPARQL = RAIZ / "E3_rdf" / "sparql"
DIR_CAPTURAS = RAIZ / "E3_rdf" / "informe" / "capturas"
DATA = "http://example.org/bcn-kg/data/"
CARTEL = """(texto) => {
  const d = document.createElement('div'); d.id = 'cartel-demo'; d.textContent = texto;
  Object.assign(d.style, {position: 'fixed', left: '50%', bottom: '28px', transform: 'translateX(-50%)',
    background: '#1f2933', color: '#fff', padding: '14px 22px', borderRadius: '10px', zIndex: 99999,
    font: '600 19px -apple-system, Segoe UI, sans-serif', maxWidth: '1100px', textAlign: 'center',
    boxShadow: '0 6px 24px rgba(0,0,0,.35)'});
  document.body.appendChild(d);
}"""


def consulta(nombre: str) -> str:
    return (DIR_SPARQL / nombre).read_text(encoding="utf-8")


# El aviso de cookies del Workbench se oculta (no se acepta): solo tapa la captura.
OCULTAR_AVISO = """() => {
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if ((s.position === 'fixed' || s.position === 'sticky') && /cookies/i.test(el.textContent || '')) {
      el.style.display = 'none';
    }
  }
}"""


def paso(pg: Page, texto: str, archivo: str, espera_ms: int, bajar_px: int = 0) -> None:
    """Muestra el cartel para quien mira la pantalla, lo quita y guarda la captura."""
    pg.wait_for_timeout(espera_ms)
    if bajar_px:  # baja hasta la tabla (una captura de página completa haría que GraphDB vuelva a dibujarla)
        pg.mouse.move(1200, 600)
        pg.mouse.wheel(0, bajar_px)
        pg.wait_for_timeout(800)
    pg.evaluate(OCULTAR_AVISO)
    pg.evaluate(CARTEL, texto)
    pg.wait_for_timeout(3500)
    pg.evaluate("() => document.getElementById('cartel-demo')?.remove()")
    pg.screenshot(path=str(DIR_CAPTURAS / archivo))
    print(f"  ✓ {archivo}")


def abrir_sparql(pg: Page, base: str, archivo: str) -> None:
    """Carga la consulta en el editor SPARQL, la ejecuta y espera a que aparezcan los resultados."""
    pg.goto(f"{base}/sparql?query={urllib.parse.quote(consulta(archivo))}&execute=true")
    pg.locator("text=Showing results >> visible=true").first.wait_for(timeout=60000)
    pg.locator("text=Rendering results").first.wait_for(state="hidden", timeout=60000)
    pg.wait_for_timeout(1000)


def ejecutar(base: str, oculto: bool) -> None:
    DIR_CAPTURAS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=oculto, slow_mo=0 if oculto else 250)
        pg = navegador.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.5)

        print("1. Seleccionar el repositorio bcn-kg")
        pg.goto(f"{base}/graphs")
        pg.wait_for_timeout(2000)
        pg.locator("text=bcn-kg >> visible=true").first.click()
        paso(pg, "Paso 1 · Graphs overview: UN solo grafo (graph/bcn-kg) con el modelo y las tres fuentes",
             "graphdb_importacion.png", 2500)

        print("2. Nodos por clase")
        abrir_sparql(pg, base, "01_nodos_por_clase.rq")
        paso(pg, "Paso 2 · Consulta 01: total de nodos por clase (con las superclases que infiere GraphDB)",
             "graphdb_nodos_por_clase.png", 1500, bajar_px=330)

        print("3. Una estación con todas sus conexiones")
        pg.goto(f"{base}/graphs-visualizations?query={urllib.parse.quote(consulta('04_grafo_visual.rq'))}")
        paso(pg, "Paso 3 · Estado → Estación → Barrio → Distrito → Barcelona · Estación → Celda CAMS ← NO₂, PM10, PM2.5",
             "graphdb_grafo.png", 7000)

        print("4. Jerarquía territorial")
        pg.goto(f"{base}/graphs-visualizations?uri={urllib.parse.quote(DATA + 'distrito_06')}")
        paso(pg, "Paso 4 · Distrito de Gràcia: sus barrios y Barcelona (schema:containedInPlace)",
             "graphdb_jerarquia.png", 6000)

        print("5. Celda CAMS: nodo puente con la calidad del aire")
        pg.goto(f"{base}/graphs-visualizations?uri={urllib.parse.quote(DATA + 'celda_41.35_2.15')}")
        paso(pg, "Paso 5 · Celda CAMS 41.35, 2.15: estaciones que contiene y mediciones de aire que tratan de ella",
             "graphdb_grafo_enlace.png", 6000)

        print("6. Tabla de integración movilidad + calidad del aire")
        abrir_sparql(pg, base, "06_integracion_movilidad_aire.rq")
        paso(pg, "Paso 6 · Consulta 06: una fila por estación con barrio, distrito, bicicletas y aire de su celda",
             "graphdb_integracion.png", 1500)

        print("7. Resumen por distrito")
        abrir_sparql(pg, base, "07_resumen_por_distrito.rq")
        paso(pg, "Paso 7 · Consulta 07: estaciones, bicicletas y NO₂ medio por distrito",
             "graphdb_distritos.png", 1500, bajar_px=330)
        navegador.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recorrido guiado por GraphDB y capturas para el informe")
    parser.add_argument("--url", default="http://localhost:7200")
    parser.add_argument("--oculto", action="store_true", help="sin ventana visible (solo capturas)")
    args = parser.parse_args()
    ejecutar(args.url, args.oculto)
