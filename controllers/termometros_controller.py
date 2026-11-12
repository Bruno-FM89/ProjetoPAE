"""Controller dos termômetros da comunidade (camada C do MVC).

Como as partes conversam
------------------------
    Página "Temperatura e Umidade" (View)
        │  1. o usuário escolhe termômetros, período e agrupamento
        ▼
    FiltrosTermometros  ──►  TermometrosController  ──►  DadosTermometros / AnaliseTermometros (Model)
        ▲                                            │  2. o Model recorta os dados e calcula
        └──────── 3. tabelas e frases prontas ◄──────┘

O Controller não desenha nada e não faz contas: ele recebe os filtros, pede
ao Model o recorte e os cálculos, troca os ids (T1, T2...) pelos nomes de
exibição e devolve tudo pronto para a View.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from models.estatistica import AnaliseEstatistica
from models.termometros import (
    AGRUPAMENTOS,
    COL_DATA,
    COL_ID,
    COL_TEMP,
    COL_UMID,
    GRANDEZAS,
    AnaliseTermometros,
    DadosTermometros,
)
from services.config import Configuracao

__all__ = ["FiltrosTermometros", "TermometrosController", "AGRUPAMENTOS", "GRANDEZAS", "COL_TEMP", "COL_UMID"]


@dataclass(frozen=True)
class FiltrosTermometros:
    """Escolhas do usuário na página dos termômetros.

    Atributos:
        ids: termômetros escolhidos (ex.: ("T1", "T3")).
        inicio, fim: período (dias inteiros, inclusive).
        agrupamento: "10min", "h", "D", "W" ou "MS" (veja ``AGRUPAMENTOS``).
    """

    ids: tuple[str, ...]
    inicio: date
    fim: date
    agrupamento: str = "D"


class TermometrosController:
    """Coordena os dados dos termômetros e entrega resultados prontos para a tela."""

    def __init__(self, dados: DadosTermometros) -> None:
        self._dados = dados

    @classmethod
    def a_partir_da_configuracao(cls, config: Configuracao) -> "TermometrosController":
        """Cria o Controller usando os caminhos de ``services/config.py``.

        Lança ``ErroFonteDados`` (do Model) se o arquivo de medições não existir;
        o ``app.py`` trata esse erro e mostra uma mensagem amigável.
        """
        return cls(DadosTermometros(
            config.caminho_medicoes_termometros, config.caminho_metadados_termometros, config.caminho_locais_termometros,
        ))

    # --- informações gerais -------------------------------------------------------
    @property
    def ids(self) -> list[str]:
        return self._dados.ids

    def nome(self, tid: str) -> str:
        """Nome de exibição de um termômetro (ex.: "Termômetro 3")."""
        return self._dados.termometro(tid).nome

    def nome_com_regiao(self, tid: str) -> str:
        """Nome + região, se informada (ex.: "Termômetro 3 · Lagoa (a confirmar)")."""
        t = self._dados.termometro(tid)
        if not t.quebrada:
            return t.nome
        return f"{t.nome} · {t.quebrada}" + ("" if t.localizacao_validada else " (a confirmar)")

    def tabela_termometros(self) -> pd.DataFrame:
        return self._dados.tabela_termometros()

    @property
    def metadados(self) -> dict:
        return self._dados.metadados

    def periodo(self, ids: list[str]) -> tuple[date, date]:
        """Do primeiro ao último dia com medição entre os termômetros escolhidos."""
        return self._dados.periodo(list(ids))

    def periodo_comum(self, ids: list[str]) -> tuple[date, date] | None:
        """Dias em que todos os termômetros escolhidos mediram ao mesmo tempo (ou None)."""
        return self._dados.periodo_comum(list(ids))

    @staticmethod
    def grandezas() -> dict:
        return dict(GRANDEZAS)

    @staticmethod
    def agrupamentos() -> dict:
        return dict(AGRUPAMENTOS)

    # --- recorte ------------------------------------------------------------------
    def _recorte(self, f: FiltrosTermometros) -> pd.DataFrame:
        """Pede ao Model as leituras dos termômetros e do período escolhidos."""
        return self._dados.recorte(list(f.ids), f.inicio, f.fim)

    def _analise(self, f: FiltrosTermometros) -> AnaliseTermometros:
        """Cria o objeto de cálculos (Model) para o recorte atual."""
        return AnaliseTermometros(self._recorte(f))

    def sem_dados(self, f: FiltrosTermometros) -> bool:
        """Verdadeiro quando nenhum termômetro escolhido mediu no período."""
        return not f.ids or self._recorte(f).empty

    def ids_sem_dados(self, f: FiltrosTermometros) -> list[str]:
        """Termômetros escolhidos que NÃO têm leitura no período (para avisar o usuário)."""
        com_dados = set(self._recorte(f)[COL_ID].unique())
        return [t for t in f.ids if t not in com_dados]

    def nomes(self) -> dict[str, str]:
        """Dicionário id → nome de exibição (ex.: {"T1": "Termômetro 1"})."""
        return {tid: self.nome(tid) for tid in self.ids}

    def medicoes(self, f: FiltrosTermometros) -> pd.DataFrame:
        """Leituras originais (10 em 10 minutos) do recorte, para histogramas e boxplots."""
        return self._recorte(f)

    def _renomear(self, tabela: pd.DataFrame) -> pd.DataFrame:
        """Troca colunas T1, T2... pelos nomes de exibição (para as legendas dos gráficos)."""
        return tabela.rename(columns={tid: self.nome(tid) for tid in self.ids})

    # --- resultados para a View -------------------------------------------------------
    def resumo(self, f: FiltrosTermometros) -> pd.DataFrame:
        """Média, mínimo, máximo e amplitude de cada termômetro, com o nome de exibição."""
        tabela = self._analise(f).resumo()
        if not tabela.empty:
            tabela.insert(1, "nome", tabela["id"].map(self.nome))
        return tabela

    def serie(self, f: FiltrosTermometros, coluna: str) -> pd.DataFrame:
        """Série no tempo (uma coluna por termômetro), já agrupada conforme ``f.agrupamento``."""
        return self._renomear(self._analise(f).serie(coluna, f.agrupamento))

    def extremos_diarios(self, f: FiltrosTermometros, coluna: str) -> pd.DataFrame:
        """Mínimo, média e máximo de cada dia, por termômetro, com o nome de exibição."""
        tabela = self._analise(f).extremos_diarios(coluna)
        if not tabela.empty:
            tabela["nome"] = tabela[COL_ID].map(self.nome)
        return tabela

    def perfil_horario(self, f: FiltrosTermometros, coluna: str) -> pd.DataFrame:
        """Dia típico: média de cada hora do dia, uma coluna por termômetro (nomes de exibição)."""
        return self._renomear(self._analise(f).perfil_horario(coluna))

    def media_mensal(self, f: FiltrosTermometros, coluna: str) -> pd.DataFrame:
        """Média de cada mês, por termômetro, com o número de leituras usadas."""
        tabela = self._analise(f).media_mensal(coluna)
        if not tabela.empty:
            tabela["nome"] = tabela[COL_ID].map(self.nome)
        return tabela

    def tempo_acima(self, f: FiltrosTermometros, coluna: str, limite: float) -> pd.DataFrame:
        """Quanto tempo cada termômetro ficou acima do valor de referência escolhido pelo usuário."""
        tabela = self._analise(f).tempo_acima(coluna, limite)
        if not tabela.empty:
            tabela.insert(0, "nome", [self.nome(t) for t in tabela.index])
        return tabela

    def amplitude_diaria_media(self, f: FiltrosTermometros, coluna: str) -> pd.Series:
        """Variação média dentro do dia (máximo − mínimo do dia), por termômetro."""
        serie = self._analise(f).amplitude_diaria_media(coluna)
        return serie.rename(index=self.nome)

    def descritiva(self, f: FiltrosTermometros, coluna: str) -> pd.DataFrame:
        """Estatística descritiva de uma medida, por termômetro (linhas com o nome de exibição)."""
        tabela = self._analise(f).descritiva(coluna)
        return tabela.rename(index=self.nome)

    def dados_dispersao(self, f: FiltrosTermometros, tid: str) -> pd.DataFrame:
        """Leituras de UM termômetro (temperatura e umidade) para o gráfico de dispersão.

        Para o gráfico não ficar pesado, usamos a média de cada hora (no máximo
        ~5.300 pontos em 7 meses) em vez das leituras de 10 em 10 minutos.
        """
        d = self._recorte(f)
        d = d[d[COL_ID] == tid].set_index(COL_DATA)[[COL_TEMP, COL_UMID]]
        return d.resample("h").mean().dropna().reset_index()

    def relacao_temp_umid(self, f: FiltrosTermometros, tid: str) -> dict:
        """Relação entre temperatura e umidade de um termômetro, com explicação em palavras.

        Retorna um dicionário: ``r`` (de −1 a +1, ou None), ``n`` (leituras usadas),
        ``classificacao`` (ex.: "forte negativa") e ``frase`` (para leigos).
        """
        r, n = self._analise(f).correlacao_temp_umid(tid)
        if r is None:
            return {"r": None, "n": n, "classificacao": "indefinida", "frase": "Há poucas leituras para calcular a relação."}
        classificacao = AnaliseEstatistica.classificar_correlacao(r)
        if r <= -0.3:
            frase = "Quando a temperatura sobe, a umidade tende a cair (e vice-versa). É o comportamento esperado do ar ao longo do dia."
        elif r >= 0.3:
            frase = "Temperatura e umidade tendem a subir e descer juntas neste local, o que é pouco comum e merece atenção."
        else:
            frase = "Não há uma relação clara entre temperatura e umidade neste local."
        return {"r": r, "n": n, "classificacao": classificacao, "frase": frase}

    def interpretacoes(self, f: FiltrosTermometros, coluna: str) -> list[str]:
        """Frases automáticas sobre o recorte atual (todas calculadas, nada escrito à mão).

        Descrevem o que os números mostram, sem apontar causas.
        """
        resumo = self.resumo(f)
        if resumo.empty:
            return ["Não há medições dos termômetros escolhidos no período."]
        g = GRANDEZAS[coluna]
        un, prefixo = g["unidade"], "temp" if coluna == COL_TEMP else "umid"
        frases = []
        if len(resumo) > 1:
            maior = resumo.loc[resumo[f"{prefixo}_media"].idxmax()]
            menor = resumo.loc[resumo[f"{prefixo}_media"].idxmin()]
            diferenca = maior[f"{prefixo}_media"] - menor[f"{prefixo}_media"]
            frases.append(
                f"A maior {g['nome'].lower()} média foi a do {maior['nome']} ({_num(maior[f'{prefixo}_media'])} {un}) e a "
                f"menor, a do {menor['nome']} ({_num(menor[f'{prefixo}_media'])} {un}): diferença de {_num(diferenca)} {un}."
            )
            comum = self.periodo_comum(list(f.ids))
            if comum is None or comum[0] > f.inicio or comum[1] < f.fim:
                frases.append(
                    "Atenção: nem todos os termômetros mediram durante todo o período escolhido. Para uma comparação justa, "
                    "use a opção “Período em que todos mediram juntos”."
                )
        mais_alto = resumo.loc[resumo[f"{prefixo}_max"].idxmax()]
        mais_baixo = resumo.loc[resumo[f"{prefixo}_min"].idxmin()]
        frases.append(
            f"O valor mais alto registrado foi {_num(mais_alto[f'{prefixo}_max'])} {un} ({mais_alto['nome']}, em "
            f"{_data_hora(mais_alto[f'{prefixo}_quando_max'])}); o mais baixo foi {_num(mais_baixo[f'{prefixo}_min'])} {un} "
            f"({mais_baixo['nome']}, em {_data_hora(mais_baixo[f'{prefixo}_quando_min'])})."
        )
        amplitude = self.amplitude_diaria_media(f, coluna)
        if not amplitude.empty:
            frases.append(
                f"Em média, dentro de um mesmo dia, a {g['nome'].lower()} variou entre {_num(amplitude.min())} e "
                f"{_num(amplitude.max())} {un} de um termômetro para outro (diferença entre o máximo e o mínimo do dia)."
                if len(amplitude) > 1 else
                f"Em média, dentro de um mesmo dia, a {g['nome'].lower()} variou {_num(amplitude.iloc[0])} {un} "
                "(diferença entre o máximo e o mínimo do dia)."
            )
        perfil = self.perfil_horario(f, coluna).mean(axis=1).dropna()
        if len(perfil) >= 12:
            frases.append(
                f"No “dia típico”, a {g['nome'].lower()} costuma ser mais alta por volta das {int(perfil.idxmax())}h e mais "
                f"baixa por volta das {int(perfil.idxmin())}h."
            )
        return frases

    def conferencia_com_aparelho(self) -> pd.DataFrame:
        """Compara as estatísticas calculadas pelo sistema com o resumo gravado pelo próprio aparelho.

        Serve como prova de que a leitura das planilhas está correta: os valores
        devem coincidir. Tolerância: menos de 0,1, porque o aparelho CORTA a média
        na 1ª casa decimal em vez de arredondar (ex.: 21,77 aparece como 21,7).
        """
        linhas = []
        aparelhos = {a["termometro_id"]: a for a in self.metadados.get("aparelhos", [])}
        for tid in self.ids:
            dados = self._dados.medicoes[self._dados.medicoes[COL_ID] == tid]
            resumo = aparelhos.get(tid, {}).get("resumo_do_aparelho", {})
            for coluna, nome in ((COL_TEMP, "temperatura"), (COL_UMID, "umidade")):
                for estat, funcao in (("maximo", "max"), ("minimo", "min"), ("media", "mean")):
                    calculado = getattr(dados[coluna], funcao)()
                    informado = resumo.get(f"{nome}_{estat}")
                    linhas.append({
                        "termometro": self.nome(tid), "grandeza": nome, "estatistica": estat,
                        "calculado_pelo_sistema": round(float(calculado), 2), "informado_pelo_aparelho": informado,
                        "confere": informado is not None and abs(calculado - informado) < 0.1,
                    })
        return pd.DataFrame(linhas)

    # --- tabela e exportação ---------------------------------------------------------------
    def tabela_medicoes(self, f: FiltrosTermometros) -> pd.DataFrame:
        """Medições do recorte, agrupadas conforme ``f.agrupamento``, em formato de tabela legível."""
        d = self._recorte(f)
        if d.empty:
            return pd.DataFrame(columns=["termometro", COL_DATA, COL_TEMP, COL_UMID])
        if f.agrupamento != "10min":
            d = (d.set_index(COL_DATA).groupby(COL_ID)[[COL_TEMP, COL_UMID]].resample(f.agrupamento).mean()
                 .dropna(how="all").round(2).reset_index())
        d.insert(0, "termometro", d[COL_ID].map(self.nome))
        return d.drop(columns=COL_ID)

    def exportar_csv(self, f: FiltrosTermometros) -> bytes:
        """CSV do recorte (separador ``;``, ponto decimal) com uma linha de identificação da fonte."""
        tabela = self.tabela_medicoes(f)
        tabela.insert(1, "fonte", "Termômetros da UNAS em residências de Heliópolis (identificação anônima)")
        return tabela.to_csv(index=False, sep=";", date_format="%Y-%m-%d %H:%M:%S").encode("utf-8")


# --- formatação curta usada nas frases --------------------------------------------------
def _num(valor: float, casas: int = 1) -> str:
    """Número no padrão brasileiro: 21.75 → "21,8"."""
    return f"{valor:,.{casas}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _data_hora(valor) -> str:
    """Timestamp → "13/03/2025 às 15h20"."""
    return pd.Timestamp(valor).strftime("%d/%m/%Y às %Hh%M")
