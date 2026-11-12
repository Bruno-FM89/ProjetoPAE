"""Termômetros da comunidade: leitura das planilhas e cálculos (Model).

De onde vêm estes dados
-----------------------
A UNAS instalou registradores de temperatura e umidade (modelo RC-51H) em
residências de Heliópolis. Cada aparelho mede a temperatura (°C) e a umidade
relativa do ar (%) a cada 10 minutos e guarda tudo na memória. Depois, o
programa do fabricante exporta uma planilha com três abas:

* ``Resumo``  — dados do aparelho e um resumo (máximo, mínimo, média);
* ``Lista``   — a série completa: número da leitura, data/hora, temperatura, umidade;
* ``Gráfico`` — apenas uma imagem (não é usada).

Este arquivo tem duas partes
----------------------------
1. LEITURA (``ler_planilha_rc51h``): transforma a planilha original numa
   tabela limpa. Só é usada pelo script ``scripts/preparar_dados_termometros.py``
   — o app nunca lê as planilhas originais, porque elas ficam fora do
   repositório (os nomes dos arquivos identificam moradores).
2. DADOS E CÁLCULOS (``DadosTermometros`` e ``AnaliseTermometros``): carregam
   o arquivo já preparado (``data/termometros/``) e calculam médias, mínimos,
   máximos, séries por dia/hora etc. O Controller pede esses cálculos e a
   View só desenha o resultado.

Cuidados com os dados (decisões metodológicas)
---------------------------------------------
* Nenhuma medição é inventada: se um termômetro não mediu num dia, o dia fica
  vazio (não preenchemos com médias nem interpolação).
* Termômetros NUNCA são misturados numa média única: cada um representa um
  local diferente. A comparação é sempre lado a lado.
* Os períodos de medição não são iguais para todos os aparelhos. Para comparar
  de forma justa, o sistema oferece o "período em comum", que respeita a DATA
  E A HORA exatas: começa na primeira leitura em que todos já estavam ligados
  e termina na última leitura em que todos ainda estavam ligados. Assim, o
  primeiro e o último dia podem ser dias incompletos, mas são incompletos
  igualmente para todos (nenhum termômetro "ganha" horas a mais).
"""

from __future__ import annotations

import json
import re  # expressões regulares: usadas para tirar números de textos como "32,1°C / 87,8%RH"
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from models.fontes import ErroFonteDados

# Nomes das colunas da tabela preparada (o "formato padrão" usado em todo o sistema).
COL_ID = "termometro_id"
COL_DATA = "data_hora"
COL_TEMP = "temperatura_c"
COL_UMID = "umidade_pct"

#: As duas grandezas medidas. Para cada uma: nome para a tela, unidade e casas decimais.
GRANDEZAS = {
    COL_TEMP: {"nome": "Temperatura", "unidade": "°C", "casas": 1},
    COL_UMID: {"nome": "Umidade relativa do ar", "unidade": "%", "casas": 1},
}

#: Agrupamentos de tempo que o usuário pode escolher (código do pandas → texto da tela).
AGRUPAMENTOS = {
    "10min": "A cada 10 minutos (como o aparelho mediu)",
    "h": "Média de cada hora",
    "D": "Média de cada dia",
    "W": "Média de cada semana",
    "MS": "Média de cada mês",
}

#: Mínimo de leituras para um dia entrar nas médias diárias (144 = dia completo).
#: Dias com menos de metade das leituras (o 1º e o último dia, por exemplo)
#: entram nos gráficos, mas são sinalizados na tabela de cobertura.
LEITURAS_DIA_COMPLETO = 144


