"""Entregable 3 — Generación de datos RDF (Smart City Barcelona).

Convierte los CSV limpios del Entregable 2 en RDF (Turtle) siguiendo el
modelo v2 (E3_rdf/modelo/vocab.ttl y modelo_datos.png).

Salidas en E3_rdf/rdf/:
    bicing.ttl        Fuente 1: red Bicing, operadores, estaciones y estados.
    calidad_aire.ttl  Fuente 2: Barcelona, celdas CAMS, contaminantes y observaciones.
    estadisticas.md   Total de nodos por clase y total de tripletas.

Uso:
    uv run --no-project --with rdflib --with pandas python E3_rdf/scripts/generar_rdf.py [--limit N]
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, XSD

import preprocesar

# ---------------------------------------------------------------------------
# Rutas y espacios de nombres
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[2]
DIR_PROCESADOS = RAIZ / "E2_extraccion" / "data" / "processed"
RUTA_VOCAB = RAIZ / "E3_rdf" / "modelo" / "vocab.ttl"
DIR_SALIDA = RAIZ / "E3_rdf" / "rdf"

# Una sola URI base para TODAS las fuentes: así los nodos comunes se enlazan.
DATA = Namespace("http://example.org/bcn-kg/data/")
VOCAB = Namespace("http://example.org/bcn-kg/vocab#")
SCHEMA = Namespace("https://schema.org/")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
DBR = Namespace("http://dbpedia.org/resource/")

PREFIJOS = {
    "data": DATA, "vocab": VOCAB, "schema": SCHEMA, "sosa": SOSA,
    "geo": GEO, "dcterms": DCTERMS, "rdfs": RDFS, "xsd": XSD, "dbr": DBR,
}


# ---------------------------------------------------------------------------
# Esquema de identificación de entidades (URIs)
# ---------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Formatea un texto para usarlo como nombre local de una URI.

    Quita tildes y diacríticos, reemplaza espacios y símbolos por '_' y
    elimina guiones bajos sobrantes. Es la MISMA regla para ambas fuentes.
    Ejemplo: 'Barcelona de Serveis Municipals, S.A. (BSM)'
             -> 'Barcelona_de_Serveis_Municipals_S.A._BSM'
    """
    ascii_ = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_).strip("_")


def compactar_fecha(iso: str) -> str:
    """'2026-11-12T16:30:24.89+00:00' -> '20261112T163024' (para URIs)."""
    return re.sub(r"[^0-9T]", "", str(iso))[:15]


def uri_red() -> URIRef:
    return DATA["red_bicing"]


def uri_ciudad() -> URIRef:
    return DATA["Barcelona"]


def uri_operador(nombre: str) -> URIRef:
    return DATA[f"organizacion_{normalizar(nombre)}"]


def uri_estacion(id_estacion: str) -> URIRef:
    return DATA[f"estacion_{normalizar(id_estacion)}"]


def uri_estado(id_estacion: str, captura_utc: str) -> URIRef:
    return DATA[f"estado_{normalizar(id_estacion)}_{compactar_fecha(captura_utc)}"]


def uri_celda(id_celda: str) -> URIRef:
    # El id ya viene como 'celda_41.40_2.20': se usa tal cual en ambas fuentes.
    return DATA[normalizar(id_celda)]


def uri_contaminante(codigo: str) -> URIRef:
    return DATA[f"contaminante_{normalizar(codigo)}"]


def uri_observacion(id_celda: str, hora_utc: str, codigo: str) -> URIRef:
    return DATA[f"obs_{normalizar(id_celda)}_{compactar_fecha(hora_utc)}_{normalizar(codigo)}"]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def nuevo_grafo() -> Graph:
    """Crea un grafo vacío con todos los prefijos del modelo registrados."""
    g = Graph()
    for prefijo, ns in PREFIJOS.items():
        g.bind(prefijo, ns, override=True, replace=True)
    return g


def decimal(valor) -> Literal:
    return Literal(str(valor), datatype=XSD.decimal)


def entero(valor) -> Literal:
    return Literal(int(valor), datatype=XSD.nonNegativeInteger)


def fecha_hora(valor: str) -> Literal:
    return Literal(str(valor), datatype=XSD.dateTime)


