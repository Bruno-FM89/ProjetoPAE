# Roteiro de apresentação (≈ 10 minutos) — V2

## Antes de começar
1. Dê dois cliques em `iniciar.bat` (Windows) ou `iniciar.command` (macOS). Abre em http://localhost:8501.
2. Deixe a seção *Visão geral* aberta, com a fonte **Dados reais — MonitorAr (CETESB)** e a estação **Mooca**
   (padrão, a mais próxima), com o navegador em tela cheia.

## Sequência sugerida

| Tempo | O que mostrar | O que falar |
|---|---|---|
| 1 min | **Faixa de contexto** (topo) | Os dados são oficiais da CETESB, publicados pelo MonitorAr (MMA). A estação Mooca fica a 6,7 km: **não há estação dentro de Heliópolis**, e o painel diz isso em todas as telas. |
| 1,5 min | **Visão geral** | Indicadores com nome, sigla, unidade e faixa oficial. Em 2024–2025, 87% das horas com índice na Mooca ficaram na faixa N1 – Boa; o maior índice foi 187 (N4 – Muito Ruim). Leia a caixa de interpretação automática e abra "Entenda cada indicador". |
| 1 min | **Barra lateral** | Troque a estação (todas com a distância), o período e o indicador. Em *Opções avançadas*: original × tratado, agrupamento, ignorar outliers. Tudo atualiza em todas as seções. |
| 1,5 min | **Análise temporal** | Média mensal (maior em setembro de 2024, menor em janeiro de 2024). Lembre: o painel mostra padrões, não causas. Padrão por hora: média mais alta às 18h. Mostre o gráfico "qual poluente foi registrado em cada hora" e explique por que ele existe. |
| 1 min | **Comparação** | Aba *Entre estações*: o mesmo índice em 3 estações, lado a lado, sem misturar os dados. |
| 1,5 min | **Análise estatística** | Média × mediana (27,2 × 24: a média é puxada por valores altos). Histograma, boxplot, outliers pelo IQR (**sinalizados, nunca removidos**). Na aba *Correlações*, mostre a explicação de por que ela não é calculada nesses dados. |
| 1 min | **Sobre os dados** | Fonte, licença, SHA-256, mapa das estações, cobertura (88%), metodologia (lista de transformações), exportação CSV. |
| 0,5 min | **Ajuda** | Glossário (MP2,5, IQAr, mediana, IQR…) e perguntas frequentes. |
| 1 min | **Arquitetura** | Pastas `models/ controllers/ views/`. `FonteDados` → `FonteMonitorAr`, `FonteQualar`, `FonteCSV`, `FontePostgres` (herança e polimorfismo). A View só fala com o Controller. Código comentado e `GUIA_MANUTENCAO.md`. |

Se sobrar tempo: troque a fonte para **Demonstração — dados fictícios** e mostre que temperatura, umidade e
correlações voltam a aparecer, com o aviso de dado fictício.

## Perguntas que podem aparecer
- **Esses dados são de Heliópolis?** Não. São de estações oficiais a 6,7–9,8 km em linha reta. Servem como
  referência da região, não como medição exata do bairro.
- **Por que não há temperatura, umidade nem concentração em µg/m³?** O arquivo aberto do MonitorAr traz, para a
  CETESB, só o índice. Essas informações estão no QUALAR, que exige login; o painel já tem o importador e o passo a
  passo (`docs/FONTES_DE_DADOS.md`). Nada foi inventado.
- **O que é o "IQAr da estação"?** O maior índice entre os poluentes em cada hora, que é a regra da CETESB para
  classificar a estação. Nesses arquivos há um poluente por hora, então é o próprio valor registrado.
- **Por que não preencher as lacunas?** Para não criar dados. A versão "tratada" existe, mas só interpola
  lacunas de até 4 h e é opcional.
- **Por que não remover outliers?** Um valor extremo pode ser um evento real; o app sinaliza e deixa o usuário decidir.
- **Os dados são validados?** Não: a própria fonte avisa que são automáticos. Para estudos técnicos, use o QUALAR.
- **O que o projeto não faz?** Não prevê, não afirma causas e não mede o ar dentro de Heliópolis.