# =============================================================================
# 1. Leitura da planilha original (usada só pelo script de preparação)
# =============================================================================
def _numero_br(texto) -> float | None:
    """Converte texto no padrão brasileiro em número: ``"28,6"`` → ``28.6``.

    As planilhas do aparelho guardam os números como TEXTO com vírgula. Se o
    valor estiver vazio ou não for um número, devolve ``None`` (valor ausente).
    """
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return float(texto)
    texto = str(texto).strip().replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _resumo_aparelho(aba) -> dict:
    """Lê a aba "Resumo" e devolve um dicionário com as informações do aparelho.

    A aba não é uma tabela: é um relatório com rótulos espalhados (ex.: na
    coluna A "Modelo" e na B o valor; na D "Intervalo" e na E o valor). Por isso
    percorremos as linhas guardando pares rótulo → valor.
    """
    pares: dict[str, str] = {}
    for linha in aba.iter_rows(values_only=True):
        celulas = [str(c).strip() if c is not None else "" for c in linha]
        # Pares (coluna A, B) e (coluna D, E) do relatório.
        for i_rotulo, i_valor in ((0, 1), (3, 4)):
            if len(celulas) > i_valor and celulas[i_rotulo]:
                pares.setdefault(celulas[i_rotulo], celulas[i_valor])

    def temp_umid(texto: str) -> tuple[float | None, float | None]:
        # "32,1°C / 87,8%RH" → (32.1, 87.8)
        numeros = re.findall(r"-?\d+(?:,\d+)?", texto or "")
        return (_numero_br(numeros[0]) if numeros else None, _numero_br(numeros[1]) if len(numeros) > 1 else None)

    resumo = {}
    for rotulo, chave in (("Máximo", "maximo"), ("Mínimo", "minimo"), ("Média", "media")):
        t, u = temp_umid(pares.get(rotulo, ""))
        resumo[f"temperatura_{chave}"] = t
        resumo[f"umidade_{chave}"] = u
    return {
        "modelo": pares.get("Modelo", ""),
        "tipo_sensor": pares.get("Tipo de Sensor", ""),
        "intervalo": pares.get("Intervalo", ""),
        "fuso_horario": pares.get("Fuso horário", ""),
        "primeira_leitura": pares.get("Primeira leitura", ""),
        "ultima_leitura": pares.get("Ultima leitura", ""),
        "leituras_informadas": int(_numero_br(pares.get("Leituras Atuais")) or 0),
        "resumo_do_aparelho": resumo,
    }


def ler_planilha_rc51h(caminho: Path) -> tuple[pd.DataFrame, dict]:
    """Lê UMA planilha exportada pelo registrador RC-51H.

    Parâmetros:
        caminho: arquivo da planilha. Atenção: os arquivos da UNAS terminam em
            ``.xls``, mas por dentro são do formato novo do Excel (``.xlsx``).
            Por isso abrimos o arquivo "pelo conteúdo", sem confiar na extensão.

    Retorna:
        (tabela, informacoes)
        * tabela: colunas ``data_hora``, ``temperatura_c`` e ``umidade_pct``,
          uma linha por leitura, em ordem de tempo;
        * informacoes: dicionário com modelo, intervalo, fuso, resumo do
          próprio aparelho e a lista de problemas encontrados.

    Lança:
        ErroFonteDados se o arquivo não tiver a aba "Lista" no formato esperado.
    """
    import openpyxl  # importado aqui: só o script de preparação precisa desta biblioteca

    # Abrimos com open(..., "rb") para o openpyxl não recusar a extensão ".xls".
    with open(caminho, "rb") as arquivo:
        livro = openpyxl.load_workbook(arquivo, data_only=True)

    if "Lista" not in livro.sheetnames:
        raise ErroFonteDados(f"{caminho.name}: a aba 'Lista' não foi encontrada (abas: {livro.sheetnames}).")
    informacoes = _resumo_aparelho(livro["Resumo"]) if "Resumo" in livro.sheetnames else {}

    linhas = list(livro["Lista"].iter_rows(values_only=True))
    if not linhas or len(linhas[0]) < 4:
        raise ErroFonteDados(f"{caminho.name}: a aba 'Lista' não tem as 4 colunas esperadas.")
    # Usamos a POSIÇÃO das colunas (Nº, Tempo, Temperatura, Umidade), não o nome,
    # porque o cabeçalho tem símbolos (°C, %RH) que mudam conforme o programa.
    dados = pd.DataFrame([linha[:4] for linha in linhas[1:]], columns=["n", COL_DATA, COL_TEMP, COL_UMID])

    problemas: list[str] = []
    dados[COL_DATA] = pd.to_datetime(dados[COL_DATA], errors="coerce")
    for coluna in (COL_TEMP, COL_UMID):
        dados[coluna] = dados[coluna].map(_numero_br).astype(float)

    sem_data = int(dados[COL_DATA].isna().sum())
    if sem_data:
        problemas.append(f"{sem_data} leitura(s) sem data/hora válida foram descartadas.")
        dados = dados.dropna(subset=[COL_DATA])
    duplicadas = int(dados[COL_DATA].duplicated().sum())
    if duplicadas:
        problemas.append(f"{duplicadas} leitura(s) com data/hora repetida: mantida a primeira.")
        dados = dados.drop_duplicates(subset=[COL_DATA])
    for coluna, nome in ((COL_TEMP, "temperatura"), (COL_UMID, "umidade")):
        ausentes = int(dados[coluna].isna().sum())
        if ausentes:
            problemas.append(f"{ausentes} leitura(s) sem valor de {nome} (mantidas como ausentes).")
    # Valores fisicamente impossíveis viram ausentes (umidade fora de 0–100 %, por exemplo).
    fora = (dados[COL_UMID] < 0) | (dados[COL_UMID] > 100)
    if fora.any():
        problemas.append(f"{int(fora.sum())} umidade(s) fora de 0–100 % marcadas como ausentes.")
        dados.loc[fora, COL_UMID] = float("nan")

    dados = dados.sort_values(COL_DATA).reset_index(drop=True)
    intervalos = dados[COL_DATA].diff().dropna()
    if not intervalos.empty:
        passo = intervalos.mode().iloc[0]  # intervalo mais comum entre leituras
        lacunas = int((intervalos > passo).sum())
        informacoes["intervalo_observado_min"] = passo.total_seconds() / 60
        informacoes["lacunas_na_serie"] = lacunas
        if lacunas:
            problemas.append(f"{lacunas} interrupção(ões) na sequência de leituras (períodos sem medição).")
    if informacoes.get("leituras_informadas") and informacoes["leituras_informadas"] != len(dados):
        problemas.append(
            f"O resumo do aparelho informa {informacoes['leituras_informadas']} leituras, mas a lista tem {len(dados)}."
        )
    informacoes["problemas"] = problemas
    return dados[[COL_DATA, COL_TEMP, COL_UMID]], informacoes


