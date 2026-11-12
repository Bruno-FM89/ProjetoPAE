"""Página "Visão Geral" — a página inicial do painel (View).

Objetivo (feedback da UNAS: "deixar o site mais fácil de usar")
---------------------------------------------------------------
Quem abre o painel pela primeira vez precisa entender em poucos segundos:

1. para que serve o painel;
2. quais informações existem (três conjuntos de dados) e onde estão;
3. como começar.

Por isso a página tem: uma frase de objetivo, três "cartões" (um por conjunto
de dados) com 2 ou 3 números principais e um botão que leva à seção, e um
"como usar em 3 passos". Os números são calculados na hora, a partir dos dados.
"""

from __future__ import annotations

import streamlit as st

from controllers.painel_controller import Filtros
from controllers.sistema import Sistema
from controllers.termometros_controller import FiltrosTermometros
from views import estilo
from views.estilo import data_br, inteiro, numero, percentual


#: Arquivos das páginas (usados nos botões "Abrir ..."). Precisam ser os mesmos do app.py.
PAGINAS = {
    "termometros": "app_pages/termometros.py",
    "qualidade_ar": "app_pages/qualidade_ar.py",
    "mapa": "app_pages/mapa.py",
    "ajuda": "app_pages/ajuda.py",
    "sobre": "app_pages/sobre_dados.py",
}


def renderizar(sistema: Sistema, paginas: dict[str, str] | None = None) -> None:
    """Desenha a página inicial.

    Parâmetros:
        sistema: os Controllers (qualquer um pode faltar).
        paginas: arquivos das páginas para os botões "Abrir ..." (padrão: ``PAGINAS``).
    """
    paginas = paginas or PAGINAS
    estilo.cabecalho(
        "Inteligência Climática para Heliópolis",
        "Um painel para a comunidade e a equipe da UNAS acompanharem o calor, a umidade e a qualidade do ar em "
        "Heliópolis e arredores — com explicações simples em cada tela.",
    )
    st.markdown("#### O que você encontra aqui")
    col1, col2, col3 = st.columns(3)
    with col1:
        _cartao_termometros(sistema, paginas["termometros"])
    with col2:
        _cartao_ar(sistema, paginas["qualidade_ar"])
    with col3:
        _cartao_mapa(sistema, paginas["mapa"])

    st.markdown("#### Como usar em 3 passos")
    with st.container(border=True):
        st.markdown(
            "1. **Escolha um assunto** nos cartões acima ou no menu à esquerda (no celular, toque em ☰ no canto de cima).\n"
            "2. **Use os filtros numerados** no topo de cada página (ou na barra lateral, na Qualidade do Ar) para escolher "
            "locais e datas. Passe o mouse sobre o ícone **?** ao lado de cada filtro para ver uma explicação.\n"
            "3. **Leia as explicações**: abaixo de cada gráfico há uma frase sobre o que ele mostra e a seção "
            "“Como interpretar este gráfico”. Para voltar a esta página, clique em **Visão Geral** no menu."
        )
    c1, c2 = st.columns(2)
    with c1:
        st.page_link(paginas["ajuda"], label="Primeira vez aqui? Veja o tutorial e o glossário", icon=":material/school:", width="stretch")
    with c2:
        st.page_link(paginas["sobre"], label="De onde vêm os dados e como foram tratados", icon=":material/database:", width="stretch")

    st.info(
        "Os três conjuntos de dados vêm de fontes diferentes e **nunca são misturados**. Os termômetros medem dentro de "
        "casas de Heliópolis; a qualidade do ar vem de estações oficiais a alguns quilômetros do bairro; os mapas vêm dos "
        "arquivos geográficos da UNAS.",
        icon=":material/info:",
    )
    if sistema.erros:
        for parte, erro in sistema.erros.items():
            st.warning(f"Parte do painel indisponível ({parte.replace('_', ' ')}): {erro}", icon=":material/warning:")


