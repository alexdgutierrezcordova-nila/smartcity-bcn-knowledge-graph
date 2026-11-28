"""Script de procesamiento completo: transforma datos crudos JSON en CSV limpios e integrados.

Uso:
    uv run python scripts/procesar_datos.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Añadir src al path
DIR_RAIZ = Path(__file__).resolve().parent.parent
if str(DIR_RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ / "src"))

import pandas as pd
from bcn_kg.limpieza import (
    procesar_raw_citybikes,
    validar_calidad_citybikes,
    desanidar_hourly_openmeteo,
)
from bcn_kg.enlace import (
    enlazar_estaciones_con_celdas,
    enlazar_estado_con_observaciones,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("procesador")


def procesar_todo(dir_raw: Path, dir_processed: Path) -> dict[str, int]:
    dir_raw = Path(dir_raw)
    dir_processed = Path(dir_processed)
    dir_processed.mkdir(parents=True, exist_ok=True)

    archivos_cb = sorted(list((dir_raw / "citybikes").glob("citybikes_bicing_*.json")))
    archivos_om = sorted(list((dir_raw / "openmeteo").glob("openmeteo_cams_*.json")))

    if not archivos_cb:
        raise FileNotFoundError(f"No se encontraron archivos CityBikes en {dir_raw / 'citybikes'}")
    if not archivos_om:
        raise FileNotFoundError(f"No se encontraron archivos Open-Meteo en {dir_raw / 'openmeteo'}")

    logger.info("Procesando %d capturas de CityBikes y %d de Open-Meteo...", len(archivos_cb), len(archivos_om))

    # 1. Procesar CityBikes
    lista_df_est = []
    lista_df_estado = []
    df_operadores = pd.DataFrame()

    for arch in archivos_cb:
        with open(arch, "r", encoding="utf-8") as f:
            sobre = json.load(f)
        df_est, df_estado, df_op = procesar_raw_citybikes(sobre["payload"])
        lista_df_est.append(df_est)
        lista_df_estado.append(df_estado)
        if df_operadores.empty:
            df_operadores = df_op

    # Catálogo estático único de estaciones (último reporte disponible)
    df_estaciones = pd.concat(lista_df_est, ignore_index=True).drop_duplicates(subset=["id_estacion"], keep="last")
    # Estado diacrónico (concatenar todas las observaciones temporales)
    df_estado_total = pd.concat(lista_df_estado, ignore_index=True).drop_duplicates(subset=["id_estacion", "captura_utc"])

    # Validar incidencias de calidad
    df_incidencias = validar_calidad_citybikes(df_estaciones, df_estado_total)

    # 2. Procesar Open-Meteo
    lista_df_celdas = []
    lista_df_obs = []

    for arch in archivos_om:
        with open(arch, "r", encoding="utf-8") as f:
            sobre = json.load(f)
        df_celdas, df_obs = desanidar_hourly_openmeteo(sobre["payload"])
        lista_df_celdas.append(df_celdas)
        lista_df_obs.append(df_obs)

    df_celdas_total = pd.concat(lista_df_celdas, ignore_index=True).drop_duplicates(subset=["id_celda"])
    df_obs_total = pd.concat(lista_df_obs, ignore_index=True).drop_duplicates(subset=["id_celda", "hora_utc", "contaminante"])

    # 3. Enlaces Espacial y Temporal
    df_enlace_esp = enlazar_estaciones_con_celdas(df_estaciones, df_celdas_total)
    df_enlace_temp, metricas_temp = enlazar_estado_con_observaciones(
        df_estado=df_estado_total,
        df_enlace_espacial=df_enlace_esp,
        df_observaciones=df_obs_total,
        tolerancia_minutos=30,
    )

    # 4. Guardar archivos CSV limpios
    rutas_guardado = {
        "citybikes_estaciones.csv": df_estaciones,
        "citybikes_estado.csv": df_estado_total,
        "citybikes_operadores.csv": df_operadores,
        # Celdas, observaciones CAMS y enlace estación–celda los genera
        # E3_rdf/scripts/preprocesar.py con la rejilla CAMS corregida.
        "incidencias_calidad.csv": df_incidencias,
    }

    conteos = {}
    for nombre_csv, df in rutas_guardado.items():
        p = dir_processed / nombre_csv
        df.to_csv(p, index=False, encoding="utf-8")
        conteos[nombre_csv] = len(df)
        logger.info("Guardado %s: %d filas", nombre_csv, len(df))

    logger.info("=== RESUMEN DE ENLACE TEMPORAL ===")
    for k, v in metricas_temp.items():
        logger.info("  %s: %s", k, v)

    return conteos


if __name__ == "__main__":
    dir_base = DIR_RAIZ
    procesar_todo(dir_base.parent / "datos" / "crudos", dir_base.parent / "datos" / "procesados")
