"""Construção dos gráficos interativos com Plotly (View).

Como um gráfico Plotly é montado
--------------------------------
1. Cria-se uma figura vazia: ``fig = go.Figure()``.
2. Acrescentam-se "traços" (``fig.add_trace``): cada traço é uma série
   desenhada como linha (``go.Scatter``), barra (``go.Bar``), mapa de calor
   (``go.Heatmap``), caixa (``go.Box``) etc.
3. Ajusta-se o "layout": título, eixos, legenda, cores de fundo.
4. A página mostra a figura com ``st.plotly_chart(fig)``. O Plotly já traz
   zoom, legenda clicável e valores ao passar o mouse.

Regras seguidas em todos os gráficos
------------------------------------
* Título em português e eixos com a unidade de medida.
* Cada parâmetro tem sempre a mesma cor (``views/estilo.py``).
* Nunca dois eixos verticais com escalas diferentes: variáveis de unidades
  diferentes vão para painéis separados.
* Números no padrão brasileiro (``separators=",."``).

Aqui não há cálculo estatístico: as funções recebem tabelas prontas do Controller.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go  # "graph_objects": peças básicas dos gráficos Plotly
from plotly.subplots import make_subplots  # cria figuras com vários painéis

from views.estilo import (
    ESCALA_DIVERGENTE,
    ESCALA_SEQUENCIAL,
    FONTE,
    LINHA,
    PRIMARIA,
    TINTA,
    TINTA_2,
    cor_parametro,
    numero,
)

GRADE = "#E1E8E7"  # cor das linhas de grade (bem clara, para não competir com os dados)
MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


# =============================================================================
# Utilidades comuns
# =============================================================================
def _base(fig: go.Figure, titulo: str, altura: int, legenda: bool = False) -> go.Figure:
    """Aplica o visual padrão: título, tamanho, fontes, fundo transparente e legenda."""
    fig.update_layout(
        title=dict(text=titulo, x=0, xanchor="left", y=0.98, font=dict(size=15, color=TINTA)),
        height=altura,
        margin=dict(l=8, r=8, t=64 if legenda else 48, b=8),
        paper_bgcolor="rgba(0,0,0,0)",  # transparente: usa a cor de fundo da página
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, color=TINTA_2, size=13),
        separators=",.",  # vírgula decimal e ponto de milhar
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, font=dict(size=13)),
        hoverlabel=dict(bgcolor="white", bordercolor=LINHA, font=dict(family=FONTE, size=13, color=TINTA)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=LINHA, ticks="outside", tickcolor=LINHA)
    fig.update_yaxes(gridcolor=GRADE, zeroline=False, linecolor="rgba(0,0,0,0)")
    return fig


def _horario(df: pd.DataFrame) -> bool:
    """Verdadeiro quando os pontos estão a menos de 1 dia de distância (série horária)."""
    datas = pd.to_datetime(df["Data"]).dropna()
    return len(datas) > 1 and (datas.iloc[1] - datas.iloc[0]) < pd.Timedelta(days=1)


def _eixo_data(fig: go.Figure, datas: pd.Series, horario: bool = False, **kwargs) -> None:
    """Escreve as datas do eixo X em português.

    O Plotly só conhece nomes de mês em inglês; por isso, em períodos longos,
    criamos as marcas do eixo manualmente ("jan/24", "fev/24"...).
    """
    datas = pd.to_datetime(datas).dropna()
    fig.update_xaxes(hoverformat="%d/%m/%Y %Hh" if horario else "%d/%m/%Y", **kwargs)
    if datas.empty:
        return
    inicio, fim = datas.min(), datas.max()
    if (fim - inicio).days >= 120:  # mais de ~4 meses: uma marca por mês (ou a cada 3 ou 6 meses)
        dias = (fim - inicio).days
        passo = 1 if dias <= 400 else (3 if dias <= 1500 else 6)
        meses = pd.date_range(inicio.normalize().replace(day=1), fim, freq=f"{passo}MS")
        fig.update_xaxes(
            tickmode="array", tickvals=list(meses),
            ticktext=[f"{MESES_ABREV[d.month - 1].lower()}/{str(d.year)[2:]}" for d in meses], **kwargs,
        )
    else:
        fig.update_xaxes(tickformat="%d/%m", **kwargs)


def _hover(unidade: str) -> str:
    """Texto que aparece ao passar o mouse: valor com 1 casa + unidade + nome da série."""
    sufixo = "" if unidade.startswith("índice") else f" {unidade}"
    return f"%{{y:,.1f}}{sufixo}<extra>%{{fullData.name}}</extra>"


def _faixas_fundo(fig: go.Figure, faixas, maximo: float, **kwargs) -> None:
    """Pinta, ao fundo, as faixas oficiais do IQAr (N1 verde ... N5 roxo).

    Só é usada em gráficos de ÍNDICE. ``maximo`` limita até onde pintar, para
    não esticar o gráfico até 200+ quando os valores são pequenos.
    """
    topo = max(maximo * 1.05, 45)
    for faixa in faixas:
        y0 = faixa.indice_min if faixa.indice_min == 0 else faixa.indice_min - 1
        y1 = faixa.indice_max if faixa.indice_max is not None else topo
        if y0 >= topo:
            break
        # add_hrect desenha um retângulo horizontal; layer="below" o coloca atrás das linhas.
        fig.add_hrect(y0=y0, y1=min(y1, topo), fillcolor=faixa.cor, opacity=0.09, line_width=0, layer="below", **kwargs)


# =============================================================================
# Séries temporais
# =============================================================================
def linhas(df: pd.DataFrame, variaveis: list, titulo: str, altura: int = 360, faixas=None) -> go.Figure:
    """Uma ou mais variáveis da MESMA unidade num único eixo.

    Parâmetros:
        df: tabela com ``Data`` e uma coluna por variável (chave).
        variaveis: objetos Variavel (dão nome, unidade e cor).
        titulo: título do gráfico.
        faixas: lista de faixas do IQAr para pintar o fundo (só para índices).
    """
    fig = go.Figure()
    for v in variaveis:
        fig.add_trace(go.Scatter(
            x=df["Data"], y=df[v.chave], mode="lines", name=v.rotulo,
            line=dict(color=cor_parametro(v.parametro.codigo), width=1.8),
            connectgaps=False,  # não liga pontos separados por lacunas: o vazio fica visível
            hovertemplate=_hover(v.unidade),
        ))
    fig.update_yaxes(title_text=variaveis[0].titulo_eixo if len(variaveis) == 1 else variaveis[0].unidade)
    fig.update_layout(hovermode="x unified")  # um só balão com todas as séries daquela data
    if faixas and variaveis and variaveis[0].eh_indice:
        maximo = df[[v.chave for v in variaveis]].max().max()
        _faixas_fundo(fig, faixas, maximo if maximo == maximo else 50)
    _base(fig, titulo, altura, legenda=len(variaveis) > 1)
    _eixo_data(fig, df["Data"], horario=_horario(df))
    return fig


def paineis(df: pd.DataFrame, variaveis: list, titulo: str, pontos_outliers: dict | None = None, faixas=None, altura_painel: int = 240) -> go.Figure:
    """Um painel por variável, com o eixo do tempo compartilhado.

    Usado para comparar variáveis de unidades diferentes sem misturar escalas.
    ``pontos_outliers`` (opcional) marca com losangos os valores sinalizados pelo IQR.
    """
    n = len(variaveis)
    fig = make_subplots(
        rows=n, cols=1, shared_xaxes=True, vertical_spacing=min(0.08, 0.3 / n),
        subplot_titles=[v.rotulo for v in variaveis],
    )
    largura = 1.1 if len(df) > 2500 else 1.8  # linha mais fina quando há muitos pontos
    legenda_outlier_criada = False
    for i, v in enumerate(variaveis, start=1):  # i = número do painel (1, 2, 3...)
        fig.add_trace(go.Scatter(
            x=df["Data"], y=df[v.chave], mode="lines", name=v.rotulo,
            line=dict(color=cor_parametro(v.parametro.codigo), width=largura), connectgaps=False,
            hovertemplate=_hover(v.unidade),
        ), row=i, col=1)
        pontos = (pontos_outliers or {}).get(v.chave)
        if pontos is not None and not pontos.empty:
            fig.add_trace(go.Scatter(
                x=pontos["Data"], y=pontos[v.chave], mode="markers", name="Outlier sinalizado (IQR)",
                marker=dict(color=TINTA, size=8, symbol="diamond", line=dict(color="white", width=1.5)),
                legendgroup="outlier", showlegend=not legenda_outlier_criada, hovertemplate=_hover(v.unidade),
            ), row=i, col=1)
            legenda_outlier_criada = True
        if faixas and v.eh_indice:
            maximo = df[v.chave].max()
            _faixas_fundo(fig, faixas, maximo if maximo == maximo else 50, row=i, col=1)
        fig.update_yaxes(title_text=v.unidade if not v.eh_indice else "índice", row=i, col=1)
    fig.update_annotations(font=dict(size=13, color=TINTA), xanchor="left", x=0)
    fig.update_layout(hovermode="x unified")
    _base(fig, titulo, altura_painel * n + 70, legenda=len(fig.data) > 1)
    fig.update_xaxes(title_text="Data", row=n, col=1)
    _eixo_data(fig, df["Data"], horario=_horario(df))
    return fig


def comparacao_estacoes(df: pd.DataFrame, variavel, titulo: str, cores: dict[str, str], faixas=None) -> go.Figure:
    """A mesma variável em várias estações, cada uma com sua linha e cor fixa."""
    fig = go.Figure()
    for estacao in [c for c in df.columns if c != "Data"]:
        fig.add_trace(go.Scatter(
            x=df["Data"], y=df[estacao], mode="lines", name=estacao,
            line=dict(color=cores.get(estacao, PRIMARIA), width=1.7), connectgaps=False,
            hovertemplate=_hover(variavel.unidade),
        ))
    fig.update_yaxes(title_text=variavel.titulo_eixo)
    fig.update_layout(hovermode="x unified")
    if faixas and variavel.eh_indice and len(df.columns) > 1:
        maximo = df.drop(columns="Data").max().max()
        _faixas_fundo(fig, faixas, maximo if maximo == maximo else 50)
    _base(fig, titulo, 420, legenda=True)
    _eixo_data(fig, df["Data"], horario=_horario(df))
    return fig


# =============================================================================
# Padrões no tempo
# =============================================================================
def linha_hora(df: pd.DataFrame, v) -> go.Figure:
    """Média de cada hora do dia (0 a 23 h)."""
    cor = cor_parametro(v.parametro.codigo)
    fig = go.Figure(go.Scatter(
        x=df["hora"], y=df["media"], mode="lines+markers", name=v.rotulo,
        line=dict(color=cor, width=2), marker=dict(size=8, color=cor, line=dict(color="white", width=1.5)),
        customdata=df["n"], hovertemplate="%{x}h: média %{y:,.1f}<br>%{customdata:,d} registros<extra></extra>",
    ))
    fig.update_xaxes(title_text="Hora do dia", dtick=3, range=[-0.5, 23.5])
    fig.update_yaxes(title_text=v.titulo_eixo)  # o título do gráfico já diz "Média"
    return _base(fig, f"Média por hora do dia — {v.rotulo}", 340)


def barras(df: pd.DataFrame, eixo_x: str, v, titulo_x: str, titulo: str) -> go.Figure:
    """Barras de média por categoria (dia da semana, mês do ano...)."""
    fig = go.Figure(go.Bar(
        x=df[eixo_x].astype(str), y=df["media"], name=v.rotulo,
        marker=dict(color=cor_parametro(v.parametro.codigo)), customdata=df["n"],
        hovertemplate="%{x}: média %{y:,.1f}<br>%{customdata:,d} registros<extra></extra>",
    ))
    fig.update_xaxes(title_text=titulo_x)
    fig.update_yaxes(title_text=v.titulo_eixo, rangemode="tozero")  # barras começam no zero; "Média" já está no título
    fig.update_layout(bargap=0.28)
    return _base(fig, titulo, 340)


def barras_mensais(df: pd.DataFrame, v) -> go.Figure:
    """Média de cada mês do calendário (ex.: jul/24 e jul/25 separados)."""
    rotulos = [f"{MESES_ABREV[d.month - 1]}/{str(d.year)[2:]}" for d in df["mes"]]
    fig = go.Figure(go.Bar(
        x=rotulos, y=df["media"], name=v.rotulo, marker=dict(color=cor_parametro(v.parametro.codigo)),
        customdata=df["n"], hovertemplate="%{x}: média %{y:,.1f}<br>%{customdata:,d} registros<extra></extra>",
    ))
    fig.update_xaxes(title_text="Mês")
    # O título do gráfico já diz "Média de cada mês"; o eixo mostra só o indicador e a unidade,
    # para o texto caber na altura do gráfico.
    fig.update_yaxes(title_text=v.titulo_eixo, rangemode="tozero")
    fig.update_layout(bargap=0.2)
    return _base(fig, f"Média de cada mês — {v.rotulo}", 340)


def calendario(df: pd.DataFrame, v) -> go.Figure:
    """Mapa de calor: cada linha é um mês, cada coluna um dia; a cor é a média do dia."""
    df = df.copy()
    df["linha"] = [f"{MESES_ABREV[m - 1]}/{str(a)[2:]}" for a, m in zip(df["ano"], df["mes"])]
    ordem = list(dict.fromkeys(df["linha"]))  # mantém a ordem cronológica sem repetir
    tabela = df.pivot_table(index="linha", columns="dia", values="valor", aggfunc="mean", dropna=False).reindex(index=ordem, columns=range(1, 32))
    sufixo = "" if v.eh_indice else f" {v.unidade}"
    textos = [[("" if pd.isna(tabela.loc[l, d]) else f"{d:02d} {l}: {numero(tabela.loc[l, d])}{sufixo}") for d in tabela.columns] for l in tabela.index]
    fig = go.Figure(go.Heatmap(
        z=tabela.to_numpy(), x=list(tabela.columns), y=ordem, text=textos, hovertemplate="%{text}<extra></extra>",
        colorscale=ESCALA_SEQUENCIAL, xgap=2, ygap=2,
        colorbar=dict(title=dict(text="índice" if v.eh_indice else v.unidade, side="right"), thickness=12, outlinewidth=0),
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)  # primeiro mês no topo
    fig.update_xaxes(title_text="Dia do mês", dtick=1, showgrid=False, tickfont=dict(size=11))
    return _base(fig, f"Calendário — média diária de {v.rotulo}", max(320, 18 * len(ordem) + 120))


def poluente_por_hora(tabela: pd.DataFrame, cores: dict[str, str]) -> go.Figure:
    """Barras empilhadas: em cada hora do dia, quantas vezes cada poluente foi o registrado."""
    fig = go.Figure()
    for poluente in sorted(tabela["poluente"].unique()):
        parte = tabela[tabela["poluente"] == poluente]
        fig.add_trace(go.Bar(
            x=parte["hora"], y=parte["horas"], name=poluente, marker=dict(color=cores.get(poluente, PRIMARIA), line=dict(color="white", width=1)),
            hovertemplate=f"{poluente} — %{{x}}h: %{{y:,d}} horas<extra></extra>",
        ))
    fig.update_layout(barmode="stack", bargap=0.15)
    fig.update_xaxes(title_text="Hora do dia", dtick=3)
    fig.update_yaxes(title_text="Quantidade de horas")
    return _base(fig, "Qual poluente teve o índice registrado em cada hora do dia", 360, legenda=True)


# =============================================================================
# Qualidade do ar (faixas)
# =============================================================================
def barras_faixas(dist: pd.DataFrame, titulo: str) -> go.Figure:
    """Barras horizontais com o percentual de registros em cada faixa (N1 a N5)."""
    fig = go.Figure(go.Bar(
        y=dist["faixa"], x=dist["percentual"], orientation="h", marker=dict(color=dist["cor"]),
        customdata=dist[["registros", "intervalo"]].to_numpy(),
        hovertemplate="%{y} (índice %{customdata[1]}): %{x:,.1f}% — %{customdata[0]:,d} registros<extra></extra>",
        text=[numero(p) + "%" for p in dist["percentual"]], textposition="outside", cliponaxis=False,
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    maximo = dist["percentual"].max()
    # Espaço extra à direita para o texto do valor não ser cortado.
    fig.update_xaxes(title_text="% dos registros com valor", range=[0, (maximo if maximo == maximo else 100) * 1.2], showgrid=True, gridcolor=GRADE)
    return _base(fig, titulo, 300)


def cobertura(tabela: pd.DataFrame, catalogo: dict) -> go.Figure:
    """Barras horizontais: percentual de horas com valor em cada variável."""
    rotulos = [catalogo[c].rotulo for c in tabela["chave"]]
    cores = [cor_parametro(catalogo[c].parametro.codigo) for c in tabela["chave"]]
    fig = go.Figure(go.Bar(
        y=rotulos, x=tabela["percentual"], orientation="h", marker=dict(color=cores),
        customdata=tabela[["horas_com_valor", "horas_no_periodo"]].to_numpy(),
        hovertemplate="%{y}: %{x:,.1f}% (%{customdata[0]:,d} de %{customdata[1]:,d} horas)<extra></extra>",
        text=[numero(p) + "%" for p in tabela["percentual"]], textposition="outside", cliponaxis=False,
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(title_text="% das horas com valor", range=[0, 110], showgrid=True, gridcolor=GRADE)
    return _base(fig, "Cobertura: em quantas horas cada variável tem valor", max(220, 46 * len(tabela) + 90))


# =============================================================================
# Distribuições
# =============================================================================
def histograma(df: pd.DataFrame, v, classes: int, referencia: pd.Series | None = None) -> go.Figure:
    """Histograma com linhas verticais da média (tracejada) e da mediana (cheia).

    ``referencia``: série completa usada para média e mediana quando ``df`` foi recortado.
    """
    serie = df[v.chave].dropna()
    base = (referencia if referencia is not None else serie).dropna()
    fig = go.Figure(go.Histogram(
        x=serie, nbinsx=classes, name=v.rotulo,
        marker=dict(color=cor_parametro(v.parametro.codigo), line=dict(color="white", width=1)),
        hovertemplate="%{x}: %{y:,d} registros<extra></extra>",
    ))
    if len(base):
        media, mediana = base.mean(), base.median()
        mediana_a_esquerda = mediana <= media  # posiciona os textos para não se sobreporem
        fig.add_vline(x=mediana, line=dict(color=TINTA, width=2), annotation_text=f"Mediana {numero(mediana)}",
                      annotation_position="top left" if mediana_a_esquerda else "top right", annotation_font=dict(size=12, color=TINTA))
        fig.add_vline(x=media, line=dict(color=TINTA, width=2, dash="dash"), annotation_text=f"Média {numero(media)}",
                      annotation_position="top right" if mediana_a_esquerda else "top left", annotation_font=dict(size=12, color=TINTA))
    fig.update_xaxes(title_text=v.titulo_eixo)
    fig.update_yaxes(title_text="Quantidade de registros")
    fig.update_layout(bargap=0.02)
    return _base(fig, f"Distribuição dos valores — {v.rotulo}", 380)


def boxplot(df: pd.DataFrame, v, agrupar: str | None) -> go.Figure:
    """Boxplot geral ou agrupado por mês do ano / dia da semana."""
    cor = cor_parametro(v.parametro.codigo)
    estilo_caixa = dict(boxpoints="outliers", marker=dict(color=cor, size=5, opacity=0.6), line=dict(color=cor, width=1.6), fillcolor="rgba(0,0,0,0.04)")
    fig = go.Figure()
    if agrupar is None:
        fig.add_trace(go.Box(y=df[v.chave], name=v.rotulo, **estilo_caixa))
    else:
        for categoria in list(df[agrupar].cat.categories):  # uma caixa por categoria, na ordem certa
            fig.add_trace(go.Box(y=df.loc[df[agrupar] == categoria, v.chave], name=str(categoria), **estilo_caixa))
    fig.update_yaxes(title_text=v.titulo_eixo)
    fig.update_layout(showlegend=False)
    return _base(fig, f"Boxplot — {v.rotulo}", 420)


def dispersao(df: pd.DataFrame, vx, vy) -> go.Figure:
    """Gráfico de dispersão: cada ponto é uma hora com valor nas duas variáveis."""
    fig = go.Figure(go.Scattergl(  # Scattergl desenha muitos pontos com rapidez
        x=df[vx.chave], y=df[vy.chave], mode="markers", name=f"{vx.rotulo} × {vy.rotulo}",
        marker=dict(size=5, color=PRIMARIA, opacity=0.35),
        hovertemplate=f"{vx.parametro.sigla}: %{{x:,.1f}}<br>{vy.parametro.sigla}: %{{y:,.1f}}<extra></extra>",
    ))
    fig.update_xaxes(title_text=vx.titulo_eixo, showgrid=True, gridcolor=GRADE)
    fig.update_yaxes(title_text=vy.titulo_eixo)
    return _base(fig, f"Dispersão: {vx.rotulo} × {vy.rotulo}", 440)


def heatmap_correlacao(matriz: pd.DataFrame, metodo: str, rotulos: dict[str, str]) -> go.Figure:
    """Mapa de calor da correlação: azul = negativa, cinza = perto de zero, laranja = positiva."""
    nomes = [rotulos.get(c, c) for c in matriz.columns]
    anotacoes = []
    for i, linha in enumerate(nomes):  # escreve o valor de r dentro de cada quadradinho
        for j, coluna in enumerate(nomes):
            valor = matriz.iloc[i, j]
            texto = "—" if pd.isna(valor) else numero(valor, 2)
            cor = "white" if (not pd.isna(valor) and abs(valor) > 0.7) else TINTA
            anotacoes.append(dict(x=coluna, y=linha, text=texto, showarrow=False, font=dict(size=12, color=cor)))
    fig = go.Figure(go.Heatmap(
        z=matriz.to_numpy(), x=nomes, y=nomes, zmin=-1, zmax=1, colorscale=ESCALA_DIVERGENTE, xgap=2, ygap=2,
        hovertemplate="%{y} × %{x}: r = %{z:.2f}<extra></extra>",
        colorbar=dict(title=dict(text="r", side="right"), thickness=12, outlinewidth=0, tickvals=[-1, -0.5, 0, 0.5, 1]),
    ))
    fig.update_layout(annotations=anotacoes)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False)
    nome = "Pearson" if metodo == "pearson" else "Spearman"
    return _base(fig, f"Matriz de correlação ({nome})", max(360, 70 * len(nomes) + 160))
