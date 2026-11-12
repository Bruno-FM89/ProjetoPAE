"""Catálogo de parâmetros ambientais e de variáveis analisáveis (Model).

Conceitos usados neste arquivo
------------------------------
* **Parâmetro** é O QUE foi observado: MP2.5, ozônio, temperatura...
* **Grandeza** é COMO o parâmetro foi expresso no arquivo:
    - ``concentracao``: quantidade do poluente no ar (ex.: µg/m³ ou ppm);
    - ``indice``: valor do IQAr (Índice de Qualidade do Ar), que não tem unidade;
    - ``meteorologia``: medidas do tempo (temperatura em °C, umidade em %).
* **Variável** é a combinação parâmetro + grandeza + unidade. É ela que vira
  uma coluna nos gráficos e tabelas.

Por que separar? Os dados reais do MonitorAr trazem, para as estações da
CETESB, apenas o ÍNDICE de cada poluente, enquanto o dataset fictício traz
CONCENTRAÇÕES. Índice e concentração NÃO são equivalentes e não podem ser
comparados como se fossem a mesma coisa. Por isso cada variável carrega sua
grandeza e sua unidade, e a chave da variável deixa isso visível:

    "MP2.5"       -> concentração de MP2.5
    "MP2.5_IQAr"  -> índice IQAr calculado para o MP2.5

Este arquivo substitui o antigo ``variaveis.py`` da V1, que tinha 8 colunas
fixas. Agora as variáveis são montadas a partir do que cada arquivo realmente contém.
"""

from __future__ import annotations

import unicodedata  # usado para remover acentos ao comparar textos
from dataclasses import dataclass

# --- grandezas ----------------------------------------------------------------
GRANDEZA_CONCENTRACAO = "concentracao"
GRANDEZA_INDICE = "indice"
GRANDEZA_METEOROLOGIA = "meteorologia"

#: Nome de cada grandeza como aparece para o usuário.
NOMES_GRANDEZA = {
    GRANDEZA_CONCENTRACAO: "Concentração",
    GRANDEZA_INDICE: "Índice de qualidade do ar (IQAr)",
    GRANDEZA_METEOROLOGIA: "Meteorologia",
}

#: Texto usado como "unidade" quando a variável é um índice.
UNIDADE_INDICE = "índice (sem unidade)"

#: Nome da coluna de data/hora nas tabelas "largas" (uma coluna por variável).
COLUNA_DATA = "Data"


@dataclass(frozen=True)
class Parametro:
    """Algo que pode ser medido no ar (um poluente ou uma grandeza do tempo).

    Atributos:
        codigo: identificador interno, sem espaços (ex.: ``"MP2.5"``).
        sigla: como a sigla é escrita na tela (ex.: ``"MP2,5"``, com vírgula, padrão brasileiro).
        nome: nome completo em português.
        descricao: explicação simples, sem termos técnicos e sem afirmações médicas.
        categoria: ``"poluente"``, ``"meteorologia"`` ou ``"indice"`` (índice geral da estação).
        ordem: posição em listas e tabelas (os mais conhecidos primeiro).
    """

    codigo: str
    sigla: str
    nome: str
    descricao: str
    categoria: str
    ordem: int


