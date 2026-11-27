"""Entregable 3 — Almacenamiento de los datos RDF en GraphDB.

Crea el repositorio `bcn-kg`, importa el vocabulario y los dos archivos RDF
(cada uno en su grafo con nombre) y verifica la carga con las consultas de
E3_rdf/sparql/ (verificación y preguntas de competencia). Los resultados se guardan en E3_rdf/graphdb/.

Requisito: GraphDB en ejecución, por ejemplo con Docker:
    docker run -d --name graphdb-bcn -p 7200:7200 ontotext/graphdb:10.8.5

Uso:
    uv run --no-project python E3_rdf/scripts/cargar_graphdb.py [--url http://localhost:7200]
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REPO = "bcn-kg"
# Un solo grafo: modelo y datos de ambas fuentes comparten grafo y namespace,
# así las estaciones (Bicing) y las celdas (CAMS) quedan conectadas.
GRAFO = "http://example.org/bcn-kg/graph/bcn-kg"
ARCHIVOS = [
    RAIZ / "E3_rdf" / "modelo" / "vocab.ttl",
    RAIZ / "E3_rdf" / "rdf" / "bicing.ttl",
    RAIZ / "E3_rdf" / "rdf" / "calidad_aire.ttl",
]
DIR_SPARQL = RAIZ / "E3_rdf" / "sparql"
DIR_RESULTADOS = RAIZ / "E3_rdf" / "graphdb"

CONFIG_REPO = f"""
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rep: <http://www.openrdf.org/config/repository#> .
@prefix sr: <http://www.openrdf.org/config/repository/sail#> .
@prefix sail: <http://www.openrdf.org/config/sail#> .
@prefix graphdb: <http://www.ontotext.com/config/graphdb#> .

[] a rep:Repository ;
    rep:repositoryID "{REPO}" ;
    rdfs:label "Smart City Barcelona - Bicing y calidad del aire" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;
            graphdb:ruleset "rdfsplus-optimized" ;
            graphdb:base-URL "http://example.org/bcn-kg/data/"
        ]
    ] .
"""


def peticion(url: str, metodo: str = "GET", datos: bytes | None = None,
             cabeceras: dict | None = None) -> bytes:
    req = urllib.request.Request(url, data=datos, method=metodo, headers=cabeceras or {})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def crear_repositorio(base: str) -> None:
    """Crea el repositorio; si ya existe, lo elimina antes para una carga limpia."""
    existentes = json.loads(peticion(f"{base}/rest/repositories", cabeceras={"Accept": "application/json"}))
    if any(r["id"] == REPO for r in existentes):
        peticion(f"{base}/rest/repositories/{REPO}", "DELETE")
    limite = uuid.uuid4().hex
    cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"config\"; filename=\"config.ttl\"\r\n"
              f"Content-Type: text/turtle\r\n\r\n{CONFIG_REPO}\r\n--{limite}--\r\n").encode()
    peticion(f"{base}/rest/repositories", "POST", cuerpo,
             {"Content-Type": f"multipart/form-data; boundary={limite}"})


def importar(base: str) -> None:
    """Sube los archivos Turtle (modelo + ambas fuentes) al mismo grafo."""
    contexto = urllib.parse.quote(f"<{GRAFO}>")
    for ruta in ARCHIVOS:
        peticion(f"{base}/repositories/{REPO}/statements?context={contexto}", "POST",
                 ruta.read_bytes(), {"Content-Type": "text/turtle"})
        print(f"Importado {ruta.relative_to(RAIZ)} -> <{GRAFO}>")


def consultar(base: str, consulta: str) -> list[dict]:
    datos = urllib.parse.urlencode({"query": consulta, "infer": "false"}).encode()
    res = json.loads(peticion(f"{base}/repositories/{REPO}", "POST", datos,
                              {"Content-Type": "application/x-www-form-urlencoded",
                               "Accept": "application/sparql-results+json"}))
    return [{k: v["value"] for k, v in fila.items()} for fila in res["results"]["bindings"]]


def verificar(base: str) -> None:
    """Ejecuta las consultas de verificación y guarda sus resultados en JSON."""
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    rutas = sorted(DIR_SPARQL.glob("0[1235]_*.rq")) + sorted(DIR_SPARQL.glob("pc*.rq"))
    for ruta in rutas:
        filas = consultar(base, ruta.read_text(encoding="utf-8"))
        (DIR_RESULTADOS / f"{ruta.stem}.json").write_text(
            json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{ruta.name}")
        print(f"  {len(filas)} filas")
        for f in filas[:3]:
            print("  " + " | ".join(f.values()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga los datos RDF en GraphDB")
    parser.add_argument("--url", default="http://localhost:7200")
    args = parser.parse_args()
    try:
        crear_repositorio(args.url)
        importar(args.url)
        verificar(args.url)
    except urllib.error.URLError as e:
        raise SystemExit(f"No se pudo conectar con GraphDB en {args.url}: {e}")
