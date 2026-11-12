# Feedbacks da UNAS — registro e implementação (V4)

Este documento registra os **feedbacks efetivamente recebidos da equipe da UNAS** e o que foi feito com cada
um. Só constam aqui pedidos documentados; nada foi inventado. O status reflete o que foi **verificado** (testes
automáticos e conferência no navegador), não apenas o que foi escrito.

Legenda de status: **Implementado** (feito e verificado) · **Parcial** (feito em parte ou falta validação com a
UNAS) · **Pendente** (não feito).

## Feedbacks recebidos

| # | Pedido da UNAS (como recebido) |
|---|---|
| 1 | Tornar o site mais fácil de utilizar. |
| 2 | Deixar a interface mais explicativa, informando o que cada seção, gráfico, tabela e indicador apresenta. |
| 3 | Simplificar a navegação e as interações para pessoas com pouco conhecimento técnico. |
| 4 | Adicionar comentários simples e didáticos ao código do back-end, para facilitar seu entendimento e manutenção. |

---

## 1. Tornar o site mais fácil de utilizar

**Status: Implementado** · validação com usuários da UNAS: **pendente** (veja o fim do documento)

| Alteração | Arquivos |
|---|---|
| Nova página inicial (**Visão Geral**) com um cartão por assunto, os números principais e um botão "Abrir ..." para cada um; "Como usar em 3 passos"; atalhos para Ajuda e Sobre os Dados. | `views/pagina_inicio.py`, `app_pages/inicio.py` |
| Filtros dos termômetros **numerados** (1. Termômetros, 2. Período, 3. Mostrar os valores, 4. Medida) no topo da página, em botões visíveis (sem menus escondidos). | `views/filtros_termometros.py` |
| Período padrão "**Quando todos mediram juntos**", que já deixa a comparação justa sem a pessoa precisar entender o problema dos períodos diferentes. | `views/filtros_termometros.py`, `models/termometros.py` (`periodo_comum`) |
| Mensagens claras quando faltam dados ou nada foi escolhido ("Escolha pelo menos um termômetro clicando nos botões acima"; "Sem medições no período: Termômetro 3..."). | `views/pagina_termometros.py`, `views/estilo.py` |
| Mapa: a rodinha do mouse **rola a página** em vez de dar zoom (evita ficar "preso" no mapa); instrução de como aproximar com os botões + e −. | `views/pagina_mapa.py` |
| Mapa funciona sem internet e avisa ("Sem internet agora: mostrando as áreas sobre fundo branco"). | `services/conectividade.py`, `views/pagina_mapa.py` |
| Botões de download com nomes diretos ("Baixar esta tabela (CSV)") e explicação de como abrir no Excel. | `views/pagina_termometros.py`, `views/pagina_mapa.py` |
| Programa que abre com dois cliques, sem instalar Python. | `executavel/` |

**Evidências**
- Testes `tests/test_paginas_v4.py`: as 7 páginas abrem sem erro; os links "Abrir ..." existem na Visão Geral;
  a mensagem para escolher termômetro aparece quando nada é selecionado.
- Conferência no navegador (12/11/2026): Visão Geral, Temperatura e Umidade (Comparar e Ao longo do tempo),
  Mapa e Qualidade do Ar abertos e verificados visualmente.

## 2. Interface mais explicativa

**Status: Implementado** · validação com usuários da UNAS: **pendente**

| Alteração | Arquivos |
|---|---|
| Toda página começa com título + uma frase de objetivo + uma faixa "de onde vêm estes dados". | todos os `views/pagina_*.py` |
| Todo gráfico novo tem título, unidade no eixo, linha de fonte, uma frase "o que mostra" e a seção expansível **"Como interpretar este gráfico"**. | `views/pagina_termometros.py`, `views/pagina_estatistica.py`, `views/pagina_mapa.py` (função `estilo.explicar_grafico`) |
| Frases automáticas "**O que os dados mostram**" calculadas dos dados (ex.: "No dia típico, a temperatura costuma ser mais alta por volta das 15h e mais baixa por volta das 7h"). | `controllers/termometros_controller.py` (`interpretacoes`) |
| Seção "**Entenda os indicadores**" (temperatura, umidade relativa, média/mínima/máxima, amplitude, agrupamentos, período em comum). | `views/pagina_termometros.py` (`_entenda`) |
| Termos técnicos trocados por títulos explicativos: "Correlação de Pearson" → **"Relação entre temperatura e umidade"** (com o resultado em palavras: "Quando a temperatura sobe, a umidade tende a cair"); "Dispersão" → "Relação entre dois indicadores"; abas "Outliers (IQR)" → "Valores fora do padrão", "Correlações" → "Relação entre indicadores". | `views/pagina_estatistica.py`, `views/ar_comparacao.py`, `views/ar_estatistica.py` |
| Tabela estatística com "**O que significa cada coluna?**" (média, mediana, desvio padrão, quartis). | `views/pagina_estatistica.py` |
| Mapa com legenda explicada ("Como interpretar este mapa": linha preta = recorte, áreas coloridas = quebradas, pontos = projetos/estações). | `views/pagina_mapa.py` |
| Aviso destacado de que a qualidade do ar **não** é medida dentro de Heliópolis. | `views/pagina_qualidade_ar.py` |
| Glossário ampliado (umidade relativa, amplitude, dia típico, período em comum, quebrada, gleba, recorte, Shapefile/SIRGAS) e novas perguntas frequentes (onde ficam os termômetros, se medem a rua, se precisa de internet). | `views/pagina_ajuda.py` |
| Tutorial reescrito com a tabela das 7 páginas e 4 exemplos práticos ("Qual casa ficou mais quente?"...). | `views/pagina_ajuda.py` |

