# Alterações da V2

Registro de tudo o que mudou da V1 (dataset fictício) para a V2 (dados reais, código comentado e interface
educativa). Data: 08/11/2026.

## 1. Resumo

| Área | V1 | V2 |
|---|---|---|
| Dados | 1 arquivo fictício, 8 colunas fixas | Dados **reais** (MonitorAr/CETESB, 2024–2025, 6 estações) + importador QUALAR + demonstração fictícia mantida |
| Local | "Heliópolis" (fictício) | Estações **próximas**, com distância e aviso em todas as telas; nada é apresentado como medição dentro do bairro |
| Variáveis | Fixas no código | Descobertas a partir do arquivo (parâmetro + grandeza + unidade) |
| Interface | 7 páginas | 6 seções: Visão geral, Análise temporal, Comparação, Análise estatística, Sobre os dados, Ajuda |
| Explicações | Guia de interpretação | Explicação em todo gráfico, "Entenda cada indicador", glossário, tutorial, perguntas frequentes, ajuda nos filtros |
| Interpretação | Algumas frases | Interpretações calculadas (mês de maior média, hora de pico, % na faixa Boa, cobertura, avisos) |
| Qualidade do ar | — | Faixas oficiais N1–N5 (CETESB/CONAMA 491/2018) aplicadas da forma correta |
| Código | Comentado em partes | Comentado em português, para iniciantes, em todos os arquivos |
| Documentação | README, requisitos | + `GUIA_MANUTENCAO.md`, `docs/FONTES_DE_DADOS.md`, este arquivo |
| Testes | 148 | 176 (inclui conferência com os registros oficiais e funcionamento sem internet) |

## 2. Funcionalidades modificadas

**Preservadas (com o mesmo comportamento, agora para qualquer conjunto de variáveis):** estatística descritiva
(média, mediana, moda, mínimo, máximo, desvio padrão, variância, quartis), interpolação opcional de lacunas
curtas, sinalização de outliers por IQR sem remoção, exclusão opcional de outliers, versões original × tratada
e sua comparação, séries temporais com agrupamento, padrões por hora/dia da semana/mês, calendário, histograma,
boxplot, dispersão, correlação Pearson/Spearman, integridade dos dados, tabela detalhada, exportação CSV, banco
PostgreSQL opcional com *fallback*, iniciadores de dois cliques.

**Reorganizadas (sem perda):**

| Página da V1 | Onde está na V2 |
|---|---|
| Visão geral | Visão geral (indicadores redesenhados) |
| Séries temporais + Padrões no tempo | Análise temporal |
| Distribuições e outliers + Correlações | Análise estatística |
| Dados e qualidade | Sobre os dados (Qualidade dos dados; Tabela e exportação) |
| Guia de interpretação | Ajuda (glossário ampliado) |
| — | Comparação de indicadores (nova, inclui comparação entre estações) |

**Novas:** seletor de fonte e de estação, faixa de contexto (estação, município, distância, tipo de local,
fonte, datas de publicação e download), "IQAr da estação", gráfico de qual poluente foi registrado em cada hora,
comparação entre estações, distribuição por faixa de qualidade, cobertura por indicador, mapa das estações,
registro automático das transformações, média de cada mês do calendário, agrupamento mensal.

**Mudança de padrão:** a versão dos dados exibida por padrão passou a ser a **original** (sem preenchimento).
A tratada continua disponível em *Opções avançadas*.

## 3. Problemas encontrados e como foram resolvidos

| # | Problema | Solução |
|---|---|---|
| 1 | O dataset era fictício | Dados oficiais do MonitorAr incluídos, com SHA-256 e metadados; o fictício virou "Demonstração" identificada |
| 2 | Não há estação dentro de Heliópolis; São Caetano do Sul não está ativa | 6 estações ativas mais próximas, distância calculada de um ponto de referência com fonte (OpenStreetMap) |
| 3 | MonitorAr traz só **índice** para a CETESB (sem concentração, temperatura ou umidade) | Variáveis criadas a partir do arquivo; ausentes mostradas como indisponíveis; nada inventado |
| 4 | **Um único poluente por hora** no arquivo | Criada a variável "IQAr da estação"; avisos nas médias por poluente; gráfico explicativo |
| 5 | Correlação IQAr × poluente daria r = 1 sem sentido, e poluentes nunca coincidem | Correlação bloqueada nessa fonte, com explicação; mínimo de 30 horas em comum em qualquer correlação |
| 6 | Coordenadas genéricas no arquivo de 2025 | Coordenadas e endereços do serviço oficial da CETESB |
| 7 | Coluna de status com nomes diferentes em 2024 e 2025 | Unificada na leitura, com registro |
| 8 | "MP2,5" × "MP2.5" em fontes diferentes | Padronização de siglas (`normalizar_codigo`) sem mudar valores |
| 9 | Variáveis fixas no código (V1) impediam dados reais | Catálogo dinâmico (`models/parametros.py`) e tabelas por estação (`models/conjunto.py`) |
| 10 | Médias por hora podem ser enviesadas pela quantidade desigual de registros | A interpretação automática avisa quando a quantidade de registros varia muito entre as horas |
| 11 | Faixas oficiais não podem ser aplicadas a períodos errados | Índice usa as faixas do índice; concentração só com unidade confirmada e média no período oficial (24 h com 16 h válidas; 8 h completas; 1 h) |
| 12 | Marcas de mês do eixo apertadas em períodos longos | Marcas a cada 3 ou 6 meses conforme o período |
| 13 | Valores das barras de faixa cortados na borda | Espaço extra no eixo |
| 14 | No celular a barra lateral cobria o conteúdo (corrigido no fim da V1) | Mantido `initial_sidebar_state="auto"` |
| 15 | QUALAR exige login | Importador por nome de coluna + passo a passo; o projeto não guarda credenciais |

