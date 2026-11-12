"""Fontes de dados: de onde os registros vêm e como são lidos (Model).

Ideia central (POO)
-------------------
* ``FonteDados`` é a classe-base ABSTRATA: diz o que toda fonte precisa saber
  fazer (``carregar_registros``), sem dizer como.
* Cada subclasse sabe ler um tipo de arquivo (HERANÇA):
    - ``FonteMonitorAr``: dados REAIS do MonitorAr (MMA), recorte das estações da CETESB;
    - ``FonteQualar``: arquivos CSV exportados manualmente do QUALAR (CETESB);
    - ``FonteCSV``: o dataset FICTÍCIO da V1, mantido como demonstração;
    - ``FontePostgres``: banco PostgreSQL/Supabase (estrutura do dataset fictício).
* Todas devolvem a MESMA estrutura de tabela (POLIMORFISMO). O resto do
  sistema chama ``fonte.carregar_registros()`` sem saber qual fonte é.

Formato padrão: "registros" (formato longo)
------------------------------------------
Cada linha é UMA medição: uma estação, uma hora, um parâmetro, um valor.

    estacao_id | estacao | municipio | ... | data_hora | parametro | grandeza | unidade | valor | situacao

Esse formato aceita fontes com quantidades diferentes de variáveis: se um
arquivo não tem temperatura, simplesmente não há linhas de temperatura.
Nenhuma coluna é inventada.
"""

# --- imports ----------------------------------------------------------------
from __future__ import annotations

import json  # lê os metadados (.json) gravados pelo script de preparação
import re  # expressões regulares: usadas para validar o nome de tabela do banco
from abc import ABC, abstractmethod  # ABC = "classe base abstrata"
from io import StringIO  # permite ler um texto já carregado como se fosse um arquivo
from pathlib import Path

import numpy as np
import pandas as pd

from models.parametros import (
    CODIGO_IQAR_ESTACAO,
    COLUNA_DATA,
    COLUNAS_DEMONSTRACAO,
    COLUNAS_ESPERADAS_DEMONSTRACAO,
    GRANDEZA_CONCENTRACAO,
    GRANDEZA_INDICE,
    UNIDADE_INDICE,
    normalizar_codigo,
    normalizar_unidade,
    sem_acentos,
)

#: Colunas da tabela padrão de registros, na ordem em que são produzidas.
COLUNAS_REGISTROS = [
    "estacao_id", "estacao", "municipio", "endereco", "latitude", "longitude",
    "fonte_localizacao", "localizacao", "data_hora", "parametro", "grandeza",
    "unidade", "unidade_confirmada", "valor", "situacao",
]


class ErroFonteDados(Exception):
    """Erro com mensagem amigável quando uma fonte não pode ser lida.

    Herdar de ``Exception`` permite usar ``raise ErroFonteDados("...")`` e
    capturar só esse tipo de erro com ``except ErroFonteDados``.
    """


class FonteDados(ABC):
    """Contrato comum a todas as fontes.

    Atributos (privados, com ``_`` no início; lidos pelas propriedades):
        _nome: nome mostrado na tela (ex.: "Dados reais — MonitorAr").
        _tipo: tipo técnico (CSV, MonitorAr, QUALAR, PostgreSQL).
        _metadados: informações de origem (licença, endereço, data...).
        _transformacoes: lista, em português, de tudo que foi feito com os
            dados na leitura. É exibida na página "Sobre os dados".
    """

    def __init__(self, nome: str, tipo: str) -> None:
        self._nome = nome
        self._tipo = tipo
        self._metadados: dict = {}
        self._transformacoes: list[str] = []

    # @property transforma o método num "atributo somente leitura":
    # escrevemos fonte.nome (sem parênteses) e não conseguimos alterá-lo por fora.
    @property
    def nome(self) -> str:
        return self._nome

    @property
    def tipo(self) -> str:
        return self._tipo

    @property
    def metadados(self) -> dict:
        return dict(self._metadados)  # devolvemos uma cópia para proteger o original

    @property
    def transformacoes(self) -> list[str]:
        return list(self._transformacoes)

    @abstractmethod
    def carregar_registros(self) -> pd.DataFrame:
        """Lê a fonte e devolve uma tabela no formato padrão (COLUNAS_REGISTROS).

        ``@abstractmethod`` obriga cada subclasse a escrever sua própria versão;
        tentar criar um objeto ``FonteDados`` diretamente gera erro.
        """

    def _registrar(self, texto: str) -> None:
        """Anota uma transformação aplicada aos dados (para documentação na tela)."""
        self._transformacoes.append(texto)

    @staticmethod
    def _finalizar_registros(registros: pd.DataFrame, origem: str) -> pd.DataFrame:
        """Confere e organiza a tabela de registros antes de entregá-la.

        * garante que todas as colunas padrão existem e estão na ordem certa;
        * converte data/hora e valor para os tipos corretos;
        * ordena por estação, parâmetro e data.

        Lança ErroFonteDados se a tabela ficou vazia.
        """
        for coluna in COLUNAS_REGISTROS:
            if coluna not in registros.columns:
                registros[coluna] = np.nan
        registros = registros[COLUNAS_REGISTROS].copy()
        registros["data_hora"] = pd.to_datetime(registros["data_hora"])
        registros["valor"] = pd.to_numeric(registros["valor"], errors="coerce")
        registros = registros.dropna(subset=["valor", "data_hora"])
        if registros.empty:
            raise ErroFonteDados(f"A fonte '{origem}' não tem nenhum registro com valor.")
        return registros.sort_values(["estacao_id", "parametro", "grandeza", "data_hora"], kind="stable").reset_index(drop=True)


