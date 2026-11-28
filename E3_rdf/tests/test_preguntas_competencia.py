"""Las 15 preguntas de competencia se responden con SPARQL sobre el grafo generado."""
import sys
from pathlib import Path

import pandas as pd
import pytest
from rdflib import Graph

RAIZ_E3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_E3 / "scripts"))
import generar_rdf as m  # noqa: E402

HORA_H = "2026-11-12T17:00:00+00:00"


@pytest.fixture(scope="module")
def grafo():
    gb, ga = m.ejecutar(limite=0, guardar=False)
    return gb + ga + Graph().parse(m.RUTA_VOCAB)


def consultar(grafo, pc):
    return list(grafo.query((RAIZ_E3 / "sparql" / f"{pc}.rq").read_text(encoding="utf-8")))


@pytest.mark.parametrize("pc", [f"pc{i:02d}" for i in range(1, 16)])
def test_cada_pregunta_se_ejecuta(grafo, pc):
    consultar(grafo, pc)  # no debe lanzar errores de sintaxis ni de evaluación


def test_pc01_coincide_con_los_datos_limpios(grafo):
    estado = pd.read_csv(m.DIR_PROCESADOS / "citybikes_estado.csv")
    assert len(consultar(grafo, "pc01")) == (estado.free_bikes > 10).sum()


def test_pc06_no2_de_la_celda_de_plaza_cataluna(grafo):
    filas = consultar(grafo, "pc06")
    assert [(str(f.celda), float(f.no2)) for f in filas] == [("celda_41.35_2.15", 17.2)]


def test_pc11_integra_ambas_fuentes_igual_que_pandas(grafo):
    estado = pd.read_csv(m.DIR_PROCESADOS / "citybikes_estado.csv")
    enlace = pd.read_csv(m.DIR_PROCESADOS / "enlace_estacion_celda.csv")
    obs = pd.read_csv(m.DIR_PROCESADOS / "cams_observaciones.csv")
    no2 = obs[(obs.contaminante == "NO2") & (obs.hora_utc == HORA_H)][["id_celda", "valor"]]
    esperado = estado[estado.free_bikes >= 5].merge(enlace, on="id_estacion").merge(no2, on="id_celda")
    assert len(consultar(grafo, "pc11")) == (esperado.valor <= 25).sum() > 0


def test_pc14_celda_con_mas_no2_y_sus_estaciones(grafo):
    (fila,) = consultar(grafo, "pc14")
    enlace = pd.read_csv(m.DIR_PROCESADOS / "enlace_estacion_celda.csv")
    assert int(fila.estaciones) == (enlace.id_celda == str(fila.celda)).sum()
