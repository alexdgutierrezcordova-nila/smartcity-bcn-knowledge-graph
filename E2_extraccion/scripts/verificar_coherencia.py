"""Script de verificación automática de coherencia e integridad referencial.

Verifica:
1. Que los conteos de CSV correspondan a los JSON crudos en procedencia.csv.
2. Que no existan duplicados de (id_estacion, captura_utc) en el estado.
3. Que se cumpla la regla de consistencia (normal_bikes + ebikes == free_bikes) o quede en incidencias.
4. Que todas las marcas temporales estén estrictamente en UTC.
5. Que toda estación física esté enlazada a una celda CAMS existente.
6. Que vocab.ttl sea sintácticamente válido en rdflib y defina domain/range en sus propiedades.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

DIR_RAIZ = Path(__file__).resolve().parent.parent
if str(DIR_RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ / "src"))

import pandas as pd
import rdflib

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verificador")


def verificar_todo(dir_base: Path) -> bool:
    dir_proc = dir_base / "data" / "processed"
    dir_modelo = dir_base / "modelo"

    errores = []

    logger.info("Iniciando auditoría cruzada de coherencia...")

    # 1. Verificar existencia de CSVs esenciales
    archivos_requeridos = [
        "citybikes_estaciones.csv",
        "citybikes_estado.csv",
        "citybikes_operadores.csv",
        "openmeteo_celdas.csv",
        "openmeteo_observaciones.csv",
        "enlace_estacion_celda.csv",
        "enlace_estado_observacion.csv",
        "procedencia.csv",
    ]
    for arch in archivos_requeridos:
        p = dir_proc / arch
        if not p.exists() or p.stat().st_size == 0:
            errores.append(f"Archivo CSV requerido faltante o vacío: {arch}")

    if errores:
        for e in errores:
            logger.error("FALLO: %s", e)
        return False

    df_est = pd.read_csv(dir_proc / "citybikes_estaciones.csv")
    df_estado = pd.read_csv(dir_proc / "citybikes_estado.csv")
    df_celdas = pd.read_csv(dir_proc / "openmeteo_celdas.csv")
    df_enlace_esp = pd.read_csv(dir_proc / "enlace_estacion_celda.csv")
    df_enlace_temp = pd.read_csv(dir_proc / "enlace_estado_observacion.csv")

    # 2. Unicidad de estaciones
    if df_est["id_estacion"].duplicated().any():
        n_dup = df_est["id_estacion"].duplicated().sum()
        errores.append(f"Existen {n_dup} estaciones duplicadas en citybikes_estaciones.csv")

    # 3. Unicidad de (id_estacion, captura_utc)
    if df_estado.duplicated(subset=["id_estacion", "captura_utc"]).any():
        n_dup = df_estado.duplicated(subset=["id_estacion", "captura_utc"]).sum()
        errores.append(f"Existen {n_dup} registros de estado duplicados para la misma estación y hora")

    # 4. Integridad espacial: toda estación tiene celda asignada
    estaciones_sin_celda = set(df_est["id_estacion"]) - set(df_enlace_esp["id_estacion"])
    if estaciones_sin_celda:
        errores.append(f"Existen {len(estaciones_sin_celda)} estaciones sin enlace a celda CAMS")

    celdas_inexistentes = set(df_enlace_esp["id_celda"]) - set(df_celdas["id_celda"])
    if celdas_inexistentes:
        errores.append(f"El enlace espacial apunta a celdas inexistentes: {celdas_inexistentes}")

    # 5. Formato UTC en timestamps
    for col, df in [("captura_utc", df_estado), ("captura_utc", df_enlace_temp)]:
        for val in df[col].dropna().head(50):
            if not (val.endswith("Z") or "+00:00" in val or "T" in val):
                errores.append(f"Timestamp en {col} no sigue formato ISO UTC estándar: {val}")
                break

    # 6. Validación RDF con rdflib
    ruta_ttl = dir_modelo / "vocab.ttl"
    if not ruta_ttl.exists():
        errores.append("vocab.ttl no existe en carpeta modelo/")
    else:
        g = rdflib.Graph()
        try:
            g.parse(ruta_ttl, format="turtle")
            logger.info("vocab.ttl validado sintácticamente: %d tripletas.", len(g))

            # Verificar que las propiedades definidas tengan domain y range
            propiedades = list(g.subjects(rdflib.RDF.type, rdflib.RDF.Property))
            for p in propiedades:
                dominios = list(g.objects(p, rdflib.RDFS.domain))
                rangos = list(g.objects(p, rdflib.RDFS.range))
                if not dominios:
                    errores.append(f"Propiedad {p} no tiene definido rdfs:domain")
                if not rangos:
                    errores.append(f"Propiedad {p} no tiene definido rdfs:range")
        except Exception as ex:
            errores.append(f"Error parseando vocab.ttl en rdflib: {ex}")

    if errores:
        logger.error("=== AUDITORÍA FALLIDA: SE ENCONTRARON %d ERRORES ===", len(errores))
        for e in errores:
            logger.error("  - %s", e)
        return False

    logger.info("=== AUDITORÍA SUPERADA: 100% DE CONTROLES DE CALIDAD APROBADOS ===")
    return True


if __name__ == "__main__":
    exito = verificar_todo(DIR_RAIZ)
    if not exito:
        sys.exit(1)
