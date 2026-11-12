"""Identidade visual e componentes reutilizáveis da interface (View).

O que fica aqui
---------------
* As CORES e a FONTE do sistema (os "tokens" de design). Para mudar a cor de
  uma variável ou o verde principal, altere só este arquivo.
* Pequenos componentes usados em várias páginas: cabeçalho, faixa de
  contexto (de onde vêm os dados), faixa de indicadores, caixa de
  interpretação, explicação de gráfico e mensagens de "sem dados".
* Funções de formatação de números no padrão brasileiro (1.234,5).

Sobre ``st.markdown(..., unsafe_allow_html=True)``: o Streamlit normalmente
mostra texto simples; com essa opção ele aceita HTML, o que nos permite criar
componentes com layout próprio. Todo texto vindo de dados passa por
``html.escape`` antes, para não quebrar o HTML.
"""

from __future__ import annotations

import html  # html.escape troca < > & por códigos seguros

import streamlit as st

# --- tokens de cor -------------------------------------------------------------
TINTA = "#12262B"        # texto principal (azul-petróleo quase preto)
TINTA_2 = "#4A5B60"      # texto secundário
TINTA_MUDA = "#6F7F83"   # notas e legendas
LINHA = "#D5DFDE"        # filetes e bordas
FUNDO = "#F3F6F6"        # fundo da página
PRIMARIA = "#0F5E5A"     # verde-azulado principal (tema ambiental)
ALERTA_FUNDO = "#FFF4DC"  # fundo do aviso de dados fictícios
ALERTA_BORDA = "#C98A00"

# Uma cor FIXA por parâmetro: a cor identifica o parâmetro em qualquer gráfico.
# Os oito primeiros tons formam uma paleta testada para daltonismo (método da
# skill de visualização usada no projeto).
COR_PARAMETRO = {
    "IQAR": PRIMARIA,
    "MP2.5": "#eb6834",   # laranja
    "MP10": "#6250d6",    # violeta
    "O3": "#1baf7a",      # verde-água
    "CO": "#eda100",      # amarelo
    "CO2": "#e87ba4",     # magenta
    "NO2": "#008300",     # verde
    "TEMP": "#e34948",    # vermelho
    "UR": "#2a78d6",      # azul
    "SO2": "#8c6d46",     # marrom
    "BENZENO": "#7d8790",  # cinza
}

# Cores para séries que não são parâmetros (por exemplo, estações na
# comparação). A ordem é sempre a mesma, para que cada estação mantenha sua cor.
CORES_SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#e34948", "#eda100", "#e87ba4", "#008300"]

# Escala sequencial (uma cor, do claro ao escuro) e divergente (azul ↔ cinza ↔ laranja).
ESCALA_SEQUENCIAL = ["#eaf4f2", "#b5dbd3", "#5bb3a3", "#1d8372", "#0b4f45"]
ESCALA_DIVERGENTE = [[0.0, "#2a78d6"], [0.5, "#f1f3f2"], [1.0, "#eb6834"]]

#: Configuração da barra de ferramentas dos gráficos (esconde o logotipo do Plotly).
CONFIG_PLOTLY = {"displaylogo": False}

#: Como cada agrupamento de tempo aparece nos títulos.
DESCRICAO_AGREGACAO = {"h": "valores horários", "D": "médias diárias", "W": "médias semanais", "MS": "médias mensais"}

# Fonte tipográfica: Public Sans (gratuita, do Google Fonts). Sem internet, o
# navegador usa a próxima da lista, sem prejudicar o funcionamento.
FONTE = "'Public Sans', 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif"


def cor_parametro(codigo: str) -> str:
    """Cor fixa de um parâmetro (verde principal se não estiver cadastrado)."""
    return COR_PARAMETRO.get(codigo, PRIMARIA)


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap');

.stApp, .stMarkdown, .stMarkdown p, .stCaption, label, h1, h2, h3, h4, input, textarea,
[data-testid="stSidebar"] p, [data-testid="stExpander"] summary p {{ font-family: {FONTE}; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1280px; }}
h1 {{ font-weight: 700; letter-spacing: -0.015em; font-size: 2rem !important; padding-bottom: .1rem; }}
h2, h3 {{ font-weight: 650; letter-spacing: -0.01em; }}
[data-testid="stSidebar"] {{ border-right: 1px solid {LINHA}; }}

.marca {{ font-weight: 700; font-size: 1.05rem; line-height: 1.25; color: {TINTA}; margin: .2rem 0 .1rem; }}
.marca-sub {{ font-size: .82rem; color: {TINTA_2}; margin-bottom: .6rem; }}
.descricao {{ color: {TINTA_2}; font-size: 1.02rem; max-width: 72ch; margin: 0 0 .9rem; }}