def cargar_csv(limite: int = 0) -> dict[str, pd.DataFrame]:
    """Lee los CSV procesados en E2 y el preprocesamiento CAMS de E3. Con `limite` toma solo N filas (prueba)."""
    nombres = ["citybikes_estaciones", "citybikes_estado", "citybikes_operadores", "procedencia"]
    dfs = {n: pd.read_csv(DIR_PROCESADOS / f"{n}.csv") for n in nombres}
    # Celdas, observaciones y enlace vienen del preprocesamiento E3 (rejilla CAMS corregida)
    pre = preprocesar.ejecutar(guardar=False)
    dfs["openmeteo_celdas"] = pre["celdas_cams"]
    dfs["openmeteo_observaciones"] = pre["observaciones_cams"]
    dfs["enlace_estacion_celda"] = pre["enlace_estacion_celda"]
    if limite:
        dfs["citybikes_estaciones"] = dfs["citybikes_estaciones"].head(limite)
        ids = set(dfs["citybikes_estaciones"].id_estacion)
        for n in ("citybikes_estado", "enlace_estacion_celda"):
            dfs[n] = dfs[n][dfs[n].id_estacion.isin(ids)]
        dfs["openmeteo_observaciones"] = dfs["openmeteo_observaciones"].head(limite)
    return dfs


def url_y_fecha(procedencia: pd.DataFrame, fuente: str) -> tuple[str, str]:
    """Devuelve (url, extraido_utc) de la captura cruda de una fuente."""
    fila = procedencia[procedencia.archivo_raw.str.contains(fuente)].iloc[0]
    return fila.url, fila.extraido_utc


# ---------------------------------------------------------------------------
# Fuente 1: CityBikes (Bicing)
# ---------------------------------------------------------------------------
def agregar_ciudad(g: Graph) -> URIRef:
    """Barcelona como schema:Place, enlazada a DBpedia. Se declara en ambas fuentes
    con las mismas tripletas, así cada archivo queda completo por sí solo."""
    ciudad = uri_ciudad()
    g.add((ciudad, RDF.type, SCHEMA.Place))
    g.add((ciudad, SCHEMA.name, Literal("Barcelona")))
    g.add((ciudad, SCHEMA.sameAs, DBR.Barcelona))
    return ciudad


def generar_bicing(dfs: dict[str, pd.DataFrame]) -> Graph:
    """Instancia RedBicicletas, Organization, EstacionBicicleta y EstadoEstacion."""
    g = nuevo_grafo()
    url, _ = url_y_fecha(dfs["procedencia"], "citybikes")

    red = uri_red()
    g.add((red, RDF.type, VOCAB.RedBicicletas))
    g.add((red, SCHEMA.identifier, Literal("bicing")))
    g.add((red, SCHEMA.name, Literal("Bicing")))
    g.add((red, SCHEMA.areaServed, agregar_ciudad(g)))
    g.add((red, SCHEMA.url, Literal(url, datatype=XSD.anyURI)))
    g.add((red, SCHEMA.sameAs, DBR.Bicing))

    for op in dfs["citybikes_operadores"].itertuples():
        u = uri_operador(op.nombre)
        g.add((u, RDF.type, SCHEMA.Organization))
        g.add((u, SCHEMA.identifier, Literal(normalizar(op.nombre))))
        g.add((u, SCHEMA.name, Literal(op.nombre)))
        g.add((red, VOCAB.operadaPor, u))

    enlace = dfs["enlace_estacion_celda"].set_index("id_estacion")
    for est in dfs["citybikes_estaciones"].itertuples():
        u = uri_estacion(est.id_estacion)
        g.add((u, RDF.type, VOCAB.EstacionBicicleta))
        g.add((u, SCHEMA.identifier, Literal(str(est.uid))))
        g.add((u, SCHEMA.name, Literal(est.nombre_limpio)))
        g.add((u, GEO.lat, decimal(est.latitud)))
        g.add((u, GEO.long, decimal(est.longitud)))
        g.add((u, VOCAB.perteneceARed, red))
        if est.id_estacion in enlace.index:
            fila = enlace.loc[est.id_estacion]
            # Nodo puente con la Fuente 2: misma URI de celda que en calidad_aire.ttl
            g.add((u, VOCAB.contenidaEnCelda, uri_celda(fila.id_celda)))
            g.add((u, VOCAB.distanciaACentroideKm, decimal(fila.distancia_centro_km)))

    columnas = {
        VOCAB.bicicletasDisponibles: "free_bikes",
        VOCAB.anclajesLibres: "empty_slots",
        VOCAB.bicicletasMecanicas: "normal_bikes",
        VOCAB.bicicletasElectricas: "ebikes",
    }
    for s in dfs["citybikes_estado"].itertuples():
        u = uri_estado(s.id_estacion, s.captura_utc)
        estacion = uri_estacion(s.id_estacion)
        g.add((u, RDF.type, VOCAB.EstadoEstacion))
        g.add((u, SOSA.hasFeatureOfInterest, estacion))
        g.add((u, SOSA.resultTime, fecha_hora(s.captura_utc)))
        for propiedad, columna in columnas.items():
            valor = getattr(s, columna)
            if pd.notna(valor):
                g.add((u, propiedad, entero(valor)))
        g.add((u, VOCAB.enLinea, Literal(str(s.online).lower() == "true")))
    return g


