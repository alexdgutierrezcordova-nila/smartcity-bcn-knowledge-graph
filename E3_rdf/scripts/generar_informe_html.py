"""Genera el informe del proyecto (HTML autocontenido y Word) SIN código.

El informe explica el proceso y los resultados de las tres fases:
fuentes, limpieza, preguntas de competencia, modelo, RDF, GraphDB y respuestas.
El código queda aparte (scripts/ y el notebook técnico).

Todo el contenido se arma una sola vez como una lista de bloques
(título, párrafo, tabla, imagen...) y se dibuja dos veces: en HTML y en .docx.
Las cifras se calculan desde los datos, no se escriben a mano.

Salidas:
    E3_rdf/informe/informe_proyecto.html
    E3_rdf/informe/Informe_proyecto.docx
    E3_rdf/informe/capturas/nodos_por_clase.png

Uso:
    uv run --no-project --with rdflib --with pandas --with matplotlib --with python-docx \
        python E3_rdf/scripts/generar_informe_html.py
"""

from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Inches, Pt, RGBColor  # noqa: E402
from rdflib import Graph, Literal  # noqa: E402

import generar_rdf as gen  # noqa: E402
import preprocesar  # noqa: E402

RAIZ = gen.RAIZ
DIR_E3 = RAIZ / "E3_rdf"
DIR_INFORME = DIR_E3 / "informe"
DIR_CAPTURAS = DIR_INFORME / "capturas"
DIR_MODELO = DIR_E3 / "modelo"
DIR_SPARQL = DIR_E3 / "sparql"
DIR_GRAPHDB = DIR_E3 / "graphdb"
DIR_RAW = RAIZ / "E2_extraccion" / "data" / "raw"
RUTA_E1 = RAIZ / "E1_correccion" / "E1_base_corregida.md"
HORA_H = "2026-11-12T17:00:00+00:00"


# ---------------------------------------------------------------------------
# Bloques de contenido
# ---------------------------------------------------------------------------
def h1(t): return ("h1", t)
def h2(t): return ("h2", t)
def h3(t): return ("h3", t)
def p(t): return ("p", t)
def ul(*items): return ("ul", list(items))
def nota(t): return ("nota", t)
def tabla(df: pd.DataFrame, pie: str = "") -> tuple: return ("tabla", df, pie)
def imagen(ruta: Path, pie: str) -> tuple: return ("img", ruta, pie)
def ejemplo(t: str, pie: str = "") -> tuple: return ("pre", t, pie)


# ---------------------------------------------------------------------------
# Datos de entrada
# ---------------------------------------------------------------------------
def leer_raw() -> tuple[dict, list]:
    cb = json.loads(next((DIR_RAW / "citybikes").glob("*.json")).read_text(encoding="utf-8"))
    om = json.loads(next((DIR_RAW / "openmeteo").glob("*.json")).read_text(encoding="utf-8"))
    return cb, om


def preguntas_e1() -> pd.DataFrame:
    """Lee la matriz PC1–PC15 del Entregable 1 y limpia la notación LaTeX."""
    filas = []
    for linea in RUTA_E1.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*\*\*(PC\d+)\*\*\s*\|(.+)", linea)
        if m:
            celdas = [c.strip() for c in m.group(2).strip().strip("|").split("|")]
            filas.append((m.group(1), limpiar_latex(celdas[0]), celdas[1], celdas[2].strip("*"),
                          limpiar_latex(celdas[3])))
    return pd.DataFrame(filas, columns=["PC", "Pregunta", "Fuentes", "Tipo", "Para quién / decisión"])


def limpiar_latex(t: str) -> str:
    t = re.sub(r"\\,?\\mu\\text\{g/m\}\^3", " µg/m³", t)
    t = t.replace("\\text{ en 24h}", " en 24 h")
    t = re.sub(r"NO_2", "NO₂", t)
    t = re.sub(r"PM_\{?(2\.5|10)\}?", r"PM\1", t)
    t = t.replace("\\le", "≤").replace("\\ge", "≥")
    return t.replace("$", "").replace("\\,", " ").replace("  ", " ")


def ejecutar_pc(grafo: Graph) -> dict[str, pd.DataFrame]:
    """Ejecuta pc01..pc15 con rdflib y comprueba que GraphDB devolvió lo mismo."""
    resultados = {}
    for ruta in sorted(DIR_SPARQL.glob("pc*.rq")):
        res = grafo.query(ruta.read_text(encoding="utf-8"))
        filas = [[v.toPython() if isinstance(v, Literal) else str(v) for v in fila] for fila in res]
        df = pd.DataFrame(filas, columns=[str(v) for v in res.vars])
        json_gdb = DIR_GRAPHDB / f"{ruta.stem}.json"
        if json_gdb.exists():
            n_gdb = len(json.loads(json_gdb.read_text(encoding="utf-8")))
            if n_gdb != len(df):
                raise ValueError(f"{ruta.stem}: rdflib {len(df)} filas, GraphDB {n_gdb}")
        resultados[ruta.stem.upper().replace("PC0", "PC")] = df
    return resultados