# ============================================================================
# Dataset fictício (V1) e banco de dados — estrutura "larga"
# ============================================================================
def largo_para_registros(df: pd.DataFrame, estacao: dict) -> pd.DataFrame:
    """Converte a tabela "larga" do dataset fictício para o formato de registros.

    Tabela larga = uma coluna por variável (Data | MP10 | MP2.5 | ... | Umidade).
    Formato de registros = uma linha por medição.

    Parâmetros:
        df: tabela larga com a coluna ``Data`` e as colunas de COLUNAS_DEMONSTRACAO.
        estacao: dicionário com as informações de "local" a repetir em todas as linhas.

    Retorna:
        Tabela no formato padrão, sem as linhas vazias.
    """
    # melt "derrete" a tabela: cada par (data, coluna) vira uma linha com
    # duas colunas novas: "coluna" (o nome da variável) e "valor".
    longo = df.melt(id_vars=[COLUNA_DATA], value_vars=list(COLUNAS_DEMONSTRACAO), var_name="coluna", value_name="valor")
    longo = longo.dropna(subset=["valor"])
    # Para cada nome de coluna, buscamos parâmetro, grandeza e unidade em COLUNAS_DEMONSTRACAO.
    info = longo["coluna"].map(COLUNAS_DEMONSTRACAO)
    longo["parametro"] = info.map(lambda t: t[0])
    longo["grandeza"] = info.map(lambda t: t[1])
    longo["unidade"] = info.map(lambda t: t[2])
    longo["unidade_confirmada"] = info.map(lambda t: t[3])
    longo["data_hora"] = longo[COLUNA_DATA]
    longo["situacao"] = ""
    for campo, valor in estacao.items():
        longo[campo] = valor
    return longo


#: Identificação do "local" fictício: deixa claro que não é medição.
ESTACAO_FICTICIA = {
    "estacao_id": "DEMO",
    "estacao": "Dataset fictício (didático)",
    "municipio": "—",
    "endereco": "—",
    "latitude": np.nan,
    "longitude": np.nan,
    "fonte_localizacao": "não se aplica: dados gerados para fins didáticos",
    "localizacao": "ficticio",
}