## 4. Decisões técnicas

- **Formato de registros (longo) + tabela por estação.** Aceita fontes com variáveis diferentes sem colunas
  vazias inventadas e impede misturar estações.
- **Chave da variável inclui a grandeza** (`MP2.5` × `MP2.5_IQAr`), para que índice e concentração nunca sejam
  confundidos; unidades diferentes geram variáveis diferentes.
- **"IQAr da estação" = maior índice da hora**, seguindo a regra da CETESB de classificar a estação pelo pior
  poluente. Com um poluente por hora, é o próprio valor registrado. O dicionário do MonitorAr não documenta isso,
  e o painel diz isso explicitamente.
- **Recorte em vez dos zips completos no projeto:** os zips oficiais têm 54 MB; o recorte (360 KB) contém as
  linhas das 6 estações sem alteração, e o script permite refazê-lo a partir dos zips (SHA-256 registrado).
- **Coordenadas da CETESB** (serviço ArcGIS) em vez das do arquivo, por causa das coordenadas genéricas de 2025.
- **Serviço ArcGIS não usado como série:** só 48 horas, unidade não documentada.
- **Sem novas dependências obrigatórias:** continuam Streamlit, Pandas, NumPy e Plotly.
- **Original como padrão:** o enunciado da V2 pede evitar preenchimento automático de lacunas.
- **Distâncias em linha reta** (fórmula de Haversine) a partir de um ponto aproximado, sempre rotuladas assim.

## 5. Arquivos

**Novos:** `models/parametros.py`, `models/conjunto.py`, `models/qualidade_ar.py`, `models/localizacao.py`,
`views/pagina_temporal.py`, `views/pagina_comparacao.py`, `views/pagina_estatistica.py`,
`views/pagina_sobre_dados.py`, `views/pagina_ajuda.py`, `scripts/preparar_dados_monitorar.py`,
`data/reais/*`, `data/qualar/LEIA-ME.md`, `docs/FONTES_DE_DADOS.md`,
`docs/fontes/arquivo-auxiliar-dados-monitorar.pdf`, `GUIA_MANUTENCAO.md`, `ALTERACOES_V2.md`,
`tests/test_modelos.py`, `tests/test_preparar_dados.py`.

**Reescritos:** `models/fontes.py`, `models/tratamento.py`, `models/estatistica.py`,
`controllers/painel_controller.py`, `services/config.py`, `views/estilo.py`, `views/graficos.py`,
`views/tabelas.py`, `views/barra_lateral.py`, `views/pagina_visao_geral.py`, `app.py`, testes, README.

**Removidos (conteúdo migrado):** `models/variaveis.py` (→ `parametros.py`), `views/pagina_series.py`,
`pagina_padroes.py`, `pagina_distribuicoes.py`, `pagina_correlacoes.py`, `pagina_dados.py`,
`pagina_guia.py` (→ novas seções, veja a tabela da seção 2).

**Movido:** `data/ambiental_heliopolis.csv` → `data/demonstracao/ambiental_heliopolis.csv`.

## 6. Testes realizados (execução real)

- `python -m pytest`: **176 testes passando**. Cobrem:
  - leitura dos dados reais, com o total e a contagem por estação/parâmetro iguais às dos arquivos oficiais, e
    8 valores pontuais conferidos de forma independente direto do zip;
  - arquivos vazios, corrompidos, sem colunas ou com estação desconhecida;
  - valores ausentes, lacunas e duplicados;
  - dados sem determinada variável e unidades diferentes;
  - seleção de períodos (incluindo vazio e invertido) e alteração de filtros na barra lateral;
  - as 6 seções renderizadas em 6 cenários;
  - cálculos estatísticos conferidos com Pandas/cálculo direto, e faixas oficiais nos limites;
  - exportação CSV relida e conferida;
  - mensagens de erro, inclusive sem vazar senha;
  - funcionamento **sem internet** (conexões de rede bloqueadas no teste);
  - inicialização do app e o script de preparação.
- Navegador (Chromium headless): todas as seções abertas e conferidas visualmente.
- Script de preparação executado nos zips oficiais de 2024 e 2025 (SHA-256 conferido com o calculado no
  navegador no momento do download).

## 7. Limitações e melhorias futuras

Veja a seção "Limitações" do README e `docs/FONTES_DE_DADOS.md`. Principais próximos passos: validar o
importador com uma exportação real do QUALAR (concentrações, temperatura e umidade), incluir 2022–2023 e
mais estações, e automatizar a atualização anual.
