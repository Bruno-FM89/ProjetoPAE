"""Testes das peças do Model: catálogo, faixas oficiais, distâncias, conjunto, tratamento e estatística."""

import numpy as np
import pandas as pd
import pytest

from models.conjunto import ConjuntoDados
from models.estatistica import AnaliseEstatistica
from models.localizacao import REFERENCIA_HELIOPOLIS, distancia_ate_heliopolis, distancia_km
from models.parametros import chave_variavel, criar_variavel, normalizar_codigo, normalizar_unidade
from models.qualidade_ar import (
    classificar_concentracao,
    classificar_indice,
    distribuicao_por_faixa,
    medias_no_periodo_oficial,
    pode_classificar_concentracao,
)
from models.tratamento import TratadorDados, interpolar_lacunas_curtas, limites_iqr, nome_coluna_outlier, validar
from tests.conftest import NOME_REAL, construir_largo


# =============================================================================
# Catálogo de parâmetros
# =============================================================================
@pytest.mark.parametrize("texto,codigo", [
    ("MP2,5", "MP2.5"), ("MP10 (Partículas Inaláveis)", "MP10"), ("O3 (Ozônio)", "O3"),
    ("TEMP (Temperatura do Ar)", "TEMP"), ("UR (Umidade Relativa do Ar)", "UR"), ("PM2.5", "MP2.5"), ("XYZ", "XYZ"),
])
def test_normalizar_codigo(texto, codigo):
    assert normalizar_codigo(texto) == codigo


def test_chaves_deixam_clara_a_grandeza():
    assert chave_variavel("MP2.5", "indice") == "MP2.5_IQAr"
    assert chave_variavel("MP2.5", "concentracao") == "MP2.5"
    assert chave_variavel("IQAR", "indice") == "IQAR"


def test_rotulos_de_indice_e_concentracao():
    assert criar_variavel("MP2.5", "indice", "").rotulo == "MP2,5 · índice IQAr"
    assert criar_variavel("MP2.5", "concentracao", "µg/m³").rotulo == "MP2,5 (µg/m³)"
    assert criar_variavel("IQAR", "indice", "").rotulo == "IQAr da estação"


def test_normalizar_unidade():
    assert normalizar_unidade("ug/m3") == "µg/m³"
    assert normalizar_unidade("ºC") == "°C"
    assert normalizar_unidade("ppm") == "ppm"


# =============================================================================
# Faixas oficiais (CETESB / CONAMA 491/2018)
# =============================================================================
@pytest.mark.parametrize("valor,faixa", [
    (0, "N1"), (40, "N1"), (40.5, "N2"), (41, "N2"), (80, "N2"), (81, "N3"), (120, "N3"),
    (121, "N4"), (200, "N4"), (201, "N5"), (1198, "N5"),
])
def test_classificar_indice_nos_limites(valor, faixa):
    assert classificar_indice(valor).codigo == faixa


def test_indice_invalido_nao_tem_faixa():
    assert classificar_indice(-1) is None and classificar_indice(float("nan")) is None


def test_distribuicao_por_faixa_soma_100():
    dist = distribuicao_por_faixa(pd.Series([10, 20, 50, 90, 150, 250, np.nan]))
    assert dist["registros"].tolist() == [2, 1, 1, 1, 1]
    assert dist["percentual"].sum() == pytest.approx(100)


@pytest.mark.parametrize("codigo,valor,faixa", [("MP2.5", 25, "N1"), ("MP2.5", 26, "N2"), ("MP10", 151, "N4"), ("NO2", 1131, "N5")])
def test_classificar_concentracao(codigo, valor, faixa):
    assert classificar_concentracao(valor, codigo).codigo == faixa


def test_concentracao_so_e_classificada_com_unidade_confirmada_e_igual():
    assert pode_classificar_concentracao("MP10", "µg/m³", True)
    assert not pode_classificar_concentracao("MP10", "µg/m³", False)  # unidade suposta
    assert not pode_classificar_concentracao("CO", "µg/m³", True)  # limites do CO estão em ppm
    assert not pode_classificar_concentracao("TEMP", "°C", True)  # sem limites oficiais


def test_media_24h_exige_16_horas_validas():
    indice = pd.date_range("2024-01-01", periods=48, freq="h")
    serie = pd.Series(10.0, index=indice)
    serie.iloc[24:24 + 9] = np.nan  # o segundo dia fica com só 15 horas
    medias = medias_no_periodo_oficial(serie, "MP10")
    assert list(medias.index.date) == [pd.Timestamp("2024-01-01").date()]


def test_media_8h_exige_as_8_horas():
    indice = pd.date_range("2024-01-01", periods=10, freq="h")
    serie = pd.Series(np.arange(10, dtype=float), index=indice)
    serie.iloc[5] = np.nan
    medias = medias_no_periodo_oficial(serie, "O3")
    assert medias.empty  # nenhuma janela de 8 horas completas