# =============================================================================
# 2. Dados preparados (usados pelo app)
# =============================================================================
@dataclass(frozen=True)
class Termometro:
    """Informações de UM termômetro, como aparecem na tela.

    Atributos:
        id: identificador anônimo (ex.: "T1"). Nunca usamos nomes de moradores.
        nome: nome de exibição (ex.: "Termômetro 1").
        quebrada: região de Heliópolis informada (vazia se ainda não informada).
        localizacao_validada: verdadeiro só quando a UNAS confirmou a quebrada.
        observacao: texto livre (ex.: "região sugerida pelo nome do arquivo").
    """

    id: str
    nome: str
    quebrada: str
    localizacao_validada: bool
    observacao: str


class DadosTermometros:
    """Carrega as medições preparadas e as informações de cada termômetro.

    Parâmetros do construtor:
        caminho_medicoes: ``medicoes_termometros.csv.gz`` (gerado pelo script).
        caminho_metadados: ``metadados_termometros.json`` (gerado pelo script).
        caminho_locais: ``locais_termometros.csv`` (preenchido pela equipe; diz
            em qual quebrada cada termômetro está e se isso foi validado).

    Lança:
        ErroFonteDados se o arquivo de medições não existir ou estiver incompleto.
    """

    def __init__(self, caminho_medicoes: Path, caminho_metadados: Path, caminho_locais: Path) -> None:
        if not Path(caminho_medicoes).is_file():
            raise ErroFonteDados(
                f"Arquivo de medições dos termômetros não encontrado: {caminho_medicoes}. "
                "Gere-o com scripts/preparar_dados_termometros.py (veja o GUIA_MANUTENCAO.md)."
            )
        medicoes = pd.read_csv(caminho_medicoes, parse_dates=[COL_DATA], dtype={COL_ID: str})
        faltando = {COL_ID, COL_DATA, COL_TEMP, COL_UMID} - set(medicoes.columns)
        if faltando:
            raise ErroFonteDados(f"Arquivo de medições sem as colunas: {sorted(faltando)}.")
        self.medicoes = medicoes.sort_values([COL_ID, COL_DATA]).reset_index(drop=True)
        self.metadados = json.loads(Path(caminho_metadados).read_text(encoding="utf-8")) if Path(caminho_metadados).is_file() else {}
        self._termometros = self._ler_locais(caminho_locais)

    def _ler_locais(self, caminho: Path) -> dict[str, Termometro]:
        """Junta os ids encontrados nas medições com as informações de local.

        Se o arquivo de locais não existir (ou não citar algum termômetro), o
        termômetro aparece mesmo assim, com local "não informado".
        """
        locais = pd.read_csv(caminho, sep=";", dtype=str).fillna("") if Path(caminho).is_file() else pd.DataFrame()
        por_id = {linha["termometro_id"]: linha for _, linha in locais.iterrows()} if not locais.empty else {}
        termometros = {}
        for tid in sorted(self.medicoes[COL_ID].unique(), key=_ordem_id):
            linha = por_id.get(tid, {})
            termometros[tid] = Termometro(
                id=tid,
                nome=(linha.get("nome_exibicao") or f"Termômetro {tid.lstrip('T')}").strip(),
                quebrada=(linha.get("quebrada") or "").strip(),
                localizacao_validada=(linha.get("localizacao_validada") or "").strip().lower() in ("sim", "s", "true", "1"),
                observacao=(linha.get("observacao") or "").strip(),
            )
        return termometros

    # --- consultas ------------------------------------------------------------
    @property
    def ids(self) -> list[str]:
        """Identificadores de todos os termômetros, em ordem (T1, T2, ...)."""
        return list(self._termometros)

    def termometro(self, tid: str) -> Termometro:
        return self._termometros[tid]

    def tabela_termometros(self) -> pd.DataFrame:
        """Uma linha por termômetro: nome, região, período, número de leituras.

        É a tabela "quem é quem" mostrada na tela e usada pelo mapa.
        """
        periodo = self.medicoes.groupby(COL_ID)[COL_DATA].agg(["min", "max", "count"])
        linhas = []
        for tid, t in self._termometros.items():
            linhas.append({
                "id": tid, "nome": t.nome, "quebrada": t.quebrada, "localizacao_validada": t.localizacao_validada,
                "observacao": t.observacao, "inicio": periodo.loc[tid, "min"], "fim": periodo.loc[tid, "max"],
                "leituras": int(periodo.loc[tid, "count"]),
            })
        return pd.DataFrame(linhas)

    def periodo(self, ids: list[str]) -> tuple[date, date]:
        """Do primeiro ao último dia com medição, considerando TODOS os termômetros escolhidos."""
        sub = self.medicoes[self.medicoes[COL_ID].isin(ids)]
        return sub[COL_DATA].min().date(), sub[COL_DATA].max().date()

    def periodo_comum(self, ids: list[str]) -> tuple[datetime, datetime] | None:
        """Momento (data E hora) em que TODOS os termômetros escolhidos estavam medindo ao mesmo tempo.

        Exemplo: se o termômetro A mediu de 11/02 18h00 a 21/09 23h10 e o B de
        17/02 19h00 a 28/09 00h10, o período em comum vai de 17/02 19h00 a
        21/09 23h10. Devolve ``None`` se não houver sobreposição (ou se a lista
        estiver vazia).

        Por que devolver a HORA e não só o dia: se devolvêssemos só as datas, o
        recorte pegaria o dia inteiro de 17/02 — incluindo as horas da manhã em
        que o B ainda não estava ligado. A comparação ficaria desequilibrada.

        Lacunas no meio do período (aparelho desligado por algumas horas) NÃO
        mudam esses limites: elas continuam vazias, sem valores inventados.
        """
        sub = self.medicoes[self.medicoes[COL_ID].isin(ids)]
        if sub.empty:
            return None
        limites = sub.groupby(COL_ID)[COL_DATA].agg(["min", "max"])
        inicio, fim = limites["min"].max(), limites["max"].min()  # o mais tardio dos inícios e o mais cedo dos fins
        if inicio > fim:
            return None
        return inicio.to_pydatetime(), fim.to_pydatetime()

    @staticmethod
    def limites(inicio: date | datetime, fim: date | datetime) -> tuple[pd.Timestamp, pd.Timestamp]:
        """Converte o período escolhido em dois instantes: início (incluso) e fim (EXCLUÍDO).

        Duas formas de informar o período:
        * só datas (``date``): vale o dia inteiro — de 00h00 do início até
          23h59 do fim. É o que acontece em "Todo o período" e "Escolher datas";
        * data e hora (``datetime``): vale exatamente aquele instante — é o
          que acontece em "Quando todos mediram juntos".
        """
        # Atenção: datetime é um "tipo filho" de date, por isso testamos datetime primeiro.
        if isinstance(fim, datetime):
            fim_excluido = pd.Timestamp(fim) + pd.Timedelta(microseconds=1)  # inclui a leitura exatamente no fim
        else:
            fim_excluido = pd.Timestamp(fim) + pd.Timedelta(days=1)  # +1 dia para incluir o último dia inteiro
        return pd.Timestamp(inicio), fim_excluido

    def recorte(self, ids: list[str], inicio: date | datetime, fim: date | datetime) -> pd.DataFrame:
        """Medições dos termômetros escolhidos entre ``inicio`` e ``fim`` (inclusive).

        Com datas, pega os dias inteiros; com data e hora, respeita o horário
        exato (veja ``limites``).
        """
        m = self.medicoes
        ini, fim_excluido = self.limites(inicio, fim)
        filtro = m[COL_ID].isin(ids) & (m[COL_DATA] >= ini) & (m[COL_DATA] < fim_excluido)
        return m[filtro].reset_index(drop=True)


