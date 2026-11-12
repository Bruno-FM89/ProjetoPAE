"""Configuração do sistema, lida de variáveis de ambiente (Service).

Variável de ambiente é um "ajuste" definido fora do código (no terminal ou
num arquivo ``.env``). Assim, senhas e caminhos podem mudar sem editar o
programa. NADA aqui é obrigatório: sem nenhuma variável definida, o app usa
os arquivos que já vêm na pasta ``data/``.

Variáveis aceitas (todas opcionais):
    PAE_DADOS_MONITORAR      caminho do recorte real do MonitorAr (.csv.gz)
    PAE_PASTA_QUALAR         pasta com CSVs exportados do QUALAR
    PAE_CSV_PATH             caminho do dataset fictício de demonstração
    PAE_PASTA_TERMOMETROS    pasta com os dados preparados dos termômetros da UNAS
    PAE_PASTA_GEO            pasta com as camadas geográficas (GeoJSON) de Heliópolis
    DATABASE_URL             conexão com PostgreSQL/Supabase (opcional)
    PAE_TABELA               tabela do banco (padrão: registros_ambientais)
    PAE_LIMITE_LACUNA_HORAS  maior lacuna preenchida no modo "tratado" (padrão 4)
    PAE_FATOR_IQR            multiplicador do IQR para outliers (padrão 1,5)
"""

from __future__ import annotations

import os  # acesso às variáveis de ambiente do sistema
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# Pasta raiz do projeto (este arquivo fica em <raiz>/services/config.py).
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ_PROJETO / "data"

# Caminhos padrão dos arquivos de dados.
MONITORAR_PADRAO = PASTA_DADOS / "reais" / "monitorar_estacoes_proximas.csv.gz"
METADADOS_MONITORAR = PASTA_DADOS / "reais" / "metadados_monitorar.json"
ESTACOES_PADRAO = PASTA_DADOS / "reais" / "estacoes.csv"
QUALAR_PADRAO = PASTA_DADOS / "qualar"
CSV_PADRAO = PASTA_DADOS / "demonstracao" / "ambiental_heliopolis.csv"
# Novidades da V4: termômetros da comunidade e mapas (ambos gerados pelos scripts da pasta scripts/).
TERMOMETROS_PADRAO = PASTA_DADOS / "termometros"
GEO_PADRAO = PASTA_DADOS / "geo"


@dataclass(frozen=True)
class Configuracao:
    """Todos os ajustes do sistema num só objeto imutável."""

    caminho_monitorar: Path = MONITORAR_PADRAO
    caminho_metadados_monitorar: Path = METADADOS_MONITORAR
    caminho_estacoes: Path = ESTACOES_PADRAO
    pasta_qualar: Path = QUALAR_PADRAO
    caminho_csv: Path = CSV_PADRAO
    pasta_termometros: Path = TERMOMETROS_PADRAO
    pasta_geo: Path = GEO_PADRAO
    database_url: str | None = None
    tabela: str = "registros_ambientais"
    limite_lacuna_horas: int = 4
    fator_iqr: float = 1.5

    @property
    def caminho_medicoes_termometros(self) -> Path:
        """Arquivo com todas as leituras dos termômetros (gerado pelo script de preparação)."""
        return self.pasta_termometros / "medicoes_termometros.csv.gz"

    @property
    def caminho_metadados_termometros(self) -> Path:
        return self.pasta_termometros / "metadados_termometros.json"

    @property
    def caminho_locais_termometros(self) -> Path:
        """Tabela editável: em qual quebrada fica cada termômetro (sem endereço)."""
        return self.pasta_termometros / "locais_termometros.csv"

    @property
    def usa_banco(self) -> bool:
        """Verdadeiro quando uma URL de banco foi configurada."""
        return bool(self.database_url)

    @classmethod
    def carregar(cls, ambiente: Mapping[str, str] | None = None) -> "Configuracao":
        """Monta a configuração a partir do ambiente (e de um ``.env``, se existir).

        Parâmetros:
            ambiente: dicionário com as variáveis. Se ``None``, usa as do sistema
                operacional. Os testes passam um dicionário próprio.

        ``@classmethod`` significa que o método é chamado na CLASSE
        (``Configuracao.carregar()``) e devolve um objeto novo.
        """
        if ambiente is None:
            _carregar_dotenv()
            ambiente = os.environ

        return cls(
            caminho_monitorar=_caminho(ambiente.get("PAE_DADOS_MONITORAR"), MONITORAR_PADRAO),
            caminho_metadados_monitorar=METADADOS_MONITORAR,
            caminho_estacoes=ESTACOES_PADRAO,
            pasta_qualar=_caminho(ambiente.get("PAE_PASTA_QUALAR"), QUALAR_PADRAO),
            caminho_csv=_caminho(ambiente.get("PAE_CSV_PATH"), CSV_PADRAO),
            pasta_termometros=_caminho(ambiente.get("PAE_PASTA_TERMOMETROS"), TERMOMETROS_PADRAO),
            pasta_geo=_caminho(ambiente.get("PAE_PASTA_GEO"), GEO_PADRAO),
            database_url=(ambiente.get("DATABASE_URL") or "").strip() or None,
            tabela=(ambiente.get("PAE_TABELA") or "registros_ambientais").strip(),
            limite_lacuna_horas=_inteiro(ambiente.get("PAE_LIMITE_LACUNA_HORAS"), 4),
            fator_iqr=_decimal(ambiente.get("PAE_FATOR_IQR"), 1.5),
        )


def _caminho(valor: str | None, padrao: Path) -> Path:
    """Converte um texto em caminho; caminhos relativos partem da raiz do projeto."""
    if not valor:
        return padrao
    caminho = Path(valor)
    return caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho


def _carregar_dotenv() -> None:
    """Carrega ``.env`` se a biblioteca opcional python-dotenv estiver instalada."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return  # sem a biblioteca, simplesmente seguimos com as variáveis do sistema
    load_dotenv(RAIZ_PROJETO / ".env")


def _inteiro(valor: str | None, padrao: int) -> int:
    """Converte texto em inteiro ≥ 0; valores inválidos voltam ao padrão."""
    try:
        resultado = int(valor) if valor else padrao
    except ValueError:
        return padrao
    return resultado if resultado >= 0 else padrao


def _decimal(valor: str | None, padrao: float) -> float:
    """Converte texto em número decimal > 0; valores inválidos voltam ao padrão."""
    try:
        resultado = float(valor) if valor else padrao
    except ValueError:
        return padrao
    return resultado if resultado > 0 else padrao