class FonteCSV(FonteDados):
    """Lê o dataset FICTÍCIO da V1 (CSV com separador ``;``).

    Foi mantido como "Demonstração" para não perder nenhuma funcionalidade da
    V1 e para permitir praticar com uma série completa. Nunca é apresentado
    como medição real.
    """

    def __init__(self, nome: str, caminho: str | Path, separador: str = ";") -> None:
        super().__init__(nome, "CSV (fictício)")  # super() chama o __init__ da classe-mãe
        self._caminho = Path(caminho)
        self._separador = separador
        self._metadados = {
            "fonte": "Dataset fictício criado para fins didáticos (V1 do projeto)",
            "licenca": "uso didático",
            "aviso_da_fonte": "Valores simulados. Não representam medições reais de Heliópolis.",
        }

    @property
    def caminho(self) -> Path:
        return self._caminho

    def carregar_dados(self) -> pd.DataFrame:
        """Lê o CSV e devolve a tabela LARGA original (Data + 8 colunas).

        Mantido da V1: é usado pelo script de carga no banco e pelos testes.
        """
        if not self._caminho.is_file():
            raise ErroFonteDados(f"Arquivo CSV não encontrado: {self._caminho}")
        try:
            try:
                bruto = pd.read_csv(self._caminho, sep=self._separador, encoding="utf-8")
            except UnicodeDecodeError:
                # Arquivos gerados no Excel brasileiro costumam usar a codificação latin1.
                bruto = pd.read_csv(self._caminho, sep=self._separador, encoding="latin1")
        except (pd.errors.ParserError, pd.errors.EmptyDataError, OSError) as erro:
            raise ErroFonteDados(f"Não foi possível ler o CSV: {erro}") from erro
        return _padronizar_largo(bruto, self._nome)

    def carregar_registros(self) -> pd.DataFrame:
        """Lê a fonte e devolve os registros no formato padrão do sistema (uma linha por medição).

        Cada fonte implementa este método do seu jeito (polimorfismo): CSV, banco,
        MonitorAr ou QUALAR. Também anota em ``transformacoes`` o que foi feito com os dados.
        """
        largo = self.carregar_dados()
        self._transformacoes = [
            "Tabela larga (uma coluna por variável) convertida para o formato de registros (uma linha por medição).",
            "Células vazias do arquivo não viram registros: continuam como valores ausentes.",
            "Unidades dos poluentes ASSUMIDAS (o arquivo não as informa); temperatura (°C) e umidade (%) confirmadas.",
        ]
        return self._finalizar_registros(largo_para_registros(largo, ESTACAO_FICTICIA), self._nome)


def _padronizar_largo(df: pd.DataFrame, origem: str) -> pd.DataFrame:
    """Valida as colunas do dataset fictício e converte tipos, sem alterar valores."""
    ausentes = [c for c in COLUNAS_ESPERADAS_DEMONSTRACAO if c not in df.columns]
    if ausentes:
        raise ErroFonteDados(f"A fonte '{origem}' não possui as colunas esperadas: {', '.join(ausentes)}.")
    df = df[COLUNAS_ESPERADAS_DEMONSTRACAO].copy()
    try:
        df[COLUNA_DATA] = pd.to_datetime(df[COLUNA_DATA])
    except (ValueError, TypeError) as erro:
        raise ErroFonteDados(f"Datas inválidas na fonte '{origem}': {erro}") from erro
    for coluna in COLUNAS_DEMONSTRACAO:
        # errors="coerce": textos que não são números viram NaN (ausente) em vez de travar.
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    if df.empty:
        raise ErroFonteDados(f"A fonte '{origem}' não retornou nenhum registro.")
    return df.sort_values(COLUNA_DATA, kind="stable").reset_index(drop=True)