# Dicionário com todos os parâmetros conhecidos pelo sistema.
# A "compreensão de dicionário" ({p.codigo: p for p in (...)}) cria um dicionário
# em que a chave é o código e o valor é o objeto Parametro correspondente.
PARAMETROS: dict[str, Parametro] = {
    p.codigo: p
    for p in (
        Parametro(
            "IQAR", "IQAr", "Índice de Qualidade do Ar da estação",
            "Número sem unidade que resume a qualidade do ar numa estação. Cada poluente recebe um "
            "índice próprio, e a estação é classificada pelo MAIOR deles (o poluente em pior situação "
            "naquela hora). Quanto maior o número, pior a qualidade do ar.",
            "indice", 0,
        ),
        Parametro(
            "MP2.5", "MP2,5", "Material Particulado Fino",
            "Partículas muito pequenas suspensas no ar, com até 2,5 micrômetros de diâmetro "
            "(dezenas de vezes mais finas que um fio de cabelo). Por serem tão pequenas, podem "
            "penetrar profundamente no sistema respiratório.",
            "poluente", 1,
        ),
        Parametro(
            "MP10", "MP10", "Material Particulado Inalável",
            "Partículas suspensas no ar com até 10 micrômetros de diâmetro, como poeira e fuligem. "
            "O MP2,5 é uma parte do MP10.",
            "poluente", 2,
        ),
        Parametro(
            "O3", "O₃", "Ozônio",
            "Gás que, perto do solo, não é emitido diretamente: ele se forma no ar a partir de outros "
            "poluentes com a ajuda da luz do sol.",
            "poluente", 3,
        ),
        Parametro(
            "NO2", "NO₂", "Dióxido de Nitrogênio",
            "Gás formado principalmente na queima de combustíveis, como nos motores de veículos.",
            "poluente", 4,
        ),
        Parametro(
            "CO", "CO", "Monóxido de Carbono",
            "Gás sem cor e sem cheiro, produzido quando um combustível queima de forma incompleta.",
            "poluente", 5,
        ),
        Parametro(
            "SO2", "SO₂", "Dióxido de Enxofre",
            "Gás produzido pela queima de combustíveis que contêm enxofre.",
            "poluente", 6,
        ),
        Parametro(
            "CO2", "CO₂", "Dióxido de Carbono",
            "Gás presente naturalmente na atmosfera, também liberado pela respiração e pela combustão.",
            "poluente", 7,
        ),
        Parametro(
            "BENZENO", "Benzeno", "Benzeno",
            "Composto químico que evapora com facilidade, presente em combustíveis.",
            "poluente", 8,
        ),
        Parametro(
            "TEMP", "Temp.", "Temperatura do ar",
            "Indica o quanto o ar está quente ou frio.",
            "meteorologia", 20,
        ),
        Parametro(
            "UR", "UR", "Umidade relativa do ar",
            "Quanto vapor d'água há no ar em relação ao máximo que ele suportaria naquela temperatura "
            "(100% significa ar saturado).",
            "meteorologia", 21,
        ),
    )
}

# Apelidos aceitos na leitura de arquivos, já sem acentos e em maiúsculas.
# Ex.: o MonitorAr escreve "MP2,5"; o QUALAR pode escrever "MP2.5 (Partículas ...)".
_APELIDOS = {
    "MP2,5": "MP2.5", "MP25": "MP2.5", "PM2.5": "MP2.5", "PM25": "MP2.5", "PM2,5": "MP2.5",
    "PM10": "MP10",
    "OZONIO": "O3",
    "TEMPERATURA": "TEMP", "TEMP.": "TEMP",
    "UMIDADE": "UR", "UMIDADE RELATIVA": "UR",
    "BEN": "BENZENO",
}


def sem_acentos(texto: str) -> str:
    """Remove acentos e cedilha: ``"Ozônio"`` vira ``"Ozonio"``.

    Útil para comparar textos vindos de arquivos diferentes, que nem sempre
    usam a mesma acentuação.
    """
    # NFKD separa cada letra de seu acento (ex.: "ô" vira "o" + "^");
    # depois mantemos só os caracteres que não são marcas de acento.
    normalizado = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def normalizar_codigo(texto: str) -> str:
    """Converte a forma como um arquivo escreve um parâmetro para o código interno.

    Exemplos: ``"MP2,5"`` → ``"MP2.5"``; ``"MP10 (Particulas Inalaveis)"`` → ``"MP10"``;
    ``"O3"`` → ``"O3"``. Se o texto for desconhecido, devolve-o em maiúsculas,
    sem inventar uma correspondência.
    """
    bruto = sem_acentos(texto).strip().upper()
    # Muitos arquivos escrevem "SIGLA (Nome por extenso)": ficamos com a sigla.
    sigla = bruto.split("(")[0].strip()
    if sigla in PARAMETROS:
        return sigla
    if sigla in _APELIDOS:
        return _APELIDOS[sigla]
    # Último recurso: primeira palavra (ex.: "TEMP TEMPERATURA DO AR" → "TEMP").
    primeira = sigla.split(" ")[0] if sigla else sigla
    return _APELIDOS.get(primeira, primeira if primeira in PARAMETROS else sigla)


