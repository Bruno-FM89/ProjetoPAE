"""Filtros dos termômetros, desenhados DENTRO da página (View).

Por que os filtros ficam na página e não na barra lateral
--------------------------------------------------------
Pedido da UNAS: navegação mais simples. A barra lateral fica só com o menu
(e, nas páginas de qualidade do ar, os filtros do ar). Os filtros dos
termômetros aparecem no topo da própria página, numerados (1, 2, 3...),
na ordem em que a pessoa deve escolher. No celular, onde a barra lateral fica
escondida, isso também evita que os filtros "sumam".

``persist_state="session"`` faz o Streamlit lembrar a escolha quando o
usuário troca de página e volta.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from controllers.termometros_controller import FiltrosTermometros, TermometrosController
from views.estilo import data_br

#: Opções de período (chave interna → texto do botão).
OPCOES_PERIODO = {
    "comum": "Quando todos mediram juntos",
    "todo": "Todo o período",
    "escolher": "Escolher datas",
}


def renderizar(ctrl: TermometrosController, prefixo: str, agrupamento: bool = True) -> FiltrosTermometros | None:
    """Desenha os filtros e devolve as escolhas (ou ``None`` se nenhum termômetro foi escolhido).

    Parâmetros:
        ctrl: Controller dos termômetros.
        prefixo: texto que diferencia as "keys" dos widgets entre páginas
            (cada página guarda suas próprias escolhas).
        agrupamento: se ``False``, não mostra a opção de agrupar por hora/dia/mês
            (a página de estatística sempre usa as leituras originais).
    """
    with st.container(border=True):
        st.markdown("**Escolha o que você quer ver**")
        ids = st.pills(
            "1. Termômetros", ctrl.ids, selection_mode="multi", default=ctrl.ids,
            format_func=ctrl.nome_com_regiao, key=f"{prefixo}_ids", persist_state="session",
            help="Clique num termômetro para incluir ou tirar da análise. Cada termômetro representa uma casa diferente.",
        )
        if not ids:
            st.warning("Escolha pelo menos um termômetro clicando nos botões acima.", icon=":material/touch_app:")
            return None
        colunas = st.columns([3, 2] if agrupamento else [1])
        with colunas[0]:
            modo = st.segmented_control(
                "2. Período", list(OPCOES_PERIODO), format_func=OPCOES_PERIODO.get, default="comum",
                key=f"{prefixo}_modo_periodo", persist_state="session",
                help=(
                    "Os termômetros não mediram todos nas mesmas datas. “Quando todos mediram juntos” usa só os dias em "
                    "que TODOS os escolhidos estavam funcionando — é a forma justa de comparar."
                ),
            ) or "comum"
            inicio, fim = _periodo(ctrl, ids, modo, prefixo)
        if agrupamento:
            with colunas[1]:
                opcoes = ctrl.agrupamentos()
                agrup = st.selectbox(
                    "3. Mostrar os valores", list(opcoes), index=list(opcoes).index("D"), format_func=opcoes.get,
                    key=f"{prefixo}_agrupamento", persist_state="session",
                    help=(
                        "O aparelho mede a cada 10 minutos (mais de 100 valores por dia). Mostrar a média de cada dia "
                        "deixa o gráfico mais fácil de ler; escolha “cada hora” para ver detalhes."
                    ),
                )
        else:
            agrup = "10min"
        st.caption(f"Período analisado: {data_br(inicio)} a {data_br(fim)}.")
    return FiltrosTermometros(tuple(ids), inicio, fim, agrup)


def _periodo(ctrl: TermometrosController, ids: list[str], modo: str, prefixo: str) -> tuple[date, date]:
    """Calcula o período conforme a opção escolhida (e mostra o seletor de datas, se for o caso)."""
    total = ctrl.periodo(ids)
    if modo == "comum":
        comum = ctrl.periodo_comum(ids)
        if comum is None:
            st.info(
                "Os termômetros escolhidos nunca mediram ao mesmo tempo. Mostrando todo o período de cada um.",
                icon=":material/info:",
            )
            return total
        return comum
    if modo == "todo":
        return total
    escolha = st.date_input(
        "Datas (clique no início e depois no fim)", value=total, min_value=total[0], max_value=total[1],
        format="DD/MM/YYYY", key=f"{prefixo}_datas",
    )
    if isinstance(escolha, (tuple, list)) and len(escolha) == 2:
        return escolha[0], escolha[1]
    st.caption("Escolha também a data final.")
    dia = escolha[0] if isinstance(escolha, (tuple, list)) and escolha else total[0]
    return dia, dia
