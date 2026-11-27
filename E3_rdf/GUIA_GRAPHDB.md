# Guía rápida: demostración en GraphDB

Requisito: la computadora conectada a la corriente (si entra en reposo, Docker se detiene).
Si GraphDB no abre: ejecutar `docker start graphdb-bcn` y esperar unos 30 segundos.
Workbench: http://localhost:7200

## 0. Seleccionar el repositorio
Arriba a la derecha, seleccionar **bcn-kg**.

## 1. Verificar los datos cargados
**Explore → Graphs overview**. Debe aparecer **un solo grafo**, `http://example.org/bcn-kg/graph/bcn-kg`,
con el modelo (vocab) y las dos fuentes (Bicing y calidad del aire) juntos.
(«The default graph» lo muestra GraphDB siempre: es el grafo por defecto del repositorio.)

Para demostrar que las fuentes están conectadas: **SPARQL** → pegar `E3_rdf/sparql/05_enlace_fuentes.rq`.
Debe dar 542 estaciones en una celda descrita por la fuente CAMS (misma URI en ambas fuentes) y 500 con datos
de aire; las 42 restantes están en `celda_41.45_2.25`, que no tuvo punto de consulta en Open-Meteo.

## 2. Totales de nodos por clase
**SPARQL** → pegar y presionar **Run**:

```sparql
PREFIX data: <http://example.org/bcn-kg/data/>
SELECT ?clase (COUNT(DISTINCT ?s) AS ?nodos)
WHERE { ?s a ?clase . FILTER(STRSTARTS(STR(?s), STR(data:))) }
GROUP BY ?clase ORDER BY DESC(?nodos)
```

Si queda en "Rendering results": clic en **Results only** y luego en **Editor and results**.
Las clases extra (`sosa:Observation` = 974, `sosa:FeatureOfInterest` = 546, `schema:Place` = 5, etc.) son superclases inferidas por el razonamiento RDFS.

## 3. Ver el grafo
**Explore → Visual graph** → buscar `celda_41.35_2.15`. Doble clic en un nodo para expandirlo:
las estaciones (Bicing) se conectan con la celda CAMS (nodo puente).

## 4. Preguntas de competencia
**SPARQL** → pegar el contenido de `E3_rdf/sparql/pc11.rq` (integrada) y ejecutar.
Devuelve las estaciones con 5 o más bicicletas en celdas con NO₂ ≤ 25 µg/m³ a las 17:00 UTC (183 filas).
Cada pregunta PC1–PC15 tiene su archivo `pcNN.rq` en la misma carpeta.
