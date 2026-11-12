"""Testes das fontes de dados: leitura de dados reais, fictícios, QUALAR e banco."""

import gzip
import json

import pandas as pd
import pytest

from models.fontes import (
    COLUNAS_REGISTROS,
    ErroFonteDados,
    FonteCSV,
    FonteDados,
    FonteMonitorAr,
    FontePostgres,
    FonteQualar,
    ler_exportacao_qualar,
)
from tests.conftest import CSV_DEMO, ESTACOES, METADADOS, construir_largo, linha_monitorar


# =============================================================================
# Dados reais (MonitorAr) — conferência com os registros originais
# =============================================================================
def test_recorte_real_tem_o_total_de_linhas_registrado_nos_metadados(fonte_real, registros_reais):
    """O total lido deve bater com o que o script contou nos arquivos oficiais."""
    meta = json.loads(METADADOS.read_text(encoding="utf-8"))
    indices_por_poluente = registros_reais[registros_reais["parametro"] != "IQAR"]
    assert len(indices_por_poluente) == meta["total_de_linhas"] == 92753


def test_contagem_por_estacao_e_parametro_bate_com_os_arquivos_oficiais(registros_reais):
    """Cada combinação estação + parâmetro tem exatamente as linhas contadas no arquivo oficial."""
    meta = json.loads(METADADOS.read_text(encoding="utf-8"))["linhas_por_estacao_e_parametro"]
    lidos = registros_reais[registros_reais["parametro"] != "IQAR"].groupby(["estacao_id", "parametro"]).size()
    for chave, quantidade in meta.items():
        estacao_id, _, parametro = chave.split("|")
        assert lidos[(estacao_id, parametro.replace("MP2,5", "MP2.5"))] == quantidade


@pytest.mark.parametrize(
    "estacao,parametro,data_hora,valor",
    [
        # Valores conferidos de forma INDEPENDENTE: lidos no navegador, direto do zip
        # oficial descompactado, antes de o script de preparação existir.
        ("Mooca", "O3", "2024-01-01 18:00", 22.0),
        ("Mooca", "O3", "2024-01-02 13:00", 19.0),
        ("Mooca", "O3", "2024-01-02 14:00", 24.0),
        ("Mooca", "O3", "2024-01-02 15:00", 29.0),
        ("Diadema", "O3", "2024-01-09 16:00", 51.0),
        ("Diadema", "O3", "2024-01-09 19:00", 72.0),
        ("Congonhas", "MP10", "2024-03-07 16:00", 19.0),
        ("Congonhas", "MP10", "2024-01-14 07:00", 11.0),
    ],
)
def test_valores_pontuais_conferem_com_o_arquivo_oficial(registros_reais, estacao, parametro, data_hora, valor):
    linha = registros_reais[
        (registros_reais["estacao"] == estacao) & (registros_reais["parametro"] == parametro)
        & (registros_reais["data_hora"] == pd.Timestamp(data_hora))
    ]
    assert list(linha["valor"]) == [valor]


def test_dados_reais_so_trazem_indice_sem_concentracao(registros_reais):
    """Para a CETESB, o MonitorAr só tem IQAr: nenhuma concentração pode aparecer."""
    assert set(registros_reais["grandeza"]) == {"indice"}
    assert not registros_reais["parametro"].isin(["TEMP", "UR"]).any()


def test_iqar_da_estacao_e_o_maior_indice_de_cada_hora(registros_reais):
    pol = registros_reais[registros_reais["parametro"] != "IQAR"]
    maior = pol.groupby(["estacao_id", "data_hora"])["valor"].max()
    iqar = registros_reais[registros_reais["parametro"] == "IQAR"].set_index(["estacao_id", "data_hora"])["valor"]
    pd.testing.assert_series_equal(iqar.sort_index(), maior.sort_index(), check_names=False)


def test_um_unico_poluente_por_hora_e_registrado(fonte_real, registros_reais):
    assert fonte_real.metadados["um_poluente_por_hora"] is True
    assert any("único poluente por hora" in t for t in fonte_real.transformacoes)


def test_coordenadas_vem_da_cetesb_e_nao_do_arquivo(registros_reais):
    """No arquivo de 2025 a Mooca aparece com a coordenada genérica -23.5475; usamos a da CETESB."""
    mooca = registros_reais[registros_reais["estacao"] == "Mooca"]
    assert mooca["latitude"].round(4).unique().tolist() == [-23.5497]
    assert (mooca["localizacao"] == "estacao_proxima").all()


def test_colunas_padrao_e_ordem(registros_reais):
    assert list(registros_reais.columns) == COLUNAS_REGISTROS


def test_transformacoes_registradas(fonte_real, registros_reais):
    texto = " ".join(fonte_real.transformacoes)
    assert "st_situacao_item" in texto and "MP2,5" in texto and "CETESB" in texto


# --- arquivos inválidos -----------------------------------------------------
def _gravar_monitorar(tmp_path, linhas, nome="recorte.csv.gz"):
    caminho = tmp_path / nome
    pd.DataFrame(linhas).to_csv(caminho, index=False, compression="gzip")
    return caminho