def obter_parametro(codigo: str) -> Parametro:
    """Devolve o Parametro do catálogo, ou um parâmetro "genérico" se for desconhecido.

    O genérico usa o próprio código como nome e avisa que não há descrição.
    Assim, um parâmetro novo num arquivo não derruba o sistema: ele aparece
    na tela, mas sem explicação inventada.
    """
    if codigo in PARAMETROS:
        return PARAMETROS[codigo]
    return Parametro(codigo, codigo, codigo, "Parâmetro sem descrição cadastrada no sistema.", "poluente", 99)


def normalizar_unidade(texto: str) -> str:
    """Padroniza a escrita de unidades vindas de arquivos (ex.: ``"ug/m3"`` → ``"µg/m³"``)."""
    bruto = sem_acentos(str(texto)).strip().lower().replace(" ", "")
    conversoes = {
        "ug/m3": "µg/m³", "µg/m3": "µg/m³", "ug/m³": "µg/m³", "mg/m3": "mg/m³",
        "ppm": "ppm", "ppb": "ppb",
        "oc": "°C", "ºc": "°C", "°c": "°C", "c": "°C", "graus": "°C",
        "%": "%",
    }
    # sem_acentos transforma "µ" em "μ"/"u" dependendo da fonte; cobrimos as duas formas.
    bruto = bruto.replace("μ", "u").replace("µ", "u")
    return conversoes.get(bruto, str(texto).strip())


@dataclass(frozen=True)
class Variavel:
    """Uma coluna analisável: parâmetro + grandeza + unidade.

    Atributos:
        chave: identificador único dentro do conjunto de dados (ex.: ``"MP2.5_IQAr"``).
        parametro: o objeto Parametro (nome, sigla, descrição).
        grandeza: concentração, índice ou meteorologia (veja o topo do arquivo).
        unidade: unidade de medida como deve aparecer na tela.
        unidade_confirmada: ``False`` quando a unidade foi apenas suposta
            (caso do dataset fictício) ou quando o arquivo não a informa.
        casas_moda: casas decimais usadas para arredondar antes de calcular a moda.
    """

    chave: str
    parametro: Parametro
    grandeza: str
    unidade: str
    unidade_confirmada: bool
    casas_moda: int

    @property
    def eh_indice(self) -> bool:
        return self.grandeza == GRANDEZA_INDICE

    @property
    def eh_indice_estacao(self) -> bool:
        """Verdadeiro para o índice geral da estação (o maior entre os poluentes)."""
        return self.parametro.codigo == CODIGO_IQAR_ESTACAO

    @property
    def nome_completo(self) -> str:
        """Ex.: ``"MP2,5 — Material Particulado Fino"``."""
        p = self.parametro
        return p.nome if p.sigla == p.nome else f"{p.sigla} — {p.nome}"

    @property
    def rotulo(self) -> str:
        """Rótulo curto com a unidade, usado em menus e títulos de eixo.

        Ex.: ``"IQAr da estação"``, ``"MP2,5 · índice IQAr"`` ou ``"MP2,5 (µg/m³)"``.
        """
        if self.eh_indice_estacao:
            return "IQAr da estação"
        if self.eh_indice:
            return f"{self.parametro.sigla} · índice IQAr"
        return f"{self.parametro.sigla} ({self.unidade})"

    @property
    def titulo_eixo(self) -> str:
        """Texto do eixo dos gráficos: o que é e em que unidade."""
        if self.eh_indice_estacao:
            return "IQAr da estação (sem unidade)"
        if self.eh_indice:
            return f"IQAr de {self.parametro.sigla} (sem unidade)"
        return f"{self.parametro.sigla} ({self.unidade})"


