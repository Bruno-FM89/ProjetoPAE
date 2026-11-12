"""Verificação de integridade, tratamento opcional e sinalização de outliers (Model).

Princípios (iguais aos da V1, agora para qualquer conjunto de variáveis)
-----------------------------------------------------------------------
* Os dados ORIGINAIS são preservados. O tratamento gera OUTRA tabela.
* Lacunas NÃO são preenchidas com medianas. A versão "tratada" usa
  interpolação temporal (uma linha reta entre o valor anterior e o seguinte)
  e só em lacunas curtas (até ``limite_lacuna`` horas seguidas). Lacunas
  maiores continuam vazias. Na V2, a versão ORIGINAL é a padrão na tela.
* Outliers (regra do IQR) são SINALIZADOS, nunca removidos: um valor extremo
  pode ser um evento real.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from models.parametros import COLUNA_DATA

# Nomes curtos usados nos gráficos (a ordem importa: segunda-feira primeiro).
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
MESES_EXTENSO = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def nome_coluna_outlier(coluna: str) -> str:
    """Nome da coluna verdadeiro/falso que marca os outliers de ``coluna``."""
    return f"outlier_{coluna}"


@dataclass(frozen=True)
class LimitesIQR:
    """Quartis e "cercas" usadas para sinalizar outliers.

    Atributos:
        q1: 1º quartil (25% dos valores estão abaixo dele).
        q3: 3º quartil (75% dos valores estão abaixo dele).
        iqr: intervalo interquartil = q3 − q1 (onde ficam os 50% centrais).
        inferior: q1 − fator × iqr. Abaixo disso, o valor é sinalizado.
        superior: q3 + fator × iqr. Acima disso, o valor é sinalizado.
    """

    q1: float
    q3: float
    iqr: float
    inferior: float
    superior: float


def limites_iqr(serie: pd.Series, fator: float = 1.5) -> LimitesIQR:
    """Calcula os limites do método IQR para uma série de valores.

    Parâmetros:
        serie: valores numéricos (os ausentes são ignorados).
        fator: multiplicador do IQR (1,5 é o valor clássico de Tukey).

    Retorna:
        LimitesIQR; todos os campos ficam NaN se a série não tiver valores.
    """
    valores = serie.dropna()
    if valores.empty:
        nan = float("nan")
        return LimitesIQR(nan, nan, nan, nan, nan)
    # quantile(0.25) devolve o valor que deixa 25% dos dados abaixo dele.
    q1, q3 = valores.quantile(0.25), valores.quantile(0.75)
    iqr = q3 - q1
    return LimitesIQR(float(q1), float(q3), float(iqr), float(q1 - fator * iqr), float(q3 + fator * iqr))


@dataclass(frozen=True)
class RelatorioIntegridade:
    """Resultado da verificação dos dados brutos de uma estação.

    Cada campo é um número ou dicionário simples, pronto para ser exibido.
    """

    n_linhas: int
    n_colunas: int
    inicio: pd.Timestamp
    fim: pd.Timestamp
    colunas: list[str]
    nulos_por_coluna: dict[str, int]
    datas_duplicadas: int
    horas_faltantes: int
    horas_sem_nenhum_valor: int
    maior_lacuna_horas: dict[str, int]
    valores_negativos: dict[str, int]
    mp25_maior_mp10: int | None
    imputados_por_coluna: dict[str, int] = field(default_factory=dict)
    ausentes_apos_tratamento: dict[str, int] = field(default_factory=dict)

    @property
    def total_nulos(self) -> int:
        return int(sum(self.nulos_por_coluna.values()))

    @property
    def alertas(self) -> list[str]:
        """Frases em linguagem simples sobre os problemas encontrados."""
        avisos: list[str] = []
        if self.datas_duplicadas:
            avisos.append(f"{self.datas_duplicadas} data(s) repetida(s); no tratamento fica só a primeira.")
        if self.horas_faltantes:
            avisos.append(f"Faltam {self.horas_faltantes} hora(s) na sequência horária.")
        negativos = {c: n for c, n in self.valores_negativos.items() if n}
        if negativos:
            detalhe = ", ".join(f"{c}: {n}" for c, n in negativos.items())
            avisos.append(f"Há valores negativos (mantidos, sem correção) — {detalhe}.")
        if self.mp25_maior_mp10:
            avisos.append(
                f"{self.mp25_maior_mp10} registro(s) com concentração de MP2,5 maior que a de MP10. "
                "Como o MP2,5 é uma parte do MP10, isso é incomum; os valores foram mantidos."
            )
        return avisos


def validar(bruto: pd.DataFrame, colunas: list[str]) -> RelatorioIntegridade:
    """Verifica a integridade de uma tabela larga, sem modificá-la.

    Parâmetros:
        bruto: tabela com a coluna ``Data`` e as colunas de ``colunas``.
        colunas: nomes das colunas numéricas a verificar.

    Retorna:
        RelatorioIntegridade com contagens de ausentes, lacunas, duplicatas etc.
    """
    datas = bruto[COLUNA_DATA].sort_values()
    # Quantas horas deveriam existir entre a primeira e a última data.
    horas_esperadas = int((datas.iloc[-1] - datas.iloc[0]) / pd.Timedelta(hours=1)) + 1
    horas_faltantes = max(horas_esperadas - datas.nunique(), 0)

    # Maior sequência de horas seguidas sem valor, para cada coluna.
    maior: dict[str, int] = {}
    for coluna in colunas:
        ausente = bruto[coluna].isna().astype(int)
        # Truque comum: cada vez que o valor muda (ausente ↔ presente) começa um
        # novo grupo; somando os "1" de cada grupo obtemos o tamanho da lacuna.
        grupos = (ausente != ausente.shift()).cumsum()
        maior[coluna] = int(ausente.groupby(grupos).sum().max()) if ausente.any() else 0

    # A comparação MP2,5 > MP10 só faz sentido para CONCENTRAÇÕES na mesma unidade.
    mp25_maior = int((bruto["MP2.5"] > bruto["MP10"]).sum()) if {"MP2.5", "MP10"} <= set(colunas) else None

    return RelatorioIntegridade(
        n_linhas=len(bruto),
        n_colunas=len(colunas) + 1,
        inicio=datas.iloc[0],
        fim=datas.iloc[-1],
        colunas=list(colunas),
        nulos_por_coluna={c: int(bruto[c].isna().sum()) for c in colunas},
        datas_duplicadas=int(bruto[COLUNA_DATA].duplicated().sum()),
        horas_faltantes=horas_faltantes,
        horas_sem_nenhum_valor=int(bruto[colunas].isna().all(axis=1).sum()) if colunas else 0,
        maior_lacuna_horas=maior,
        valores_negativos={c: int((bruto[c] < 0).sum()) for c in colunas},
        mp25_maior_mp10=mp25_maior,
    )


def interpolar_lacunas_curtas(serie: pd.Series, limite: int) -> pd.Series:
    """Interpola no tempo apenas lacunas de até ``limite`` valores seguidos.

    Parâmetros:
        serie: valores com índice de datas ordenado e sem repetições.
        limite: tamanho máximo (em horas) de uma lacuna que pode ser preenchida.

    Retorna:
        Nova série. Lacunas nas pontas (início/fim) e lacunas longas continuam vazias.

    Exemplo: [10, vazio, vazio, 40] com limite 4 → [10, 20, 30, 40].
    """
    # method="time" usa a distância real entre as datas; limit_area="inside"
    # só preenche lacunas que têm valor dos dois lados.
    interpolada = serie.interpolate(method="time", limit_area="inside")
    ausente = serie.isna()
    grupo = (ausente != ausente.shift()).cumsum()
    tamanho_lacuna = ausente.astype(int).groupby(grupo).transform("sum")
    # Desfaz o preenchimento onde a lacuna original era maior que o limite.
    interpolada[ausente & (tamanho_lacuna > limite)] = np.nan
    return interpolada


class TratadorDados:
    """Produz as versões ORIGINAL e TRATADA da tabela de uma estação.

    Parâmetros do construtor:
        bruto: tabela larga (``Data`` + colunas numéricas).
        colunas: nomes das colunas numéricas a tratar.
        limite_lacuna: maior lacuna (em horas) que a interpolação pode preencher.
        fator_iqr: multiplicador do IQR para sinalizar outliers.

    As duas versões ganham colunas auxiliares: ``hora``, ``dia_semana``,
    ``mes_nome``, ``n_imputados`` e uma coluna ``outlier_<variável>`` por variável.
    """

    def __init__(self, bruto: pd.DataFrame, colunas: list[str], limite_lacuna: int = 4, fator_iqr: float = 1.5) -> None:
        faltando = [c for c in [COLUNA_DATA, *colunas] if c not in bruto.columns]
        if faltando:
            raise ValueError(f"Colunas ausentes no dataset: {', '.join(faltando)}")
        if bruto.empty:
            raise ValueError("O dataset está vazio.")

        self._colunas = list(colunas)
        self._limite_lacuna = limite_lacuna
        self._fator_iqr = fator_iqr
        # Ordenamos por data; kind="stable" mantém a ordem original entre datas iguais.
        self._bruto = bruto[[COLUNA_DATA, *colunas]].sort_values(COLUNA_DATA, kind="stable").reset_index(drop=True)
        self._relatorio_base = validar(self._bruto, self._colunas)

        tratado_base = self._tratar()
        self._limites_original = self._calcular_limites(self._bruto)
        self._limites_tratado = self._calcular_limites(tratado_base)
        self._original = self._finalizar(self._bruto, self._limites_original)
        self._tratado = self._finalizar(tratado_base, self._limites_tratado, comparar_com=self._bruto)
        self._relatorio = self._completar_relatorio()

    # --- acesso encapsulado (sempre cópias) ----------------------------------
    @property
    def original(self) -> pd.DataFrame:
        return self._original.copy()

    @property
    def tratado(self) -> pd.DataFrame:
        return self._tratado.copy()

    @property
    def colunas(self) -> list[str]:
        return list(self._colunas)

    @property
    def relatorio(self) -> RelatorioIntegridade:
        return self._relatorio

    @property
    def limites_original(self) -> dict[str, LimitesIQR]:
        return dict(self._limites_original)

    @property
    def limites_tratado(self) -> dict[str, LimitesIQR]:
        return dict(self._limites_tratado)

    @property
    def limite_lacuna(self) -> int:
        return self._limite_lacuna

    @property
    def fator_iqr(self) -> float:
        return self._fator_iqr

    # --- etapas internas ------------------------------------------------------
    def _tratar(self) -> pd.DataFrame:
        """Interpolação temporal das lacunas curtas (datas repetidas: fica a primeira)."""
        base = self._bruto.drop_duplicates(subset=COLUNA_DATA, keep="first").set_index(COLUNA_DATA)
        for coluna in self._colunas:
            base[coluna] = interpolar_lacunas_curtas(base[coluna], self._limite_lacuna)
        return base.reset_index()

    def _calcular_limites(self, df: pd.DataFrame) -> dict[str, LimitesIQR]:
        """Calcula, para cada variável, os limites do IQR (Q1 − fator×IQR e Q3 + fator×IQR) usados para sinalizar outliers."""
        return {c: limites_iqr(df[c], self._fator_iqr) for c in self._colunas}

    def _finalizar(self, df: pd.DataFrame, limites: dict[str, LimitesIQR], comparar_com: pd.DataFrame | None = None) -> pd.DataFrame:
        """Acrescenta colunas auxiliares de tempo, marcação de outliers e contagem de imputados."""
        saida = df.copy()
        datas = saida[COLUNA_DATA]
        saida["hora"] = datas.dt.hour
        # Categorical com ordem definida faz os gráficos mostrarem Seg → Dom e Jan → Dez.
        saida["dia_semana"] = pd.Categorical.from_codes(datas.dt.day_of_week.to_numpy(), categories=DIAS_SEMANA, ordered=True)
        saida["mes_nome"] = pd.Categorical.from_codes((datas.dt.month - 1).to_numpy(), categories=MESES, ordered=True)
        for coluna in self._colunas:
            lim = limites[coluna]
            # Comparações com NaN resultam em False: valores ausentes nunca são outliers.
            saida[nome_coluna_outlier(coluna)] = (saida[coluna] < lim.inferior) | (saida[coluna] > lim.superior)
        if comparar_com is None:
            saida["n_imputados"] = 0
        else:
            antes = comparar_com.drop_duplicates(subset=COLUNA_DATA, keep="first")[self._colunas].isna().to_numpy()
            depois = saida[self._colunas].isna().to_numpy()
            # Estava ausente antes E tem valor agora = foi preenchido pela interpolação.
            saida["n_imputados"] = (antes & ~depois).sum(axis=1)
        return saida

    def _completar_relatorio(self) -> RelatorioIntegridade:
        """Preenche o relatório de integridade com as contagens da versão tratada (valores estimados)."""
        ref = self._original.drop_duplicates(subset=COLUNA_DATA, keep="first").reset_index(drop=True)
        imputados = {c: int((ref[c].isna() & self._tratado[c].notna()).sum()) for c in self._colunas}
        restantes = {c: int(self._tratado[c].isna().sum()) for c in self._colunas}
        # replace() cria uma cópia do relatório (que é imutável) com dois campos novos.
        return replace(self._relatorio_base, imputados_por_coluna=imputados, ausentes_apos_tratamento=restantes)