def test_monitorar_arquivo_inexistente(tmp_path):
    with pytest.raises(ErroFonteDados, match="não encontrado"):
        FonteMonitorAr("x", tmp_path / "nada.csv.gz", ESTACOES).carregar_registros()


def test_monitorar_arquivo_corrompido(tmp_path):
    caminho = tmp_path / "ruim.csv.gz"
    caminho.write_bytes(b"isto nao e gzip")
    with pytest.raises(ErroFonteDados):
        FonteMonitorAr("x", caminho, ESTACOES).carregar_registros()


def test_monitorar_arquivo_vazio(tmp_path):
    caminho = tmp_path / "vazio.csv.gz"
    with gzip.open(caminho, "wt") as f:
        f.write("")
    with pytest.raises(ErroFonteDados):
        FonteMonitorAr("x", caminho, ESTACOES).carregar_registros()


def test_monitorar_sem_coluna_obrigatoria(tmp_path):
    linhas = [linha_monitorar("2024-01-01 00:00:00.000", "10.000")]
    for linha in linhas:
        del linha["nu_iqar"]
    with pytest.raises(ErroFonteDados, match="nu_iqar"):
        FonteMonitorAr("x", _gravar_monitorar(tmp_path, linhas), ESTACOES).carregar_registros()


def test_monitorar_concentracao_sem_unidade_vira_grandeza_separada(tmp_path):
    linhas = [linha_monitorar("2024-01-01 00:00:00.000", "", conc="12.5", parametro="MP10")]
    registros = FonteMonitorAr("x", _gravar_monitorar(tmp_path, linhas), ESTACOES).carregar_registros()
    assert registros["grandeza"].tolist() == ["concentracao"]
    assert registros["unidade"].iloc[0] == "não informada no arquivo"
    assert not registros["unidade_confirmada"].iloc[0]


def test_monitorar_estacao_fora_da_lista_fica_nao_verificada(tmp_path):
    linhas = [linha_monitorar("2024-01-01 00:00:00.000", "10.000", id_estacao="999", nome="Outra")]
    registros = FonteMonitorAr("x", _gravar_monitorar(tmp_path, linhas), ESTACOES).carregar_registros()
    assert (registros["localizacao"] == "estacao").all()
    assert "não verificada" in registros["fonte_localizacao"].iloc[0]


def test_monitorar_aceita_coluna_de_status_de_2024(tmp_path):
    linhas = [linha_monitorar("2024-01-01 00:00:00.000", "10.000", situacao_col="st_situacao_item")]
    registros = FonteMonitorAr("x", _gravar_monitorar(tmp_path, linhas), ESTACOES).carregar_registros()
    assert set(registros["situacao"]) == {"VA"}


# =============================================================================
# Dataset fictício (V1)
# =============================================================================
def test_demo_carrega_8784_linhas(demo_largo):
    assert demo_largo.shape == (8784, 9)
    assert demo_largo["Data"].min() == pd.Timestamp("2024-01-01 00:00")


def test_demo_registros_sao_marcados_como_ficticios():
    fonte = FonteCSV("demo", CSV_DEMO)
    registros = fonte.carregar_registros()
    assert (registros["localizacao"] == "ficticio").all()
    assert set(registros["parametro"]) == {"MP10", "MP2.5", "O3", "CO", "CO2", "NO2", "TEMP", "UR"}
    # células vazias do CSV não viram registros: 8784 horas × 8 colunas − 6 × 263 ausentes
    assert len(registros) == 8784 * 8 - 6 * 263
    assert any("ASSUMIDAS" in t for t in fonte.transformacoes)


def test_fonte_base_e_abstrata():
    with pytest.raises(TypeError):
        FonteDados("x", "y")  # type: ignore[abstract]


def test_csv_inexistente(tmp_path):
    with pytest.raises(ErroFonteDados, match="não encontrado"):
        FonteCSV("csv", tmp_path / "nao.csv").carregar_registros()


def test_csv_sem_colunas(tmp_path):
    caminho = tmp_path / "x.csv"
    caminho.write_text("Data;MP10\n2024-01-01 00:00:00;10\n", encoding="utf-8")
    with pytest.raises(ErroFonteDados, match="colunas esperadas"):
        FonteCSV("csv", caminho).carregar_dados()


def test_csv_vazio(tmp_path):
    caminho = tmp_path / "vazio.csv"
    caminho.write_text("", encoding="utf-8")
    with pytest.raises(ErroFonteDados):
        FonteCSV("csv", caminho).carregar_dados()


def test_csv_latin1(tmp_path):
    df = construir_largo(5, colunas=("MP10", "MP2.5", "O3", "CO", "CO2", "NO2", "Temp", "Umidade"))
    df["Observação"] = "ação"
    caminho = tmp_path / "latin1.csv"
    caminho.write_bytes(df.to_csv(index=False, sep=";").encode("latin1"))
    assert len(FonteCSV("csv", caminho).carregar_dados()) == 5


