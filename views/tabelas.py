"""Formatação de tabelas para exibição (View).

O Controller devolve tabelas com nomes técnicos (``media``, ``desvio_padrao``)
e números "crus". Estas funções trocam os nomes por títulos em português e
formatam os números no padrão brasileiro, só para mostrar na tela.
"""

from __future__ import annotations

import pandas as pd

from views.estilo import numero


def _fmt(valor: float) -> str:
    """Número com 2 casas (ou 3 se for menor que 1, como 0,045)."""
    if valor is None or valor != valor:
        return "—"
    return numero(valor, 3 if abs(valor) < 1 else 2)


def _inteiro(valor) -> str:
    return numero(float(valor), 0)


def descritiva(desc: pd.DataFrame, rotulo) -> pd.DataFrame:
    """Tabela de estatística descritiva com cabeçalhos em português.

    Parâmetros:
        desc: resultado de ``AnaliseEstatistica.descritiva``.
        rotulo: função que recebe a chave da variável e devolve o rótulo legível.
    """
    return pd.DataFrame(
        {
            "Variável": [rotulo(c) for c in desc.index],
            "Registros com valor": desc["n"].map(_inteiro),
            "Horas sem valor": desc["nulos"].map(_inteiro),
            "Média": desc["media"].map(_fmt),
            "Mediana": desc["mediana"].map(_fmt),
            "Moda*": desc["moda"].map(_fmt),
            "Mínimo": desc["minimo"].map(_fmt),
            "Máximo": desc["maximo"].map(_fmt),
            "Desvio padrão": desc["desvio_padrao"].map(_fmt),
            "Variância": desc["variancia"].map(_fmt),
            "Q1": desc["q1"].map(_fmt),
            "Q3": desc["q3"].map(_fmt),
        }
    ).reset_index(drop=True)


def outliers(resumo: pd.DataFrame, rotulo) -> pd.DataFrame:
    """Tabela dos limites do IQR e da quantidade de valores sinalizados."""
    return pd.DataFrame(
        {
            "Variável": [rotulo(c) for c in resumo.index],
            "Q1": resumo["q1"].map(_fmt),
            "Q3": resumo["q3"].map(_fmt),
            "Limite inferior": resumo["limite_inferior"].map(_fmt),
            "Limite superior": resumo["limite_superior"].map(_fmt),
            "Valores sinalizados": resumo["outliers"].map(_inteiro),
            "% dos registros": resumo["percentual"].map(lambda v: numero(v, 2)),
        }
    ).reset_index(drop=True)


def comparacao(comp: pd.DataFrame, rotulo) -> pd.DataFrame:
    """Tabela "original × tratado" com números formatados."""
    saida = pd.DataFrame({"Variável": [rotulo(c) for c in comp.index]})
    for coluna in comp.columns:
        formatar = _inteiro if coluna.startswith("Registros") else _fmt
        saida[coluna] = comp[coluna].map(formatar).to_numpy()
    return saida


def pares(tabela: pd.DataFrame, classificar, rotulo) -> pd.DataFrame:
    """Ranking de pares de variáveis pela força da correlação."""
    return pd.DataFrame(
        {
            "Variável A": tabela["variavel_a"].map(rotulo),
            "Variável B": tabela["variavel_b"].map(rotulo),
            "Horas em comum": tabela["pares"].map(_inteiro),
            "r": tabela["r"].map(lambda v: numero(v, 2)),
            "Leitura": tabela["r"].map(classificar),
        }
    )


def estacoes(tabela: pd.DataFrame) -> pd.DataFrame:
    """Lista de estações para a página "Sobre os dados"."""
    return pd.DataFrame(
        {
            "Estação": tabela["estacao"],
            "Município": tabela["municipio"],
            "Endereço": tabela["endereco"],
            "Distância de Heliópolis (km, linha reta)": tabela["distancia_km"].map(lambda v: numero(v, 1)),
            "Latitude": tabela["latitude"].map(lambda v: numero(v, 5)),
            "Longitude": tabela["longitude"].map(lambda v: numero(v, 5)),
            "Tipo de local": tabela["tipo_localizacao"],
            "Primeiro registro": tabela["inicio"].dt.strftime("%d/%m/%Y %H:%M"),
            "Último registro": tabela["fim"].dt.strftime("%d/%m/%Y %H:%M"),
            "Registros": tabela["registros"].map(_inteiro),
        }
    )
