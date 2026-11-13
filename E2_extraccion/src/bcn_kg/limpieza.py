"""Módulo de limpieza, normalización y validación de calidad de datos.

Implementa los controles de auditoría:
- H1: Trazabilidad total de cada campo hacia los JSON crudos.
- H2: Normalización y análisis de dispersión de timestamps de CityBikes.
- H3: Corrección del bug de formateo de timestamp '+00:00Z' de CityBikes.
- H4: Estandarización a marcas temporales UTC (ISO 8601).
- H11: Reglas de consistencia (normal_bikes + ebikes == free_bikes) e incidencias.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


def normalizar_texto(texto: str | None) -> str | None:
    """Aplica trim y colapso de espacios múltiples internos.

    Conserva mayúsculas, minúsculas, barras y caracteres acentuados originales.
    Ejemplo: '  PL JOANIC - C /  BRUNIQUER, 59 ' -> 'PL JOANIC - C / BRUNIQUER, 59'
    """
    if texto is None:
        return None
    texto_limpio = re.sub(r"\s+", " ", str(texto)).strip()
    return texto_limpio if texto_limpio else None


def parsear_ts_citybikes(ts_str: str | None) -> pd.Timestamp | None:
    """Parsea el timestamp de CityBikes corrigiendo el error de estándar '+00:00Z'.

    CityBikes suele devolver: '2026-10-25T16:55:24.292784+00:00Z', que combina
    un desplazamiento numérico (+00:00) con el sufijo 'Z'. Esto causa fallos
    en parsers estrictos de ISO 8601.
    """
    if not ts_str:
        return None

    cadena = str(ts_str).strip()
    # Si termina en +00:00Z o similar (+HH:MMZ o -HH:MMZ), removemos la 'Z' redundante
    if re.search(r"[+-]\d{2}:\d{2}Z$", cadena):
        cadena = cadena[:-1]

    # Convertir a Timestamp forzando UTC
    ts = pd.to_datetime(cadena)
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts


def procesar_raw_citybikes(payload: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Procesa el payload crudo de CityBikes Bicing.

    Retorna tres DataFrames:
    1. df_estaciones: catálogo estático/geográfico de estaciones.
    2. df_estado: observación dinámica instantánea de disponibilidad.
    3. df_operadores: catálogo de entidades operadoras de la red.
    """
    red = payload.get("network", {})
    estaciones_raw = red.get("stations", [])
    companias = red.get("company", [])

    if isinstance(companias, str):
        companias = [companias]

    df_operadores = pd.DataFrame([{"id_operador": f"op_{idx+1}", "nombre": c} for idx, c in enumerate(companias)])

    filas_estacion = []
    filas_estado = []

    for est in estaciones_raw:
        est_id = str(est.get("id", "")).strip()
        extra = est.get("extra", {}) or {}

        # 1. Metadatos de Estación
        nombre_raw = est.get("name")
        nombre_limpio = normalizar_texto(nombre_raw)
        lat = est.get("latitude")
        lon = est.get("longitude")

        filas_estacion.append({
            "id_estacion": est_id,
            "uid": extra.get("uid"),
            "nombre_original": nombre_raw,
            "nombre_limpio": nombre_limpio,
            "latitud": float(lat) if lat is not None else None,
            "longitud": float(lon) if lon is not None else None,
            "id_red": red.get("id", "bicing"),
        })

        # 2. Estado dinámico de la estación
        ts_captura = parsear_ts_citybikes(est.get("timestamp"))
        free_bikes = est.get("free_bikes")
        empty_slots = est.get("empty_slots")
        ebikes = extra.get("ebikes")
        normal_bikes = extra.get("normal_bikes")
        online = extra.get("online")

        filas_estado.append({
            "id_estacion": est_id,
            "captura_utc": ts_captura.isoformat() if ts_captura is not None else None,
            "free_bikes": int(free_bikes) if free_bikes is not None else None,
            "empty_slots": int(empty_slots) if empty_slots is not None else None,
            "ebikes": int(ebikes) if ebikes is not None else 0,
            "normal_bikes": int(normal_bikes) if normal_bikes is not None else None,
            "online": bool(online) if online is not None else True,
        })

    df_estaciones = pd.DataFrame(filas_estacion)
    df_estado = pd.DataFrame(filas_estado)

    return df_estaciones, df_estado, df_operadores


