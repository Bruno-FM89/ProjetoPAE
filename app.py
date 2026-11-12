"""Ponto de entrada do painel (camada View): ``streamlit run app.py``.

O que acontece quando o app abre
--------------------------------
1. ``st.set_page_config`` define o título da aba do navegador e o layout largo.
2. ``obter_sistema`` (em ``views/sessao.py``) carrega os TRÊS conjuntos de
   dados — qualidade do ar, termômetros e mapas — criando um Controller para
   cada um. ``@st.cache_resource`` faz isso UMA vez só: nas próximas
   interações, os mesmos objetos são reaproveitados (os arquivos não são relidos).
3. ``st.navigation`` cria o menu com as 7 páginas (uma por arquivo em ``app_pages/``).
4. Os filtros da qualidade do ar só aparecem na barra lateral nas páginas (ou
   partes de página) que os usam — pedido da UNAS para simplificar a navegação.
5. A página escolhida é executada.

Arquitetura MVC em uma frase: a View (este arquivo, ``app_pages/`` e ``views/``)
mostra a tela; o Controller (``controllers/``) organiza o pedido; o Model
(``models/``) lê os dados e faz as contas. Este arquivo não contém regra de negócio.
"""

from __future__ import annotations

import streamlit as st  # biblioteca que transforma o script Python numa página web

from views import barra_lateral, estilo, pagina_estatistica, pagina_sobre_dados
from views.sessao import guardar_filtros_ar, obter_sistema

# Precisa ser o primeiro comando do Streamlit na página.
st.set_page_config(
    page_title="Inteligência Climática · Heliópolis",
    page_icon=":material/thermostat:",
    layout="wide",
    initial_sidebar_state="auto",  # aberta no computador, recolhida no celular
)

#: Chaves dos filtros da qualidade do ar (barra lateral).
CHAVES_FILTROS_AR = ["fonte", "estacao", "periodo", "variavel", "comparar", "dados", "agregacao", "excluir_outliers", "_contexto"]

#: Menu: (arquivo, título, ícone, endereço na barra do navegador, explicação curta).
PAGINAS = [
    ("app_pages/inicio.py", "Visão Geral", ":material/home:", "visao-geral",
     "Página inicial: resumo dos dados e por onde começar."),
    ("app_pages/termometros.py", "Temperatura e Umidade", ":material/thermostat:", "temperatura-e-umidade",
     "Medições dos termômetros da UNAS em casas de Heliópolis."),
    ("app_pages/qualidade_ar.py", "Qualidade do Ar", ":material/air:", "qualidade-do-ar",
     "Índice de qualidade do ar das estações oficiais mais próximas (fora do bairro)."),
    ("app_pages/mapa.py", "Mapa de Heliópolis", ":material/map:", "mapa",
     "Quebradas, glebas, projetos da UNAS e estações de qualidade do ar."),
    ("app_pages/estatistica.py", "Análise Estatística", ":material/bar_chart:", "analise-estatistica",
     "Médias, medianas, distribuição e relações, explicadas em linguagem simples."),
    ("app_pages/sobre_dados.py", "Sobre os Dados", ":material/database:", "sobre-os-dados",
     "Origem, tratamento, conferências, privacidade e limitações de cada conjunto de dados."),
    ("app_pages/ajuda.py", "Ajuda e Tutorial", ":material/help:", "ajuda",
     "Passo a passo, glossário e perguntas frequentes."),
]


def _manter_filtros_ar() -> None:
    """Faz o Streamlit lembrar os filtros do ar mesmo nas páginas em que eles não aparecem.

    Por padrão, o Streamlit apaga o valor de um filtro quando ele não é
    desenhado. Regravar o valor em ``st.session_state`` a cada execução o
    transforma num valor "do usuário", que não é apagado.
    """
    for chave in CHAVES_FILTROS_AR:
        if chave in st.session_state:
            st.session_state[chave] = st.session_state[chave]


def _precisa_filtros_ar(url_path: str) -> bool:
    """Diz se a página atual usa os filtros da qualidade do ar."""
    if url_path == "qualidade-do-ar":
        return True
    if url_path == "analise-estatistica":
        return pagina_estatistica.conjunto_escolhido() == "ar"
    if url_path == "sobre-os-dados":
        return pagina_sobre_dados.assunto_escolhido() == "ar"
    return False


def main() -> None:
    """Monta a tela: estilo, menu, filtros do ar (só quando a página usa) e executa a página escolhida."""
    estilo.aplicar_estilo()
    sistema = obter_sistema()
    _manter_filtros_ar()

    paginas = [
        st.Page(arquivo, title=titulo, icon=icone, url_path=caminho, help=ajuda, default=(i == 0))
        for i, (arquivo, titulo, icone, caminho, ajuda) in enumerate(PAGINAS)
    ]
    navegacao = st.navigation(paginas)  # desenha o menu no topo da barra lateral

    with st.sidebar:
        st.markdown(
            '<div class="marca">Inteligência Climática</div><div class="marca-sub">Heliópolis · UNAS</div>',
            unsafe_allow_html=True,
        )
    filtros = None
    if sistema.painel is not None and _precisa_filtros_ar(navegacao.url_path):
        filtros = barra_lateral.renderizar(sistema.painel)  # filtros do ar abaixo do menu
    else:
        with st.sidebar:
            st.caption("Os filtros de cada assunto ficam no topo da própria página.")
    with st.sidebar:
        st.caption("Dúvidas? Abra **Ajuda e Tutorial** no menu acima.")
    guardar_filtros_ar(filtros)
    navegacao.run()  # executa a página escolhida


main()
