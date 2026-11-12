# Checklist da rubrica — auditoria crítica (V4)

Auditoria feita em 12/11/2026, baseada em evidências verificáveis. **Não é uma autoavaliação de nota máxima**:
cada critério lista o que ainda pode custar pontos. Resultados de testes: `docs/TESTES_REALIZADOS.md`.

| Critério | Pontos | Situação | Principal risco |
|---|---:|---|---|
| Código bem explicado | 1,0 | Forte | Avaliador pode achar comentários longos demais em alguns arquivos |
| Explicações no Streamlit | 1,0 | Forte | Ainda não validado com usuários reais da UNAS |
| Executável | 1,5 | **Bom, com pendência** | Teste em computador sem Python **não feito**; Release não publicada |
| README | 0,8 | **Bom, com pendência** | Link da Release e nomes dos integrantes **em branco** |
| Qualidade do código | 1,0 | Forte (2 erros da auditoria corrigidos) | Arquivos grandes herdados da V2 (`painel_controller.py`, `fontes.py`) |
| Funcionalidades | 1,2 | Forte | Termômetros sem localização validada; feedbacks sem validação da UNAS |
| Organização e commits | 0,5 | **Pendente** | Commits ainda não feitos; depende de todos os integrantes |
| **Total** | **7,0** | | |

---

## 1. Código bem explicado (1,0)

**Implementado:** cabeçalho em todo módulo explicando o porquê e a ligação com o MVC; docstrings com
parâmetros/retorno nas funções de leitura, cálculo, controllers e páginas; explicações didáticas (Shapefile,
GeoJSON, conversão de coordenadas, "método do raio", "fórmula do cadarço", período em comum, cache do
Streamlit, `developmentMode` no executável); `__init__.py` de cada camada explicando o papel dela;
`GUIA_MANUTENCAO.md` atualizado.

**Evidência:** `models/termometros.py`, `models/geografia.py`, `controllers/termometros_controller.py`,
`scripts/preparar_dados_geograficos.py`, `executavel/iniciar_painel.py`; varredura com `ast` (só propriedades
triviais sem docstring).

**Testado:** varredura automática de docstrings; compilação de todos os módulos.

**Pendências / riscos:** cerca de 80 métodos curtos (propriedades e `__init__` já descritos na docstring da
classe) não têm docstring própria — decisão consciente para evitar comentários redundantes, mas um avaliador
pode contar isso. Peça a um integrante iniciante para ler `models/termometros.py` e apontar trechos confusos.

## 2. Explicações no Streamlit (1,0)

**Implementado:** página inicial com "como usar em 3 passos"; título + frase de objetivo + faixa de origem dos
dados em todas as páginas; "Como interpretar este gráfico" em todos os gráficos; frases automáticas "O que os
dados mostram"; "Entenda os indicadores"; filtros numerados com `?`; termos técnicos em linguagem simples
("Relação entre temperatura e umidade"); avisos claros sem dados; glossário, tutorial com exemplos e perguntas
frequentes; aviso de que a qualidade do ar não é medida no bairro; seção de privacidade.

**Evidência:** `views/pagina_*.py`; `FEEDBACK_UNAS.md` (itens 1–3); testes em `tests/test_paginas_v4.py`.

**Testado:** 7 páginas e todas as seções abertas sem erro (testes automáticos + navegador, incluindo largura de
celular sem rolagem horizontal).

**Pendências / riscos:** a eficácia das explicações **não foi validada com pessoas da UNAS** (roteiro de
validação em `FEEDBACK_UNAS.md`). Algumas tabelas da V2 (seção Qualidade do Ar → Sobre) continuam densas.

## 3. Executável (1,5) — maior peso

**Implementado:** `executavel/iniciar_painel.py` (porta livre automática, abre o navegador, mensagens e log de
erro em português), `painel_heliopolis.spec` (PyInstaller, modo pasta, só dados preparados, sem dependências
geográficas nativas), `gerar_executavel.bat` (reproduzível), `COMO_USAR.txt`, `LEIA-ME.md` com o teste manual.

**Testado (na máquina de desenvolvimento, Windows 11, que TEM Python instalado):**
- executável **gerado de novo após as correções** (12/11/2026): zip de 92,8 MB, SHA-256
  `9C753E9908BFD3880B470CC38F43397989FF285AED29A8F911FE9E58135A724B`; `python313.dll` incluída; nenhuma
  planilha/arquivo bruto, nome de morador ou senha incluídos (verificado no zip);
- zip extraído fora da pasta do projeto e aberto com **PATH sem Python** e sem variáveis do Python: endereço
  mostrado em menos de 1 s; mostrou o período em comum com hora (código corrigido está no executável);
- as 7 páginas abertas no navegador a partir do executável, com gráficos, mapa e conferência "30 de 30";
- (build anterior) com a porta 8501 ocupada escolheu a 8502;
- caminho de erro: com `app.py` removido, mostrou a mensagem em português, gravou `erro_ao_iniciar.txt` e saiu
  com código 1.

