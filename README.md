# Smart City Barcelona: Knowledge Graph & Heterogeneous Data Pipeline (LOD)

> **Universidad Técnica Particular de Loja (UTPL)**  
> **Asignatura:** Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos  
> **Docente:** Dra. Janneth Alexandra Chicaiza Espinosa  
> **Autores:** Alex Gutiérrez, David Manotoa  
> **Periodo:** Noviembre 2026  

---

## 📌 Descripción del Proyecto

Grafo de conocimiento que integra, en **un solo grafo RDF con URIs comunes**, la movilidad urbana y la calidad del
aire de **Barcelona**. Tres fuentes abiertas:

1. **Movilidad (CityBikes):** las 542 estaciones de la red Bicing y su estado (bicicletas y anclajes libres).
2. **Calidad del aire (Open-Meteo / Copernicus CAMS):** concentraciones horarias de NO₂, PM10 y PM2.5 por celda
   de 0.1° (~11 km) del modelo europeo CAMS.
3. **Territorio (Open Data BCN):** los 73 barrios y 10 distritos oficiales, con sus contornos.

Cómo se conecta todo (todas las ubicaciones usan `schema:containedInPlace`):

```text
Estado (schema:Observation) ──observationAbout──▶ Estación ──containedInPlace──▶ Barrio ──▶ Distrito ──▶ Barcelona
                                                     │
                                              containedInPlace
                                                     ▼
Medición NO₂/PM10/PM2.5 (schema:Observation) ──observationAbout──▶ Celda CAMS   ← nodo puente movilidad ↔ aire
```

> **Para presentar:** abrir `E3_rdf/informe/informe_proyecto.html` (informe sin código, 3 fases) y
> `E3_rdf/notebooks/E3_generacion_rdf.html` (código con sus salidas). Demo en GraphDB: `E3_rdf/GUIA_GRAPHDB.md`.

---

## 🏗️ Estructura del Repositorio

```text
smartcity-bcn-knowledge-graph/
├── E1_dominio/                  # Entregable 1: dominio, fuentes y 15 preguntas de competencia
│   ├── E1_base_corregida.md/.docx   # versión corregida
│   └── E1_entrega_original.docx     # lo que se entregó
├── E2_extraccion/               # Entregable 2: extracción y limpieza (histórico, sigue funcionando)
│   ├── src/bcn_kg/              # funciones de extracción, limpieza y enlace
│   ├── scripts/                 # capturar.py (APIs → datos/crudos) y procesar_datos.py (→ datos/procesados)
│   ├── modelo/                  # modelo tentativo del E2 (reemplazado por E3_rdf/modelo)
│   ├── notebooks/               # notebook HTML entregado en el E2
│   └── tests/
├── datos/                       # ÚNICA carpeta de datos (ver datos/README.md)
│   ├── crudos/                  # respuestas de las 3 fuentes, sin modificar
│   └── procesados/              # los 11 CSV que se convierten a RDF
├── E3_rdf/                      # Entregable 3 (final): modelo v3, RDF, GraphDB, informe
├── material_curso/              # apuntes de clase y especificación de los entregables
└── README.md
```

---

## 🧩 Entregable 3 (`E3_rdf/`)

