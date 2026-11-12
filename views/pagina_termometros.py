"""Página "Temperatura e Umidade em Heliópolis" (View).

Mostra os dados dos termômetros que a UNAS instalou em residências da
comunidade. Organização da página (pensada para quem nunca usou o painel):

1. Título, frase de objetivo e uma caixa "De onde vêm estes dados".
2. Filtros numerados (termômetros, período, forma de mostrar os valores).
3. Faixa de números principais (média, mínima, máxima) e frases automáticas.
4. Um seletor "O que você quer ver?" com 5 opções — só a opção escolhida é
   desenhada, o que deixa a tela limpa e rápida:
   comparar termômetros · ao longo do tempo · dia típico · mês a mês · tabela.
5. "Entenda os indicadores": explicações em seções que abrem e fecham.

Nenhum cálculo é feito aqui: tudo vem do ``TermometrosController``.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from controllers.sistema import Sistema
from controllers.termometros_controller import COL_TEMP, COL_UMID, FiltrosTermometros, TermometrosController
from views import estilo, filtros_termometros
from views import graficos_comunidade as gc
from views.estilo import CONFIG_PLOTLY, data_br, inteiro, numero, percentual

FONTE = "Fonte: termômetros instalados pela UNAS em residências de Heliópolis (identificação anônima)."

SECOES = {
    "comparar": ":material/compare_arrows: Comparar termômetros",
    "tempo": ":material/show_chart: Ao longo do tempo",
    "dia": ":material/schedule: Dia típico",
    "mes": ":material/calendar_month: Mês a mês",
    "tabela": ":material/table: Tabela e download",
}


def renderizar(sistema: Sistema) -> None:
    """Desenha a página. ``sistema`` traz os Controllers (aqui só o dos termômetros é usado)."""
    estilo.cabecalho(
        "Temperatura e Umidade em Heliópolis",
        "Medições feitas dentro da comunidade por termômetros da UNAS. Veja quanto calor e quanta umidade cada casa "
        "registrou, compare os locais e acompanhe as mudanças ao longo dos dias.",
    )
    ctrl = sistema.termometros
    if ctrl is None:
        st.error(
            "Os dados dos termômetros não foram encontrados. " + sistema.erros.get("termometros", ""),
            icon=":material/error:",
        )
        st.caption("Como resolver: veja o GUIA_MANUTENCAO.md, seção “Atualizar os dados dos termômetros”.")
        return

    _caixa_origem(ctrl)
    f = filtros_termometros.renderizar(ctrl, "term")
    if f is None:
        return
    if ctrl.sem_dados(f):
        estilo.sem_dados("Nenhuma medição dos termômetros escolhidos neste período. Escolha outro período ou outros termômetros.")
        return
    faltando = ctrl.ids_sem_dados(f)
    if faltando:
        st.info(
            "Sem medições no período: " + ", ".join(ctrl.nome(t) for t in faltando) + ". Eles não aparecem nos gráficos.",
            icon=":material/info:",
        )

    coluna = st.segmented_control(
        "4. Medida", [COL_TEMP, COL_UMID], format_func=lambda c: ctrl.grandezas()[c]["nome"], default=COL_TEMP,
        key="term_grandeza", persist_state="session",
        help="Temperatura: quanto o ar está quente ou frio (°C). Umidade relativa: quanta água há no ar (%).",
    ) or COL_TEMP
    g = ctrl.grandezas()[coluna]
    cores = gc.cores_termometros([ctrl.nome(t) for t in ctrl.ids])

    _indicadores(ctrl, f, coluna)
    estilo.interpretacoes(ctrl.interpretacoes(f, coluna), titulo=f"O que os dados mostram — {g['nome']}")

    secao = st.segmented_control(
        "O que você quer ver?", list(SECOES), format_func=SECOES.get, default="comparar",
        key="term_secao", persist_state="session",
    ) or "comparar"
    if secao == "comparar":
        _comparar(ctrl, f, coluna, cores)
    elif secao == "tempo":
        _tempo(ctrl, f, coluna, cores)
    elif secao == "dia":
        _dia_tipico(ctrl, f, coluna, cores)
    elif secao == "mes":
        _mes_a_mes(ctrl, f, coluna, cores)
    else:
        _tabela(ctrl, f)

    _entenda()


# --- blocos da página ----------------------------------------------------------------
def _caixa_origem(ctrl: TermometrosController) -> None:
    """Explica de onde vêm os dados e quem é cada termômetro (sem endereços)."""
    tabela = ctrl.tabela_termometros()
    validados = int(tabela["localizacao_validada"].sum())
    st.markdown(
        f'<div class="contexto"><div class="linha1">Medições feitas DENTRO de Heliópolis por {len(tabela)} termômetros '
        f"instalados pela UNAS em residências, uma leitura a cada 10 minutos.</div>"
        f'<div class="linha2">Para proteger os moradores, os termômetros aparecem como “Termômetro 1, 2, 3...”, sem nomes '
        f"nem endereços. Região confirmada pela UNAS: {validados} de {len(tabela)}.</div></div>",
        unsafe_allow_html=True,
    )
    with st.expander("Quem é cada termômetro e quando mediu", icon=":material/thermostat:"):
        st.dataframe(
            pd.DataFrame({
                "Termômetro": tabela["nome"],
                "Região (quebrada)": [q or "não informada" for q in tabela["quebrada"]],
                "Situação da região": ["confirmada pela UNAS" if v else "a confirmar" for v in tabela["localizacao_validada"]],
                "Primeira leitura": [data_br(d) for d in tabela["inicio"]],
                "Última leitura": [data_br(d) for d in tabela["fim"]],
                "Leituras": [inteiro(n) for n in tabela["leituras"]],
            }),
            hide_index=True, width="stretch",
        )
        st.caption(
            "Os aparelhos foram instalados em casas; a UNAS ainda vai registrar em qual cômodo e a que altura ficou "
            "cada um. Por isso os valores descrevem o ambiente onde o aparelho estava, e não a temperatura da rua. "
            "Veja o mapa em “Mapa de Heliópolis”."
        )


def _indicadores(ctrl: TermometrosController, f: FiltrosTermometros, coluna: str) -> None:
    """Faixa com os números principais do recorte."""
    resumo = ctrl.resumo(f)
    g = ctrl.grandezas()[coluna]
    p = "temp" if coluna == COL_TEMP else "umid"
    mais_alto = resumo.loc[resumo[f"{p}_max"].idxmax()]
    mais_baixo = resumo.loc[resumo[f"{p}_min"].idxmin()]
    media_geral = (resumo[f"{p}_media"] * resumo["leituras"]).sum() / resumo["leituras"].sum()
    itens = [
        {"rotulo": f"{g['nome']} média", "valor": numero(media_geral), "unidade": g["unidade"],
         "nota": "dos termômetros escolhidos" if len(resumo) > 1 else mais_alto["nome"]},
        {"rotulo": "Máxima registrada", "valor": numero(mais_alto[f"{p}_max"]), "unidade": g["unidade"], "nota": mais_alto["nome"]},
        {"rotulo": "Mínima registrada", "valor": numero(mais_baixo[f"{p}_min"]), "unidade": g["unidade"], "nota": mais_baixo["nome"]},
        {"rotulo": "Leituras analisadas", "valor": inteiro(resumo["leituras"].sum()), "nota": f"{len(resumo)} termômetro(s)"},
        {"rotulo": "Período", "valor": data_br(f.inicio), "nota": f"até {data_br(f.fim)}", "compacto": True},
    ]
    estilo.faixa_indicadores(itens)


def _comparar(ctrl, f, coluna, cores) -> None:
    """Comparação lado a lado: faixa mínimo–máximo com a média, tabela e tempo acima de um limite."""
    g = ctrl.grandezas()[coluna]
    p = "temp" if coluna == COL_TEMP else "umid"
    resumo = ctrl.resumo(f)
    st.plotly_chart(
        gc.intervalo_por_termometro(resumo, p, g["unidade"], cores, f"{g['nome']}: menor valor, média e maior valor de cada termômetro"),
        width="stretch", config=CONFIG_PLOTLY,
    )
    estilo.explicar_grafico(
        "Cada linha é um termômetro: começa no menor valor medido, termina no maior, e o círculo branco marca a média.",
        "Linhas mais à direita indicam locais mais quentes (ou mais úmidos). Linhas mais compridas indicam locais com "
        "variação maior entre o momento mais frio e o mais quente. Compare a posição dos círculos para ver qual casa "
        "costuma ficar mais quente. **Atenção:** compare usando o mesmo período para todos (opção “Quando todos mediram juntos”).",
        FONTE,
    )
    st.markdown("##### Tabela de comparação")
    amplitude = ctrl.amplitude_diaria_media(f, coluna)
    st.dataframe(
        pd.DataFrame({
            "Termômetro": resumo["nome"],
            f"Média ({g['unidade']})": [numero(v) for v in resumo[f"{p}_media"]],
            f"Mínima ({g['unidade']})": [numero(v) for v in resumo[f"{p}_min"]],
            f"Máxima ({g['unidade']})": [numero(v) for v in resumo[f"{p}_max"]],
            f"Amplitude ({g['unidade']})": [numero(v) for v in resumo[f"{p}_amplitude"]],
            f"Variação média dentro do dia ({g['unidade']})": [numero(amplitude.get(n)) for n in resumo["nome"]],
            "Leituras": [inteiro(v) for v in resumo["leituras"]],
        }),
        hide_index=True, width="stretch",
    )
    st.caption(
        "Amplitude = máxima − mínima de todo o período. Variação média dentro do dia = média, entre os dias completos, "
        "da diferença entre o momento mais quente (ou úmido) e o mais frio (ou seco) do mesmo dia."
    )

    st.markdown(f"##### Quanto tempo ficou acima de um valor?")
    padrao, minimo, maximo = (30.0, 20.0, 35.0) if coluna == COL_TEMP else (80.0, 40.0, 95.0)
    limite = st.slider(
        f"Escolha o valor de referência ({g['unidade']})", min_value=minimo, max_value=maximo, value=padrao, step=0.5,
        key=f"term_limite_{p}", help="Arraste para mudar o valor. A tabela mostra quanto tempo cada termômetro passou acima dele.",
    )
    acima = ctrl.tempo_acima(f, coluna, limite)
    st.dataframe(
        pd.DataFrame({
            "Termômetro": acima["nome"],
            "Tempo acima (horas, aprox.)": [numero(v, 0) for v in acima["horas_aprox"]],
            "% das leituras": [percentual(v, 1) for v in acima["percentual"]],
            "Dias em que aconteceu": [inteiro(v) for v in acima["dias_com_ocorrencia"]],
        }),
        hide_index=True, width="stretch",
    )
    st.caption(
        f"Cada leitura vale cerca de 10 minutos. Este valor de referência ({numero(limite)} {g['unidade']}) é só uma régua "
        "escolhida por você para comparar os locais; não é um limite oficial de saúde."
    )


def _tempo(ctrl, f, coluna, cores) -> None:
    """Evolução no tempo, um termômetro por linha, e a faixa diária de um termômetro."""
    g = ctrl.grandezas()[coluna]
    agrup = ctrl.agrupamentos()[f.agrupamento].lower()
    serie = ctrl.serie(f, coluna)
    st.plotly_chart(
        gc.linhas_termometros(serie, g["unidade"], f"{g['nome']} ao longo do tempo — {agrup}", cores, f"{g['nome']} ({g['unidade']})"),
        width="stretch", config=CONFIG_PLOTLY,
    )
    estilo.explicar_grafico(
        "Cada linha colorida é um termômetro. A linha sobe quando a casa esquentou (ou ficou mais úmida) e desce quando esfriou.",
        "Passe o mouse para ver os valores de todos os termômetros naquela data. Clique no nome de um termômetro na "
        "legenda para escondê-lo ou mostrá-lo. Arraste sobre o gráfico para aproximar e dê dois cliques para voltar. "
        "Espaços sem linha são períodos sem medição: nada foi inventado para preenchê-los.",
        FONTE,
    )
    st.markdown("##### Quanto variou em cada dia")
    nomes = [ctrl.nome(t) for t in f.ids]
    escolhido = st.selectbox(
        "Termômetro", nomes, key="term_faixa_nome",
        help="Mostra o menor valor, a média e o maior valor de cada dia para o termômetro escolhido.",
    )
    extremos = ctrl.extremos_diarios(f, coluna)
    st.plotly_chart(gc.faixa_diaria(extremos, escolhido, cores.get(escolhido), g["unidade"], f"{g['nome']} ({g['unidade']})"),
                    width="stretch", config=CONFIG_PLOTLY)
    estilo.explicar_grafico(
        "A faixa clara vai do valor mais baixo ao mais alto de cada dia; a linha forte é a média do dia.",
        "Uma faixa larga significa que naquele dia houve muita diferença entre a hora mais fria e a mais quente. "
        "Faixas estreitas indicam dias de temperatura (ou umidade) mais constante. O primeiro e o último dia podem estar "
        "incompletos, porque o aparelho começou ou parou de medir no meio do dia.",
        FONTE,
    )


def _dia_tipico(ctrl, f, coluna, cores) -> None:
    """Seção Dia típico: média de cada hora do dia para cada termômetro."""
    g = ctrl.grandezas()[coluna]
    st.plotly_chart(
        gc.perfil_horario(ctrl.perfil_horario(f, coluna), g["unidade"], cores, f"{g['nome']} ({g['unidade']})",
                          f"Dia típico: {g['nome'].lower()} média em cada hora do dia"),
        width="stretch", config=CONFIG_PLOTLY,
    )
    estilo.explicar_grafico(
        "Mostra em que horas do dia cada casa costuma ficar mais quente ou mais fria (ou mais úmida ou mais seca).",
        "Cada ponto é a média de todas as leituras feitas naquela hora, em todos os dias do período. Por exemplo, o ponto "
        "das 15h junta todas as leituras entre 15h00 e 15h59. Assim dá para ver o “ritmo” de um dia comum, sem a "
        "confusão de dias muito quentes ou muito frios.",
        FONTE,
    )


def _mes_a_mes(ctrl, f, coluna, cores) -> None:
    """Seção Mês a mês: média de cada mês, para comparar períodos."""
    g = ctrl.grandezas()[coluna]
    mensal = ctrl.media_mensal(f, coluna)
    st.plotly_chart(
        gc.barras_mensais(mensal, g["unidade"], cores, f"{g['nome']} ({g['unidade']})", f"{g['nome']} média de cada mês"),
        width="stretch", config=CONFIG_PLOTLY,
    )
    estilo.explicar_grafico(
        "Compara os meses: cada grupo de barras é um mês e cada cor é um termômetro.",
        "Use para comparar períodos (por exemplo, março com julho). Passe o mouse para ver quantas leituras entraram em "
        "cada média: meses com poucas leituras (início ou fim da medição) representam só parte do mês e merecem cautela. "
        "Um termômetro sem barra num mês não estava medindo naquele mês.",
        FONTE,
    )


def _tabela(ctrl, f) -> None:
    """Seção Tabela e download: as medições em tabela e o botão para baixar em CSV."""
    tabela = ctrl.tabela_medicoes(f)
    agrup = ctrl.agrupamentos()[f.agrupamento]
    st.caption(f"{inteiro(len(tabela))} linhas · {agrup.lower()}. Para ver cada leitura de 10 minutos, mude o item 3 dos filtros.")
    st.dataframe(
        tabela, hide_index=True, width="stretch", height=380,
        column_config={
            "termometro": st.column_config.TextColumn("Termômetro"),
            "data_hora": st.column_config.DatetimeColumn("Data e hora", format="DD/MM/YYYY HH:mm"),
            "temperatura_c": st.column_config.NumberColumn("Temperatura (°C)", format="%.1f"),
            "umidade_pct": st.column_config.NumberColumn("Umidade (%)", format="%.1f"),
        },
    )
    st.download_button(
        "Baixar esta tabela (CSV)", data=ctrl.exportar_csv(f), file_name="termometros_heliopolis.csv", mime="text/csv",
        icon=":material/download:", key="term_baixar",
    )
    st.caption(
        "O arquivo abre no Excel ou no Google Planilhas. Separador “;” e ponto como separador decimal. "
        "Ele não contém nomes nem endereços dos moradores."
    )


def _entenda() -> None:
    """Explicações dos indicadores em seções que abrem e fecham."""
    st.markdown("#### Entenda os indicadores")
    itens = {
        "Temperatura (°C)": "Indica o quanto o ar está quente ou frio, em graus Celsius. Como os aparelhos ficaram dentro "
        "das casas, mostram o calor que os moradores sentiram no ambiente onde o aparelho estava.",
        "Umidade relativa do ar (%)": "Quanto vapor de água há no ar, em comparação com o máximo que o ar aguentaria naquela "
        "temperatura. 100% = ar saturado (como em dia de neblina). Umidade muito baixa resseca as vias respiratórias; muito "
        "alta favorece mofo. A Defesa Civil de São Paulo considera estado de atenção quando a umidade fica entre 20% e 30%.",
        "Média, mínima e máxima": "**Média:** soma de todas as leituras dividida pela quantidade — o valor “típico”. "
        "**Mínima:** o menor valor medido. **Máxima:** o maior valor medido. A média esconde os extremos; por isso mostramos os três.",
        "Amplitude": "Diferença entre a máxima e a mínima. Mostra o tamanho da variação: uma amplitude grande indica um "
        "local que esquenta e esfria muito.",
        "Média de cada hora / dia / semana / mês": "O aparelho mede a cada 10 minutos. Para facilitar a leitura, podemos "
        "juntar as leituras e mostrar a média de cada hora, dia, semana ou mês. Isso não altera os dados originais.",
        "Período em que todos mediram juntos": "Os termômetros começaram e terminaram de medir em datas diferentes (veja "
        "“Quem é cada termômetro e quando mediu”, no topo da página). Comparar períodos diferentes seria injusto: um mês de "
        "verão é mais quente que um de inverno, por exemplo. Por isso a comparação usa, por padrão, só os dias em que "
        "todos os termômetros escolhidos estavam medindo.",
    }
    for titulo, texto in itens.items():
        with st.expander(titulo):
            st.markdown(texto)
