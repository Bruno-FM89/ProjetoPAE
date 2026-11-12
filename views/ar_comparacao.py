"""Seção "Comparar" da página Qualidade do Ar (View).

Antes era a página "Comparação de indicadores" da V2.

Abas:
* Indicadores da estação — painéis alinhados no tempo e gráfico de dispersão;
* Entre estações — o mesmo indicador em várias estações próximas, lado a lado.

Regra: estações diferentes nunca são somadas nem misturadas numa média; cada
uma aparece como uma linha separada.

Comandos do Streamlit usados nas páginas (resumo para iniciantes)
-----------------------------------------------------------------
* ``st.tabs([...])`` cria abas; o conteúdo de cada aba fica dentro de ``with aba:``.
* ``st.columns(n)`` divide a largura em colunas lado a lado.
* ``st.plotly_chart(fig, width="stretch")`` mostra um gráfico Plotly ocupando a largura disponível.
* ``st.dataframe(tabela, hide_index=True)`` mostra uma tabela rolável (sem a coluna de índice).
* ``st.selectbox`` / ``st.multiselect`` / ``st.radio`` / ``st.checkbox`` / ``st.slider`` são
  controles; o valor escolhido é devolvido pela função. O parâmetro ``key`` dá um nome
  único ao controle, para o Streamlit lembrar a escolha entre uma interação e outra.
* ``st.expander("título")`` cria uma seção que abre e fecha com um clique.
* ``st.info`` / ``st.warning`` mostram caixas de mensagem coloridas.
* ``return`` no meio da função encerra a página mais cedo (por exemplo, quando não há dados).
"""

from __future__ import annotations

import streamlit as st

from controllers.painel_controller import Filtros, PainelController
from views import estilo, graficos
from views.estilo import CONFIG_PLOTLY, CORES_SERIES, DESCRICAO_AGREGACAO, inteiro, numero