# ---------------------------------------------------------------------------
# Fuente 2: Open-Meteo (CAMS)
# ---------------------------------------------------------------------------
CONTAMINANTES = {  # código -> (nombre, recurso DBpedia relacionado)
    "NO2": ("Dióxido de nitrógeno", DBR.Nitrogen_dioxide),
    "PM10": ("Material particulado PM10", DBR.Particulates),
    "PM2_5": ("Material particulado PM2.5", DBR.Particulates),
}


def generar_calidad_aire(dfs: dict[str, pd.DataFrame]) -> Graph:
    """Instancia Place (Barcelona), CeldaModelo, Contaminante y ObservacionCalidadAire."""
    g = nuevo_grafo()
    _, extraido = url_y_fecha(dfs["procedencia"], "openmeteo")
    ciudad = agregar_ciudad(g)

    for c in dfs["openmeteo_celdas"].itertuples():
        u = uri_celda(c.id_celda)
        g.add((u, RDF.type, VOCAB.CeldaModelo))
        g.add((u, SCHEMA.identifier, Literal(c.id_celda)))
        g.add((u, SCHEMA.name, Literal(f"Celda CAMS Barcelona {c.id_celda.removeprefix('celda_')}")))
        g.add((u, GEO.lat, decimal(c.latitud_celda)))
        g.add((u, GEO.long, decimal(c.longitud_celda)))
        if pd.notna(c.elevacion):
            g.add((u, SCHEMA.elevation, decimal(c.elevacion)))
        g.add((u, DCTERMS.source, Literal("Copernicus CAMS 0.1°")))
        g.add((u, SCHEMA.containedInPlace, ciudad))

    obs = dfs["openmeteo_observaciones"]
    unidades = obs.groupby("contaminante").unidad.first()
    for codigo in sorted(obs.contaminante.unique()):
        nombre, recurso = CONTAMINANTES.get(codigo, (codigo, None))
        u = uri_contaminante(codigo)
        g.add((u, RDF.type, VOCAB.Contaminante))
        g.add((u, SCHEMA.identifier, Literal(codigo)))
        g.add((u, SCHEMA.name, Literal(nombre, lang="es")))
        # La unidad es la misma para todas las observaciones de un contaminante.
        g.add((u, SCHEMA.unitText, Literal(unidades[codigo])))
        g.add((u, SCHEMA.unitCode, Literal("GQ")))  # UN/CEFACT: microgramo por metro cúbico
        if recurso:
            g.add((u, RDFS.seeAlso, recurso))

    for o in obs.dropna(subset=["valor"]).itertuples():
        u = uri_observacion(o.id_celda, o.hora_utc, o.contaminante)
        g.add((u, RDF.type, VOCAB.ObservacionCalidadAire))
        g.add((u, SOSA.hasFeatureOfInterest, uri_celda(o.id_celda)))
        g.add((u, VOCAB.mideContaminante, uri_contaminante(o.contaminante)))
        g.add((u, SOSA.resultTime, fecha_hora(o.hora_utc)))
        g.add((u, SOSA.hasSimpleResult, decimal(o.valor)))
        g.add((u, DCTERMS.issued, fecha_hora(extraido)))
    return g


