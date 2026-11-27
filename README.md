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
Proyecto General/
├── Clases/                      # Apuntes y transcripciones de las cátedras universitarias
├── E1_correccion/               # Documento base corregido del Entregable 1 (auditoría técnica)
│   └── E1_base_corregida.md     # Fichas técnicas, matriz de 15 PC y estrategia de enlace
├── E2_extraccion/               # Entregable 2: Pipeline ETL, datos y modelo tentativo
│   ├── data/
│   │   ├── raw/                 # Capturas crudas JSON inalteradas (sobres de procedencia)
│   │   └── processed/           # Datasets limpios e integrados (CSV)
│   ├── modelo/                  # Especificación ontológica tentativa
│   │   ├── vocab.ttl            # Vocabulario formal en sintaxis Turtle (RDF/OWL/SOSA)
│   │   ├── modelo_tentativo.md  # Justificación ontológica, clases, propiedades y axiomas
│   │   └── mapeo_campos.csv     # Matriz de correspondencia campos API ↔ términos semánticos
│   ├── notebooks/               # Cuadernos Jupyter y reportes exportados
│   │   ├── E2_extraccion_limpieza.ipynb # Pipeline reproducible con análisis exploratorio
│   │   └── E2_extraccion_limpieza.html  # Reporte autocontenido para evaluación docente
│   ├── scripts/                 # Scripts modulares de captura, procesamiento y verificación
│   ├── src/bcn_kg/              # Paquete Python estructurado (extracción, limpieza, enlace)
│   ├── tests/                   # Batería de pruebas unitarias automatizadas (pytest)
│   ├── pyproject.toml           # Configuración de dependencias con uv (Python 3.12)
│   └── run_final.ps1            # Script de orquestación y empaquetado final
├── BIM1 - Práctica - E1.docx    # Documento original del Entregable 1
└── .gitignore                   # Exclusión estricta de entornos virtuales y archivos temporales
```

---

## 🚀 Instrucciones de Reproducción

### 1. Clonar el repositorio y configurar el entorno
```bash
git clone https://github.com/alexdgutierrezcordova-nila/smartcity-bcn-knowledge-graph.git
cd smartcity-bcn-knowledge-graph/E2_extraccion
uv sync
```

### 2. Ejecutar las pruebas unitarias
```bash
uv run pytest -v
```

### 3. Verificar coherencia e integridad de datos
```bash
uv run python scripts/verificar_coherencia.py
```

### 4. Orquestación y generación del reporte HTML
```powershell
powershell -ExecutionPolicy Bypass -File .\run_final.ps1
```

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
│   ├── preprocesar.py        # Corrige la asignación de celdas CAMS (rejilla 0.1°)
│   ├── generar_rdf.py        # CSV -> RDF (Turtle) + validación contra vocab.ttl
│   ├── generar_diagrama.py   # Dibuja el diagrama del modelo
│   ├── cargar_graphdb.py     # Crea el repositorio bcn-kg en GraphDB, importa y ejecuta las consultas
│   ├── generar_notebook.py   # Construye, ejecuta y exporta el notebook técnico a HTML
│   └── generar_informe_html.py # Informe sin código (HTML + Word)
├── data/                     # Celdas, observaciones y enlace CAMS corregidos (CSV)
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
