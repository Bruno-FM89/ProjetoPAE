"""Controller do dashboard (camada C do MVC).

Papel do Controller
-------------------
Ele fica no meio do caminho:

    View (telas)  --Filtros-->  Controller  --pede cálculos-->  Model (dados e estatística)
    View (telas)  <--tabelas--  Controller  <--resultados----  Model

* NÃO desenha nada na tela (isso é da View).
* NÃO faz contas estatísticas (isso é do Model).
* Recebe os filtros escolhidos pelo usuário, busca os dados certos
  (fonte + estação + período), pede os cálculos ao Model e devolve
  tabelas prontas para a View exibir.

Novidades da V2
---------------
* Várias fontes ao mesmo tempo (dados reais do MonitorAr, QUALAR importado,
  banco e demonstração fictícia), com um seletor na tela.
* Várias estações por fonte, nunca misturadas entre si.
* Variáveis descobertas a partir dos dados (nada de colunas fixas).
* Interpretações automáticas calculadas a partir dos números.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from models.conjunto import ConjuntoDados
from models.estatistica import FREQUENCIAS, AnaliseEstatistica
from models.fontes import ErroFonteDados, FonteCSV, FonteDados, FonteMonitorAr, FontePostgres, FonteQualar
from models.localizacao import REFERENCIA_HELIOPOLIS, TIPOS_LOCALIZACAO
from models.parametros import COLUNA_DATA, NOMES_GRANDEZA, Variavel
from models.qualidade_ar import (
    FAIXAS_IQAR,
    LIMITES_CONCENTRACAO,
    classificar_concentracao,
    classificar_indice,
    distribuicao_por_faixa,
    medias_no_periodo_oficial,
    pode_classificar_concentracao,
)
from models.tratamento import MESES_EXTENSO, TratadorDados, nome_coluna_outlier
from services.config import Configuracao

# __all__ lista o que outros módulos podem importar daqui. ErroFonteDados é
# "reexportado" para que a View (app.py) não precise importar nada do Model.
__all__ = ["ErroFonteDados", "Filtros", "PainelController", "TIPOS_DADOS"]

#: Versões dos dados que o usuário pode escolher.
TIPOS_DADOS = {
    "originais": "Originais",
    "tratados": "Tratados",
}

#: Mínimo de registros num mês para ele entrar na frase "maior média mensal".
MINIMO_REGISTROS_MES = 24


@dataclass(frozen=True)
class Filtros:
    """Tudo o que o usuário escolheu na barra lateral, num único objeto.

    Atributos:
        fonte: nome da fonte de dados (ex.: "Dados reais — MonitorAr").
        estacao: identificador da estação dentro da fonte.
        inicio, fim: período (datas, inclusive).
        variavel: chave da variável principal.
        comparar: chaves de outras variáveis para comparação.
        dados: "originais" (padrão) ou "tratados".
        agregacao: "h" (horária), "D" (diária), "W" (semanal) ou "MS" (mensal).
        excluir_outliers: se verdadeiro, valores sinalizados pelo IQR são ignorados.
    """

    fonte: str
    estacao: str
    inicio: date
    fim: date
    variavel: str
    comparar: tuple[str, ...] = ()
    dados: str = "originais"
    agregacao: str = "D"
    excluir_outliers: bool = False

    @property
    def variaveis_selecionadas(self) -> list[str]:
        """Variável principal seguida das de comparação, sem repetir."""
        return [self.variavel, *[c for c in self.comparar if c != self.variavel]]


class PainelController:
    """Coordena fontes, estações, filtros e cálculos.

    Parâmetros do construtor:
        fontes: lista de objetos FonteDados, na ordem de preferência.
        limite_lacuna: maior lacuna (horas) preenchida no modo "tratados".
        fator_iqr: multiplicador do IQR para sinalizar outliers.

    Fontes que falharem são ignoradas com um aviso; se TODAS falharem,
    lança ErroFonteDados explicando o motivo de cada uma.
    """

    def __init__(self, fontes: list[FonteDados], limite_lacuna: int = 4, fator_iqr: float = 1.5) -> None:
        self._limite_lacuna = limite_lacuna
        self._fator_iqr = fator_iqr
        self._avisos: list[str] = []
        self._conjuntos: dict[str, ConjuntoDados] = {}
        self._tipos: dict[str, str] = {}
        # Cache de tratadores: montar um tratador custa um pouco, então
        # guardamos um por combinação (fonte, estação).
        self._tratadores: dict[tuple[str, str], TratadorDados] = {}

        erros = []
        for fonte in fontes:  # tentamos carregar cada fonte; uma falha não derruba as outras
            try:
                registros = fonte.carregar_registros()
            except ErroFonteDados as erro:
                erros.append(f"{fonte.nome}: {erro}")
                continue
            self._conjuntos[fonte.nome] = ConjuntoDados(registros, fonte.nome, fonte.metadados, fonte.transformacoes)
            self._tipos[fonte.nome] = fonte.tipo
        if not self._conjuntos:
            raise ErroFonteDados("Nenhuma fonte de dados pôde ser carregada. " + " | ".join(erros))
        self._avisos.extend(f"Fonte indisponível — {e}" for e in erros)

    @classmethod
    def a_partir_da_configuracao(cls, config: Configuracao) -> "PainelController":
        """Monta a lista de fontes conforme os arquivos existentes e a configuração.

        Ordem: dados reais (MonitorAr) → QUALAR importado → banco → demonstração fictícia.
        Fontes sem arquivo simplesmente não entram (sem erro).
        """
        fontes: list[FonteDados] = []
        avisos: list[str] = []
        if config.caminho_monitorar.is_file():
            fontes.append(FonteMonitorAr(
                "Dados reais — MonitorAr (CETESB)", config.caminho_monitorar,
                config.caminho_estacoes, config.caminho_metadados_monitorar,
            ))
        else:
            avisos.append("Recorte de dados reais não encontrado em data/reais. Veja docs/FONTES_DE_DADOS.md.")
        qualar = FonteQualar("Dados reais — QUALAR importado (CETESB)", config.pasta_qualar, config.caminho_estacoes)
        if qualar.arquivos():
            fontes.append(qualar)
        if config.usa_banco:
            fontes.append(FontePostgres("Banco de dados (PostgreSQL)", config.database_url, config.tabela))
        if config.caminho_csv.is_file():
            fontes.append(FonteCSV("Demonstração — dados fictícios", config.caminho_csv))
        controller = cls(fontes, config.limite_lacuna_horas, config.fator_iqr)
        controller._avisos = avisos + controller._avisos
        return controller

    # =====================================================================
    # Informações gerais (fontes, estações, variáveis)
    # =====================================================================
    @property
    def nomes_fontes(self) -> list[str]:
        return list(self._conjuntos)

    @property
    def avisos(self) -> list[str]:
        return list(self._avisos)

    @property
    def limite_lacuna(self) -> int:
        return self._limite_lacuna

    @property
    def fator_iqr(self) -> float:
        return self._fator_iqr

    @property
    def referencia_heliopolis(self):
        return REFERENCIA_HELIOPOLIS

    @staticmethod
    def opcoes_agregacao() -> dict[str, str]:
        return dict(FREQUENCIAS)

    @staticmethod
    def faixas_iqar():
        return list(FAIXAS_IQAR)

    @staticmethod
    def limites_concentracao():
        return dict(LIMITES_CONCENTRACAO)

    @staticmethod
    def nomes_grandeza() -> dict[str, str]:
        return dict(NOMES_GRANDEZA)

    def tipo_fonte(self, fonte: str) -> str:
        return self._tipos[fonte]

    def eh_ficticia(self, fonte: str) -> bool:
        """Verdadeiro quando todos os registros da fonte são fictícios."""
        estacoes = self._conjunto(fonte).estacoes()
        return bool((estacoes["localizacao"] == "ficticio").all())

    def _conjunto(self, fonte: str) -> ConjuntoDados:
        if fonte not in self._conjuntos:
            raise ValueError(f"Fonte desconhecida: {fonte}")
        return self._conjuntos[fonte]

    def estacoes(self, fonte: str) -> pd.DataFrame:
        """Tabela de estações da fonte, da mais próxima à mais distante de Heliópolis."""
        return self._conjunto(fonte).estacoes()

    def estacao_padrao(self, fonte: str) -> str:
        """Estação inicial: a primeira da lista, que é a mais próxima de Heliópolis."""
        return str(self.estacoes(fonte)["estacao_id"].iloc[0])

    def nome_estacao(self, fonte: str, estacao: str) -> str:
        """Nome legível da estação (ex.: "Mooca") a partir do identificador."""
        tabela = self.estacoes(fonte).set_index("estacao_id")
        return str(tabela.loc[estacao, "estacao"]) if estacao in tabela.index else estacao

    def catalogo(self, fonte: str) -> dict[str, Variavel]:
        return self._conjunto(fonte).catalogo

    def variavel(self, fonte: str, chave: str) -> Variavel:
        return self._conjunto(fonte).catalogo[chave]

    def rotulo(self, fonte: str, chave: str) -> str:
        catalogo = self._conjunto(fonte).catalogo
        return catalogo[chave].rotulo if chave in catalogo else chave

    def variaveis(self, fonte: str, estacao: str) -> list[str]:
        """Indicadores (variáveis) que a estação mede nesta fonte."""
        return self._conjunto(fonte).variaveis_da_estacao(estacao)

    def cobertura(self, fonte: str, estacao: str) -> pd.DataFrame:
        """Quantas horas têm valor em cada indicador da estação (mostra o tamanho das lacunas)."""
        return self._conjunto(fonte).cobertura(estacao)

    def variavel_padrao(self, fonte: str, estacao: str) -> str:
        """A variável com mais horas com valor (a mais completa) é a escolha inicial."""
        cob = self.cobertura(fonte, estacao)
        return str(cob.sort_values("horas_com_valor", ascending=False)["chave"].iloc[0])

    def periodo_disponivel(self, fonte: str, estacao: str) -> tuple[date, date]:
        """Primeiro e último dia com registro na estação."""
        larga = self._conjunto(fonte).tabela_larga(estacao)
        return larga[COLUNA_DATA].min().date(), larga[COLUNA_DATA].max().date()

    def contexto(self, filtros: Filtros) -> dict:
        """Tudo o que a tela precisa para dizer DE ONDE vêm os dados mostrados."""
        conjunto = self._conjunto(filtros.fonte)
        estacoes = conjunto.estacoes().set_index("estacao_id")
        info = estacoes.loc[filtros.estacao].to_dict()
        return {
            "fonte": filtros.fonte,
            "tipo_fonte": self._tipos[filtros.fonte],
            "metadados": conjunto.metadados,
            "estacao": info["estacao"],
            "municipio": info["municipio"],
            "endereco": info["endereco"],
            "latitude": info["latitude"],
            "longitude": info["longitude"],
            "fonte_localizacao": info["fonte_localizacao"],
            "localizacao": info["localizacao"],
            "tipo_localizacao": TIPOS_LOCALIZACAO.get(info["localizacao"], "não informado"),
            "distancia_km": info["distancia_km"],
            "periodo_disponivel": self.periodo_disponivel(filtros.fonte, filtros.estacao),
            "transformacoes": conjunto.transformacoes,
        }

    # =====================================================================
    # Dados filtrados
    # =====================================================================
    def _tratador(self, fonte: str, estacao: str) -> TratadorDados:
        """Devolve (criando só na primeira vez) o objeto que prepara as versões original e tratada da estação."""
        chave = (fonte, estacao)
        if chave not in self._tratadores:
            larga = self._conjunto(fonte).tabela_larga(estacao)
            colunas = [c for c in larga.columns if c != COLUNA_DATA]
            self._tratadores[chave] = TratadorDados(larga, colunas, self._limite_lacuna, self._fator_iqr)
        return self._tratadores[chave]

    def colunas(self, filtros: Filtros) -> list[str]:
        """Variáveis disponíveis na estação escolhida."""
        return self._tratador(filtros.fonte, filtros.estacao).colunas

    def relatorio_integridade(self, filtros: Filtros):
        """Relatório de lacunas, horas vazias e valores preenchidos da estação escolhida."""
        return self._tratador(filtros.fonte, filtros.estacao).relatorio

    def dados_filtrados(self, filtros: Filtros, tipo: str | None = None, aplicar_exclusao: bool = True) -> pd.DataFrame:
        """Tabela larga da estação no período escolhido.

        Parâmetros:
            filtros: escolhas do usuário.
            tipo: força "originais" ou "tratados" (senão usa ``filtros.dados``).
            aplicar_exclusao: se ``False``, ignora a opção de excluir outliers.

        Retorna:
            Tabela (pode ter zero linhas se o período não tiver registros).
            Com ``excluir_outliers``, cada valor sinalizado vira ausente apenas
            na própria variável; as outras variáveis da mesma hora continuam.
        """
        tipo = tipo or filtros.dados
        if tipo not in TIPOS_DADOS:
            raise ValueError(f"Tipo de dados inválido: {tipo}")
        tratador = self._tratador(filtros.fonte, filtros.estacao)
        df = tratador.tratado if tipo == "tratados" else tratador.original
        inicio = pd.Timestamp(filtros.inicio)
        fim = pd.Timestamp(filtros.fim) + pd.Timedelta(days=1)  # +1 dia para incluir o dia final inteiro
        recorte = df[(df[COLUNA_DATA] >= inicio) & (df[COLUNA_DATA] < fim)].copy()
        if aplicar_exclusao and filtros.excluir_outliers:
            for coluna in tratador.colunas:
                recorte.loc[recorte[nome_coluna_outlier(coluna)], coluna] = np.nan
        return recorte.reset_index(drop=True)

    def sem_dados(self, filtros: Filtros) -> bool:
        """Verdadeiro se o período não tem nenhuma hora com valor em nenhuma variável."""
        df = self.dados_filtrados(filtros)
        return df.empty or df[self.colunas(filtros)].isna().all().all()

    def tem_valores(self, filtros: Filtros, chave: str) -> bool:
        """Verdadeiro se o indicador tem pelo menos um valor no período escolhido."""
        df = self.dados_filtrados(filtros)
        return chave in df and df[chave].notna().any()

    def _analise(self, filtros: Filtros, df: pd.DataFrame | None = None) -> AnaliseEstatistica:
        """Cria o objeto de cálculos estatísticos (Model) para o recorte atual."""
        dados = self.dados_filtrados(filtros) if df is None else df
        return AnaliseEstatistica(dados, self.catalogo(filtros.fonte))

    # =====================================================================
    # Resultados para a View
    # =====================================================================
    def indicadores(self, filtros: Filtros) -> dict:
        """Resumo do período: horas, datas e, por variável, média, mediana, cobertura e faixa."""
        df = self.dados_filtrados(filtros)
        if df.empty:
            return {}
        colunas = self.colunas(filtros)
        desc = self._analise(filtros, df).descritiva(colunas)
        catalogo = self.catalogo(filtros.fonte)
        por_variavel = {}
        for chave in colunas:
            linha = desc.loc[chave]
            item = {
                "media": linha["media"], "mediana": linha["mediana"], "maximo": linha["maximo"],
                "n": int(linha["n"]), "cobertura": linha["n"] / len(df) * 100,
            }
            if catalogo[chave].eh_indice and linha["n"]:
                dist = distribuicao_por_faixa(df[chave])
                item["percentual_boa"] = float(dist.loc[0, "percentual"])
                item["faixa_maximo"] = classificar_indice(linha["maximo"])
                item["faixa_mediana"] = classificar_indice(linha["mediana"])
            por_variavel[chave] = item
        return {
            "horas": int(len(df)),
            "horas_com_algum_valor": int(df[colunas].notna().any(axis=1).sum()),
            "inicio": df[COLUNA_DATA].min(),
            "fim": df[COLUNA_DATA].max(),
            "variaveis": por_variavel,
        }

    def serie_temporal(self, filtros: Filtros, colunas: list[str] | None = None) -> pd.DataFrame:
        """Série no tempo dos indicadores, agrupada como o usuário escolheu (horária, diária, semanal ou mensal)."""
        return self._analise(filtros).serie_temporal(colunas or filtros.variaveis_selecionadas, filtros.agregacao)

    def pontos_outliers(self, filtros: Filtros, colunas: list[str]) -> dict[str, pd.DataFrame]:
        """Pontos sinalizados em cada variável (vazio se o usuário excluiu os outliers)."""
        if filtros.excluir_outliers:
            return {}
        df = self.dados_filtrados(filtros)
        return {c: df.loc[df[nome_coluna_outlier(c)], [COLUNA_DATA, c]] for c in colunas}

    def padroes(self, filtros: Filtros) -> dict[str, pd.DataFrame]:
        """Médias por hora do dia, dia da semana e mês do ano, média de cada mês e calendário diário do indicador principal."""
        analise = self._analise(filtros)
        v = filtros.variavel
        return {
            "hora": analise.media_por_hora(v),
            "dia_semana": analise.media_por_dia_semana(v),
            "mes": analise.media_por_mes(v),
            "mensal": analise.media_mensal(v),
            "calendario": analise.calendario_diario(v),
        }

    def descritiva(self, filtros: Filtros, colunas: list[str] | None = None) -> pd.DataFrame:
        """Estatística descritiva (média, mediana, moda, desvio padrão, quartis...) de cada indicador no período."""
        return self._analise(filtros).descritiva(colunas or self.colunas(filtros))

    def resumo_outliers(self, filtros: Filtros) -> pd.DataFrame:
        """Limites do IQR (calculados com TODOS os dados da estação) e contagem no período."""
        tratador = self._tratador(filtros.fonte, filtros.estacao)
        limites = tratador.limites_tratado if filtros.dados == "tratados" else tratador.limites_original
        df = self.dados_filtrados(filtros, aplicar_exclusao=False)
        return self._analise(filtros, df).resumo_outliers(limites, tratador.colunas)

    def comparar_original_tratado(self, filtros: Filtros) -> pd.DataFrame:
        """Estatísticas das duas versões no mesmo período, lado a lado."""
        colunas = self.colunas(filtros)
        original = self._analise(filtros, self.dados_filtrados(filtros, "originais", False)).descritiva(colunas)
        tratado = self._analise(filtros, self.dados_filtrados(filtros, "tratados", False)).descritiva(colunas)
        return pd.DataFrame(
            {
                "Registros válidos (original)": original["n"],
                "Registros válidos (tratado)": tratado["n"],
                "Média (original)": original["media"],
                "Média (tratado)": tratado["media"],
                "Mediana (original)": original["mediana"],
                "Mediana (tratado)": tratado["mediana"],
                "Desvio padrão (original)": original["desvio_padrao"],
                "Desvio padrão (tratado)": tratado["desvio_padrao"],
            }
        )

    def correlacao(self, filtros: Filtros, colunas: list[str], metodo: str = "pearson") -> pd.DataFrame:
        """Matriz de correlação entre indicadores (Pearson ou Spearman); pares com menos de 30 horas em comum ficam vazios."""
        return self._analise(filtros).correlacao(colunas, metodo)

    def pares_correlacionados(self, filtros: Filtros, colunas: list[str], metodo: str = "pearson") -> pd.DataFrame:
        """Pares de indicadores ordenados da correlação mais forte para a mais fraca."""
        return self._analise(filtros).pares_correlacionados(colunas, metodo)

    def correlacao_entre(self, filtros: Filtros, a: str, b: str, metodo: str = "pearson") -> tuple[float, int]:
        """Correlação entre duas variáveis e quantas horas em comum foram usadas."""
        df = self.dados_filtrados(filtros)
        pares = int(df[[a, b]].dropna().shape[0]) if a != b else int(df[a].notna().sum())
        if a == b:
            return 1.0, pares
        return float(self._analise(filtros, df).correlacao([a, b], metodo).loc[a, b]), pares

    # --- qualidade do ar (faixas oficiais) ------------------------------------
    def distribuicao_faixas(self, filtros: Filtros, chave: str) -> pd.DataFrame | None:
        """Quantos registros caem em cada faixa N1–N5 (só para variáveis de índice)."""
        if not self.variavel(filtros.fonte, chave).eh_indice:
            return None
        return distribuicao_por_faixa(self.dados_filtrados(filtros)[chave])

    def classificacao_concentracao(self, filtros: Filtros, chave: str) -> tuple[pd.DataFrame | None, str]:
        """Classifica concentrações usando o período de média OFICIAL do poluente.

        Retorna (tabela, mensagem). A tabela é ``None`` quando não é possível
        classificar; a mensagem diz por quê (ex.: unidade não confirmada).
        """
        v = self.variavel(filtros.fonte, chave)
        codigo = v.parametro.codigo
        if v.eh_indice:
            return None, "Esta variável já é um índice: use as faixas do IQAr."
        if codigo not in LIMITES_CONCENTRACAO:
            return None, f"Não há faixas oficiais de concentração para {v.parametro.sigla} na tabela da CETESB."
        if not pode_classificar_concentracao(codigo, v.unidade, v.unidade_confirmada):
            return None, (
                f"Classificação indisponível: a unidade de {v.parametro.sigla} não foi confirmada pela fonte "
                f"ou é diferente da unidade dos limites oficiais ({LIMITES_CONCENTRACAO[codigo].unidade})."
            )
        serie = self.dados_filtrados(filtros).set_index(COLUNA_DATA)[chave]
        medias = medias_no_periodo_oficial(serie, codigo)
        if medias.empty:
            return None, f"Não há horas suficientes para calcular a {LIMITES_CONCENTRACAO[codigo].periodo}."
        faixas = medias.map(lambda x: classificar_concentracao(x, codigo).rotulo)
        tabela = faixas.value_counts().reindex([f.rotulo for f in FAIXAS_IQAR], fill_value=0).rename("quantidade").reset_index()
        tabela.columns = ["faixa", "quantidade"]
        return tabela, f"Classificação feita sobre a {LIMITES_CONCENTRACAO[codigo].periodo} ({len(medias)} médias calculadas)."

    def um_poluente_por_hora(self, fonte: str) -> bool:
        """Verdadeiro quando a fonte traz o índice de um único poluente por hora (caso do MonitorAr)."""
        return bool(self._conjunto(fonte).metadados.get("um_poluente_por_hora", False))

    def motivo_sem_correlacao(self, fonte: str, a: str | None = None, b: str | None = None) -> str | None:
        """Explica por que uma correlação NÃO deve ser calculada nesta fonte (ou ``None`` se pode).

        Nos dados do MonitorAr cada hora traz um único poluente, então:
        * dois poluentes diferentes nunca têm valor na mesma hora;
        * o "IQAr da estação" é formado pelos próprios valores dos poluentes,
          e compará-lo com um deles daria r = 1 sem nenhum significado.
        """
        if not self.um_poluente_por_hora(fonte):
            return None
        catalogo = self.catalogo(fonte)
        if a is not None and b is not None and not (catalogo[a].eh_indice and catalogo[b].eh_indice):
            return None
        return (
            "Nesta fonte, cada hora traz o índice de um único poluente e o “IQAr da estação” é formado por esses mesmos "
            "valores. Por isso a correlação entre esses indicadores não tem significado: poluentes diferentes nunca "
            "aparecem na mesma hora, e o IQAr comparado com um poluente repetiria os mesmos números (r = 1)."
        )

    def poluente_registrado(self, filtros: Filtros) -> pd.DataFrame | None:
        """Qual poluente teve o índice registrado em cada hora do dia (só para fontes de índice).

        Retorna uma tabela longa com ``hora``, ``poluente`` e ``horas`` (quantidade),
        ou ``None`` se a estação não tiver índices por poluente.
        """
        catalogo = self.catalogo(filtros.fonte)
        colunas = [c for c in self.colunas(filtros) if catalogo[c].eh_indice and not catalogo[c].eh_indice_estacao]
        if not colunas:
            return None
        df = self.dados_filtrados(filtros, aplicar_exclusao=False)
        valores = df[colunas]
        com_valor = valores.notna().any(axis=1)
        if not com_valor.any():
            return pd.DataFrame(columns=["hora", "poluente", "horas"])
        # idxmax(axis=1) dá, para cada linha, a coluna com o maior valor (o poluente com maior índice).
        poluente = valores[com_valor].fillna(-1).idxmax(axis=1).map(lambda c: catalogo[c].parametro.sigla)
        tabela = pd.DataFrame({"hora": df.loc[com_valor, "hora"], "poluente": poluente})
        return tabela.groupby(["hora", "poluente"]).size().rename("horas").reset_index()

    # --- comparação entre estações -----------------------------------------
    def comparar_estacoes(self, filtros: Filtros, chave: str, estacoes: list[str]) -> pd.DataFrame:
        """Mesma variável em várias estações da MESMA fonte, lado a lado (nunca somadas ou misturadas).

        Retorna uma tabela com ``Data`` e uma coluna por estação (nome da estação),
        já agrupada conforme ``filtros.agregacao``.
        """
        series = []
        for estacao in estacoes:
            if chave not in self.variaveis(filtros.fonte, estacao):
                continue
            f = Filtros(**{**filtros.__dict__, "estacao": estacao})
            df = self.dados_filtrados(f)
            if df.empty:
                continue
            serie = AnaliseEstatistica(df, self.catalogo(f.fonte)).serie_temporal([chave], filtros.agregacao)
            series.append(serie.set_index(COLUNA_DATA)[chave].rename(self.nome_estacao(filtros.fonte, estacao)))
        if not series:
            return pd.DataFrame(columns=[COLUNA_DATA])
        return pd.concat(series, axis=1).reset_index().rename(columns={"index": COLUNA_DATA})

    # --- interpretações automáticas -------------------------------------------
    def interpretacoes(self, filtros: Filtros, chave: str | None = None) -> list[str]:
        """Frases calculadas a partir dos dados do recorte atual.

        Nenhum número é escrito à mão: tudo sai dos cálculos. As frases
        descrevem o que os dados mostram, sem apontar causas.
        """
        chave = chave or filtros.variavel
        df = self.dados_filtrados(filtros)
        if df.empty or chave not in df or df[chave].notna().sum() == 0:
            return ["Não há valores desta variável no período escolhido."]
        v = self.variavel(filtros.fonte, chave)
        analise = self._analise(filtros, df)
        frases = []
        n, total = int(df[chave].notna().sum()), len(df)
        cobertura = n / total * 100
        frase = f"{v.parametro.sigla} tem valor em {_pct(cobertura)} das horas do período ({_int(n)} de {_int(total)})."
        if cobertura < 50:
            frase += " Como faltam muitas horas, as médias podem não representar bem todo o período."
        frases.append(frase)

        mensal = analise.media_mensal(chave)
        mensal = mensal[mensal["n"] >= MINIMO_REGISTROS_MES]
        if len(mensal) >= 2:
            maior, menor = mensal.loc[mensal["media"].idxmax()], mensal.loc[mensal["media"].idxmin()]
            frases.append(
                f"A maior média mensal ocorreu em {_mes(maior['mes'])} ({_num(maior['media'])}) e a menor em "
                f"{_mes(menor['mes'])} ({_num(menor['media'])}), considerando os meses com pelo menos "
                f"{MINIMO_REGISTROS_MES} registros."
            )

        hora = analise.media_por_hora(chave).dropna(subset=["media"])
        if len(hora) >= 12:
            alta, baixa = hora.loc[hora["media"].idxmax()], hora.loc[hora["media"].idxmin()]
            frase = (
                f"Por hora do dia, a média mais alta aparece às {int(alta['hora'])}h ({_num(alta['media'])}) "
                f"e a mais baixa às {int(baixa['hora'])}h ({_num(baixa['media'])})."
            )
            if hora["n"].min() > 0 and hora["n"].max() / hora["n"].min() > 2:
                frase += (
                    f" Atenção: a quantidade de registros muda muito conforme a hora (de {_int(hora['n'].min())} "
                    f"a {_int(hora['n'].max())}), o que pode influenciar essa comparação."
                )
            frases.append(frase)

        if v.eh_indice and not v.eh_indice_estacao and self.um_poluente_por_hora(filtros.fonte):
            frases.append(
                f"Atenção: neste arquivo cada hora traz o índice de um único poluente. Os valores de "
                f"{v.parametro.sigla} só existem nas horas em que ele foi o poluente registrado, então "
                "esta média não descreve o comportamento do poluente em todas as horas."
            )
        if v.eh_indice:
            dist = distribuicao_por_faixa(df[chave])
            maximo = df[chave].max()
            faixa_max = classificar_indice(maximo)
            frases.append(
                f"{_pct(dist.loc[0, 'percentual'])} dos registros ficaram na faixa {FAIXAS_IQAR[0].rotulo}; "
                f"o maior índice registrado foi {_num(maximo, 0)} ({faixa_max.rotulo if faixa_max else '—'})."
            )
        desc = analise.descritiva([chave]).loc[chave]
        texto = AnaliseEstatistica.comparar_media_mediana(desc["media"], desc["mediana"])
        if texto:
            frases.append(texto)
        return frases

    @staticmethod
    def classificar_correlacao(r: float) -> str:
        return AnaliseEstatistica.classificar_correlacao(r)

    @staticmethod
    def comparar_media_mediana(media: float, mediana: float) -> str:
        return AnaliseEstatistica.comparar_media_mediana(media, mediana)

    # =====================================================================
    # Tabela e exportação
    # =====================================================================
    def tabela_detalhada(self, filtros: Filtros, colunas: list[str] | None = None, incluir_marcacoes: bool = False) -> pd.DataFrame:
        """Recorte atual com colunas de identificação (estação, município, tipo de local, fonte)."""
        df = self.dados_filtrados(filtros)
        selecionadas = colunas or self.colunas(filtros)
        saida = df[[COLUNA_DATA, *selecionadas]].copy()
        if incluir_marcacoes:
            for c in selecionadas:
                saida[nome_coluna_outlier(c)] = df[nome_coluna_outlier(c)]
            saida["n_imputados"] = df["n_imputados"]
        ctx = self.contexto(filtros)
        # insert(posição, nome, valor) coloca a coluna numa posição específica.
        saida.insert(1, "estacao", ctx["estacao"])
        saida.insert(2, "municipio", ctx["municipio"])
        saida.insert(3, "tipo_de_local", ctx["tipo_localizacao"])
        saida.insert(4, "fonte", ctx["fonte"])
        return saida

    def exportar_csv(self, filtros: Filtros, colunas: list[str] | None = None, incluir_marcacoes: bool = False) -> bytes:
        """CSV do recorte atual (separador ``;`` e ponto decimal, como o arquivo da V1).

        As colunas de identificação garantem que o arquivo exportado nunca seja
        confundido com medições feitas dentro de Heliópolis.
        """
        tabela = self.tabela_detalhada(filtros, colunas, incluir_marcacoes)
        return tabela.to_csv(index=False, sep=";", date_format="%Y-%m-%d %H:%M:%S").encode("utf-8")


# --- formatação curta usada nas frases ------------------------------------------
def _num(valor: float, casas: int = 1) -> str:
    """Número no padrão brasileiro: 1234.5 → "1.234,5"."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def _int(valor) -> str:
    return _num(float(valor), 0)


def _pct(valor: float) -> str:
    return f"{_num(valor, 0)}%"


def _mes(data: pd.Timestamp) -> str:
    """Ex.: Timestamp('2024-07-01') → "julho de 2024"."""
    return f"{MESES_EXTENSO[data.month - 1]} de {data.year}"
