# Datos del proyecto

Única carpeta de datos del proyecto. Todo lo que se convierte a RDF sale de aquí.

```text
datos/
├── crudos/                      ← respuestas de las APIs, sin modificar (captura del 12/11/2026 16:30 UTC)
│   ├── citybikes/citybikes_bicing_20261112T163053Z.json
│   └── openmeteo/openmeteo_cams_20261112T163054Z.json
└── procesados/                  ← los 8 CSV definitivos
```

## Flujo

```text
APIs ──capturar.py──▶ crudos/*.json ──procesar_datos.py──▶ citybikes_*.csv, incidencias_calidad.csv
                                    └──preprocesar.py────▶ cams_*.csv, enlace_estacion_celda.csv
procesados/*.csv ──generar_rdf.py──▶ E3_rdf/rdf/*.ttl ──cargar_graphdb.py──▶ GraphDB
```

- `capturar.py` y `procesar_datos.py` están en `E2_extraccion/scripts/`.
- `preprocesar.py` y `generar_rdf.py` están en `E3_rdf/scripts/`.

## Los 8 CSV definitivos

| # | CSV | Filas | Lo genera | Qué contiene | Por qué se queda |
|---|---|---:|---|---|---|
| 1 | `citybikes_estaciones.csv` | 542 | `procesar_datos.py` | Una fila por estación: id, nombre original y limpio, lat/long, red | Datos fijos de cada estación → nodos `EstacionBicicleta` |
| 2 | `citybikes_estado.csv` | 542 | `procesar_datos.py` | Bicicletas libres, anclajes libres, mecánicas, eléctricas y en línea en el momento de la captura | Datos que cambian con el tiempo → nodos `EstadoEstacion` (observaciones) |
| 3 | `citybikes_operadores.csv` | 3 | `procesar_datos.py` | Operadores de Bicing: BSM, CESPA, PBSC | Nodos `schema:Organization` que operan la red |
| 4 | `cams_celdas.csv` | 4 | `preprocesar.py` | Celdas CAMS de 0.1°: centro (lat/long), elevación y puntos consultados | Nodo puente entre las dos fuentes → `CeldaModelo` |
| 5 | `cams_observaciones.csv` | 432 | `preprocesar.py` | Una fila por celda × hora × contaminante (NO₂, PM10, PM2.5) con su valor | Mediciones de aire → nodos `ObservacionCalidadAire` |
| 6 | `enlace_estacion_celda.csv` | 542 | `preprocesar.py` | Celda que contiene cada estación y su distancia al centro de la celda | Une Bicing con calidad del aire: es la integración de las fuentes |
| 7 | `procedencia.csv` | 2 | `capturar.py` | URL, fecha, código HTTP y número de registros de cada captura | Trazabilidad: de dónde y cuándo salió cada dato (`dcterms:source` / `issued`) |
| 8 | `incidencias_calidad.csv` | 8 | `procesar_datos.py` | Problemas detectados al limpiar (p. ej. mecánicas + eléctricas ≠ disponibles) | Evidencia de la limpieza; se muestra en el informe |

## Archivos eliminados (obsoletos del Entregable 2)

| Archivo | Por qué se eliminó |
|---|---|
| `openmeteo_celdas.csv` (2 celdas) | Usaba la coordenada redondeada de Open-Meteo como identificador y mezclaba celdas distintas. Lo reemplaza `cams_celdas.csv` (4 celdas) |
| `openmeteo_observaciones.csv` (288 filas) | Mismo error: series de celdas distintas fusionadas. Lo reemplaza `cams_observaciones.csv` (432) |
| `enlace_estacion_celda.csv` del E2 | Asignaba estaciones a las 2 celdas erróneas. Lo reemplaza el nuevo `enlace_estacion_celda.csv` |
| `enlace_estado_observacion.csv` | Tabla plana que unía estado + aire. En el E3 esa unión la hace el grafo; además estaba armada sobre las celdas erróneas |

Siguen disponibles en el historial de git si hiciera falta consultarlos.
