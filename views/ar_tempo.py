"""Seção "Ao longo do tempo" da página Qualidade do Ar (View).

Antes era a página "Análise temporal" da V2.

Abas:
* Evolução — série no tempo (com faixas do IQAr ao fundo) e média de cada mês;
* Padrões do dia e da semana — médias por hora, dia da semana e mês do ano,
  e (para índices) qual poluente foi registrado em cada hora;
* Calendário — mapa de calor com a média de cada dia.

Junta as páginas "Séries temporais" e "Padrões no tempo" da V1.

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
from views.estilo import CONFIG_PLOTLY, DESCRICAO_AGREGACAO, cor_parametro


def renderizar(ctrl: PainelController, f: Filtros, embutido: bool = False) -> None:
    """Desenha a seção Ao longo do tempo: evolução, padrões do dia e da semana e calendário."""
    # Parâmetros: ctrl = Controller (fornece dados e cálculos); f = filtros escolhidos na barra lateral;
    # embutido = True quando a seção é mostrada dentro de outra página (que já tem título e faixa de contexto).
    # Retorno: nada. A função apenas desenha a página na tela.
    v = ctrl.variavel(f.fonte, f.variavel)
    if not embutido:
        estilo.cabecalho(
            "Análise temporal",
            f"Como {v.rotulo} muda ao longo do tempo: tendência, padrões ao longo do dia e da semana, e um calendário diário. "
            "Para analisar outro indicador, troque-o na barra lateral.",
        )
    ctx = ctrl.contexto(f)
    if not embutido:
        estilo.faixa_contexto(ctx)
    if not ctrl.tem_valores(f, f.variavel):
        estilo.sem_dados(f"Não há valores de {v.rotulo} no período escolhido.")
        return
    fonte_txt = estilo.texto_fonte(ctx)
    faixas = ctrl.faixas_iqar() if v.eh_indice else None

    aba_evolucao, aba_padroes, aba_calendario = st.tabs(["Evolução", "Padrões do dia e da semana", "Calendário"])

    with aba_evolucao:
        marcar = st.checkbox(
            "Marcar outliers (disponível com “Agrupar as séries por: Horária”, em Opções avançadas)",
            value=False, key="marcar_outliers", disabled=(f.agregacao != "h" or f.excluir_outliers),
            help="Losangos marcam os valores fora das cercas do IQR. Eles continuam fazendo parte dos dados.",
        )
        # Os losangos só fazem sentido na série horária: numa média diária o valor extremo some na média.
        pontos = ctrl.pontos_outliers(f, [f.variavel]) if (marcar and f.agregacao == "h") else None
        serie = ctrl.serie_temporal(f, [f.variavel])
        st.plotly_chart(
            graficos.paineis(serie, [v], f"Variação de {v.rotulo} ao longo do tempo — {DESCRICAO_AGREGACAO[f.agregacao]}", pontos, faixas),
            width="stretch", config=CONFIG_PLOTLY,
        )
        estilo.explicar_grafico(
            f"Permite observar como {v.rotulo} mudou durante o período selecionado.",
            "Valores mais altos ficam mais acima no gráfico. "
            + ("Para o índice, as faixas coloridas mostram a categoria oficial (verde = Boa ... roxo = Péssima). " if v.eh_indice else "")
            + "Trechos sem linha são horas ou dias sem registro: eles NÃO foram preenchidos. "
            "Agrupar por dia, semana ou mês (Opções avançadas) suaviza as oscilações e destaca a tendência.",
            fonte_txt,
        )
        p = ctrl.padroes(f)
        mensal = p["mensal"].dropna(subset=["media"])
        if len(mensal) >= 2:  # com um único mês não há o que comparar
            st.plotly_chart(graficos.barras_mensais(mensal, v), width="stretch", config=CONFIG_PLOTLY)
            estilo.explicar_grafico(
                "Média de cada mês do calendário, considerando só as horas com registro.",
                "Compare a altura das barras para ver meses com valores maiores ou menores. Passe o mouse para ver "
                "quantos registros entraram em cada média: meses com poucos registros merecem mais cautela.",
                fonte_txt,
            )

    with aba_padroes:
        p = ctrl.padroes(f)
        esquerda, direita = st.columns(2)
        with esquerda:
            st.plotly_chart(graficos.linha_hora(p["hora"], v), width="stretch", config=CONFIG_PLOTLY)
            estilo.explicar_grafico(
                "Média do indicador em cada hora do dia, juntando todos os dias do período.",
                "Cada ponto é a média de todas as medições feitas naquela hora (por exemplo, todas as 8h). "
                "Picos mostram horários com valores tipicamente maiores. Isso descreve um padrão, não explica a causa.",
                fonte_txt,
            )
        with direita:
            st.plotly_chart(
                graficos.barras(p["dia_semana"], "dia_semana", v, "Dia da semana", f"Média por dia da semana — {v.rotulo}"),
                width="stretch", config=CONFIG_PLOTLY,
            )
            estilo.explicar_grafico(
                "Média do indicador em cada dia da semana.",
                "Barras mais altas indicam dias da semana com valores médios maiores no período escolhido.",
                fonte_txt,
            )
        st.plotly_chart(graficos.barras(p["mes"], "mes_nome", v, "Mês do ano", f"Média por mês do ano — {v.rotulo}"), width="stretch", config=CONFIG_PLOTLY)
        estilo.explicar_grafico(
            "Média por mês do ano. Se o período tiver mais de um ano, os mesmos meses são somados (ex.: julho de 2024 e de 2025).",
            "Ajuda a perceber variações entre estações do ano. Para ver cada mês separadamente, use a aba Evolução.",
            fonte_txt,
        )

        # Só existe para fontes de índice por poluente (dados reais do MonitorAr).
        tabela = ctrl.poluente_registrado(f)
        if tabela is not None and not tabela.empty:
            cores = {var.parametro.sigla: cor_parametro(var.parametro.codigo) for var in ctrl.catalogo(f.fonte).values()}
            st.plotly_chart(graficos.poluente_por_hora(tabela, cores), width="stretch", config=CONFIG_PLOTLY)
            estilo.explicar_grafico(
                "Em cada hora do dia, quantas vezes cada poluente foi o que teve o índice registrado na estação.",
                "O arquivo do MonitorAr traz, para cada hora, o índice de um único poluente. Este gráfico mostra qual "
                "foi, hora a hora. Ele ajuda a entender por que as médias de cada poluente não são comparáveis "
                "entre si: cada uma vem de horários diferentes.",
                fonte_txt,
            )

    with aba_calendario:
        p = ctrl.padroes(f)
        st.plotly_chart(graficos.calendario(p["calendario"], v), width="stretch", config=CONFIG_PLOTLY)
        estilo.explicar_grafico(
            "Cada quadrado é um dia; cada linha é um mês. A cor indica a média do dia.",
            "Cores mais escuras significam valores maiores. Quadrados vazios são dias sem registro. Procure "
            "sequências de dias escuros (episódios) e diferenças entre os meses.",
            fonte_txt,
        )
