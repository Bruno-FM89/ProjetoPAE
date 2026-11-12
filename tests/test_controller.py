"""Testes do Controller: filtros, períodos, estações, interpretações, exportação e configuração."""

import io
import socket
from datetime import date

import numpy as np
import pandas as pd
import pytest

from controllers.painel_controller import Filtros, PainelController
from models.fontes import ErroFonteDados, FonteCSV
from services.config import Configuracao
from tests.conftest import CSV_DEMO, NOME_DEMO, NOME_REAL


def filtros_reais(estacao="128", **extra) -> Filtros:
    base = dict(fonte=NOME_REAL, estacao=estacao, inicio=date(2024, 1, 1), fim=date(2025, 12, 31), variavel="IQAR")
    return Filtros(**{**base, **extra})


def filtros_demo(**extra) -> Filtros:
    base = dict(fonte=NOME_DEMO, estacao="DEMO", inicio=date(2024, 1, 1), fim=date(2024, 12, 31), variavel="MP2.5")
    return Filtros(**{**base, **extra})


# --- fontes e padrões ------------------------------------------------------------
def test_fontes_carregadas_na_ordem_real_primeiro(controller):
    assert controller.nomes_fontes == [NOME_REAL, NOME_DEMO]
    assert not controller.eh_ficticia(NOME_REAL) and controller.eh_ficticia(NOME_DEMO)


def test_padroes_iniciais(controller):
    assert controller.estacao_padrao(NOME_REAL) == "128"  # Mooca, a mais próxima
    assert controller.variavel_padrao(NOME_REAL, "128") == "IQAR"
    assert controller.periodo_disponivel(NOME_REAL, "128") == (date(2024, 1, 1), date(2025, 12, 31))


def test_contexto_identifica_local_e_fonte(controller):
    ctx = controller.contexto(filtros_reais())
    assert ctx["estacao"] == "Mooca" and ctx["localizacao"] == "estacao_proxima"
    assert "fora de Heliópolis" in ctx["tipo_localizacao"]
    assert ctx["distancia_km"] == pytest.approx(6.71, abs=0.01)


def test_versao_padrao_e_a_original():
    assert filtros_reais().dados == "originais"


# --- filtros de período -------------------------------------------------------------
def test_filtro_de_periodo(controller):
    df = controller.dados_filtrados(filtros_reais(inicio=date(2024, 3, 1), fim=date(2024, 3, 31)))
    assert len(df) == 31 * 24 and df["Data"].min() == pd.Timestamp("2024-03-01")


def test_periodo_sem_registros_nao_quebra_nada(controller):
    f = filtros_reais(inicio=date(2030, 1, 1), fim=date(2030, 1, 31))
    assert controller.sem_dados(f) and controller.indicadores(f) == {}
    controller.serie_temporal(f)
    controller.descritiva(f)
    controller.padroes(f)
    controller.resumo_outliers(f)
    controller.comparar_original_tratado(f)
    assert controller.interpretacoes(f) == ["Não há valores desta variável no período escolhido."]
    assert controller.exportar_csv(f).decode().startswith("Data;estacao;municipio;tipo_de_local;fonte")


def test_periodo_invertido(controller):
    assert controller.sem_dados(filtros_reais(inicio=date(2024, 5, 1), fim=date(2024, 4, 1)))


def test_variavel_sem_valores_no_periodo(controller):
    # o CO da Mooca só tem registros até abril de 2025
    f = filtros_reais(inicio=date(2025, 6, 1), fim=date(2025, 6, 30), variavel="CO_IQAr")
    assert not controller.tem_valores(f, "CO_IQAr")
    assert controller.interpretacoes(f) == ["Não há valores desta variável no período escolhido."]


# --- originais × tratados e outliers -------------------------------------------------
def test_tratados_preenchem_apenas_lacunas_curtas(controller):
    original = controller.dados_filtrados(filtros_reais())
    tratado = controller.dados_filtrados(filtros_reais(dados="tratados"))
    assert tratado["IQAR"].notna().sum() > original["IQAR"].notna().sum()
    assert tratado["IQAR"].isna().sum() > 0  # lacunas longas continuam vazias
    onde_tinha = original["IQAR"].notna()
    assert (tratado.loc[onde_tinha, "IQAR"] == original.loc[onde_tinha, "IQAR"]).all()


