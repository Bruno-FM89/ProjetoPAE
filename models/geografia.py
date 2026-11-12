"""Camadas geográficas de Heliópolis (Model).

O que este módulo faz
---------------------
Lê os arquivos GeoJSON gerados por ``scripts/preparar_dados_geograficos.py``
(a partir dos Shapefiles da UNAS) e oferece consultas simples:

* tabela das quebradas, das glebas e dos projetos da UNAS;
* em qual quebrada fica cada projeto (cálculo "ponto dentro do polígono");
* o centro e os limites do mapa.

O que é GeoJSON (resumo para iniciantes)
---------------------------------------
É um arquivo de texto com uma lista de "feições" (features). Cada feição tem:

* ``geometry`` — a forma: um ponto ``[longitude, latitude]`` ou um polígono
  (lista de anéis; cada anel é uma lista de pontos que fecha no primeiro);
* ``properties`` — os atributos (nome, área...).

Este módulo não usa bibliotecas geográficas: só ``json`` e um pouco de
geometria. Isso mantém o executável leve.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from models.fontes import ErroFonteDados

#: Arquivos esperados na pasta ``data/geo`` (nome da camada → arquivo).
ARQUIVOS_CAMADAS = {
    "recorte": "recorte.geojson",
    "quebradas": "quebradas.geojson",
    "glebas": "glebas.geojson",
    "projetos_unas": "projetos_unas.geojson",
}


# =============================================================================
# Geometria básica
# =============================================================================
def ponto_no_anel(lon: float, lat: float, anel: list) -> bool:
    """Diz se um ponto está dentro de um anel (contorno fechado).

    Método do "raio": imagine uma linha saindo do ponto para a direita. Se
    ela cruzar o contorno um número ÍMPAR de vezes, o ponto está dentro; se
    cruzar um número PAR de vezes, está fora.
    """
    dentro = False
    for (x1, y1), (x2, y2) in zip(anel, anel[1:] + anel[:1]):
        cruza = (y1 > lat) != (y2 > lat)  # o lado do segmento atravessa a altura do ponto?
        if cruza and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro


def ponto_no_poligono(lon: float, lat: float, geometria: dict) -> bool:
    """Ponto dentro de um Polygon ou MultiPolygon do GeoJSON (descontando buracos)."""
    poligonos = [geometria["coordinates"]] if geometria["type"] == "Polygon" else geometria["coordinates"]
    for poligono in poligonos:
        externo, *buracos = poligono
        if ponto_no_anel(lon, lat, externo) and not any(ponto_no_anel(lon, lat, b) for b in buracos):
            return True
    return False


def coordenadas_contorno(geometria: dict) -> list[list[tuple[float, float]]]:
    """Lista de contornos externos (lista de (lon, lat)) de um Polygon/MultiPolygon.

    Usada para desenhar as linhas de borda no mapa.
    """
    poligonos = [geometria["coordinates"]] if geometria["type"] == "Polygon" else geometria["coordinates"]
    return [[(p[0], p[1]) for p in poligono[0]] for poligono in poligonos]


def centroide_aproximado(geometria: dict) -> tuple[float, float]:
    """Ponto central aproximado (média dos vértices do contorno), usado só para posicionar rótulos."""
    pontos = [p for contorno in coordenadas_contorno(geometria) for p in contorno]
    return sum(p[0] for p in pontos) / len(pontos), sum(p[1] for p in pontos) / len(pontos)


# =============================================================================
# Camadas
# =============================================================================
class CamadasGeograficas:
    """Conjunto das camadas geográficas de Heliópolis.

    Parâmetros do construtor:
        pasta: pasta com os GeoJSON (normalmente ``data/geo``).

    Lança:
        ErroFonteDados se a camada principal (quebradas) não existir.
        Camadas opcionais ausentes são apenas registradas em ``avisos``.
    """

    def __init__(self, pasta: Path) -> None:
        self.pasta = Path(pasta)
        self.avisos: list[str] = []
        self.camadas: dict[str, dict] = {}
        for nome, arquivo in ARQUIVOS_CAMADAS.items():
            caminho = self.pasta / arquivo
            if caminho.is_file():
                self.camadas[nome] = json.loads(caminho.read_text(encoding="utf-8"))
            else:
                self.avisos.append(f"Camada '{nome}' não encontrada ({caminho.name}).")
        if "quebradas" not in self.camadas:
            raise ErroFonteDados(
                f"Mapa indisponível: arquivo {ARQUIVOS_CAMADAS['quebradas']} não encontrado em {self.pasta}. "
                "Gere-o com scripts/preparar_dados_geograficos.py."
            )
        meta = self.pasta / "metadados_geo.json"
        self.metadados = json.loads(meta.read_text(encoding="utf-8")) if meta.is_file() else {}

    def feicoes(self, camada: str) -> list[dict]:
        """Lista de feições de uma camada (lista vazia se a camada não existir)."""
        return self.camadas.get(camada, {}).get("features", [])

    def quebradas(self) -> pd.DataFrame:
        """Tabela das quebradas: nome, área (m² e km²) e quantos projetos da UNAS ficam dentro."""
        projetos = self.projetos()
        linhas = []
        for f in self.feicoes("quebradas"):
            nome = f["properties"]["nome"]
            linhas.append({
                "nome": nome,
                "area_m2": f["properties"].get("area_m2"),
                "area_km2": (f["properties"].get("area_m2") or 0) / 1_000_000,
                "projetos_unas": int((projetos["quebrada"] == nome).sum()) if not projetos.empty else 0,
            })
        return pd.DataFrame(linhas).sort_values("nome").reset_index(drop=True)

    def glebas(self) -> pd.DataFrame:
        """Tabela das glebas: nome e área."""
        return pd.DataFrame([
            {"nome": f["properties"]["nome"], "area_m2": f["properties"].get("area_m2")} for f in self.feicoes("glebas")
        ]).sort_values("nome").reset_index(drop=True) if self.feicoes("glebas") else pd.DataFrame(columns=["nome", "area_m2"])

    def area_recorte_m2(self) -> float | None:
        """Área total do recorte de Heliópolis (m²), se a camada existir."""
        feicoes = self.feicoes("recorte")
        return sum(f["properties"].get("area_m2") or 0 for f in feicoes) if feicoes else None

    def projetos(self) -> pd.DataFrame:
        """Tabela dos projetos da UNAS com coordenadas, tipo e em qual quebrada ficam.

        Para cada ponto testamos cada quebrada com ``ponto_no_poligono``. Pontos
        fora de todas as quebradas recebem "Fora das quebradas mapeadas"; também
        dizemos se o ponto está dentro do recorte de Heliópolis.
        """
        feicoes = self.feicoes("projetos_unas")
        if not feicoes:
            return pd.DataFrame(columns=["nome", "tipo", "descricao", "longitude", "latitude", "quebrada", "dentro_recorte"])
        quebradas = self.feicoes("quebradas")
        recorte = self.feicoes("recorte")
        linhas = []
        for f in feicoes:
            lon, lat = f["geometry"]["coordinates"][:2]
            quebrada = next((q["properties"]["nome"] for q in quebradas if ponto_no_poligono(lon, lat, q["geometry"])), None)
            linhas.append({
                "nome": f["properties"].get("nome"),
                "tipo": f["properties"].get("tipo") or "Não informado",
                "descricao": f["properties"].get("descricao") or "",
                "longitude": lon,
                "latitude": lat,
                "quebrada": quebrada or "Fora das quebradas mapeadas",
                "dentro_recorte": any(ponto_no_poligono(lon, lat, r["geometry"]) for r in recorte),
            })
        return pd.DataFrame(linhas)

    def limites(self, camada: str = "recorte") -> tuple[float, float, float, float]:
        """Menor e maior longitude/latitude de uma camada: (lon_min, lat_min, lon_max, lat_max)."""
        feicoes = self.feicoes(camada) or self.feicoes("quebradas")
        pontos = [p for f in feicoes for contorno in coordenadas_contorno(f["geometry"]) for p in contorno]
        lons, lats = [p[0] for p in pontos], [p[1] for p in pontos]
        return min(lons), min(lats), max(lons), max(lats)

    def centro(self) -> tuple[float, float]:
        """Centro do mapa (lon, lat): meio dos limites do recorte."""
        lon_min, lat_min, lon_max, lat_max = self.limites()
        return (lon_min + lon_max) / 2, (lat_min + lat_max) / 2
