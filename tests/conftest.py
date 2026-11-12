"""Peças compartilhadas pelos testes (fixtures do pytest).

Uma *fixture* é uma função que prepara algo que vários testes usam (um
arquivo, um controller...). O pytest a executa automaticamente quando um
teste pede um parâmetro com o mesmo nome.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from controllers.painel_controller import PainelController
from models.fontes import FonteCSV, FonteMonitorAr
from services.config import Configuracao

RAIZ = Path(__file__).resolve().parent.parent
CSV_DEMO = RAIZ / "data" / "demonstracao" / "ambiental_heliopolis.csv"
RECORTE_REAL = RAIZ / "data" / "reais" / "monitorar_estacoes_proximas.csv.gz"
ESTACOES = RAIZ / "data" / "reais" / "estacoes.csv"
METADADOS = RAIZ / "data" / "reais" / "metadados_monitorar.json"

NOME_REAL = "Dados reais — MonitorAr (CETESB)"
NOME_DEMO = "Demonstração — dados fictícios"


def construir_largo(horas: int = 240, inicio: str = "2024-01-01", colunas=("A", "B", "C")) -> pd.DataFrame:
    """Tabela larga sintética e previsível (sem ausentes), para testar o tratamento."""
    datas = pd.date_range(inicio, periods=horas, freq="h")
    base = np.arange(horas, dtype=float)
    dados = {"Data": datas}
    for i, coluna in enumerate(colunas):
        dados[coluna] = 10.0 + 5 * i + (base % 24) * 0.5
    return pd.DataFrame(dados)


def linha_monitorar(dh, iqar, parametro="O3", id_estacao="128", nome="Mooca", conc="", situacao_col="st_situacao"):
    """Uma linha no formato do arquivo oficial do MonitorAr (para arquivos de teste)."""
    return {
        "no_fonte_dados": "Companhia Ambiental do Estado de São Paulo - CETESB", "dh_medicao": dh,
        "nu_iqar": iqar, "nu_concentracao": conc, situacao_col: "VA", "cd_flag": "", "ds_flag": "",
        "st_situacao_iqar": "VA", "no_item_monitorado": parametro, "cd_normalizado": parametro,
        "id_estacao": id_estacao, "cod_estacao": "3", "no_estacao": nome, "nu_latitude": "-23.5475",
        "nu_longitude": "-46.636111", "st_estacao": "O", "id_municipio": "3550308", "no_municipio": "São Paulo", "sg_uf": "SP",
    }


@pytest.fixture(scope="session")
def fonte_real() -> FonteMonitorAr:
    return FonteMonitorAr(NOME_REAL, RECORTE_REAL, ESTACOES, METADADOS)


@pytest.fixture(scope="session")
def registros_reais(fonte_real) -> pd.DataFrame:
    return fonte_real.carregar_registros()


@pytest.fixture(scope="session")
def controller() -> PainelController:
    """Controller montado exatamente como no app, sem variáveis de ambiente."""
    return PainelController.a_partir_da_configuracao(Configuracao.carregar({}))


@pytest.fixture(scope="session")
def demo_largo() -> pd.DataFrame:
    return FonteCSV("demo", CSV_DEMO).carregar_dados()
