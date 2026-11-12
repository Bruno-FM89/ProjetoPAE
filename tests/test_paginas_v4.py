"""Testes de interface da V4: navegação pelas 7 páginas e seções novas (sem navegador).

Usam o ``AppTest`` do Streamlit: o app roda em memória, os testes "clicam" nos
controles e conferem o que apareceu na tela.
"""

import pytest
from streamlit.testing.v1 import AppTest

from tests.conftest import RAIZ

ARQUIVOS = ["inicio", "termometros", "qualidade_ar", "mapa", "estatistica", "sobre_dados", "ajuda"]
TITULOS = {
    "inicio": "Inteligência Climática para Heliópolis",
    "termometros": "Temperatura e Umidade em Heliópolis",
    "qualidade_ar": "Qualidade do Ar perto de Heliópolis",
    "mapa": "Mapa de Heliópolis",
    "estatistica": "Análise Estatística",
    "sobre_dados": "Sobre os Dados",
    "ajuda": "Ajuda e Tutorial",
}


@pytest.fixture(scope="module")
def app():
    return AppTest.from_file(str(RAIZ / "app.py"), default_timeout=180).run()


def _ir(app, arquivo):
    return app.switch_page(f"app_pages/{arquivo}.py").run()


def _sem_erros(at):
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


@pytest.mark.parametrize("arquivo", ARQUIVOS)
def test_cada_pagina_abre_com_titulo(app, arquivo):
    at = _ir(app, arquivo)
    _sem_erros(at)
    assert at.title[0].value == TITULOS[arquivo]


def test_inicio_tem_cartoes_e_links(app):
    at = _ir(app, "inicio")
    links = [p.label for p in at.page_link]
    assert "Abrir temperatura e umidade" in links and "Abrir qualidade do ar" in links and "Abrir mapa" in links


def test_filtros_do_ar_so_aparecem_onde_sao_usados(app):
    assert len(_ir(app, "termometros").sidebar.selectbox) == 0
    assert len(_ir(app, "mapa").sidebar.selectbox) == 0
    assert _ir(app, "qualidade_ar").sidebar.selectbox(key="estacao") is not None


def test_filtro_do_ar_e_lembrado_ao_trocar_de_pagina(app):
    at = _ir(app, "qualidade_ar")
    at.sidebar.selectbox(key="estacao").set_value("134").run()
    _ir(at, "mapa")
    assert _ir(at, "qualidade_ar").sidebar.selectbox(key="estacao").value == "134"


@pytest.mark.parametrize("secao", ["comparar", "tempo", "dia", "mes", "tabela"])
@pytest.mark.parametrize("grandeza", ["temperatura_c", "umidade_pct"])
def test_secoes_dos_termometros(app, secao, grandeza):
    at = _ir(app, "termometros")
    at.segmented_control(key="term_grandeza").set_value(grandeza).run()
    at.segmented_control(key="term_secao").set_value(secao).run()
    _sem_erros(at)


def test_termometros_sem_selecao_pede_escolha(app):
    at = _ir(app, "termometros")
    at.pills(key="term_ids").set_value([]).run()
    _sem_erros(at)
    assert any("Escolha pelo menos um termômetro" in w.value for w in at.warning)
    at.pills(key="term_ids").set_value(["T1", "T2", "T3", "T4", "T5"]).run()


def test_termometros_explicam_origem_e_privacidade(app):
    at = _ir(app, "termometros")
    texto = " ".join(m.value for m in at.markdown)
    assert "DENTRO de Heliópolis" in texto and "sem nomes" in texto


def test_mapa_camadas_e_destaque(app):
    at = _ir(app, "mapa")
    at.pills(key="mapa_camadas").set_value(["glebas", "projetos", "estacoes"]).run()
    at.selectbox(key="mapa_destaque").set_value("Lagoa").run()
    _sem_erros(at)
    assert any("Quebrada Lagoa" in h.value for h in at.markdown)


@pytest.mark.parametrize("secao", ["resumo", "tempo", "comparar"])
def test_secoes_da_qualidade_do_ar(app, secao):
    at = _ir(app, "qualidade_ar")
    at.segmented_control(key="ar_secao").set_value(secao).run()
    _sem_erros(at)


@pytest.mark.parametrize("conjunto", ["termometros", "ar"])
def test_estatistica_dos_dois_conjuntos(app, conjunto):
    at = _ir(app, "estatistica")
    at.segmented_control(key="estat_conjunto").set_value(conjunto).run()
    _sem_erros(at)
    assert (len(at.sidebar.selectbox) > 0) == (conjunto == "ar")  # filtros do ar só quando o ar é escolhido


@pytest.mark.parametrize("assunto", ["termometros", "mapas", "ar", "privacidade"])
def test_sobre_os_dados(app, assunto):
    at = _ir(app, "sobre_dados")
    at.segmented_control(key="sobre_assunto").set_value(assunto).run()
    _sem_erros(at)


def test_sobre_mostra_conferencia_com_aparelho(app):
    at = _ir(app, "sobre_dados")
    at.segmented_control(key="sobre_assunto").set_value("termometros").run()
    assert any("30 de 30 valores conferem" in s.value for s in at.success)
