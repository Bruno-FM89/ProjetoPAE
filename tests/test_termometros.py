"""Testes dos termômetros da comunidade: leitura das planilhas, cálculos e Controller.

Dois tipos de teste:
* com uma planilha SINTÉTICA criada no próprio teste (valores conhecidos), para
  conferir a leitura e os cálculos com exatidão;
* com os dados REAIS preparados (``data/termometros``), para conferir que o
  sistema bate com o resumo gravado pelos próprios aparelhos.
"""

from datetime import date, datetime, timedelta

import openpyxl
import pandas as pd
import pytest

from controllers.termometros_controller import COL_TEMP, COL_UMID, FiltrosTermometros, TermometrosController
from models.fontes import ErroFonteDados
from models.termometros import AnaliseTermometros, DadosTermometros, ler_planilha_rc51h
from scripts import preparar_dados_termometros
from services.config import Configuracao


# --- planilha sintética no formato do registrador RC-51H -------------------------------
def criar_planilha(caminho, leituras, resumo=("25,0°C / 60,0%RH", "20,0°C / 50,0%RH", "22,5°C / 55,0%RH")):
    """Cria uma planilha com as abas Resumo e Lista, igual à exportada pelo aparelho.

    ``leituras``: lista de (datetime, "temperatura com vírgula", "umidade com vírgula").
    O arquivo é salvo com extensão .xls, mas em formato .xlsx (como os arquivos da UNAS).
    """
    livro = openpyxl.Workbook()
    aba = livro.active
    aba.title = "Resumo"
    aba.append(["Relatório"])
    aba.append(["Modelo", "RC-51H", "", "Tipo de Sensor", "Temperatura & Umidade(Interna)"])
    aba.append(["Modo Iniciar", "Início cronometrado", "", "Intervalo", "0:10:0"])
    aba.append(["Fuso horário", "UTC -03:00", "", "Modo parada", "Use Software"])
    aba.append(["Máximo", resumo[0], "", "Primeira leitura", str(leituras[0][0])])
    aba.append(["Mínimo", resumo[1], "", "Ultima leitura", str(leituras[-1][0])])
    aba.append(["Média", resumo[2], "", "Leituras Atuais", str(len(leituras))])
    lista = livro.create_sheet("Lista")
    lista.append(["Não.", "Tempo", "Temperatura°C", "Umidade%RH"])
    for i, (quando, temp, umid) in enumerate(leituras, start=1):
        lista.append([str(i), quando.strftime("%Y-%m-%d %H:%M:%S"), temp, umid])
    livro.save(caminho)
    return caminho


def leituras_regulares(inicio="2025-03-01 00:00", n=300, temp_base=20.0):
    """n leituras de 10 em 10 minutos, temperatura subindo 0,1 a cada leitura (ciclo de 50)."""
    t0 = datetime.fromisoformat(inicio)
    return [
        (t0 + timedelta(minutes=10 * i), f"{temp_base + (i % 50) / 10:.1f}".replace(".", ","), f"{60 + (i % 20) / 2:.1f}".replace(".", ","))
        for i in range(n)
    ]


def test_leitura_converte_virgula_e_le_resumo(tmp_path):
    caminho = criar_planilha(tmp_path / "Casa.xls", leituras_regulares(n=10))
    dados, info = ler_planilha_rc51h(caminho)
    assert len(dados) == 10
    assert dados["temperatura_c"].iloc[1] == pytest.approx(20.1)
    assert dados["umidade_pct"].iloc[2] == pytest.approx(61.0)
    assert info["modelo"] == "RC-51H"
    assert info["intervalo_observado_min"] == 10
    assert info["resumo_do_aparelho"]["temperatura_maximo"] == 25.0
    assert info["resumo_do_aparelho"]["umidade_media"] == 55.0
    assert info["problemas"] == []