# ---------------------------------------------------------------------------
# Validación contra el modelo
# ---------------------------------------------------------------------------
def validar(grafo: Graph, vocab: Graph) -> list[str]:
    """Comprueba la coherencia de los datos con vocab.ttl. Devuelve errores.

    1. Cada uso de una propiedad vocab: respeta su rdfs:domain y rdfs:range.
    2. Ningún nodo data: usado como objeto queda sin rdf:type (sin describir).
    3. Ningún sujeto queda sin rdf:type.
    """
    errores: list[str] = []
    datos = grafo + vocab
    for prop in vocab.subjects(RDF.type, RDF.Property):
        dominio = vocab.value(prop, RDFS.domain)
        rango = vocab.value(prop, RDFS.range)
        for s, o in grafo.subject_objects(prop):
            if dominio and (s, RDF.type, dominio) not in datos:
                errores.append(f"dominio: {s} {prop} (se esperaba {dominio})")
            if rango is None:
                continue
            if str(rango).startswith(str(XSD)):
                if not isinstance(o, Literal) or (o.datatype or XSD.string) != rango:
                    errores.append(f"rango: {s} {prop} {o!r} (se esperaba {rango})")
            elif (o, RDF.type, rango) not in datos:
                errores.append(f"rango: {s} {prop} {o} (se esperaba {rango})")
    for o in set(grafo.objects()):
        if isinstance(o, URIRef) and str(o).startswith(str(DATA)) and (o, RDF.type, None) not in datos:
            errores.append(f"nodo sin describir: {o}")
    for s in set(grafo.subjects()):
        if (s, RDF.type, None) not in grafo:
            errores.append(f"sujeto sin tipo: {s}")
    return errores


def nodos_por_clase(grafo: Graph) -> pd.DataFrame:
    """SPARQL: número de instancias por clase (la misma consulta se usa en GraphDB)."""
    consulta = """
        SELECT ?clase (COUNT(DISTINCT ?s) AS ?nodos)
        WHERE { ?s a ?clase . FILTER(STRSTARTS(STR(?s), STR(data:))) }
        GROUP BY ?clase ORDER BY DESC(?nodos) ?clase
    """
    filas = [(r.clase.n3(grafo.namespace_manager), int(r.nodos))
             for r in grafo.query(consulta, initNs={"data": DATA})]
    return pd.DataFrame(filas, columns=["Clase", "Nodos"])


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------
def ejecutar(limite: int = 0, guardar: bool = True) -> tuple[Graph, Graph]:
    dfs = cargar_csv(limite)
    g_bicing = generar_bicing(dfs)
    g_aire = generar_calidad_aire(dfs)
    vocab = Graph().parse(RUTA_VOCAB)
    errores = validar(g_bicing + g_aire, vocab)
    if errores:
        raise ValueError(f"{len(errores)} errores de coherencia, p. ej.: {errores[:5]}")
    if guardar:
        DIR_SALIDA.mkdir(parents=True, exist_ok=True)
        g_bicing.serialize(DIR_SALIDA / "bicing.ttl", format="turtle")
        g_aire.serialize(DIR_SALIDA / "calidad_aire.ttl", format="turtle")
        total = nuevo_grafo()
        total += g_bicing
        total += g_aire
        tabla = nodos_por_clase(total)
        lineas = ["| Clase | Nodos |", "|---|---:|"]
        lineas += [f"| `{c}` | {n} |" for c, n in tabla.itertuples(index=False)]
        lineas += ["", f"Total de tripletas (datos): {len(total)}"]
        (DIR_SALIDA / "estadisticas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return g_bicing, g_aire


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=0, help="procesar solo N filas (prueba)")
    args = parser.parse_args()
    gb, ga = ejecutar(args.limit, guardar=not args.limit)
    print(f"bicing.ttl: {len(gb)} tripletas | calidad_aire.ttl: {len(ga)} tripletas | 0 errores")
