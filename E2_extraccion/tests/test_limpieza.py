"""Pruebas unitarias para bcn_kg.limpieza."""

import pytest
import pandas as pd
from bcn_kg.limpieza import (
    normalizar_texto,
    parsear_ts_citybikes,
    procesar_raw_citybikes,
    validar_calidad_citybikes,
    desanidar_hourly_openmeteo,
)


def test_normalizar_texto_espacios_y_mayusculas():
    caso_e1 = "  PL JOANIC - C /   BRUNIQUER, 59  "
    esperado = "PL JOANIC - C / BRUNIQUER, 59"
    assert normalizar_texto(caso_e1) == esperado
    assert normalizar_texto(None) is None
    assert normalizar_texto("") is None


def test_parsear_ts_citybikes_bug_h3():
    # Caso real extraído de la captura del E1 con defecto '+00:00Z'
    ts_malformado = "2026-10-25T16:55:24.292784+00:00Z"
    ts = parsear_ts_citybikes(ts_malformado)
    assert ts is not None
    assert ts.year == 2026
    assert ts.month == 10
    assert ts.day == 25
    assert ts.hour == 16
    assert ts.minute == 55
    assert str(ts.tz) == "UTC"


def test_procesar_raw_citybikes_y_validar_calidad():
    payload_mock = {
        "network": {
            "id": "bicing",
            "company": ["BSM", "CESPA"],
            "stations": [
                {
                    "id": "est_1",
                    "name": " C/ SARDENYA, 178 ",
                    "latitude": 41.3967,
                    "longitude": 2.1825,
                    "timestamp": "2026-10-25T16:55:24.292740+00:00Z",
                    "free_bikes": 17,
                    "empty_slots": 15,
                    "extra": {
                        "uid": "119",
                        "online": True,
                        "normal_bikes": 10,
                        "ebikes": 7,  # 10 + 7 == 17 (Consistente)
                    },
                },
                {
                    "id": "est_inconsistente",
                    "name": "ESTACION FALLIDA",
                    "latitude": 45.0000,  # Fuera de Barcelona
                    "longitude": 2.1825,
                    "timestamp": "2026-10-25T16:55:24.000000Z",
                    "free_bikes": 10,
                    "empty_slots": 5,
                    "extra": {
                        "uid": "999",
                        "online": True,
                        "normal_bikes": 2,
                        "ebikes": 3,  # 2 + 3 = 5 != 10 (Inconsistente)
                    },
                },
            ],
        }
    }

    df_est, df_estado, df_op = procesar_raw_citybikes(payload_mock)

    assert len(df_est) == 2
    assert len(df_estado) == 2
    assert len(df_op) == 2
    assert df_est.loc[0, "nombre_limpio"] == "C/ SARDENYA, 178"

    incidencias = validar_calidad_citybikes(df_est, df_estado)
    assert len(incidencias) >= 2
    # Debe haber detectado la coordenada fuera de rango y la discrepancia de suma
    reglas = incidencias["regla"].tolist()
    assert any("Bounding Box" in r for r in reglas)
    assert any("Discrepancia suma" in r for r in reglas)


def test_desanidar_hourly_openmeteo():
    payload_mock = {
        "latitude": 41.4,
        "longitude": 2.2,
        "elevation": 44.0,
        "hourly_units": {
            "nitrogen_dioxide": "µg/m³",
            "pm10": "µg/m³",
            "pm2_5": "µg/m³",
        },
        "hourly": {
            "time": ["2026-10-25T00:00", "2026-10-25T01:00"],
            "nitrogen_dioxide": [71.3, 65.0],
            "pm10": [22.0, 20.5],
            "pm2_5": [14.1, 13.0],
        },
    }

    df_celdas, df_obs = desanidar_hourly_openmeteo(payload_mock)
    assert len(df_celdas) == 1
    assert df_celdas.iloc[0]["id_celda"] == "celda_41.40_2.20"
    assert len(df_obs) == 6  # 2 horas * 3 contaminantes

    # Probar que falla si las longitudes de arreglos son asimétricas
    payload_invalido = dict(payload_mock)
    payload_invalido["hourly"] = dict(payload_mock["hourly"])
    payload_invalido["hourly"]["nitrogen_dioxide"] = [71.3]  # Solo 1 elemento frente a 2

    with pytest.raises(ValueError, match="Inconsistencia en Open-Meteo"):
        desanidar_hourly_openmeteo(payload_invalido)
