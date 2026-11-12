# Testes realizados — V4 (12/11/2026, atualizado após a auditoria)

Registro do que foi **realmente executado**, com o resultado. Cada seção diz que tipo de verificação foi feita:

- **automático** — testes com `pytest` (incluindo o `AppTest` do Streamlit, que roda as páginas em memória, sem
  navegador: confere textos, controles e erros, mas **não** desenha gráficos);
- **visual** — painel aberto no navegador, conferindo na tela e no código da página que os gráficos e o mapa
  foram desenhados;
- **HTTP** — só a resposta do servidor. **Uma resposta HTTP 200 NÃO prova que gráficos e mapas apareceram**, por
  isso não usamos HTTP como prova de funcionamento das páginas.

Ambiente da máquina de desenvolvimento: Windows 11 Pro. O Python **está instalado** nesta máquina.

## 0. O que mudou após a auditoria externa

| Problema encontrado | Correção | Como foi verificado |
|---|---|---|
| "Quando todos mediram juntos" devolvia só as datas e pegava os dias inteiros: em 17/02/2025 o Termômetro 2 tinha 30 leituras e os outros 144; em 12/06/2025 o Termômetro 3 tinha 2 e os outros 144. | O período em comum agora tem **data e hora** (17/02/2025 às 19h00 a 12/06/2025 às 00h10 com os 5). O recorte respeita esse horário. "Todo o período" e "Escolher datas" continuam com dias inteiros. | 10 testes novos (seção 1) + navegador (seção 3) |
| `requirements.txt` aceitava Streamlit 1.50, mas o código usa `persist_state` (existe desde 1.59) e `st.Page(help=...)` (existe desde **1.67**). | Mínimo corrigido para `streamlit>=1.67,<2`. Os iniciadores (`iniciar.bat`, `iniciar.sh`) agora exigem Python 3.11+ e reinstalam se o Streamlit do `.venv` for anterior a 1.67. | Wheels oficiais inspecionadas + suíte completa em ambientes novos (seção 2) |

### Como ficou o período em comum (explicação simples)

Ele começa quando o **último** termômetro escolhido foi ligado e termina quando o **primeiro** foi desligado,
com a hora exata. Exemplo com os 5: o Termômetro 2 começou em 17/02/2025 às 19h00 e o Termômetro 3 parou em
12/06/2025 às 00h10. Assim todos têm exatamente as mesmas leituras (16.448 cada). O primeiro e o último dia
ficam incompletos, mas **igualmente para todos**, e o painel avisa isso embaixo dos filtros.

- **Lacunas no meio** (aparelho desligado por algumas horas) não mudam esses limites e continuam vazias: nada é
  preenchido nem inventado. Hoje não há lacunas nos dados reais.
- **Amplitude diária** continua usando só dias completos (144 leituras). Se a sobreposição tiver menos de um dia
  completo, ela fica vazia em vez de usar um dia pela metade.
- **Sem sobreposição:** aparece "Os termômetros escolhidos nunca mediram ao mesmo tempo" e o painel mostra todo
  o período de cada um, com o aviso de comparação injusta.
- O aviso "nem todos os termômetros mediram durante todo o período" agora é conferido nas próprias leituras do
  recorte (primeira e última), e não só pelas datas.

## 1. Testes automáticos (`python -m pytest`)

| Ambiente | Python | Streamlit · pandas · Plotly · NumPy | Resultado |
|---|---|---|---|
| `.venv` do projeto (o mesmo que gera o executável) | 3.13 | 1.67.0 · 3.1.1 · 7.1.0 · — | **238 passed**, 0 falhas (9 min 20 s) |
| Ambiente **novo e isolado**, `pip install -r requirements-dev.txt` | 3.14.7 | 1.67.0 · 3.1.1 · 7.1.0 · 2.5.4 | **238 passed**, 0 falhas (8 min 52 s) |
| Ambiente **novo e isolado** com as **versões mínimas** declaradas | 3.13 | 1.67.0 · 2.2.3 · 5.24.1 · 2.5.4 | **238 passed** (199 + 39 de `test_fontes.py`, rodado à parte depois de instalar o `sqlalchemy` opcional), 0 falhas |

