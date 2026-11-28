import sys
from pathlib import Path

from rdflib import RDF, Graph, Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generar_rdf as m  # noqa: E402


def test_normalizar_quita_tildes_espacios_y_simbolos():
    assert m.normalizar("Universidad Autónoma de Madrid") == "Universidad_Autonoma_de_Madrid"
    assert m.normalizar("PL  JOANIC - C / BRUNIQUER, 59") == "PL_JOANIC_-_C_BRUNIQUER_59"


def test_celdas_enlazan_ambas_fuentes_con_la_misma_uri():
    gb, ga, _ = m.ejecutar(limite=0, guardar=False)
    celdas_aire = set(ga.subjects(RDF.type, m.VOCAB.CeldaModelo))
    celdas_bicing = {o for o in gb.objects(None, m.SCHEMA.containedInPlace) if o in celdas_aire}
    assert celdas_bicing == celdas_aire


def test_contaminantes_tienen_unidad_y_vocab_sin_datos():
    vocab = Graph().parse(m.RUTA_VOCAB)
    assert not list(vocab.subjects(RDF.type, m.VOCAB.Contaminante))  # sin datos en el TBox
    _, ga, _ = m.ejecutar(limite=2, guardar=False)
    for c in ga.subjects(RDF.type, m.VOCAB.Contaminante):
        assert ga.value(c, m.SCHEMA.unitText) is not None


def test_modelo_v3_una_sola_relacion_por_vinculo():
    """Corrección 27/11: sin subpropiedades propias (contenidaEnCelda, perteneceARed...)."""
    vocab = Graph().parse(m.RUTA_VOCAB)
    assert not list(vocab.subject_objects(m.RDFS.subPropertyOf))
    gb, ga, gz = m.ejecutar(limite=0, guardar=False)
    g = gb + ga + gz
    usadas = {p for p in g.predicates() if str(p).startswith(str(m.VOCAB))}
    assert usadas <= {m.VOCAB[x] for x in ("bicicletasDisponibles", "anclajesLibres", "bicicletasMecanicas",
                                           "bicicletasElectricas", "enLinea", "distanciaACeldaModeloKm")}


def test_lo_dinamico_es_schema_observation():
    """Corrección E2: EstadoEstacion se reemplaza por schema:Observation."""
    gb, ga, _ = m.ejecutar(limite=0, guardar=False)
    estados = set(gb.subjects(RDF.type, m.SCHEMA.Observation))
    medidas = set(ga.subjects(RDF.type, m.SCHEMA.Observation))
    assert len(estados) == 542 and len(medidas) == 432
    assert all(gb.value(e, m.SCHEMA.observationAbout) for e in estados)
    assert all(ga.value(o, m.SCHEMA.observationAbout) and ga.value(o, m.SCHEMA.value) for o in medidas)
    assert not list((gb + ga).subjects(RDF.type, m.VOCAB.EstadoEstacion))


def test_estacion_barrio_distrito_barcelona():
    """Corrección 27/11: estación → barrio → distrito → Barcelona con schema:containedInPlace."""
    gb, _, gz = m.ejecutar(limite=0, guardar=False)
    g = gb + gz
    barrios = set(g.subjects(RDF.type, m.VOCAB.Barrio))
    distritos = set(g.subjects(RDF.type, m.VOCAB.Distrito))
    assert len(barrios) == 73 and len(distritos) == 10
    for e in g.subjects(RDF.type, m.VOCAB.EstacionBicicleta):
        (barrio,) = [o for o in g.objects(e, m.SCHEMA.containedInPlace) if o in barrios]
        distrito = g.value(barrio, m.SCHEMA.containedInPlace)
        assert distrito in distritos
        assert g.value(distrito, m.SCHEMA.containedInPlace) == m.uri_ciudad()


def test_todas_las_instancias_tienen_rdfs_label():
    gb, ga, gz = m.ejecutar(limite=0, guardar=False)
    g = gb + ga + gz
    sujetos = {s for s in g.subjects(RDF.type, None)}
    assert all(g.value(s, m.RDFS.label) for s in sujetos)
    assert str(g.value(m.uri_red(), m.RDFS.label)) == "Red Bicing (Barcelona)"


def test_validar_detecta_rango_incorrecto_y_nodo_sin_describir():
    vocab = Graph().parse(m.RUTA_VOCAB)
    g = Graph()
    e = m.DATA["estacion_x"]
    g.add((e, RDF.type, m.VOCAB.EstacionBicicleta))
    g.add((e, m.VOCAB.distanciaACeldaModeloKm, Literal("lejos")))
    g.add((e, m.SCHEMA.containedInPlace, m.DATA["celda_inexistente"]))
    errores = m.validar(g, vocab)
    assert any(x.startswith("rango") for x in errores)
    assert any(x.startswith("nodo sin describir") for x in errores)


def test_datos_completos_sin_errores():
    gb, ga, gz = m.ejecutar(limite=0, guardar=False)
    assert m.validar(gb + ga + gz, Graph().parse(m.RUTA_VOCAB)) == []


import preprocesar as pre  # noqa: E402


def test_celda_de_usa_rejilla_cams_de_01_grados():
    assert pre.celda_de(41.3865, 2.1694)[0] == "celda_41.35_2.15"
    assert pre.celda_de(41.4055, 2.1623)[0] == "celda_41.45_2.15"
    assert pre.celda_de(41.398, 2.203)[0] == "celda_41.35_2.25"


def test_preprocesar_conserva_las_tres_series_distintas():
    r = pre.ejecutar(guardar=False)
    no2 = r["cams_observaciones"].query("contaminante == 'NO2'")
    primeras = no2.sort_values("hora_utc").groupby("id_celda").valor.first()
    assert primeras.nunique() == 3  # E2 las había fusionado en una sola
    assert len(r["enlace_estacion_celda"]) == 542


def test_preprocesar_ubica_cada_estacion_en_un_barrio():
    r = pre.ejecutar(guardar=False)
    eb = r["enlace_estacion_barrio"]
    assert len(eb) == 542 and eb.id_barrio.isin(r["bcn_barrios"].id_barrio).all()
    assert len(r["bcn_barrios"]) == 73 and len(r["bcn_distritos"]) == 10


def test_punto_en_poligono():
    cuadrado = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
    assert pre.dentro(0.5, 0.5, cuadrado) and not pre.dentro(1.5, 0.5, cuadrado)
    assert pre.poligonos_wkt("MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)), ((2 2, 3 2, 3 3, 2 2)))")[1][0] == (2.0, 2.0)
