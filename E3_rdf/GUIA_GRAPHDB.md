# Guía de la demostración en GraphDB

Workbench: http://localhost:7200 · repositorio **bcn-kg** · un solo grafo `http://example.org/bcn-kg/graph/bcn-kg`.

## Antes de empezar

- Conectar la computadora a la corriente: si entra en reposo, Docker se detiene.
- Abrir **Docker Desktop**. GraphDB arranca solo; esperar unos 30 segundos y abrir el Workbench.
  - Si no arranca, ejecutar `docker compose up -d` desde la raíz del repositorio.
  - Los datos quedan guardados en un volumen: no hace falta volver a cargarlos.
- Solo si el repositorio está vacío (primera vez en otra computadora) o se cambió el RDF, ejecutar
  `uv run --no-project python E3_rdf/scripts/cargar_graphdb.py`. Este comando importa los datos y deja guardadas
  todas las consultas.
- **Recorrido automático:** `uv run --no-project --with playwright python E3_rdf/scripts/capturar_graphdb.py`.
  - Abre un navegador visible y hace solo los pasos 1 a 7 de abajo.
  - En cada paso muestra un cartel que explica lo que se ve.
  - Guarda las capturas del informe en `E3_rdf/informe/capturas/`.

Para hacerlo a mano, primero **seleccionar el repositorio**: clic en **bcn-kg** (arriba a la derecha o en la lista).

Todas las consultas están guardadas en **SPARQL → icono de carpeta (*Show saved queries*)**. Son `01`–`07` y
`PC01`–`PC15`; se elige una y se presiona **Run**.

## Paso 1 · Un solo grafo
Ir a **Explore → Graphs overview**. Aparece un solo grafo, `graph/bcn-kg`, que contiene:

- el modelo (`vocab.ttl`);
- las tres fuentes: Bicing, calidad del aire, barrios y distritos.

«The default graph» no tiene datos cargados: ahí deja GraphDB las tripletas que **infiere** el razonador
(los axiomas RDFS y, p. ej., `estación a schema:CivicStructure`). Todas las tripletas explícitas (13 874)
están en `graph/bcn-kg`.

## Paso 2 · Nodos por clase (consulta `01`)

| Clase | Nodos |
|---|---:|
| `schema:Observation` (estados de estación + mediciones de aire) | 974 |
| `vocab:EstacionBicicleta` | 542 |
| `vocab:Barrio` | 73 |
| `vocab:Distrito` | 10 |
| `vocab:CeldaModelo` | 4 |
| `vocab:Contaminante` | 3 |
| `schema:Organization` (operadores) | 3 |
| `vocab:RedBicicletas` | 1 |
| `schema:City` (Barcelona) | 1 |

Las filas extra que muestra GraphDB son superclases inferidas por el razonamiento RDFS. Por ejemplo,
`schema:AdministrativeArea` = 83, que son los 73 barrios más los 10 distritos.

## Paso 3 · Una estación con todas sus conexiones (consulta `04`)
Abrir `04` y, en vez de **Run**, usar el botón **Visual graph** (el icono de los tres círculos). Se ven las cadenas
completas de la estación:

- Estado (`observationAbout`) → Estación → Barrio → Distrito → Barcelona (`containedInPlace`);
- Estación → Red Bicing (`isPartOf`) → operadores (`provider`);
- Estación → Celda CAMS ← mediciones de NO₂, PM10 y PM2.5 (`observationAbout`) → contaminante (`observedProperty`).

## Paso 4 · Jerarquía territorial
**Explore → Visual graph** → buscar `distrito_06` (Gràcia). Aparecen sus barrios y, hacia arriba, Barcelona.
Doble clic en un barrio para ver sus estaciones.

## Paso 5 · La celda CAMS, nodo puente
**Explore → Visual graph** → buscar `celda_41.35_2.15`. Hacia un lado están las estaciones que contiene (Bicing) y
hacia el otro, las mediciones de aire que tratan de ella (CAMS). Así se conectan movilidad y calidad del aire.

## Paso 6 · Evidencia de la integración (consultas `05` y `06`)
- **`05`** da 542 · 542 · 542 · 500:
  - 542 estaciones en total;
  - 542 en un barrio;
  - 542 en una celda CAMS;
  - 500 con datos de aire.

  Las 42 restantes están en `celda_41.45_2.25`, que no tuvo punto de consulta en Open-Meteo.
- **`06`** devuelve una fila por estación con su barrio, distrito, bicicletas, anclajes y el NO₂, PM10 y PM2.5 de su
  celda a la hora H (12/11/2026 17:00 UTC). Son 542 filas. También se exporta a
  `E3_rdf/graphdb/integracion_movilidad_aire.csv`.

## Paso 7 · Resumen por distrito (consulta `07`)
Muestra 10 filas: estaciones, bicicletas disponibles y NO₂ medio por distrito. Por ejemplo, Eixample tiene 114 estaciones.

## Preguntas de competencia
`PC01`–`PC15` responden las 15 preguntas del E1; `PC11`–`PC15` son las integradas (Bicing + aire). Por ejemplo,
`PC11` devuelve 183 estaciones con 5 o más bicicletas en celdas con NO₂ ≤ 25 µg/m³ a la hora H.
Cada una tiene su archivo `E3_rdf/sparql/pcNN.rq`.

## Si algo falla
- **"Rendering results" se queda cargando:** clic en **Results only** y luego en **Editor and results**.
- **Error *Insufficient free Heap Memory*:** el contenedor no se creó con `docker-compose.yml`. Recrearlo así:
  ```bash
  docker rm -f graphdb-bcn
  docker compose up -d
  uv run --no-project python E3_rdf/scripts/cargar_graphdb.py
  ```
