"""Filtros da barra lateral (View).

Como os filtros funcionam no Streamlit
--------------------------------------
Cada vez que o usuário mexe num filtro, o Streamlit roda o script INTEIRO de
novo, de cima para baixo. Os valores escolhidos ficam guardados em
``st.session_state`` (um dicionário que sobrevive entre as execuções), sob a
"key" de cada widget (ex.: ``key="estacao"``).

Este módulo:
1. confere se os valores guardados ainda fazem sentido (ex.: ao trocar de
   estação, a variável escolhida pode não existir na nova estação);
2. desenha os filtros com textos de ajuda;
3. devolve um objeto ``Filtros`` com tudo o que foi escolhido.
"""

from __future__ import annotations

import streamlit as st

from controllers.painel_controller import TIPOS_DADOS, Filtros, PainelController
from views.estilo import numero


def _ajustar_estado(ctrl: PainelController) -> None:
    """Corrige valores guardados que deixaram de ser válidos ANTES de desenhar os filtros.

    O Streamlit só permite alterar ``st.session_state[chave]`` antes de o widget
    com aquela chave ser criado na execução atual; por isso fazemos tudo aqui.
    """
    estado = st.session_state
    # Valores iniciais das opções avançadas, definidos aqui (e não no widget) para o
    # Streamlit não reclamar de "valor padrão definido em dois lugares".
    estado.setdefault("dados", "originais")
    estado.setdefault("agregacao", "D")
    estado.setdefault("excluir_outliers", False)
    if estado.get("fonte") not in ctrl.nomes_fontes:
        estado["fonte"] = ctrl.nomes_fontes[0]  # a primeira fonte é a de dados reais, quando existe
    fonte = estado["fonte"]

    estacoes = list(ctrl.estacoes(fonte)["estacao_id"])
    if estado.get("estacao") not in estacoes:
        estado["estacao"] = ctrl.estacao_padrao(fonte)
    estacao = estado["estacao"]

    # Se a fonte ou a estação mudou, reiniciamos período e variável.
    contexto_atual = (fonte, estacao)
    if estado.get("_contexto") != contexto_atual:
        estado["_contexto"] = contexto_atual
        estado["periodo"] = ctrl.periodo_disponivel(fonte, estacao)
        variaveis = ctrl.variaveis(fonte, estacao)
        if estado.get("variavel") not in variaveis:
            estado["variavel"] = ctrl.variavel_padrao(fonte, estacao)

    variaveis = ctrl.variaveis(fonte, estacao)
    if estado.get("variavel") not in variaveis:
        estado["variavel"] = ctrl.variavel_padrao(fonte, estacao)
    # A variável principal não pode estar também na lista de comparação.
    estado["comparar"] = [c for c in estado.get("comparar", []) if c in variaveis and c != estado["variavel"]]


def _restaurar_periodo(ctrl: PainelController) -> None:
    """Função chamada pelo botão "Período completo" (um "callback")."""
    st.session_state["periodo"] = ctrl.periodo_disponivel(st.session_state["fonte"], st.session_state["estacao"])


def renderizar(ctrl: PainelController) -> Filtros:
    """Desenha a barra lateral e devolve os filtros escolhidos."""
    _ajustar_estado(ctrl)

    with st.sidebar:  # tudo dentro deste bloco aparece na barra lateral
        st.markdown("#### Filtros da qualidade do ar")
        st.caption("Escolha a estação, o período e o indicador. Valem só para as telas de qualidade do ar.")

        fonte = st.selectbox(
            "1. Fonte de dados", ctrl.nomes_fontes, key="fonte",
            help=(
                "“Dados reais” são medições oficiais da CETESB publicadas no MonitorAr (Ministério do Meio Ambiente). "
                "“Demonstração” é o conjunto fictício da primeira versão, só para praticar."
            ),
        )
        tabela_estacoes = ctrl.estacoes(fonte).set_index("estacao_id")

        def nome_estacao(estacao_id: str) -> str:
            linha = tabela_estacoes.loc[estacao_id]
            dist = linha["distancia_km"]
            return linha["estacao"] if dist is None or dist != dist else f"{linha['estacao']} — {numero(dist)} km"

        estacao = st.selectbox(
            "2. Estação", list(tabela_estacoes.index), format_func=nome_estacao, key="estacao",
            help=(
                "Não há estação oficial dentro de Heliópolis. A lista mostra as estações mais próximas, com a "
                "distância aproximada em linha reta até o bairro. Os dados de cada estação nunca são misturados."
            ),
        )

        minimo, maximo = ctrl.periodo_disponivel(fonte, estacao)
        periodo = st.date_input(
            "3. Período", min_value=minimo, max_value=maximo, format="DD/MM/YYYY", key="periodo",
            help="Clique na data inicial e depois na final. As análises usam só os dias escolhidos.",
        )
        st.button("Período completo", on_click=_restaurar_periodo, args=(ctrl,), key="btn_periodo", icon=":material/restart_alt:")

        variaveis = ctrl.variaveis(fonte, estacao)
        variavel = st.selectbox(
            "4. Indicador principal", variaveis, format_func=lambda c: ctrl.rotulo(fonte, c), key="variavel",
            help="Indicador usado nos gráficos de evolução, padrões e distribuição.",
        )
        comparar = st.multiselect(
            "Comparar com (opcional)", [c for c in variaveis if c != variavel],
            format_func=lambda c: ctrl.rotulo(fonte, c), key="comparar", placeholder="Escolha indicadores",
            help="Mostra outros indicadores da mesma estação em painéis alinhados, na seção “Comparar indicadores e estações”.",
        )

        with st.expander("Opções avançadas", expanded=False):
            dados = st.radio(
                "Versão dos dados", list(TIPOS_DADOS), format_func=TIPOS_DADOS.get, key="dados",
                help=(
                    "Originais: exatamente como no arquivo, com as lacunas. Tratados: lacunas de até "
                    f"{ctrl.limite_lacuna} horas seguidas preenchidas por interpolação (estimativa em linha reta)."
                ),
            )
            opcoes = ctrl.opcoes_agregacao()
            agregacao = st.selectbox(
                "Agrupar as séries por", list(opcoes), format_func=opcoes.get, key="agregacao",
                help="Com muitos pontos, agrupar por dia, semana ou mês deixa a tendência mais fácil de ver.",
            )
            excluir = st.checkbox(
                "Ignorar outliers nas análises", key="excluir_outliers",
                help=(
                    "Valores muito diferentes dos demais (regra do IQR) deixam de entrar nos cálculos. "
                    "Fica desmarcado por padrão: um valor extremo pode ser um evento real."
                ),
            )

    # O seletor de período devolve uma tupla com 1 data enquanto o usuário
    # ainda não clicou na data final; nesse caso usamos início = fim.
    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
        inicio, fim = periodo
    else:
        inicio = fim = periodo[0] if isinstance(periodo, (tuple, list)) and periodo else periodo
        with st.sidebar:
            st.caption("Escolha também a data final do período.")

    if ctrl.avisos:
        with st.sidebar:
            for aviso in ctrl.avisos:
                st.caption(f"⚠ {aviso}")

    return Filtros(
        fonte=fonte, estacao=estacao, inicio=inicio, fim=fim, variavel=variavel,
        comparar=tuple(comparar), dados=dados, agregacao=agregacao, excluir_outliers=excluir,
    )
