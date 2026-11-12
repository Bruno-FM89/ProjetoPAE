"""Página "Ajuda": tutorial de uso, glossário e perguntas frequentes (View).

Todo o texto desta página é fixo e explicativo; nenhum resultado numérico é
escrito aqui (resultados vêm sempre dos cálculos, nas outras páginas).
Substitui o "Guia de interpretação" da V1, ampliado com o glossário.

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

from controllers.painel_controller import PainelController
from views import estilo
from views.estilo import numero

# Glossário: (termo, explicação em Markdown). Para acrescentar um termo,
# basta adicionar uma tupla nesta lista.
GLOSSARIO = [
    ("IQAr — Índice de Qualidade do Ar",
     "Número sem unidade que transforma a concentração de cada poluente numa escala comum. A estação é classificada "
     "pelo poluente com o maior índice. Faixas da CETESB: **0–40 Boa**, **41–80 Moderada**, **81–120 Ruim**, "
     "**121–200 Muito Ruim** e **acima de 200 Péssima**."),
    ("MP2,5 — Material Particulado Fino",
     "Partículas muito pequenas presentes no ar, com até 2,5 micrômetros (milésimos de milímetro). Por serem tão "
     "pequenas, podem penetrar profundamente no sistema respiratório."),
    ("MP10 — Material Particulado Inalável",
     "Partículas com até 10 micrômetros, como poeira e fuligem. O MP2,5 faz parte do MP10."),
    ("O₃ — Ozônio",
     "Gás que, perto do solo, se forma a partir de outros poluentes com a ajuda da luz do sol. Por isso costuma "
     "aparecer mais nas horas de sol."),
    ("CO — Monóxido de Carbono",
     "Gás sem cor e sem cheiro, produzido pela queima incompleta de combustíveis."),
    ("NO₂ — Dióxido de Nitrogênio",
     "Gás formado principalmente na queima de combustíveis, como em motores de veículos."),
    ("Temperatura do ar (°C)",
     "Indica o quanto o ar está quente ou frio, em graus Celsius. No painel, vem dos **termômetros da UNAS** instalados "
     "em casas de Heliópolis. Os dados de qualidade do ar da CETESB (MonitorAr) não trazem temperatura."),
    ("Umidade relativa do ar (%)",
     "Quanto vapor de água há no ar em comparação com o máximo possível naquela temperatura. 100% = ar saturado. "
     "Também vem dos **termômetros da UNAS**. A Defesa Civil de São Paulo considera estado de atenção quando a "
     "umidade fica entre 20% e 30%."),
    ("Amplitude",
     "Diferença entre o maior e o menor valor. Ex.: máxima de 31 °C e mínima de 16 °C → amplitude de 15 °C. "
     "Mostra o tamanho da variação."),
    ("Dia típico",
     "Média de cada hora do dia (0h a 23h), juntando todos os dias do período. Mostra o “ritmo” de um dia comum: "
     "a que horas costuma esquentar e esfriar."),
    ("Período em que todos mediram juntos",
     "Os dias em que todos os termômetros escolhidos estavam funcionando ao mesmo tempo. É a forma justa de "
     "comparar locais, porque compara as mesmas datas."),
    ("Quebrada",
     "Nome usado na comunidade para as sub-regiões de Heliópolis (ex.: Mina, Lagoa, Imperador / Pilões). O mapa "
     "mostra as 7 quebradas dos arquivos da UNAS."),
    ("Gleba",
     "Divisão do terreno usada em processos de regularização fundiária (posse e registro dos terrenos). Heliópolis "
     "tem glebas identificadas por letras (A a N)."),
    ("Recorte de Heliópolis",
     "O contorno da comunidade usado pela UNAS nos seus mapas."),
    ("Shapefile e coordenadas (SIRGAS 2000)",
     "Shapefile é o formato de mapa usado pela UNAS (um conjunto de arquivos .shp, .shx, .dbf, .prj e .cpg). As "
     "posições estavam em metros no sistema SIRGAS 2000 / UTM 23S e foram convertidas para latitude e longitude, "
     "o formato dos mapas da internet."),
    ("Média",
     "Soma de todos os valores dividida pela quantidade de valores. É sensível a valores muito altos ou muito baixos."),
    ("Mediana",
     "O valor do meio quando todos os valores são colocados em ordem. Metade dos registros fica abaixo e metade acima. "
     "É pouco afetada por valores extremos, por isso representa bem o “valor típico”."),
    ("Moda", "O valor que mais se repete. Aqui é calculada depois de arredondar os valores."),
    ("Desvio padrão",
     "Mostra o quanto os valores costumam se afastar da média. Desvio pequeno: valores parecidos entre si. "
     "Desvio grande: valores muito espalhados. Tem a mesma unidade dos dados."),
    ("Variância", "O desvio padrão elevado ao quadrado. É usada em cálculos estatísticos; para leitura, prefira o desvio padrão."),
    ("Correlação (r)",
     "Número de −1 a +1 que mede o quanto dois indicadores variam juntos. **Positiva:** quando um sobe, o outro "
     "tende a subir. **Negativa:** quando um sobe, o outro tende a descer. **Perto de zero:** sem relação linear clara. "
     "**Correlação não é causa:** dois indicadores podem variar juntos por coincidência ou por causa de um terceiro fator."),
    ("Outlier (valor atípico)",
     "Valor muito diferente dos demais. Pode ser um erro de medição ou um evento real (por exemplo, um episódio de "
     "poluição). Por isso o painel sinaliza, mas não remove."),
    ("IQR — Intervalo interquartil",
     "Distância entre o 1º quartil (Q1, abaixo do qual estão 25% dos valores) e o 3º quartil (Q3, 75%): "
     "**IQR = Q3 − Q1**. Valores abaixo de Q1 − 1,5 × IQR ou acima de Q3 + 1,5 × IQR são sinalizados como outliers."),
    ("Interpolação",
     "Estimativa de um valor ausente traçando uma linha reta entre o valor anterior e o seguinte. Só é usada na "
     "versão “tratada” e apenas em lacunas curtas. Uma interpolação é uma estimativa, não uma medição."),
    ("Estação de monitoramento",
     "Local com equipamentos que medem a qualidade do ar continuamente. Os dados representam o ar no entorno da "
     "estação; não são medições de todo o município nem de Heliópolis."),
]


def renderizar(ctrl: PainelController | None) -> None:
    """Desenha a página de ajuda: tutorial com exemplos, glossário e perguntas frequentes."""
    # Parâmetro: ctrl = Controller da qualidade do ar (usado só para calcular as distâncias citadas nas
    # perguntas frequentes; pode ser None se esses dados faltarem).
    # Retorno: nada. A função apenas desenha a página na tela.
    estilo.cabecalho(
        "Ajuda e Tutorial",
        "Como usar o painel, o significado de cada termo e respostas para as dúvidas mais comuns. Não é preciso "
        "saber programação nem estatística.",
    )
    aba_tutorial, aba_glossario, aba_duvidas = st.tabs(["Como usar", "Glossário", "Perguntas frequentes"])

    with aba_tutorial:
        st.markdown(
            """