```text
E3_rdf/
├── modelo/                   # Modelo v3: vocab.ttl, modelo_datos.png/.svg,
│                             # vocabularios_reutilizados.csv (justificación), mapeo_campos.csv (CSV → RDF)
├── scripts/
│   ├── preprocesar.py        # celdas CAMS, enlace estación–celda y estación–barrio (punto en polígono)
│   ├── generar_rdf.py        # CSV → RDF (Turtle) + validación contra vocab.ttl
│   ├── generar_diagrama.py   # dibuja el diagrama del modelo
│   ├── cargar_graphdb.py     # crea el repositorio bcn-kg, importa, ejecuta y guarda las consultas
│   ├── capturar_graphdb.py   # recorrido guiado y VISIBLE por GraphDB + capturas del informe
│   ├── generar_notebook.py   # construye, ejecuta y exporta el notebook técnico a HTML
│   └── generar_informe_html.py # informe sin código (HTML + Word)
├── rdf/                      # bicing.ttl, calidad_aire.ttl, barrios.ttl, estadisticas.md
├── sparql/                   # 01–07 (verificación e integración) y pc01–pc15 (preguntas de competencia)
├── graphdb/                  # resultados obtenidos en GraphDB + integracion_movilidad_aire.csv
├── notebooks/                # E3_generacion_rdf.ipynb / .html
├── informe/                  # informe_proyecto.html, Informe_proyecto.docx y capturas/
├── GUIA_GRAPHDB.md           # guion de la demostración
└── tests/                    # pytest: preprocesamiento, RDF, integración y las 15 preguntas
```

**Modelo v3** (correcciones de la docente del 26 y 27/11):

- Lo dinámico (estado de la estación y mediciones de aire) es `schema:Observation`.
- Una sola relación por vínculo, sin subpropiedades propias: `schema:containedInPlace` (ubicación),
  `dcterms:isPartOf` (estación → red), `schema:provider` (red → operadores).
- La red Bicing y los operadores son instancias reales; las estaciones están en barrios y distritos
  (`vocab:Barrio`, `vocab:Distrito` ⊑ `schema:AdministrativeArea`) dentro de Barcelona (`schema:City`).
- Todas las instancias tienen `rdfs:label`, para que el Visual graph de GraphDB se lea.

Nodos por clase: 974 `schema:Observation`, 542 `EstacionBicicleta`, 73 `Barrio`, 10 `Distrito`,
4 `CeldaModelo`, 3 `Contaminante`, 3 `schema:Organization`, 1 `RedBicicletas`, 1 `schema:City`.

---

## 🚀 Reproducción

Desde la raíz del repositorio (requiere [uv](https://docs.astral.sh/uv/)):

```bash
# 1. (opcional) nueva captura de CityBikes y Open-Meteo y su limpieza
cd E2_extraccion && uv sync && uv run python scripts/capturar.py && uv run python scripts/procesar_datos.py && cd ..

# 2. CSV → RDF, diagrama y tests
uv run --no-project --with rdflib --with pandas python E3_rdf/scripts/generar_rdf.py
uv run --no-project --with matplotlib python E3_rdf/scripts/generar_diagrama.py
uv run --no-project --with rdflib --with pandas --with pytest python -m pytest E3_rdf/tests

# 3. GraphDB (repositorio bcn-kg, un solo grafo graph/bcn-kg)
docker run -d --name graphdb-bcn -p 7200:7200 -e GDB_HEAP_SIZE=1200m ontotext/graphdb:10.8.5
uv run --no-project python E3_rdf/scripts/cargar_graphdb.py
uv run --no-project --with playwright python E3_rdf/scripts/capturar_graphdb.py   # recorrido visible

# 4. Notebook e informe
uv run --no-project --with rdflib --with pandas --with matplotlib --with nbformat --with nbclient --with nbconvert --with ipykernel python E3_rdf/scripts/generar_notebook.py
uv run --no-project --with rdflib --with pandas --with matplotlib --with python-docx python E3_rdf/scripts/generar_informe_html.py
```

`GDB_HEAP_SIZE=1200m` es necesario: con la memoria por defecto, la consulta 07 (agrupa por distrito) falla con
*Insufficient free Heap Memory*. La primera vez que se usa Playwright: `uv run --no-project --with playwright playwright install chromium`.

---

## 📄 Licencia y Atribución
* Datos de Movilidad: **Open Database License (ODbL)** / **CC BY 4.0** (CityBikes / Bicing BSM).
* Datos de Calidad del Aire: **CC BY 4.0** (Open-Meteo / Copernicus CAMS).
* Barrios y distritos: **CC BY 4.0** (Open Data BCN, Ajuntament de Barcelona).