def test_leitura_sinaliza_problemas_sem_inventar_valores(tmp_path):
    leituras = leituras_regulares(n=6)
    leituras[2] = (leituras[2][0], "", "55,0")          # temperatura vazia
    leituras[3] = (leituras[3][0], "21,0", "120,0")     # umidade impossível
    leituras[4] = (leituras[3][0], "21,0", "50,0")      # horário repetido
    del leituras[5]
    leituras.append((leituras[-1][0] + timedelta(hours=2), "22,0", "50,0"))  # interrupção de 2 h
    dados, info = ler_planilha_rc51h(criar_planilha(tmp_path / "x.xls", leituras))
    texto = " ".join(info["problemas"])
    assert "repetida" in texto and "sem valor de temperatura" in texto and "fora de 0–100" in texto and "interrupção" in texto
    assert dados["temperatura_c"].isna().sum() == 1     # o vazio continua vazio
    assert dados["umidade_pct"].isna().sum() == 1       # a umidade impossível vira ausente
    assert info["lacunas_na_serie"] == 1


def test_planilha_sem_aba_lista_gera_erro_claro(tmp_path):
    livro = openpyxl.Workbook()
    livro.active.title = "Outra"
    livro.save(tmp_path / "ruim.xlsx")
    with pytest.raises(ErroFonteDados, match="Lista"):
        ler_planilha_rc51h(tmp_path / "ruim.xlsx")


def test_script_de_preparacao_anonimiza_e_gera_arquivos(tmp_path, monkeypatch):
    bruto = tmp_path / "bruto"
    bruto.mkdir()
    criar_planilha(bruto / "Maria.xls", leituras_regulares(n=20))
    criar_planilha(bruto / "Joao.xls", leituras_regulares(inicio="2025-03-02 00:00", n=20))
    monkeypatch.setattr(preparar_dados_termometros, "PASTA_SAIDA", tmp_path)
    assert preparar_dados_termometros.main(["--pasta", str(bruto)]) == 0
    medicoes = pd.read_csv(tmp_path / "medicoes_termometros.csv.gz")
    assert set(medicoes["termometro_id"]) == {"T1", "T2"}
    conteudo = (tmp_path / "metadados_termometros.json").read_text(encoding="utf-8") + medicoes.to_csv()
    assert "Maria" not in conteudo and "Joao" not in conteudo  # nomes de moradores não saem da pasta bruta
    correspondencia = pd.read_csv(bruto / "correspondencia.csv", sep=";")
    assert dict(zip(correspondencia["arquivo"], correspondencia["termometro_id"])) == {"Joao.xls": "T1", "Maria.xls": "T2"}
    # Uma planilha nova recebe o próximo número, sem mudar os antigos.
    criar_planilha(bruto / "Ana.xls", leituras_regulares(n=20))
    preparar_dados_termometros.main(["--pasta", str(bruto)])
    correspondencia = pd.read_csv(bruto / "correspondencia.csv", sep=";")
    assert dict(zip(correspondencia["arquivo"], correspondencia["termometro_id"]))["Ana.xls"] == "T3"


# --- cálculos -------------------------------------------------------------------------------
@pytest.fixture
def dados_sinteticos(tmp_path):
    """Dois termômetros: T1 de 1 a 3/mar, T2 de 2 a 4/mar (período em comum: 2 a 3/mar)."""
    linhas = []
    for tid, inicio, base in (("T1", "2025-03-01", 20.0), ("T2", "2025-03-02", 30.0)):
        for i in range(3 * 144):
            linhas.append({"termometro_id": tid, "data_hora": pd.Timestamp(inicio) + pd.Timedelta(minutes=10 * i),
                           "temperatura_c": base + (i % 144) / 144 * 10, "umidade_pct": 80 - (i % 144) / 144 * 20})
    caminho = tmp_path / "medicoes.csv.gz"
    pd.DataFrame(linhas).to_csv(caminho, index=False)
    (tmp_path / "locais.csv").write_text(
        "termometro_id;nome_exibicao;quebrada;localizacao_validada;observacao\nT1;Casa A;Lagoa;sim;\n", encoding="utf-8")
    return DadosTermometros(caminho, tmp_path / "nao_existe.json", tmp_path / "locais.csv")


