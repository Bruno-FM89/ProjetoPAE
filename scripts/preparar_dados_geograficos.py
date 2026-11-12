"""Converte os Shapefiles da UNAS (Drive "dados geográficos") em GeoJSON para o mapa do painel.

O que é um Shapefile
--------------------
É o formato mais comum de mapas em programas como o QGIS. Apesar do nome no
singular, ele é um CONJUNTO de arquivos com o mesmo nome e extensões diferentes,
que só funcionam juntos:

* ``.shp`` — as formas (pontos, linhas ou polígonos);
* ``.shx`` — um índice para achar cada forma rapidamente;
* ``.dbf`` — a tabela de atributos (nome da quebrada, área...);
* ``.prj`` — o sistema de coordenadas (como ler os números das posições);
* ``.cpg`` — a codificação de texto da tabela (aqui, UTF-8).

Por que converter
-----------------
Os arquivos da UNAS estão em SIRGAS 2000 / UTM zona 23S (EPSG:31983): as
posições são METROS a partir de uma origem, e não latitude/longitude. Os mapas
da web usam graus (WGS 84, EPSG:4326). Este script faz a conversão UMA vez e
grava arquivos GeoJSON (texto simples), que o app lê sem precisar de
bibliotecas geográficas pesadas. Isso deixa o executável menor e mais confiável.

Camadas convertidas (pasta ``data/geo/bruto/<camada>/``)
---------------------------------------------------------
* recorte        — contorno de Heliópolis usado pela UNAS;
* quebradas      — 7 quebradas (sub-regiões) com nome e área;
* glebas         — 15 glebas (divisão fundiária, letras A a N);
* projetos_unas  — 52 pontos de projetos e equipamentos da UNAS (2020).

Como usar
---------
    python scripts/preparar_dados_geograficos.py

Requer ``pyshp`` e ``pyproj`` (``pip install -r requirements-dev.txt``). O app
NÃO precisa delas: ele só lê os GeoJSON gerados.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import shapefile  # biblioteca pyshp: lê os arquivos .shp/.shx/.dbf
from pyproj import CRS, Transformer  # converte coordenadas entre sistemas

RAIZ = Path(__file__).resolve().parent.parent
PASTA_BRUTO = RAIZ / "data" / "geo" / "bruto"
PASTA_SAIDA = RAIZ / "data" / "geo"
PARTES = (".shp", ".shx", ".dbf", ".prj", ".cpg")

# Para cada camada: quais atributos manter e com que nome (atributo original → nome no GeoJSON).
CAMADAS = {
    "recorte": {"ID": "id", "NOME": "nome_original"},
    "quebradas": {"ID": "id", "NOME": "nome", "area": "area_m2_original"},
    "glebas": {"ID": "id", "Nome": "nome"},
    "projetos_unas": {"Name": "nome", "descriptio": "descricao", "Tipo": "tipo"},
}
CASAS_DECIMAIS = 6  # ~10 cm de precisão em graus: suficiente e deixa os arquivos menores


def _sha256(caminho: Path) -> str:
    """Impressão digital do arquivo (permite conferir se o Shapefile original mudou)."""
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _area_anel(anel: list) -> float:
    """Área de um anel de coordenadas planas (metros) pela "fórmula do cadarço" (shoelace)."""
    soma = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:] + anel[:1]):
        soma += x1 * y2 - x2 * y1
    return abs(soma) / 2


def area_m2(geometria: dict) -> float:
    """Área de um Polígono/MultiPolígono em m² (anel externo menos os buracos)."""
    poligonos = [geometria["coordinates"]] if geometria["type"] == "Polygon" else geometria["coordinates"]
    total = 0.0
    for poligono in poligonos:
        aneis = [[tuple(p[:2]) for p in anel] for anel in poligono]
        total += _area_anel(aneis[0]) - sum(_area_anel(buraco) for buraco in aneis[1:])
    return total


def _converter(coordenadas, transformador: Transformer):
    """Converte recursivamente as coordenadas (listas aninhadas) de metros UTM para graus."""
    if isinstance(coordenadas[0], (int, float)):
        lon, lat = transformador.transform(coordenadas[0], coordenadas[1])  # descarta a altura (Z), se houver
        return [round(lon, CASAS_DECIMAIS), round(lat, CASAS_DECIMAIS)]
    return [_converter(c, transformador) for c in coordenadas]


def _texto(valor):
    """Limpa textos da tabela: tira espaços invisíveis (\\xa0) das pontas."""
    return valor.replace("\xa0", " ").strip() if isinstance(valor, str) else valor


def converter_camada(nome: str, campos: dict[str, str]) -> tuple[dict, dict]:
    """Lê um Shapefile completo e devolve (GeoJSON, informações da camada).

    Verifica se todas as partes do conjunto existem, lê o sistema de
    coordenadas no ``.prj``, converte para WGS 84 e calcula a área de cada
    polígono em m² (no sistema original, que está em metros).
    """
    pasta = PASTA_BRUTO / nome
    base = pasta / nome
    faltando = [ext for ext in PARTES if not base.with_suffix(ext).is_file()]
    if any(ext in faltando for ext in (".shp", ".shx", ".dbf", ".prj")):
        raise FileNotFoundError(f"Camada '{nome}': faltam as partes {faltando} em {pasta}.")

    crs_origem = CRS.from_wkt(base.with_suffix(".prj").read_text(encoding="utf-8"))
    epsg = crs_origem.to_epsg(min_confidence=20)
    transformador = Transformer.from_crs(crs_origem, "EPSG:4326", always_xy=True)  # always_xy: ordem (x=lon, y=lat)
    codificacao = base.with_suffix(".cpg").read_text().strip() if base.with_suffix(".cpg").is_file() else "utf-8"

    leitor = shapefile.Reader(str(base), encoding=codificacao)
    nomes_campos = [f[0] for f in leitor.fields[1:]]  # o primeiro campo é interno do formato
    feicoes = []
    for forma, registro in zip(leitor.shapes(), leitor.records()):
        atributos = dict(zip(nomes_campos, registro))
        geometria = forma.__geo_interface__  # a forma no padrão GeoJSON, ainda em metros
        propriedades = {destino: _texto(atributos.get(origem)) for origem, destino in campos.items()}
        if geometria["type"] in ("Polygon", "MultiPolygon"):
            propriedades["area_m2"] = round(area_m2(geometria), 1)
        feicoes.append({
            "type": "Feature",
            "properties": propriedades,
            "geometry": {"type": geometria["type"], "coordinates": _converter(geometria["coordinates"], transformador)},
        })
    geojson = {"type": "FeatureCollection", "name": nome, "features": feicoes}
    info = {
        "camada": nome,
        "tipo_geometria": leitor.shapeTypeName,
        "feicoes": len(feicoes),
        "atributos_originais": nomes_campos,
        "sistema_original": crs_origem.name,
        "epsg_original": epsg,
        "codificacao_dbf": codificacao,
        "partes_presentes": [ext for ext in PARTES if base.with_suffix(ext).is_file()],
        "sha256_shp": _sha256(base.with_suffix(".shp")),
    }
    return geojson, info


def main() -> int:
    """Converte todas as camadas e grava os GeoJSON e o arquivo de metadados. Devolve 0 se deu certo."""
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    infos = []
    for nome, campos in CAMADAS.items():
        geojson, info = converter_camada(nome, campos)
        (PASTA_SAIDA / f"{nome}.geojson").write_text(json.dumps(geojson, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        infos.append(info)
        print(f"{nome}: {info['feicoes']} feições ({info['tipo_geometria']}), {info['sistema_original']} → WGS 84")
    metadados = {
        "origem": "Google Drive da UNAS — pasta de dados geográficos de Heliópolis (Shapefiles).",
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "conversao": (
            "Coordenadas convertidas de SIRGAS 2000 / UTM 23S (metros) para WGS 84 (graus) com a biblioteca pyproj. "
            "Para mapas na escala de um bairro, a diferença entre SIRGAS 2000 e WGS 84 é menor que 1 metro."
        ),
        "areas": "Calculadas em m² no sistema original (UTM, em metros), pela fórmula do cadarço.",
        "camadas": infos,
    }
    (PASTA_SAIDA / "metadados_geo.json").write_text(json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
