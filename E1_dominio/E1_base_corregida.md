# Documento Base Corregido: Entregable 1 (E1)
**Versión de Referencia Interna para el Desarrollo de los Entregables E2 y E3**

* **Institución:** Universidad Técnica Particular de Loja (UTPL)
* **Asignatura:** Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos
* **Docente:** Janneth Alexandra Chicaiza Espinosa
* **Integrantes del Grupo:** Alex Gutiérrez, David Manotoa
* **Dominio:** Ciudades Inteligentes (Smart Cities) — Barcelona, España
* **Subdominios Integrados:** Movilidad Urbana Sostenible (Bicing / CityBikes) y Medio Ambiente (Calidad del Aire / Open-Meteo CAMS)
* **Fecha de consolidación:** 12 de noviembre de 2026

---

## 1. Registro Crítico de Cambios y Rectificaciones (Auditoría Adversarial)

| Código | Defecto Original en el E1 Entregado | Causa Raíz / Evidencia Empírica | Corrección Aplicada en este Documento Base |
|---|---|---|---|
| **H-NOM** | Portada consignaba "Davide Manotoa". | Error tipográfico en el nombre del estudiante. | Corregido a **David Manotoa**. |
| **H-IA** | Declaración de IA mencionaba accidentes en Madrid, Overpass API y farolas (`street_lamp`). | Texto residual no auditado proveniente de borradores previos. | Reescrita al 100% reflejando exclusivamente el procesamiento real de Barcelona (Bicing + Open-Meteo). |
| **H1** | El registro citado en texto (§5.2) decía `05:19:23`, `free=1`, `empty=9`, pero la captura de la Fig. 1 mostraba `16:55:24`, `free=4`, `empty=3`. | Desconexión entre muestras redactadas y la evidencia visual. | Sustituido por registros reales extraídos directamente de las llamadas a la API oficial con hash y timestamp auditables. |
| **H2** | El informe afirmaba que el `timestamp` era la marca de tiempo de reporte de la estación. | Análisis de dispersión: 542 estaciones reportan marcas dentro del mismo segundo (`16:30:24.89...`). | Redefinido como **marca temporal de captura/ingesta** del servicio CityBikes. |
| **H3** | Timestamps con formato inválido `+00:00Z`. | Bug del backend de CityBikes al combinar desplazamiento numérico y sufijo Z. | Función de limpieza `parsear_ts_citybikes` documentada y probada formalmente. |
| **H4** | Consulta a Open-Meteo usaba `Europe/Berlin` pero la tabla declaraba "UTC". Día 25/10/2026 coincidió con el cambio de hora de verano (DST). | Ambigüedad de huso horario y hora repetida. | Todas las consultas fijadas estrictamente a `timezone=GMT` (UTC sin DST). |
| **H5** | Coordenadas contradictorias de "Plaza Cataluña" (PC3 usaba `41.3865, 2.1694`; ficha Open-Meteo usaba `41.3888, 2.1589`). | Incoherencia de georreferenciación interna. | Estandarizado a la estación oficial Bicing "PL. CATALUNYA, 7" (`41.38654, 2.16943`). |
| **H6** | Regla de enlace espacial exigía distancia Haversine <= 1 km. | La resolución regional CAMS es de 0.1° (~11 km). La distancia promedio de las estaciones al centroide de celda es de 3.13 km. Un radio <= 1 km descartaría más del 97% de la red. | Rediseño: **Pertenencia a celda CAMS (`vocab:contenidaEnCelda`)**, manteniendo la distancia geodésica como métrica de calidad. |
| **H7** | PC comparaban lecturas horarias con umbrales diarios (PM10 > 45 µg/m³ OMS 24h) o anuales (NO2 > 40 µg/m³ UE anual). | Error metodológico de comparación de escalas temporales. | Reformulación de las PC a medias móviles/diarias o umbrales horarios técnicamente válidos. |
| **H9** | URIs preliminares usaban `geo:{lat}_{long}` (invadiendo prefijo estándar) y dominio ajeno `smartcity.bcn.es`. | Infracción de higiene de URIs (Clase 4 y 7). | Espacios de nombres saneados: `vocab:` (`http://example.org/bcn-kg/vocab#`) y `data:` (`http://example.org/bcn-kg/data/`). |
| **H10** | Uso de `geo:location` hacia un `PuntoEspacial` ficticio afirmando que la estación y el contaminante estaban en el mismo punto. | Falacia semántica de identidad locativa. | Adopción de la ontología W3C SOSA/SSN: `vocab:CeldaModelo` ⊑ `schema:Place` y `vocab:EstadoEstacion` ⊑ `sosa:Observation`. |
| **H11** | Omisión de operadores (`BSM`, `CESPA`, `PBSC`) y de la regla de consistencia `normal_bikes + ebikes == free_bikes`. | Subutilización de campos existentes en el payload. | Incorporación formal de `vocab:operadaPor` e implementación de pruebas de integridad aritmética. |

