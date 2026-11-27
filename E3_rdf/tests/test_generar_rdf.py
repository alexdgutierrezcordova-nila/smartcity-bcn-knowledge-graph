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


def test_vocab_v2_solo_define_el_modelo_y_contaminantes_tienen_unidad():
    vocab = Graph().parse(m.RUTA_VOCAB)
    assert not list(vocab.subjects(RDF.type, m.VOCAB.Contaminante))  # sin datos en el TBox
    _, ga = m.ejecutar(limite=2, guardar=False)
    for c in ga.subjects(RDF.type, m.VOCAB.Contaminante):
        assert ga.value(c, m.SCHEMA.unitText) is not None


def test_modelo_v2_sin_terminos_redundantes():
    gb, ga = m.ejecutar(limite=0, guardar=False)
    g = gb + ga
    assert not list(g.triples((None, m.VOCAB.tieneEstado, None)))
    assert not list(g.subjects(RDF.type, m.SCHEMA.QuantitativeValue))
    # Los estados llegan a su estación solo con sosa:hasFeatureOfInterest
    estados = set(g.subjects(RDF.type, m.VOCAB.EstadoEstacion))
    assert all(g.value(e, m.SOSA.hasFeatureOfInterest) for e in estados)


def test_validar_detecta_rango_incorrecto_y_nodo_sin_describir():
    vocab = Graph().parse(m.RUTA_VOCAB)
    g = Graph()
    e = m.DATA["estacion_x"]
    g.add((e, RDF.type, m.VOCAB.EstacionBicicleta))
    g.add((e, m.VOCAB.distanciaACeldaModeloKm, Literal("lejos")))
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
