"""Gráficos dos termômetros da comunidade e do mapa de Heliópolis (View).

Segue as mesmas regras de ``views/graficos.py`` (título em português, unidade
nos eixos, números no padrão brasileiro, cores fixas) e reaproveita as funções
de acabamento de lá (``_base`` e ``_eixo_data``).

Cores: cada termômetro tem SEMPRE a mesma cor em todos os gráficos, definida
pela sua posição na lista completa (T1 = azul, T2 = laranja...). Assim o usuário
reconhece o termômetro pela cor de uma tela para outra.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from views.estilo import CORES_SERIES, LINHA, PRIMARIA, TINTA, numero
from views.graficos import GRADE, _base, _eixo_data

# Cores das quebradas no mapa (tons suaves, distintos entre si e legíveis em cima do mapa).
CORES_QUEBRADAS = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#e34948", "#eda100", "#e87ba4", "#008300"]
COR_PROJETOS = "#12262B"
COR_ESTACOES = "#8c6d46"


def cores_termometros(nomes: list[str]) -> dict[str, str]:
    """Dicionário nome → cor, na ordem da lista COMPLETA de termômetros."""
    return {nome: CORES_SERIES[i % len(CORES_SERIES)] for i, nome in enumerate(nomes)}


def _hover(unidade: str) -> str:
    return f"%{{y:,.1f}} {unidade}<extra>%{{fullData.name}}</extra>"


# =============================================================================
# Termômetros
# =============================================================================
def linhas_termometros(serie: pd.DataFrame, unidade: str, titulo: str, cores: dict[str, str], eixo_y: str) -> go.Figure:
    """Uma linha por termômetro ao longo do tempo.

    Parâmetros:
        serie: índice = data/hora; uma coluna por termômetro (nome de exibição).
        unidade: "°C" ou "%". eixo_y: texto do eixo vertical.
        cores: cor de cada termômetro (``cores_termometros``).
    """
    fig = go.Figure()
    for nome in serie.columns:
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie[nome], mode="lines", name=nome, connectgaps=False,  # lacunas ficam visíveis
            line=dict(color=cores.get(nome, PRIMARIA), width=1.8), hovertemplate=_hover(unidade),
        ))
    fig.update_yaxes(title_text=eixo_y)
    fig.update_layout(hovermode="x unified")
    _base(fig, titulo, 400, legenda=True)
    horario = len(serie.index) > 1 and (serie.index[1] - serie.index[0]) < pd.Timedelta(days=1)
    _eixo_data(fig, pd.Series(serie.index), horario=horario)
    return fig


def faixa_diaria(extremos: pd.DataFrame, nome: str, cor: str, unidade: str, eixo_y: str) -> go.Figure:
    """Mínimo, média e máximo de cada dia de UM termômetro.

    A área sombreada vai do mínimo ao máximo do dia; a linha é a média do dia.
    Quanto mais larga a faixa, mais a temperatura (ou umidade) variou naquele dia.
    """
    d = extremos[extremos["nome"] == nome]
    fig = go.Figure()
    # Truque do Plotly para área entre duas linhas: desenha o máximo e preenche até o mínimo ("tonexty").
    fig.add_trace(go.Scatter(x=d["dia"], y=d["maximo"], mode="lines", line=dict(width=0), name="Máximo do dia",
                             hovertemplate=_hover(unidade)))
    fig.add_trace(go.Scatter(x=d["dia"], y=d["minimo"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=_transparente(cor, 0.22), name="Mínimo do dia", hovertemplate=_hover(unidade)))
    fig.add_trace(go.Scatter(x=d["dia"], y=d["media"], mode="lines", line=dict(color=cor, width=2), name="Média do dia",
                             hovertemplate=_hover(unidade)))
    fig.update_yaxes(title_text=eixo_y)
    fig.update_layout(hovermode="x unified")
    _base(fig, f"{nome}: mínimo, média e máximo de cada dia", 380, legenda=True)
    _eixo_data(fig, d["dia"])
    return fig


def intervalo_por_termometro(resumo: pd.DataFrame, prefixo: str, unidade: str, cores: dict[str, str], titulo: str) -> go.Figure:
    """Para cada termômetro, uma barra do MÍNIMO ao MÁXIMO com um ponto na MÉDIA.

    Permite comparar, numa olhada, onde cada local fica mais quente/frio e
    quanto ele varia no período.
    """
    fig = go.Figure()
    for _, linha in resumo.iterrows():
        cor = cores.get(linha["nome"], PRIMARIA)
        fig.add_trace(go.Scatter(
            x=[linha[f"{prefixo}_min"], linha[f"{prefixo}_max"]], y=[linha["nome"]] * 2, mode="lines+markers",
            line=dict(color=cor, width=6), marker=dict(size=10, color=cor, symbol="line-ns-open"),
            showlegend=False, hovertemplate=f"%{{x:,.1f}} {unidade}<extra>{linha['nome']}</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[linha[f"{prefixo}_media"]], y=[linha["nome"]], mode="markers+text",
            marker=dict(size=14, color="white", line=dict(color=cor, width=3)),
            text=[f"média {numero(linha[f'{prefixo}_media'])}"], textposition="top center",
            textfont=dict(size=12, color=TINTA), showlegend=False,
            hovertemplate=f"Média: %{{x:,.1f}} {unidade}<extra>{linha['nome']}</extra>",
        ))
    fig.update_xaxes(title_text=unidade, showgrid=True, gridcolor=GRADE)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return _base(fig, titulo, 110 + 62 * len(resumo))


def perfil_horario(tabela: pd.DataFrame, unidade: str, cores: dict[str, str], eixo_y: str, titulo: str) -> go.Figure:
    """"Dia típico": média de cada hora do dia (0h–23h), uma linha por termômetro."""
    fig = go.Figure()
    for nome in tabela.columns:
        fig.add_trace(go.Scatter(
            x=tabela.index, y=tabela[nome], mode="lines+markers", name=nome, marker=dict(size=5),
            line=dict(color=cores.get(nome, PRIMARIA), width=2), hovertemplate=_hover(unidade),
        ))
    fig.update_xaxes(title_text="Hora do dia", tickmode="array", tickvals=list(range(0, 24, 2)),
                     ticktext=[f"{h}h" for h in range(0, 24, 2)])
    fig.update_yaxes(title_text=eixo_y)
    fig.update_layout(hovermode="x unified")
    return _base(fig, titulo, 380, legenda=True)


def barras_mensais(tabela: pd.DataFrame, unidade: str, cores: dict[str, str], eixo_y: str, titulo: str) -> go.Figure:
    """Média de cada mês, barras agrupadas por termômetro (comparação de períodos)."""
    meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    fig = go.Figure()
    for nome, grupo in tabela.groupby("nome", sort=False):
        rotulos = [f"{meses[m.month - 1]}/{str(m.year)[2:]}" for m in grupo["mes"]]
        fig.add_trace(go.Bar(
            x=rotulos, y=grupo["media"], name=nome, marker_color=cores.get(nome, PRIMARIA),
            customdata=grupo["leituras"],
            hovertemplate=f"%{{y:,.1f}} {unidade} (%{{customdata:,d}} leituras)<extra>{nome}</extra>",
        ))
    fig.update_yaxes(title_text=eixo_y)
    fig.update_layout(barmode="group", bargap=0.25)
    return _base(fig, titulo, 380, legenda=True)


def dispersao_temp_umid(dados: pd.DataFrame, nome: str, cor: str) -> go.Figure:
    """Cada ponto é uma hora: temperatura (eixo X) × umidade (eixo Y)."""
    fig = go.Figure(go.Scattergl(
        x=dados["temperatura_c"], y=dados["umidade_pct"], mode="markers", name=nome,
        marker=dict(size=4, color=cor, opacity=0.3),
        hovertemplate="Temperatura %{x:,.1f} °C<br>Umidade %{y:,.1f} %<extra></extra>",
    ))
    fig.update_xaxes(title_text="Temperatura (°C)", showgrid=True, gridcolor=GRADE)
    fig.update_yaxes(title_text="Umidade relativa (%)")
    return _base(fig, f"Temperatura × umidade — {nome} (média de cada hora)", 420)


def histogramas(dados: pd.DataFrame, coluna: str, nomes: dict[str, str], cores: dict[str, str], unidade: str, titulo: str) -> go.Figure:
    """Distribuição dos valores (quantas leituras em cada faixa), um contorno por termômetro."""
    fig = go.Figure()
    for tid, grupo in dados.groupby("termometro_id", sort=False):
        nome = nomes[tid]
        fig.add_trace(go.Histogram(
            x=grupo[coluna], name=nome, histnorm="percent", xbins=dict(size=1 if unidade == "°C" else 2.5),
            marker=dict(color=_transparente(cores.get(nome, PRIMARIA), 0.45), line=dict(color=cores.get(nome, PRIMARIA), width=1)),
            hovertemplate=f"%{{x}} {unidade}: %{{y:.1f}}% das leituras<extra>{nome}</extra>",
        ))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text=unidade)
    fig.update_yaxes(title_text="% das leituras")
    return _base(fig, titulo, 400, legenda=True)


def caixas(dados: pd.DataFrame, coluna: str, nomes: dict[str, str], cores: dict[str, str], unidade: str, titulo: str) -> go.Figure:
    """Boxplot por termômetro (mediana, quartis e valores extremos)."""
    fig = go.Figure()
    for tid, grupo in dados.groupby("termometro_id", sort=False):
        nome, cor = nomes[tid], cores.get(nomes[tid], PRIMARIA)
        fig.add_trace(go.Box(
            y=grupo[coluna], name=nome, boxpoints=False, line=dict(color=cor, width=1.6),
            fillcolor=_transparente(cor, 0.15),
        ))
    fig.update_yaxes(title_text=unidade)
    fig.update_layout(showlegend=False)
    return _base(fig, titulo, 420)


def _transparente(cor_hex: str, opacidade: float) -> str:
    """"#2a78d6" + 0.2 → "rgba(42,120,214,0.2)" (mesma cor, mais clara)."""
    cor_hex = cor_hex.lstrip("#")
    r, g, b = (int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{opacidade})"


# =============================================================================
# Mapa
# =============================================================================
def mapa_heliopolis(
    recorte: list[dict], quebradas: list[dict], glebas: list[dict] | None, projetos: pd.DataFrame | None,
    estacoes: pd.DataFrame | None, centro: tuple[float, float], destaque: str | None = None,
    com_fundo: bool = True, zoom: float = 14.2,
) -> go.Figure:
    """Mapa interativo com as camadas escolhidas.

    Parâmetros:
        recorte, quebradas, glebas: listas de ``MapaController.contornos(...)``.
        projetos: tabela de projetos (ou None para esconder).
        estacoes: estações de qualidade do ar (ou None para esconder).
        centro: (lon, lat) do centro do mapa.
        destaque: nome da quebrada selecionada (fica mais forte, as outras mais claras).
        com_fundo: True usa o mapa de ruas (OpenStreetMap, precisa de internet);
            False mostra só as camadas sobre fundo branco (funciona sem internet).

    Como é desenhado: cada polígono vira uma linha fechada (``Scattermap`` com
    ``fill="toself"``), o que permite cor de preenchimento, borda e nome no balão.
    """
    fig = go.Figure()
    for item in recorte:
        for contorno in item["contornos"]:
            lon, lat = zip(*contorno)
            fig.add_trace(go.Scattermap(
                lon=lon, lat=lat, mode="lines", line=dict(color=TINTA, width=3), name="Recorte de Heliópolis",
                hoverinfo="skip", showlegend=False,
            ))
    if glebas:
        for i, item in enumerate(glebas):
            for contorno in item["contornos"]:
                lon, lat = zip(*contorno)
                fig.add_trace(go.Scattermap(
                    lon=lon, lat=lat, mode="lines", line=dict(color="#6F7F83", width=1.2),
                    name="Glebas", legendgroup="glebas", showlegend=i == 0, hoverinfo="text",
                    text=f"{item['nome']} · {numero((item['area_m2'] or 0) / 10_000, 1)} hectares",
                ))
    for i, item in enumerate(quebradas):
        cor = CORES_QUEBRADAS[i % len(CORES_QUEBRADAS)]
        apagada = destaque is not None and item["nome"] != destaque
        for contorno in item["contornos"]:
            lon, lat = zip(*contorno)
            fig.add_trace(go.Scattermap(
                lon=lon, lat=lat, mode="lines", fill="toself", name=item["nome"],
                fillcolor=_transparente(cor, 0.08 if apagada else (0.45 if destaque else 0.28)),
                line=dict(color=cor, width=1.5 if apagada else 3),
                hoverinfo="text", text=f"Quebrada {item['nome']} · {numero((item['area_m2'] or 0) / 1_000_000, 2)} km²",
            ))
    # Rótulos com o nome de cada quebrada, no centro aproximado.
    fig.add_trace(go.Scattermap(
        lon=[q["centro"][0] for q in quebradas], lat=[q["centro"][1] for q in quebradas], mode="text",
        text=[q["nome"] for q in quebradas], textfont=dict(size=12, color=TINTA), hoverinfo="skip", showlegend=False,
    ))
    if projetos is not None and not projetos.empty:
        fig.add_trace(go.Scattermap(
            lon=projetos["longitude"], lat=projetos["latitude"], mode="markers", name="Projetos da UNAS",
            marker=dict(size=10, color=COR_PROJETOS), customdata=projetos[["nome", "tipo", "quebrada"]],
            hovertemplate="<b>%{customdata[0]}</b><br>Tipo: %{customdata[1]}<br>Quebrada: %{customdata[2]}<extra></extra>",
        ))
    if estacoes is not None and not estacoes.empty:
        fig.add_trace(go.Scattermap(
            lon=estacoes["longitude"], lat=estacoes["latitude"], mode="markers+text", name="Estações de qualidade do ar (CETESB)",
            marker=dict(size=13, color=COR_ESTACOES), text=estacoes["estacao"], textposition="top right",
            customdata=estacoes[["estacao", "distancia_km"]],
            hovertemplate="<b>Estação %{customdata[0]}</b><br>%{customdata[1]:.1f} km de Heliópolis<extra></extra>",
        ))
    fig.update_layout(
        map=dict(style="open-street-map" if com_fundo else "white-bg", center=dict(lon=centro[0], lat=centro[1]), zoom=zoom),
        height=620, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.85)",
                    bordercolor=LINHA, borderwidth=1, font=dict(size=12)),
        separators=",.",
    )
    return fig
