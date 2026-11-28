# Datos del proyecto

Esta es la única carpeta de datos del proyecto: todo lo que se convierte a RDF sale de aquí.

```text
datos/
├── crudos/                      ← respuestas de las fuentes, sin modificar
│   ├── citybikes/citybikes_bicing_20261112T163053Z.json          (captura 12/11/2026 16:30 UTC)
│   ├── openmeteo/openmeteo_cams_20261112T163054Z.json            (captura 12/11/2026 16:30 UTC)
│   └── opendata_bcn/opendata_bcn_barris_…json, opendata_bcn_districtes_…json
└── procesados/                  ← los 11 CSV definitivos
```

## Las tres fuentes

| Fuente | Qué aporta | Cómo se obtuvo |
|---|---|---|
| CityBikes (`api.citybik.es/v2/networks/bicing`) | Estaciones Bicing, su estado y los operadores | `E2_extraccion/scripts/capturar.py` |
| Open-Meteo Air Quality (Copernicus CAMS) | NO₂, PM10 y PM2.5 por hora y celda de 0.1° | `E2_extraccion/scripts/capturar.py` |
| Open Data BCN (barrios `b21fa550-56ea-4f4c-9adc-b8009381896e`, distritos `576bc645-9481-4bc4-b8bf-f5972c20df3f`) | Los 73 barrios y 10 distritos con su contorno (WKT) | API CKAN `opendata-ajuntament.barcelona.cat/data/api/3/action/datastore_search?resource_id=<id>&limit=1000` (la descarga directa del archivo responde 403) |

## Flujo

```text
APIs ──capturar.py──▶ crudos/*.json ──procesar_datos.py──▶ citybikes_*.csv, incidencias_calidad.csv, procedencia.csv
                                    └──preprocesar.py────▶ cams_*.csv, bcn_*.csv, enlace_estacion_celda.csv,
                                                           enlace_estacion_barrio.csv
procesados/*.csv ──generar_rdf.py──▶ E3_rdf/rdf/{bicing,calidad_aire,barrios}.ttl ──cargar_graphdb.py──▶ GraphDB
```

- `capturar.py` y `procesar_datos.py` están en `E2_extraccion/scripts/`.
- `preprocesar.py` y `generar_rdf.py` están en `E3_rdf/scripts/`.

## Los 11 CSV definitivos

| # | CSV | Filas | Lo genera | Qué contiene | En el grafo |
|---|---|---:|---|---|---|
| 1 | `citybikes_estaciones.csv` | 542 | `procesar_datos.py` | Una fila por estación: id, nombre original y limpio, lat/long, red | Nodos `vocab:EstacionBicicleta` |
| 2 | `citybikes_estado.csv` | 542 | `procesar_datos.py` | Bicicletas libres, anclajes libres, mecánicas, eléctricas y en línea en el momento de la captura | `schema:Observation` con `observationAbout` → estación |
| 3 | `citybikes_operadores.csv` | 3 | `procesar_datos.py` | Operadores de Bicing: BSM, CESPA, PBSC | `schema:Organization`, `schema:provider` de la red |
| 4 | `cams_celdas.csv` | 4 | `preprocesar.py` | Celdas CAMS de 0.1°: centro (lat/long), elevación y puntos consultados | `vocab:CeldaModelo`, el nodo puente entre movilidad y aire |
| 5 | `cams_observaciones.csv` | 432 | `preprocesar.py` | Una fila por celda × hora × contaminante (NO₂, PM10, PM2.5) con su valor | `schema:Observation` con `observationAbout` → celda |
| 6 | `enlace_estacion_celda.csv` | 542 | `preprocesar.py` | Celda que contiene cada estación y su distancia al centro de la celda | `estación schema:containedInPlace celda` |
| 7 | `bcn_distritos.csv` | 10 | `preprocesar.py` | Código y nombre de cada distrito | `vocab:Distrito` `containedInPlace` Barcelona |
| 8 | `bcn_barrios.csv` | 73 | `preprocesar.py` | Código, nombre y distrito de cada barrio | `vocab:Barrio` `containedInPlace` distrito |
| 9 | `enlace_estacion_barrio.csv` | 542 | `preprocesar.py` | Barrio de cada estación, calculado con punto en polígono sobre el contorno oficial (las 542 caen dentro de un contorno) | `estación schema:containedInPlace barrio` |
| 10 | `procedencia.csv` | 2 | `capturar.py` | URL, fecha, código HTTP y número de registros de cada captura de API | `dcterms:source` / `dcterms:issued` |
| 11 | `incidencias_calidad.csv` | 8 | `procesar_datos.py` | Problemas detectados al limpiar, p. ej. mecánicas + eléctricas ≠ disponibles | No se convierte; es la evidencia de la limpieza que se muestra en el informe |

En `incidencias_calidad.csv`, la columna `entidad` conserva el nombre que usaba el E2 (`EstadoEstacion`). En el
modelo final esa entidad es un `schema:Observation`.

## Archivos eliminados (obsoletos del Entregable 2)

| Archivo | Por qué se eliminó |
|---|---|
| `openmeteo_celdas.csv` (2 celdas) | Usaba como identificador la coordenada redondeada de Open-Meteo y mezclaba celdas distintas. Lo reemplaza `cams_celdas.csv` (4 celdas) |
| `openmeteo_observaciones.csv` (288 filas) | Tenía el mismo error: fusionaba series de celdas distintas. Lo reemplaza `cams_observaciones.csv` (432 filas) |
| `enlace_estacion_celda.csv` del E2 | Asignaba las estaciones a las 2 celdas erróneas. Lo reemplaza el nuevo `enlace_estacion_celda.csv` |
| `enlace_estado_observacion.csv` | Era una tabla plana que unía estado + aire. En el E3 esa unión la hace el grafo; además estaba armada sobre las celdas erróneas |

Siguen disponibles en el historial de git si hiciera falta consultarlos.