**O painel tem 7 partes (menu à esquerda; no celular, toque em ☰ no canto de cima):**

| Parte | Para que serve |
|---|---|
| **Visão Geral** | Página inicial: resumo dos três conjuntos de dados e botões para cada assunto. |
| **Temperatura e Umidade** | Medições feitas DENTRO de Heliópolis pelos termômetros da UNAS. |
| **Qualidade do Ar** | Índice de qualidade do ar de estações oficiais próximas (fora do bairro). |
| **Mapa de Heliópolis** | Quebradas, glebas, projetos da UNAS e estações de qualidade do ar. |
| **Análise Estatística** | Médias, medianas, distribuição e relações, para quem quer se aprofundar. |
| **Sobre os Dados** | De onde vem cada dado, como foi tratado, conferências e limitações. |
| **Ajuda e Tutorial** | Esta página. |

**Exemplo 1 — Qual casa ficou mais quente?**

1. Abra **Temperatura e Umidade**.
2. Deixe todos os termômetros marcados e o período em “Quando todos mediram juntos”.
3. Em “O que você quer ver?”, escolha **Comparar termômetros**. O termômetro com o círculo mais à direita teve a
   maior temperatura média.

**Exemplo 2 — A que horas costuma esquentar?** Na mesma página, escolha **Dia típico**.