def _numeros(itens: list[tuple[str, str]]) -> None:
    """Lista curta de números do cartão: (valor, descrição)."""
    for valor, texto in itens:
        st.markdown(f"**{valor}** {texto}")


def _cartao_termometros(sistema: Sistema, pagina: str) -> None:
    """Cartão dos termômetros: número de aparelhos, período e faixa de temperatura."""
    with st.container(border=True, height="stretch"):
        st.markdown("##### :material/thermostat: Temperatura e umidade")
        st.caption("Medidas DENTRO de Heliópolis por termômetros da UNAS em residências.")
        ctrl = sistema.termometros
        if ctrl is None:
            st.caption("Dados indisponíveis no momento.")
        else:
            inicio, fim = ctrl.periodo(ctrl.ids)
            comum = ctrl.periodo_comum(ctrl.ids)
            itens = [(inteiro(len(ctrl.ids)), "termômetros"), (f"{data_br(inicio)} a {data_br(fim)}", "")]
            if comum:
                resumo = ctrl.resumo(FiltrosTermometros(tuple(ctrl.ids), comum[0], comum[1]))
                itens.append((f"{numero(resumo['temp_min'].min())} a {numero(resumo['temp_max'].max())} °C",
                              "do mais frio ao mais quente, quando todos mediram juntos"))
            _numeros(itens)
        st.page_link(pagina, label="Abrir temperatura e umidade", icon=":material/arrow_forward:", width="stretch")


def _cartao_ar(sistema: Sistema, pagina: str) -> None:
    """Cartão da qualidade do ar: estações, distância até o bairro e % de horas com qualidade Boa."""
    with st.container(border=True, height="stretch"):
        st.markdown("##### :material/air: Qualidade do ar")
        st.caption("Índice oficial (CETESB) de estações próximas — fora de Heliópolis.")
        ctrl = sistema.painel
        if ctrl is None:
            st.caption("Dados indisponíveis no momento.")
        else:
            fonte = ctrl.nomes_fontes[0]
            estacoes = ctrl.estacoes(fonte)
            distancias = estacoes["distancia_km"].dropna()
            itens = [(inteiro(len(estacoes)), "estações oficiais")]
            if not distancias.empty:
                itens.append((f"{numero(distancias.min())} a {numero(distancias.max())} km", "de distância do bairro"))
            estacao = ctrl.estacao_padrao(fonte)
            inicio, fim = ctrl.periodo_disponivel(fonte, estacao)
            f = Filtros(fonte=fonte, estacao=estacao, inicio=inicio, fim=fim, variavel=ctrl.variavel_padrao(fonte, estacao))
            dist = ctrl.distribuicao_faixas(f, f.variavel)
            if dist is not None:
                itens.append((percentual(dist.loc[0, "percentual"]),
                              f"das horas com qualidade Boa na estação mais próxima ({ctrl.nome_estacao(fonte, estacao)})"))
            _numeros(itens)
        st.page_link(pagina, label="Abrir qualidade do ar", icon=":material/arrow_forward:", width="stretch")


def _cartao_mapa(sistema: Sistema, pagina: str) -> None:
    """Cartão do mapa: quebradas, projetos da UNAS e área do recorte."""
    with st.container(border=True, height="stretch"):
        st.markdown("##### :material/map: Mapa de Heliópolis")
        st.caption("Quebradas, glebas e projetos da UNAS, a partir dos arquivos geográficos da UNAS.")
        mapa = sistema.mapa
        if mapa is None:
            st.caption("Mapa indisponível no momento.")
        else:
            area = mapa.area_recorte_km2()
            _numeros([
                (inteiro(len(mapa.quebradas())), "quebradas"),
                (inteiro(len(mapa.projetos())), "projetos e equipamentos da UNAS"),
                (f"{numero(area, 2)} km²" if area else "—", "de área no recorte de Heliópolis"),
            ])
        st.page_link(pagina, label="Abrir mapa", icon=":material/arrow_forward:", width="stretch")
