"""Seção "Qualidade do ar" da página Sobre os Dados (View): fonte, estações, cobertura, metodologia, qualidade e exportação.

É a página da transparência: explica de onde vêm os números, o que foi feito
com eles e quais são os limites. Reúne também a tabela detalhada e a
exportação em CSV (que na V1 ficavam em "Dados e qualidade").

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

import pandas as pd
import streamlit as st

from controllers.painel_controller import TIPOS_DADOS, Filtros, PainelController
from views import estilo, graficos, tabelas
from views.estilo import CONFIG_PLOTLY, data_br, inteiro, numero


def renderizar(ctrl: PainelController, f: Filtros, embutido: bool = False) -> None:
    """Desenha as informações da qualidade do ar: fonte, estações, cobertura, metodologia, qualidade, tabela e como obter mais dados."""
    # Parâmetros: ctrl = Controller (fornece dados e cálculos); f = filtros escolhidos na barra lateral;
    # embutido = True quando a seção é mostrada dentro de outra página (que já tem título e faixa de contexto).
    # Retorno: nada. A função apenas desenha a página na tela.
    if not embutido:
        estilo.cabecalho(
            "Sobre os dados",
            "De onde vêm os dados, quais estações foram usadas, quantas horas têm registro, o que foi feito com os "
            "valores e quais são as limitações. Aqui também é possível baixar o recorte atual.",
        )
    ctx = ctrl.contexto(f)
    if not embutido:
        estilo.faixa_contexto(ctx)

    abas = st.tabs(["Fonte", "Estações", "Cobertura", "Metodologia", "Qualidade dos dados", "Tabela e exportação", "Como obter mais dados"])

    with abas[0]:
        _fonte(ctx)
    with abas[1]:
        _estacoes(ctrl, f)
    with abas[2]:
        cob = ctrl.cobertura(f.fonte, f.estacao)
        st.plotly_chart(graficos.cobertura(cob, ctrl.catalogo(f.fonte)), width="stretch", config=CONFIG_PLOTLY)
        estilo.explicar_grafico(
            f"Percentual de horas com valor para cada indicador da estação {ctx['estacao']}, em todo o período do arquivo.",
            "100% significaria um valor em todas as horas. Barras curtas indicam muitas lacunas: médias e padrões desses "
            "indicadores devem ser lidos com cautela. As lacunas NÃO são preenchidas na versão original dos dados.",
            estilo.texto_fonte(ctx),
        )
    with abas[3]:
        _metodologia(ctrl, f, ctx)
    with abas[4]:
        _qualidade(ctrl, f)
    with abas[5]:
        _tabela(ctrl, f)
    with abas[6]:
        _como_obter()


def _fonte(ctx: dict) -> None:
    """Origem, licença, arquivos originais e aviso da fonte."""
    meta = ctx["metadados"]
    if ctx["localizacao"] == "ficticio":
        st.markdown(
            "Esta fonte é o **conjunto fictício** da primeira versão do projeto, mantido para demonstração e prática. "
            "Os valores foram gerados para fins didáticos e **não são medições**."
        )
        return
    st.markdown(f"**Fonte:** {meta.get('fonte', ctx['fonte'])}")
    if meta.get("orgao_responsavel_pelas_medicoes"):
        st.markdown(f"**Responsável pelas medições:** {meta['orgao_responsavel_pelas_medicoes']}")
    if meta.get("pagina_do_conjunto"):
        st.markdown(f"**Página oficial do conjunto de dados:** {meta['pagina_do_conjunto']}")
    if meta.get("licenca"):
        st.markdown(f"**Licença:** {meta['licenca']}")
    if meta.get("aviso_da_fonte"):
        st.warning(f"Aviso da própria fonte: {meta['aviso_da_fonte']}", icon=":material/info:")
    arquivos = meta.get("arquivos_originais", [])
    if arquivos:
        st.markdown("**Arquivos oficiais usados** (o SHA-256 permite conferir que o arquivo é idêntico ao do portal):")
        st.dataframe(
            pd.DataFrame(arquivos).rename(columns={
                "nome": "Arquivo", "url": "Endereço", "publicado_no_portal_em": "Publicado em", "bytes": "Tamanho (bytes)",
                "sha256": "SHA-256", "data_download": "Baixado em", "linhas_mantidas": "Linhas usadas",
            }),
            hide_index=True, width="stretch",
        )
    st.markdown(
        "**O que estes dados são:** para as estações da CETESB, o arquivo do MonitorAr traz o **Índice de Qualidade do "
        "Ar (IQAr)**, e não a concentração dos poluentes. Também não traz temperatura nem umidade. Por isso essas "
        "informações aparecem como indisponíveis, em vez de serem estimadas."
    )


def _estacoes(ctrl: PainelController, f: Filtros) -> None:
    """Tabela e mapa das estações da fonte, com a referência de Heliópolis."""
    tabela = ctrl.estacoes(f.fonte)
    st.dataframe(tabelas.estacoes(tabela), hide_index=True, width="stretch")
    ref = ctrl.referencia_heliopolis
    st.caption(
        f"Distâncias em linha reta até o ponto de referência de Heliópolis ({numero(ref.latitude, 5)}, "
        f"{numero(ref.longitude, 5)}). Fonte do ponto: {ref.fonte} Coordenadas das estações: "
        f"{tabela['fonte_localizacao'].iloc[0]}."
    )
    com_coordenadas = tabela.dropna(subset=["latitude", "longitude"])
    if not com_coordenadas.empty:
        pontos = pd.DataFrame({
            "latitude": [*com_coordenadas["latitude"], ref.latitude],
            "longitude": [*com_coordenadas["longitude"], ref.longitude],
            "cor": ["#0F5E5A"] * len(com_coordenadas) + ["#eb6834"],
            "tamanho": [140] * len(com_coordenadas) + [220],
        })
        st.map(pontos, latitude="latitude", longitude="longitude", color="cor", size="tamanho")
        st.caption("Verde: estações. Laranja: ponto de referência de Heliópolis. O fundo do mapa precisa de internet para aparecer.")
    st.info(
        "Nenhuma estação oficial fica dentro de Heliópolis. A estação de São Caetano do Sul (código 86 no QUALAR, "
        "segundo o pacote qualR) não aparecia entre as 62 estações ativas do serviço da CETESB consultado em "
        "08/11/2026, e não existe estação chamada “Ipiranga” na rede da Região Metropolitana.",
        icon=":material/location_on:",
    )


def _metodologia(ctrl: PainelController, f: Filtros, ctx: dict) -> None:
    """Lista de transformações aplicadas, gerada pelo próprio sistema durante a leitura."""
    st.markdown("**Transformações registradas na leitura dos dados** (geradas automaticamente pelo sistema):")
    for item in ctx["transformacoes"]:
        st.markdown(f"- {item}")
    st.markdown(
        f"""