**Exemplo 3 — Como está o ar perto do bairro?** Abra **Qualidade do Ar**, escolha a estação na barra lateral
(a mais próxima vem primeiro) e leia o **Resumo do período**.

**Exemplo 4 — Onde ficam os projetos da UNAS?** Abra o **Mapa**, ligue “Projetos da UNAS” e escolha uma quebrada.

**Dicas para os gráficos**

- Passe o mouse (ou toque) sobre o gráfico para ver os valores.
- Clique num nome da legenda para esconder ou mostrar aquela linha.
- Arraste sobre o gráfico para aproximar; dê dois cliques para voltar ao normal.
- Abaixo de cada gráfico há uma frase explicando o que ele mostra e a seção **Como interpretar este gráfico**.
- O ícone **?** ao lado de cada filtro explica a opção.
- Para baixar os dados em planilha, use os botões **Baixar** (Temperatura e Umidade → Tabela e download; Sobre os
  Dados → Qualidade do ar → Tabela e exportação).
"""
        )

    with aba_glossario:
        for termo, explicacao in GLOSSARIO:  # um item expansível para cada termo
            with st.expander(termo):
                st.markdown(explicacao)

    with aba_duvidas:
        # A faixa de distâncias é calculada a partir das estações carregadas (nada escrito à mão).
        distancias = [
            d for fonte in ctrl.nomes_fontes if not ctrl.eh_ficticia(fonte)
            for d in ctrl.estacoes(fonte)["distancia_km"].dropna()
        ] if ctrl is not None else []
        trecho = (
            f", entre {numero(min(distancias))} e {numero(max(distancias))} km em linha reta," if distancias else ""
        )
        duvidas = [
            ("Onde ficam os termômetros? Por que não aparecem no mapa?",
             "Eles estão em casas de moradores. Para proteger essas famílias, o painel não mostra nomes nem endereços: "
             "os aparelhos aparecem como “Termômetro 1 a 5” e, no máximo, a quebrada onde estão é indicada, depois de "
             "confirmada pela UNAS."),
            ("Os termômetros medem a temperatura da rua?",
             "Não. Eles medem o ambiente onde foram colocados (provavelmente dentro das casas). Por isso os valores "
             "podem ser diferentes da temperatura divulgada na previsão do tempo."),
            ("Por que os termômetros têm períodos diferentes?",
             "Cada aparelho foi instalado e retirado numa data. Para comparar de forma justa, use a opção “Quando todos "
             "mediram juntos”."),
            ("Os dados mostram a qualidade do ar dentro de Heliópolis?",
             f"Não. Não há estação oficial dentro do bairro. Os dados reais vêm de estações próximas{trecho} e podem "
             "ser diferentes do que ocorre em Heliópolis."),
            ("Por que a página de Qualidade do Ar não mostra temperatura, umidade ou concentrações?",
             "Porque o arquivo oficial do MonitorAr traz, para as estações da CETESB, apenas o índice de qualidade do ar "
             "(temperatura e umidade de Heliópolis estão na página Temperatura e Umidade, vindas dos termômetros da UNAS). "
             "O painel não inventa colunas. Concentrações e meteorologia podem ser obtidas no QUALAR da CETESB "
             "(veja *Sobre os Dados → Qualidade do ar → Como obter mais dados*)."),
            ("Por que há tantas lacunas?",
             "O arquivo traz registros em parte das horas. Além disso, cada hora tem o índice de um único poluente; "
             "por isso cada poluente aparece só em algumas horas. O painel mostra as lacunas em vez de escondê-las."),
            ("Posso dizer que um poluente causou o aumento de outro?",
             "Não com estes gráficos. Eles mostram associações (correlação), não causas."),
            ("Os valores fora do padrão foram apagados?",
             "Não. São apenas sinalizados. Você pode ignorá-los nas contas marcando a opção em *Opções avançadas*."),
            ("Preciso de internet?",
             "Não para os dados: tudo fica no computador. Só o fundo de ruas do mapa e a fonte das letras vêm da internet; "
             "sem conexão, o mapa aparece sobre fundo branco."),
            ("O que é a fonte “Demonstração”?",
             "O conjunto fictício da primeira versão do projeto. Ele foi mantido para prática e está sempre "
             "identificado como fictício."),
        ]
        for pergunta, resposta in duvidas:
            with st.expander(pergunta):
                st.markdown(resposta)