---

## 2. Dominio y Problema (Redacción Académica Corregida)

### 2.1 Ámbito y delimitación geográfica
El proyecto se sitúa en la intersección de dos ámbitos prioritarios de las Ciudades Inteligentes (Smart Cities): **Movilidad Urbana Sostenible** (gestión del sistema público de bicicletas compartidas) y **Medio Ambiente** (análisis de la exposición a contaminantes atmosféricos mediante modelos de reanálisis). El área de estudio comprende el término municipal y metropolitano de **Barcelona, España** (coordenadas aproximadas: latitud 41.35° N a 41.46° N, longitud 2.10° E a 2.23° E).

### 2.2 Formulación del problema y beneficiarios
La actividad física asociada al transporte activo (ciclismo urbano) genera beneficios evidentes para la salud cardiovascular y la reducción de emisiones vehiculares. No obstante, cuando los ciclistas realizan esfuerzo físico en entornos con concentraciones elevadas de dióxido de nitrógeno ($NO_2$) y material particulado fino ($PM_{10}$ y $PM_{2.5}$), el incremento en la tasa de ventilación pulmonar incrementa la inhalación neta de contaminantes tóxicos, aumentando el riesgo de exacerbaciones respiratorias e inflamación vascular.

En la actualidad, los datos requeridos para monitorizar este fenómeno operan en silos aislados:
1. **Infraestructura de movilidad:** El sistema Bicing (operado por BSM, CESPA y PBSC) expone el inventario de 542 estaciones físicas a través de la API REST de CityBikes.
2. **Estimación ambiental:** El Servicio de Vigilancia Atmosférica de Copernicus (**CAMS**), integrado globalmente mediante la API REST de Open-Meteo, modela concentraciones horarias continuas en cuadrículas regionales de ~11 km ($0.1^\circ$).

**Beneficiarios directos:**
* **Área de Movilidad y Medio Ambiente del Ajuntament de Barcelona:** Disponer de un Grafo de Conocimiento semántico para identificar qué sectores de la red de bicicletas operan bajo celdas con excedencias de contaminantes y regular las políticas de rebalanceo de flotas.
* **Planificadores Urbanos:** Detectar corredores con alta demanda de anclajes pero comprometidos por mala calidad atmosférica para planificar barreras vegetales o pacificación de tráfico.
* **Comunidad ciclista metropolitana:** Consultar información semánticamente integrada sobre estaciones con alta oferta y menores índices de dispersión de partículas finas.

---

## 3. Matriz Reformulada de Preguntas de Competencia (PC1 a PC15)

