"""Cálculos estatísticos e agregações (Model).

Toda a matemática fica aqui, feita com Pandas. A View só exibe os resultados
e o Controller só decide o que calcular. Cada método recebe nomes de colunas,
então funciona com qualquer conjunto de variáveis (reais ou fictícias).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.parametros import COLUNA_DATA, Variavel
from models.tratamento import DIAS_SEMANA, MESES, LimitesIQR, nome_coluna_outlier

#: Agrupamentos de tempo aceitos nas séries ("h" = sem agrupar).
FREQUENCIAS = {"h": "Horária", "D": "Diária", "W": "Semanal", "MS": "Mensal"}

#: Mínimo de horas em comum para calcular a correlação entre duas variáveis.
#: Com poucos pares, um único valor pode criar uma correlação enganosa.
MINIMO_PARES_CORRELACAO = 30


class AnaliseEstatistica:
    """Estatísticas sobre uma tabela larga JÁ filtrada (estação, período, tratamento).

    Parâmetros do construtor:
        df: tabela com ``Data``, as colunas numéricas e as colunas auxiliares
            criadas pelo TratadorDados (hora, dia_semana, mes_nome...).
        catalogo: dicionário chave → Variavel, usado para saber quantas casas
            decimais arredondar antes de calcular a moda.
    """

    def __init__(self, df: pd.DataFrame, catalogo: dict[str, Variavel] | None = None) -> None:
        self._df = df
        self._catalogo = catalogo or {}

    # --- estatística descritiva ---------------------------------------------
    def descritiva(self, colunas: list[str]) -> pd.DataFrame:
        """Uma linha por variável com as principais medidas.

        Colunas do resultado e o que significam:
            n: quantidade de valores existentes (sem contar ausentes);
            nulos: quantidade de horas sem valor;
            media: soma dos valores ÷ quantidade;
            mediana: valor do meio quando tudo é colocado em ordem;
            moda: valor que mais se repete (após arredondar; ver ``casas_moda``);
            minimo / maximo: menor e maior valor;
            desvio_padrao: o quanto os valores se afastam, em média, da média
                (calculado com n − 1, o padrão do Pandas para amostras);
            variancia: desvio padrão ao quadrado;
            q1 / q3: 1º e 3º quartis.
        """
        linhas = []
        for coluna in colunas:
            serie = self._df[coluna].dropna()  # dropna() remove os valores ausentes
            casas = self._catalogo[coluna].casas_moda if coluna in self._catalogo else 1
            # Em medidas contínuas quase nenhum valor se repete exatamente;
            # arredondando antes, a moda passa a dizer algo útil. Em empate, usamos a menor.
            modas = serie.round(casas).mode()
            tem = serie.size > 0
            linhas.append(
                {
                    "variavel": coluna,
                    "n": int(serie.size),
                    "nulos": int(self._df[coluna].isna().sum()),
                    "media": serie.mean() if tem else np.nan,
                    "mediana": serie.median() if tem else np.nan,
                    "moda": modas.min() if len(modas) else np.nan,
                    "minimo": serie.min() if tem else np.nan,
                    "maximo": serie.max() if tem else np.nan,
                    "desvio_padrao": serie.std() if serie.size > 1 else np.nan,
                    "variancia": serie.var() if serie.size > 1 else np.nan,
                    "q1": serie.quantile(0.25) if tem else np.nan,
                    "q3": serie.quantile(0.75) if tem else np.nan,
                }
            )
        return pd.DataFrame(linhas).set_index("variavel")

    # --- séries e padrões no tempo ----------------------------------------------
    def serie_temporal(self, colunas: list[str], frequencia: str = "D") -> pd.DataFrame:
        """Valores ao longo do tempo, agrupados por hora (sem agrupar), dia, semana ou mês.

        A média de cada dia/semana/mês usa apenas as horas que têm valor.
        Semanas começam na segunda-feira.
        """
        if frequencia not in FREQUENCIAS:
            raise ValueError(f"Frequência inválida: {frequencia}")
        base = self._df[[COLUNA_DATA, *colunas]]
        if frequencia == "h":
            return base.reset_index(drop=True)
        indexado = base.set_index(COLUNA_DATA)
        if frequencia == "W":
            agregado = indexado.resample("W-MON", label="left", closed="left").mean()
        else:
            # resample agrupa por período de tempo ("D" = dia, "MS" = início do mês).
            agregado = indexado.resample(frequencia).mean()
        return agregado.reset_index()

    def media_por_hora(self, coluna: str) -> pd.DataFrame:
        """Média e quantidade de valores para cada hora do dia (0 a 23)."""
        return self._df.groupby("hora")[coluna].agg(media="mean", n="count").reset_index()

    def media_por_dia_semana(self, coluna: str) -> pd.DataFrame:
        """Média e quantidade de valores para cada dia da semana (Seg a Dom)."""
        # observed=False mantém os 7 dias mesmo que algum não tenha dados.
        agrupado = self._df.groupby("dia_semana", observed=False)[coluna].agg(media="mean", n="count").reset_index()
        agrupado["dia_semana"] = pd.Categorical(agrupado["dia_semana"], categories=DIAS_SEMANA, ordered=True)
        return agrupado.sort_values("dia_semana").reset_index(drop=True)

    def media_por_mes(self, coluna: str) -> pd.DataFrame:
        """Média por mês do ANO (Jan a Dez), juntando anos diferentes."""
        agrupado = self._df.groupby("mes_nome", observed=False)[coluna].agg(media="mean", n="count").reset_index()
        agrupado["mes_nome"] = pd.Categorical(agrupado["mes_nome"], categories=MESES, ordered=True)
        return agrupado.sort_values("mes_nome").reset_index(drop=True)

    def media_mensal(self, coluna: str) -> pd.DataFrame:
        """Média de cada mês do CALENDÁRIO (ex.: julho/2024 e julho/2025 separados)."""
        serie = self._df.set_index(COLUNA_DATA)[coluna]
        mensal = serie.resample("MS").agg(["mean", "count"]).reset_index()
        mensal.columns = ["mes", "media", "n"]
        return mensal

    def calendario_diario(self, coluna: str) -> pd.DataFrame:
        """Média de cada dia, com ano, mês e dia separados (para o mapa de calor)."""
        diario = self._df.set_index(COLUNA_DATA)[coluna].resample("D").mean().reset_index()
        diario.columns = ["data", "valor"]
        diario["ano"] = diario["data"].dt.year
        diario["mes"] = diario["data"].dt.month
        diario["dia"] = diario["data"].dt.day
        return diario

    # --- correlação --------------------------------------------------------------
    def correlacao(self, colunas: list[str], metodo: str = "pearson") -> pd.DataFrame:
        """Matriz de correlação entre as colunas.

        * Pearson mede relação LINEAR (os pontos seguem uma reta).
        * Spearman compara as POSIÇÕES (rankings) dos valores; capta relações
          que sobem ou descem juntas mesmo sem formar uma reta.
        Pares com menos de MINIMO_PARES_CORRELACAO horas em comum ficam vazios.
        """
        if metodo not in ("pearson", "spearman"):
            raise ValueError("Método de correlação deve ser 'pearson' ou 'spearman'.")
        return self._df[colunas].corr(method=metodo, min_periods=MINIMO_PARES_CORRELACAO)

    def pares_correlacionados(self, colunas: list[str], metodo: str = "pearson") -> pd.DataFrame:
        """Pares únicos de variáveis, do mais forte ao mais fraco (em valor absoluto)."""
        matriz = self.correlacao(colunas, metodo)
        pares = []
        for i, a in enumerate(colunas):
            for b in colunas[i + 1:]:  # b começa depois de a: cada par aparece uma vez
                r = matriz.loc[a, b]
                n = int(self._df[[a, b]].dropna().shape[0])
                pares.append({"variavel_a": a, "variavel_b": b, "r": r, "forca": abs(r), "pares": n})
        tabela = pd.DataFrame(pares, columns=["variavel_a", "variavel_b", "r", "forca", "pares"])
        return tabela.sort_values("forca", ascending=False, na_position="last").reset_index(drop=True)

    # --- outliers ----------------------------------------------------------------
    def resumo_outliers(self, limites: dict[str, LimitesIQR], colunas: list[str]) -> pd.DataFrame:
        """Conta os valores sinalizados em cada variável dentro do recorte atual."""
        linhas = []
        for coluna in colunas:
            lim = limites[coluna]
            validos = int(self._df[coluna].notna().sum())
            marca = nome_coluna_outlier(coluna)
            n = int(self._df[marca].sum()) if marca in self._df else 0
            linhas.append(
                {
                    "variavel": coluna, "q1": lim.q1, "q3": lim.q3,
                    "limite_inferior": lim.inferior, "limite_superior": lim.superior,
                    "outliers": n, "percentual": (n / validos * 100) if validos else np.nan,
                }
            )
        return pd.DataFrame(linhas).set_index("variavel")

    # --- frases de interpretação (calculadas, nunca fixas) ---------------------------
    @staticmethod
    def classificar_correlacao(r: float) -> str:
        """Descreve o coeficiente r em palavras (ex.: ``"moderada positiva"``)."""
        if r is None or np.isnan(r):
            return "indefinida (dados insuficientes)"
        forca = abs(r)
        if forca < 0.1:
            return "praticamente nula"
        if forca < 0.3:
            nivel = "fraca"
        elif forca < 0.7:
            nivel = "moderada"
        elif forca < 0.9:
            nivel = "forte"
        else:
            nivel = "muito forte"
        return f"{nivel} {'positiva' if r > 0 else 'negativa'}"

    @staticmethod
    def comparar_media_mediana(media: float, mediana: float) -> str:
        """Frase simples sobre a diferença entre média e mediana."""
        if media is None or mediana is None or np.isnan(media) or np.isnan(mediana) or mediana == 0:
            return ""
        diferenca = (media - mediana) / abs(mediana)
        if abs(diferenca) < 0.03:
            return "A média e a mediana são muito próximas: os valores se distribuem de forma bastante equilibrada."
        if diferenca > 0:
            return (
                "A média é maior que a mediana: alguns valores altos puxam a média para cima, "
                "por isso a mediana representa melhor o valor típico."
            )
        return (
            "A média é menor que a mediana: alguns valores baixos puxam a média para baixo, "
            "por isso a mediana representa melhor o valor típico."
        )