def _ordem_id(tid: str) -> tuple:
    """Ordena "T2" antes de "T10" (ordem numérica, não alfabética)."""
    numero = re.sub(r"\D", "", tid)
    return (int(numero) if numero else 0, tid)


# =============================================================================
# 3. Cálculos (sem nenhum código de tela)
# =============================================================================
class AnaliseTermometros:
    """Cálculos estatísticos sobre um recorte de medições.

    Recebe a tabela devolvida por ``DadosTermometros.recorte`` (formato
    "longo": uma linha por leitura de cada termômetro). Cada método devolve uma
    tabela pronta; nenhum deles altera os dados originais.
    """

    def __init__(self, dados: pd.DataFrame) -> None:
        self.dados = dados

    @property
    def vazio(self) -> bool:
        return self.dados.empty

    # --- resumo -----------------------------------------------------------------
    def resumo(self) -> pd.DataFrame:
        """Média, mínimo, máximo e amplitude de temperatura e umidade, por termômetro.

        Amplitude = máximo − mínimo (o tamanho da variação no período).
        Também informa QUANDO ocorreram o máximo e o mínimo, para o usuário
        poder conferir no gráfico.
        """
        if self.vazio:
            return pd.DataFrame()
        linhas = []
        for tid, grupo in self.dados.groupby(COL_ID, sort=False):
            linha = {"id": tid, "leituras": int(len(grupo)), "inicio": grupo[COL_DATA].min(), "fim": grupo[COL_DATA].max()}
            for coluna, prefixo in ((COL_TEMP, "temp"), (COL_UMID, "umid")):
                serie = grupo[coluna].dropna()
                if serie.empty:
                    continue
                linha.update({
                    f"{prefixo}_media": serie.mean(), f"{prefixo}_mediana": serie.median(),
                    f"{prefixo}_min": serie.min(), f"{prefixo}_max": serie.max(),
                    f"{prefixo}_amplitude": serie.max() - serie.min(),
                    # idxmin/idxmax devolvem a linha do menor/maior valor; dela tiramos a data/hora.
                    f"{prefixo}_quando_min": grupo.loc[serie.idxmin(), COL_DATA],
                    f"{prefixo}_quando_max": grupo.loc[serie.idxmax(), COL_DATA],
                })
            linhas.append(linha)
        return pd.DataFrame(linhas)

    def descritiva(self, coluna: str) -> pd.DataFrame:
        """Estatística descritiva completa de UMA grandeza, por termômetro.

        Colunas: n, média, mediana, desvio padrão, 1º quartil, 3º quartil, mínimo, máximo.
        """
        if self.vazio:
            return pd.DataFrame()
        g = self.dados.groupby(COL_ID, sort=False)[coluna]
        return pd.DataFrame({
            "n": g.count(), "media": g.mean(), "mediana": g.median(), "desvio_padrao": g.std(),
            "q1": g.quantile(0.25), "q3": g.quantile(0.75), "minimo": g.min(), "maximo": g.max(),
        })

    # --- séries no tempo ----------------------------------------------------------
    def serie(self, coluna: str, agrupamento: str = "D") -> pd.DataFrame:
        """Série no tempo com uma coluna por termômetro (formato "largo").

        Parâmetros:
            coluna: ``temperatura_c`` ou ``umidade_pct``.
            agrupamento: chave de ``AGRUPAMENTOS`` ("10min", "h", "D", "W", "MS").

        Como funciona: ``pivot_table`` coloca cada termômetro numa coluna e
        ``resample`` junta as leituras de cada hora/dia/semana/mês calculando a
        média. Períodos sem nenhuma leitura ficam vazios (NaN) — não são preenchidos.
        """
        if self.vazio:
            return pd.DataFrame()
        larga = self.dados.pivot_table(index=COL_DATA, columns=COL_ID, values=coluna, aggfunc="mean")
        if agrupamento != "10min":
            larga = larga.resample(agrupamento).mean()
        larga.columns.name = None
        return larga

    def extremos_diarios(self, coluna: str) -> pd.DataFrame:
        """Mínimo, média e máximo de CADA DIA, por termômetro (formato longo).

        Útil para ver a variação dentro do dia: a faixa entre o mínimo e o
        máximo mostra quanto a temperatura (ou umidade) mudou naquele dia.
        Inclui ``leituras`` para sinalizar dias incompletos.
        """
        if self.vazio:
            return pd.DataFrame()
        d = self.dados.assign(dia=self.dados[COL_DATA].dt.floor("D"))
        tabela = d.groupby([COL_ID, "dia"])[coluna].agg(minimo="min", media="mean", maximo="max", leituras="count").reset_index()
        tabela["amplitude"] = tabela["maximo"] - tabela["minimo"]
        return tabela

    def amplitude_diaria_media(self, coluna: str) -> pd.Series:
        """Média, por termômetro, da diferença entre o máximo e o mínimo de cada dia.

        Só usa dias completos (144 leituras), para que um dia com poucas horas
        medidas não pareça ter variado pouco.
        """
        tabela = self.extremos_diarios(coluna)
        if tabela.empty:
            return pd.Series(dtype=float)
        completos = tabela[tabela["leituras"] >= LEITURAS_DIA_COMPLETO]
        return completos.groupby(COL_ID)["amplitude"].mean()

    def perfil_horario(self, coluna: str) -> pd.DataFrame:
        """"Dia típico": média de cada hora do dia (0h a 23h), por termômetro.

        Junta todos os dias do período. Ex.: o valor das 14h é a média de todas
        as leituras feitas entre 14h00 e 14h59.
        """
        if self.vazio:
            return pd.DataFrame()
        d = self.dados.assign(hora=self.dados[COL_DATA].dt.hour)
        tabela = d.pivot_table(index="hora", columns=COL_ID, values=coluna, aggfunc="mean")
        tabela.columns.name = None
        return tabela

    def media_mensal(self, coluna: str) -> pd.DataFrame:
        """Média de cada mês do calendário, por termômetro (formato longo, com nº de leituras)."""
        if self.vazio:
            return pd.DataFrame()
        d = self.dados.assign(mes=self.dados[COL_DATA].dt.to_period("M").dt.to_timestamp())
        return d.groupby([COL_ID, "mes"])[coluna].agg(media="mean", leituras="count").reset_index()

    def tempo_acima(self, coluna: str, limite: float) -> pd.DataFrame:
        """Quanto tempo cada termômetro ficou ACIMA de um limite escolhido pelo usuário.

        Como o aparelho mede a cada 10 minutos, cada leitura representa ~10
        minutos. Horas = leituras acima do limite × 10 / 60.
        """
        if self.vazio:
            return pd.DataFrame()
        g = self.dados.groupby(COL_ID, sort=False)[coluna]
        acima = g.apply(lambda s: int((s > limite).sum()))
        total = g.count()
        return pd.DataFrame({
            "leituras_acima": acima, "percentual": acima / total * 100, "horas_aprox": acima * 10 / 60,
            "dias_com_ocorrencia": self.dados[self.dados[coluna] > limite].groupby(COL_ID)[COL_DATA].apply(lambda s: s.dt.date.nunique()).reindex(acima.index, fill_value=0),
        })

    def correlacao_temp_umid(self, tid: str) -> tuple[float | None, int]:
        """Relação entre temperatura e umidade de UM termômetro (correlação de Pearson).

        Retorna (r, n): r vai de −1 a +1 e n é o número de leituras usadas.
        r negativo = quando a temperatura sobe, a umidade tende a cair.
        Devolve r = None se houver menos de 30 leituras com os dois valores.
        """
        par = self.dados.loc[self.dados[COL_ID] == tid, [COL_TEMP, COL_UMID]].dropna()
        if len(par) < 30:
            return None, len(par)
        return float(par[COL_TEMP].corr(par[COL_UMID])), len(par)
