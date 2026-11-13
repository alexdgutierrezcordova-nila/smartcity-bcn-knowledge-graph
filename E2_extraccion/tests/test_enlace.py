"""Pruebas unitarias para bcn_kg.enlace."""

import pytest
import pandas as pd
from bcn_kg.enlace import (
    haversine_km,
    enlazar_estaciones_con_celdas,
    enlazar_estado_con_observaciones,
)


def test_haversine_conocido():
    # Coordenadas: Plaza Cataluña a Plaza Joanic (~2.18 km)
    lat1, lon1 = 41.3865, 2.1694
    lat2, lon2 = 41.4055, 2.1623
    distancia = haversine_km(lat1, lon1, lat2, lon2)

    assert 2.0 < distancia < 2.3
    # Distancia al mismo punto debe ser 0.0
    assert haversine_km(lat1, lon1, lat1, lon1) == 0.0


def test_enlazar_estaciones_con_celdas():
    df_est = pd.DataFrame([
        {"id_estacion": "est_1", "latitud": 41.4055, "longitud": 2.1623},
        {"id_estacion": "est_2", "latitud": 41.3865, "longitud": 2.1694},
    ])

    df_celdas = pd.DataFrame([
        {"id_celda": "celda_41.40_2.20", "latitud_celda": 41.40, "longitud_celda": 2.20},
        {"id_celda": "celda_41.30_2.10", "latitud_celda": 41.30, "longitud_celda": 2.10},
    ])

    df_enlace = enlazar_estaciones_con_celdas(df_est, df_celdas)

    assert len(df_enlace) == 2
    # Ambas estaciones en el norte/centro de BCN deben asignarse a la celda 41.40_2.20
    assert df_enlace.loc[0, "id_celda"] == "celda_41.40_2.20"
    assert df_enlace.loc[1, "id_celda"] == "celda_41.40_2.20"
    assert df_enlace.loc[0, "distancia_centro_km"] > 0.0


def test_enlazar_estado_con_observaciones_tolerancia():
    df_estado = pd.DataFrame([
        {
            "id_estacion": "est_1",
            "captura_utc": "2026-10-25T16:55:00+00:00",
            "free_bikes": 5,
            "empty_slots": 10,
            "ebikes": 2,
        },
        {
            "id_estacion": "est_1",
            "captura_utc": "2026-10-25T18:45:00+00:00",  # Desfase de 45 min vs 18:00 o 19:00 (> 30 min)
            "free_bikes": 3,
            "empty_slots": 12,
            "ebikes": 1,
        },
    ])

    df_enlace_esp = pd.DataFrame([
        {"id_estacion": "est_1", "id_celda": "celda_41.40_2.20"},
    ])

    df_obs = pd.DataFrame([
        {"id_celda": "celda_41.40_2.20", "hora_utc": "2026-10-25T17:00:00+00:00", "contaminante": "NO2", "valor": 45.0},
        {"id_celda": "celda_41.40_2.20", "hora_utc": "2026-10-25T17:00:00+00:00", "contaminante": "PM10", "valor": 20.0},
        {"id_celda": "celda_41.40_2.20", "hora_utc": "2026-10-25T17:00:00+00:00", "contaminante": "PM2_5", "valor": 12.0},
    ])

    df_cruce, metricas = enlazar_estado_con_observaciones(
        df_estado, df_enlace_esp, df_obs, tolerancia_minutos=30
    )

    # Solo el primer registro (16:55 vs 17:00 -> delta = 5 min <= 30) debe emparejarse
    assert len(df_cruce) == 1
    assert metricas["emparejados"] == 1
    assert metricas["sin_emparejar"] == 1
    assert df_cruce.iloc[0]["delta_minutos"] == 5.0
    assert df_cruce.iloc[0]["no2"] == 45.0
