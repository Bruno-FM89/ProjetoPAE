"""Seção "Resumo do período" da página Qualidade do Ar (View).

Antes era a página "Visão geral" da V2; na V4 virou uma seção da página
"Qualidade do Ar" (``views/pagina_qualidade_ar.py``) para simplificar o menu.

Ordem da página (do mais importante ao detalhe):
1. de onde vêm os dados (faixa de contexto);
2. indicadores principais numa única faixa;
3. frases de interpretação calculadas;
4. um gráfico de evolução e a distribuição nas faixas de qualidade;
5. "Entenda cada indicador": explicação de cada variável, em seções expansíveis.

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
from views.estilo import CONFIG_PLOTLY, DESCRICAO_AGREGACAO, cor_parametro, data_br, inteiro, numero, percentual


def renderizar(ctrl: PainelController, f: Filtros, embutido: bool = False) -> None:
    # Parâmetros: ctrl = Controller (fornece dados e cálculos); f = filtros escolhidos na barra lateral;
    # embutido = True quando a seção é mostrada dentro de outra página (que já tem título e faixa de contexto).
    # Retorno: nada. A função apenas desenha a página na tela.
    """Desenha a página. ``ctrl`` fornece os dados; ``f`` traz os filtros da barra lateral."""
    if not embutido:
        estilo.cabecalho(
            "Visão geral",
            "Resumo dos indicadores de qualidade do ar no período escolhido. Comece por aqui e use o menu à "
            "esquerda para análises mais detalhadas.",
        )
    ctx = ctrl.contexto(f)
    if not embutido:
        estilo.faixa_contexto(ctx)

    ind = ctrl.indicadores(f)
    if not ind or ctrl.sem_dados(f):
        estilo.sem_dados()
        return

    catalogo = ctrl.catalogo(f.fonte)
    # Dados de índice (reais) e de concentração (demonstração) pedem indicadores diferentes.
    if "IQAR" in ind["variaveis"]:
        itens = _indicadores_indice(ctrl, f, ind)
    else:
        itens = _indicadores_por_variavel(catalogo, f, ind)
    itens.append({
        "rotulo": "Horas com algum valor", "valor": inteiro(ind["horas_com_algum_valor"]),
        "nota": f"de {inteiro(ind['horas'])} horas no período",
    })
    itens.append({"rotulo": "Período analisado", "valor": data_br(ind["inicio"]), "nota": f"até {data_br(ind['fim'])}", "compacto": True})
    estilo.faixa_indicadores(itens)

    principal = catalogo[f.variavel]
    estilo.interpretacoes(ctrl.interpretacoes(f), titulo=f"O que os dados mostram — {principal.rotulo}")

    # --- gráfico principal ---------------------------------------------------
    serie = ctrl.serie_temporal(f, [f.variavel])
    # Para índices, o gráfico de faixas fica ao lado (proporção 3:2); para concentrações, o gráfico ocupa a largura toda.
    esquerda, direita = st.columns([3, 2]) if principal.eh_indice else (st.container(), None)
    with esquerda:
        st.plotly_chart(
            graficos.linhas(serie, [principal], f"Evolução de {principal.rotulo} — {DESCRICAO_AGREGACAO[f.agregacao]}",
                            faixas=ctrl.faixas_iqar() if principal.eh_indice else None),
            width="stretch", config=CONFIG_PLOTLY,
        )
        estilo.explicar_grafico(
            f"Mostra como {principal.rotulo} variou no período escolhido. Espaços sem linha são períodos sem registro.",
            _como_ler_evolucao(principal),
            estilo.texto_fonte(ctx),
        )
    if direita is not None:
        with direita:
            dist = ctrl.distribuicao_faixas(f, f.variavel)
            st.plotly_chart(graficos.barras_faixas(dist, "Registros em cada faixa de qualidade"), width="stretch", config=CONFIG_PLOTLY)
            estilo.explicar_grafico(
                "Percentual dos registros do período em cada faixa oficial do índice (N1 Boa a N5 Péssima).",
                "Cada barra mostra que parte das horas com valor ficou em cada faixa. As faixas seguem a tabela da "
                "CETESB (índice 0–40 Boa, 41–80 Moderada, 81–120 Ruim, 121–200 Muito Ruim, acima de 200 Péssima). "
                "Uma barra N1 longa indica que a maior parte das horas teve qualidade do ar boa.",
                estilo.texto_fonte(ctx),
            )

    # --- explicação de cada indicador -------------------------------------------
    st.markdown("#### Entenda cada indicador")
    cobertura = ctrl.cobertura(f.fonte, f.estacao).set_index("chave")
    for chave in ctrl.variaveis(f.fonte, f.estacao):
        v = catalogo[chave]
        titulo = v.nome_completo + (" (índice por poluente)" if v.eh_indice and not v.eh_indice_estacao else "")
        with st.expander(titulo):
            _explicar_indicador(ctrl, f, ctx, v, ind["variaveis"].get(chave), cobertura.loc[chave])


def _indicadores_indice(ctrl: PainelController, f: Filtros, ind: dict) -> list[dict]:
    """Indicadores para fontes de ÍNDICE (dados reais do MonitorAr).

    Mostramos o IQAr da estação e não as médias de cada poluente, porque nesses
    dados cada hora traz um único poluente: a média de um poluente só cobre as
    horas em que ele foi o registrado e enganaria quem compara os números.
    """
    dados = ind["variaveis"]["IQAR"]
    dist = ctrl.distribuicao_faixas(f, "IQAR")
    ruim_ou_pior = dist.loc[2:, "percentual"].sum()
    itens = [
        {
            "rotulo": "IQAr da estação — mediana", "valor": numero(dados["mediana"], 0), "cor": cor_parametro("IQAR"),
            "nota": f"média {numero(dados['media'], 0)} · faixa {dados['faixa_mediana'].rotulo if dados.get('faixa_mediana') else '—'}",
        },
        {
            "rotulo": "Horas na faixa Boa (N1)", "valor": percentual(dist.loc[0, "percentual"]),
            "nota": f"Moderada {percentual(dist.loc[1, 'percentual'])} · Ruim ou pior {percentual(ruim_ou_pior, 1)}",
        },
        {
            "rotulo": "Maior índice no período", "valor": numero(dados["maximo"], 0),
            "nota": dados["faixa_maximo"].rotulo if dados.get("faixa_maximo") else "",
        },
    ]
    tabela = ctrl.poluente_registrado(f)
    if tabela is not None and not tabela.empty:
        totais = tabela.groupby("poluente")["horas"].sum().sort_values(ascending=False)
        itens.append({
            "rotulo": "Poluente registrado com mais frequência", "valor": totais.index[0],
            "nota": f"em {percentual(totais.iloc[0] / totais.sum() * 100)} das horas com valor",
        })
    return itens


def _indicadores_por_variavel(catalogo: dict, f: Filtros, ind: dict) -> list[dict]:
    """Indicadores para fontes de concentração/meteorologia: média de cada variável."""
    chaves = sorted(ind["variaveis"], key=lambda c: (c != f.variavel, -ind["variaveis"][c]["n"]))[:4]
    itens = []
    for chave in chaves:  # o principal primeiro, depois os de maior cobertura
        v, dados = catalogo[chave], ind["variaveis"][chave]
        itens.append({
            "rotulo": f"{v.rotulo} — média", "valor": numero(dados["media"]),
            "unidade": v.unidade, "nota": f"mediana {numero(dados['mediana'])} {v.unidade}",
            "cor": cor_parametro(v.parametro.codigo),
        })
    return itens


def _como_ler_evolucao(v) -> str:
    """Texto de "como interpretar" para gráficos de evolução no tempo."""
    if v.eh_indice:
        return (
            "O eixo horizontal é o tempo; o vertical é o valor do índice (um número sem unidade). Quanto mais alto, "
            "pior a qualidade do ar. As faixas coloridas ao fundo são as categorias oficiais: verde (Boa), amarelo "
            "(Moderada), laranja (Ruim), vermelho (Muito Ruim) e roxo (Péssima). Picos isolados indicam horas ou dias "
            "com qualidade pior que o habitual."
        )
    return (
        f"O eixo horizontal é o tempo; o vertical é o valor em {v.unidade}. Valores mais altos significam maior "
        "concentração (ou temperatura/umidade maior). Observe tendências, picos e períodos sem dados."
    )


def _explicar_indicador(ctrl: PainelController, f: Filtros, ctx: dict, v, dados: dict | None, cob) -> None:
    """Bloco explicativo de um indicador: o que é, unidade, origem, período e interpretação."""
    st.markdown(f"**O que é:** {v.parametro.descricao}")
    if v.eh_indice_estacao:
        st.markdown(
            "**Como ler:** é um número sem unidade. A CETESB calcula um índice para cada poluente e classifica a "
            "estação pelo maior deles. Faixas: 0–40 Boa, 41–80 Moderada, 81–120 Ruim, 121–200 Muito Ruim, acima de 200 Péssima."
        )
    elif v.eh_indice:
        st.markdown(
            f"**Como ler:** índice de qualidade do ar calculado para {v.parametro.sigla} (sem unidade). Não é a "
            "concentração do poluente."
        )
        if ctrl.um_poluente_por_hora(f.fonte):
            st.markdown(
                f"**Atenção:** neste arquivo, cada hora traz o índice de um único poluente. O valor de "
                f"{v.parametro.sigla} só existe nas horas em que ele foi o poluente registrado."
            )
    else:
        unidade_txt = v.unidade + ("" if v.unidade_confirmada else " (unidade assumida, não confirmada pela fonte)")
        st.markdown(f"**Unidade:** {unidade_txt}.")
    origem = "dataset fictício (não é medição)" if ctx["localizacao"] == "ficticio" else f"{ctx['fonte']}, estação {ctx['estacao']} ({ctx['municipio']}), fora de Heliópolis"
    st.markdown(f"**Origem dos dados:** {origem}.")
    st.markdown(
        f"**Registros:** {inteiro(cob['horas_com_valor'])} horas com valor ({percentual(cob['percentual'])} das horas "
        f"entre {data_br(cob['primeiro'])} e {data_br(cob['ultimo'])}). Período analisado agora: "
        f"{data_br(f.inicio)} a {data_br(f.fim)}."
    )
    if dados and dados["n"]:
        if v.eh_indice:
            st.markdown(
                f"**No período:** média {numero(dados['media'], 0)}, mediana {numero(dados['mediana'], 0)} "
                f"({dados['faixa_mediana'].rotulo if dados.get('faixa_mediana') else '—'}), maior valor "
                f"{numero(dados['maximo'], 0)} ({dados['faixa_maximo'].rotulo if dados.get('faixa_maximo') else '—'})."
            )
        else:
            st.markdown(f"**No período:** média {numero(dados['media'])} {v.unidade}, mediana {numero(dados['mediana'])} {v.unidade}.")
            _, mensagem = ctrl.classificacao_concentracao(f, v.chave)
            st.caption(mensagem)
    else:
        st.caption("Sem valores deste indicador no período escolhido.")
