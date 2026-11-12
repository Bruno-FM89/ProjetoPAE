"""Faixas oficiais de qualidade do ar e classificação dos valores (Model).

Fonte das faixas
----------------
CETESB, página "Padrões de qualidade do ar"
(https://cetesb.sp.gov.br/ar/padroes-de-qualidade-do-ar/), consultada em
08/11/2026. A própria página informa que a qualificação está vinculada à
Resolução CONAMA nº 491/2018.

Duas formas de classificar, cada uma no seu caso
-----------------------------------------------
1. **Índice (IQAr):** as faixas do índice valem para qualquer poluente,
   porque o índice já foi calculado pela fonte com a regra de cada um.
   É o caso dos dados reais do MonitorAr usados no projeto.
2. **Concentração:** cada poluente tem limites próprios e um PERÍODO DE MÉDIA
   próprio (24 horas, 8 horas ou 1 hora). Não se pode comparar um valor de
   uma única hora com um limite de 24 horas, nem usar o limite de um
   poluente para outro. Por isso este módulo primeiro calcula a média no
   período correto e só então compara com os limites do mesmo poluente.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

FONTE_FAIXAS = (
    "CETESB, “Padrões de qualidade do ar” (cetesb.sp.gov.br/ar/padroes-de-qualidade-do-ar), "
    "qualificação vinculada à Resolução CONAMA nº 491/2018. Consultado em 08/11/2026."
)


@dataclass(frozen=True)
class FaixaQualidade:
    """Uma faixa de qualidade do ar (N1 a N5).

    Atributos:
        codigo: ``"N1"`` ... ``"N5"``.
        nome: nome oficial da faixa (Boa, Moderada, Ruim, Muito Ruim, Péssima).
        indice_min, indice_max: limites do índice nesta faixa
            (``indice_max=None`` significa "sem limite superior").
        cor: cor usada nos gráficos (verde → roxo, como nos boletins da CETESB).
    """

    codigo: str
    nome: str
    indice_min: float
    indice_max: float | None
    cor: str

    @property
    def rotulo(self) -> str:
        """Ex.: ``"N1 – Boa"``."""
        return f"{self.codigo} – {self.nome}"

    @property
    def intervalo(self) -> str:
        """Ex.: ``"0 a 40"`` ou ``"acima de 200"``."""
        if self.indice_max is None:
            return f"acima de {int(self.indice_min) - 1}"
        return f"{int(self.indice_min)} a {int(self.indice_max)}"


# Faixas do índice conforme a tabela da CETESB:
# N1 Boa 0–40 | N2 Moderada 41–80 | N3 Ruim 81–120 | N4 Muito Ruim 121–200 | N5 Péssima >200
FAIXAS_IQAR: list[FaixaQualidade] = [
    FaixaQualidade("N1", "Boa", 0, 40, "#3a9b47"),
    FaixaQualidade("N2", "Moderada", 41, 80, "#d8b600"),
    FaixaQualidade("N3", "Ruim", 81, 120, "#e07b00"),
    FaixaQualidade("N4", "Muito Ruim", 121, 200, "#d0302b"),
    FaixaQualidade("N5", "Péssima", 201, None, "#7b3294"),
]


def classificar_indice(valor: float) -> FaixaQualidade | None:
    """Diz em qual faixa (N1 a N5) um valor de IQAr cai.

    Parâmetros:
        valor: valor do índice (número).

    Retorna:
        A FaixaQualidade correspondente, ou ``None`` se o valor estiver
        ausente ou for negativo (índice negativo não existe).

    Como valores podem ter casas decimais (ex.: 40,5), usamos "até 40",
    "até 80" etc. como limites superiores.
    """
    if valor is None or valor != valor or valor < 0:  # valor != valor detecta NaN
        return None
    for limite, faixa in zip((40, 80, 120, 200), FAIXAS_IQAR):
        if valor <= limite:
            return faixa
    return FAIXAS_IQAR[-1]


def distribuicao_por_faixa(serie: pd.Series) -> pd.DataFrame:
    """Conta quantos valores de índice caem em cada faixa.

    Parâmetros:
        serie: valores de IQAr (valores ausentes são ignorados).

    Retorna:
        Tabela com as colunas ``faixa``, ``intervalo``, ``cor``, ``registros``
        e ``percentual`` (em relação aos registros com valor), uma linha por faixa,
        de N1 a N5, mesmo que alguma tenha zero registros.
    """
    validos = serie.dropna()
    # Para cada valor, descobrimos a faixa (ou None para valores negativos, que
    # não são índices válidos); depois descartamos os None e contamos por código.
    def codigo_da_faixa(valor: float) -> str | None:
        faixa = classificar_indice(valor)
        return faixa.codigo if faixa else None

    codigos = validos.map(codigo_da_faixa).dropna()
    contagem = codigos.value_counts()
    linhas = []
    for faixa in FAIXAS_IQAR:
        n = int(contagem.get(faixa.codigo, 0))
        linhas.append(
            {
                "faixa": faixa.rotulo,
                "intervalo": faixa.intervalo,
                "cor": faixa.cor,
                "registros": n,
                "percentual": (n / len(codigos) * 100) if len(codigos) else float("nan"),
            }
        )
    return pd.DataFrame(linhas)


# --- concentrações ----------------------------------------------------------
@dataclass(frozen=True)
class LimitesConcentracao:
    """Limites de concentração de UM poluente, no SEU período de média.

    Atributos:
        periodo: descrição do período de média ("24 horas", "8 horas", "1 hora").
        horas: tamanho do período em horas (24, 8 ou 1).
        unidade: unidade em que os limites estão expressos.
        limites: limite superior das faixas N1, N2, N3 e N4 (acima do último é N5).
    """

    periodo: str
    horas: int
    unidade: str
    limites: tuple[float, float, float, float]


# Tabela da CETESB (mesma fonte citada no topo).
LIMITES_CONCENTRACAO: dict[str, LimitesConcentracao] = {
    "MP10": LimitesConcentracao("média de 24 horas", 24, "µg/m³", (50, 100, 150, 250)),
    "MP2.5": LimitesConcentracao("média de 24 horas", 24, "µg/m³", (25, 50, 75, 125)),
    "O3": LimitesConcentracao("média de 8 horas", 8, "µg/m³", (100, 130, 160, 200)),
    "CO": LimitesConcentracao("média de 8 horas", 8, "ppm", (9, 11, 13, 15)),
    "NO2": LimitesConcentracao("média de 1 hora", 1, "µg/m³", (200, 240, 320, 1130)),
    "SO2": LimitesConcentracao("média de 24 horas", 24, "µg/m³", (20, 40, 365, 800)),
}

#: Mínimo de horas válidas para aceitar uma média de 24 horas. A página do
#: QUALAR (CETESB) informa o critério de 16 valores válidos por dia.
MINIMO_HORAS_MEDIA_24H = 16


def pode_classificar_concentracao(codigo: str, unidade: str, unidade_confirmada: bool) -> bool:
    """Só classificamos concentrações com limites oficiais na MESMA unidade e unidade confirmada."""
    limites = LIMITES_CONCENTRACAO.get(codigo)
    return bool(limites and unidade_confirmada and unidade == limites.unidade)


def medias_no_periodo_oficial(serie_horaria: pd.Series, codigo: str) -> pd.Series:
    """Calcula as médias no período de referência do poluente.

    Parâmetros:
        serie_horaria: valores horários com índice de datas/horas (DatetimeIndex).
        codigo: código do poluente (MP10, MP2.5, O3, CO, NO2 ou SO2).

    Retorna:
        Série de médias:
        * 24 horas → uma média por dia, só nos dias com pelo menos
          ``MINIMO_HORAS_MEDIA_24H`` horas válidas;
        * 8 horas → média móvel das últimas 8 horas, só quando as 8 horas
          têm valor (critério conservador adotado por este projeto);
        * 1 hora → os próprios valores horários.
    """
    limites = LIMITES_CONCENTRACAO[codigo]
    serie = serie_horaria.sort_index()
    if limites.horas == 24:
        # resample("D") agrupa por dia; agg calcula, para cada dia, a média e a quantidade de valores.
        diario = serie.resample("D").agg(["mean", "count"])
        return diario.loc[diario["count"] >= MINIMO_HORAS_MEDIA_24H, "mean"]
    if limites.horas == 8:
        # Para a média móvel precisamos de uma grade horária completa
        # (asfreq("h") cria as horas que faltam, vazias), senão "8 linhas" não seriam "8 horas".
        grade = serie.asfreq("h")
        return grade.rolling(window=8, min_periods=8).mean().dropna()
    return serie.dropna()


def classificar_concentracao(valor: float, codigo: str) -> FaixaQualidade | None:
    """Faixa de uma concentração JÁ calculada no período de média correto do poluente."""
    limites = LIMITES_CONCENTRACAO.get(codigo)
    if limites is None or valor is None or valor != valor or valor < 0:
        return None
    for limite, faixa in zip(limites.limites, FAIXAS_IQAR):
        if valor <= limite:
            return faixa
    return FAIXAS_IQAR[-1]
