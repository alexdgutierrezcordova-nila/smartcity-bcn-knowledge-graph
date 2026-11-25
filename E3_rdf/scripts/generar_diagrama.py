"""Dibuja el diagrama del modelo v2 (estilo UML de pizarra) a partir de una
descripción declarativa de clases y relaciones.

Cada caja muestra: la clase, su superclase reutilizada y sus atributos clave.
Cada flecha lleva el nombre de la propiedad. El color indica la fuente de datos.

Salida: E3_rdf/modelo/modelo_datos.png y modelo_datos.svg

Uso:
    uv run --no-project --with matplotlib python E3_rdf/scripts/generar_diagrama.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

DIR_MODELO = Path(__file__).resolve().parents[1] / "modelo"

# Paleta: una por fuente de datos y otra para el nodo puente.
COLORES = {
    "bicing": ("#e3edf9", "#2f5f98"),    # Fuente 1: CityBikes (Bicing)
    "cams": ("#e4f3e6", "#2e7d3a"),      # Fuente 2: Open-Meteo (CAMS)
    "puente": ("#fff1d6", "#b7791f"),    # Nodo puente entre fuentes
    "contexto": ("#f1f1f1", "#6b6b6b"),  # Contexto compartido
}

# Posiciones en una rejilla: columnas x (centro) y filas y (centro).
X = {0: 0.1, 1: 0.365, 2: 0.635, 3: 0.9}
Y = {"arriba": 0.80, "medio": 0.50, "abajo": 0.17}
ANCHO = 0.18

# clave: (columna, fila, color, clase, superclase, atributos)
CLASES = {
    "org": (0, "arriba", "bicing", "schema:Organization", "",
            ["schema:name", "schema:identifier"]),
    "red": (1, "arriba", "bicing", "vocab:RedBicicletas", "⊑ schema:Service",
            ["schema:name", "schema:url", "schema:sameAs → dbr:Bicing"]),
    "bcn": (2, "arriba", "contexto", "schema:Place  (Barcelona)", "",
            ["schema:name", "schema:sameAs → dbr:Barcelona"]),
    "est": (1, "medio", "bicing", "vocab:EstacionBicicleta",
            "⊑ schema:CivicStructure\n⊑ sosa:FeatureOfInterest",
            ["schema:name, schema:identifier", "geo:lat, geo:long : decimal",
             "vocab:distanciaACentroideKm"]),
    "celda": (2, "medio", "puente", "vocab:CeldaModelo",
              "⊑ schema:Place\n⊑ sosa:FeatureOfInterest",
              ["schema:identifier", "geo:lat, geo:long : decimal", "schema:elevation : decimal"]),
    "estado": (1, "abajo", "bicing", "vocab:EstadoEstacion", "⊑ sosa:Observation",
               ["sosa:resultTime : dateTime", "vocab:bicicletasDisponibles : int",
                "vocab:anclajesLibres : int", "vocab:bicicletasMecanicas : int",
                "vocab:bicicletasElectricas : int", "vocab:enLinea : boolean"]),
    "obs": (2, "abajo", "cams", "vocab:ObservacionCalidadAire", "⊑ sosa:Observation",
            ["sosa:resultTime : dateTime", "sosa:hasSimpleResult : decimal"]),
    "cont": (3, "abajo", "cams", "vocab:Contaminante", "⊑ sosa:ObservableProperty",
             ["schema:name  (NO₂, PM10, PM2.5)", "schema:unitText  (µg/m³)",
              "rdfs:seeAlso → DBpedia"]),
}

# (origen, destino, propiedad, es_puente)
RELACIONES = [
    ("red", "org", "vocab:operadaPor", False),
    ("red", "bcn", "schema:areaServed", False),
    ("est", "red", "vocab:perteneceARed", False),
    ("celda", "bcn", "schema:containedInPlace", False),
    ("est", "celda", "vocab:contenidaEnCelda", True),
    ("estado", "est", "sosa:hasFeatureOfInterest", False),
    ("obs", "celda", "sosa:hasFeatureOfInterest", False),
    ("obs", "cont", "vocab:mideContaminante", False),
]

LINEA_TITULO, LINEA_SUPER, LINEA_ATRIB = 0.034, 0.026, 0.027


def alto(clave: str) -> float:
    _, _, _, _, superclase, atributos = CLASES[clave]
    lineas_super = len(superclase.splitlines())
    return LINEA_TITULO + LINEA_SUPER * lineas_super + 0.012 + LINEA_ATRIB * len(atributos)


def caja(ax, clave: str) -> None:
    col, fila, color, clase, superclase, atributos = CLASES[clave]
    fondo, borde = COLORES[color]
    cx, cy, h = X[col], Y[fila], alto(clave)
    x0, y1 = cx - ANCHO / 2, cy + h / 2
    ax.add_patch(FancyBboxPatch((x0, cy - h / 2), ANCHO, h, boxstyle="round,pad=0.004,rounding_size=0.008",
                                fc=fondo, ec=borde, lw=1.8 if color != "puente" else 2.6))
    y = y1 - LINEA_TITULO / 2 - 0.004
    ax.text(cx, y, clase, ha="center", va="center", fontsize=11, weight="bold", color=borde)
    y -= LINEA_TITULO / 2
    for linea in superclase.splitlines():
        ax.text(cx, y - LINEA_SUPER / 2 + 0.002, linea, ha="center", va="center",
                fontsize=8.8, style="italic", color="#444")
        y -= LINEA_SUPER
    ax.plot([x0 + 0.006, x0 + ANCHO - 0.006], [y, y], color=borde, lw=0.8)
    y -= 0.006
    for atributo in atributos:
        y -= LINEA_ATRIB
        ax.text(x0 + 0.009, y + LINEA_ATRIB / 2, atributo, ha="left", va="center",
                fontsize=8.8, family="DejaVu Sans Mono", color="#222")


def borde(clave: str, hacia: str) -> tuple[float, float]:
    """Punto del borde de la caja `clave` en dirección a la caja `hacia`."""
    col, fila = CLASES[clave][:2]
    col2, fila2 = CLASES[hacia][:2]
    cx, cy, h = X[col], Y[fila], alto(clave)
    if fila == fila2:
        return (cx + ANCHO / 2, cy) if X[col2] > cx else (cx - ANCHO / 2, cy)
    return (cx, cy + h / 2) if Y[fila2] > cy else (cx, cy - h / 2)


def flecha(ax, origen: str, destino: str, propiedad: str, puente: bool) -> None:
    p0, p1 = borde(origen, destino), borde(destino, origen)
    color = COLORES["puente"][1] if puente else "#333"
    ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", color=color,
                lw=3.2 if puente else 1.5, mutation_scale=18))
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    horizontal = abs(p0[1] - p1[1]) < 1e-6
    if horizontal:  # en dos líneas (prefijo / nombre) para que quepa entre las cajas
        propiedad = propiedad.replace(":", ":\n", 1)
    ax.text(mx + (0 if horizontal else 0.006), my + (0.04 if horizontal else 0), propiedad,
            ha="center" if horizontal else "left", va="center", fontsize=9.2,
            weight="bold" if puente else "normal", color=color,
            bbox=None if horizontal else dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.9))


def leyenda(ax) -> None:
    x, y = 0.015, 0.40
    ax.text(x, y, "Fuente de cada clase", fontsize=10.5, weight="bold", va="center")
    items = [("bicing", "Fuente 1 · CityBikes (Bicing)"), ("cams", "Fuente 2 · Open-Meteo (CAMS)"),
             ("puente", "Nodo puente entre fuentes"), ("contexto", "Contexto compartido")]
    for i, (clave, texto) in enumerate(items):
        fondo, borde_ = COLORES[clave]
        yy = y - 0.045 * (i + 1)
        ax.add_patch(FancyBboxPatch((x, yy - 0.012), 0.022, 0.024, boxstyle="round,pad=0.002",
                                    fc=fondo, ec=borde_, lw=1.5))
        ax.text(x + 0.03, yy, texto, fontsize=9.5, va="center")
    yy = y - 0.045 * 5 - 0.01
    notas = ["⊑  subclase de (vocabulario reutilizado)", "vocab:  término propio del proyecto",
             "dbr:  recurso de DBpedia (enlace LOD)"]
    for i, nota in enumerate(notas):
        ax.text(x, yy - 0.032 * i, nota, fontsize=9, va="center", color="#333")


def dibujar() -> None:
    fig, ax = plt.subplots(figsize=(20, 11))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.text(0.5, 0.975, "Modelo de datos v2 · Movilidad (Bicing) y calidad del aire (CAMS) en Barcelona",
            ha="center", va="center", fontsize=16, weight="bold")
    ax.text(0.5, 0.94, "Cada estado observa una estación y cada medición de aire observa una celda CAMS; "
            "la celda une ambas fuentes (Estación → contenidaEnCelda → Celda).",
            ha="center", va="center", fontsize=11, color="#444")
    for origen, destino, propiedad, puente in RELACIONES:
        flecha(ax, origen, destino, propiedad, puente)
    for clave in CLASES:
        caja(ax, clave)
    leyenda(ax)
    DIR_MODELO.mkdir(parents=True, exist_ok=True)
    fig.savefig(DIR_MODELO / "modelo_datos.png", dpi=170, bbox_inches="tight")
    fig.savefig(DIR_MODELO / "modelo_datos.svg", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    dibujar()
    print("Diagrama generado en", DIR_MODELO / "modelo_datos.png")
