# Smart City Barcelona: Knowledge Graph & Heterogeneous Data Pipeline (LOD)

> **Universidad Técnica Particular de Loja (UTPL)**  
> **Asignatura:** Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos  
> **Docente:** Dra. Janneth Alexandra Chicaiza Espinosa  
> **Autores:** Alex Gutiérrez, David Manotoa  
> **Periodo:** Noviembre 2026  

---

## 📌 Descripción del Proyecto

Este repositorio contiene la arquitectura, pipeline ETL, modelo ontológico (RDF / RDFS / OWL / SOSA) y análisis de interoperabilidad para la integración semántica de dos ecosistemas heterogéneos de datos abiertos en la ciudad de **Barcelona, España**:

1. **Movilidad Urbana Sostenible:** Red pública de bicicletas compartidas (Bicing) consumida en tiempo real vía API REST de CityBikes.
2. **Medio Ambiente y Salud:** Concentraciones horarias de contaminantes atmosféricos ($NO_2$, $PM_{10}$, $PM_{2.5}$) obtenidas del modelo de dispersión regional europeo Copernicus Atmosphere Monitoring Service (**CAMS**) vía API REST de Open-Meteo.

---

## 🏗️ Estructura del Repositorio

```text
smartcity-bcn-knowledge-graph/
├── datos/                       # ÚNICA carpeta de datos del proyecto (ver datos/README.md)
│   ├── crudos/                  # Respuestas JSON de las APIs, sin modificar
│   └── procesados/              # Los 8 CSV definitivos que se convierten a RDF
├── E1_correccion/               # Entregable 1: dominio, fuentes y 15 preguntas de competencia
├── E2_extraccion/               # Entregable 2: código de extracción y limpieza, modelo tentativo
│   ├── src/bcn_kg/              # Funciones de extracción, limpieza y enlace
│   ├── scripts/                 # capturar.py (APIs → datos/crudos) y procesar_datos.py (→ datos/procesados)
│   ├── modelo/                  # Modelo tentativo del E2 (histórico)
│   ├── notebooks/               # Notebook HTML entregado en el E2
│   └── tests/
├── E3_rdf/                      # Entregable 3: modelo v2, RDF, GraphDB e informe
├── Clases/                      # Apuntes de clase
└── README.md
```

---

## 🚀 Instrucciones de Reproducción

```bash
git clone https://github.com/alexdgutierrezcordova-nila/smartcity-bcn-knowledge-graph.git
cd smartcity-bcn-knowledge-graph/E2_extraccion
uv sync
uv run python scripts/capturar.py        # (opcional) nueva captura de las APIs → datos/crudos
uv run python scripts/procesar_datos.py  # JSON → CSV de CityBikes en datos/procesados
uv run pytest -v
```

Los CSV de calidad del aire y el enlace estación–celda los genera `E3_rdf/scripts/preprocesar.py`
(ver la sección del Entregable 3).

---

## 🧩 Entregable 3: Modelo v2, datos RDF y GraphDB (`E3_rdf/`)

> **Para leer primero:** `E3_rdf/informe/informe_proyecto.html` (informe sin código: fuentes, limpieza,
> preguntas de competencia, modelo, RDF, GraphDB y respuestas). El código y sus salidas están en
> `E3_rdf/notebooks/E3_generacion_rdf.html`.

`E3_rdf/modelo/` es el **modelo vigente (v2)**. Simplifica el modelo tentativo de `E2_extraccion/modelo/`, que se
conserva como historial.

```text
E3_rdf/
├── modelo/                   # Modelo v2: vocab.ttl, modelo_datos.png/.svg,
│                             # vocabularios_reutilizados.csv, mapeo_campos.csv
├── scripts/
│   ├── preprocesar.py        # Corrige las celdas CAMS y escribe cams_*.csv y enlace en datos/procesados
│   ├── generar_rdf.py        # CSV -> RDF (Turtle) + validación contra vocab.ttl
│   ├── generar_diagrama.py   # Dibuja el diagrama del modelo
│   ├── cargar_graphdb.py     # Crea el repositorio bcn-kg en GraphDB, importa y ejecuta las consultas
│   ├── generar_notebook.py   # Construye, ejecuta y exporta el notebook técnico a HTML
│   └── generar_informe_html.py # Informe sin código (HTML + Word)
├── rdf/                      # bicing.ttl, calidad_aire.ttl, estadisticas.md
├── sparql/                   # pc01–pc15.rq (preguntas de competencia) y consultas de verificación
├── graphdb/                  # Resultados de las consultas ejecutadas en GraphDB
├── notebooks/                # E3_generacion_rdf.ipynb / .html (anexo técnico)
├── informe/                  # informe_proyecto.html, Informe_proyecto.docx y capturas/
└── tests/                    # pytest: preprocesamiento, RDF y las 15 preguntas
```

Desde la raíz del repositorio:

```bash
uv run --no-project --with rdflib --with pandas --with pytest python -m pytest E3_rdf/tests
uv run --no-project --with rdflib --with pandas python E3_rdf/scripts/generar_rdf.py
uv run --no-project --with matplotlib python E3_rdf/scripts/generar_diagrama.py
uv run --no-project --with rdflib --with pandas --with matplotlib --with python-docx python E3_rdf/scripts/generar_informe_html.py
uv run --no-project --with rdflib --with pandas --with matplotlib --with nbformat --with nbclient --with nbconvert --with ipykernel python E3_rdf/scripts/generar_notebook.py
```

Almacenamiento en GraphDB (repositorio `bcn-kg`, un solo grafo `graph/bcn-kg` con el modelo y ambas fuentes):

```bash
docker run -d --name graphdb-bcn -p 7200:7200 ontotext/graphdb:10.8.5
uv run --no-project python E3_rdf/scripts/cargar_graphdb.py
```

Workbench en http://localhost:7200. Guía para la demostración: `E3_rdf/GUIA_GRAPHDB.md`.

---

## 📄 Licencia y Atribución
* Datos de Movilidad: **Open Database License (ODbL)** / **CC BY 4.0** (CityBikes / Bicing BSM).
* Datos de Calidad del Aire: **CC BY 4.0** (Open-Meteo / Copernicus CAMS).
