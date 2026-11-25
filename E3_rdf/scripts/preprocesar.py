"""Entregable 3 — Preprocesamiento previo a la generación RDF.

Corrige la identificación de celdas CAMS heredada del Entregable 2.

Problema detectado: Open-Meteo devuelve en `latitude`/`longitude` una coordenada
redondeada (p. ej. 41.4, 2.2) que NO identifica la celda real. En la captura,
5 de los 6 puntos consultados reportan (41.4, 2.2) pero traen 3 series de
contaminantes distintas; E2 los fusionó en una sola celda y descartó 2 series.

Solución: la rejilla CAMS Europa tiene celdas de 0.1° cuyos centros están en
múltiplos de 0.05 (p. ej. 41.35, 2.15). La celda real de un punto se obtiene
con floor(coord * 10) / 10 sobre la coordenada SOLICITADA (la de la URL), y las
estaciones se asignan a su celda por la misma regla (contención exacta).
La función verifica que todos los puntos de una misma celda traigan series
idénticas; si no, falla (la hipótesis de rejilla sería incorrecta).

Salidas en E3_rdf/data/: celdas_cams.csv, observaciones_cams.csv,
enlace_estacion_celda.csv
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DIR_RAW_CAMS = RAIZ / "E2_extraccion" / "data" / "raw" / "openmeteo"
DIR_PROCESADOS = RAIZ / "E2_extraccion" / "data" / "processed"
DIR_SALIDA = RAIZ / "E3_rdf" / "data"

TAMANO_CELDA = 0.1
CONTAMINANTES = {"nitrogen_dioxide": "NO2", "pm10": "PM10", "pm2_5": "PM2_5"}
RADIO_TIERRA_KM = 6371.0088


def celda_de(lat: float, lon: float) -> tuple[str, float, float]:
    """Devuelve (id_celda, lat_centro, lon_centro) de la celda CAMS de 0.1° que contiene el punto."""
    lat0 = math.floor(round(lat / TAMANO_CELDA, 9)) * TAMANO_CELDA
    lon0 = math.floor(round(lon / TAMANO_CELDA, 9)) * TAMANO_CELDA
    lat_c, lon_c = round(lat0 + TAMANO_CELDA / 2, 2), round(lon0 + TAMANO_CELDA / 2, 2)
    return f"celda_{lat_c:.2f}_{lon_c:.2f}", lat_c, lon_c


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(a))


def puntos_solicitados(url: str) -> list[tuple[float, float]]:
    """Extrae las coordenadas pedidas a la API (parámetros latitude/longitude de la URL)."""
    q = parse_qs(urlparse(url).query)
    lats = [float(x) for x in q["latitude"][0].split(",")]
    lons = [float(x) for x in q["longitude"][0].split(",")]
    return list(zip(lats, lons))


def desanidar_cams(ruta_raw: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convierte la captura cruda de Open-Meteo en celdas y observaciones atómicas.

    Agrupa los puntos por celda real y comprueba que sus series coinciden.
    """
    sobre = json.loads(ruta_raw.read_text(encoding="utf-8"))
    items = sobre["payload"] if isinstance(sobre["payload"], list) else [sobre["payload"]]
    puntos = puntos_solicitados(sobre["url"])
    if len(puntos) != len(items):
        raise ValueError(f"{len(puntos)} puntos solicitados pero {len(items)} respuestas")

    series: dict[str, dict] = {}
    celdas: dict[str, dict] = {}
    for (lat, lon), item in zip(puntos, items):
        id_celda, lat_c, lon_c = celda_de(lat, lon)
        serie = {k: item["hourly"][k] for k in ["time", *CONTAMINANTES]}
        if id_celda in series:
            if series[id_celda] != serie:
                raise ValueError(f"Puntos de {id_celda} con series distintas: rejilla incorrecta")
            celdas[id_celda]["puntos_muestreo"] += 1
            continue
        series[id_celda] = serie
        celdas[id_celda] = {"id_celda": id_celda, "latitud_celda": lat_c, "longitud_celda": lon_c,
                            "elevacion": float(item.get("elevation", 0.0)), "puntos_muestreo": 1,
                            "unidad": item.get("hourly_units", {})}

    filas = []
    for id_celda, serie in series.items():
        unidades = celdas[id_celda].pop("unidad")
        for i, t in enumerate(serie["time"]):
            hora = pd.Timestamp(t).tz_localize("UTC").isoformat()
            for var, codigo in CONTAMINANTES.items():
                valor = serie[var][i]
                filas.append({"id_celda": id_celda, "hora_utc": hora, "contaminante": codigo,
                              "valor": None if valor is None else float(valor),
                              "unidad": unidades.get(var, "μg/m³")})
    return pd.DataFrame(list(celdas.values())), pd.DataFrame(filas)


def enlazar_estaciones(estaciones: pd.DataFrame, celdas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Asigna cada estación a la celda que la contiene (misma regla que los puntos CAMS).

    Las celdas que contienen estaciones pero no fueron muestreadas se añaden con
    puntos_muestreo = 0 para que el nodo exista y quede descrito en el grafo.
    """
    filas, nuevas = [], {}
    muestreadas = set(celdas.id_celda)
    for e in estaciones.itertuples():
        id_celda, lat_c, lon_c = celda_de(e.latitud, e.longitud)
        if id_celda not in muestreadas and id_celda not in nuevas:
            nuevas[id_celda] = {"id_celda": id_celda, "latitud_celda": lat_c, "longitud_celda": lon_c,
                                "elevacion": None, "puntos_muestreo": 0}
        filas.append({"id_estacion": e.id_estacion, "id_celda": id_celda,
                      "distancia_centro_km": round(haversine_km(e.latitud, e.longitud, lat_c, lon_c), 4),
                      "celda_con_datos": id_celda in muestreadas})
    todas = pd.concat([celdas, pd.DataFrame(list(nuevas.values()))], ignore_index=True)
    return pd.DataFrame(filas), todas.sort_values("id_celda", ignore_index=True)


def ejecutar(guardar: bool = True) -> dict[str, pd.DataFrame]:
    capturas = sorted(DIR_RAW_CAMS.glob("openmeteo_cams_*.json"))
    partes = [desanidar_cams(r) for r in capturas]
    celdas = pd.concat([p[0] for p in partes]).drop_duplicates("id_celda", keep="last")
    obs = pd.concat([p[1] for p in partes]).drop_duplicates(
        ["id_celda", "hora_utc", "contaminante"], keep="last").dropna(subset=["valor"])
    estaciones = pd.read_csv(DIR_PROCESADOS / "citybikes_estaciones.csv")
    enlace, celdas = enlazar_estaciones(estaciones, celdas)
    salida = {"celdas_cams": celdas, "observaciones_cams": obs.reset_index(drop=True),
              "enlace_estacion_celda": enlace}
    if guardar:
        DIR_SALIDA.mkdir(parents=True, exist_ok=True)
        for nombre, df in salida.items():
            df.to_csv(DIR_SALIDA / f"{nombre}.csv", index=False, encoding="utf-8")
    return salida


if __name__ == "__main__":
    r = ejecutar()
    print(r["celdas_cams"].to_string(index=False))
    print(r["enlace_estacion_celda"].id_celda.value_counts().to_string())
    print(f"observaciones: {len(r['observaciones_cams'])}")
