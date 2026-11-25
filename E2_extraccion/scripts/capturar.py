"""Script ejecutable de captura horaria continua para CityBikes y Open-Meteo CAMS.

Uso:
    uv run python scripts/capturar.py --n 19 --intervalo-min 60
    uv run python scripts/capturar.py --una-vez  # Para el piloto o prueba rápida
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Añadir src al path si se ejecuta directamente
DIR_RAIZ = Path(__file__).resolve().parent.parent
if str(DIR_RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ / "src"))

from bcn_kg.extraccion import (
    extraer_citybikes,
    extraer_openmeteo_celdas,
    registrar_procedencia,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("capturador")

# Coordenadas estratégicas que cubren todos los cuadrantes del sistema Bicing en Barcelona
# Open-Meteo (CAMS) mapeará cada una a su centroide de celda oficial (~11 km de resolución)
COORDENADAS_COBERTURA_BCN = [
    (41.3865, 2.1694),  # Centro urbano (Plaza Cataluña / Eixample)
    (41.4055, 2.1623),  # Norte-Centro (Gràcia / Joanic)
    (41.3750, 2.1400),  # Suroeste (Sants / Montjuïc)
    (41.4260, 2.1850),  # Noreste (Sant Andreu / Nou Barris)
    (41.3980, 2.2030),  # Este / Litoral (Poblenou / Sant Martí)
    (41.3800, 2.1900),  # Sureste (Barceloneta / Port Olímpic)
]


def ejecutar_ciclo_captura(
    salida_dir: Path,
    procedencia_csv: Path,
    past_days: int = 1,
    forecast_days: int = 1,
) -> tuple[int, int]:
    """Ejecuta una ronda de captura para ambas APIs y registra su procedencia."""
    dir_citybikes = salida_dir / "citybikes"
    dir_openmeteo = salida_dir / "openmeteo"

    # 1. Captura CityBikes
    logger.info("Iniciando captura de CityBikes Bicing...")
    sobre_cb = extraer_citybikes(destino_dir=dir_citybikes)
    estaciones = sobre_cb["payload"].get("network", {}).get("stations", [])
    n_estaciones = len(estaciones)

    ts_cb = sobre_cb["extraido_utc"].replace(":", "").replace("-", "")[:15]
    archivo_cb = f"citybikes_bicing_{ts_cb}Z.json"
    registrar_procedencia(
        ruta_registro_csv=procedencia_csv,
        archivo_raw=f"data/raw/citybikes/{archivo_cb}",  # relative: no local user paths
        url=sobre_cb["url"],
        extraido_utc=sobre_cb["extraido_utc"],
        http_status=sobre_cb["http_status"],
        n_registros=n_estaciones,
    )
    logger.info("CityBikes capturado: %d estaciones físicas.", n_estaciones)

    # 2. Captura Open-Meteo Air Quality (CAMS)
    logger.info("Iniciando captura de Open-Meteo CAMS...")
    sobre_om = extraer_openmeteo_celdas(
        coordenadas=COORDENADAS_COBERTURA_BCN,
        past_days=past_days,
        forecast_days=forecast_days,
        destino_dir=dir_openmeteo,
    )
    payload_om = sobre_om["payload"]
    items_om = payload_om if isinstance(payload_om, list) else [payload_om]
    total_cortes_om = sum(len(it.get("hourly", {}).get("time", [])) for it in items_om)

    ts_om = sobre_om["extraido_utc"].replace(":", "").replace("-", "")[:15]
    archivo_om = f"openmeteo_cams_{ts_om}Z.json"
    registrar_procedencia(
        ruta_registro_csv=procedencia_csv,
        archivo_raw=f"data/raw/openmeteo/{archivo_om}",  # relative: no local user paths
        url=sobre_om["url"],
        extraido_utc=sobre_om["extraido_utc"],
        http_status=sobre_om["http_status"],
        n_registros=total_cortes_om,
    )
    logger.info("Open-Meteo capturado: %d registros horarios totales en %d puntos/celdas.", total_cortes_om, len(items_om))

    return n_estaciones, total_cortes_om


def main() -> None:
    parser = argparse.ArgumentParser(description="Capturador horario automatizado para Bicing y Open-Meteo.")
    parser.add_argument("--n", type=int, default=19, help="Número de ciclos de captura (por defecto: 19)")
    parser.add_argument("--intervalo-min", type=int, default=60, help="Intervalo en minutos entre capturas (por defecto: 60)")
    parser.add_argument("--past-days", type=int, default=1, help="Días pasados a consultar en Open-Meteo (por defecto: 1)")
    parser.add_argument("--forecast-days", type=int, default=1, help="Días de pronóstico en Open-Meteo (por defecto: 1)")
    parser.add_argument("--salida-dir", type=str, default="data/raw", help="Directorio raíz para JSON crudos")
    parser.add_argument("--procedencia-csv", type=str, default="data/processed/procedencia.csv", help="Ruta para registro de procedencia")
    parser.add_argument("--una-vez", action="store_true", help="Ejecutar una sola captura y salir (modo piloto)")

    args = parser.parse_args()

    salida_dir = (DIR_RAIZ / args.salida_dir).resolve()
    procedencia_csv = (DIR_RAIZ / args.procedencia_csv).resolve()

    logger.info("=== CONFIGURACIÓN DE CAPTURA BCN-KG ===")
    logger.info("Directorio de salida crudos: %s", salida_dir)
    logger.info("Registro de procedencia:     %s", procedencia_csv)
    logger.info("Número de ejecuciones:       %d", 1 if args.una_vez else args.n)
    logger.info("Intervalo entre ciclos:      %d minutos", args.intervalo_min)
    logger.info("========================================")

    total_ciclos = 1 if args.una_vez else args.n

    for ciclo in range(1, total_ciclos + 1):
        t_inicio = time.monotonic()
        logger.info(">>> INICIO DE CICLO %d DE %d <<<", ciclo, total_ciclos)

        try:
            ejecutar_ciclo_captura(
                salida_dir=salida_dir,
                procedencia_csv=procedencia_csv,
                past_days=args.past_days,
                forecast_days=args.forecast_days,
            )
            logger.info(">>> CICLO %d COMPLETADO CON ÉXITO <<<", ciclo)
        except Exception as exc:
            logger.error("Error en ciclo %d: %s. El capturador continuará en el siguiente ciclo.", ciclo, exc, exc_info=True)

        if ciclo < total_ciclos:
            duracion_ciclo = time.monotonic() - t_inicio
            tiempo_espera = max(0.0, (args.intervalo_min * 60.0) - duracion_ciclo)
            logger.info("Esperando %.1f segundos (~%.1f minutos) hasta el siguiente ciclo...", tiempo_espera, tiempo_espera / 60.0)
            try:
                time.sleep(tiempo_espera)
            except KeyboardInterrupt:
                logger.info("Captura interrumpida manualmente por el usuario (KeyboardInterrupt). Finalizando de forma limpia.")
                break

    logger.info("Proceso de captura finalizado. Datos disponibles en: %s", salida_dir)


if __name__ == "__main__":
    main()