| ID | Pregunta de Competencia (Formulación Rigurosa) | Fuentes | Tipo | Beneficiario y Decisión de Gestión | Viabilidad Técnica Demostrada en Datos |
|---|---|---|---|---|---|
| **PC1** | ¿Qué estaciones de bicicletas cuentan con más de 10 bicicletas mecánicas o eléctricas disponibles para uso inmediato en el corte de captura $t$? | CityBikes | Simple | Ciclista urbano: localizar estaciones con alta disponibilidad garantizada. | Resuelta con `vocab:bicicletasDisponibles > 10` sobre `vocab:EstadoEstacion`. |
| **PC2** | ¿Qué estaciones presentan saturación operativa total (`anclajesLibres == 0`), impidiendo la devolución de vehículos en el instante $t$? | CityBikes | Simple | Operador BSM: planificar furgonetas de rebalanceo para retirar exceso de vehículos. | Resuelta con `vocab:anclajesLibres == 0`. |
| **PC3** | ¿Qué estaciones de bicicletas se ubican a menos de 1 km geodésico del centro neurálgico de Plaza Cataluña (`41.38654, 2.16943`)? | CityBikes | Simple | Turistas y usuarios intermodales: acceso peatonal desde Cercanías y Metro. | Resuelta aplicando Haversine sobre `geo:lat` y `geo:long`. |
| **PC4** | ¿Cuáles estaciones disponen de bicicletas con asistencia eléctrica (`ebikes > 0`) en la captura actual? | CityBikes | Simple | Usuarios de movilidad de media distancia o sectores con pendiente (Gràcia/Montjuïc). | Resuelta con `vocab:bicicletasElectricas > 0`. |
| **PC5** | ¿Cuáles son las 10 estaciones con mayor capacidad de anclajes operativos observados (suma de `bicicletasDisponibles` + `anclajesLibres`)? | CityBikes | Simple | Planificador de transporte: identificar nodos estructurales de alta capacidad. | Resuelta sumando `vocab:bicicletasDisponibles + vocab:anclajesLibres`. |
| **PC6** | ¿Cuál es la concentración estimada de $NO_2$ en la celda CAMS que contiene a la estación central de Plaza Cataluña a la hora $H$ UTC? | Open-Meteo | Simple | Agencia de salud ambiental: verificar cumplimiento horario en el núcleo urbano. | Resuelta consultando la observación de la celda `celda_41.40_2.20`. |
| **PC7** | ¿En qué celdas la media móvil diaria de $PM_{10}$ superó el valor guía de protección de la salud de la OMS ($45\,\mu\text{g/m}^3$ en 24h)? | Open-Meteo | Simple | Autoridad metropolitana: activar protocolo de aviso por polvo y partículas. | Resuelta agregando 24 cortes horarios en `vocab:ObservacionCalidadAire`. |
| **PC8** | ¿Qué celdas atmosféricas registran niveles horarios de $PM_{2.5} > 25\,\mu\text{g/m}^3$ (categoría desfavorable para esfuerzo físico intenso)? | Open-Meteo | Simple | Deportistas y ciclistas: advertencia de exposición pulmonar a partículas finas. | Resuelta filtrando observaciones de $PM_{2.5} > 25$. |
| **PC9** | ¿Cuál fue la amplitud de dispersión (máximo y mínimo) de $NO_2$ registrado entre las distintas celdas de Barcelona a lo largo del período capturado? | Open-Meteo | Simple | Investigadores de calidad del aire: cuantificar el gradiente espacial y temporal intraurbano. | Resuelta agregando `MAX()` y `MIN()` por celda en SPARQL. |
| **PC10** | ¿Cuál es la relación porcentual entre $PM_{2.5}$ y $PM_{10}$ ($PM_{2.5} / PM_{10}$) en cada celda para evaluar la preponderancia de aerosoles de combustión? | Open-Meteo | Simple | Epidemiólogos: caracterizar si la contaminación proviene de tráfico o polvo sahariano. | Resuelta con cálculo de razón, manejando denominadores nulos. |
| **PC11** | ¿Qué estaciones con alta disponibilidad (`bicicletasDisponibles >= 5`) se ubican en celdas con $NO_2 \le 25\,\mu\text{g/m}^3$ en la misma ventana horaria UTC? | CityBikes + Open-Meteo | **Integrada** | Ciclista: seleccionar estaciones de origen con aire relativamente limpio y buen inventario. | Cruza `vocab:EstadoEstacion` con `vocab:ObservacionCalidadAire` vía `vocab:CeldaModelo`. |
| **PC12** | ¿Qué estaciones con saturación de devolución (`anclajesLibres <= 2`) coinciden con celdas cuya media diaria de $PM_{10}$ excedió el límite legal UE ($50\,\mu\text{g/m}^3$)? | CityBikes + Open-Meteo | **Integrada** | Gestores de tráfico: evitar demoras forzadas de ciclistas buscando anclaje en zonas contaminadas. | Cruza estaciones críticas con medias agregadas de la celda. |
| **PC13** | ¿Qué estaciones con oferta de ebikes (`ebikes >= 3`) se encuentran en sectores donde las partículas $PM_{2.5}$ superan $15\,\mu\text{g/m}^3$? | CityBikes + Open-Meteo | **Integrada** | Ciclistas con afecciones respiratorias: evitar sobreesfuerzo en microambientes polucionados. | Cruza inventario eléctrico con concentración de partículas finas. |
| **PC14** | ¿Qué estaciones de bicicletas están asignadas a la celda CAMS que registró la máxima concentración de $NO_2$ en la última lectura horaria disponible? | CityBikes + Open-Meteo | **Integrada** | Inspectores ambientales: focalizar controles de tráfico rodado en el sector de máxima emisión. | Subconsulta `ORDER BY DESC(?no2) LIMIT 1` vinculada a sus estaciones hijas. |
| **PC15** | ¿Cuáles estaciones presentan simultáneamente déficit crítico (`bicicletasDisponibles <= 1`) y una celda con $NO_2 > 40\,\mu\text{g/m}^3$, requiriendo intervención prioritaria? | CityBikes + Open-Meteo | **Integrada** | Mesa de movilidad municipal: priorizar cuadrillas de distribución donde el servicio falla en ambiente tóxico. | Filtro multi-criterio integrado sobre movilidad y medio ambiente. |

---

## 4. Fichas Técnicas Definitivas de las Fuentes Seleccionadas

