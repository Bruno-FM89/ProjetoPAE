"""Página "Mapa de Heliópolis" (View).

Usa os arquivos geográficos da UNAS (convertidos por
``scripts/preparar_dados_geograficos.py``) para mostrar:

* o contorno de Heliópolis (recorte usado pela UNAS);
* as 7 quebradas (sub-regiões), com nome e área;
* as glebas (divisão fundiária), se o usuário quiser;
* os projetos e equipamentos da UNAS (pontos), filtráveis por tipo;
* as estações de qualidade do ar da CETESB, para mostrar que ficam FORA do bairro.

Termômetros: por privacidade, não há pontos de termômetros. A página informa
em qual quebrada cada um está, e só destaca essa quebrada como "com termômetro"
quando a UNAS validou a informação.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from controllers.sistema import Sistema
from services.conectividade import tem_internet
from views import estilo
from views import graficos_comunidade as gc
from views.estilo import CONFIG_PLOTLY, inteiro, numero, percentual

CAMADAS = {
    "glebas": "Glebas",
    "projetos": "Projetos da UNAS",
    "estacoes": "Estações de qualidade do ar",
}
TODAS = "(todas as quebradas)"


@st.cache_data(ttl=300, show_spinner=False)
def _internet() -> bool:
    """Guarda o resultado do teste de internet por 5 minutos (evita testar a cada clique)."""
    return tem_internet()


def renderizar(sistema: Sistema) -> None:
    """Desenha a página do mapa: controles, mapa, detalhes da quebrada escolhida, termômetros e tabelas."""
    estilo.cabecalho(
        "Mapa de Heliópolis",
        "Veja as quebradas de Heliópolis, os projetos da UNAS e onde ficam as estações de qualidade do ar. "
        "Escolha uma quebrada para ver as informações dela.",
    )
    mapa = sistema.mapa
    if mapa is None:
        st.error("Os arquivos do mapa não foram encontrados. " + sistema.erros.get("mapa", ""), icon=":material/error:")
        st.caption("Como resolver: veja o GUIA_MANUTENCAO.md, seção “Atualizar os mapas”.")
        return

    st.markdown(
        '<div class="contexto"><div class="linha1">Mapa feito com os arquivos geográficos da UNAS (quebradas, recorte, '
        'glebas e projetos, 2019–2020).</div><div class="linha2">Como usar: 1) escolha o que mostrar; 2) escolha uma '
        "quebrada para destacá-la; 3) passe o mouse sobre o mapa para ver nomes. Para aproximar ou afastar, use os "
        "botões + e − que aparecem no canto de cima do mapa (no celular, use dois dedos); arraste para mover.</div></div>",
        unsafe_allow_html=True,
    )

    quebradas = mapa.quebradas()
    with st.container(border=True):
        col1, col2 = st.columns([3, 2], vertical_alignment="bottom")
        with col1:
            camadas = st.pills(
                "1. O que mostrar além das quebradas", list(CAMADAS), selection_mode="multi", default=["projetos"],
                format_func=CAMADAS.get, key="mapa_camadas", persist_state="session",
                help="Clique para ligar ou desligar cada camada do mapa.",
            ) or []
        with col2:
            destaque = st.selectbox(
                "2. Destacar uma quebrada", [TODAS, *quebradas["nome"]], key="mapa_destaque", persist_state="session",
                help="A quebrada escolhida fica com a cor mais forte, e as informações dela aparecem abaixo do mapa.",
            )
        tipos_escolhidos = None
        if "projetos" in camadas:
            tipos = mapa.tipos_projeto()
            tipos_escolhidos = st.multiselect(
                "Tipos de projeto (deixe vazio para mostrar todos)", tipos, key="mapa_tipos", persist_state="session",
                placeholder="Todos os tipos", help="CEI = Centro de Educação Infantil; CCA = Centro para Crianças e Adolescentes.",
            )
        internet = _internet()
        fundo = st.toggle(
            "Mostrar ruas ao fundo", value=internet, key="mapa_fundo", disabled=not internet,
            help="O fundo com as ruas vem da internet (OpenStreetMap). Sem internet, o mapa mostra só as áreas da UNAS.",
        )
        if not internet:
            st.caption(":material/wifi_off: Sem internet agora: mostrando as áreas sobre fundo branco. Os dados continuam completos.")

    projetos = mapa.projetos(tipos_escolhidos) if "projetos" in camadas else None
    estacoes = mapa.estacoes_ar() if "estacoes" in camadas else None
    fig = gc.mapa_heliopolis(
        recorte=mapa.contornos("recorte"), quebradas=mapa.contornos("quebradas"),
        glebas=mapa.contornos("glebas") if "glebas" in camadas else None,
        projetos=projetos, estacoes=estacoes, centro=mapa.centro(),
        destaque=None if destaque == TODAS else destaque, com_fundo=fundo,
        zoom=11.3 if estacoes is not None and not estacoes.empty else 14.2,
    )
    # scrollZoom=False: a rodinha do mouse rola a PÁGINA (e não o mapa), para ninguém ficar "preso" no mapa.
    st.plotly_chart(fig, width="stretch", config={**CONFIG_PLOTLY, "scrollZoom": False})
    st.markdown(
        '<div class="fonte-grafico">Fonte: arquivos geográficos da UNAS (Shapefiles em SIRGAS 2000 / UTM 23S, convertidos '
        "para latitude/longitude). Fundo: © colaboradores do OpenStreetMap.</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Como interpretar este mapa"):
        st.markdown(
            "- **Linha preta grossa:** contorno de Heliópolis usado pela UNAS (recorte).\n"
            "- **Áreas coloridas:** as quebradas. Cada cor é uma quebrada; o nome aparece no centro. As quebradas mapeadas "
            "não cobrem todo o recorte: há partes do bairro sem quebrada definida nos arquivos.\n"
            "- **Linhas cinza finas:** glebas (divisão do terreno usada em processos de regularização fundiária).\n"
            "- **Pontos escuros:** projetos e equipamentos da UNAS (creches, centros para crianças, cultura, esporte...). "
            "Alguns ficam fora de Heliópolis, porque a UNAS também atua em bairros vizinhos.\n"
            "- **Pontos marrons:** estações oficiais de qualidade do ar da CETESB. Repare que todas ficam a vários "
            "quilômetros: os dados de qualidade do ar do painel **não** são medições feitas dentro de Heliópolis."
        )

    if destaque != TODAS:
        _detalhe_quebrada(mapa, quebradas, destaque)
    _termometros_no_mapa(mapa, quebradas)
    _tabelas(mapa, quebradas)


def _detalhe_quebrada(mapa, quebradas: pd.DataFrame, nome: str) -> None:
    """Informações da quebrada escolhida."""
    linha = quebradas.set_index("nome").loc[nome]
    area_total = mapa.area_recorte_km2()
    st.markdown(f"#### Quebrada {nome}")
    estilo.faixa_indicadores([
        {"rotulo": "Área", "valor": numero(linha["area_km2"], 2), "unidade": "km²",
         "nota": f"{numero(linha['area_m2'] / 10_000, 1)} hectares"},
        {"rotulo": "Parte do recorte de Heliópolis", "valor": percentual(linha["area_km2"] / area_total * 100, 1) if area_total else "—"},
        {"rotulo": "Projetos da UNAS dentro", "valor": inteiro(linha["projetos_unas"])},
        {"rotulo": "Termômetros (região confirmada)", "valor": inteiro(linha["termometros_validados"]),
         "nota": f"{inteiro(linha['termometros_a_confirmar'])} a confirmar"},
    ])
    projetos = mapa.projetos()
    dentro = projetos[projetos["quebrada"] == nome]
    if not dentro.empty:
        st.dataframe(dentro[["nome", "tipo"]].rename(columns={"nome": "Projeto", "tipo": "Tipo"}), hide_index=True, width="stretch")


def _termometros_no_mapa(mapa, quebradas: pd.DataFrame) -> None:
    """Explica a situação da localização dos termômetros (sem expor endereços)."""
    st.markdown("#### Termômetros no mapa")
    validados = quebradas[quebradas["termometros_validados"] > 0]
    a_confirmar = quebradas[quebradas["termometros_a_confirmar"] > 0]
    if validados.empty:
        st.info(
            "Ainda não há termômetros com região confirmada pela UNAS, por isso nenhum aparece no mapa. "
            "Por privacidade, o mapa nunca mostra a casa exata: no máximo, a quebrada onde o termômetro está.",
            icon=":material/privacy_tip:",
        )
    else:
        for _, linha in validados.iterrows():
            st.markdown(f"- **{linha['nome']}:** " + ", ".join(mapa.termometros_na_quebrada(linha["nome"], True)))
    if not a_confirmar.empty:
        st.caption(
            "Região sugerida, ainda a confirmar: "
            + "; ".join(f"{q} ({', '.join(mapa.termometros_na_quebrada(q, False))})" for q in a_confirmar["nome"])
            + ". A equipe pode confirmar no arquivo data/termometros/locais_termometros.csv (veja o GUIA_MANUTENCAO.md)."
        )


def _tabelas(mapa, quebradas: pd.DataFrame) -> None:
    """Tabelas das camadas, em seções que abrem e fecham (para não poluir a tela)."""
    st.markdown("#### Tabelas do mapa")
    with st.expander("Quebradas", icon=":material/map:"):
        st.dataframe(pd.DataFrame({
            "Quebrada": quebradas["nome"],
            "Área (km²)": [numero(v, 2) for v in quebradas["area_km2"]],
            "Projetos da UNAS": quebradas["projetos_unas"],
        }), hide_index=True, width="stretch")
        area = mapa.area_recorte_km2()
        if area:
            st.caption(
                f"Área do recorte de Heliópolis: {numero(area, 2)} km². Soma das quebradas mapeadas: "
                f"{numero(quebradas['area_km2'].sum(), 2)} km². Áreas calculadas a partir das formas originais (em metros)."
            )
    glebas = mapa.glebas()
    if not glebas.empty:
        with st.expander("Glebas", icon=":material/grid_view:"):
            st.dataframe(pd.DataFrame({
                "Gleba": glebas["nome"], "Área (hectares)": [numero(v / 10_000, 2) for v in glebas["area_m2"]],
            }), hide_index=True, width="stretch")
    projetos = mapa.projetos()
    if not projetos.empty:
        with st.expander(f"Projetos da UNAS ({len(projetos)})", icon=":material/location_on:"):
            tabela = pd.DataFrame({
                "Projeto": projetos["nome"], "Tipo": projetos["tipo"], "Quebrada": projetos["quebrada"],
                "Dentro do recorte de Heliópolis": ["sim" if v else "não" for v in projetos["dentro_recorte"]],
                "Descrição": projetos["descricao"].str.replace("<br>", " ", regex=False),
            })
            st.dataframe(tabela, hide_index=True, width="stretch")
            st.download_button(
                "Baixar lista de projetos (CSV)", tabela.to_csv(index=False, sep=";").encode("utf-8"),
                file_name="projetos_unas.csv", mime="text/csv", icon=":material/download:", key="mapa_baixar_projetos",
            )
            st.caption("Descrições como estão no arquivo da UNAS (o formato limita cada texto a 254 caracteres).")