# =============================================================================
# Localização
# =============================================================================
def test_distancia_zero_e_simetrica():
    assert distancia_km(-23.6, -46.6, -23.6, -46.6) == pytest.approx(0)
    assert distancia_km(-23.6, -46.6, -23.5, -46.5) == pytest.approx(distancia_km(-23.5, -46.5, -23.6, -46.6))


def test_distancia_conhecida():
    # 1 grau de latitude ≈ 111,2 km
    assert distancia_km(0, 0, 1, 0) == pytest.approx(111.2, abs=0.1)


def test_distancia_mooca_e_sem_coordenada():
    assert distancia_ate_heliopolis(-23.549734, -46.600417) == pytest.approx(6.71, abs=0.01)
    assert distancia_ate_heliopolis(None, None) is None and distancia_ate_heliopolis(float("nan"), 1.0) is None
    assert REFERENCIA_HELIOPOLIS.fonte.startswith("OpenStreetMap")


# =============================================================================
# ConjuntoDados (tabelas por estação)
# =============================================================================
@pytest.fixture(scope="module")
def conjunto(registros_reais):
    return ConjuntoDados(registros_reais, NOME_REAL)


def test_seis_estacoes_ordenadas_por_distancia(conjunto):
    estacoes = conjunto.estacoes()
    assert estacoes["estacao"].tolist()[0] == "Mooca"
    assert len(estacoes) == 6 and estacoes["distancia_km"].is_monotonic_increasing
    assert estacoes["distancia_km"].between(6, 10).all()


def test_tabela_larga_tem_grade_horaria_completa(conjunto):
    larga = conjunto.tabela_larga("128")
    esperado = pd.date_range("2024-01-01 00:00", "2025-12-31 22:00", freq="h")
    assert larga["Data"].tolist() == list(esperado)
    assert list(larga.columns) == ["Data", "IQAR", "MP2.5_IQAr", "O3_IQAr", "CO_IQAr"]


def test_tabela_larga_nao_mistura_estacoes(conjunto, registros_reais):
    larga = conjunto.tabela_larga("128").set_index("Data")
    mooca_o3 = registros_reais[(registros_reais["estacao_id"] == "128") & (registros_reais["parametro"] == "O3")]
    assert larga["O3_IQAr"].notna().sum() == len(mooca_o3)
    assert (larga.loc[mooca_o3["data_hora"], "O3_IQAr"].to_numpy() == mooca_o3["valor"].to_numpy()).all()


def test_cobertura(conjunto):
    cob = conjunto.cobertura("128").set_index("chave")
    assert cob.loc["IQAR", "horas_com_valor"] == 15503
    assert cob.loc["IQAR", "percentual"] == pytest.approx(15503 / 17543 * 100)


def test_estacao_desconhecida(conjunto):
    with pytest.raises(ValueError):
        conjunto.tabela_larga("nao-existe")


def _registros(linhas):
    base = {"estacao_id": "E1", "estacao": "E", "municipio": "M", "endereco": "", "latitude": np.nan, "longitude": np.nan,
            "fonte_localizacao": "", "localizacao": "estacao", "grandeza": "concentracao", "unidade_confirmada": True, "situacao": ""}
    return pd.DataFrame([{**base, **l} for l in linhas]).assign(data_hora=lambda d: pd.to_datetime(d["data_hora"]))


def test_unidades_diferentes_viram_variaveis_diferentes():
    reg = _registros([
        {"data_hora": "2024-01-01 00:00", "parametro": "CO", "unidade": "ppm", "valor": 1.0},
        {"data_hora": "2024-01-01 00:00", "parametro": "CO", "unidade": "mg/m³", "valor": 1.2},
    ])
    catalogo = ConjuntoDados(reg, "t").catalogo
    assert sorted(catalogo) == ["CO [mg/m³]", "CO [ppm]"]


def test_duplicados_na_mesma_hora_mantem_o_primeiro():
    reg = _registros([
        {"data_hora": "2024-01-01 00:00", "parametro": "MP10", "unidade": "µg/m³", "valor": 10.0},
        {"data_hora": "2024-01-01 00:00", "parametro": "MP10", "unidade": "µg/m³", "valor": 99.0},
        {"data_hora": "2024-01-01 02:00", "parametro": "MP10", "unidade": "µg/m³", "valor": 30.0},
    ])
    conjunto = ConjuntoDados(reg, "t")
    larga = conjunto.tabela_larga("E1")
    assert larga["MP10"].tolist()[0] == 10.0
    assert len(larga) == 3 and np.isnan(larga["MP10"].iloc[1])  # 01:00 sem registro fica vazia
    assert any("repetido" in t for t in conjunto.transformacoes)