Observações honestas:
- Com pandas 2.2.3 + NumPy 2.5 aparecem 922 avisos (`DeprecationWarning` do NumPy sobre unidades de `timedelta`,
  vindos de dentro do pandas 2.2). Não são falhas; com pandas 3 eles não aparecem.
- O mesmo ambiente mínimo com **Streamlit 1.59.0** falhou em 40 testes (`Page() got an unexpected keyword
  argument 'help'`) — é a prova de que 1.67 é o mínimo real.
- Os ambientes novos foram criados numa pasta temporária, sem alterar o Python global nem o `.venv` do projeto.

### Testes novos desta correção

| Teste | O que garante |
|---|---|
| `test_periodo_comum_respeita_horarios_diferentes_no_mesmo_dia` | Início às 19h00 e fim às 08h00: os dois termômetros ficam com as mesmas 223 leituras |
| `test_periodo_comum_sem_sobreposicao` | Sem sobreposição → `None`, e o aviso de comparação injusta aparece |
| `test_periodo_comum_com_um_so_termometro` | Um termômetro só → período = da 1ª à última leitura dele |
| `test_periodo_comum_muda_quando_muda_a_escolha` | Trocar os termômetros escolhidos muda os limites; cada escolha fica consistente |
| `test_lacuna_no_meio_nao_muda_limites_nem_e_preenchida` | Lacuna não encolhe o período, não é preenchida e o dia com lacuna sai da amplitude diária |
| `test_periodo_comum_menor_que_um_dia_sem_dias_completos` | Sobreposição de 6 h: resumo calculado, amplitude diária vazia |
| `test_datas_sem_hora_continuam_usando_dias_inteiros` | "Todo o período"/"Escolher datas" seguem com dias inteiros |
| `test_dados_reais_periodo_comum_tem_as_mesmas_horas_para_todos` | Dados reais: 5 termômetros com os mesmos limites e contagem; 30 leituras em 17/02 e 2 em 12/06 para **todos**; exportação CSV com o mesmo número de linhas por termômetro |
| `test_dados_reais_so_com_as_datas_avisa_comparacao_injusta` | O comportamento antigo (só datas) é reconhecido como injusto |
| `test_termometros_periodo_com_hora_e_troca_de_termometros` (AppTest) | A legenda mostra a hora; muda ao trocar termômetros; "Todo o período" e "Escolher datas" usam datas |

### Arquivos de teste

| Arquivo | O que verifica |
|---|---|
| `tests/test_termometros.py` | Leitura das planilhas RC-51H; sinalização de problemas sem inventar valores; anonimização; período em comum (com hora); cálculos; dados reais (30/30 conferem com os aparelhos); exportação CSV. |
| `tests/test_geografia.py` | Ponto em polígono, áreas, camadas reais, conversão de coordenadas, áreas < 0,1 % da tabela original. |
| `tests/test_paginas_v4.py` | As 7 páginas (AppTest), filtros só onde são usados e lembrados, seções, mensagens sem dados, período com hora. |
| `tests/test_app.py`, `test_controller.py`, `test_fontes.py`, `test_modelos.py`, `test_preparar_dados.py` | Qualidade do ar (V2), atualizados para a navegação nova. |

## 2. Versão mínima das dependências (como foi descoberta)

As wheels oficiais do Streamlit 1.50.0 a 1.67.0 foram baixadas (sem instalar) e o código delas foi lido por um
script que compara cada `st.<função>(parâmetro=...)` usado no projeto com a definição da função:

- `persist_state` nos widgets: ausente até 1.58.0, presente a partir de **1.59.0**;
- `st.Page(help=...)`: ausente até 1.66.0, presente em **1.67.0**.

Plotly: `go.Scattermap` existe desde 5.24 (testado com 5.24.1). Python: o Streamlit 1.67 exige 3.11+.

## 3. Interface no navegador (verificação **visual**, painel rodando com `streamlit run`)

