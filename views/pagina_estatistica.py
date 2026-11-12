"""Página "Análise Estatística" (View).

Junta, numa página só, as análises estatísticas mais detalhadas dos DOIS
conjuntos de medições (eles nunca são misturados):

* Termômetros da comunidade — estatística descritiva, distribuição, boxplot e
  a relação entre temperatura e umidade;
* Qualidade do ar — seção da V2 (``views/ar_estatistica.py``).

Um seletor no topo escolhe o conjunto. Os filtros da barra lateral só
aparecem quando "Qualidade do ar" está escolhido (``app.py`` decide isso).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from controllers.painel_controller import Filtros
from controllers.sistema import Sistema
from controllers.termometros_controller import COL_TEMP, COL_UMID
from views import ar_estatistica, estilo, filtros_termometros
from views import graficos_comunidade as gc
from views.estilo import CONFIG_PLOTLY, inteiro, numero

CONJUNTOS = {"termometros": "Temperatura e umidade (termômetros)", "ar": "Qualidade do ar (estações CETESB)"}
FONTE_TERM = "Fonte: termômetros instalados pela UNAS em residências de Heliópolis (identificação anônima)."


def conjunto_escolhido() -> str:
    """Conjunto escolhido no seletor (lido também pelo app.py para decidir a barra lateral)."""
    return st.session_state.get("estat_conjunto") or "termometros"


def renderizar(sistema: Sistema, f: Filtros | None) -> None:
    """Desenha a página: seletor do conjunto de dados e as análises do conjunto escolhido.

    Parâmetros:
        sistema: os Controllers.
        f: filtros do ar da barra lateral (None quando a barra lateral não os mostra).
    """
    estilo.cabecalho(
        "Análise Estatística",
        "Para quem quer ir além dos gráficos: médias, medianas, como os valores se espalham e a relação entre "
        "medidas. Cada termo é explicado em linguagem simples.",
    )
    conjunto = st.segmented_control(
        "Quais medições analisar?", list(CONJUNTOS), format_func=CONJUNTOS.get, default="termometros",
        key="estat_conjunto", persist_state="session",
        help="Os dois conjuntos vêm de fontes e lugares diferentes, por isso são analisados separadamente.",
    ) or "termometros"

    if conjunto == "ar":
        if sistema.painel is None or f is None:
            st.error("Dados de qualidade do ar indisponíveis. " + sistema.erros.get("qualidade_ar", ""), icon=":material/error:")
            return
        st.caption("Use os filtros da barra lateral (à esquerda) para escolher estação, período e indicador.")
        estilo.faixa_contexto(sistema.painel.contexto(f))
        ar_estatistica.renderizar(sistema.painel, f, embutido=True)
        return

    ctrl = sistema.termometros
    if ctrl is None:
        st.error("Dados dos termômetros indisponíveis. " + sistema.erros.get("termometros", ""), icon=":material/error:")
        return
    ft = filtros_termometros.renderizar(ctrl, "est", agrupamento=False)
    if ft is None:
        return
    if ctrl.sem_dados(ft):
        estilo.sem_dados("Nenhuma medição dos termômetros escolhidos neste período.")
        return
    coluna = st.segmented_control(
        "3. Medida", [COL_TEMP, COL_UMID], format_func=lambda c: ctrl.grandezas()[c]["nome"], default=COL_TEMP,
        key="est_grandeza", persist_state="session",
    ) or COL_TEMP
    g = ctrl.grandezas()[coluna]
    un = g["unidade"]
    cores = gc.cores_termometros([ctrl.nome(t) for t in ctrl.ids])
    nomes = ctrl.nomes()

    aba_resumo, aba_dist, aba_caixa, aba_relacao = st.tabs(
        ["Resumo estatístico", "Distribuição dos valores", "Caixa (boxplot)", "Relação entre temperatura e umidade"]
    )
    with aba_resumo:
        desc = ctrl.descritiva(ft, coluna)
        st.dataframe(pd.DataFrame({
            "Termômetro": desc.index,
            "Leituras": [inteiro(v) for v in desc["n"]],
            f"Média ({un})": [numero(v, 2) for v in desc["media"]],
            f"Mediana ({un})": [numero(v, 2) for v in desc["mediana"]],
            f"Desvio padrão ({un})": [numero(v, 2) for v in desc["desvio_padrao"]],
            f"1º quartil ({un})": [numero(v, 1) for v in desc["q1"]],
            f"3º quartil ({un})": [numero(v, 1) for v in desc["q3"]],
            f"Mínimo ({un})": [numero(v, 1) for v in desc["minimo"]],
            f"Máximo ({un})": [numero(v, 1) for v in desc["maximo"]],
        }), hide_index=True, width="stretch")
        with st.expander("O que significa cada coluna?", icon=":material/help:"):
            st.markdown(
                "- **Média:** soma de todas as leituras ÷ quantidade de leituras.\n"
                "- **Mediana:** o valor do meio quando as leituras são colocadas em ordem: metade fica abaixo, metade acima. "
                "Quando média e mediana são parecidas, não há valores extremos “puxando” a média.\n"
                "- **Desvio padrão:** o quanto as leituras costumam se afastar da média. Pequeno = valores parecidos o tempo "
                "todo; grande = valores que mudam bastante.\n"
                "- **1º e 3º quartil:** 25% das leituras ficam abaixo do 1º quartil e 75% abaixo do 3º. Entre os dois "
                "estão as 50% leituras “do meio”.\n"
                "- **Mínimo e máximo:** o menor e o maior valor medido."
            )
    medicoes = ctrl.medicoes(ft)
    with aba_dist:
        st.plotly_chart(
            gc.histogramas(medicoes, coluna, nomes, cores, un, f"Distribuição das leituras de {g['nome'].lower()}"),
            width="stretch", config=CONFIG_PLOTLY,
        )
        estilo.explicar_grafico(
            "Mostra quais valores aparecem com mais frequência em cada termômetro.",
            "Cada barra representa uma faixa de valores (por exemplo, de 22 a 23 °C) e sua altura é a porcentagem das "
            "leituras naquela faixa. Um “morro” mais à direita indica um local mais quente (ou mais úmido). Um morro "
            "largo indica valores que variam muito; estreito, valores parecidos. Clique na legenda para esconder termômetros.",
            FONTE_TERM,
        )
    with aba_caixa:
        st.plotly_chart(gc.caixas(medicoes, coluna, nomes, cores, un, f"{g['nome']}: resumo em caixa por termômetro"),
                        width="stretch", config=CONFIG_PLOTLY)
        estilo.explicar_grafico(
            "Resumo visual de onde ficam a maioria das leituras de cada termômetro.",
            "A caixa vai do 1º ao 3º quartil (a metade “do meio” das leituras) e o traço dentro dela é a mediana. As "
            "linhas que saem da caixa vão até os valores mais distantes considerados normais. Caixas mais altas no "
            "gráfico = locais mais quentes (ou úmidos); caixas mais compridas = mais variação.",
            FONTE_TERM,
        )
    with aba_relacao:
        st.markdown("##### Relação entre temperatura e umidade")
        st.caption(
            "Será que, quando a casa esquenta, o ar fica mais seco? Este gráfico responde para cada termômetro."
        )
        escolhido = st.selectbox("Termômetro", list(ft.ids), format_func=ctrl.nome, key="est_rel_termometro")
        relacao = ctrl.relacao_temp_umid(ft, escolhido)
        st.plotly_chart(gc.dispersao_temp_umid(ctrl.dados_dispersao(ft, escolhido), ctrl.nome(escolhido), cores[ctrl.nome(escolhido)]),
                        width="stretch", config=CONFIG_PLOTLY)
        if relacao["r"] is not None:
            estilo.leitura(
                f"<strong>Resultado:</strong> relação {relacao['classificacao']} (correlação = {numero(relacao['r'], 2)}, "
                f"com {inteiro(relacao['n'])} leituras). {relacao['frase']}"
            )
        estilo.explicar_grafico(
            "Cada ponto é uma hora: a posição na horizontal é a temperatura e na vertical, a umidade.",
            "Se os pontos descem da esquerda para a direita, quanto mais quente, mais seco o ar (relação negativa). "
            "A **correlação** resume isso num número de −1 a +1: perto de −1, relação negativa forte; perto de 0, "
            "nenhuma relação clara; perto de +1, os dois sobem juntos. Ela foi calculada com todas as leituras de 10 "
            "minutos (coeficiente de Pearson). **Relação não prova causa**: mostra só que as duas medidas variam juntas.",
            FONTE_TERM,
        )
        tabela = pd.DataFrame([{"Termômetro": ctrl.nome(t), **ctrl.relacao_temp_umid(ft, t)} for t in ft.ids])
        st.dataframe(pd.DataFrame({
            "Termômetro": tabela["Termômetro"],
            "Correlação (−1 a +1)": [numero(v, 2) for v in tabela["r"]],
            "Relação": tabela["classificacao"],
            "Leituras usadas": [inteiro(v) for v in tabela["n"]],
        }), hide_index=True, width="stretch")