# =============================================================================
# Tratamento
# =============================================================================
def _serie(valores):
    return pd.Series(valores, index=pd.date_range("2024-01-01", periods=len(valores), freq="h"), dtype=float)


def test_interpola_lacuna_curta():
    assert list(interpolar_lacunas_curtas(_serie([10, np.nan, np.nan, 40]), 4)) == [10, 20, 30, 40]


def test_nao_interpola_lacuna_longa_nem_pontas():
    r = interpolar_lacunas_curtas(_serie([np.nan, 1, np.nan, np.nan, np.nan, np.nan, np.nan, 7, np.nan]), 4)
    assert r.isna().sum() == 7


def test_limites_iqr():
    lim = limites_iqr(pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 100], dtype=float))
    assert (lim.q1, lim.q3, lim.iqr, lim.superior) == pytest.approx((3.25, 7.75, 4.5, 14.5))


def test_outlier_sinalizado_nao_removido():
    df = construir_largo(100)
    df.loc[50, "A"] = 5000.0
    t = TratadorDados(df, ["A", "B", "C"])
    assert len(t.original) == 100
    assert t.original.loc[t.original[nome_coluna_outlier("A")], "A"].tolist() == [5000.0]


def test_original_preservado_e_tratado_separado():
    df = construir_largo(48)
    df.loc[[5, 6], "B"] = np.nan
    copia = df.copy()
    t = TratadorDados(df, ["A", "B", "C"])
    pd.testing.assert_frame_equal(df, copia)
    assert t.original["B"].isna().sum() == 2 and t.tratado["B"].isna().sum() == 0
    assert t.tratado["n_imputados"].sum() == 2


def test_tratador_aceita_qualquer_conjunto_de_colunas():
    t = TratadorDados(construir_largo(24, colunas=("IQAR",)), ["IQAR"])
    assert t.colunas == ["IQAR"] and t.relatorio.mp25_maior_mp10 is None


def test_relatorio_compara_mp25_e_mp10_so_quando_existem():
    df = construir_largo(24, colunas=("MP2.5", "MP10"))
    df.loc[0, "MP2.5"] = 999
    assert validar(df, ["MP2.5", "MP10"]).mp25_maior_mp10 == 1


def test_relatorio_lacunas_e_horas_vazias():
    df = construir_largo(24, colunas=("A", "B"))
    df.loc[3:6, "A"] = np.nan
    df.loc[5, "B"] = np.nan
    r = validar(df, ["A", "B"])
    assert r.maior_lacuna_horas["A"] == 4 and r.horas_sem_nenhum_valor == 1


def test_tratador_rejeita_colunas_ausentes_e_vazio():
    with pytest.raises(ValueError):
        TratadorDados(construir_largo(10), ["A", "Z"])
    with pytest.raises(ValueError):
        TratadorDados(construir_largo(10).iloc[0:0], ["A"])


# =============================================================================
# Estatística
# =============================================================================
def test_exemplo_dos_slides():
    d = AnaliseEstatistica(pd.DataFrame({"T": [22, 24, 24, 26, 30]})).descritiva(["T"]).loc["T"]
    assert (d["media"], d["mediana"], d["moda"]) == (pytest.approx(25.2), 24, 24)


def test_descritiva_confere_com_pandas():
    df = construir_largo(100)
    d = AnaliseEstatistica(df).descritiva(["A"]).loc["A"]
    assert d["media"] == pytest.approx(df["A"].mean()) and d["desvio_padrao"] == pytest.approx(df["A"].std())
    assert d["variancia"] == pytest.approx(df["A"].var())


def test_descritiva_vazia_nao_quebra():
    d = AnaliseEstatistica(pd.DataFrame({"A": [np.nan, np.nan]})).descritiva(["A"]).loc["A"]
    assert d["n"] == 0 and np.isnan(d["media"])


def test_correlacao_exige_30_pares():
    df = pd.DataFrame({"A": np.arange(29.0), "B": np.arange(29.0)})
    assert np.isnan(AnaliseEstatistica(df).correlacao(["A", "B"]).loc["A", "B"])
    df = pd.DataFrame({"A": np.arange(30.0), "B": np.arange(30.0)})
    assert AnaliseEstatistica(df).correlacao(["A", "B"]).loc["A", "B"] == pytest.approx(1.0)


def test_media_mensal_separa_anos():
    t = TratadorDados(construir_largo(24 * 400, colunas=("A",)), ["A"])
    mensal = AnaliseEstatistica(t.original).media_mensal("A")
    assert len(mensal) == 14 and mensal["mes"].iloc[0] == pd.Timestamp("2024-01-01")


@pytest.mark.parametrize("r,texto", [(0.05, "praticamente nula"), (-0.5, "moderada negativa"), (0.95, "muito forte positiva"), (float("nan"), "indefinida")])
def test_classificar_correlacao(r, texto):
    assert texto in AnaliseEstatistica.classificar_correlacao(r)