def grafico_nodos(tabla_nodos: pd.DataFrame) -> Path:
    t = tabla_nodos.sort_values("Nodos")
    fig, ax = plt.subplots(figsize=(8, 3.6))
    barras = ax.barh(t["Clase"], t["Nodos"], color="#2f5f98")
    ax.bar_label(barras, padding=3)
    ax.set_xlabel("Número de nodos (instancias)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    DIR_CAPTURAS.mkdir(parents=True, exist_ok=True)
    ruta = DIR_CAPTURAS / "nodos_por_clase.png"
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    return ruta


def ejemplo_turtle(g: Graph, estacion_id: str, celda: str) -> str:
    """Turtle de una estación, su estado, su celda y una observación de la hora H."""
    sub = gen.nuevo_grafo()
    e = gen.uri_estacion(estacion_id)
    nodos = [e, gen.uri_celda(celda)]
    nodos += list(g.subjects(gen.SOSA.hasFeatureOfInterest, e))
    nodos.append(gen.uri_observacion(celda, HORA_H, "NO2"))
    for n in nodos:
        for t in g.triples((n, None, None)):
            sub.add(t)
    texto = sub.serialize(format="turtle")
    return "\n".join(ln for ln in texto.splitlines() if not ln.startswith("@prefix")).strip()


# ---------------------------------------------------------------------------
# Contenido del informe
# ---------------------------------------------------------------------------
def construir() -> list[tuple]:
    cb, om = leer_raw()
    red = cb["payload"]["network"]
    estaciones_raw = red["stations"]
    dfs = gen.cargar_csv()
    pre = preprocesar.ejecutar(guardar=False)
    estado, celdas, obs = dfs["citybikes_estado"], pre["celdas_cams"], pre["observaciones_cams"]
    enlace = pre["enlace_estacion_celda"]

    gb, ga = gen.ejecutar(guardar=False)
    vocab = Graph().parse(gen.RUTA_VOCAB)
    total = gen.nuevo_grafo()
    total += gb
    total += ga
    nodos = gen.nodos_por_clase(total)
    pcs = ejecutar_pc(total + vocab)
    pc_e1 = preguntas_e1()
    vocab_reuso = pd.read_csv(DIR_MODELO / "vocabularios_reutilizados.csv")
    mapeo = pd.read_csv(DIR_MODELO / "mapeo_campos.csv")
    tripletas_gdb = json.loads((DIR_GRAPHDB / "02_total_tripletas.json").read_text(encoding="utf-8"))[0]
    enlace_gdb = json.loads((DIR_GRAPHDB / "05_enlace_fuentes.json").read_text(encoding="utf-8"))[0]
    dominio_cams = "domains=" + (om["url"].split("domains=")[1].split("&")[0] if "domains=" in om["url"]
                                 else "auto (no se envía, valor por defecto)")

    nombres_sucios = [s["name"] for s in estaciones_raw if re.sub(r"\s+", " ", s["name"]).strip() != s["name"]]
    puntos_om = len(om["payload"])
    horas = len(om["payload"][0]["hourly"]["time"])
    valores_raw = puntos_om * horas * 3
    incidencias = pd.read_csv(gen.DIR_PROCESADOS / "incidencias_calidad.csv")
    sin_obs = celdas[celdas.puntos_muestreo == 0].id_celda.tolist()
    est_sin_obs = int(enlace.id_celda.isin(sin_obs).sum())
    no2_h = obs[(obs.contaminante == "NO2") & (obs.hora_utc == HORA_H)]
    pm25_h = obs[(obs.contaminante == "PM2_5") & (obs.hora_utc == HORA_H)]
    pm10_dia = obs[(obs.contaminante == "PM10") & obs.hora_utc.str.startswith("2026-11-12")] \
        .groupby("id_celda").valor.mean()

    b: list[tuple] = []
    b += [h1("Grafo de conocimiento Smart City Barcelona: movilidad y calidad del aire"),
          p("**Universidad Técnica Particular de Loja (UTPL)** · Interoperabilidad y Explotación de Datos "
            "en Ecosistemas Heterogéneos · Docente: Dra. Janneth Alexandra Chicaiza Espinosa · "
            "Integrantes: Alex Gutiérrez, David Manotoa · Noviembre de 2026")]

    # 1. Resumen
    b += [h2("1. Resumen"),
          p("Barcelona publica por separado el estado de su red de bicicletas (Bicing) y la contaminación del aire. "
            "Un ciclista que pedalea por una zona con mucho NO₂ o partículas respira más contaminantes, pero no hay "
            "un lugar donde cruzar ambos datos. Este proyecto los integra en un **grafo de conocimiento RDF** que "
            "responde preguntas como *«¿qué estaciones tienen bicicletas y están en una zona con aire limpio?»*."),
          tabla(pd.DataFrame([
              ["Fuentes integradas", "2 APIs abiertas: CityBikes (Bicing) y Open-Meteo (Copernicus CAMS)"],
              ["Estaciones de bicicletas", f"{len(dfs['citybikes_estaciones'])}"],
              ["Observaciones de calidad del aire", f"{len(obs)} (NO₂, PM10 y PM2.5, {horas} horas)"],
              ["Celdas CAMS (nodo puente)", f"{len(celdas)}"],
              ["Tripletas RDF", f"{len(total):,}".replace(",", " ")],
              ["Preguntas de competencia respondidas con SPARQL", "15 de 15"],
              ["Almacenamiento", "GraphDB 10.8.5, repositorio bcn-kg"],
          ], columns=["Indicador", "Valor"]))]

    # 2. Fase 1
    b += [h2("2. Fase 1 · Preguntas de competencia y fuentes"),
          p("Las fuentes y los campos se eligieron a partir de las preguntas que el grafo debe responder. "
            "PC1–PC5 usan solo Bicing, PC6–PC10 solo calidad del aire y **PC11–PC15 necesitan ambas fuentes**: "
            "son las que justifican la integración."),
          tabla(pc_e1[["PC", "Pregunta", "Fuentes", "Tipo"]], "Preguntas de competencia (Entregable 1)."),
          h3("2.1 Fuente 1 · CityBikes (red Bicing)"),
          tabla(pd.DataFrame([
              ["Origen", "API REST abierta de CityBikes, que publica el estado de la red Bicing de Barcelona"],
              ["Acceso", f"GET {red.get('href') and 'https://api.citybik.es' + red['href']}"],
              ["Formato / licencia", "JSON · ODbL / CC BY 4.0"],
              ["Registros obtenidos", f"{len(estaciones_raw)} estaciones en una captura ({cb['extraido_utc'][:16]} UTC)"],
              ["Campos elegidos", "id, name, latitude, longitude, timestamp, free_bikes, empty_slots, "
                                  "extra.normal_bikes, extra.ebikes, extra.online, extra.uid; company (operadores)"],
              ["Campos descartados", "extra.has_ebikes (se deduce de ebikes > 0); ebikes y location de la red "
                                     "(no los usa ninguna pregunta)"],
          ], columns=["Aspecto", "Detalle"])),
          h3("2.2 Fuente 2 · Open-Meteo Air Quality (Copernicus CAMS)"),
          tabla(pd.DataFrame([
              ["Origen", "API REST abierta de Open-Meteo que sirve el modelo europeo de calidad del aire CAMS"],
              ["Acceso", f"GET air-quality-api.open-meteo.com/v1/air-quality con {puntos_om} puntos de Barcelona, "
                         "variables nitrogen_dioxide, pm10, pm2_5, ayer y hoy (48 h)"],
              ["Formato / licencia", "JSON · CC BY 4.0"],
              ["Registros obtenidos", f"{puntos_om} puntos × {horas} horas × 3 contaminantes = {valores_raw} valores"],
              ["Campos elegidos", "latitude, longitude, elevation, hourly.time, hourly.nitrogen_dioxide, "
                                  "hourly.pm10, hourly.pm2_5, hourly_units"],
              ["Campos descartados", "generationtime_ms, utc_offset_seconds, timezone, timezone_abbreviation "
                                     "(metadatos técnicos de la respuesta)"],
          ], columns=["Aspecto", "Detalle"])),
          p("Ambas respuestas crudas se guardaron sin modificar, junto con su procedencia (URL, fecha de extracción "
            "y código HTTP), para poder rastrear cada dato hasta su origen.")]

    # 3. Fase 2
    ts_raw = estaciones_raw[0]["timestamp"]
    peticion = preprocesar.puntos_solicitados(om["url"])[0]
    respuesta = om["payload"][0]
    b += [h2("3. Fase 2 · Limpieza y modelo de datos"),
          h3("3.1 Qué se limpió y por qué"),
          tabla(pd.DataFrame([
              ["Nombres de estación con espacios de más", f"`«{nombres_sucios[0]}»`",
               f"`«{re.sub(chr(92) + 's+', ' ', nombres_sucios[0]).strip()}»`",
               f"{len(nombres_sucios)} nombres normalizados"],
              ["Hora con formato inválido (+00:00 y Z a la vez)", ts_raw, estado.captura_utc.iloc[0],
               "Todas las horas en UTC ISO 8601"],
              ["Hora de Open-Meteo sin zona horaria", respuesta["hourly"]["time"][0], obs.hora_utc.iloc[0],
               "Se fija UTC (la consulta pidió GMT)"],
              ["Series en vectores paralelos", "hourly.time[], hourly.pm10[] …",
               "1 fila = celda + hora + contaminante + valor", "Formato apto para convertir a RDF"],
              ["Coordenada redondeada de Open-Meteo", f"pedido ({peticion[0]}, {peticion[1]}) → "
               f"respuesta ({respuesta['latitude']}, {respuesta['longitude']:.1f})",
               preprocesar.celda_de(*peticion)[0], "Ver 3.2"],
              ["Bicicletas que no suman", "mecánicas + eléctricas ≠ disponibles",
               "se conservan y se registran", f"{len(incidencias)} incidencias documentadas"],
          ], columns=["Problema", "Antes", "Después", "Resultado"]), "Ejemplos reales tomados de los datos."),
          tabla(pd.DataFrame([
              ["CityBikes · estaciones", len(estaciones_raw), len(dfs["citybikes_estaciones"])],
              ["CityBikes · estados (inventario)", len(estaciones_raw), len(estado)],
              ["Open-Meteo · valores horarios", valores_raw, len(obs)],
          ], columns=["Conjunto", "Filas extraídas", "Filas limpias"]),
              f"Open-Meteo baja de {valores_raw} a {len(obs)} porque varios puntos caen en la misma celda y traen "
              "exactamente la misma serie (se verifica antes de unirlos)."),
          h3("3.2 Corrección de las celdas CAMS"),
          p("Open-Meteo devuelve una coordenada redondeada (41.4, 2.2) que **no identifica la celda real**. "
            "En el Entregable 2 se usó esa coordenada como identificador y se mezclaron celdas distintas. "
            "La rejilla CAMS es de 0.1°, así que cada punto pertenece a la celda "
            "`floor(coordenada × 10) / 10`; se comprobó que todos los puntos de una misma celda traen la misma serie."),
          tabla(celdas.merge(enlace.groupby("id_celda").size().rename("Estaciones"), on="id_celda", how="left")
                .assign(Observaciones=lambda d: d.puntos_muestreo.gt(0).map({True: "Sí", False: "No"}))
                [["id_celda", "puntos_muestreo", "Estaciones", "Observaciones"]]
                .rename(columns={"id_celda": "Celda", "puntos_muestreo": "Puntos consultados"})),
          h3("3.3 Modelo de datos"),
          nota("**Idea central:** todo dato medido es una observación (`sosa:Observation`) sobre algo. "
               "El estado de inventario observa una **estación**; la medición de aire observa una **celda CAMS**. "
               "Como cada estación está **contenida en** una celda, la celda une las dos fuentes."),
          imagen(DIR_MODELO / "modelo_datos.png", "Modelo de datos v2. El color indica la fuente de cada clase."),
          p("Frente al modelo tentativo del Entregable 2 se simplificó: se quitó `vocab:tieneEstado` "
            "(duplicaba `sosa:hasFeatureOfInterest`), el nodo `schema:QuantitativeValue` (432 nodos que repetían el "
            "valor; la unidad se declara una vez en el contaminante) y `schema:address` en las estaciones "
            "(la fuente no la trae). Se añadieron enlaces a DBpedia para Barcelona, Bicing y los contaminantes."),
          h3("3.4 Vocabularios reutilizados"),
          p("Antes de crear un término propio se buscó en schema.org, SOSA (W3C), WGS84, Dublin Core y DBpedia. "
            "Solo se crearon términos `vocab:` cuando no había uno adecuado."),
          tabla(vocab_reuso.rename(columns={"concepto": "Concepto", "termino_usado": "Término usado",
                                            "vocabulario": "Vocabulario", "alternativas_revisadas": "Alternativas revisadas",
                                            "justificacion": "Por qué"})),
          h3("3.5 De cada campo a cada pregunta"),
          tabla(mapeo[["fuente", "campo_origen", "termino", "preguntas", "uso"]].rename(columns={
              "fuente": "Fuente", "campo_origen": "Campo de origen", "termino": "Término en el grafo",
              "preguntas": "Preguntas", "uso": "Para qué sirve"})),
          h3("3.6 Correcciones tras la revisión con la docente"),
          p("En la revisión del modelo la docente hizo observaciones; cada una se comprobó contra los datos y el "
            "código antes de cambiar algo:"),
          tabla(pd.DataFrame([
              ["Todo debe estar en un solo grafo, con URIs comunes, para que los datos se conecten",
               "Modelo y ambas fuentes se cargan en **un único grafo** (`graph/bcn-kg`) con una sola URI base "
               "(`data:`); antes eran tres grafos con nombre",
               f"Consulta de enlace en GraphDB: las **{enlace_gdb['estaciones_en_celda']} de "
               f"{len(dfs['citybikes_estaciones'])} estaciones** apuntan a una celda descrita por la fuente CAMS; "
               f"{enlace_gdb['estaciones_con_datos_aire']} tienen datos de aire (las demás están en "
               "`celda_41.45_2.25`, sin punto de consulta en Open-Meteo)"],
              ["Las URIs generadas por script podrían no coincidir entre archivos",
               "Las dos fuentes construyen la URI de la celda con la **misma función** a partir de la misma "
               "regla de rejilla (`data:celda_<lat>_<lon>`)",
               "Prueba automática: todas las celdas usadas por Bicing existen en calidad del aire"],
              ["¿Dónde está el centroide? Usar la misma nomenclatura que el modelo",
               "`distanciaACentroideKm` pasa a `vocab:distanciaACeldaModeloKm`. El centroide **es** la CeldaModelo: "
               "sus `geo:lat`/`geo:long` son el punto central de la cuadrícula",
               "Ningún término del modelo nombra un concepto que no esté en el diagrama"],
              ["Fuente del modelo atmosférico (CAMS europeo, global o auto): modelarla solo si varía",
               "No se modela por observación. Queda como un solo dato de procedencia en cada celda: "
               "«Copernicus CAMS European»",
               f"La consulta usó {dominio_cams}; la rejilla de 0.1° (~11 km) corresponde a CAMS European "
               "(CAMS Global es de ~45 km). Es **constante** en las 4 celdas y las "
               f"{len(obs)} observaciones"],
              ["Lo que cambia en el tiempo (bicicletas disponibles) debe ser una Observation",
               "Ya en el modelo v2: `EstadoEstacion` es `sosa:Observation` sobre la estación, que conserva su "
               "identidad", "Cada estado tiene `sosa:hasFeatureOfInterest` y `sosa:resultTime`"],
              ["Reutilizar Observation en vez de clases propias aisladas",
               "Las dos mediciones (inventario y aire) son subclases de `sosa:Observation`",
               "GraphDB infiere `sosa:Observation` para estados y observaciones de aire"],
          ], columns=["Observación de la docente", "Qué se hizo", "Evidencia"]))]

    # 4. Fase 3
    estacion_ej = enlace[enlace.id_celda == "celda_41.35_2.15"].id_estacion.iloc[0]
    b += [h2("4. Fase 3 · Datos RDF y GraphDB"),
          h3("4.1 Identificación de entidades (URIs)"),
          p("Las dos fuentes usan **la misma URI base** `http://example.org/bcn-kg/data/` y **la misma regla** para "
            "formar el nombre: se quitan tildes y espacios. Las estaciones usan el identificador de CityBikes y no "
            "el nombre, porque hay nombres de calle repetidos."),
          tabla(pd.DataFrame([
              ["Red", "data:red_bicing"], ["Operador", f"data:{gen.uri_operador('CESPA').split('/')[-1]}"],
              ["Estación", "data:estacion_<id CityBikes>"], ["Estado", "data:estado_<id>_<fecha>"],
              ["Celda (nodo puente)", "data:celda_<lat>_<lon>"], ["Contaminante", "data:contaminante_<código>"],
              ["Observación", "data:obs_<celda>_<hora>_<código>"], ["Ciudad", "data:Barcelona"],
          ], columns=["Entidad", "Patrón de URI"])),
          h3("4.2 Ejemplo de los datos generados"),
          p("Una estación, su estado, la celda que la contiene y la observación de NO₂ de esa celda a las "
            "17:00 UTC (formato Turtle):"),
          ejemplo(ejemplo_turtle(total, estacion_ej, "celda_41.35_2.15")),
          h3("4.3 Validación y totales"),
          p(f"Primero se probó con 2 filas por fuente y luego con todos los datos. Cada propiedad se valida contra "
            f"el dominio y rango del modelo: **0 errores**. Se generaron dos archivos: `bicing.ttl` "
            f"({len(gb):,} tripletas) y `calidad_aire.ttl` ({len(ga):,} tripletas).".replace(",", " ")),
          tabla(nodos, "Nodos por clase en el grafo generado."),
          imagen(grafico_nodos(nodos), "Nodos por clase."),
          h3("4.4 Almacenamiento en GraphDB"),
          p(f"Se creó el repositorio `bcn-kg` en GraphDB 10.8.5 con razonamiento RDFS y se cargó cada archivo en "
            f"**un único grafo** (`graph/bcn-kg`): vocabulario, Bicing y calidad del aire juntos, para que las "
            f"estaciones y las celdas queden conectadas. El repositorio tiene "
            f"**{int(tripletas_gdb['tripletas']):,} tripletas** (datos + vocabulario).".replace(",", " ")),
          imagen(DIR_CAPTURAS / "graphdb_importacion.png", "Un solo grafo en GraphDB con el modelo y las dos fuentes."),
          imagen(DIR_CAPTURAS / "graphdb_nodos_por_clase.png",
                 "Nodos por clase en GraphDB. Además de las clases propias aparecen sus superclases "
                 "inferidas (p. ej., sosa:Observation = estados + observaciones de aire)."),
          imagen(DIR_CAPTURAS / "graphdb_grafo.png", "Una estación en el grafo: su red, su estado y su celda CAMS."),
          imagen(DIR_CAPTURAS / "graphdb_grafo_enlace.png",
                 "Celda CAMS expandida: las estaciones de Bicing enlazadas al nodo puente.")]

    # 5. Respuestas
    def top(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
        nombres = {"nombre": "Estación", "bicicletas": "Bicicletas", "celda": "Celda", "no2": "NO₂ (µg/m³)",
                   "estaciones": "Estaciones", "electricas": "Eléctricas", "capacidad": "Capacidad"}
        return df.drop(columns=[c for c in ("estacion",) if c in df.columns]).head(n).rename(columns=nombres)

    r = pcs
    respuestas = {
        "PC1": f"**{len(r['PC1'])} estaciones** tienen más de 10 bicicletas disponibles.",
        "PC2": f"**{len(r['PC2'])} estaciones** están llenas (0 anclajes libres).",
        "PC3": f"**{len(r['PC3'])} estaciones** están a menos de 1 km de Plaza Cataluña.",
        "PC4": f"**{len(r['PC4'])} estaciones** tienen al menos una bicicleta eléctrica.",
        "PC5": "Las 10 estaciones con más capacidad observada (bicicletas + anclajes libres).",
        "PC6": f"A las 17:00 UTC el NO₂ en la celda de Plaza Cataluña fue **{r['PC6'].no2.iloc[0]} µg/m³**.",
        "PC7": f"**Ninguna celda** superó 45 µg/m³ de PM10 diario; el máximo fue {r['PC7'].pm10_medio.max()} µg/m³.",
        "PC8": f"**Ninguna celda** superó 25 µg/m³ de PM2.5 horario; el máximo fue {r['PC8'].pm25_max.max()} µg/m³.",
        "PC9": "Mínimo, máximo y amplitud de NO₂ de cada celda en las 48 horas.",
        "PC10": "Razón media PM2.5/PM10 por celda; valores cercanos a 0.7 indican partículas de combustión.",
        "PC11": f"**{len(r['PC11'])} estaciones** tienen 5 o más bicicletas y aire con NO₂ ≤ 25 µg/m³ a las 17:00 UTC.",
        "PC12": f"**Ninguna**: la media diaria de PM10 más alta del 12/11 fue {pm10_dia.max():.1f} µg/m³ (límite UE: 50).",
        "PC13": f"**Ninguna**: el PM2.5 más alto a las 17:00 UTC fue {pm25_h.valor.max()} µg/m³ (umbral: 15).",
        "PC14": f"La celda con más NO₂ a las 17:00 UTC fue `{r['PC14'].celda.iloc[0]}` "
                f"({r['PC14'].no2.iloc[0]} µg/m³) y contiene **{r['PC14'].estaciones.iloc[0]} estaciones**.",
        "PC15": f"**Ninguna**: el NO₂ más alto a las 17:00 UTC fue {no2_h.valor.max()} µg/m³ (umbral: 40).",
    }
    b += [h2("5. Respuestas a las preguntas de competencia"),
          p("Cada pregunta tiene su consulta SPARQL en `E3_rdf/sparql/pcNN.rq`. Se ejecutaron en GraphDB y dieron "
            "los mismos resultados que localmente. Las preguntas integradas cruzan la hora de captura de Bicing "
            "(16:30 UTC) con la hora CAMS más cercana (**H = 17:00 UTC**, ±30 min)."),
          tabla(pd.DataFrame([(pc, pc_e1.set_index("PC").Tipo.get(pc, ""), len(df), respuestas[pc])
                              for pc, df in r.items()], columns=["PC", "Tipo", "Filas", "Respuesta"]),
                "Resumen de respuestas. Una respuesta «ninguna» también es un resultado: el umbral no se superó.")]
    for pc in ("PC1", "PC6", "PC11", "PC14"):
        b += [h3(f"{pc} · {pc_e1.set_index('PC').Pregunta[pc]}"), p(respuestas[pc]), tabla(top(r[pc]))]

    # 6. Conclusiones
    b += [h2("6. Conclusiones y limitaciones"),
          ul("Las dos fuentes quedaron integradas en un grafo RDF con una URI base común; la celda CAMS es el "
             "puente que permite responder las preguntas integradas PC11–PC15.",
             "El modelo reutiliza schema.org, SOSA, WGS84 y Dublin Core, y enlaza con DBpedia; solo los conteos de "
             "bicicletas y las relaciones del dominio son términos propios.",
             "Los datos se validan contra el modelo (0 errores) y las 15 preguntas tienen pruebas automáticas.",
             f"**Limitación:** la celda {', '.join(sin_obs)} ({est_sin_obs} estaciones) no tiene observaciones "
             "porque ningún punto consultado cayó en ella; esas estaciones no aparecen en las preguntas integradas.",
             "**Limitación:** hay una sola captura de Bicing; las 48 horas de CAMS incluyen horas de pronóstico "
             "posteriores a la captura.",
             "**Limitación:** la resolución CAMS (0.1°, unos 11 × 8 km) da un valor por zona, no por calle."),
          h2("Anexo · Dónde está el código"),
          tabla(pd.DataFrame([
              ["Notebook técnico con código y salidas", "E3_rdf/notebooks/E3_generacion_rdf.html"],
              ["Modelo (vocabulario, diagrama, mapeo)", "E3_rdf/modelo/"],
              ["Datos RDF", "E3_rdf/rdf/bicing.ttl, E3_rdf/rdf/calidad_aire.ttl"],
              ["Consultas SPARQL (PC1–PC15)", "E3_rdf/sparql/"],
              ["Scripts de conversión y carga", "E3_rdf/scripts/"],
              ["Extracción y limpieza (Fase 2)", "E2_extraccion/"],
          ], columns=["Qué", "Dónde"])),
          p("Declaración de uso de IA: se usó Claude Code (Anthropic) como asistente en la revisión, los scripts y "
            "la redacción. Todo se verificó ejecutando las pruebas, revisando las muestras de 2 filas y comparando "
            "los totales con GraphDB.")]
    return b


# ---------------------------------------------------------------------------
# Render HTML
# ---------------------------------------------------------------------------
CSS = """
:root{--tinta:#1f2933;--suave:#52606d;--linea:#d9e2ec;--azul:#2f5f98;--fondo:#f7f9fb;--nota:#fff6e0}
*{box-sizing:border-box}body{margin:0;background:var(--fondo);color:var(--tinta);
font:16px/1.6 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1040px;margin:0 auto;padding:40px 24px 80px;background:#fff;box-shadow:0 0 0 1px var(--linea)}
h1{font-size:2rem;line-height:1.2;margin:0 0 8px}h2{font-size:1.45rem;margin:48px 0 12px;padding-bottom:6px;
border-bottom:3px solid var(--azul)}h3{font-size:1.12rem;margin:28px 0 8px;color:var(--azul)}
p{margin:10px 0}code{font:0.88em ui-monospace,Menlo,Consolas,monospace;background:#eef2f6;padding:1px 5px;border-radius:4px}
.tabla{overflow-x:auto;margin:14px 0}table{border-collapse:collapse;width:100%;font-size:.9rem}
th{background:var(--azul);color:#fff;text-align:left;padding:7px 10px}td code{white-space:pre}td{padding:6px 10px;border-bottom:1px solid var(--linea);vertical-align:top}
tr:nth-child(even) td{background:#f5f8fb}.pie{font-size:.85rem;color:var(--suave);font-style:italic;margin-top:4px}
figure{margin:20px 0;text-align:center}figure img{max-width:100%;border:1px solid var(--linea);border-radius:6px}
.nota{background:var(--nota);border-left:5px solid #b7791f;padding:12px 16px;border-radius:4px;margin:16px 0}
pre{background:#1f2933;color:#e4e7eb;padding:14px 16px;border-radius:6px;overflow-x:auto;font-size:.8rem;line-height:1.45}
nav{background:var(--fondo);border:1px solid var(--linea);border-radius:6px;padding:10px 18px;margin:20px 0}
nav a{color:var(--azul);text-decoration:none;margin-right:14px;white-space:nowrap}
@media print{main{box-shadow:none}h2{break-after:avoid}figure,table{break-inside:avoid}}
"""


def en_linea(t: str) -> str:
    t = html.escape(str(t))
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)


def html_tabla(df: pd.DataFrame) -> str:
    cab = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    filas = "".join("<tr>" + "".join(f"<td>{en_linea(v)}</td>" for v in fila) + "</tr>"
                    for fila in df.astype(str).itertuples(index=False))
    return f'<div class="tabla"><table><thead><tr>{cab}</tr></thead><tbody>{filas}</tbody></table></div>'


def render_html(bloques: list[tuple]) -> str:
    cuerpo, indice = [], []
    for b in bloques:
        tipo = b[0]
        if tipo == "h1":
            cuerpo.append(f"<h1>{en_linea(b[1])}</h1>")
        elif tipo == "h2":
            ancla = f"s{len(indice) + 1}"
            indice.append(f'<a href="#{ancla}">{html.escape(b[1])}</a>')
            cuerpo.append(f'<h2 id="{ancla}">{en_linea(b[1])}</h2>')
        elif tipo == "h3":
            cuerpo.append(f"<h3>{en_linea(b[1])}</h3>")
        elif tipo == "p":
            cuerpo.append(f"<p>{en_linea(b[1])}</p>")
        elif tipo == "nota":
            cuerpo.append(f'<div class="nota">{en_linea(b[1])}</div>')
        elif tipo == "ul":
            cuerpo.append("<ul>" + "".join(f"<li>{en_linea(i)}</li>" for i in b[1]) + "</ul>")
        elif tipo == "tabla":
            cuerpo.append(html_tabla(b[1]) + (f'<div class="pie">{en_linea(b[2])}</div>' if b[2] else ""))
        elif tipo == "img":
            ruta, pie = b[1], b[2]
            if ruta.exists():
                datos = base64.b64encode(ruta.read_bytes()).decode()
                cuerpo.append(f'<figure><img alt="{html.escape(pie)}" src="data:image/png;base64,{datos}">'
                              f'<figcaption class="pie">{en_linea(pie)}</figcaption></figure>')
            else:
                cuerpo.append(f'<p class="pie">[Falta la imagen {ruta.name}]</p>')
        elif tipo == "pre":
            cuerpo.append(f"<pre>{html.escape(b[1])}</pre>")
    nav = f'<nav><strong>Contenido:</strong> {" ".join(indice)}</nav>'
    cuerpo.insert(2, nav)
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Informe · Grafo de conocimiento Smart City Barcelona</title>'
            f"<style>{CSS}</style></head><body><main>{''.join(cuerpo)}</main></body></html>")