**Processamento feito pelo painel**

- **Versão original (padrão):** os valores exatamente como no arquivo; horas sem registro ficam vazias.
- **Versão tratada (opcional):** lacunas de até {ctrl.limite_lacuna} horas seguidas são estimadas por interpolação
  temporal (linha reta entre o valor anterior e o seguinte). Lacunas maiores continuam vazias. Medianas **não** são
  usadas para preencher lacunas.
- **Outliers:** sinalizados pela regra do IQR (fator {numero(ctrl.fator_iqr)}), nunca removidos automaticamente.
- **Médias por dia, semana ou mês:** usam só as horas com registro.
- **Correlação:** calculada apenas com pelo menos 30 horas em comum entre os dois indicadores.
- **Faixas de qualidade do ar:** tabela da CETESB (Resolução CONAMA nº 491/2018), aplicada ao índice. Concentrações
  só são classificadas quando a unidade é confirmada, usando o período de média oficial de cada poluente.
- **Estações nunca são misturadas:** cada análise usa uma estação; a comparação mostra estações lado a lado.
"""
    )


def _qualidade(ctrl: PainelController, f: Filtros) -> None:
    """Integridade dos dados da estação (inclui a comparação original × tratado da V1)."""
    r = ctrl.relatorio_integridade(f)
    st.caption("Esta seção descreve todos os dados da estação escolhida, sem aplicar o filtro de período.")
    estilo.faixa_indicadores([
        {"rotulo": "Horas na tabela", "valor": inteiro(r.n_linhas), "nota": f"{data_br(r.inicio)} a {data_br(r.fim)}"},
        {"rotulo": "Indicadores", "valor": inteiro(len(r.colunas))},
        {"rotulo": "Horas sem nenhum valor", "valor": inteiro(r.horas_sem_nenhum_valor)},
        {"rotulo": "Valores preenchidos (versão tratada)", "valor": inteiro(sum(r.imputados_por_coluna.values())), "nota": f"lacunas de até {ctrl.limite_lacuna} h"},
    ])
    for alerta in r.alertas:
        st.warning(alerta, icon=":material/info:")
    rotulo = lambda c: ctrl.rotulo(f.fonte, c)  # noqa: E731
    st.markdown("##### Lacunas por indicador")
    st.dataframe(pd.DataFrame({
        "Indicador": [rotulo(c) for c in r.colunas],
        "Horas sem valor (original)": [inteiro(r.nulos_por_coluna[c]) for c in r.colunas],
        "% das horas": [numero(r.nulos_por_coluna[c] / r.n_linhas * 100, 1) for c in r.colunas],
        "Maior lacuna (horas seguidas)": [inteiro(r.maior_lacuna_horas[c]) for c in r.colunas],
        "Preenchidas na versão tratada": [inteiro(r.imputados_por_coluna[c]) for c in r.colunas],
    }), hide_index=True, width="stretch")
    if not ctrl.sem_dados(f):
        st.markdown("##### Original × tratado (período escolhido)")
        st.dataframe(tabelas.comparacao(ctrl.comparar_original_tratado(f), rotulo), hide_index=True, width="stretch")
        estilo.leitura(
            "A versão tratada só difere da original onde lacunas curtas foram estimadas. Se médias e medianas mudam "
            "pouco, o tratamento não altera as conclusões; o que muda é a quantidade de registros."
        )


def _tabela(ctrl: PainelController, f: Filtros) -> None:
    """Tabela detalhada do recorte atual e botão de exportação em CSV."""
    colunas = ctrl.colunas(f)
    escolhidas = st.multiselect("Indicadores", colunas, default=colunas, format_func=lambda c: ctrl.rotulo(f.fonte, c), key="tabela_colunas")
    marcacoes = st.checkbox(
        "Incluir colunas de marcação (outlier_* e n_imputados)", value=False, key="tabela_marcacoes",
        help="Colunas verdadeiro/falso dos valores sinalizados pelo IQR e quantos valores foram preenchidos em cada hora.",
    )
    if not escolhidas:
        st.info("Escolha ao menos um indicador.")
        return
    tabela = ctrl.tabela_detalhada(f, escolhidas, marcacoes)
    if tabela.empty:
        estilo.sem_dados()
        return
    st.caption(
        f"{inteiro(len(tabela))} horas · dados {TIPOS_DADOS[f.dados].lower()}"
        + (" · outliers ignorados" if f.excluir_outliers else "")
        + ". As colunas estação, município, tipo de local e fonte acompanham o arquivo exportado."
    )
    st.dataframe(tabela, hide_index=True, width="stretch", height=380)
    st.download_button(
        "Baixar CSV do recorte atual", data=ctrl.exportar_csv(f, escolhidas, marcacoes),
        file_name="heliopolis_recorte.csv", mime="text/csv", icon=":material/download:", key="baixar_csv",
    )
    st.caption("Formato: separador “;” e ponto como separador decimal. Células vazias = hora sem registro.")


def _como_obter() -> None:
    """Resumo do procedimento para obter dados oficiais adicionais."""
    st.markdown(
        """
**Atualizar os dados do MonitorAr (sem login)**

1. Acesse o Portal de Dados Abertos do MMA, conjunto “Sistema Nacional de Gestão da Qualidade do Ar – MonitorAr”.
2. Baixe os arquivos anuais `dados_monitorar_AAAA.zip` desejados.
3. Na pasta do projeto, rode: `python scripts/preparar_dados_monitorar.py CAMINHO/dados_monitorar_2024.zip CAMINHO/dados_monitorar_2025.zip`
4. Reinicie o painel.

**Obter concentrações (µg/m³, ppm) e meteorologia pelo QUALAR (exige cadastro gratuito)**

1. Acesse o QUALAR da CETESB e faça login (ou cadastre-se).
2. Em *Consultas → Exportar dados*, escolha a estação, o parâmetro, o período e o tipo “Média horária”.
3. Exporte em CSV e salve o arquivo na pasta `data/qualar` do projeto (um arquivo por consulta).
4. Reinicie o painel: aparecerá a fonte “Dados reais — QUALAR importado”.

O passo a passo completo, com os códigos das estações, está em `docs/FONTES_DE_DADOS.md`.
"""
    )
