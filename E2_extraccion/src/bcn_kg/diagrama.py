"""Módulo para dibujar el diagrama conceptual bipartito (UML-RDF / Chowlk) del modelo de datos tentativo."""

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle


def dibujar_modelo(ruta_salida: Path | str | None = None) -> None:
    """Dibuja el diagrama conceptual de clases y propiedades ontológicas (TBox) siguiendo la notación de cátedra."""
    fig, ax = plt.subplots(figsize=(18.5, 11.5), dpi=160)
    bg_color = "#f6f5f0"
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Título principal
    ax.text(
        50, 97.8,
        "Modelo de datos tentativo (TBox UML-RDF): movilidad urbana (CityBikes Bicing) y calidad del aire (Open-Meteo CAMS)",
        ha="center", va="center", fontsize=13.2, fontweight="bold", color="#141414",
        family="sans-serif"
    )

    # Paleta cromática por vocabulario de la clase
    C_SOSA = "#d6e6f5"       # Azul suave: W3C SOSA / SSN (Observaciones)
    C_SCHEMA = "#deecd7"     # Verde suave: Schema.org + W3C Basic Geo (Lugares / Infraestructura)
    C_SERVICE = "#eadce8"    # Lavanda suave: Schema.org (Servicio y Organización)
    C_PROP = "#f4e5cf"       # Arena suave: Propiedad Observable y QuantitativeValue
    C_RED = "#b81d1d"        # Rojo cátedra: Término propio (vocab:)
    C_BLUE = "#1e40af"       # Azul cátedra: Relación reflexiva / jerárquica

    # =========================================================================
    # 1. CAJA DE LEYENDA (Arriba - Izquierda)
    # =========================================================================
    leg_box = FancyBboxPatch(
        (1.2, 74.5), 27.8, 20.5,
        boxstyle="round,pad=0.3,rounding_size=0.8",
        facecolor="#fbfaf7", edgecolor="#7a7a7a", linewidth=1.0, linestyle="--"
    )
    ax.add_patch(leg_box)

    ax.text(2.2, 93.1, "Leyenda y Notación Ontológica (UML-RDF)", fontsize=9.3, fontweight="bold", color="#1a1a1a")

    items_leyenda = [
        (2.2, 89.3, C_SOSA, "W3C SOSA / SSN (Observation)"),
        (15.5, 89.3, C_SERVICE, "Schema.org (Service / Org)"),
        (2.2, 85.3, C_SCHEMA, "Schema.org / W3C Geo (Place)"),
        (15.5, 85.3, C_PROP, "SOSA Property / Q.Value"),
    ]
    for lx, ly, col, texto in items_leyenda:
        rect = Rectangle((lx, ly - 1.05), 2.0, 2.1, facecolor=col, edgecolor="#444444", linewidth=0.85)
        ax.add_patch(rect)
        ax.text(lx + 2.4, ly, texto, fontsize=7.7, va="center", color="#222222")

    ax.text(2.2, 81.3, "◆ vocab:* (en rojo) = término propio definido en vocab.ttl", fontsize=7.9, fontweight="bold", color=C_RED)
    ax.plot([2.2, 5.2], [78.5, 78.5], color=C_BLUE, linestyle="-", linewidth=1.35)
    ax.text(5.6, 78.5, "bucle reflexivo (Dominio = Rango, ej. containedInPlace)", fontsize=7.7, va="center", color=C_BLUE)
    ax.plot([2.2, 5.2], [75.8, 75.8], color="#991b1b", linestyle="--", linewidth=1.25)
    ax.text(5.6, 75.8, "relación por consulta SPARQL / enlace espacio-temporal", fontsize=7.7, va="center", color="#7f1d1d")

    # =========================================================================
    # Función para dibujar Cajas Bipartitas estilo Cátedra Dra. Chicaiza
    # Compartimento superior: Encabezado de Clase (rdfs:Class)
    # Línea horizontal divisoria estricta
    # Compartimento inferior: SOLO Propiedades de Tipo de Dato (owl:DatatypeProperty)
    # =========================================================================
    def dibujar_clase_bipartita(
        x: float, y: float, w: float, h: float, color: str,
        titulo_clase: str, superclase: str,
        atributos: list[tuple[str, str]]
    ) -> None:
        # Contorno principal
        caja = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.25,rounding_size=0.9",
            facecolor=color, edgecolor="#333333", linewidth=1.25
        )
        ax.add_patch(caja)

        # Compartimento superior (Encabezado de Clase)
        y_header_top = y + h
        h_header = 6.0
        y_sep = y_header_top - h_header

        ax.text(
            x + w / 2, y_header_top - 2.1, titulo_clase,
            ha="center", va="center", fontsize=10.4, fontweight="bold",
            color=C_RED if titulo_clase.startswith("vocab:") else "#111111",
            family="monospace"
        )
        ax.text(
            x + w / 2, y_header_top - 4.4, superclase,
            ha="center", va="center", fontsize=8.0, style="italic", color="#333333"
        )

        # Línea horizontal divisoria bipartita (como en el dibujo de clase)
        ax.plot([x - 0.15, x + w + 0.15], [y_sep, y_sep], color="#333333", linewidth=1.15)

        # Compartimento inferior: SOLO Datatype Properties
        y_cursor = y_sep - 2.2
        paso_y = (y_sep - y - 2.6) / max(len(atributos), 1)
        paso_y = min(paso_y, 3.35)

        for prop, mapeo in atributos:
            es_propio = prop.startswith("vocab:") or prop.startswith("◆ vocab:")
            color_prop = C_RED if es_propio else "#141414"
            peso_prop = "bold" if (es_propio or prop.startswith("dcterms:") or prop.startswith("geo:")) else "normal"

            ax.text(
                x + 0.9, y_cursor, prop,
                ha="left", va="center", fontsize=7.8, family="monospace",
                color=color_prop, fontweight=peso_prop
            )
            if mapeo:
                ax.text(
                    x + w - 0.8, y_cursor, mapeo,
                    ha="right", va="center", fontsize=7.2, family="monospace",
                    color="#4b5563"
                )
            y_cursor -= paso_y

    # =========================================================================
    # 2. CAJAS BIPARTITAS DE CLASES ONTOLÓGICAS
    # =========================================================================

    # 2.1 Arriba - Centro: vocab:RedBicicletas
    dibujar_clase_bipartita(
        37.2, 74.8, 25.6, 19.8, C_SERVICE,
        "vocab:RedBicicletas",
        "⊑ schema:Service (Red Bicing)",
        [
            ("schema:identifier", "← network.id ('bicing')"),
            ("schema:name", "← network.name ('Bicing')"),
            ("dcterms:spatial", "← location.city ('Barcelona')"),
            ("schema:url", "← href (API endpoint)"),
        ]
    )

    # 2.2 Arriba - Derecha: schema:Organization
    dibujar_clase_bipartita(
        71.3, 74.8, 27.5, 19.8, C_SERVICE,
        "schema:Organization",
        "⊑ dcterms:Agent (Operadores Bicing)",
        [
            ("schema:identifier", "← id_operador (slug)"),
            ("schema:name", "← company[] (BSM/CESPA/PBSC)"),
            ("schema:address", "← 'Barcelona, ES' (xsd:string)"),
        ]
    )

    # 2.3 Medio - Izquierda: vocab:EstacionBicicleta
    dibujar_clase_bipartita(
        1.2, 39.0, 27.8, 27.0, C_SCHEMA,
        "vocab:EstacionBicicleta",
        "⊑ schema:CivicStructure + geo:SpatialThing",
        [
            ("schema:identifier", "← extra.uid (cód. municipal)"),
            ("schema:name", "← name (normalizado trim)"),
            ("geo:lat", "← latitude (xsd:decimal)"),
            ("geo:long", "← longitude (xsd:decimal)"),
            ("schema:address", "← address (vía pública)"),
            ("◆ vocab:distanciaACentroideKm", "← dist_km (xsd:decimal)"),
        ]
    )

    # 2.4 Medio - Centro: vocab:CeldaModelo (Nodo Puente)
    dibujar_clase_bipartita(
        37.2, 39.0, 25.6, 27.0, C_SCHEMA,
        "vocab:CeldaModelo",
        "⊑ schema:Place (Nodo Puente CAMS ~11 km)",
        [
            ("schema:identifier", "← id_celda (41.40_2.20)"),
            ("schema:name", "← 'Celda CAMS Barcelona'"),
            ("geo:lat", "← latitude (centroide CAMS)"),
            ("geo:long", "← longitude (centroide CAMS)"),
            ("schema:elevation", "← elevation (m s.n.m.)"),
            ("dcterms:source", "← 'Copernicus CAMS 0.1°'"),
        ]
    )

    # 2.5 Medio - Derecha: vocab:ObservacionCalidadAire
    dibujar_clase_bipartita(
        71.3, 39.0, 27.5, 27.0, "#c5dced",
        "vocab:ObservacionCalidadAire",
        "⊑ sosa:Observation (Open-Meteo CAMS)",
        [
            ("dcterms:identifier", "← id_obs_aire (URI hash)"),
            ("sosa:resultTime", "← hourly.time (UTC dateTime)"),
            ("sosa:hasSimpleResult", "← valor (xsd:decimal)"),
            ("dcterms:issued", "← extraido_utc (procedencia)"),
        ]
    )

    # 2.6 Abajo - Izquierda: vocab:EstadoEstacion
    dibujar_clase_bipartita(
        1.2, 2.5, 27.8, 26.5, C_SOSA,
        "vocab:EstadoEstacion",
        "⊑ sosa:Observation (Inventario CityBikes)",
        [
            ("sosa:resultTime", "← timestamp (UTC limpio)"),
            ("◆ vocab:bicicletasDisponibles", "← free_bikes (integer)"),
            ("◆ vocab:anclajesLibres", "← empty_slots (integer)"),
            ("◆ vocab:bicicletasMecanicas", "← extra.normal_bikes"),
            ("◆ vocab:bicicletasElectricas", "← extra.ebikes"),
            ("◆ vocab:enLinea", "← extra.online (boolean)"),
        ]
    )

    # 2.7 Abajo - Centro: vocab:Contaminante
    dibujar_clase_bipartita(
        37.2, 2.5, 25.6, 26.5, C_PROP,
        "vocab:Contaminante",
        "⊑ sosa:ObservableProperty (Agente químico)",
        [
            ("dcterms:identifier", "← codigo ('NO2'|'PM10'|'PM2_5')"),
            ("rdfs:label", "← 'NO2', 'PM10', 'PM2.5'@es"),
            ("schema:name", "← hourly.{variable_cams}"),
            ("rdfs:comment", "← descripción contaminante"),
        ]
    )

    # 2.8 Abajo - Derecha: schema:QuantitativeValue
    dibujar_clase_bipartita(
        71.3, 2.5, 27.5, 26.5, C_PROP,
        "schema:QuantitativeValue",
        "Resultado estructurado (Schema.org)",
        [
            ("schema:value", "← concentración (xsd:decimal)"),
            ("schema:unitText", "← hourly_units ('µg/m³')"),
            ("schema:unitCode", "← 'GQ' (UN/CEFACT µg/m³)"),
            ("schema:minValue", "← '0.0'^^xsd:decimal"),
        ]
    )

    # =========================================================================
    # 3. FLECHAS DE PROPIEDADES DE OBJETO (owl:ObjectProperty)
    # Viven EXCLUSIVAMENTE en las aristas entre cajas (Dominio -> Rango)
    # =========================================================================
    def flecha_objeto(
        p1: tuple[float, float], p2: tuple[float, float],
        prop_principal: str, subprop: str,
        tx: float, ty: float, rad: float = 0.0
    ) -> None:
        es_propio = "vocab:" in prop_principal
        color_flecha = "#222222"
        color_texto = C_RED if es_propio else "#111111"

        arr = FancyArrowPatch(
            p1, p2,
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>,head_length=6.2,head_width=3.6",
            color=color_flecha, linewidth=1.3
        )
        ax.add_patch(arr)

        etiqueta = f"{prop_principal}\n{subprop}" if subprop else prop_principal
        ax.text(
            tx, ty, etiqueta,
            fontsize=7.8, ha="center", va="center",
            color=color_texto, fontweight="bold" if es_propio else "normal",
            family="monospace",
            bbox=dict(
                boxstyle="round,pad=0.18",
                facecolor=bg_color,
                edgecolor=C_RED if es_propio else "none",
                linewidth=0.75 if es_propio else 0.0,
                alpha=0.92
            )
        )

    # 1. EstacionBicicleta -> RedBicicletas
    flecha_objeto(
        (23.5, 66.3), (36.9, 77.5),
        "◆ vocab:perteneceARed", "(⊑ dcterms:isPartOf)",
        29.8, 70.6, rad=-0.12
    )

    # 2. RedBicicletas -> Organization
    flecha_objeto(
        (63.1, 84.5), (71.0, 84.5),
        "◆ vocab:operadaPor", "(⊑ schema:provider)",
        67.05, 87.8
    )

    # 3. EstacionBicicleta -> CeldaModelo
    flecha_objeto(
        (29.3, 55.5), (36.9, 55.5),
        "◆ vocab:contenidaEnCelda", "(⊑ schema:containedInPlace)",
        33.1, 59.0
    )

    # 4. ObservacionCalidadAire -> CeldaModelo
    flecha_objeto(
        (71.0, 55.5), (63.1, 55.5),
        "sosa:hasFeatureOfInterest", "(Celda observada)",
        67.05, 58.8
    )

    # 5. EstacionBicicleta -> EstadoEstacion
    flecha_objeto(
        (14.5, 38.7), (14.5, 29.3),
        "◆ vocab:tieneEstado", "(⊑ sosa:hasObservation)",
        14.5, 34.0
    )

    # 6. ObservacionCalidadAire -> Contaminante
    flecha_objeto(
        (74.5, 38.7), (61.0, 29.3),
        "◆ vocab:mideContaminante", "(⊑ sosa:observedProperty)",
        67.8, 32.0, rad=-0.06
    )

    # 7. ObservacionCalidadAire -> QuantitativeValue
    flecha_objeto(
        (85.5, 38.7), (85.5, 29.3),
        "sosa:hasResult", "(Valor y unidad)",
        90.2, 34.0
    )

    # =========================================================================
    # 4. BUCLE REFLEXIVO AZUL (Self-Loop de Cátedra: schema:containedInPlace)
    # Sobre vocab:CeldaModelo (⊑ schema:Place) -> jerarquía Place ⊂ Place
    # =========================================================================
    loop_place = FancyArrowPatch(
        (43.5, 66.2), (56.5, 66.2),
        connectionstyle="arc3,rad=-0.55",
        arrowstyle="-|>,head_length=5.8,head_width=3.4",
        color=C_BLUE, linewidth=1.35
    )
    ax.add_patch(loop_place)
    ax.text(
        50.0, 71.1,
        "schema:containedInPlace\n(Celda ⊂ Barcelona [schema:Place])",
        fontsize=7.6, ha="center", va="center", color=C_BLUE, fontweight="bold",
        family="monospace",
        bbox=dict(boxstyle="round,pad=0.14", facecolor=bg_color, edgecolor="none", alpha=0.9)
    )

    # =========================================================================
    # 5. FLECHAS PUNTEADAS ROJAS (Consultas SPARQL / Enlace Espacio-Temporal)
    # =========================================================================
    # Enlace geodésico Haversine Estación <-> Celda
    arr_geo = FancyArrowPatch(
        (29.3, 45.5), (36.9, 45.5),
        connectionstyle="arc3,rad=0.22",
        arrowstyle="<->,head_length=5.2,head_width=3.0",
        color="#991b1b", linewidth=1.2, linestyle="--"
    )
    ax.add_patch(arr_geo)
    ax.text(
        33.1, 41.8, "enlace geodésico Haversine\n(dist. prom. 3.13 km)",
        fontsize=7.4, ha="center", va="center", color="#7f1d1d", style="italic"
    )

    # Enlace espacio-temporal EstadoEstacion <-> ObservacionCalidadAire (PC11 a PC15)
    arr_temp = FancyArrowPatch(
        (28.2, 29.3), (71.5, 39.2),
        connectionstyle="arc3,rad=-0.10",
        arrowstyle="<->,head_length=5.5,head_width=3.2",
        color="#991b1b", linewidth=1.3, linestyle="--"
    )
    ax.add_patch(arr_temp)
    ax.text(
        49.5, 35.8,
        "consulta integrada SPARQL (PC11–PC15): misma celda CAMS ∧ |captura_utc - hora_utc| ≤ 30 min",
        fontsize=7.9, ha="center", va="center", color="#7f1d1d", style="italic",
        bbox=dict(boxstyle="round,pad=0.18", facecolor=bg_color, edgecolor="none", alpha=0.92)
    )

    plt.tight_layout()
    if ruta_salida is not None:
        ruta_salida = Path(ruta_salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(ruta_salida, dpi=160, bbox_inches="tight", facecolor=bg_color)
    plt.show()
