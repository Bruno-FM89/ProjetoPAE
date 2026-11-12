# Alterações da V4

Resumo do que mudou da V2 para a V4: integração dos dados da UNAS (termômetros e mapas), aplicação dos
feedbacks reais da UNAS e preparação para a avaliação final (executável, documentação, testes).

## 1. Novidades

| Área | O que foi feito |
|---|---|
| **Termômetros da UNAS** | Leitura das 5 planilhas (160.000 leituras), anonimização, conferência com o resumo dos aparelhos (30/30), página "Temperatura e Umidade" com comparação, evolução, faixa diária, dia típico, mês a mês, tempo acima de um valor, tabela e CSV. |
| **Mapa de Heliópolis** | Conversão de 4 Shapefiles (SIRGAS 2000 / UTM 23S → WGS 84) para GeoJSON; mapa com recorte, 7 quebradas, 15 glebas, 52 projetos da UNAS e estações da CETESB; detalhes por quebrada; funciona sem internet. |
| **Navegação** | 7 páginas por assunto (Visão Geral, Temperatura e Umidade, Qualidade do Ar, Mapa, Análise Estatística, Sobre os Dados, Ajuda e Tutorial); páginas do ar unificadas em seções; filtros do ar só onde são usados; escolhas lembradas entre páginas. |
| **Explicações** | Frase de objetivo, fonte e "Como interpretar" em todos os gráficos; termos técnicos substituídos por títulos explicativos; glossário e tutorial ampliados. |
| **Código** | Novos Model/Controller (termômetros, geografia, mapa, sistema), docstrings didáticas, `app_pages/` (uma página por arquivo). |
| **Executável** | Inicializador + receita do PyInstaller + script de geração; pasta `PainelHeliopolis` com `.exe` e `COMO_USAR.txt`. |
| **Correções** | Compatibilidade com pandas 3 (leitura de estações fora da lista; `day_of_week`); aviso do Streamlit sobre valores padrão dos filtros. |

## 2. Arquivos

**Novos:** `app_pages/*.py`, `controllers/termometros_controller.py`, `controllers/mapa_controller.py`,
`controllers/sistema.py`, `models/termometros.py`, `models/geografia.py`, `services/conectividade.py`,
`views/pagina_inicio.py`, `views/pagina_termometros.py`, `views/pagina_mapa.py`, `views/pagina_qualidade_ar.py`,
`views/filtros_termometros.py`, `views/graficos_comunidade.py`, `views/sessao.py`,
`scripts/preparar_dados_termometros.py`, `scripts/preparar_dados_geograficos.py`, `executavel/*`,
`data/termometros/*`, `data/geo/*`, `tests/test_termometros.py`, `tests/test_geografia.py`,
`tests/test_paginas_v4.py`, `FEEDBACK_UNAS.md`, `ROTEIRO_VIDEO_FINAL.md`, `CHECKLIST_RUBRICA.md`,
`docs/GITHUB_E_RELEASE.md`, `docs/TESTES_REALIZADOS.md`.

**Renomeados (viraram seções):** `views/pagina_visao_geral.py` → `views/ar_resumo.py`;
`views/pagina_temporal.py` → `views/ar_tempo.py`; `views/pagina_comparacao.py` → `views/ar_comparacao.py`;
`views/pagina_sobre_dados.py` → `views/ar_sobre.py` (a nova `pagina_sobre_dados.py` reúne os três conjuntos);
`views/pagina_estatistica.py` → `views/ar_estatistica.py` (a nova `pagina_estatistica.py` reúne os dois conjuntos).

**Alterados:** `app.py`, `services/config.py`, `views/barra_lateral.py`, `views/pagina_ajuda.py`,
`models/fontes.py`, `models/tratamento.py`, `controllers/painel_controller.py` (docstrings), `requirements*.txt`,
`.gitignore`, `README.md`, `GUIA_MANUTENCAO.md`, `docs/FONTES_DE_DADOS.md`, `tests/test_app.py`.

## 3. Decisões técnicas

- **Sem bibliotecas geográficas no app:** os Shapefiles são convertidos uma vez para GeoJSON; o app usa só
  `json` + Plotly. Evita empacotar GDAL/PROJ no executável (fonte comum de falhas).
- **Termômetros nunca viram pontos no mapa:** não há coordenadas validadas e seriam endereços de moradores. A
  região (quebrada) só é destacada quando validada pela UNAS.
- **Período em comum como padrão:** os aparelhos mediram em datas diferentes; comparar meses diferentes
  enviesaria a comparação.
- **Nenhuma medição inventada:** dias sem leitura ficam vazios em todos os gráficos.
- **Executável em modo pasta (onedir):** abre mais rápido que o arquivo único; distribuído como .zip.