class FontePostgres(FonteDados):
    """Lê registros de uma tabela PostgreSQL (por exemplo, no Supabase).

    Usa a estrutura do dataset fictício (tabela ``registros_ambientais``,
    veja ``docs/schema.sql``). A conexão vem da variável de ambiente
    ``DATABASE_URL``; a senha nunca aparece em mensagens de erro.
    """

    #: coluna no banco → coluna do dataset fictício
    COLUNAS_BANCO = {
        "data_hora": "Data", "mp10": "MP10", "mp2_5": "MP2.5", "o3": "O3", "co": "CO",
        "co2": "CO2", "no2": "NO2", "temp": "Temp", "umidade": "Umidade",
    }

    def __init__(self, nome: str, url: str, tabela: str = "registros_ambientais") -> None:
        super().__init__(nome, "PostgreSQL")
        # A expressão regular aceita só letras, números e "_" (começando por letra ou "_").
        # Isso impede que um nome de tabela malicioso injete comandos SQL.
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tabela):
            raise ErroFonteDados("Nome de tabela inválido (use apenas letras, números e _).")
        self._url = url
        self._tabela = tabela
        self._metadados = {"fonte": "Banco PostgreSQL (estrutura do dataset fictício)", "tabela": tabela}

    def carregar_dados(self) -> pd.DataFrame:
        """Consulta a tabela e devolve a estrutura larga (igual à do CSV fictício)."""
        try:
            # Import dentro da função: o SQLAlchemy só é necessário para quem usa banco.
            from sqlalchemy import create_engine, text
        except ImportError as erro:
            raise ErroFonteDados("SQLAlchemy não está instalado. Rode: pip install -r requirements-db.txt") from erro

        colunas = ", ".join(self.COLUNAS_BANCO)
        consulta = text(f"SELECT {colunas} FROM {self._tabela} ORDER BY data_hora")
        # connect_timeout: desiste da conexão em 5 s (só existe no PostgreSQL).
        argumentos = {"connect_args": {"connect_timeout": 5}} if self._url.startswith("postgres") else {}
        engine = None
        try:
            engine = create_engine(self._url, pool_pre_ping=True, **argumentos)
            with engine.connect() as conexao:
                bruto = pd.read_sql(consulta, conexao)
        except Exception as erro:  # noqa: BLE001 - qualquer falha de banco vira ErroFonteDados
            # Só o TIPO do erro é mostrado: a mensagem original pode conter a senha.
            raise ErroFonteDados(f"Falha ao consultar o banco de dados ({type(erro).__name__}).") from None
        finally:
            if engine is not None:
                engine.dispose()  # fecha as conexões abertas
        return _padronizar_largo(bruto.rename(columns=self.COLUNAS_BANCO), self._nome)

    def carregar_registros(self) -> pd.DataFrame:
        """Lê a fonte e devolve os registros no formato padrão do sistema (uma linha por medição).

        Cada fonte implementa este método do seu jeito (polimorfismo): CSV, banco,
        MonitorAr ou QUALAR. Também anota em ``transformacoes`` o que foi feito com os dados.
        """
        largo = self.carregar_dados()
        self._transformacoes = ["Tabela do banco convertida para o formato de registros."]
        estacao = dict(ESTACAO_FICTICIA, estacao="Banco de dados (estrutura do dataset fictício)")
        return self._finalizar_registros(largo_para_registros(largo, estacao), self._nome)


# ============================================================================
# Dados REAIS: MonitorAr (MMA)
# ============================================================================
def carregar_estacoes(caminho: str | Path) -> pd.DataFrame:
    """Lê a lista curada de estações (``data/reais/estacoes.csv``).

    Retorna uma tabela vazia (com as colunas certas) se o arquivo não existir,
    para que o sistema continue funcionando e mostre "localização não verificada".
    """
    caminho = Path(caminho)
    colunas = ["id_estacao_monitorar", "nome", "municipio", "endereco", "latitude", "longitude", "fonte_localizacao", "codigo_qualar"]
    if not caminho.is_file():
        return pd.DataFrame(columns=colunas)
    return pd.read_csv(caminho, dtype={"id_estacao_monitorar": str, "codigo_qualar": str})


