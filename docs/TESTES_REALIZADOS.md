# Testes realizados — V4 (12/11/2026)

Registro do que foi **realmente executado**, com o resultado. Ambiente: Windows 11 Pro, Python 3.13 (ambiente
virtual), Streamlit 1.67, pandas 3.1, Plotly 7.1, PyInstaller 6.22.

## 1. Testes automáticos (`python -m pytest`)

Resultado da última execução completa: **228 passed, 0 failed, 0 avisos** (8 min 0 s).

| Arquivo | O que verifica |
|---|---|
| `tests/test_termometros.py` | Leitura de planilha no formato RC-51H (vírgula decimal, resumo do aparelho, `.xls` com conteúdo `.xlsx`); sinalização de vazios, duplicatas, umidade impossível e interrupções **sem inventar valores**; erro claro sem a aba "Lista"; script de preparação **anonimiza** (nomes não saem da pasta bruta) e mantém os números antigos; período em comum; média/mín/máx/amplitude; série diária sem preencher dias; dia típico; tempo acima de um limite; relação temperatura × umidade; dados reais: 5 termômetros, **30/30 valores conferem com os aparelhos**, sem lacunas, aviso de períodos diferentes, exportação CSV, período sem dados. |
| `tests/test_geografia.py` | Ponto dentro de polígono (com buraco); área (com buraco e multipolígono); erro claro sem a camada de quebradas; camadas opcionais ausentes viram aviso; camadas reais (7 quebradas, 15 glebas, 52 projetos, 2,46 km²); coordenadas convertidas caem em Heliópolis; áreas conferem com a tabela original (< 0,1 %); projetos por quebrada; termômetros validados por quebrada. |
| `tests/test_paginas_v4.py` | As 7 páginas abrem com o título certo; links da Visão Geral; filtros do ar só onde são usados e lembrados ao trocar de página; todas as seções dos termômetros (temperatura e umidade); aviso sem termômetro escolhido; texto de origem e privacidade; mapa com todas as camadas e quebrada destacada; seções da qualidade do ar; estatística dos dois conjuntos; os 4 assuntos de Sobre os Dados; conferência "30 de 30". |
| `tests/test_app.py`, `test_controller.py`, `test_fontes.py`, `test_modelos.py`, `test_preparar_dados.py` | Testes da V2 (qualidade do ar), atualizados para a nova navegação. Um deles falhava com pandas 3 antes da V4 (`test_monitorar_estacao_fora_da_lista_fica_nao_verificada`) e foi corrigido. |

## 2. Verificações dos dados

| Verificação | Resultado |
|---|---|
| Leitura das 5 planilhas | 160.000 leituras (32.000 cada), intervalo de 10 min, sem vazios, duplicatas ou interrupções |
| Conferência com o resumo dos aparelhos | 30 de 30 conferem (médias do aparelho são cortadas na 1ª casa decimal) |
| Shapefiles | 4 conjuntos completos (.shp/.shx/.dbf/.prj/.cpg), SIRGAS 2000 / UTM 23S, texto em UTF-8 |
| Conversão de coordenadas | Centro do mapa em −23,611 / −46,589 (Heliópolis); áreas com diferença < 0,02 % |
| Privacidade | Busca automática por nomes de moradores e endereços nos arquivos do projeto e do executável: nenhum encontrado fora de `data/termometros/bruto/` (que fica fora do Git e do executável) |

## 3. Interface no navegador (painel em execução)

Conferido visualmente: Visão Geral, Temperatura e Umidade (Comparar termômetros, Ao longo do tempo), Mapa
(quebradas, projetos, recorte; zoom pela rodinha desativado após o teste), Qualidade do Ar (filtros na barra
lateral). Largura de celular (375 px): sem rolagem horizontal e sem erros.

## 4. Executável

| Teste | Resultado |
|---|---|
| Geração com PyInstaller (`painel_heliopolis.spec`) | Concluída sem erros; pasta de 233 MB; zip de 92,8 MB (SHA-256 `D84304168649E543B16DEF1B8EE2A997200DC989722DCEF9078C6A186818B7FD`) |
| Conteúdo | Só dados preparados; nenhuma pasta `bruto/`; nenhum nome de morador |
| Execução fora da pasta do projeto, com PATH **sem Python** e sem variáveis do Python | Servidor pronto em ~8 s |
| Porta ocupada (8501 em uso) | Escolheu 8502 automaticamente |
| As 7 páginas servidas pelo executável | Abriram sem erro; gráficos (Plotly) e mapa desenhados; "30 de 30 conferem" |
| Erro de inicialização simulado (`app.py` removido) | Mensagem em português, `erro_ao_iniciar.txt` gravado, código de saída 1 |

## 5. NÃO testado (pendente)

- **Executável em um computador sem Python instalado.** O teste acima removeu o Python do PATH, mas o Python
  continuava instalado no disco. Procedimento obrigatório em `executavel/LEIA-ME.md`.
- **Funcionamento com a internet desligada.** Os dados são todos locais e o mapa tem fundo branco quando não há
  conexão (código em `services/conectividade.py`), mas o teste com a rede desligada não foi feito.
- **Validação com usuários da UNAS** (roteiro em `FEEDBACK_UNAS.md`).
- Download do zip a partir de uma Release publicada (a Release ainda não existe).
