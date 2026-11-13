"""Módulo de enlace geoespacial (WGS84 / Haversine / CAMS) y temporal (UTC ISO 8601).

Implementa la corrección de los hallazgos:
- H6: Superación del radio rígido de 1 km. Enlace por pertenencia a celda CAMS
      (resolución ~11 km) con métrica continua de distancia geodésica al centroide.
- H4: Sincronización temporal en UTC con tolerancia explícita y auditoría de delta.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

RADIO_TIERRA_WGS84_KM = 6371.0088
SEMIDIAGONAL_MAXIMA_CELDA_KM = 6.95  # Semidiagonal teórica de una celda de 0.1° a ~41.4° Lat


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float, r: float = RADIO_TIERRA_WGS84_KM) -> float:
    """Calcula la distancia geodésica exacta en kilómetros entre dos coordenadas WGS84."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def enlazar_estaciones_con_celdas(
    df_estaciones: pd.DataFrame,
    df_celdas: pd.DataFrame,
) -> pd.DataFrame:
    """Asocia cada estación de bicicletas a la celda CAMS más cercana/contenedora.

    Calcula la distancia en kilómetros al centroide de la celda y evalúa
    si excede la semidiagonal teórica de la grilla.
    """
    enlaces = []

    for _, est in df_estaciones.iterrows():
        lat_est = est["latitud"]
        lon_est = est["longitud"]

        if lat_est is None or lon_est is None:
            continue

        mejor_celda: str | None = None
        menor_distancia = float("inf")

        for _, celda in df_celdas.iterrows():
            d = haversine_km(lat_est, lon_est, celda["latitud_celda"], celda["longitud_celda"])
            if d < menor_distancia:
                menor_distancia = d
                mejor_celda = celda["id_celda"]

        enlaces.append({
            "id_estacion": est["id_estacion"],
            "id_celda": mejor_celda,
            "distancia_centro_km": round(menor_distancia, 4),
            "alerta_distancia": menor_distancia > SEMIDIAGONAL_MAXIMA_CELDA_KM,
        })

    return pd.DataFrame(enlaces)


def enlazar_estado_con_observaciones(
    df_estado: pd.DataFrame,
    df_enlace_espacial: pd.DataFrame,
    df_observaciones: pd.DataFrame,
    tolerancia_minutos: int = 30,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Enlaza cada registro de estado de estación con la observación ambiental de su celda.

    Busca el corte horario más cercano en UTC (|delta_min| <= tolerancia_minutos).
    Retorna:
    - df_enlace_temporal: tabla con el cruce integrado.
    - metricas_enlace: diccionario con tasa de éxito, delta medio y registros sin par.
    """
    # 1. Unir estado con su celda correspondiente
    df_est_celda = df_estado.merge(
        df_enlace_espacial[["id_estacion", "id_celda"]],
        on="id_estacion",
        how="inner",
    )

    # Convertir a datetime para operaciones temporales
    df_est_celda["dt_captura"] = pd.to_datetime(df_est_celda["captura_utc"])
    df_obs = df_observaciones.copy()
    df_obs["dt_hora"] = pd.to_datetime(df_obs["hora_utc"])

    # 2. Realizar cruce temporal por celda buscando la hora más cercana
    filas_cruce = []
    total_estados = len(df_est_celda)
    emparejados = 0

    # Agrupar observaciones por celda y hora para búsqueda eficiente
    obs_pivot = df_obs.pivot_table(
        index=["id_celda", "dt_hora"],
        columns="contaminante",
        values="valor",
    ).reset_index()

    for _, fila in df_est_celda.iterrows():
        id_celda = fila["id_celda"]
        t_captura = fila["dt_captura"]

        # Filtrar observaciones de la celda
        obs_celda = obs_pivot[obs_pivot["id_celda"] == id_celda]
        if obs_celda.empty:
            continue

        # Calcular diferencia absoluta en minutos
        deltas = (obs_celda["dt_hora"] - t_captura).abs().dt.total_seconds() / 60.0
        idx_min = deltas.idxmin()
        delta_min = deltas.loc[idx_min]

        if delta_min <= tolerancia_minutos:
            emparejados += 1
            obs_match = obs_celda.loc[idx_min]
            filas_cruce.append({
                "id_estacion": fila["id_estacion"],
                "captura_utc": fila["captura_utc"],
                "id_celda": id_celda,
                "hora_utc": obs_match["dt_hora"].isoformat(),
                "delta_minutos": round(delta_min, 2),
                "free_bikes": fila["free_bikes"],
                "empty_slots": fila["empty_slots"],
                "ebikes": fila["ebikes"],
                "no2": obs_match.get("NO2"),
                "pm10": obs_match.get("PM10"),
                "pm2_5": obs_match.get("PM2_5"),
            })

    df_resultado = pd.DataFrame(filas_cruce)

    metricas = {
        "total_estados": total_estados,
        "emparejados": emparejados,
        "tasa_enlace_pct": round((emparejados / total_estados * 100.0), 2) if total_estados > 0 else 0.0,
        "sin_emparejar": total_estados - emparejados,
        "tolerancia_minutos": tolerancia_minutos,
        "delta_promedio_minutos": round(df_resultado["delta_minutos"].mean(), 2) if not df_resultado.empty else 0.0,
    }

    return df_resultado, metricas