/* faixa de contexto: de onde vêm os dados desta tela */
.contexto {{
    border-left: 3px solid {PRIMARIA}; background: #E3EEEC; color: {TINTA};
    padding: .6rem .95rem; font-size: .9rem; margin: 0 0 1.3rem; border-radius: 0 4px 4px 0; max-width: 100ch;
}}
.contexto.ficticio {{ border-left-color: {ALERTA_BORDA}; background: {ALERTA_FUNDO}; }}
.contexto .linha1 {{ font-weight: 600; }}
.contexto .linha2 {{ color: {TINTA_2}; margin-top: .15rem; }}

/* faixa de leitura: indicadores numa única barra, separados por filetes */
.faixa {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    border-top: 2px solid {TINTA}; border-bottom: 1px solid {LINHA}; margin: .3rem 0 1.4rem;
}}
.celula {{ padding: .85rem 1rem .8rem; border-left: 1px solid {LINHA}; }}
.celula:first-child {{ border-left: none; padding-left: .1rem; }}
.celula .rotulo {{ font-size: .82rem; color: {TINTA_2}; display: flex; align-items: center; gap: .4rem; }}
.celula .ponto {{ width: .6rem; height: .6rem; border-radius: 50%; display: inline-block; flex: none; }}
.celula .valor {{
    font-size: 1.9rem; font-weight: 600; letter-spacing: -0.02em; color: {TINTA};
    font-variant-numeric: tabular-nums; line-height: 1.15; margin-top: .15rem;
}}
.celula .valor.compacto {{ font-size: 1.4rem; margin-top: .35rem; }}
.celula .valor .un {{ font-size: .9rem; font-weight: 500; color: {TINTA_2}; margin-left: .25rem; letter-spacing: 0; }}
.celula .nota {{ font-size: .78rem; color: {TINTA_MUDA}; margin-top: .1rem; }}