**Pendências / riscos (podem custar pontos):**
- **NÃO foi testado em um computador sem Python instalado.** Na máquina de teste o Python existe no disco,
  ainda que fora do PATH. Fazer o teste de `executavel/LEIA-ME.md` (Windows Sandbox ou outro computador).
- **O funcionamento sem internet não foi testado com a rede desligada**; o código prevê o fundo branco do mapa,
  e todos os dados são locais.
- **A Release ainda não foi publicada** e o link não está no README.
- SmartScreen/antivírus podem alertar (executável sem assinatura digital) — instrução já incluída.
- Só Windows.

## 4. README (0,8)

**Implementado:** propósito, contexto UNAS/Heliópolis, funcionalidades, fontes, tecnologias, estrutura,
instalação para desenvolvedores, uso para a UNAS, uso sem Python, atualização das bases, limitações.

**Pendências / riscos:** **link da Release** (placeholder no topo e na seção 4) e **integrantes do grupo**
(tabela "preencher") — sem isso o critério cai para "Parcial" ("falta alguma dessas partes").

## 5. Qualidade do código e boas práticas (1,0)

**Implementado:** MVC mantido; responsabilidades separadas (Model sem Streamlit, Controller sem desenho);
`Sistema` isola falhas de cada conjunto; páginas em `app_pages/` (padrão recomendado do Streamlit); reuso de
componentes (`estilo.explicar_grafico`, `_base`, filtros dos termômetros compartilhados por duas páginas);
caminhos relativos à raiz que funcionam com e sem empacotamento; dependências separadas
(`requirements.txt`, `-db`, `-dev`); correções de compatibilidade com pandas 3; aviso do Streamlit eliminado.

**Testado:** 238 testes automáticos (`python -m pytest`) em 3 ambientes: `.venv` do projeto, ambiente novo com Python 3.14 e ambiente novo com as versões mínimas (Streamlit 1.67.0, pandas 2.2.3, Plotly 5.24.1).

**Corrigido após a auditoria externa (12/11/2026):**
- **Período em comum dos termômetros:** devolvia só as datas e o recorte pegava os dias inteiros (em 17/02/2025 o
  Termômetro 2 tinha 30 leituras e os outros 144). Agora usa data **e hora**; os 5 termômetros têm exatamente as
  mesmas leituras. 10 testes de regressão novos (`tests/test_termometros.py`, `tests/test_paginas_v4.py`).
- **Versão mínima do Streamlit:** `requirements.txt` aceitava 1.50, mas o código usa `persist_state` (1.59+) e
  `st.Page(help=...)` (1.67+). Mínimo corrigido para 1.67, conferido nas wheels oficiais e testado em ambientes
  virtuais novos (veja `docs/TESTES_REALIZADOS.md`). Os iniciadores reinstalam se o Streamlit for antigo.

**Pendências / riscos:** `controllers/painel_controller.py` (≈650 linhas) e `models/fontes.py` (≈650 linhas),
herdados da V2, são grandes; não foram divididos para não arriscar regressões. Não há verificador de tipos
(mypy/ty) nem formatador configurado.

## 6. Funcionalidades (1,2)

**Implementado:** os três conjuntos integrados sem mistura; seção completa de termômetros (selecionar,
comparar, média/mín/máx, evolução, períodos, tabelas, exportação, explicações); mapa com delimitação,
quebradas, seleção de área, informações, projetos e estações; os 4 feedbacks reais da UNAS aplicados
(`FEEDBACK_UNAS.md`); funcionalidades da V2 preservadas.

**Evidência:** `tests/test_termometros.py`, `tests/test_geografia.py`, `tests/test_paginas_v4.py`, conferência
com os aparelhos (30/30), conferência de áreas (< 0,02 %).

**Pendências / riscos:** termômetros **não aparecem no mapa** porque nenhuma localização foi validada pela UNAS
(decisão de privacidade, explicada na tela); feedbacks implementados mas **não validados pela UNAS**; outras
camadas do Drive (setores censitários etc.) não usadas.

## 7. Organização do repositório e commits (0,5)

**Implementado:** estrutura de pastas limpa; `.gitignore` bloqueando dados pessoais, executáveis e temporários;
sem credenciais; guia de commits por funcionalidade em `docs/GITHUB_E_RELEASE.md`.

**Pendências / riscos (alto):** os **commits ainda não foram feitos**. A rubrica exige "commits de todos do
grupo com mensagens úteis" — cada integrante precisa fazer os seus, com a própria conta. Antes de cada commit,
conferir `git status` (nenhum arquivo de `bruto/`, `dist/` ou `.env`).

---

## Ações para fechar as pendências (em ordem de impacto)

1. Teste do executável em computador sem Python (1,5 ponto em jogo) → registrar em `docs/TESTES_REALIZADOS.md`.
2. Commits de cada integrante (0,5) → `docs/GITHUB_E_RELEASE.md`.
3. Publicar a Release e colar o link no README; preencher os integrantes (0,8).
4. Sessão rápida de validação com a UNAS e registro em `FEEDBACK_UNAS.md` (reforça 1,0 + 1,2).
5. Confirmar com a UNAS a quebrada dos termômetros (`data/termometros/locais_termometros.csv`).