def test_periodo_comum_e_total(dados_sinteticos):
    assert dados_sinteticos.periodo(["T1", "T2"]) == (date(2025, 3, 1), date(2025, 3, 4))
    # O período em comum tem data E hora: da 1ª leitura do T2 à última do T1.
    assert dados_sinteticos.periodo_comum(["T1", "T2"]) == (datetime(2025, 3, 2, 0, 0), datetime(2025, 3, 3, 23, 50))


def test_locais_nome_quebrada_e_validacao(dados_sinteticos):
    t1, t2 = dados_sinteticos.termometro("T1"), dados_sinteticos.termometro("T2")
    assert (t1.nome, t1.quebrada, t1.localizacao_validada) == ("Casa A", "Lagoa", True)
    assert (t2.nome, t2.quebrada, t2.localizacao_validada) == ("Termômetro 2", "", False)


def test_resumo_media_minimo_maximo(dados_sinteticos):
    analise = AnaliseTermometros(dados_sinteticos.recorte(["T1"], date(2025, 3, 1), date(2025, 3, 1)))
    resumo = analise.resumo().iloc[0]
    assert resumo["leituras"] == 144
    assert resumo["temp_min"] == pytest.approx(20.0)
    assert resumo["temp_max"] == pytest.approx(20 + 143 / 144 * 10)
    assert resumo["temp_amplitude"] == pytest.approx(143 / 144 * 10)
    assert resumo["temp_quando_min"] == pd.Timestamp("2025-03-01 00:00")


def test_serie_diaria_nao_inventa_dias(dados_sinteticos):
    analise = AnaliseTermometros(dados_sinteticos.recorte(["T1", "T2"], date(2025, 3, 1), date(2025, 3, 4)))
    serie = analise.serie(COL_TEMP, "D")
    assert len(serie) == 4
    assert pd.isna(serie.loc["2025-03-01", "T2"])  # T2 ainda não media no dia 1: fica vazio
    assert pd.isna(serie.loc["2025-03-04", "T1"])


def test_perfil_horario_e_tempo_acima(dados_sinteticos):
    analise = AnaliseTermometros(dados_sinteticos.recorte(["T1"], date(2025, 3, 1), date(2025, 3, 3)))
    perfil = analise.perfil_horario(COL_TEMP)
    assert list(perfil.index) == list(range(24)) and perfil["T1"].iloc[23] > perfil["T1"].iloc[0]
    acima = analise.tempo_acima(COL_TEMP, 25.0).loc["T1"]
    assert acima["leituras_acima"] == 3 * 71  # em cada dia, 71 leituras passam de 25 °C
    assert acima["horas_aprox"] == pytest.approx(3 * 71 * 10 / 60)
    assert acima["dias_com_ocorrencia"] == 3


def test_relacao_temperatura_umidade_negativa(dados_sinteticos):
    r, n = AnaliseTermometros(dados_sinteticos.recorte(["T1"], date(2025, 3, 1), date(2025, 3, 3))).correlacao_temp_umid("T1")
    assert r == pytest.approx(-1.0) and n == 3 * 144  # nos dados sintéticos a umidade cai exatamente quando a temperatura sobe


# --- dados reais preparados ---------------------------------------------------------------------
@pytest.fixture(scope="module")
def ctrl_real():
    return TermometrosController.a_partir_da_configuracao(Configuracao.carregar({}))


def test_dados_reais_sem_nomes_de_moradores(ctrl_real):
    assert ctrl_real.ids == ["T1", "T2", "T3", "T4", "T5"]
    assert all(nome.startswith("Termômetro") for nome in ctrl_real.nomes().values())