class FonteMonitorAr(FonteDados):
    """Lê o recorte REAL do MonitorAr gerado por ``scripts/preparar_dados_monitorar.py``.

    O que é feito na leitura (e registrado em ``transformacoes``):

    * a coluna de status, que se chama ``st_situacao_item`` em 2024 e
      ``st_situacao`` em 2025, é unificada na coluna ``situacao``;
    * ``nu_iqar`` vira registros de grandeza "índice"; ``nu_concentracao``,
      quando preenchida, vira registros de "concentração" com a unidade
      marcada como não informada (o arquivo não traz unidades);
    * as coordenadas das estações vêm do serviço oficial da CETESB, porque no
      arquivo de 2025 várias estações aparecem com a mesma coordenada genérica.
    """

    #: colunas que o arquivo precisa ter para ser lido
    COLUNAS_OBRIGATORIAS = ["dh_medicao", "nu_iqar", "nu_concentracao", "cd_normalizado", "id_estacao", "no_estacao", "no_municipio"]

    def __init__(self, nome: str, caminho: str | Path, caminho_estacoes: str | Path, caminho_metadados: str | Path | None = None) -> None:
        super().__init__(nome, "MonitorAr")
        self._caminho = Path(caminho)
        self._caminho_estacoes = Path(caminho_estacoes)
        self._caminho_metadados = Path(caminho_metadados) if caminho_metadados else None

    def carregar_registros(self) -> pd.DataFrame:
        """Lê a fonte e devolve os registros no formato padrão do sistema (uma linha por medição).

        Cada fonte implementa este método do seu jeito (polimorfismo): CSV, banco,
        MonitorAr ou QUALAR. Também anota em ``transformacoes`` o que foi feito com os dados.
        """
        if not self._caminho.is_file():
            raise ErroFonteDados(f"Arquivo de dados reais não encontrado: {self._caminho.name}")
        try:
            # dtype=str + keep_default_na=False: lemos os textos exatamente como estão.
            bruto = pd.read_csv(self._caminho, dtype=str, keep_default_na=False)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, OSError, EOFError) as erro:
            raise ErroFonteDados(f"Não foi possível ler {self._caminho.name}: {erro}") from erro

        faltando = [c for c in self.COLUNAS_OBRIGATORIAS if c not in bruto.columns]
        if faltando:
            raise ErroFonteDados(f"O arquivo {self._caminho.name} não tem as colunas: {', '.join(faltando)}.")
        if bruto.empty:
            raise ErroFonteDados(f"O arquivo {self._caminho.name} não tem linhas.")

        self._metadados = self._ler_metadados()
        self._transformacoes = [
            f"{len(bruto)} linhas lidas do recorte {self._caminho.name} (cópia sem alterações das linhas oficiais)."
        ]

        # --- status de validação: nome da coluna mudou entre os anos -------------
        situacao = pd.Series("", index=bruto.index)
        for coluna in ("st_situacao_item", "st_situacao"):
            if coluna in bruto.columns:
                # where(cond, outro): mantém o valor atual onde cond é verdadeira; senão usa "outro".
                situacao = situacao.where(situacao != "", bruto[coluna])
        if {"st_situacao_item", "st_situacao"} & set(bruto.columns):
            self._registrar("Colunas de status 'st_situacao_item' (2024) e 'st_situacao' (2025) unificadas em 'situacao'.")

        base = pd.DataFrame(
            {
                "estacao_id": bruto["id_estacao"],
                "estacao": bruto["no_estacao"],
                "municipio": bruto["no_municipio"],
                "data_hora": bruto["dh_medicao"],
                "parametro": bruto["cd_normalizado"].map(normalizar_codigo),
                "situacao": situacao,
                "lat_arquivo": bruto.get("nu_latitude", ""),
                "lon_arquivo": bruto.get("nu_longitude", ""),
            }
        )
        if (bruto["cd_normalizado"] != base["parametro"]).any():
            self._registrar("Siglas de parâmetro padronizadas (ex.: 'MP2,5' → 'MP2.5'); os valores não mudam.")

        # --- índices (IQAr) ------------------------------------------------------
        indices = base[bruto["nu_iqar"] != ""].copy()
        indices["valor"] = bruto.loc[indices.index, "nu_iqar"]
        indices["grandeza"] = GRANDEZA_INDICE
        indices["unidade"] = UNIDADE_INDICE
        indices["unidade_confirmada"] = True

        # --- concentrações (quando existirem) -------------------------------------
        conc = base[bruto["nu_concentracao"] != ""].copy()
        conc["valor"] = bruto.loc[conc.index, "nu_concentracao"]
        conc["grandeza"] = GRANDEZA_CONCENTRACAO
        conc["unidade"] = "não informada no arquivo"
        conc["unidade_confirmada"] = False
        self._registrar(
            f"{len(indices)} valores de IQAr (coluna nu_iqar) e {len(conc)} valores de concentração "
            "(coluna nu_concentracao) encontrados. Para as estações da CETESB, o MonitorAr só traz o índice."
        )

        estacao_hora = self._indice_da_estacao(indices)
        registros = pd.concat([estacao_hora, indices, conc], ignore_index=True)
        registros = self._aplicar_localizacao(registros)
        return self._finalizar_registros(registros, self._nome)

    def _indice_da_estacao(self, indices: pd.DataFrame) -> pd.DataFrame:
        """Cria a variável "IQAr da estação": o MAIOR índice entre os poluentes em cada hora.

        Por que isso é necessário: conferindo os dados, cada estação tem UM único
        poluente por hora no arquivo. Logo, a série de um poluente só existe nas
        horas em que ele foi o registrado, e séries de poluentes diferentes nunca
        se cruzam. A série contínua que faz sentido analisar é o índice da
        estação. A CETESB classifica a estação pelo poluente de maior índice
        (página "Padrões de qualidade do ar"); por isso, se houver mais de um
        poluente na mesma hora, usamos o maior.
        """
        if indices.empty:
            return indices
        valores = indices.assign(valor_num=pd.to_numeric(indices["valor"], errors="coerce"))
        por_hora = valores.groupby(["estacao_id", "data_hora"])["valor_num"]
        poluentes_por_hora = por_hora.size()
        self._metadados["um_poluente_por_hora"] = bool((poluentes_por_hora == 1).all())
        # idxmax devolve, para cada grupo (estação + hora), a linha com o maior índice.
        maiores = valores.loc[por_hora.idxmax()].copy()
        maiores["valor"] = maiores["valor_num"]
        maiores["parametro"] = CODIGO_IQAR_ESTACAO
        maiores = maiores.drop(columns=["valor_num"])
        frase = (
            f"Criada a variável 'IQAr da estação' ({len(maiores)} horas): em cada hora, o maior índice entre os "
            "poluentes (regra de classificação da CETESB)."
        )
        if self._metadados["um_poluente_por_hora"]:
            frase += (
                " Verificação: o arquivo traz um único poluente por hora em cada estação, então o valor é o do "
                "poluente registrado naquela hora. O dicionário de dados do MonitorAr não explica essa regra."
            )
        self._registrar(frase)
        return maiores

    def _aplicar_localizacao(self, registros: pd.DataFrame) -> pd.DataFrame:
        """Preenche endereço e coordenadas a partir da lista curada de estações (CETESB)."""
        estacoes = carregar_estacoes(self._caminho_estacoes).set_index("id_estacao_monitorar")
        conhecidas = registros["estacao_id"].isin(estacoes.index)
        # Garante que latitude/longitude sejam colunas NUMÉRICAS desde o início.
        # No pandas 3 uma coluna de texto não aceita receber números depois
        # (erro "Invalid value for dtype 'str'"), por isso convertemos antes.
        for coluna in ("latitude", "longitude"):
            registros[coluna] = pd.to_numeric(registros[coluna], errors="coerce") if coluna in registros else float("nan")
        # map(dicionário) troca cada id pelo valor correspondente na lista de estações.
        if conhecidas.any():
            for destino in ("endereco", "latitude", "longitude", "fonte_localizacao", "municipio"):
                valores = registros.loc[conhecidas, "estacao_id"].map(estacoes[destino])
                if destino in ("latitude", "longitude"):
                    valores = pd.to_numeric(valores, errors="coerce")
                registros.loc[conhecidas, destino] = valores
            registros.loc[conhecidas, "localizacao"] = "estacao_proxima"
            self._registrar(
                "Coordenadas e endereço das estações substituídos pelos do serviço ArcGIS oficial da CETESB "
                "(no arquivo de 2025 várias estações aparecem com a coordenada genérica -23,5475 / -46,636111)."
            )
        # Estações fora da lista: usamos a coordenada do arquivo, marcada como não verificada.
        desconhecidas = ~conhecidas
        if desconhecidas.any():
            registros.loc[desconhecidas, "latitude"] = pd.to_numeric(registros.loc[desconhecidas, "lat_arquivo"], errors="coerce")
            registros.loc[desconhecidas, "longitude"] = pd.to_numeric(registros.loc[desconhecidas, "lon_arquivo"], errors="coerce")
            registros.loc[desconhecidas, "fonte_localizacao"] = "coordenada do arquivo MonitorAr (não verificada)"
            registros.loc[desconhecidas, "localizacao"] = "estacao"
        registros["latitude"] = pd.to_numeric(registros["latitude"], errors="coerce")
        registros["longitude"] = pd.to_numeric(registros["longitude"], errors="coerce")
        return registros.drop(columns=["lat_arquivo", "lon_arquivo"])

    def _ler_metadados(self) -> dict:
        """Lê o JSON gerado pelo script de preparação (origem, licença, SHA-256...)."""
        if self._caminho_metadados and self._caminho_metadados.is_file():
            try:
                return json.loads(self._caminho_metadados.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {"aviso": "metadados ilegíveis"}
        return {"aviso": "arquivo de metadados não encontrado"}


# ============================================================================
# Dados REAIS: exportação manual do QUALAR (CETESB)
# ============================================================================
# O QUALAR exige login (cadastro gratuito) para exportar. Não temos um arquivo
# real de exemplo; os nomes de coluna abaixo seguem a tabela que o pacote
# científico qualR (rOpenSci) lê na mesma exportação:
#   Data | Hora | Código Estação | Nome Estação | Nome Parâmetro | Unidade de Medida | Média Horária | Válido ...
# Por isso a leitura procura as colunas pelo NOME (sem acento, minúsculas),
# e não pela posição. Se a CETESB mudar o formato, a mensagem de erro dirá
# qual coluna não foi encontrada.
_CANDIDATAS_QUALAR = {
    "data": ["data"],
    "hora": ["hora"],
    "estacao": ["nome estacao", "estacao"],
    "codigo_estacao": ["codigo estacao", "cod estacao"],
    "parametro": ["nome parametro", "parametro"],
    "unidade": ["unidade de medida", "unidade"],
    "valor": ["media horaria", "concentracao", "valor"],
    "valido": ["valido"],
}


def _normalizar_cabecalho(texto: str) -> str:
    """Ex.: ``" Média Horária "`` → ``"media horaria"`` (sem acentos, minúsculo, sem pontuação)."""
    limpo = sem_acentos(texto).lower().replace(".", " ").replace("_", " ")
    return " ".join(limpo.split())


def _numero_brasileiro(texto: str) -> float:
    """Converte ``"1.234,5"`` ou ``"25,3"`` (padrão brasileiro) e ``"25.3"`` em número."""
    texto = str(texto).strip()
    if texto == "" or texto == "-":
        return np.nan
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return np.nan


def ler_exportacao_qualar(caminho: str | Path) -> pd.DataFrame:
    """Lê UM arquivo CSV exportado do QUALAR e devolve as colunas encontradas.

    Retorna uma tabela com: data_hora, estacao, codigo_estacao, parametro,
    unidade, valor, situacao. Lança ErroFonteDados com mensagem clara se o
    arquivo não tiver o formato esperado.
    """
    caminho = Path(caminho)
    dados = caminho.read_bytes()
    if not dados.strip():
        raise ErroFonteDados(f"O arquivo {caminho.name} está vazio.")
    try:
        texto = dados.decode("utf-8")
    except UnicodeDecodeError:
        texto = dados.decode("latin1")

    # Alguns arquivos têm linhas de título antes do cabeçalho. Procuramos a
    # primeira linha que contenha "data", "hora" e uma coluna de valor.
    linhas = texto.splitlines()
    inicio = None
    for i, linha in enumerate(linhas[:50]):
        normal = _normalizar_cabecalho(linha)
        if "data" in normal and "hora" in normal and any(v in normal for v in ("media horaria", "concentracao", "valor")):
            inicio = i
            break
    if inicio is None:
        raise ErroFonteDados(f"{caminho.name}: cabeçalho com as colunas Data, Hora e Média Horária não encontrado.")

    cabecalho = linhas[inicio]
    separador = ";" if cabecalho.count(";") >= cabecalho.count(",") else ","
    tabela = pd.read_csv(StringIO("\n".join(linhas[inicio:])), sep=separador, dtype=str, keep_default_na=False)
    tabela = tabela.loc[:, [c for c in tabela.columns if str(c).strip() and not str(c).startswith("Unnamed")]]

    # Associa cada coluna "conceitual" ao nome real no arquivo.
    nomes = {_normalizar_cabecalho(c): c for c in tabela.columns}
    encontradas: dict[str, str] = {}
    for conceito, candidatas in _CANDIDATAS_QUALAR.items():
        for candidata in candidatas:
            if candidata in nomes:
                encontradas[conceito] = nomes[candidata]
                break
    faltando = [c for c in ("data", "hora", "valor", "parametro", "unidade") if c not in encontradas]
    if faltando:
        raise ErroFonteDados(f"{caminho.name}: colunas não encontradas: {', '.join(faltando)}.")

    # Data e hora: o QUALAR usa "24:00" para a última hora do dia. Convertemos
    # para 00:00 do dia seguinte, que é a mesma hora no relógio.
    hora = tabela[encontradas["hora"]].str.strip()
    vinte_e_quatro = hora.str.startswith("24")
    data = pd.to_datetime(tabela[encontradas["data"]].str.strip(), format="%d/%m/%Y", errors="coerce")
    horas = pd.to_timedelta(hora.where(~vinte_e_quatro, "00:00").str.slice(0, 5) + ":00", errors="coerce")
    data_hora = data + horas + pd.to_timedelta(vinte_e_quatro.astype(int), unit="D")

    saida = pd.DataFrame(
        {
            "data_hora": data_hora,
            "estacao": tabela[encontradas["estacao"]].str.strip() if "estacao" in encontradas else caminho.stem,
            "codigo_estacao": tabela[encontradas["codigo_estacao"]].str.strip() if "codigo_estacao" in encontradas else "",
            "parametro": tabela[encontradas["parametro"]].map(normalizar_codigo),
            "unidade": tabela[encontradas["unidade"]].map(normalizar_unidade),
            "valor": tabela[encontradas["valor"]].map(_numero_brasileiro),
            "situacao": tabela[encontradas["valido"]].str.strip() if "valido" in encontradas else "",
            "hora_24": vinte_e_quatro,
        }
    )
    if saida["data_hora"].isna().all():
        raise ErroFonteDados(f"{caminho.name}: nenhuma data/hora pôde ser interpretada (formato esperado dd/mm/aaaa e hh:mm).")
    return saida


class FonteQualar(FonteDados):
    """Lê todos os CSV exportados do QUALAR que estiverem numa pasta (``data/qualar``).

    Registros marcados como não válidos (coluna "Válido" = "Não") são
    descartados na leitura; o arquivo original continua intacto na pasta.
    """

    def __init__(self, nome: str, pasta: str | Path, caminho_estacoes: str | Path) -> None:
        super().__init__(nome, "QUALAR")
        self._pasta = Path(pasta)
        self._caminho_estacoes = Path(caminho_estacoes)
        self._metadados = {
            "fonte": "CETESB — sistema QUALAR (exportação manual pelo usuário)",
            "pagina": "https://cetesb.sp.gov.br/ar/qualar/",
            "licenca": "uso permitido citando a fonte (catálogo de dados abertos da CETESB)",
            "aviso_da_fonte": "Dados sujeitos à validação posterior pela CETESB (página do QUALAR).",
        }

    def arquivos(self) -> list[Path]:
        """Lista os .csv da pasta, em ordem alfabética."""
        if not self._pasta.is_dir():
            return []
        return sorted(p for p in self._pasta.glob("*.csv") if p.is_file())

    def carregar_registros(self) -> pd.DataFrame:
        """Lê a fonte e devolve os registros no formato padrão do sistema (uma linha por medição).

        Cada fonte implementa este método do seu jeito (polimorfismo): CSV, banco,
        MonitorAr ou QUALAR. Também anota em ``transformacoes`` o que foi feito com os dados.
        """
        arquivos = self.arquivos()
        if not arquivos:
            raise ErroFonteDados("Nenhum arquivo do QUALAR em data/qualar (veja docs/FONTES_DE_DADOS.md).")
        partes = [ler_exportacao_qualar(a).assign(arquivo=a.name) for a in arquivos]
        tabela = pd.concat(partes, ignore_index=True)
        self._transformacoes = [f"{len(tabela)} linhas lidas de {len(arquivos)} arquivo(s) do QUALAR."]

        if tabela["hora_24"].any():
            self._registrar(f"{int(tabela['hora_24'].sum())} horários '24:00' convertidos para 00:00 do dia seguinte.")
        invalidos = tabela["situacao"].map(_normalizar_cabecalho).isin(["nao", "n"])
        if invalidos.any():
            self._registrar(f"{int(invalidos.sum())} registros marcados como não válidos pela CETESB foram descartados.")
        tabela = tabela[~invalidos]

        estacoes = carregar_estacoes(self._caminho_estacoes)
        por_nome = {_normalizar_cabecalho(n): linha for n, linha in zip(estacoes["nome"], estacoes.to_dict("records"))}
        registros = []
        for nome_estacao, grupo in tabela.groupby("estacao"):
            info = por_nome.get(_normalizar_cabecalho(nome_estacao))
            g = grupo.copy()
            g["estacao_id"] = f"QUALAR-{grupo['codigo_estacao'].iloc[0] or nome_estacao}"
            g["grandeza"] = np.where(g["parametro"].isin(["TEMP", "UR"]), "meteorologia", GRANDEZA_CONCENTRACAO)
            g["unidade_confirmada"] = True
            if info:
                g["municipio"], g["endereco"] = info["municipio"], info["endereco"]
                g["latitude"], g["longitude"] = info["latitude"], info["longitude"]
                g["fonte_localizacao"], g["localizacao"] = info["fonte_localizacao"], "estacao_proxima"
            else:
                g["municipio"] = g["endereco"] = "não informado"
                g["fonte_localizacao"] = "não verificada"
                g["localizacao"] = "estacao"
            registros.append(g)
        return self._finalizar_registros(pd.concat(registros, ignore_index=True), self._nome)

