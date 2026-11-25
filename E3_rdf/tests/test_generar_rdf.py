import sys
from pathlib import Path

from rdflib import RDF, Graph, Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generar_rdf as m  # noqa: E402


def test_normalizar_quita_tildes_espacios_y_simbolos():
    assert m.normalizar("Universidad Autónoma de Madrid") == "Universidad_Autonoma_de_Madrid"
    assert m.normalizar("PL  JOANIC - C / BRUNIQUER, 59") == "PL_JOANIC_-_C_BRUNIQUER_59"


def test_celdas_enlazan_ambas_fuentes_con_la_misma_uri():
    gb, ga = m.ejecutar(limite=0, guardar=False)
    celdas_bicing = set(gb.objects(None, m.VOCAB.contenidaEnCelda))
    celdas_aire = set(ga.subjects(RDF.type, m.VOCAB.CeldaModelo))
    assert celdas_bicing and celdas_bicing <= celdas_aire


def test_contaminantes_coinciden_con_instancias_de_vocab():
    _, ga = m.ejecutar(limite=2, guardar=False)
    vocab = Graph().parse(m.RUTA_VOCAB)
    usados = set(ga.subjects(RDF.type, m.VOCAB.Contaminante))
    assert usados <= set(vocab.subjects(RDF.type, m.VOCAB.Contaminante))


def test_validar_detecta_rango_incorrecto_y_nodo_sin_describir():
    vocab = Graph().parse(m.RUTA_VOCAB)
    g = Graph()
    e = m.DATA["estacion_x"]
    g.add((e, RDF.type, m.VOCAB.EstacionBicicleta))
    g.add((e, m.VOCAB.distanciaACentroideKm, Literal("lejos")))
    g.add((e, m.VOCAB.contenidaEnCelda, m.DATA["celda_inexistente"]))
    errores = m.validar(g, vocab)
    assert any(x.startswith("rango") for x in errores)
    assert any(x.startswith("nodo sin describir") for x in errores)


def test_datos_completos_sin_errores():
    gb, ga = m.ejecutar(limite=0, guardar=False)
    assert m.validar(gb + ga, Graph().parse(m.RUTA_VOCAB)) == []


import preprocesar as pre  # noqa: E402


def test_celda_de_usa_rejilla_cams_de_01_grados():
    assert pre.celda_de(41.3865, 2.1694)[0] == "celda_41.35_2.15"
    assert pre.celda_de(41.4055, 2.1623)[0] == "celda_41.45_2.15"
    assert pre.celda_de(41.398, 2.203)[0] == "celda_41.35_2.25"


def test_preprocesar_conserva_las_tres_series_distintas():
    r = pre.ejecutar(guardar=False)
    no2 = r["observaciones_cams"].query("contaminante == 'NO2'")
    primeras = no2.sort_values("hora_utc").groupby("id_celda").valor.first()
    assert primeras.nunique() == 3  # E2 las había fusionado en una sola
    assert len(r["enlace_estacion_celda"]) == 542
