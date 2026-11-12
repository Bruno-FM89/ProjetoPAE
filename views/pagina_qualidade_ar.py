"""Página "Qualidade do Ar" (View).

Na V2 eram três itens de menu (Visão geral, Análise temporal, Comparação). A
UNAS pediu uma navegação mais simples, então na V4 eles viraram SEÇÕES de uma
única página, escolhidas por um seletor. Só a seção escolhida é desenhada.

Os filtros (fonte, estação, período, indicador) continuam na barra lateral,
porque valem para todas as seções desta página.
"""

from __future__ import annotations

import streamlit as st

from controllers.painel_controller import Filtros
from controllers.sistema import Sistema
from views import ar_comparacao, ar_resumo, ar_tempo, estilo

SECOES = {
    "resumo": ":material/dashboard: Resumo do período",
    "tempo": ":material/show_chart: Ao longo do tempo",
    "comparar": ":material/compare_arrows: Comparar indicadores e estações",
}
MODULOS = {"resumo": ar_resumo, "tempo": ar_tempo, "comparar": ar_comparacao}


def renderizar(sistema: Sistema, f: Filtros | None) -> None:
    """Desenha a página: título, de onde vêm os dados, aviso de que não é medição no bairro e a seção escolhida."""
    estilo.cabecalho(
        "Qualidade do Ar perto de Heliópolis",
        "Índice de qualidade do ar medido pelas estações oficiais da CETESB mais próximas da comunidade. "
        "Escolha a estação, o período e o indicador na barra lateral, à esquerda.",
    )
    if sistema.painel is None or f is None:
        st.error("Dados de qualidade do ar indisponíveis. " + sistema.erros.get("qualidade_ar", ""), icon=":material/error:")
        return
    ctrl = sistema.painel
    estilo.faixa_contexto(ctrl.contexto(f))
    with st.expander("Importante: estes dados NÃO foram medidos dentro de Heliópolis", icon=":material/location_off:"):
        st.markdown(
            "Não existe estação oficial de qualidade do ar dentro de Heliópolis. Os valores vêm de estações da CETESB a "
            "alguns quilômetros do bairro (a distância aparece na barra lateral, ao lado do nome de cada estação). "
            "Eles ajudam a entender a qualidade do ar da região, mas o ar dentro da comunidade pode ser diferente. "
            "As medições feitas DENTRO de Heliópolis são as dos termômetros da UNAS (temperatura e umidade)."
        )
    secao = st.segmented_control(
        "O que você quer ver?", list(SECOES), format_func=SECOES.get, default="resumo",
        key="ar_secao", persist_state="session",
    ) or "resumo"
    MODULOS[secao].renderizar(ctrl, f, embutido=True)