def test_excluir_outliers_vira_ausente(controller):
    com = controller.dados_filtrados(filtros_reais())
    sem = controller.dados_filtrados(filtros_reais(excluir_outliers=True))
    assert len(com) == len(sem)
    assert sem["IQAR"].isna().sum() - com["IQAR"].isna().sum() == int(com["outlier_IQAR"].sum())


# --- estatística e interpretações calculadas -----------------------------------------
def test_indicadores_conferem_com_calculo_direto(controller, registros_reais):
    ind = controller.indicadores(filtros_reais())
    iqar = registros_reais[(registros_reais["estacao_id"] == "128") & (registros_reais["parametro"] == "IQAR")]["valor"]
    assert ind["variaveis"]["IQAR"]["media"] == pytest.approx(iqar.mean())
    assert ind["variaveis"]["IQAR"]["mediana"] == pytest.approx(iqar.median())
    assert ind["variaveis"]["IQAR"]["percentual_boa"] == pytest.approx((iqar <= 40).mean() * 100)


def test_interpretacao_do_mes_com_maior_media_e_calculada(controller, registros_reais):
    iqar = registros_reais[(registros_reais["estacao_id"] == "128") & (registros_reais["parametro"] == "IQAR")]
    mensal = iqar.set_index("data_hora")["valor"].resample("MS").agg(["mean", "count"])
    mensal = mensal[mensal["count"] >= 24]
    maior = mensal["mean"].idxmax()
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    frases = " ".join(controller.interpretacoes(filtros_reais()))
    assert f"{meses[maior.month - 1]} de {maior.year}" in frases


def test_aviso_de_um_poluente_por_hora(controller):
    frases = " ".join(controller.interpretacoes(filtros_reais(variavel="O3_IQAr")))
    assert "único poluente" in frases


def test_correlacao_bloqueada_quando_nao_faz_sentido(controller):
    assert controller.motivo_sem_correlacao(NOME_REAL) is not None
    assert controller.motivo_sem_correlacao(NOME_DEMO) is None


def test_poluente_registrado_soma_as_horas(controller):
    tabela = controller.poluente_registrado(filtros_reais())
    assert tabela["horas"].sum() == 15503
    assert set(tabela["poluente"]) == {"MP2,5", "O₃", "CO"}


def test_faixas_do_indice(controller):
    dist = controller.distribuicao_faixas(filtros_reais(), "IQAR")
    assert dist["registros"].sum() == 15503 and dist["percentual"].sum() == pytest.approx(100)
    assert controller.distribuicao_faixas(filtros_demo(), "MP2.5") is None


def test_classificacao_de_concentracao_recusada_no_demo(controller):
    tabela, mensagem = controller.classificacao_concentracao(filtros_demo(), "MP2.5")
    assert tabela is None and "não foi confirmada" in mensagem


# --- comparação entre estações -------------------------------------------------------
def test_comparar_estacoes_mantem_cada_estacao_separada(controller):
    f = filtros_reais(agregacao="D")
    tabela = controller.comparar_estacoes(f, "IQAR", ["128", "127"])
    assert list(tabela.columns) == ["Data", "Mooca", "Ibirapuera"]
    sozinha = controller.serie_temporal(filtros_reais(estacao="127", agregacao="D"), ["IQAR"]).set_index("Data")["IQAR"]
    pd.testing.assert_series_equal(tabela.set_index("Data")["Ibirapuera"], sozinha, check_names=False)


# --- demonstração (dados fictícios) ---------------------------------------------------
def test_demo_mantem_as_8_variaveis_e_estatisticas_da_v1(controller):
    f = filtros_demo()
    assert controller.colunas(f) == ["MP2.5", "MP10", "O3", "NO2", "CO", "CO2", "TEMP", "UR"]
    assert controller.descritiva(f, ["TEMP"]).loc["TEMP", "media"] == pytest.approx(22.0013, abs=1e-3)
    r, pares = controller.correlacao_entre(f, "MP10", "MP2.5")
    assert r > 0.9 and pares > 8000


