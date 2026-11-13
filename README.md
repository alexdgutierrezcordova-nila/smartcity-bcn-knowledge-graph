# Smart City Barcelona: Knowledge Graph & Heterogeneous Data Pipeline (LOD)

> **Universidad Técnica Particular de Loja (UTPL)**  
> **Asignatura:** Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos  
> **Docente:** Dra. Janneth Alexandra Chicaiza Espinosa  
> **Autores:** Alex Gutiérrez, David Emanuel Toa  
> **Periodo:** Noviembre 2026  

---

## 📌 Descripción del Proyecto

Este repositorio contiene la arquitectura, pipeline ETL, modelo ontológico (RDF / RDFS / OWL / SOSA) y análisis de interoperabilidad para la integración semántica de dos ecosistemas heterogéneos de datos abiertos en la ciudad de **Barcelona, España**:

1. **Movilidad Urbana Sostenible:** Red pública de bicicletas compartidas (Bicing) consumida en tiempo real vía API REST de CityBikes.
2. **Medio Ambiente y Salud:** Concentraciones horarias de contaminantes atmosféricos ($NO_2$, $PM_{10}$, $PM_{2.5}$) obtenidas del modelo de dispersión regional europeo Copernicus Atmosphere Monitoring Service (**CAMS**) vía API REST de Open-Meteo.

---

## 🏗️ Estructura del Repositorio

```text
Proyecto General/
├── Clases/                      # Apuntes y transcripciones de las cátedras universitarias
├── E1_correccion/               # Documento base corregido del Entregable 1 (auditoría técnica)
│   └── E1_base_corregida.md     # Fichas técnicas, matriz de 15 PC y estrategia de enlace
├── E2_extraccion/               # Entregable 2: Pipeline ETL, datos y modelo tentativo
│   ├── data/
│   │   ├── raw/                 # Capturas crudas JSON inalteradas (sobres de procedencia)
│   │   └── processed/           # Datasets limpios e integrados (CSV)
│   ├── modelo/                  # Especificación ontológica tentativa
│   │   ├── vocab.ttl            # Vocabulario formal en sintaxis Turtle (RDF/OWL/SOSA)
│   │   ├── modelo_tentativo.md  # Justificación ontológica, clases, propiedades y axiomas
│   │   └── mapeo_campos.csv     # Matriz de correspondencia campos API ↔ términos semánticos
│   ├── notebooks/               # Cuadernos Jupyter y reportes exportados
│   │   ├── E2_extraccion_limpieza.ipynb # Pipeline reproducible con análisis exploratorio
│   │   └── E2_extraccion_limpieza.html  # Reporte autocontenido para evaluación docente
│   ├── scripts/                 # Scripts modulares de captura, procesamiento y verificación
│   ├── src/bcn_kg/              # Paquete Python estructurado (extracción, limpieza, enlace)
│   ├── tests/                   # Batería de pruebas unitarias automatizadas (pytest)
│   ├── pyproject.toml           # Configuración de dependencias con uv (Python 3.12)
│   └── run_final.ps1            # Script de orquestación y empaquetado final
├── BIM1 - Práctica - E1.docx    # Documento original del Entregable 1
└── .gitignore                   # Exclusión estricta de entornos virtuales y archivos temporales
```

---

## 🚀 Instrucciones de Reproducción

### 1. Clonar el repositorio y configurar el entorno
```bash
git clone https://github.com/alexdgutierrezcordova-nila/smartcity-bcn-knowledge-graph.git
cd smartcity-bcn-knowledge-graph/E2_extraccion
uv sync
```

### 2. Ejecutar las pruebas unitarias
```bash
uv run pytest -v
```

### 3. Verificar coherencia e integridad de datos
```bash
uv run python scripts/verificar_coherencia.py
```

### 4. Orquestación y generación del reporte HTML
```powershell
powershell -ExecutionPolicy Bypass -File .\run_final.ps1
```

---

## 📄 Licencia y Atribución
* Datos de Movilidad: **Open Database License (ODbL)** / **CC BY 4.0** (CityBikes / Bicing BSM).
* Datos de Calidad del Aire: **CC BY 4.0** (Open-Meteo / Copernicus CAMS).