### 4.1 Fuente 1: CityBikes REST API (Red Bicing Barcelona)
* **Publicador:** Proyecto internacional Open Source CityBikes (PyBikes), consumiendo el servicio de Barcelona de Serveis Municipals (BSM), CESPA y PBSC.
* **Endpoint oficial:** `https://api.citybik.es/v2/networks/bicing`
* **Autenticación:** Abierta (sin API Key). Límite de cortesía: 300 peticiones/hora.
* **Formato:** JSON estructurado jerárquico.
* **Licencia:** Open Database License (ODbL) y Creative Commons Attribution 4.0 International (CC BY 4.0).
* **Volumen real observado en piloto:** **542 estaciones físicas activas** en Barcelona.
* **Campos relevantes verificados:** `id` (hash único MD5), `name` (calle/plaza), `latitude`/`longitude` (grados decimales WGS84), `timestamp` (ISO 8601 con desfase UTC), `free_bikes`, `empty_slots`, `extra.ebikes`, `extra.normal_bikes`, `extra.online`, `network.company`.

### 4.2 Fuente 2: Open-Meteo Air Quality REST API (Copernicus CAMS)
* **Publicador:** Open-Meteo GmbH, integrando los modelos de reanálisis y dispersión del Copernicus Atmosphere Monitoring Service (**CAMS European Air Quality Ensemble**).
* **Endpoint oficial:** `https://air-quality-api.open-meteo.com/v1/air-quality`
* **Autenticación:** Libre para uso académico no comercial (límite: 10.000 peticiones/día).
* **Formato:** JSON con metadatos de cuadrícula y arreglos vectoriales horarios.
* **Licencia:** Creative Commons Attribution 4.0 International (CC BY 4.0).
* **Cobertura espacial y temporal:** Resolución regional de $0.1^\circ$ (~11 km). Cubre el área metropolitana de Barcelona a través de dos celdas primarias:
  - `celda_41.40_2.20` (Centro, Eixample, Litoral, Sant Martí: 397 estaciones).
  - `celda_41.40_2.10` (Suroeste, Sants, Les Corts: 145 estaciones).
* **Parámetros configurados:** `hourly=nitrogen_dioxide,pm10,pm2_5`, `timezone=GMT` (UTC estricto), `cell_selection=nearest`.
* **Variables atmosféricas:** $NO_2$, $PM_{10}$, $PM_{2.5}$ expresadas en $\mu\text{g/m}^3$.

---

## 5. Estrategia de Enlace Semántico (Nodo Puente y SOSA)

1. **Enlace Geoespacial:**  
   Cada estación se georreferencia con sus coordenadas puntuales `geo:lat` y `geo:long`. Mediante la propiedad `vocab:contenidaEnCelda`, la estación se enlaza a su celda contenedora `vocab:CeldaModelo` (Nodo Puente). La distancia continua entre la estación y el centroide se registra con `vocab:distanciaACentroideKm`.
2. **Enlace Temporal:**  
   Se utiliza el estándar W3C SOSA/SSN. La disponibilidad de la estación se instancia como `vocab:EstadoEstacion` (con `sosa:resultTime`), y las concentraciones de contaminantes como `vocab:ObservacionCalidadAire` (con `sosa:resultTime`). El cruce se resuelve mediante concordancia de la celda y coincidencia de la hora UTC más cercana ($|\Delta t| \le 30\text{ min}$).
3. **Vocabularios Oficiales:**  
   - `schema:` (clases de infraestructura y organizaciones)
   - `sosa:` (patrón de observaciones y sensores)
   - `geo:` (WGS84 lat/long)
   - `dcterms:` (procedencia y jerarquías)
   - `vocab:` (`http://example.org/bcn-kg/vocab#`)
   - `data:` (`http://example.org/bcn-kg/data/`)

---

## 6. Declaración de Uso de Inteligencia Artificial Generativa

En estricto cumplimiento con la directiva ética y la especificación del Entregable 1, se declara el uso transparente de modelos de IA generativa:

| Herramienta y Versión | Tarea Realizada con Asistencia de IA | Prompt / Directiva Principal Emitida | Verificación y Control Humano Riguroso |
|---|---|---|---|
| **Antigravity AI (Google DeepMind)** | Auditoría técnica adversarial de inconsistencias en el Entregable 1 preliminar y diseño del pipeline ETL. | «Actúa como un Tribunal Técnico Multi-Agente especializado en Interoperabilidad, Grafos RDF y W3C. Audita sin complacencia el avance preliminar contra los datos reales de las APIs.» | Se contrastaron manualmente las afirmaciones del informe contra la respuesta JSON real de CityBikes (detectando la discrepancia de datos en Plaza Joanic H1, el bug de timestamp H3 y la resolución de 11 km de Open-Meteo H6). |
| **Python Scripting Engine** | Desarrollo de pruebas unitarias y cálculo geodésico de distancias Haversine. | «Genera funciones de normalización de texto, corrección de timestamps '+00:00Z' y desanidación de series vectoriales Open-Meteo con pruebas pytest.» | Ejecución de 7 pruebas unitarias formales con pytest, validando el 100% de los casos borde y comprobando la sintaxis RDF con rdflib. |