def test_dados_reais_conferem_com_resumo_do_aparelho(ctrl_real):
    conferencia = ctrl_real.conferencia_com_aparelho()
    assert len(conferencia) == 5 * 2 * 3
    assert conferencia["confere"].all(), conferencia[~conferencia["confere"]]


def test_dados_reais_sem_lacunas_e_periodo_comum(ctrl_real):
    assert all(a["lacunas_na_serie"] == 0 for a in ctrl_real.metadados["aparelhos"])
    # T2 foi o último a começar (17/02 às 19h00) e T3 o primeiro a parar (12/06 às 00h10).
    assert ctrl_real.periodo_comum(ctrl_real.ids) == (datetime(2025, 2, 17, 19, 0), datetime(2025, 6, 12, 0, 10))


def test_interpretacoes_avisam_periodos_diferentes(ctrl_real):
    inicio, fim = ctrl_real.periodo(ctrl_real.ids)
    frases = ctrl_real.interpretacoes(FiltrosTermometros(tuple(ctrl_real.ids), inicio, fim), COL_TEMP)
    assert any("nem todos os termômetros mediram" in f for f in frases)
    comum = ctrl_real.periodo_comum(ctrl_real.ids)
    frases = ctrl_real.interpretacoes(FiltrosTermometros(tuple(ctrl_real.ids), *comum), COL_UMID)
    assert not any("nem todos os termômetros mediram" in f for f in frases)


def test_exportacao_csv(ctrl_real):
    f = FiltrosTermometros(("T1",), date(2025, 3, 1), date(2025, 3, 2), "h")
    texto = ctrl_real.exportar_csv(f).decode("utf-8")
    linhas = texto.strip().splitlines()
    assert linhas[0] == "termometro;fonte;data_hora;temperatura_c;umidade_pct"
    assert len(linhas) == 1 + 48  # 48 horas
    assert "Termômetro 1" in linhas[1]


def test_periodo_sem_dados(ctrl_real):
    f = FiltrosTermometros(("T3",), date(2025, 9, 1), date(2025, 9, 10))  # T3 parou em junho
    assert ctrl_real.sem_dados(f)
    assert ctrl_real.interpretacoes(f, COL_TEMP) == ["Não há medições dos termômetros escolhidos no período."]


# --- regressão: período em comum com data E hora -------------------------------------------------
# Antes da correção, o período em comum devolvia só as DATAS e o recorte pegava os
# dias inteiros: em 17/02/2025 o T2 tinha 30 leituras e os outros 144. Estes testes
# garantem que, no período em comum, todos os termômetros têm exatamente as mesmas horas.
def criar_dados(tmp_path, series, lacunas=None):
    """Cria ``DadosTermometros`` a partir de {id: (primeira leitura, número de leituras)}.

    ``lacunas``: {id: (início, fim)} — leituras nesse intervalo são REMOVIDAS
    (simula o aparelho desligado), sem colocar nada no lugar.
    """
    linhas = []
    for tid, (inicio, n) in series.items():
        for i in range(n):
            linhas.append({"termometro_id": tid, "data_hora": pd.Timestamp(inicio) + pd.Timedelta(minutes=10 * i),
                           "temperatura_c": 20 + (i % 144) / 14.4, "umidade_pct": 70 - (i % 144) / 7.2})
    tabela = pd.DataFrame(linhas)
    for tid, (ini, fim) in (lacunas or {}).items():
        tira = (tabela["termometro_id"] == tid) & tabela["data_hora"].between(pd.Timestamp(ini), pd.Timestamp(fim))
        tabela = tabela[~tira]
    caminho = tmp_path / "medicoes.csv.gz"
    tabela.to_csv(caminho, index=False)
    return DadosTermometros(caminho, tmp_path / "nao_existe.json", tmp_path / "nao_existe.csv")


def limites_por_termometro(recorte):
    """Primeira leitura, última leitura e número de leituras de cada termômetro do recorte."""
    return recorte.groupby("termometro_id")["data_hora"].agg(["min", "max", "count"])