| Página / ação | Resultado observado |
|---|---|
| Temperatura e Umidade — período padrão | Legenda "17/02/2025 às 19h00 a 12/06/2025 às 00h10"; indicador "Leituras analisadas 82.240" (5 × 16.448); gráfico desenhado; sem aviso de comparação injusta |
| Tirar o Termômetro 2 | Período passa a "11/02/2025 às 18h20 a 12/06/2025 às 00h10" |
| "Todo o período" | "01/11/2024 a 21/09/2025" (dias inteiros) e o aviso "nem todos os termômetros mediram…" |
| "Escolher datas" (01/03 a 31/03/2025) | Legenda "01/03/2025 a 31/03/2025" |
| Medida Umidade; seção "Tabela e download" | Indicadores de umidade; tabela com 580 linhas (5 × 116 dias); botão "Baixar esta tabela (CSV)" presente (o arquivo **não** foi baixado; o conteúdo do CSV é verificado pelos testes automáticos) |
| Nenhum termômetro escolhido | "Escolha pelo menos um termômetro clicando nos botões acima." |
| Mapa | Mapa desenhado com ruas, quebradas e projetos; aviso de que nenhum termômetro tem região confirmada |
| Qualidade do Ar + troca de página | Estação "Parque D.Pedro II" escolhida, ida ao Mapa e volta: a estação continuou escolhida |
| Visão Geral, Análise Estatística (3 gráficos), Sobre os Dados ("30 de 30 valores conferem"), Ajuda | Abriram sem erro |

## 4. Verificações dos dados

| Verificação | Resultado |
|---|---|
| Leitura das 5 planilhas | 160.000 leituras (32.000 cada), intervalo de 10 min, sem vazios, duplicatas ou interrupções |
| Conferência com o resumo dos aparelhos | 30 de 30 conferem (médias do aparelho são cortadas na 1ª casa decimal) |
| Shapefiles | 4 conjuntos completos, SIRGAS 2000 / UTM 23S, texto em UTF-8 |
| Privacidade | Nenhum nome de morador nem endereço fora de `data/termometros/bruto/` (que fica fora do Git e do executável) |

## 5. Executável (gerado de novo em 12/11/2026 após as correções)

| Teste | Tipo | Resultado |
|---|---|---|
| Geração com `executavel\gerar_executavel.bat` (configuração existente) | — | Concluída sem erros |
| Arquivo gerado | — | `dist/PainelHeliopolis-Windows.zip` — 97.300.056 bytes (92,8 MB); pasta extraída ~227 MB |
| SHA-256 do zip | — | `9C753E9908BFD3880B470CC38F43397989FF285AED29A8F911FE9E58135A724B` |
| Conteúdo | inspeção do zip | 2.544 entradas; `python313.dll` incluída; todos os dados preparados (termômetros, GeoJSON, MonitorAr); **0** arquivos `bruto`, `.xls`, `.shp`, `.dbf`, `.env` ou `correspondencia`; **0** nomes de moradores e **0** possíveis senhas nos arquivos do painel |
| Execução fora da pasta do projeto (zip extraído em `%LOCALAPPDATA%\Temp`), com Python **retirado do PATH** e sem `PYTHONPATH`/`PYTHONHOME` | — | Mostrou o endereço `http://localhost:8501` em menos de 1 s e serviu o painel |
| Código corrigido dentro do executável | visual | Temperatura e Umidade mostrou "17/02/2025 às 19h00 a 12/06/2025 às 00h10" e "82.240" leituras; gráfico desenhado |
| As 7 páginas servidas pelo executável | visual | Sem erro; mapa desenhado; Qualidade do Ar com 2 gráficos; Estatística com 3; "30 de 30 valores conferem" |

Testes anteriores do executável (12/11/2026, antes da correção) que não foram repetidos agora: porta ocupada →
escolheu 8502; erro simulado (`app.py` removido) → mensagem em português, `erro_ao_iniciar.txt` e código 1. O
código de inicialização (`executavel/iniciar_painel.py`) não mudou.

## 6. NÃO testado (pendente)

- **Executável em um computador sem Python instalado.** Tirar o Python do PATH **não equivale** a um computador
  sem Python: aqui o Python continua instalado no disco. Roteiro curto em `executavel/LEIA-ME.md`.
- **Funcionamento com a internet desligada** (rede fisicamente desligada).
- **Python 3.11 e 3.12** (os testes rodaram em 3.13 e 3.14).
- **Download a partir de uma Release publicada** (a Release ainda não existe).
- **Validação com usuários da UNAS** (roteiro em `FEEDBACK_UNAS.md`).
