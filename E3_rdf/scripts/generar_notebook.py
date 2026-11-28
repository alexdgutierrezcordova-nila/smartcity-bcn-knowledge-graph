"""Construye, ejecuta y exporta a HTML el notebook del Entregable 3.

Uso:
    uv run --no-project --with rdflib --with pandas --with matplotlib \
        --with nbformat --with nbclient --with nbconvert --with ipykernel \
        python E3_rdf/scripts/generar_notebook.py
"""

from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

DIR_E3 = Path(__file__).resolve().parents[1]
DIR_NB = DIR_E3 / "notebooks"
NOMBRE = "E3_generacion_rdf"


def md(texto: str):
    return nbformat.v4.new_markdown_cell(texto.strip())


def code(texto: str):
    return nbformat.v4.new_code_cell(texto.strip())


CELDAS = [
    md("""
# UNIVERSIDAD TÉCNICA PARTICULAR DE LOJA (UTPL)
## Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos
**Docente:** Dra. Janneth Alexandra Chicaiza Espinosa
**Integrantes:** Alex Gutiérrez, David Manotoa
**Fecha:** 27 de noviembre de 2026 (versión final)

---
# Entregable 3: Generación de datos RDF
**Dominio:** Smart City Barcelona — movilidad (CityBikes / Bicing), calidad del aire (Open-Meteo / CAMS)
y barrios y distritos (Open Data BCN).
"""),
    md("""
## 1. Objetivo y flujo de trabajo

Convertir los datos extraídos y limpiados a **RDF (Turtle)**, siguiendo el modelo **v3**
(`E3_rdf/modelo/vocab.ttl` y `modelo_datos.png`), almacenarlos en **un solo grafo** de **GraphDB**, comprobar la
integración entre movilidad y calidad del aire y responder las 15 preguntas de competencia con SPARQL. El informe sin código está en `E3_rdf/informe/informe_proyecto.html`.

| Paso | Qué se hace | Código |
|---|---|---|
| 1 | Configuración y prefijos del modelo | `generar_rdf.PREFIJOS` |
| 2 | Revisión de los datos de entrada (nulos, duplicados) | `pandas` |
| 3 | Preprocesamiento: celdas CAMS y barrios de cada estación | `preprocesar.py` |
| 4 | Esquema de identificación de URIs | `normalizar`, `uri_*` |
| 5 | Prueba con 2 filas | `ejecutar(limite=2)` |
| 6 | Generación Fuente 1 (Bicing), Fuente 2 (CAMS) y Fuente 3 (barrios) | `generar_bicing`, `generar_calidad_aire`, `generar_barrios` |
| 7 | Validación contra el modelo | `validar` |
| 8 | Serialización y totales por clase | `serialize`, SPARQL |
| 9 | Integración movilidad + calidad del aire | `sparql/05`, `06`, `07` |
| 10 | Almacenamiento en GraphDB | `cargar_graphdb.py` (API REST) |
| 11 | Preguntas de competencia PC1–PC15 | `sparql/pcNN.rq` |

Toda la lógica está en `E3_rdf/scripts/` (funciones documentadas y probadas con `pytest`);
el notebook la ejecuta paso a paso y muestra el resultado de cada bloque.
"""),
    md("## 2. Configuración del entorno"),
    code("""
import sys, inspect
from pathlib import Path
from IPython.display import Markdown, display

DIR_E3 = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(DIR_E3 / 'scripts'))

import pandas as pd
import rdflib
import matplotlib.pyplot as plt
import preprocesar
import generar_rdf as gen
import cargar_graphdb

def ver_codigo(funcion):
    \"\"\"Muestra el código fuente de una función del proyecto dentro del notebook.\"\"\"
    display(Markdown(f"```python\\n{inspect.getsource(funcion)}```"))

print('rdflib', rdflib.__version__, '| pandas', pd.__version__)
print('Datos de entrada:', gen.DIR_PROCESADOS.relative_to(gen.RAIZ))
"""),
    md("""
## 3. Prefijos del modelo

Antes de crear tripletas se registran los prefijos de **todo** lo que aparece en el modelo:
el de nuestros datos (`data:`), el de nuestro vocabulario (`vocab:`) y los vocabularios reutilizados.
`RDF`, `RDFS`, `XSD` y `DCTERMS` vienen precargados en rdflib; `schema:`, `sosa:` y `geo:` se
definen manualmente con `Namespace`, igual que `data:` y `vocab:`.

> Una sola URI base (`http://example.org/bcn-kg/data/`) para **las tres fuentes**: así los nodos
> comunes (estaciones, barrios, celdas CAMS) son el mismo nodo en todos los archivos y el grafo queda enlazado.
"""),
    code("""
pd.DataFrame([(p, str(ns)) for p, ns in gen.PREFIJOS.items()], columns=['Prefijo', 'Namespace'])
"""),
    md("""
Modelo v3 (final), con las correcciones de la docente:
- lo dinámico (estado de una estación y medición de aire) es **`schema:Observation`**, con `schema:observationAbout`;
- cada vínculo usa **una sola relación** reutilizada (sin subpropiedades propias): toda ubicación es `schema:containedInPlace`
  (Estación → Barrio → Distrito → Barcelona, y Estación → Celda CAMS);
- la red Bicing es una instancia con nombre y todas las instancias llevan `rdfs:label`.

Clases y atributos propios definidos en `vocab.ttl`:
"""),
    code("""
from IPython.display import Image
Image(filename=str(DIR_E3 / 'modelo' / 'modelo_datos.png'), width=1000)
"""),
    code("""
vocab = rdflib.Graph().parse(gen.RUTA_VOCAB)
RDF, RDFS = rdflib.RDF, rdflib.RDFS
filas = []
for p in vocab.subjects(RDF.type, RDF.Property):
    filas.append((p.n3(vocab.namespace_manager),
                  vocab.value(p, RDFS.domain).n3(vocab.namespace_manager),
                  vocab.value(p, RDFS.range).n3(vocab.namespace_manager)))
clases = sorted(c.n3(vocab.namespace_manager) for c in vocab.subjects(RDF.type, RDFS.Class))
print('Clases propias:', ', '.join(clases))
pd.DataFrame(sorted(filas), columns=['Propiedad', 'Dominio', 'Rango'])
"""),
    md("""
## 4. Revisión de los datos de entrada

Todos los datos están en `datos/procesados/` (11 CSV definitivos, descritos en `datos/README.md`).
Aquí se revisan los de CityBikes que vienen de la limpieza del Entregable 2: filas, duplicados por clave
y valores nulos. Los de calidad del aire (`cams_*.csv`), los de barrios (`bcn_*.csv`) y los enlaces
se generan en la sección 5.
"""),
    code("""
claves = {
    'citybikes_estaciones': ['id_estacion'],
    'citybikes_estado': ['id_estacion', 'captura_utc'],
    'citybikes_operadores': ['id_operador'],
    'procedencia': ['archivo_raw'],
}
resumen = []
for nombre, clave in claves.items():
    df = pd.read_csv(gen.DIR_PROCESADOS / f'{nombre}.csv')
    resumen.append({'archivo': nombre, 'filas': len(df),
                    'duplicados_clave': int(df.duplicated(clave).sum()),
                    'celdas_nulas': int(df.isna().sum().sum())})
pd.DataFrame(resumen)
"""),
    md("""
## 5. Preprocesamiento: corrección de las celdas CAMS

Al revisar los datos se detectó un problema heredado del Entregable 2: **las dos celdas tenían
exactamente los mismos valores de contaminación**. La causa es que Open-Meteo devuelve en
`latitude`/`longitude` una coordenada **redondeada** (41.4, 2.2) que no identifica la celda real.
Se pidieron 6 puntos; 5 respondieron "41.4, 2.2", pero con **3 series distintas**. Al usar esa
coordenada como identificador se fusionaron celdas diferentes y se perdieron 2 series.
"""),
    code("""
import json
ruta_raw = sorted(preprocesar.DIR_RAW_CAMS.glob('*.json'))[-1]
sobre = json.loads(ruta_raw.read_text(encoding='utf-8'))
filas = []
for (lat, lon), item in zip(preprocesar.puntos_solicitados(sobre['url']), sobre['payload']):
    filas.append({'lat_pedida': lat, 'lon_pedida': lon,
                  'lat_reportada': item['latitude'], 'lon_reportada': item['longitude'],
                  'NO2_primeras_3h': item['hourly']['nitrogen_dioxide'][:3],
                  'celda_real': preprocesar.celda_de(lat, lon)[0]})
pd.DataFrame(filas)
"""),
    md("""
**Solución.** La rejilla CAMS Europa es de 0.1° con centros en múltiplos de 0.05. La celda real
se obtiene con `floor(coordenada × 10) / 10` sobre la coordenada **pedida**. La tabla anterior lo
confirma: los puntos con la misma `celda_real` traen exactamente la misma serie. La función
`desanidar_cams` lo **verifica** y falla si no se cumple. Las estaciones se asignan a su celda con
la misma regla (contención exacta, en lugar de "celda más cercana").
"""),
    code("ver_codigo(preprocesar.celda_de)\nver_codigo(preprocesar.desanidar_cams)"),
    code("""
pre = preprocesar.ejecutar(guardar=True)
print('Celdas resultantes:')
display(pre['cams_celdas'])
print('Estaciones por celda:')
display(pre['enlace_estacion_celda'].groupby(['id_celda', 'celda_con_datos']).size().rename('estaciones').reset_index())
print('Observaciones CAMS:', len(pre['cams_observaciones']), '(3 celdas × 48 horas × 3 contaminantes)')
"""),
    md("""
**Limitación documentada:** la celda `celda_41.45_2.25` (noreste, 42 estaciones) no fue muestreada en la
captura del Entregable 2. Se crea igualmente como nodo `vocab:CeldaModelo` para que sus estaciones queden
enlazadas, pero no tiene observaciones. Una nueva captura que incluya un punto en esa celda la completaría.

### 5.1 Barrio y distrito de cada estación (Fuente 3: Open Data BCN)

La docente pidió conectar las estaciones con su barrio y el barrio con algo más general. Open Data BCN publica
los 73 barrios con su contorno (polígono WGS84) y su distrito. Cada estación se asigna al barrio cuyo polígono
**contiene** sus coordenadas (prueba punto-en-polígono por trazado de rayos, sin librerías externas).
"""),
    code("ver_codigo(preprocesar.dentro)\nver_codigo(preprocesar.ubicar_en_barrios)"),
    code("""
eb = pre['enlace_estacion_barrio'].merge(pre['bcn_barrios'], on='id_barrio').merge(pre['bcn_distritos'], on='id_distrito')
print('Estaciones dentro del contorno de un barrio:', int(eb.dentro_del_contorno.sum()), 'de', len(eb))
print('Barrios con estaciones:', eb.id_barrio.nunique(), 'de', len(pre['bcn_barrios']))
eb.groupby('nombre_distrito').agg(barrios=('id_barrio', 'nunique'), estaciones=('id_estacion', 'count')) \
  .sort_values('estaciones', ascending=False)
"""),
    md("""
## 6. Esquema de identificación de URIs

Se usa el **nombre o identificador natural** de cada entidad para formar su URI, con dos reglas de formato
(función `normalizar`): quitar tildes y caracteres especiales, y reemplazar espacios por `_`.
La misma función se usa en las tres fuentes, por eso el nodo común se genera idéntico.

| Clase | Patrón de URI | Ejemplo |
|---|---|---|
| `vocab:RedBicicletas` | `data:red_bicing` | `data:red_bicing` |
| `schema:Organization` | `data:organizacion_<nombre>` | `data:organizacion_CESPA` |
| `vocab:EstacionBicicleta` | `data:estacion_<id>` | `data:estacion_00028670…` |
| `schema:Observation` (estado) | `data:estado_<id>_<fecha>` | `data:estado_00028670…_20261112T163024` |
| `vocab:CeldaModelo` | `data:celda_<lat>_<lon>` | `data:celda_41.35_2.15` |
| `vocab:Contaminante` | `data:contaminante_<código>` | `data:contaminante_NO2` |
| `schema:Observation` (aire) | `data:obs_<celda>_<hora>_<código>` | `data:obs_celda_41.35_2.15_20261111T000000_NO2` |
| `vocab:Barrio` | `data:barrio_<código>` | `data:barrio_07` |
| `vocab:Distrito` | `data:distrito_<código>` | `data:distrito_02` |
| `schema:City` | `data:Barcelona` | `data:Barcelona` |

Para las estaciones se usa el `id` de CityBikes y no el nombre, porque los nombres de calle se repiten
(mismo problema que dos personas con el mismo nombre).
"""),
    code("""
ver_codigo(gen.normalizar)
for texto in ['Barcelona de Serveis Municipals, S.A. (BSM)', 'PL  JOANIC - C / BRUNIQUER, 59', 'Universidad Autónoma']:
    print(f'{texto!r:50} -> {gen.normalizar(texto)}')
print(gen.uri_operador('CESPA'))
print(gen.uri_contaminante('PM2_5'))
"""),
    md("""
## 7. Prueba con 2 filas

Antes de procesar todo se generan los datos con **solo 2 estaciones y 2 observaciones**, para revisar a mano
que cada tripleta sea coherente con el modelo.
"""),
    code("""
g_b2, g_a2, g_z2 = gen.ejecutar(limite=2, guardar=False)
print(f'Bicing: {len(g_b2)} tripletas | Calidad del aire: {len(g_a2)} tripletas | Barrios: {len(g_z2)} tripletas')
muestra = gen.nuevo_grafo()
estacion = next(g_b2.subjects(rdflib.RDF.type, gen.VOCAB.EstacionBicicleta))
for t in g_b2.triples((estacion, None, None)):
    muestra.add(t)
estado = g_b2.value(predicate=gen.SCHEMA.observationAbout, object=estacion)
for t in g_b2.triples((estado, None, None)):
    muestra.add(t)
print(muestra.serialize(format='turtle'))
"""),
    md("""
## 8. Generación de la Fuente 1 — CityBikes (Bicing)

`generar_bicing` recorre los DataFrames y, por cada entidad: (1) forma la URI, (2) la vincula a su clase con
`rdf:type`, (3) le pone un `rdfs:label` legible (el nombre que muestra GraphDB), (4) añade sus atributos como
`Literal` con su tipo XSD y (5) la conecta con las demás entidades. La estación se conecta con su barrio y con su
celda CAMS mediante **la misma relación**, `schema:containedInPlace`: la celda es el **nodo puente** con la Fuente 2.
El estado de la estación es una `schema:Observation` que apunta a ella con `schema:observationAbout`.
"""),
    code("ver_codigo(gen.generar_bicing)"),
    code("""
dfs = gen.cargar_csv()
g_bicing = gen.generar_bicing(dfs)
print('Tripletas generadas (Bicing):', len(g_bicing))
"""),
    md("""
## 9. Generación de la Fuente 2 — Open-Meteo (CAMS)

`generar_calidad_aire` crea las celdas, los contaminantes y una `schema:Observation` por celda, hora y
contaminante (`schema:observationAbout` → celda, `sosa:observedProperty` → contaminante, `schema:observationDate`
y `schema:value`). La unidad (`μg/m³`, código UN/CEFACT `GQ`) se declara una sola vez en el contaminante.
La celda (~11 km) desborda Barcelona, por eso no se declara contenida en la ciudad: se llega a ella desde
las estaciones. Barcelona, Bicing y los contaminantes se enlazan con DBpedia.
"""),
    code("ver_codigo(gen.generar_calidad_aire)"),
    code("""
g_aire = gen.generar_calidad_aire(dfs)
print('Tripletas generadas (calidad del aire):', len(g_aire))
obs = next(g_aire.subjects(rdflib.RDF.type, gen.SCHEMA.Observation))
muestra = gen.nuevo_grafo()
for t in g_aire.triples((obs, None, None)):
    muestra.add(t)
for t in g_aire.triples((g_aire.value(obs, gen.SOSA.observedProperty), None, None)):
    muestra.add(t)
print(muestra.serialize(format='turtle'))
"""),
    md("""
### 9.1 Generación de la Fuente 3 — Open Data BCN (barrios y distritos)

`generar_barrios` crea los 10 distritos (contenidos en Barcelona, `schema:City`) y los 73 barrios (contenidos en su
distrito). Junto con el enlace estación → barrio de `generar_bicing`, queda la jerarquía completa con una sola
relación: **Estación → Barrio → Distrito → Barcelona** (`schema:containedInPlace`).
"""),
    code("ver_codigo(gen.generar_barrios)"),
    code("""
g_barrios = gen.generar_barrios(dfs)
print('Tripletas generadas (barrios):', len(g_barrios))
barrio = gen.uri_barrio(7)
distrito = g_barrios.value(barrio, gen.SCHEMA.containedInPlace)
print(g_barrios.value(barrio, rdflib.RDFS.label), '→', g_barrios.value(distrito, rdflib.RDFS.label), '→',
      g_barrios.value(g_barrios.value(distrito, gen.SCHEMA.containedInPlace), rdflib.RDFS.label))
"""),
    md("""
## 10. Validación contra el modelo

`validar` comprueba automáticamente, sobre los datos + `vocab.ttl`:
1. que cada atributo `vocab:` respete su `rdfs:domain` y `rdfs:range` (clase o tipo XSD);
2. que todo nodo `data:` usado como objeto esté descrito (tenga `rdf:type`);
3. que ningún sujeto quede sin tipo.

Primero se demuestra que detecta errores con un grafo defectuoso; luego se valida el grafo real.
"""),
    code("ver_codigo(gen.validar)"),
    code("""
malo = rdflib.Graph()
e = gen.DATA['estacion_prueba']
malo.add((e, rdflib.RDF.type, gen.VOCAB.EstacionBicicleta))
malo.add((e, gen.VOCAB.distanciaACeldaModeloKm, rdflib.Literal('lejos')))
malo.add((e, gen.SCHEMA.containedInPlace, gen.DATA['celda_que_no_existe']))
print('Grafo defectuoso ->', *gen.validar(malo, vocab), sep='\\n  ')

errores = gen.validar(g_bicing + g_aire + g_barrios, vocab)
print(f'\\nGrafo del proyecto -> {len(errores)} errores')
celdas_a = set(g_aire.subjects(rdflib.RDF.type, gen.VOCAB.CeldaModelo))
celdas_b = {o for o in g_bicing.objects(None, gen.SCHEMA.containedInPlace) if o in celdas_a}
print('Celdas referenciadas desde Bicing que existen en CAMS:', len(celdas_b & celdas_a), 'de', len(celdas_b))
"""),
    md("""
## 11. Serialización y totales de nodos por clase

Se guardan tres archivos Turtle, uno por fuente (`serialize` elige el formato por la extensión). El total de
nodos por clase se calcula con SPARQL; **la misma consulta** (`E3_rdf/sparql/01_nodos_por_clase.rq`) se ejecuta
luego en GraphDB para comprobar que la carga está completa.
"""),
    code("""
gen.ejecutar(guardar=True)
for f in sorted(gen.DIR_SALIDA.glob('*.ttl')):
    n = len(rdflib.Graph().parse(f))
    print(f'{f.name:20} {f.stat().st_size/1024:8.1f} KB  {n:6} tripletas (releído desde disco)')

total = gen.nuevo_grafo()
for g in (g_bicing, g_aire, g_barrios):
    total += g
tabla = gen.nodos_por_clase(total)
print('Total de tripletas de datos:', len(total))
tabla
"""),
    code("""
fig, ax = plt.subplots(figsize=(8, 4))
orden = tabla.sort_values('Nodos')
barras = ax.barh(orden['Clase'], orden['Nodos'], color='#3b6ea5')
ax.bar_label(barras, padding=3)
ax.set_xlabel('Número de nodos (instancias)')
ax.set_title('Nodos por clase en el grafo RDF generado')
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
plt.show()
"""),
    md("""
## 12. Integración movilidad + calidad del aire

La prueba de que las fuentes quedaron **enlazadas**: partiendo de las estaciones (Fuente 1) se llega, a través
de la celda común, a las observaciones de NO₂ (Fuente 2). Consulta guardada en `sparql/03_estacion_aire.rq`.
"""),
    code("""
consulta = DIR_E3 / 'sparql' / '03_estacion_aire.rq'
res = total.query(consulta.read_text(encoding='utf-8'))
pd.DataFrame([(r.celda.n3(total.namespace_manager), int(r.estaciones), float(r.no2_medio)) for r in res],
             columns=['Celda', 'Estaciones', 'NO2 medio (μg/m³)'])
"""),
    md("""
Ahora cada celda tiene su propio valor medio de NO₂ (con los datos del Entregable 2 las dos celdas daban
el mismo valor, 27.68). La celda `celda_41.45_2.25` no aparece porque no tiene observaciones.

**Comprobación del enlace de las tres fuentes** (`sparql/05_enlace_fuentes.rq`): cuántas estaciones llegan a un
barrio, a una celda y a datos de aire.
"""),
    code("""
def consultar(nombre):
    res = (total + vocab).query((DIR_E3 / 'sparql' / f'{nombre}.rq').read_text(encoding='utf-8'))
    return pd.DataFrame([[v.toPython() if v is not None else None for v in fila] for fila in res],
                        columns=[str(v) for v in res.vars])
consultar('05_enlace_fuentes')
"""),
    md("""
**Tabla de evidencia** (`sparql/06_integracion_movilidad_aire.rq`): una fila por estación con su barrio, distrito,
bicicletas, anclajes y el aire de su celda a la hora H. Recorre las tres fuentes en una sola consulta; en GraphDB
su resultado se exporta a `E3_rdf/graphdb/integracion_movilidad_aire.csv`.
"""),
    code("""
integracion = consultar('06_integracion_movilidad_aire')
print('Filas:', len(integracion), '| con datos de aire:', int(integracion.no2.notna().sum()))
integracion.head(8)
"""),
    md("""
**Resumen por distrito** (`sparql/07_resumen_por_distrito.rq`): sube por la jerarquía Estación → Barrio → Distrito.
"""),
    code("consultar('07_resumen_por_distrito')"),
    md("""
## 13. Almacenamiento en GraphDB

GraphDB 10.8.5 se ejecuta en Docker con `docker compose up -d` (archivo `docker-compose.yml` en la raíz: datos en un
volumen persistente y memoria ajustada para las consultas con `GROUP BY`).
El script `cargar_graphdb.py` usa la API REST de GraphDB para:
1. crear el repositorio `bcn-kg` (ruleset RDFS-Plus Optimized);
2. importar los cuatro archivos (vocabulario, Bicing, calidad del aire y barrios) en **un solo grafo** `graph/bcn-kg`,
   para que las tres fuentes queden conectadas;
3. ejecutar las consultas `sparql/01–07` (verificación e integración) y `sparql/pc01–pc15`, guardar sus resultados en
   `E3_rdf/graphdb/` y exportar la tabla de evidencia a CSV;
4. registrar todas las consultas como **consultas guardadas** del Workbench.
"""),
    code("ver_codigo(cargar_graphdb.importar)"),
    md("""
Resultados devueltos por **GraphDB** (sin inferencia), comparados con los calculados localmente con rdflib en la
sección 11: deben coincidir exactamente.
"""),
    code("""
import json
dir_gdb = DIR_E3 / 'graphdb'
gdb = pd.DataFrame(json.loads((dir_gdb / '01_nodos_por_clase.json').read_text(encoding='utf-8')))
gdb['Clase'] = [total.namespace_manager.normalizeUri(rdflib.URIRef(c)) for c in gdb['clase']]
gdb['Nodos GraphDB'] = gdb['nodos'].astype(int)
comparacion = tabla.merge(gdb[['Clase', 'Nodos GraphDB']], on='Clase', how='outer')
comparacion['Coincide'] = comparacion['Nodos'] == comparacion['Nodos GraphDB']
total_gdb = json.loads((dir_gdb / '02_total_tripletas.json').read_text(encoding='utf-8'))[0]['tripletas']
print('Tripletas explícitas en GraphDB:', total_gdb, '(datos + vocab.ttl)')
comparacion
"""),
    md("""
Las capturas de GraphDB (grafos importados, totales por clase, jerarquía de clases y visual graph) están en
`E3_rdf/informe/capturas/` y se incluyen en el informe.

## 14. Preguntas de competencia (PC1–PC15)

Cada pregunta tiene su consulta en `sparql/pcNN.rq`. Se ejecutan sobre el grafo local y se compara el número de
filas con lo que devolvió GraphDB. Las integradas usan la hora CAMS más cercana a la captura de Bicing (H = 17:00 UTC).
"""),
    code("""
filas = []
for ruta in sorted((DIR_E3 / 'sparql').glob('pc*.rq')):
    n_local = len(list((total + vocab).query(ruta.read_text(encoding='utf-8'))))
    n_gdb = len(json.loads((dir_gdb / f'{ruta.stem}.json').read_text(encoding='utf-8')))
    filas.append((ruta.stem.upper(), ruta.read_text(encoding='utf-8').splitlines()[0].split('· ', 1)[-1], n_local, n_gdb))
pcs = pd.DataFrame(filas, columns=['PC', 'Pregunta', 'Filas (rdflib)', 'Filas (GraphDB)'])
pcs['Coincide'] = pcs['Filas (rdflib)'] == pcs['Filas (GraphDB)']
pd.set_option('display.max_colwidth', 120)
pcs
"""),
    md("""
Ejemplo de pregunta integrada (PC11): estaciones con 5 o más bicicletas en celdas con NO₂ ≤ 25 µg/m³ a la hora H.
"""),
    code("""
print((DIR_E3 / 'sparql' / 'pc11.rq').read_text(encoding='utf-8'))
res = (total + vocab).query((DIR_E3 / 'sparql' / 'pc11.rq').read_text(encoding='utf-8'))
pd.DataFrame([(str(r.nombre), int(r.bicicletas), str(r.celda), float(r.no2)) for r in res],
             columns=['Estación', 'Bicicletas', 'Celda', 'NO2 (µg/m³)']).head(10)
"""),
    md("""
## 15. Conclusiones

- Se generaron tres archivos RDF (uno por fuente) bajo una única URI base y se cargaron en un solo grafo:
  estación → barrio → distrito → Barcelona y estación → celda CAMS, todo con `schema:containedInPlace`.
- Lo dinámico (estados y mediciones de aire) es `schema:Observation`, como pidió la docente.
- Los datos se validan automáticamente contra el dominio y rango declarados en `vocab.ttl`: 0 errores.
- El preprocesamiento detectó y corrigió una fusión incorrecta de celdas CAMS del Entregable 2, recuperando
  2 series de contaminantes que se habían perdido.
- Las 15 preguntas de competencia se responden con SPARQL y GraphDB devuelve los mismos resultados.
- La prueba con 2 filas, la validación y los tests (`pytest E3_rdf/tests`) permiten regenerar los datos de forma
  reproducible con `python E3_rdf/scripts/generar_rdf.py`.
"""),
]


def main():
    nb = nbformat.v4.new_notebook(cells=CELDAS)
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    DIR_NB.mkdir(parents=True, exist_ok=True)
    NotebookClient(nb, timeout=300, kernel_name="python3",
                   resources={"metadata": {"path": str(DIR_NB)}}).execute()
    nbformat.write(nb, DIR_NB / f"{NOMBRE}.ipynb")
    html, _ = HTMLExporter().from_notebook_node(nb)
    (DIR_NB / f"{NOMBRE}.html").write_text(html, encoding="utf-8")
    print("Notebook y HTML generados en", DIR_NB)


if __name__ == "__main__":
    main()