def test_periodo_comum_respeita_horarios_diferentes_no_mesmo_dia(tmp_path):
    # T1: 01/03 00h00 → 03/03 23h50.  T2: 01/03 19h00 → 03/03 08h00.
    dados = criar_dados(tmp_path, {"T1": ("2025-03-01 00:00", 3 * 144), "T2": ("2025-03-01 19:00", 223)})
    comum = dados.periodo_comum(["T1", "T2"])
    assert comum == (datetime(2025, 3, 1, 19, 0), datetime(2025, 3, 3, 8, 0))
    limites = limites_por_termometro(dados.recorte(["T1", "T2"], *comum))
    assert (limites["min"] == pd.Timestamp("2025-03-01 19:00")).all()
    assert (limites["max"] == pd.Timestamp("2025-03-03 08:00")).all()
    assert limites["count"].nunique() == 1 and limites["count"].iloc[0] == 223  # as mesmas horas para os dois


def test_periodo_comum_sem_sobreposicao(tmp_path):
    dados = criar_dados(tmp_path, {"T1": ("2025-03-01 00:00", 144), "T2": ("2025-03-05 00:00", 144)})
    assert dados.periodo_comum(["T1", "T2"]) is None
    assert dados.periodo_comum([]) is None
    ctrl = TermometrosController(dados)
    f = FiltrosTermometros(("T1", "T2"), date(2025, 3, 1), date(2025, 3, 5))
    assert not ctrl.comparacao_justa(f)
    assert any("nem todos os termômetros mediram" in frase for frase in ctrl.interpretacoes(f, COL_TEMP))


def test_periodo_comum_com_um_so_termometro(tmp_path):
    dados = criar_dados(tmp_path, {"T1": ("2025-03-01 18:20", 100), "T2": ("2025-03-01 00:00", 300)})
    comum = dados.periodo_comum(["T1"])
    assert comum == (datetime(2025, 3, 1, 18, 20), datetime(2025, 3, 2, 10, 50))  # 1ª e última leitura do T1
    assert len(dados.recorte(["T1"], *comum)) == 100  # todas as leituras dele, nenhuma do T2


def test_periodo_comum_muda_quando_muda_a_escolha(tmp_path):
    dados = criar_dados(tmp_path, {
        "T1": ("2025-03-01 00:00", 5 * 144),   # 01/03 → 05/03
        "T2": ("2025-03-02 12:00", 144),       # 02/03 12h → 03/03 11h50
        "T3": ("2025-03-04 06:00", 144),       # 04/03 06h → 05/03 05h50
    })
    assert dados.periodo_comum(["T1", "T2"]) == (datetime(2025, 3, 2, 12, 0), datetime(2025, 3, 3, 11, 50))
    assert dados.periodo_comum(["T1", "T3"]) == (datetime(2025, 3, 4, 6, 0), datetime(2025, 3, 5, 5, 50))
    assert dados.periodo_comum(["T2", "T3"]) is None
    for ids in (["T1", "T2"], ["T1", "T3"]):
        limites = limites_por_termometro(dados.recorte(ids, *dados.periodo_comum(ids)))
        assert list(limites.index) == ids
        assert limites["min"].nunique() == 1 and limites["max"].nunique() == 1 and limites["count"].nunique() == 1