def validar_calidad_citybikes(df_estaciones: pd.DataFrame, df_estado: pd.DataFrame) -> pd.DataFrame:
    """Evalúa reglas de consistencia física y geográfica.

    Retorna un DataFrame de incidencias detectadas (auditables).
    """
    incidencias = []

    # Regla 1: Bounding Box metropolitano de Barcelona (Lat: [41.30, 41.50], Lon: [2.05, 2.30])
    for _, fila in df_estaciones.iterrows():
        lat = fila["latitud"]
        lon = fila["longitud"]
        if lat is None or lon is None or not (41.30 <= lat <= 41.50 and 2.05 <= lon <= 2.30):
            incidencias.append({
                "entidad": "Estacion",
                "id_recurso": fila["id_estacion"],
                "regla": "Coordenadas fuera de Bounding Box Barcelona",
                "detalle": f"lat={lat}, lon={lon}",
                "gravedad": "CRÍTICA",
            })

    # Regla 2: Integridad aritmética H11 (normal_bikes + ebikes == free_bikes)
    for _, fila in df_estado.iterrows():
        fb = fila["free_bikes"]
        nb = fila["normal_bikes"]
        eb = fila["ebikes"]

        if fb is not None and nb is not None and eb is not None:
            if nb + eb != fb:
                incidencias.append({
                    "entidad": "EstadoEstacion",
                    "id_recurso": f"{fila['id_estacion']}@{fila['captura_utc']}",
                    "regla": "Discrepancia suma bicicletas: normal + ebikes != free_bikes",
                    "detalle": f"normal={nb}, ebikes={eb}, free={fb} (delta={fb - (nb+eb)})",
                    "gravedad": "MEDIA",
                })

        # Regla 3: Valores negativos
        for campo in ["free_bikes", "empty_slots", "ebikes", "normal_bikes"]:
            val = fila.get(campo)
            if val is not None and val < 0:
                incidencias.append({
                    "entidad": "EstadoEstacion",
                    "id_recurso": f"{fila['id_estacion']}@{fila['captura_utc']}",
                    "regla": f"Valor negativo en {campo}",
                    "detalle": f"{campo}={val}",
                    "gravedad": "CRÍTICA",
                })

    return pd.DataFrame(incidencias)


def desanidar_hourly_openmeteo(payload: dict[str, Any] | list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Desanida la estructura vectorial paralela de Open-Meteo Air Quality (CAMS).

    Maneja tanto respuestas de punto único (dict) como de coordenadas múltiples (list).
    Retorna:
    1. df_celdas: metadatos de las celdas CAMS observadas.
    2. df_observaciones: observaciones atómicas (celda, hora_utc, contaminante, valor, unidad).
    """
    items = payload if isinstance(payload, list) else [payload]

    filas_celdas = []
    filas_observaciones = []

    for item in items:
        # Extraer metadatos de celda
        lat_celda = float(item["latitude"])
        lon_celda = float(item["longitude"])
        elev = float(item.get("elevation", 0.0))
        id_celda = f"celda_{lat_celda:.2f}_{lon_celda:.2f}".replace("-", "m")

        filas_celdas.append({
            "id_celda": id_celda,
            "latitud_celda": lat_celda,
            "longitud_celda": lon_celda,
            "elevacion": elev,
        })

        hourly = item.get("hourly", {})
        times = hourly.get("time", [])
        units = item.get("hourly_units", {})

        pollutants_map = {
            "nitrogen_dioxide": "NO2",
            "pm10": "PM10",
            "pm2_5": "PM2_5",
        }

        # Validación estricta de longitud de arreglos paralelos
        n_tiempos = len(times)
        for var_api in pollutants_map:
            arr = hourly.get(var_api, [])
            if len(arr) != n_tiempos:
                raise ValueError(
                    f"Inconsistencia en Open-Meteo celda {id_celda}: 'time' tiene {n_tiempos} valores "
                    f"pero '{var_api}' tiene {len(arr)} valores."
                )

        # Construir observaciones atómicas
        for idx, t_raw in enumerate(times):
            # Parsear tiempo forzando GMT/UTC
            t_ts = pd.to_datetime(t_raw)
            if t_ts.tz is None:
                t_ts = t_ts.tz_localize("UTC")
            else:
                t_ts = t_ts.tz_convert("UTC")
            t_iso = t_ts.isoformat()

            for var_api, nombre_contaminante in pollutants_map.items():
                val = hourly[var_api][idx]
                unidad = units.get(var_api, "µg/m³")
                filas_observaciones.append({
                    "id_celda": id_celda,
                    "hora_utc": t_iso,
                    "contaminante": nombre_contaminante,
                    "valor": float(val) if val is not None else None,
                    "unidad": unidad,
                })

    df_celdas = pd.DataFrame(filas_celdas).drop_duplicates(subset=["id_celda"])
    df_observaciones = pd.DataFrame(filas_observaciones)

    return df_celdas, df_observaciones