# ---------------------------------------------------------------------------
# Render Word
# ---------------------------------------------------------------------------
def docx_texto(parrafo, texto: str) -> None:
    for parte in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", str(texto)):
        if parte.startswith("**") and parte.endswith("**"):
            parrafo.add_run(parte[2:-2]).bold = True
        elif parte.startswith("`") and parte.endswith("`"):
            run = parrafo.add_run(parte[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif parte:
            parrafo.add_run(parte.replace("*", ""))


def render_docx(bloques: list[tuple], ruta: Path) -> None:
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for b in bloques:
        tipo = b[0]
        if tipo in ("h1", "h2", "h3"):
            doc.add_heading(b[1], level={"h1": 0, "h2": 1, "h3": 2}[tipo])
        elif tipo in ("p", "nota"):
            docx_texto(doc.add_paragraph(), b[1])
        elif tipo == "ul":
            for item in b[1]:
                docx_texto(doc.add_paragraph(style="List Bullet"), item)
        elif tipo == "tabla":
            df = b[1].astype(str)
            t = doc.add_table(rows=len(df) + 1, cols=len(df.columns))
            t.style = "Light Grid Accent 1"
            for j, c in enumerate(df.columns):
                t.cell(0, j).text = str(c)
            for i, fila in enumerate(df.itertuples(index=False), start=1):
                for j, v in enumerate(fila):
                    t.cell(i, j).text = ""
                    docx_texto(t.cell(i, j).paragraphs[0], v)
            for fila in t.rows:
                for celda in fila.cells:
                    for run in celda.paragraphs[0].runs:
                        run.font.size = Pt(8.5)
            if b[2]:
                pie = doc.add_paragraph(b[2].replace("*", ""))
                pie.runs[0].italic = True
                pie.runs[0].font.size = Pt(9)
        elif tipo == "img":
            if b[1].exists():
                doc.add_picture(str(b[1]), width=Inches(6.3))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                run = doc.add_paragraph().add_run(f"[Falta la imagen {b[1].name}]")
                run.font.color.rgb = RGBColor(0xC0, 0, 0)
            pie = doc.add_paragraph(b[2])
            pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pie.runs[0].italic = True
            pie.runs[0].font.size = Pt(9)
        elif tipo == "pre":
            par = doc.add_paragraph()
            run = par.add_run(b[1])
            run.font.name = "Consolas"
            run.font.size = Pt(7.5)
    doc.save(ruta)


if __name__ == "__main__":
    bloques = construir()
    DIR_INFORME.mkdir(parents=True, exist_ok=True)
    (DIR_INFORME / "informe_proyecto.html").write_text(render_html(bloques), encoding="utf-8")
    render_docx(bloques, DIR_INFORME / "Informe_proyecto.docx")
    faltan = [b[1].name for b in bloques if b[0] == "img" and not b[1].exists()]
    print("Informe generado: E3_rdf/informe/informe_proyecto.html y Informe_proyecto.docx")
    for f in faltan:
        print("  Falta imagen:", f)
