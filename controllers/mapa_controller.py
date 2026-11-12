"""Controller do mapa de Heliópolis (camada C do MVC).

Reúne, para a página "Mapa de Heliópolis":

* as camadas da UNAS (recorte, quebradas, glebas, projetos) — Model ``CamadasGeograficas``;
* a região informada de cada termômetro — Controller dos termômetros;
* as estações de qualidade do ar — Controller do painel (que já calcula as distâncias).

Regra de privacidade: termômetros NUNCA aparecem como pontos (não temos e não
queremos o endereço). No máximo, a quebrada onde estão é destacada — e só se a
UNAS tiver validado essa informação.
"""

from __future__ import annotations

import pandas as pd

from models.geografia import CamadasGeograficas, centroide_aproximado, coordenadas_contorno
from services.config import Configuracao


class MapaController:
    """Prepara as camadas e as informações exibidas no mapa.

    Parâmetros do construtor:
        camadas: objeto ``CamadasGeograficas`` já carregado.
        termometros: tabela de ``TermometrosController.tabela_termometros()`` (ou None
            se os dados dos termômetros não estiverem disponíveis).
        estacoes_ar: tabela de estações de qualidade do ar com latitude/longitude
            e distância (ou None).
    """

    def __init__(self, camadas: CamadasGeograficas, termometros: pd.DataFrame | None = None,
                 estacoes_ar: pd.DataFrame | None = None) -> None:
        self._camadas = camadas
        self._termometros = termometros if termometros is not None else pd.DataFrame()
        self._estacoes = estacoes_ar if estacoes_ar is not None else pd.DataFrame()

    @classmethod
    def a_partir_da_configuracao(cls, config: Configuracao, termometros=None, estacoes_ar=None) -> "MapaController":
        return cls(CamadasGeograficas(config.pasta_geo), termometros, estacoes_ar)

    # --- camadas para desenhar ------------------------------------------------------
    def contornos(self, camada: str) -> list[dict]:
        """Uma entrada por feição: nome, lista de contornos (lon, lat) e centro para o rótulo."""
        saida = []
        for f in self._camadas.feicoes(camada):
            nome = f["properties"].get("nome") or "Recorte de Heliópolis"
            saida.append({
                "nome": nome,
                "area_m2": f["properties"].get("area_m2"),
                "contornos": coordenadas_contorno(f["geometry"]),
                "centro": centroide_aproximado(f["geometry"]),
            })
        return saida

    def geojson(self, camada: str) -> dict:
        """GeoJSON bruto de uma camada (usado pelo gráfico de mapa preenchido)."""
        return self._camadas.camadas.get(camada, {"type": "FeatureCollection", "features": []})

    def tem_camada(self, camada: str) -> bool:
        return bool(self._camadas.feicoes(camada))

    @property
    def avisos(self) -> list[str]:
        return list(self._camadas.avisos)

    @property
    def metadados(self) -> dict:
        return self._camadas.metadados

    def centro(self) -> tuple[float, float]:
        return self._camadas.centro()

    # --- tabelas -------------------------------------------------------------------------
    def quebradas(self) -> pd.DataFrame:
        """Quebradas com área, nº de projetos da UNAS e nº de termômetros (validados ou não)."""
        tabela = self._camadas.quebradas()
        tabela["termometros_validados"] = tabela["nome"].map(lambda q: len(self.termometros_na_quebrada(q, True)))
        tabela["termometros_a_confirmar"] = tabela["nome"].map(lambda q: len(self.termometros_na_quebrada(q, False)))
        return tabela

    def glebas(self) -> pd.DataFrame:
        return self._camadas.glebas()

    def projetos(self, tipos: list[str] | None = None) -> pd.DataFrame:
        """Projetos da UNAS, opcionalmente só de alguns tipos (ex.: ["CEI", "CCA"])."""
        tabela = self._camadas.projetos()
        return tabela if not tipos else tabela[tabela["tipo"].isin(tipos)].reset_index(drop=True)

    def tipos_projeto(self) -> list[str]:
        """Tipos de projeto, do mais frequente ao menos frequente."""
        tabela = self._camadas.projetos()
        return list(tabela["tipo"].value_counts().index) if not tabela.empty else []

    def area_recorte_km2(self) -> float | None:
        area = self._camadas.area_recorte_m2()
        return area / 1_000_000 if area else None

    def termometros_na_quebrada(self, quebrada: str, validados: bool) -> list[str]:
        """Nomes dos termômetros cuja região informada é esta quebrada.

        ``validados=True`` devolve só os confirmados pela UNAS; ``False`` só os
        que ainda aguardam confirmação.
        """
        t = self._termometros
        if t.empty:
            return []
        filtro = (t["quebrada"] == quebrada) & (t["localizacao_validada"] == validados)
        return list(t.loc[filtro, "nome"])

    def conferencia_areas(self) -> pd.DataFrame:
        """Compara a área calculada pelo sistema com a área gravada na tabela original das quebradas.

        Serve de prova de que a conversão dos Shapefiles preservou as formas:
        as duas áreas devem ser praticamente iguais (diferença bem menor que 1%).
        """
        linhas = []
        for f in self._camadas.feicoes("quebradas"):
            original = f["properties"].get("area_m2_original")
            calculada = f["properties"].get("area_m2")
            linhas.append({
                "quebrada": f["properties"]["nome"], "area_original_m2": original, "area_calculada_m2": calculada,
                "diferenca_pct": abs(calculada - original) / original * 100 if original else None,
            })
        return pd.DataFrame(linhas)

    def estacoes_ar(self) -> pd.DataFrame:
        """Estações de qualidade do ar com coordenadas (para mostrar que ficam FORA de Heliópolis)."""
        if self._estacoes.empty:
            return self._estacoes
        return self._estacoes.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
