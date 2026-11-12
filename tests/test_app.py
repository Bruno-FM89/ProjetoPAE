"""Testes de interface: executam o app e cada página sem navegador (streamlit.testing).

``AppTest`` roda o script do Streamlit em memória e permite "clicar" nos
filtros e conferir o que apareceu na tela.
"""

from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from tests.conftest import RAIZ

# Seções da qualidade do ar (V2), que na V4 viraram partes das páginas Qualidade do Ar,
# Análise Estatística e Sobre os Dados. Todas recebem (ctrl, filtros).
PAGINAS = ["ar_resumo", "ar_tempo", "ar_comparacao", "ar_estatistica", "ar_sobre"]


def _pagina(nome_modulo, parametros):
    """Executa ``renderizar`` de uma página com filtros escolhidos (roda dentro do AppTest)."""
    import importlib
    import sys
    from datetime import date as d
    from pathlib import Path

    sys.path.insert(0, str(Path(parametros.pop("raiz"))))
    from controllers.painel_controller import Filtros, PainelController
    from services.config import Configuracao

    ctrl = PainelController.a_partir_da_configuracao(Configuracao.carregar({}))
    fonte = ctrl.nomes_fontes[parametros.pop("fonte_idx", 0)]
    estacao = parametros.pop("estacao", None) or ctrl.estacao_padrao(fonte)
    inicio, fim = ctrl.periodo_disponivel(fonte, estacao)
    inicio = d(*parametros.pop("inicio")) if "inicio" in parametros else inicio
    fim = d(*parametros.pop("fim")) if "fim" in parametros else fim
    variavel = parametros.pop("variavel", None) or ctrl.variavel_padrao(fonte, estacao)
    f = Filtros(fonte=fonte, estacao=estacao, inicio=inicio, fim=fim, variavel=variavel,
                comparar=tuple(parametros.pop("comparar", ())), **parametros)
    importlib.import_module(f"views.{nome_modulo}").renderizar(ctrl, f)


def _rodar(modulo, **parametros):
    parametros["raiz"] = str(RAIZ)
    return AppTest.from_function(_pagina, args=(modulo, parametros), default_timeout=120).run()


CENARIOS = {
    "real_padrao": {},
    "real_poluente_comparando": {"variavel": "O3_IQAr", "comparar": ("MP2.5_IQAr", "IQAR")},
    "real_horaria_tratada_sem_outliers": {"agregacao": "h", "dados": "tratados", "excluir_outliers": True},
    "real_outra_estacao_mensal": {"estacao": "126", "agregacao": "MS"},
    "real_periodo_curto": {"inicio": (2024, 5, 3), "fim": (2024, 5, 4)},
    "demo": {"fonte_idx": 1, "variavel": "MP2.5", "comparar": ("TEMP", "UR")},
}


@pytest.mark.parametrize("cenario", CENARIOS)
@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_renderiza_sem_excecao(pagina, cenario):
    at = _rodar(pagina, **CENARIOS[cenario])
    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("pagina", [p for p in PAGINAS if p != "ar_sobre"])
def test_periodo_sem_registros_mostra_aviso(pagina):
    at = _rodar(pagina, inicio=(2030, 1, 1), fim=(2030, 1, 31))
    assert not at.exception
    assert any("Nenhum valor" in w.value or "Não há valores" in w.value for w in at.warning)


def test_visao_geral_mostra_estacao_e_distancia():
    at = _rodar("ar_resumo")
    html = " ".join(m.value for m in at.markdown)
    assert "Estação Mooca (São Paulo)" in html and "6,7 km de Heliópolis" in html
    assert "fora de Heliópolis" in html


def test_visao_geral_demo_avisa_que_e_ficticio():
    at = _rodar("ar_resumo", fonte_idx=1, variavel="MP2.5")
    assert "Dados fictícios" in " ".join(m.value for m in at.markdown)


def test_correlacao_explica_por_que_nao_calcula_nos_dados_reais():
    at = _rodar("ar_estatistica")
    assert any("único poluente" in i.value for i in at.info)


# --- app completo: barra lateral e navegação -------------------------------------------
@pytest.fixture
def app():
    """App completo, já na página Qualidade do Ar (onde ficam os filtros da barra lateral)."""
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=120).run()
    return at.switch_page("app_pages/qualidade_ar.py").run()


def test_app_inicia_com_dados_reais(app):
    assert not app.exception and not app.error
    assert app.sidebar.selectbox(key="fonte").value.startswith("Dados reais")
    assert app.sidebar.selectbox(key="variavel").value == "IQAR"


def test_trocar_estacao_reinicia_periodo_e_mantem_variavel_valida(app):
    app.sidebar.date_input(key="periodo").set_value((date(2024, 3, 1), date(2024, 3, 31))).run()
    app.sidebar.selectbox(key="estacao").set_value("134").run()  # Diadema
    assert not app.exception
    assert app.sidebar.date_input(key="periodo").value == (date(2024, 1, 2), date(2025, 12, 31))
    assert app.sidebar.selectbox(key="variavel").value in ("IQAR", "MP10_IQAr", "O3_IQAr")


def test_trocar_para_demonstracao_ajusta_variaveis(app):
    app.sidebar.selectbox(key="fonte").set_value("Demonstração — dados fictícios").run()
    assert not app.exception
    assert app.sidebar.selectbox(key="variavel").value in ("MP2.5", "MP10", "O3", "NO2", "CO", "CO2", "TEMP", "UR")
    assert "Dados fictícios" in " ".join(m.value for m in app.markdown)


def test_mudar_periodo_atualiza_indicadores(app):
    app.sidebar.date_input(key="periodo").set_value((date(2024, 3, 1), date(2024, 3, 31))).run()
    html = " ".join(m.value for m in app.markdown)
    assert "744" in html and "01/03/2024" in html


def test_data_final_incompleta_nao_quebra(app):
    app.sidebar.date_input(key="periodo").set_value((date(2024, 3, 1),)).run()
    assert not app.exception


def test_opcoes_avancadas(app):
    app.sidebar.radio(key="dados").set_value("tratados").run()
    app.sidebar.checkbox(key="excluir_outliers").check().run()
    app.sidebar.selectbox(key="agregacao").set_value("W").run()
    assert not app.exception