#: Código do índice geral da estação (o maior índice entre os poluentes naquela hora).
CODIGO_IQAR_ESTACAO = "IQAR"


def chave_variavel(codigo: str, grandeza: str) -> str:
    """Monta a chave de uma variável.

    * índice geral da estação → ``"IQAR"``;
    * índice de um poluente → código + ``"_IQAr"`` (ex.: ``"O3_IQAr"``);
    * concentração ou meteorologia → o próprio código (ex.: ``"MP10"``).
    """
    if codigo == CODIGO_IQAR_ESTACAO:
        return CODIGO_IQAR_ESTACAO
    return f"{codigo}_IQAr" if grandeza == GRANDEZA_INDICE else codigo


def criar_variavel(codigo: str, grandeza: str, unidade: str, unidade_confirmada: bool = True, chave: str | None = None) -> Variavel:
    """Cria a Variavel correspondente a um parâmetro numa grandeza e unidade.

    Parâmetros:
        codigo: código do parâmetro (já normalizado).
        grandeza: uma das constantes GRANDEZA_*.
        unidade: unidade de medida (para índices, use UNIDADE_INDICE).
        unidade_confirmada: se a unidade foi informada pela fonte.
        chave: chave a usar; se omitida, é gerada por ``chave_variavel``.

    Retorna:
        Um objeto Variavel pronto para uso no catálogo.
    """
    parametro = obter_parametro(codigo)
    # Índices são números inteiros; CO e benzeno costumam ter valores pequenos
    # (ex.: 0,45 ppm), então arredondamos a 1 casa; os demais, à unidade.
    casas = 0 if grandeza == GRANDEZA_INDICE else (1 if codigo in ("CO", "BENZENO") else 0)
    return Variavel(
        chave=chave or chave_variavel(codigo, grandeza),
        parametro=parametro,
        grandeza=grandeza,
        unidade=UNIDADE_INDICE if grandeza == GRANDEZA_INDICE else unidade,
        unidade_confirmada=unidade_confirmada,
        casas_moda=casas,
    )


def ordenar_chaves(chaves, catalogo: dict[str, Variavel]) -> list[str]:
    """Ordena chaves de variáveis: poluentes conhecidos primeiro, índices junto do parâmetro."""
    return sorted(chaves, key=lambda c: (catalogo[c].parametro.ordem, catalogo[c].grandeza, c))


# --- estrutura do dataset FICTÍCIO da V1 ------------------------------------
# O arquivo didático tem uma coluna "Data" e oito colunas numéricas. Aqui
# dizemos, para cada coluna, qual é o parâmetro, a grandeza e a unidade.
# Só temperatura e umidade tiveram a unidade confirmada pela equipe.
COLUNAS_DEMONSTRACAO = {
    "MP10": ("MP10", GRANDEZA_CONCENTRACAO, "µg/m³", False),
    "MP2.5": ("MP2.5", GRANDEZA_CONCENTRACAO, "µg/m³", False),
    "O3": ("O3", GRANDEZA_CONCENTRACAO, "µg/m³", False),
    "CO": ("CO", GRANDEZA_CONCENTRACAO, "ppm", False),
    "CO2": ("CO2", GRANDEZA_CONCENTRACAO, "ppm", False),
    "NO2": ("NO2", GRANDEZA_CONCENTRACAO, "µg/m³", False),
    "Temp": ("TEMP", GRANDEZA_METEOROLOGIA, "°C", True),
    "Umidade": ("UR", GRANDEZA_METEOROLOGIA, "%", True),
}
COLUNAS_ESPERADAS_DEMONSTRACAO = [COLUNA_DATA, *COLUNAS_DEMONSTRACAO]