# --- exportação ------------------------------------------------------------------------
def test_exportacao_identifica_estacao_e_confere_valores(controller):
    f = filtros_reais(inicio=date(2024, 1, 1), fim=date(2024, 1, 2))
    lido = pd.read_csv(io.BytesIO(controller.exportar_csv(f, ["IQAR", "O3_IQAr"])), sep=";", parse_dates=["Data"])
    assert list(lido.columns) == ["Data", "estacao", "municipio", "tipo_de_local", "fonte", "IQAR", "O3_IQAr"]
    assert set(lido["estacao"]) == {"Mooca"} and lido["tipo_de_local"].str.contains("fora de Heliópolis").all()
    assert lido.loc[lido["Data"] == pd.Timestamp("2024-01-01 18:00"), "O3_IQAr"].item() == 22.0


def test_exportacao_com_marcacoes(controller):
    f = filtros_demo(inicio=date(2024, 2, 1), fim=date(2024, 2, 2))
    lido = pd.read_csv(io.BytesIO(controller.exportar_csv(f, ["MP10"], incluir_marcacoes=True)), sep=";")
    assert {"outlier_MP10", "n_imputados"} <= set(lido.columns)


# --- configuração e falhas de fonte -----------------------------------------------------
def test_configuracao_padrao_nao_exige_credenciais():
    cfg = Configuracao.carregar({})
    assert not cfg.usa_banco and cfg.caminho_monitorar.name == "monitorar_estacoes_proximas.csv.gz"


def test_configuracao_valores_invalidos():
    cfg = Configuracao.carregar({"PAE_LIMITE_LACUNA_HORAS": "abc", "PAE_FATOR_IQR": "-2"})
    assert (cfg.limite_lacuna_horas, cfg.fator_iqr) == (4, 1.5)


def test_sem_dados_reais_o_app_avisa_e_usa_a_demonstracao(tmp_path):
    cfg = Configuracao.carregar({"PAE_DADOS_MONITORAR": str(tmp_path / "nao_existe.csv.gz"), "PAE_PASTA_QUALAR": str(tmp_path)})
    ctrl = PainelController.a_partir_da_configuracao(cfg)
    assert ctrl.nomes_fontes == [NOME_DEMO]
    assert any("dados reais não encontrado" in a for a in ctrl.avisos)


def test_uma_fonte_com_erro_nao_derruba_as_outras(tmp_path):
    ctrl = PainelController([FonteCSV("quebrada", tmp_path / "x.csv"), FonteCSV(NOME_DEMO, CSV_DEMO)])
    assert ctrl.nomes_fontes == [NOME_DEMO] and any("quebrada" in a for a in ctrl.avisos)


def test_todas_as_fontes_com_erro(tmp_path):
    with pytest.raises(ErroFonteDados, match="Nenhuma fonte"):
        PainelController([FonteCSV("a", tmp_path / "a.csv")])


def test_banco_indisponivel_nao_impede_o_app():
    cfg = Configuracao.carregar({"DATABASE_URL": "postgresql://u:SEGREDO@127.0.0.1:1/db"})
    ctrl = PainelController.a_partir_da_configuracao(cfg)
    assert NOME_REAL in ctrl.nomes_fontes and not any("SEGREDO" in a for a in ctrl.avisos)


def test_funciona_sem_internet(monkeypatch):
    """Bloqueia qualquer conexão de rede e confere que os dados carregam e os cálculos rodam."""
    def sem_rede(*args, **kwargs):
        raise OSError("rede bloqueada no teste")
    monkeypatch.setattr(socket.socket, "connect", sem_rede)
    ctrl = PainelController.a_partir_da_configuracao(Configuracao.carregar({}))
    f = filtros_reais()
    assert ctrl.indicadores(f)["horas"] == 17543
    assert np.isfinite(ctrl.descritiva(f, ["IQAR"]).loc["IQAR", "media"])