def test_lacuna_no_meio_nao_muda_limites_nem_e_preenchida(tmp_path):
    # T2 fica desligado de 02/03 10h00 a 02/03 11h50 (12 leituras a menos).
    dados = criar_dados(
        tmp_path, {"T1": ("2025-03-01 00:00", 3 * 144), "T2": ("2025-03-01 00:00", 3 * 144)},
        lacunas={"T2": ("2025-03-02 10:00", "2025-03-02 11:50")},
    )
    comum = dados.periodo_comum(["T1", "T2"])
    assert comum == (datetime(2025, 3, 1, 0, 0), datetime(2025, 3, 3, 23, 50))  # a lacuna não encolhe o período
    limites = limites_por_termometro(dados.recorte(["T1", "T2"], *comum))
    assert limites.loc["T1", "count"] == 3 * 144
    assert limites.loc["T2", "count"] == 3 * 144 - 12  # nada inventado no lugar da lacuna
    assert not dados.recorte(["T1", "T2"], *comum)[[COL_TEMP, COL_UMID]].isna().any().any()
    # O dia com lacuna não entra na amplitude diária média (só dias completos entram).
    amplitude = AnaliseTermometros(dados.recorte(["T2"], *comum)).amplitude_diaria_media(COL_TEMP)
    assert amplitude.loc["T2"] == pytest.approx(143 / 14.4)


def test_periodo_comum_menor_que_um_dia_sem_dias_completos(tmp_path):
    # Sobreposição de só 6 horas: dá para comparar, mas não há nenhum dia completo.
    dados = criar_dados(tmp_path, {"T1": ("2025-03-01 00:00", 144), "T2": ("2025-03-01 18:00", 144)})
    comum = dados.periodo_comum(["T1", "T2"])
    assert comum == (datetime(2025, 3, 1, 18, 0), datetime(2025, 3, 1, 23, 50))
    analise = AnaliseTermometros(dados.recorte(["T1", "T2"], *comum))
    assert analise.resumo()["leituras"].tolist() == [36, 36]
    assert analise.amplitude_diaria_media(COL_TEMP).empty  # sem dia completo, não calcula amplitude diária


def test_datas_sem_hora_continuam_usando_dias_inteiros(tmp_path):
    # "Todo o período" e "Escolher datas" mandam só datas: o recorte pega o dia inteiro.
    dados = criar_dados(tmp_path, {"T1": ("2025-03-01 00:00", 3 * 144), "T2": ("2025-03-01 19:00", 223)})
    limites = limites_por_termometro(dados.recorte(["T1", "T2"], date(2025, 3, 1), date(2025, 3, 1)))
    assert limites.loc["T1", "count"] == 144 and limites.loc["T2", "count"] == 30


def test_dados_reais_periodo_comum_tem_as_mesmas_horas_para_todos(ctrl_real):
    comum = ctrl_real.periodo_comum(ctrl_real.ids)
    f = FiltrosTermometros(tuple(ctrl_real.ids), *comum, "10min")
    d = ctrl_real.medicoes(f)
    limites = limites_por_termometro(d)
    assert (limites["min"] == pd.Timestamp("2025-02-17 19:00")).all()
    assert (limites["max"] == pd.Timestamp("2025-06-12 00:10")).all()
    assert limites["count"].nunique() == 1  # mesmo número de leituras para os 5
    por_dia = d.groupby(["termometro_id", d["data_hora"].dt.date]).size()
    assert (por_dia.xs(date(2025, 2, 17), level=1) == 30).all()  # antes: T2 com 30 e os outros com 144
    assert (por_dia.xs(date(2025, 6, 12), level=1) == 2).all()   # antes: T3 com 2 e os outros com 144
    assert ctrl_real.comparacao_justa(f)
    # A exportação usa o mesmo recorte: mesmas linhas para todos.
    linhas = ctrl_real.exportar_csv(f).decode("utf-8").strip().splitlines()[1:]
    contagem = pd.Series([linha.split(";")[0] for linha in linhas]).value_counts()
    assert contagem.nunique() == 1 and len(contagem) == 5


def test_dados_reais_so_com_as_datas_avisa_comparacao_injusta(ctrl_real):
    # Usar só as datas do período em comum (o comportamento antigo) inclui horas a mais: o sistema avisa.
    f = FiltrosTermometros(tuple(ctrl_real.ids), date(2025, 2, 17), date(2025, 6, 12))
    assert not ctrl_real.comparacao_justa(f)
    assert any("nem todos os termômetros mediram" in frase for frase in ctrl_real.interpretacoes(f, COL_TEMP))