**Evidências**
- `tests/test_paginas_v4.py::test_termometros_explicam_origem_e_privacidade` (texto "DENTRO de Heliópolis" e "sem nomes").
- `tests/test_termometros.py::test_interpretacoes_avisam_periodos_diferentes` (a frase de alerta aparece só quando os períodos diferem).
- Conferência visual das explicações abaixo dos gráficos no navegador.

## 3. Simplificar a navegação e as interações

**Status: Implementado** · validação com usuários da UNAS: **pendente**

| Antes (V2) | Depois (V4) |
|---|---|
| 6 itens de menu, todos de qualidade do ar; "Visão geral", "Análise temporal" e "Comparação" separados. | 7 itens por **assunto**: Visão Geral · Temperatura e Umidade · Qualidade do Ar · Mapa · Análise Estatística · Sobre os Dados · Ajuda e Tutorial. As três páginas do ar viraram **seções de uma página só**. |
| Barra lateral com 8 filtros do ar em **todas** as páginas. | Filtros do ar aparecem **só** onde são usados; nas outras páginas a barra lateral tem só o menu. |
| Trocar de página apagava as escolhas. | As escolhas são **lembradas** ao trocar de página (filtros do ar e dos termômetros). |
| Abas que carregavam todas as seções ao mesmo tempo. | Seletor "**O que você quer ver?**": só a seção escolhida é desenhada (tela mais limpa e mais rápida). |
| Informações complementares misturadas ao conteúdo principal. | Detalhes em seções que abrem e fecham ("Quem é cada termômetro", "Tabelas do mapa", "Ver a conferência completa"). |
| — | Cada item do menu tem uma explicação curta ao passar o mouse. |

Arquivos: `app.py`, `app_pages/*.py`, `views/pagina_qualidade_ar.py`, `views/pagina_sobre_dados.py`,
`views/pagina_estatistica.py`, `views/barra_lateral.py`, `views/sessao.py`.

**Evidências**
- `tests/test_paginas_v4.py::test_filtros_do_ar_so_aparecem_onde_sao_usados`
- `tests/test_paginas_v4.py::test_filtro_do_ar_e_lembrado_ao_trocar_de_pagina`
- `tests/test_paginas_v4.py::test_estatistica_dos_dois_conjuntos` (filtros do ar só quando "Qualidade do ar" é escolhido).
- Retorno à página inicial: item **Visão Geral** sempre no topo do menu; a barra lateral lembra "Dúvidas? Abra Ajuda e Tutorial".

## 4. Comentários simples e didáticos no back-end

**Status: Implementado** (revisão por um iniciante da equipe: **recomendada**)

| Alteração | Arquivos |
|---|---|
| Todo arquivo novo começa com uma explicação do **porquê** ele existe e de como se encaixa no MVC (com diagrama de texto no Controller dos termômetros). | `models/termometros.py`, `models/geografia.py`, `controllers/termometros_controller.py`, `controllers/mapa_controller.py`, `controllers/sistema.py`, `scripts/preparar_dados_*.py`, `executavel/iniciar_painel.py`, `services/conectividade.py` |
| Docstrings com **o que recebe, o que devolve e por quê** em funções importantes; explicações de técnicas em linguagem simples ("método do raio" para ponto dentro da área, "fórmula do cadarço" para a área, o que é um Shapefile, o que é GeoJSON, por que o aparelho corta a média). | idem |
| Docstrings acrescentadas em 26 funções da V2 que não tinham (cálculos do Controller do ar, leitura das fontes, páginas). | `controllers/painel_controller.py`, `models/fontes.py`, `models/tratamento.py`, `views/ar_*.py`... |
| Explicação de cada camada do MVC nos arquivos `__init__.py` dos pacotes. | `controllers/`, `models/`, `views/`, `services/`, `scripts/` |
| Guia para iniciantes atualizado (diagrama MVC novo, como atualizar termômetros e mapas, como gerar o executável, erros comuns). | `GUIA_MANUTENCAO.md` |

Critério seguido: explicar a lógica e as decisões, sem comentários que só repetem o nome da função. Propriedades
simples (ex.: `nome`, `avisos`) ficaram sem docstring de propósito.

**Evidência:** verificação automática com `ast` — todas as funções públicas de cálculo, leitura e páginas têm
docstring; as que não têm são acessos simples a atributos.

---

## Pendências e justificativas

| Item | Situação | Justificativa / próximo passo |
|---|---|---|
| Validar a nova interface **com pessoas da UNAS** | Pendente | Os testes automáticos e a revisão no navegador foram feitos pela equipe de desenvolvimento. Falta observar 2 ou 3 pessoas da UNAS usando o painel (roteiro sugerido abaixo) e registrar as dificuldades. |
| Confirmar a **quebrada de cada termômetro** | Pendente (depende da UNAS) | Só a UNAS pode confirmar. Dois termômetros têm região sugerida pelo nome da planilha ("Lagoa"), marcada "a confirmar". O mapa só destaca regiões confirmadas. Basta editar `data/termometros/locais_termometros.csv`. |
| Registrar cômodo e altura dos aparelhos | Pendente (depende da UNAS) | Listado pela própria UNAS como "dados ainda não coletados". |

### Roteiro curto para a validação com a UNAS (10 minutos por pessoa)

Peça, sem ajudar, que a pessoa: (1) abra o programa; (2) diga para que serve a tela inicial; (3) descubra qual
termômetro teve a maior temperatura média; (4) explique o gráfico "Dia típico"; (5) encontre a quebrada Lagoa no
mapa; (6) compare dois termômetros; (7) diga de onde vêm os dados de qualidade do ar; (8) encontre a ajuda.
Anote onde ela hesitou e registre neste arquivo como novo feedback.
