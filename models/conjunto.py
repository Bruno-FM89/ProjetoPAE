"""Conjunto de dados de uma fonte, organizado por estação (Model).

O que esta classe resolve
-------------------------
A fonte entrega "registros" (uma linha por medição). Para fazer gráficos e
estatísticas, é mais prático ter, para UMA estação, uma tabela "larga":

    Data                 | MP2.5_IQAr | O3_IQAr | ...
    2024-01-01 00:00:00  |     25     |   NaN   |
    2024-01-01 01:00:00  |    NaN     |   18    |

Regras importantes (todas registradas em ``transformacoes``):

* NUNCA misturamos estações: cada tabela larga é de uma estação só.
* A tabela larga tem TODAS as horas entre o primeiro e o último registro da
  estação. As horas sem medição ficam vazias (NaN): assim as lacunas aparecem
  nos gráficos em vez de serem escondidas.
* Se a mesma estação tiver dois valores para o mesmo parâmetro e a mesma hora,
  fica o primeiro, e a quantidade descartada é informada.
"""

from __future__ import annotations

import pandas as pd

from models.localizacao import TIPOS_LOCALIZACAO, distancia_ate_heliopolis
from models.parametros import COLUNA_DATA, Variavel, criar_variavel, ordenar_chaves


class ConjuntoDados:
    """Registros de uma fonte + catálogo de variáveis + tabelas por estação.

    Parâmetros do construtor:
        registros: tabela no formato padrão (veja ``models/fontes.py``).
        nome_fonte: nome da fonte, para exibição.
        metadados: dicionário com a origem dos dados.
        transformacoes: lista de transformações já feitas pela fonte.
    """

    def __init__(self, registros: pd.DataFrame, nome_fonte: str, metadados: dict | None = None, transformacoes: list[str] | None = None) -> None:
        self._registros = registros
        self._nome_fonte = nome_fonte
        self._metadados = metadados or {}
        self._transformacoes = list(transformacoes or [])
        self._catalogo = self._montar_catalogo()
        # Chave da variável de cada registro, calculada uma vez só (usada em vários métodos).
        self._chaves = self._chave_da_linha()
        # Guarda as tabelas largas já montadas, para não refazer a cada clique ("cache").
        self._cache_largas: dict[str, pd.DataFrame] = {}
        self._duplicados: dict[str, int] = {}

    # --- propriedades simples ---------------------------------------------
    @property
    def nome_fonte(self) -> str:
        return self._nome_fonte

    @property
    def metadados(self) -> dict:
        return dict(self._metadados)

    @property
    def transformacoes(self) -> list[str]:
        return list(self._transformacoes)

    @property
    def catalogo(self) -> dict[str, Variavel]:
        """Dicionário chave → Variavel com todas as variáveis desta fonte."""
        return dict(self._catalogo)

    @property
    def registros(self) -> pd.DataFrame:
        return self._registros.copy()

    # --- catálogo ------------------------------------------------------------
    def _montar_catalogo(self) -> dict[str, Variavel]:
        """Cria uma Variavel para cada combinação parâmetro + grandeza + unidade.

        Se um mesmo parâmetro aparecer com duas unidades diferentes na mesma
        grandeza (ex.: CO em ppm e em mg/m³), as duas viram variáveis
        separadas, com a unidade na chave. Unidades diferentes nunca são
        tratadas como equivalentes.
        """
        combinacoes = (
            self._registros[["parametro", "grandeza", "unidade", "unidade_confirmada"]]
            .drop_duplicates(subset=["parametro", "grandeza", "unidade"])
        )
        catalogo: dict[str, Variavel] = {}
        # Conta quantas unidades cada (parâmetro, grandeza) tem; >1 exige chave com unidade.
        repetidas = combinacoes.groupby(["parametro", "grandeza"])["unidade"].transform("count") > 1
        for (_, linha), repetida in zip(combinacoes.iterrows(), repetidas):
            variavel = criar_variavel(linha["parametro"], linha["grandeza"], linha["unidade"], bool(linha["unidade_confirmada"]))
            if repetida:
                variavel = criar_variavel(
                    linha["parametro"], linha["grandeza"], linha["unidade"], bool(linha["unidade_confirmada"]),
                    chave=f"{variavel.chave} [{linha['unidade']}]",
                )
            catalogo[variavel.chave] = variavel
        return catalogo

    def _chave_da_linha(self) -> pd.Series:
        """Calcula, para cada registro, a chave da variável correspondente."""
        # Montamos um dicionário (parâmetro, grandeza, unidade) → chave a partir do catálogo.
        mapa = {(v.parametro.codigo, v.grandeza, v.unidade if not v.eh_indice else None): k for k, v in self._catalogo.items()}
        def chave(p, g, u):
            return mapa.get((p, g, None if g == "indice" else u))
        return pd.Series(
            [chave(p, g, u) for p, g, u in zip(self._registros["parametro"], self._registros["grandeza"], self._registros["unidade"])],
            index=self._registros.index,
        )

    # --- estações ------------------------------------------------------------
    def estacoes(self) -> pd.DataFrame:
        """Uma linha por estação: nome, município, coordenadas, distância, período e cobertura.

        A distância é calculada até o ponto de referência de Heliópolis
        (``models/localizacao.py``) e fica vazia quando a localização não é conhecida.
        """
        r = self._registros
        grupos = r.groupby("estacao_id", sort=False)
        tabela = grupos.agg(
            estacao=("estacao", "first"),
            municipio=("municipio", "first"),
            endereco=("endereco", "first"),
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
            fonte_localizacao=("fonte_localizacao", "first"),
            localizacao=("localizacao", "first"),
            registros=("valor", "size"),
            inicio=("data_hora", "min"),
            fim=("data_hora", "max"),
        ).reset_index()
        tabela["distancia_km"] = [distancia_ate_heliopolis(la, lo) for la, lo in zip(tabela["latitude"], tabela["longitude"])]
        tabela["tipo_localizacao"] = tabela["localizacao"].map(TIPOS_LOCALIZACAO).fillna("não informado")
        tabela["variaveis"] = [self.variaveis_da_estacao(e) for e in tabela["estacao_id"]]
        # Ordena da mais próxima para a mais distante; sem distância vai para o fim.
        return tabela.sort_values("distancia_km", na_position="last").reset_index(drop=True)

    def variaveis_da_estacao(self, estacao_id: str) -> list[str]:
        """Chaves das variáveis que têm pelo menos um registro nesta estação."""
        mascara = self._registros["estacao_id"] == estacao_id
        chaves = set(self._chaves[mascara].dropna())
        return ordenar_chaves(chaves, self._catalogo)

    def tabela_larga(self, estacao_id: str) -> pd.DataFrame:
        """Tabela horária (Data + uma coluna por variável) de UMA estação.

        Retorna uma cópia; a versão original fica guardada no cache.
        Lança ValueError se a estação não existir.
        """
        if estacao_id not in self._cache_largas:
            self._cache_largas[estacao_id] = self._montar_larga(estacao_id)
        return self._cache_largas[estacao_id].copy()

    def _montar_larga(self, estacao_id: str) -> pd.DataFrame:
        mascara = self._registros["estacao_id"] == estacao_id
        if not mascara.any():
            raise ValueError(f"Estação desconhecida: {estacao_id}")
        dados = self._registros.loc[mascara, ["data_hora", "valor"]].copy()
        dados["chave"] = self._chaves[mascara]

        # Arredonda para baixo até a hora cheia (ex.: 10:30 → 10:00). Os arquivos
        # usados são horários; se algum não for, isso é registrado.
        fora_da_hora = (dados["data_hora"] != dados["data_hora"].dt.floor("h")).sum()
        dados["data_hora"] = dados["data_hora"].dt.floor("h")

        # Duplicados: mesma hora e mesma variável. Ficamos com o primeiro.
        duplicados = dados.duplicated(subset=["data_hora", "chave"], keep="first")
        self._duplicados[estacao_id] = int(duplicados.sum())
        dados = dados[~duplicados]

        # pivot transforma as linhas em colunas: cada "chave" vira uma coluna.
        larga = dados.pivot(index="data_hora", columns="chave", values="valor")
        # Grade horária completa: date_range cria todas as horas entre o início e o fim.
        grade = pd.date_range(larga.index.min(), larga.index.max(), freq="h")
        larga = larga.reindex(grade)
        larga.index.name = COLUNA_DATA
        larga = larga[ordenar_chaves(larga.columns, self._catalogo)]
        larga.columns.name = None

        nota = (
            f"Estação {estacao_id}: tabela horária de {grade[0]:%d/%m/%Y %H:%M} a {grade[-1]:%d/%m/%Y %H:%M}; "
            "horas sem registro ficam vazias (não são preenchidas)."
        )
        if fora_da_hora:
            nota += f" {int(fora_da_hora)} horário(s) fora da hora cheia arredondado(s) para baixo."
        if duplicados.any():
            nota += f" {int(duplicados.sum())} registro(s) repetido(s) na mesma hora descartado(s) (mantido o primeiro)."
        if nota not in self._transformacoes:
            self._transformacoes.append(nota)
        return larga.reset_index()

    def cobertura(self, estacao_id: str) -> pd.DataFrame:
        """Quantas horas têm valor, para cada variável da estação.

        Retorna colunas: chave, horas_com_valor, horas_no_periodo, percentual,
        primeiro e ultimo (primeira e última hora com valor).
        """
        larga = self.tabela_larga(estacao_id)
        total = len(larga)
        linhas = []
        for chave in larga.columns.drop(COLUNA_DATA):
            serie = larga.set_index(COLUNA_DATA)[chave].dropna()
            linhas.append(
                {
                    "chave": chave,
                    "horas_com_valor": int(serie.size),
                    "horas_no_periodo": total,
                    "percentual": serie.size / total * 100 if total else 0.0,
                    "primeiro": serie.index.min() if serie.size else pd.NaT,
                    "ultimo": serie.index.max() if serie.size else pd.NaT,
                }
            )
        return pd.DataFrame(linhas)