# =============================================================================
# QUALAR (exportação manual) — arquivo de teste no formato descrito pelo qualR
# =============================================================================
CABECALHO_QUALAR = "Tipo de Rede;Tipo de Monitoramento;Tipo;Data;Hora;Código Estação;Nome Estação;Nome Parâmetro;Unidade de Medida;Média Horária;Média Móvel;Válido"


def _arquivo_qualar(tmp_path, linhas, nome="mooca_mp10.csv", preambulo=True, codificacao="latin1"):
    texto = ("Relatório exportado do QUALAR\nPeríodo: 01/01/2024 a 02/01/2024\n\n" if preambulo else "")
    texto += CABECALHO_QUALAR + "\n" + "\n".join(linhas) + "\n"
    caminho = tmp_path / nome
    caminho.write_bytes(texto.encode(codificacao))
    return caminho


def test_qualar_le_numero_brasileiro_e_hora_24(tmp_path):
    caminho = _arquivo_qualar(tmp_path, [
        "Automática;Automático;Dados horários;01/01/2024;01:00;85;Mooca;MP10 (Partículas Inaláveis);ug/m3;25,4;;Sim",
        "Automática;Automático;Dados horários;01/01/2024;24:00;85;Mooca;MP10 (Partículas Inaláveis);ug/m3;1.012,0;;Sim",
    ])
    tabela = ler_exportacao_qualar(caminho)
    assert tabela["valor"].tolist() == [25.4, 1012.0]
    assert tabela["data_hora"].tolist() == [pd.Timestamp("2024-01-01 01:00"), pd.Timestamp("2024-01-02 00:00")]
    assert set(tabela["parametro"]) == {"MP10"} and set(tabela["unidade"]) == {"µg/m³"}


def test_qualar_fonte_descarta_invalidos_e_usa_coordenada_da_lista(tmp_path):
    _arquivo_qualar(tmp_path, [
        "Automática;Automático;Dados horários;01/01/2024;01:00;85;Mooca;TEMP (Temperatura do Ar);ºC;21,3;;Sim",
        "Automática;Automático;Dados horários;01/01/2024;02:00;85;Mooca;TEMP (Temperatura do Ar);ºC;99,9;;Não",
    ])
    fonte = FonteQualar("qualar", tmp_path, ESTACOES)
    registros = fonte.carregar_registros()
    assert registros["valor"].tolist() == [21.3]
    assert registros["grandeza"].iloc[0] == "meteorologia" and registros["unidade"].iloc[0] == "°C"
    assert registros["localizacao"].iloc[0] == "estacao_proxima"
    assert any("não válidos" in t for t in fonte.transformacoes)


def test_qualar_sem_coluna_de_unidade_e_recusado(tmp_path):
    caminho = tmp_path / "sem_unidade.csv"
    caminho.write_text("Data;Hora;Nome Parâmetro;Média Horária\n01/01/2024;01:00;MP10;20\n", encoding="utf-8")
    with pytest.raises(ErroFonteDados, match="unidade"):
        ler_exportacao_qualar(caminho)


def test_qualar_arquivo_vazio(tmp_path):
    caminho = tmp_path / "vazio.csv"
    caminho.write_text("", encoding="utf-8")
    with pytest.raises(ErroFonteDados, match="vazio"):
        ler_exportacao_qualar(caminho)


def test_qualar_sem_cabecalho_reconhecivel(tmp_path):
    caminho = tmp_path / "x.csv"
    caminho.write_text("a;b;c\n1;2;3\n", encoding="utf-8")
    with pytest.raises(ErroFonteDados, match="cabeçalho"):
        ler_exportacao_qualar(caminho)


def test_qualar_pasta_vazia(tmp_path):
    with pytest.raises(ErroFonteDados, match="Nenhum arquivo"):
        FonteQualar("qualar", tmp_path, ESTACOES).carregar_registros()


# =============================================================================
# Banco de dados (testado com SQLite; o caminho de leitura é o mesmo do PostgreSQL)
# =============================================================================
sqlalchemy = pytest.importorskip("sqlalchemy")


def test_postgres_le_tabela(tmp_path, demo_largo):
    url = f"sqlite:///{tmp_path / 'teste.db'}"
    banco = demo_largo.head(48).rename(columns={v: k for k, v in FontePostgres.COLUNAS_BANCO.items()})
    engine = sqlalchemy.create_engine(url)
    banco.to_sql("registros_ambientais", engine, index=False)
    engine.dispose()
    fonte = FontePostgres("banco", url)
    pd.testing.assert_frame_equal(fonte.carregar_dados(), demo_largo.head(48), check_dtype=False)
    assert (fonte.carregar_registros()["localizacao"] == "ficticio").all()


def test_postgres_nome_de_tabela_invalido():
    with pytest.raises(ErroFonteDados, match="tabela inválido"):
        FontePostgres("banco", "sqlite://", "x; DROP TABLE y")


def test_postgres_falha_nao_vaza_senha():
    with pytest.raises(ErroFonteDados) as erro:
        FontePostgres("banco", "postgresql://usuario:SEGREDO123@127.0.0.1:1/db").carregar_registros()
    assert "SEGREDO123" not in str(erro.value)
