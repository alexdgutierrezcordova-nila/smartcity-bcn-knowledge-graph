"""Módulo de extracción para CityBikes (Bicing Barcelona) y Open-Meteo Air Quality (CAMS).

Asegura:
1. Almacenamiento en crudo sin modificaciones en sobres de procedencia.
2. Gestión estricta de límites de consulta (CityBikes 300 req/h; Open-Meteo cuotas diarias).
3. Manejo de reintentos con retroceso exponencial.
4. Registro auditable de procedencia (URL, timestamp UTC, HTTP status, recuentos).
"""

from __future__ import annotations

import datetime
import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bcn_kg.extraccion")

CITYBIKES_BICING_URL = "https://api.citybik.es/v2/networks/bicing"
OPENMETEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def envolver_con_procedencia(url: str, http_status: int, payload: Any) -> dict[str, Any]:
    """Empaqueta una respuesta cruda de API en un sobre de procedencia estándar."""
    return {
        "url": url,
        "extraido_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "http_status": http_status,
        "payload": payload,
    }


def extraer_citybikes(
    destino_dir: Path | None = None,
    timeout_segundos: int = 25,
    max_reintentos: int = 3,
) -> dict[str, Any]:
    """Consulta la API de CityBikes para la red Bicing Barcelona.

    Retorna el diccionario con el sobre de procedencia y el payload intacto.
    Si destino_dir se especifica, guarda el archivo JSON crudo con marca temporal.
    """
    url = CITYBIKES_BICING_URL
    ultimo_error: Exception | None = None

    for intento in range(1, max_reintentos + 1):
        try:
            logger.info("Consultando CityBikes Bicing (intento %d/%d)...", intento, max_reintentos)
            resp = requests.get(url, timeout=timeout_segundos)
            resp.raise_for_status()
            datos = resp.json()
            sobre = envolver_con_procedencia(url, resp.status_code, datos)

            if destino_dir is not None:
                destino_dir = Path(destino_dir)
                destino_dir.mkdir(parents=True, exist_ok=True)
                ts_limpio = sobre["extraido_utc"].replace(":", "").replace("-", "")[:15]
                nombre_archivo = f"citybikes_bicing_{ts_limpio}Z.json"
                ruta_salida = destino_dir / nombre_archivo
                with open(ruta_salida, "w", encoding="utf-8") as f:
                    json.dump(sobre, f, ensure_ascii=False, indent=2)
                logger.info("CityBikes guardado exitosamente en: %s", ruta_salida)

            return sobre
        except (requests.RequestException, ValueError) as err:
            logger.warning("Fallo en intento %d de CityBikes: %s", intento, err)
            ultimo_error = err
            if intento < max_reintentos:
                time.sleep(2**intento)

    raise RuntimeError(f"Error irrecuperable extrayendo CityBikes tras {max_reintentos} intentos: {ultimo_error}")


def extraer_openmeteo_celdas(
    coordenadas: list[tuple[float, float]],
    past_days: int = 1,
    forecast_days: int = 1,
    destino_dir: Path | None = None,
    timeout_segundos: int = 30,
    max_reintentos: int = 3,
) -> dict[str, Any]:
    """Consulta la API de Open-Meteo Air Quality para un lote de coordenadas en Barcelona.

    Parámetros forzados según auditoría H4:
    - timezone: GMT (estrictamente UTC)
    - hourly: nitrogen_dioxide, pm10, pm2_5
    - cell_selection: nearest
    """
    if not coordenadas:
        raise ValueError("La lista de coordenadas no puede estar vacía.")

    lats_str = ",".join(f"{lat:.5f}" for lat, _ in coordenadas)
    lons_str = ",".join(f"{lon:.5f}" for _, lon in coordenadas)

    params = {
        "latitude": lats_str,
        "longitude": lons_str,
        "hourly": "nitrogen_dioxide,pm10,pm2_5",
        "timezone": "GMT",
        "cell_selection": "nearest",
        "past_days": past_days,
        "forecast_days": forecast_days,
    }

    url = OPENMETEO_AIR_QUALITY_URL
    ultimo_error: Exception | None = None

    for intento in range(1, max_reintentos + 1):
        try:
            logger.info("Consultando Open-Meteo Air Quality (%d celdas/puntos, intento %d/%d)...", len(coordenadas), intento, max_reintentos)
            resp = requests.get(url, params=params, timeout=timeout_segundos)
            resp.raise_for_status()
            datos = resp.json()
            sobre = envolver_con_procedencia(resp.url, resp.status_code, datos)

            if destino_dir is not None:
                destino_dir = Path(destino_dir)
                destino_dir.mkdir(parents=True, exist_ok=True)
                ts_limpio = sobre["extraido_utc"].replace(":", "").replace("-", "")[:15]
                nombre_archivo = f"openmeteo_cams_{ts_limpio}Z.json"
                ruta_salida = destino_dir / nombre_archivo
                with open(ruta_salida, "w", encoding="utf-8") as f:
                    json.dump(sobre, f, ensure_ascii=False, indent=2)
                logger.info("Open-Meteo guardado exitosamente en: %s", ruta_salida)

            return sobre
        except (requests.RequestException, ValueError) as err:
            logger.warning("Fallo en intento %d de Open-Meteo: %s", intento, err)
            ultimo_error = err
            if intento < max_reintentos:
                time.sleep(2**intento)

    raise RuntimeError(f"Error irrecuperable extrayendo Open-Meteo tras {max_reintentos} intentos: {ultimo_error}")


def registrar_procedencia(
    ruta_registro_csv: Path,
    archivo_raw: str,
    url: str,
    extraido_utc: str,
    http_status: int,
    n_registros: int,
) -> None:
    """Registra una línea de auditoría en procedencia.csv."""
    ruta_registro_csv = Path(ruta_registro_csv)
    ruta_registro_csv.parent.mkdir(parents=True, exist_ok=True)

    encabezado = "archivo_raw,url,extraido_utc,http_status,n_registros\n"
    linea = f'"{archivo_raw}","{url}","{extraido_utc}",{http_status},{n_registros}\n'

    if not ruta_registro_csv.exists():
        with open(ruta_registro_csv, "w", encoding="utf-8") as f:
            f.write(encabezado)
            f.write(linea)
    else:
        with open(ruta_registro_csv, "a", encoding="utf-8") as f:
            f.write(linea)
