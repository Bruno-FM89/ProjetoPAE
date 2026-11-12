"""Seção "Qualidade do ar" da página Análise Estatística (View).

Abas:
* Resumo — tabela de estatística descritiva, interpretações e faixas de qualidade;
* Distribuição — histograma com média e mediana;
* Boxplot — geral, por mês ou por dia da semana;
* Outliers (IQR) — limites e quantidade de valores sinalizados;
* Correlações — matriz de correlação e ranking de pares.

Junta as páginas "Distribuições e outliers" e "Correlações" da V1.

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
from views import estilo, graficos, tabelas
from views.estilo import CONFIG_PLOTLY, numero


def renderizar(ctrl: PainelController, f: Filtros, embutido: bool = False) -> None:
    """Desenha a análise estatística da qualidade do ar (resumo, distribuição, boxplot, valores fora do padrão e relações)."""
    # Parâmetros: ctrl = Controller (fornece dados e cálculos); f = filtros escolhidos na barra lateral;
    # embutido = True quando a seção é mostrada dentro de outra página (que já tem título e faixa de contexto).
    # Retorno: nada. A função apenas desenha a página na tela.
    v = ctrl.variavel(f.fonte, f.variavel)
    if not embutido:
        estilo.cabecalho(
            "Análise estatística",
            "Médias, dispersão, distribuição, valores atípicos e correlações, com explicações em linguagem simples.",
        )
    ctx = ctrl.contexto(f)
    if not embutido:
        estilo.faixa_contexto(ctx)
    if ctrl.sem_dados(f):
        estilo.sem_dados()
        return
    fonte_txt = estilo.texto_fonte(ctx)
    rotulo = lambda c: ctrl.rotulo(f.fonte, c)  # noqa: E731 - atalho para escrever rótulos

    aba_resumo, aba_hist, aba_box, aba_out, aba_corr = st.tabs(["Resumo", "Distribuição dos valores", "Caixa (boxplot)", "Valores fora do padrão", "Relação entre indicadores"])

    # --- resumo -------------------------------------------------------------------
    with aba_resumo:
        st.markdown("##### Estatística descritiva do período")
        st.dataframe(tabelas.descritiva(ctrl.descritiva(f), rotulo), hide_index=True, width="stretch")
        st.caption(
            "Média: soma ÷ quantidade. Mediana: valor do meio. Moda*: valor mais frequente após arredondar "
            "(índices e a maioria das concentrações à unidade; CO e benzeno a 1 casa). Desvio padrão e variância: o "
            "quanto os valores se espalham em torno da média (calculados com n − 1). Q1 e Q3: valores abaixo dos quais "
            "estão 25% e 75% dos registros. Veja a página Ajuda para mais detalhes."
        )
        estilo.interpretacoes(ctrl.interpretacoes(f), titulo=f"Interpretação automática — {v.rotulo}")
        if v.eh_indice:
            dist = ctrl.distribuicao_faixas(f, f.variavel)
            st.plotly_chart(graficos.barras_faixas(dist, f"Faixas de qualidade do ar — {v.rotulo}"), width="stretch", config=CONFIG_PLOTLY)
            estilo.explicar_grafico(
                "Percentual dos registros em cada faixa oficial do índice.",
                "As faixas vêm da tabela da CETESB (vinculada à Resolução CONAMA nº 491/2018). Elas se aplicam ao "
                "índice, que já foi calculado pela fonte com a regra de cada poluente.",
                fonte_txt,
            )
        else:
            tabela, mensagem = ctrl.classificacao_concentracao(f, f.variavel)
            st.markdown("##### Classificação pela tabela oficial")
            st.caption(mensagem)
            if tabela is not None:
                st.dataframe(tabela.rename(columns={"faixa": "Faixa", "quantidade": "Quantidade de médias"}), hide_index=True)

    # --- distribuição ---------------------------------------------------------------
    with aba_hist:
        if not ctrl.tem_valores(f, f.variavel):
            estilo.sem_dados(f"Não há valores de {v.rotulo} no período escolhido.")
        else:
            classes = st.slider("Número de barras (classes)", 10, 80, 40, key="classes",
                                help="Mais barras mostram detalhes; menos barras mostram a forma geral.")
            foco = st.checkbox("Focar na faixa central (até o percentil 99)", value=True, key="foco_hist",
                               help="Valores muito extremos esticam o eixo e comprimem as barras. Desmarque para ver todos.")
            df = ctrl.dados_filtrados(f)
            completa = df[f.variavel].dropna()
            recorte = df
            if foco and not completa.empty:
                # quantile(0.99): valor abaixo do qual estão 99% dos registros.
                corte = completa.quantile(0.99)
                recorte = df[df[f.variavel] <= corte]
                fora = int((completa > corte).sum())
                if fora:
                    st.caption(f"{fora} registro(s) acima de {numero(corte)} não aparecem no gráfico; média e mediana consideram todos.")
            st.plotly_chart(graficos.histograma(recorte, v, classes, referencia=completa), width="stretch", config=CONFIG_PLOTLY)
            desc = ctrl.descritiva(f, [f.variavel]).loc[f.variavel]
            estilo.explicar_grafico(
                "Quantas vezes cada faixa de valores aconteceu no período.",
                "Cada barra conta quantos registros caem naquele intervalo. A linha cheia é a mediana "
                f"({numero(desc['mediana'])}) e a tracejada é a média ({numero(desc['media'])}). "
                + ctrl.comparar_media_mediana(desc["media"], desc["mediana"]),
                fonte_txt,
            )

    # --- boxplot ---------------------------------------------------------------------
    with aba_box:
        if not ctrl.tem_valores(f, f.variavel):
            estilo.sem_dados(f"Não há valores de {v.rotulo} no período escolhido.")
        else:
            opcoes = {"Geral": None, "Por mês do ano": "mes_nome", "Por dia da semana": "dia_semana"}
            escolha = st.radio("Agrupar por", list(opcoes), horizontal=True, key="agrupar_box")
            st.plotly_chart(graficos.boxplot(ctrl.dados_filtrados(f), v, opcoes[escolha]), width="stretch", config=CONFIG_PLOTLY)
            estilo.explicar_grafico(
                "Resumo visual da distribuição: onde está o meio dos dados e quais valores fogem do padrão.",
                "A caixa vai do 1º ao 3º quartil (os 50% centrais) e a linha dentro dela é a mediana. As “hastes” "
                "alcançam os valores mais distantes ainda dentro de 1,5 × IQR; pontos isolados estão além disso. "
                "Aqui a regra é aplicada a cada grupo, por isso pode diferir da aba Outliers, que usa todos os dados da estação.",
                fonte_txt,
            )

    # --- outliers -----------------------------------------------------------------------
    with aba_out:
        st.dataframe(tabelas.outliers(ctrl.resumo_outliers(f), rotulo), hide_index=True, width="stretch")
        estilo.leitura(
            f"<strong>Regra do IQR:</strong> um valor é sinalizado quando fica abaixo de Q1 − {numero(ctrl.fator_iqr)} × IQR "
            f"ou acima de Q3 + {numero(ctrl.fator_iqr)} × IQR, com Q1, Q3 e IQR calculados com todos os dados da estação "
            f"({'tratados' if f.dados == 'tratados' else 'originais'}). Os valores sinalizados <strong>não são removidos</strong>: "
            "podem ser erro de medição ou um evento real (como um episódio de poluição). Para ver o efeito de ignorá-los, "
            "marque “Ignorar outliers nas análises” em Opções avançadas."
        )

    # --- correlações -----------------------------------------------------------------------
    with aba_corr:
        motivo = ctrl.motivo_sem_correlacao(f.fonte)
        if motivo:
            st.info(motivo + " Para praticar correlações, use a fonte “Demonstração” ou importe dados do QUALAR, que trazem "
                    "concentrações em todas as horas.", icon=":material/info:")
            return
        colunas = ctrl.colunas(f)
        escolhidas = st.multiselect("Indicadores na matriz", colunas, default=colunas, format_func=rotulo, key="corr_vars")
        metodo = st.radio(
            "Forma de calcular a relação", ["pearson", "spearman"], horizontal=True, key="corr_metodo",
            help="Pearson mede relações em linha reta. Spearman compara a ordem dos valores e é menos afetado por valores extremos.",
            format_func=lambda m: "Pearson (relação em linha reta)" if m == "pearson" else "Spearman (pela ordem dos valores)",
        )
        if len(escolhidas) < 2:
            st.info("Escolha pelo menos dois indicadores para calcular a correlação.")
            return
        matriz = ctrl.correlacao(f, escolhidas, metodo)
        pares = ctrl.pares_correlacionados(f, escolhidas, metodo)
        st.plotly_chart(graficos.heatmap_correlacao(matriz, metodo, {c: rotulo(c) for c in escolhidas}), width="stretch", config=CONFIG_PLOTLY)
        estilo.explicar_grafico(
            "Cada quadrado mostra a correlação (r) entre dois indicadores, de −1 a +1. Um traço (—) indica que não há horas suficientes em comum.",
            "Perto de +1 (laranja): os indicadores tendem a subir juntos. Perto de −1 (azul): quando um sobe, o outro "
            "tende a descer. Perto de 0 (cinza): sem relação linear clara. A correlação só é calculada com pelo menos 30 "
            "horas em comum. **Correlação não prova causa.**",
            fonte_txt,
        )
        validos = pares.dropna(subset=["r"])
        if validos.empty:
            st.warning(
                "Nenhum par de indicadores tem horas suficientes em comum para calcular a correlação."
                + (" Nos dados do MonitorAr, cada hora traz o índice de um único poluente, então os poluentes quase "
                   "nunca têm valor na mesma hora." if ctrl.um_poluente_por_hora(f.fonte) else ""),
                icon=":material/info:",
            )
        else:
            topo = validos.iloc[0]
            estilo.leitura(
                f"<strong>Maior correlação no período:</strong> {rotulo(topo['variavel_a'])} × {rotulo(topo['variavel_b'])}, "
                f"r = <strong>{numero(topo['r'], 2)}</strong> ({ctrl.classificar_correlacao(topo['r'])}), com "
                f"{numero(topo['pares'], 0)} horas em comum."
            )
        st.markdown("##### Pares ordenados pela força da correlação")
        st.dataframe(tabelas.pares(pares, ctrl.classificar_correlacao, rotulo), hide_index=True, width="stretch")
        st.caption("Faixas usadas na leitura: abaixo de 0,1 praticamente nula; até 0,3 fraca; até 0,7 moderada; até 0,9 forte; acima, muito forte.")
