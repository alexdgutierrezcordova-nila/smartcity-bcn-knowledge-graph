"""Entregable 3 — Almacenamiento de los datos RDF en GraphDB.

Crea el repositorio `bcn-kg`, importa el vocabulario y los tres archivos RDF
en UN solo grafo y verifica la carga con las consultas de E3_rdf/sparql/
(verificación, integración y preguntas de competencia). Los resultados se guardan
en E3_rdf/graphdb/ (JSON) y la tabla de integración también en CSV.

Requisito: GraphDB en ejecución. Desde la raíz del repositorio:
    docker compose up -d

Uso:
    uv run --no-project python E3_rdf/scripts/cargar_graphdb.py [--url http://localhost:7200]
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REPO = "bcn-kg"
# Un solo grafo: modelo y datos de las tres fuentes comparten grafo y namespace,
# así estaciones (Bicing), barrios (Open Data BCN) y celdas (CAMS) quedan conectados.
GRAFO = "http://example.org/bcn-kg/graph/bcn-kg"
ARCHIVOS = [
    RAIZ / "E3_rdf" / "modelo" / "vocab.ttl",
    RAIZ / "E3_rdf" / "rdf" / "bicing.ttl",
    RAIZ / "E3_rdf" / "rdf" / "calidad_aire.ttl",
    RAIZ / "E3_rdf" / "rdf" / "barrios.ttl",
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
    rdfs:label "Smart City Barcelona - Bicing, barrios y calidad del aire" ;
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


def esperar_graphdb(base: str, segundos: int = 180) -> None:
    """GraphDB tarda unos 30 s en arrancar: reintenta hasta que responda."""
    limite = time.monotonic() + segundos
    while True:
        try:
            peticion(f"{base}/rest/repositories")
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if time.monotonic() > limite:
                raise
            print("  esperando a GraphDB...")
            time.sleep(5)


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
    """Sube los archivos Turtle (modelo + las tres fuentes) al mismo grafo."""
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
    # 04 es un CONSTRUCT para el grafo visual: se abre en el Workbench, no se tabula.
    rutas = [r for r in sorted(DIR_SPARQL.glob("0*.rq")) if not r.name.startswith("04_")]
    for ruta in rutas + sorted(DIR_SPARQL.glob("pc*.rq")):
        filas = consultar(base, ruta.read_text(encoding="utf-8"))
        (DIR_RESULTADOS / f"{ruta.stem}.json").write_text(
            json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
        if ruta.name.startswith("06_"):
            exportar_csv(filas, DIR_RESULTADOS / "integracion_movilidad_aire.csv")
        print(f"\n{ruta.name}")
        print(f"  {len(filas)} filas")
        for f in filas[:3]:
            print("  " + " | ".join(f.values()))


def exportar_csv(filas: list[dict], ruta: Path) -> None:
    """Tabla de evidencia: exporta el resultado de la consulta tal cual sale del grafo."""
    columnas = ["estacion", "barrio", "distrito", "bicicletas", "anclajes", "celda", "no2", "pm10", "pm25"]
    with ruta.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows({c: fila.get(c, "") for c in columnas} for fila in filas)


def nombre_consulta(ruta: Path) -> str:
    """Nombre visible en GraphDB: código del archivo + su primera línea de comentario."""
    titulo = ruta.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
    if ruta.stem.startswith("pc"):
        # «PC1 · pregunta» → «PC01 · pregunta», para que el Workbench las ordene bien
        return f"PC{ruta.stem[2:]} · {titulo.split('·', 1)[1].strip()}"
    return f"{ruta.stem[:2]} · {titulo}"


def guardar_consultas(base: str) -> None:
    """Registra cada .rq como consulta guardada del Workbench (SPARQL → carpeta de consultas guardadas)."""
    url = f"{base}/rest/sparql/saved-queries"
    vigentes = {nombre_consulta(r) for r in DIR_SPARQL.glob("*.rq")}
    for previa in json.loads(peticion(url, cabeceras={"Accept": "application/json"})):
        # elimina consultas de versiones anteriores del proyecto (nombres «0x · …» o «PCxx · …»)
        if previa["name"] not in vigentes and previa["name"][:2] in {"01", "02", "03", "04", "05", "06", "07", "PC"}:
            peticion(f"{url}?name={urllib.parse.quote(previa['name'])}", "DELETE")
    for ruta in sorted(DIR_SPARQL.glob("*.rq")):
        nombre = nombre_consulta(ruta)
        try:  # reemplaza la versión anterior si ya existía
            peticion(f"{url}?name={urllib.parse.quote(nombre)}", "DELETE")
        except urllib.error.HTTPError:
            pass
        cuerpo = json.dumps({"name": nombre, "body": ruta.read_text(encoding="utf-8"), "shared": True}).encode()
        peticion(url, "POST", cuerpo, {"Content-Type": "application/json"})
    print(f"\n{len(list(DIR_SPARQL.glob('*.rq')))} consultas guardadas en el Workbench")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga los datos RDF en GraphDB")
    parser.add_argument("--url", default="http://localhost:7200")
    args = parser.parse_args()
    try:
        esperar_graphdb(args.url)
        crear_repositorio(args.url)
        importar(args.url)
        verificar(args.url)
        guardar_consultas(args.url)
    except urllib.error.URLError as e:
        raise SystemExit(f"No se pudo conectar con GraphDB en {args.url} ({e}). "
                         "¿Está abierto Docker? Ejecutar: docker compose up -d")