/* selo colorido de faixa de qualidade do ar (N1 a N5) */
.selo {{ display: inline-block; padding: .05rem .45rem; border-radius: 3px; color: #fff; font-size: .78rem; font-weight: 600; }}

.interpretacao {{ background: #fff; border: 1px solid {LINHA}; border-radius: 4px; padding: .8rem 1rem .4rem; margin: .4rem 0 1.2rem; max-width: 100ch; }}
.interpretacao .titulo {{ font-weight: 650; color: {TINTA}; margin-bottom: .3rem; }}
.interpretacao ul {{ margin: 0 0 .4rem 1.1rem; padding: 0; color: {TINTA_2}; }}
.interpretacao li {{ margin-bottom: .3rem; }}

.leitura {{ font-size: .93rem; color: {TINTA_2}; max-width: 82ch; }}
.leitura strong {{ color: {TINTA}; }}
.fonte-grafico {{ font-size: .78rem; color: {TINTA_MUDA}; margin: -.6rem 0 .3rem; }}

@media (max-width: 640px) {{
    .celula {{ border-left: none; border-top: 1px solid {LINHA}; padding-left: .1rem; }}
    .celula:first-child {{ border-top: none; }}
}}
</style>
"""


def aplicar_estilo() -> None:
    """Injeta o CSS acima na página (chamado uma vez, no app.py)."""
    st.markdown(CSS, unsafe_allow_html=True)


# --- formatação no padrão brasileiro -----------------------------------------------
def numero(valor: float | None, casas: int = 1) -> str:
    """1234.5 → ``"1.234,5"``; valor ausente → ``"—"``.

    O Python formata com vírgula para milhar e ponto para decimal (padrão
    americano). Trocamos os dois usando um caractere provisório (§).
    """
    if valor is None or valor != valor:  # valor != valor só é verdade para NaN
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def inteiro(valor) -> str:
    return numero(float(valor), 0)


def percentual(valor: float | None, casas: int = 0) -> str:
    return "—" if valor is None or valor != valor else f"{numero(valor, casas)}%"


def data_br(valor) -> str:
    """Timestamp/data → ``"31/12/2025"``."""
    return valor.strftime("%d/%m/%Y")


# --- componentes ---------------------------------------------------------------------
def cabecalho(titulo: str, descricao: str) -> None:
    """Título da página e uma frase dizendo para que ela serve."""
    st.title(titulo)
    st.markdown(f'<p class="descricao">{html.escape(descricao)}</p>', unsafe_allow_html=True)


def faixa_contexto(ctx: dict) -> None:
    """Mostra, no topo de cada página, DE ONDE vêm os dados exibidos.

    Exigência do projeto: nunca apresentar uma medição de outro local como se
    tivesse sido feita dentro de Heliópolis. Por isso esta faixa diz o nome da
    estação, o município, o tipo de local, a distância e a fonte.
    """
    ficticio = ctx["localizacao"] == "ficticio"
    if ficticio:
        linha1 = "Dados fictícios, criados para fins didáticos. Não são medições e não descrevem o ar de Heliópolis."
        linha2 = f"Fonte selecionada: {ctx['fonte']}. Para dados reais, troque a fonte na barra lateral."
    else:
        distancia = ctx.get("distancia_km")
        dist_txt = f", a cerca de {numero(distancia)} km de Heliópolis em linha reta" if distancia == distancia and distancia is not None else ""
        linha1 = f"Estação {ctx['estacao']} ({ctx['municipio']}){dist_txt} — {ctx['tipo_localizacao']}."
        meta = ctx.get("metadados", {})
        arquivos = meta.get("arquivos_originais", [])
        atualizacao = ""
        if arquivos:
            publicado = max(a.get("publicado_no_portal_em", "") for a in arquivos)
            baixado = max(a.get("data_download", "") for a in arquivos)
            atualizacao = f" Arquivo publicado em {_data_iso(publicado)}; baixado em {_data_iso(baixado)}."
        inicio, fim = ctx["periodo_disponivel"]
        linha2 = f"Fonte: {ctx['fonte']}. Dados de {data_br(inicio)} a {data_br(fim)}.{atualizacao}"
    classe = "contexto ficticio" if ficticio else "contexto"
    st.markdown(
        f'<div class="{classe}"><div class="linha1">{html.escape(linha1)}</div>'
        f'<div class="linha2">{html.escape(linha2)}</div></div>',
        unsafe_allow_html=True,
    )


def _data_iso(texto: str) -> str:
    """``"2026-02-04"`` → ``"04/02/2026"`` (devolve o texto original se não for uma data)."""
    partes = str(texto).split("-")
    return f"{partes[2][:2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else str(texto)


def faixa_indicadores(itens: list[dict]) -> None:
    """Barra de indicadores. Cada item é um dicionário com as chaves:

    ``rotulo`` (obrigatório), ``valor`` (obrigatório), ``unidade``, ``nota``,
    ``cor`` (bolinha colorida que identifica a variável) e ``compacto``
    (fonte menor, para textos longos como datas).
    """
    celulas = []
    for item in itens:  # monta o HTML de cada célula
        ponto = f'<span class="ponto" style="background:{item["cor"]}"></span>' if item.get("cor") else ""
        unidade = f'<span class="un">{html.escape(item["unidade"])}</span>' if item.get("unidade") else ""
        nota = f'<div class="nota">{item["nota_html"] if item.get("nota_html") else html.escape(item.get("nota", ""))}</div>' if (item.get("nota") or item.get("nota_html")) else ""
        classe = "valor compacto" if item.get("compacto") else "valor"
        celulas.append(
            f'<div class="celula"><div class="rotulo">{ponto}{html.escape(item["rotulo"])}</div>'
            f'<div class="{classe}">{html.escape(item["valor"])}{unidade}</div>{nota}</div>'
        )
    st.markdown(f'<div class="faixa">{"".join(celulas)}</div>', unsafe_allow_html=True)


def selo_faixa(faixa) -> str:
    """HTML de um selo colorido com o nome da faixa (ex.: "N1 – Boa")."""
    if faixa is None:
        return "—"
    return f'<span class="selo" style="background:{faixa.cor}">{html.escape(faixa.rotulo)}</span>'


def interpretacoes(frases: list[str], titulo: str = "O que os dados mostram") -> None:
    """Caixa com frases calculadas automaticamente a partir dos dados."""
    itens = "".join(f"<li>{html.escape(f)}</li>" for f in frases)
    st.markdown(
        f'<div class="interpretacao"><div class="titulo">{html.escape(titulo)}</div><ul>{itens}</ul></div>',
        unsafe_allow_html=True,
    )


def explicar_grafico(o_que_mostra: str, como_ler: str, fonte: str) -> None:
    """Texto padrão abaixo de cada gráfico: fonte, o que ele mostra e como interpretar.

    Parâmetros:
        o_que_mostra: uma frase sobre o conteúdo do gráfico.
        como_ler: explicação de como interpretar (aparece numa seção expansível).
        fonte: texto de origem dos dados (veja ``texto_fonte``).
    """
    st.markdown(f'<div class="fonte-grafico">{html.escape(fonte)}</div>', unsafe_allow_html=True)
    st.caption(o_que_mostra)
    with st.expander("Como interpretar este gráfico"):
        st.markdown(como_ler)


def texto_fonte(ctx: dict) -> str:
    """Linha curta de fonte para legendas de gráfico."""
    if ctx["localizacao"] == "ficticio":
        return "Fonte: dataset fictício (didático) — não são medições."
    return f"Fonte: {ctx['fonte']} · estação {ctx['estacao']} ({ctx['municipio']}) · estação próxima, fora de Heliópolis."


def sem_dados(mensagem: str | None = None) -> None:
    """Aviso padrão para quando o recorte escolhido não tem valores."""
    st.warning(
        mensagem or (
            "Nenhum valor encontrado para os filtros atuais. Amplie o período na barra lateral, "
            "escolha outra estação ou desative a exclusão de outliers."
        ),
        icon=":material/search_off:",
    )


def leitura(texto_md: str) -> None:
    """Parágrafo curto de orientação (aceita <strong> e <em>)."""
    st.markdown(f'<div class="leitura">{texto_md}</div>', unsafe_allow_html=True)
