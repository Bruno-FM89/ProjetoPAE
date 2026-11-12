"""Página "Sobre os Dados" (View).

Responde, para cada conjunto de dados: de onde veio, o que foi feito com ele,
como conferir que está certo, quais problemas foram encontrados e quais são as
limitações. Um seletor no topo escolhe o assunto:

* Termômetros da comunidade;
* Mapas (arquivos geográficos da UNAS);
* Qualidade do ar (seção da V2, ``views/ar_sobre.py``, que usa a barra lateral);
* Privacidade e limitações.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from controllers.painel_controller import Filtros
from controllers.sistema import Sistema
from views import ar_sobre, estilo
from views.estilo import inteiro, numero

ASSUNTOS = {
    "termometros": ":material/thermostat: Termômetros",
    "mapas": ":material/map: Mapas",
    "ar": ":material/air: Qualidade do ar",
    "privacidade": ":material/privacy_tip: Privacidade e limitações",
}


def assunto_escolhido() -> str:
    """Assunto escolhido (lido também pelo app.py para decidir se mostra os filtros do ar)."""
    return st.session_state.get("sobre_assunto") or "termometros"


def renderizar(sistema: Sistema, f: Filtros | None) -> None:
    """Desenha a página: seletor de assunto e o conteúdo do assunto escolhido."""
    estilo.cabecalho(
        "Sobre os Dados",
        "De onde vem cada informação do painel, o que foi feito com ela, como conferir e quais são os limites. "
        "Escolha o assunto abaixo.",
    )
    assunto = st.segmented_control(
        "Assunto", list(ASSUNTOS), format_func=ASSUNTOS.get, default="termometros",
        key="sobre_assunto", persist_state="session",
    ) or "termometros"
    if assunto == "termometros":
        _termometros(sistema)
    elif assunto == "mapas":
        _mapas(sistema)
    elif assunto == "ar":
        if sistema.painel is None or f is None:
            st.error("Dados de qualidade do ar indisponíveis. " + sistema.erros.get("qualidade_ar", ""), icon=":material/error:")
            return
        st.caption("Os filtros da barra lateral (estação e período) valem para esta parte.")
        estilo.faixa_contexto(sistema.painel.contexto(f))
        ar_sobre.renderizar(sistema.painel, f, embutido=True)
    else:
        _privacidade()


def _termometros(sistema: Sistema) -> None:
    """Origem, tratamento, conferência com o aparelho e inconsistências dos dados dos termômetros."""
    ctrl = sistema.termometros
    if ctrl is None:
        st.error("Dados dos termômetros indisponíveis. " + sistema.erros.get("termometros", ""), icon=":material/error:")
        return
    meta = ctrl.metadados
    aparelhos = meta.get("aparelhos", [])
    st.markdown(
        f"**O que é:** {meta.get('descricao', '')}\n\n"
        f"**Origem:** {meta.get('origem', '')}\n\n"
        f"**Aparelho:** registrador {aparelhos[0].get('modelo', '') if aparelhos else ''}, sensor de temperatura e umidade "
        f"embutido no aparelho, uma leitura a cada {numero(aparelhos[0].get('intervalo_observado_min', 10), 0) if aparelhos else '10'} "
        f"minutos, horário de Brasília ({aparelhos[0].get('fuso_horario', '') if aparelhos else ''}).\n\n"
        f"**Unidades:** temperatura em graus Celsius (°C); umidade relativa do ar em porcentagem (%)."
    )
    st.markdown("##### Cada termômetro")
    tabela = ctrl.tabela_termometros().set_index("id")
    st.dataframe(pd.DataFrame([{
        "Termômetro": tabela.loc[a["termometro_id"], "nome"],
        "Primeira leitura": a.get("primeira_leitura_lista", ""),
        "Última leitura": a.get("ultima_leitura_lista", ""),
        "Leituras": inteiro(a.get("leituras", 0)),
        "Interrupções na série": inteiro(a.get("lacunas_na_serie", 0)),
        "Observações da leitura": " ".join(a.get("problemas", [])) or "nenhuma",
    } for a in aparelhos]), hide_index=True, width="stretch")

    st.markdown("##### Como os dados foram tratados")
    st.markdown(
        "1. As planilhas originais foram lidas pelo script `scripts/preparar_dados_termometros.py`, aba **Lista** "
        "(número da leitura, data/hora, temperatura, umidade).\n"
        "2. Os números vinham como texto com vírgula (“28,6”) e foram convertidos para número (28.6), sem arredondar.\n"
        "3. Foram verificados: datas inválidas, horários repetidos, valores vazios, umidade fora de 0–100% e "
        "interrupções na sequência de 10 em 10 minutos. **Nenhum problema foi encontrado nas séries.**\n"
        "4. Nenhum valor foi preenchido, estimado ou removido.\n"
        "5. Os nomes dos arquivos (nomes de moradores) foram trocados por “Termômetro 1 a 5”. Endereços não entram no sistema."
    )
    st.markdown("##### Conferência: o sistema calcula o mesmo que o próprio aparelho?")
    conf = ctrl.conferencia_com_aparelho()
    total, ok = len(conf), int(conf["confere"].sum())
    (st.success if ok == total else st.warning)(
        f"{ok} de {total} valores conferem com o resumo gravado pelo aparelho (máximo, mínimo e média de cada termômetro).",
        icon=":material/fact_check:",
    )
    with st.expander("Ver a conferência completa"):
        st.dataframe(pd.DataFrame({
            "Termômetro": conf["termometro"], "Medida": conf["grandeza"], "Estatística": conf["estatistica"],
            "Calculado pelo sistema": [numero(v, 2) for v in conf["calculado_pelo_sistema"]],
            "Informado pelo aparelho": [numero(v, 1) for v in conf["informado_pelo_aparelho"]],
            "Confere": ["sim" if v else "não" for v in conf["confere"]],
        }), hide_index=True, width="stretch")
        st.caption(
            "O aparelho corta a média na primeira casa decimal (21,77 aparece como 21,7), por isso aceitamos diferenças "
            "menores que 0,1. Os valores do documento “Dados dos termômetros” da UNAS são os mesmos do resumo do aparelho."
        )
    st.markdown("##### Diferenças e inconsistências encontradas nos arquivos")
    st.markdown(
        "- Os arquivos terminam em **.xls**, mas por dentro são do formato novo do Excel (**.xlsx**). O sistema lê pelo conteúdo.\n"
        "- Os termômetros **não mediram nas mesmas datas**: um deles cobre de novembro de 2024 a junho de 2025; os demais, "
        "de fevereiro a setembro de 2025. Por isso a comparação usa, por padrão, o período em que todos mediram juntos.\n"
        "- Todos os aparelhos pararam com exatamente **32.000 leituras**, o que indica que a memória encheu; as medições "
        "posteriores, se houve, não estão nos arquivos.\n"
        "- O documento de resumo da UNAS lista 6 locais, mas há 5 planilhas; não há como saber, pelos arquivos, qual "
        "local corresponde a cada planilha sem confirmação da UNAS.\n"
        "- Ainda não foram registrados o cômodo e a altura de instalação de cada aparelho (pendência anotada pela própria UNAS)."
    )
    st.caption("Atualizar com novas planilhas: veja o GUIA_MANUTENCAO.md, seção “Atualizar os dados dos termômetros”.")


def _mapas(sistema: Sistema) -> None:
    """Origem, conversão, conferência de áreas e limitações dos arquivos geográficos."""
    mapa = sistema.mapa
    if mapa is None:
        st.error("Mapa indisponível. " + sistema.erros.get("mapa", ""), icon=":material/error:")
        return
    meta = mapa.metadados
    st.markdown(f"**Origem:** {meta.get('origem', '')}\n\n**Conversão:** {meta.get('conversao', '')}\n\n**Áreas:** {meta.get('areas', '')}")
    camadas = meta.get("camadas", [])
    if camadas:
        nomes = {"recorte": "Recorte de Heliópolis", "quebradas": "Quebradas", "glebas": "Glebas", "projetos_unas": "Projetos da UNAS (2020)"}
        st.dataframe(pd.DataFrame([{
            "Camada": nomes.get(c["camada"], c["camada"]),
            "Tipo": {"POLYGON": "áreas (polígonos)", "POINTZ": "pontos"}.get(c["tipo_geometria"], c["tipo_geometria"]),
            "Itens": c["feicoes"],
            "Sistema de coordenadas original": c["sistema_original"],
            "Arquivos do conjunto": " ".join(c["partes_presentes"]),
            "Atributos originais": ", ".join(c["atributos_originais"]),
        } for c in camadas]), hide_index=True, width="stretch")
        st.caption(
            "Um Shapefile é um conjunto de arquivos com o mesmo nome: .shp (formas), .shx (índice), .dbf (tabela), "
            ".prj (sistema de coordenadas) e .cpg (codificação do texto). Todos foram lidos juntos."
        )
    st.markdown("##### Conferência das áreas")
    conf = mapa.conferencia_areas()
    if not conf.empty:
        st.dataframe(pd.DataFrame({
            "Quebrada": conf["quebrada"],
            "Área na tabela original (m²)": [numero(v, 0) for v in conf["area_original_m2"]],
            "Área calculada pelo sistema (m²)": [numero(v, 0) for v in conf["area_calculada_m2"]],
            "Diferença (%)": [numero(v, 3) for v in conf["diferenca_pct"]],
        }), hide_index=True, width="stretch")
        st.caption("Diferenças tão pequenas mostram que as formas foram lidas corretamente (a variação vem de arredondamentos do programa de origem).")
    st.markdown("##### Limitações")
    st.markdown(
        "- Os arquivos são de **2019–2020**: limites e projetos podem ter mudado desde então.\n"
        "- As 7 quebradas mapeadas **não cobrem todo o recorte** de Heliópolis.\n"
        "- O atributo de nome do arquivo de recorte traz o texto “Cazinhas”, que não corresponde ao conteúdo (contorno de "
        "Heliópolis); por isso o sistema chama a camada de “Recorte de Heliópolis”.\n"
        "- As descrições dos projetos são cortadas em 254 caracteres (limite do formato .dbf).\n"
        "- O Drive tem outras camadas (setores censitários, logradouros, relevo, educação etc.) ainda não usadas no painel."
    )
    st.caption("Atualizar os mapas: veja o GUIA_MANUTENCAO.md, seção “Atualizar os mapas”.")


def _privacidade() -> None:
    """Regras de proteção dos dados dos moradores e limitações gerais do painel."""
    st.markdown(
        """
**Proteção de dados dos moradores**

- Os nomes dos moradores (que apareciam no nome das planilhas) foram trocados por “Termômetro 1 a 5”.
- Endereços, fotos e informações pessoais **não** entram no painel, no repositório público nem no executável.
- Os termômetros **não** aparecem como pontos no mapa. No máximo, a quebrada onde estão é indicada, e só depois de
  confirmada pela UNAS.
- As planilhas originais e a tabela que liga cada planilha ao seu número ficam só no computador da equipe
  (pasta `data/termometros/bruto/`, ignorada pelo Git).

**Limitações gerais**

- **Termômetros:** medem o ambiente onde o aparelho foi colocado (provavelmente dentro das casas), não a rua. Cinco
  casas não representam toda a comunidade. Não se sabe ainda o cômodo nem a altura de cada aparelho.
- **Qualidade do ar:** vem de estações oficiais a 6,7–9,8 km de Heliópolis; os dados do MonitorAr são automáticos e não
  validados pela fonte, e trazem o índice, não a concentração dos poluentes.
- **Mapas:** arquivos de 2019–2020.
- **Nenhum dado é inventado**: períodos sem medição aparecem vazios. O painel descreve os dados; não aponta causas
  nem faz previsões.
"""
    )