def renderizar(ctrl: PainelController, f: Filtros, embutido: bool = False) -> None:
    """Desenha a seção Comparar: indicadores da mesma estação lado a lado e o mesmo indicador em várias estações."""
    # Parâmetros: ctrl = Controller (fornece dados e cálculos); f = filtros escolhidos na barra lateral;
    # embutido = True quando a seção é mostrada dentro de outra página (que já tem título e faixa de contexto).
    # Retorno: nada. A função apenas desenha a página na tela.
    if not embutido:
        estilo.cabecalho(
            "Comparação de indicadores",
            "Compare indicadores da mesma estação ao longo do tempo, ou o mesmo indicador em estações diferentes.",
        )
    ctx = ctrl.contexto(f)
    if not embutido:
        estilo.faixa_contexto(ctx)
    if ctrl.sem_dados(f):
        estilo.sem_dados()
        return
    catalogo = ctrl.catalogo(f.fonte)
    fonte_txt = estilo.texto_fonte(ctx)
    aba_indicadores, aba_estacoes = st.tabs(["Indicadores da estação", "Entre estações"])

    with aba_indicadores:
        if not f.comparar:
            st.info(
                "Escolha um ou mais indicadores em “Comparar com”, na barra lateral, para vê-los em painéis "
                "alinhados com o indicador principal.", icon=":material/info:",
            )
        variaveis = [catalogo[c] for c in f.variaveis_selecionadas]
        serie = ctrl.serie_temporal(f, f.variaveis_selecionadas)
        st.plotly_chart(
            graficos.paineis(serie, variaveis, f"Indicadores lado a lado — {DESCRICAO_AGREGACAO[f.agregacao]}",
                             faixas=ctrl.faixas_iqar()),
            width="stretch", config=CONFIG_PLOTLY,
        )
        estilo.explicar_grafico(
            "Um painel por indicador, todos com o mesmo eixo de tempo.",
            "Cada painel tem sua própria escala vertical, porque os indicadores podem ter unidades diferentes. "
            "Compare os MOMENTOS de alta e de baixa, não a altura das linhas entre painéis. Quando duas linhas sobem e "
            "descem juntas, elas podem estar relacionadas, mas isso não prova que uma causa a outra.",
            fonte_txt,
        )
        if ctrl.um_poluente_por_hora(f.fonte):
            st.caption(
                "Nos dados do MonitorAr, cada hora traz o índice de um único poluente; por isso as séries de "
                "poluentes diferentes quase não coincidem no tempo."
            )

        st.markdown("##### Relação entre dois indicadores")
        st.caption("Veja se dois indicadores costumam subir e descer juntos. Cada ponto do gráfico é uma hora.")
        colunas = ctrl.colunas(f)
        outras = [c for c in colunas if c != f.variavel]
        if not outras:
            st.info("A estação tem só um indicador; não há com o que comparar.")
        else:
            padrao = next((c for c in f.comparar if c in outras), outras[0])
            y = st.selectbox("Comparar o indicador principal com", outras, index=outras.index(padrao),
                             format_func=lambda c: ctrl.rotulo(f.fonte, c), key="dispersao_y")
            r, pares = ctrl.correlacao_entre(f, f.variavel, y)
            motivo = ctrl.motivo_sem_correlacao(f.fonte, f.variavel, y)
            if motivo:
                st.info(motivo, icon=":material/info:")
            elif pares < 30:
                st.warning(
                    f"Só {inteiro(pares)} hora(s) têm valor nos dois indicadores ao mesmo tempo. Com tão poucos pares não é "
                    "possível calcular uma correlação confiável.", icon=":material/info:",
                )
            else:
                st.plotly_chart(graficos.dispersao(ctrl.dados_filtrados(f), catalogo[f.variavel], catalogo[y]), width="stretch", config=CONFIG_PLOTLY)
                rho, _ = ctrl.correlacao_entre(f, f.variavel, y, "spearman")
                estilo.explicar_grafico(
                    f"Cada ponto é uma hora com valor nos dois indicadores ({inteiro(pares)} horas).",
                    f"Força da relação (correlação, de −1 a +1): **{numero(r, 2)}** — relação {ctrl.classificar_correlacao(r)}. "
                    "Perto de +1: sobem juntos; perto de −1: quando um sobe, o outro desce; perto de 0: sem relação clara. "
                    f"(Coeficiente de Pearson; o de Spearman, que é menos sensível a valores extremos, deu {numero(rho, 2)}.) "
                    "Se os pontos sobem da esquerda para a direita, a relação é positiva; se descem, negativa. "
                    "**Correlação não é causa:** ela não indica que um indicador provoca o outro.",
                    fonte_txt,
                )

    with aba_estacoes:
        estacoes = ctrl.estacoes(f.fonte)
        # Só entram estações que medem o mesmo indicador (mesma chave = mesma grandeza e unidade).
        com_variavel = estacoes[[f.variavel in vs for vs in estacoes["variaveis"]]]
        if len(com_variavel) < 2:
            st.info("Esta fonte tem só uma estação com este indicador; a comparação entre estações não está disponível.")
            return
        nomes = dict(zip(com_variavel["estacao_id"], com_variavel["estacao"]))
        escolhidas = st.multiselect(
            "Estações", list(nomes), default=list(nomes)[:3], format_func=lambda e: nomes[e], key="estacoes_comparadas",
            help=(
                "Estações da mesma fonte que medem o indicador principal, da mais próxima à mais distante. "
                "Começamos com as 3 mais próximas para o gráfico não ficar carregado; acrescente outras se quiser."
            ),
        )
        if not escolhidas:
            st.info("Escolha pelo menos uma estação.")
            return
        tabela = ctrl.comparar_estacoes(f, f.variavel, escolhidas)
        # Cor fixa por estação, seguindo a ordem da lista completa (da mais próxima à mais distante).
        cores = {nome: CORES_SERIES[i % len(CORES_SERIES)] for i, nome in enumerate(estacoes["estacao"])}
        v = catalogo[f.variavel]
        st.plotly_chart(
            graficos.comparacao_estacoes(tabela, v, f"{v.rotulo} em estações próximas — {DESCRICAO_AGREGACAO[f.agregacao]}", cores, ctrl.faixas_iqar()),
            width="stretch", config=CONFIG_PLOTLY,
        )
        estilo.explicar_grafico(
            "O mesmo indicador em várias estações próximas a Heliópolis, no mesmo período.",
            "Cada linha é uma estação diferente. Nenhuma delas fica dentro de Heliópolis, e os valores não foram "
            "misturados nem combinados numa média. Diferenças entre as linhas podem refletir o entorno de cada "
            "estação (trânsito, áreas verdes etc.), mas o gráfico não permite afirmar a causa.",
            f"Fonte: {ctx['fonte']} · estações próximas, fora de Heliópolis.",
        )
        resumo = tabela.drop(columns="Data").agg(["mean", "median", "count"]).T
        distancias = dict(zip(estacoes["estacao"], estacoes["distancia_km"]))
        st.dataframe(
            {
                "Estação": resumo.index,
                "Distância de Heliópolis (km)": [numero(distancias.get(n), 1) for n in resumo.index],
                f"Média das {DESCRICAO_AGREGACAO[f.agregacao]}": [numero(x) for x in resumo["mean"]],
                "Mediana": [numero(x) for x in resumo["median"]],
                "Pontos no gráfico": [inteiro(x) for x in resumo["count"]],
            },
            hide_index=True, width="stretch",
        )
