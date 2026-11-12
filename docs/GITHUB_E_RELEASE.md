# GitHub: commits por integrante e Release do executável

Este guia explica como publicar a V4 **sem expor dados pessoais** e com **commits reais de cada integrante**.

> Regra do projeto: cada pessoa faz os próprios commits, com a própria conta e identidade. Não crie commits em
> nome de outra pessoa nem reescreva o histórico para simular participação.

## 1. Antes de qualquer commit: conferir a privacidade

```bash
git status
```

Confira que **NÃO** aparecem:

- `data/termometros/bruto/` (planilhas com nomes de moradores e `correspondencia.csv`);
- `data/geo/bruto/` (Shapefiles originais);
- qualquer cópia do documento "Dados dos termômetros" (tem endereços);
- `dist/`, `build/`, arquivos `.exe` ou `.zip` do executável;
- `.env`.

O `.gitignore` já bloqueia esses caminhos. Se algum aparecer, **pare** e corrija o `.gitignore` antes de seguir.

## 2. Configurar a identidade (cada integrante, no próprio computador)

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu-email-do-github@exemplo.com"
```

## 3. Sugestão de divisão em commits por funcionalidade

Cada integrante assume um ou mais blocos, faz `git pull`, copia/ajusta os arquivos do bloco, roda os testes e faz
o commit com a mensagem sugerida (ou uma melhor, com as próprias palavras).

| # | Bloco | Arquivos | Mensagem sugerida |
|---|---|---|---|
| 1 | Correção pandas 3 | `models/fontes.py`, `models/tratamento.py` | `fix: compatibilidade com pandas 3 na leitura das estações e no dia da semana` |
| 2 | Termômetros — leitura e dados | `models/termometros.py`, `scripts/preparar_dados_termometros.py`, `scripts/__init__.py`, `data/termometros/*.csv.gz`, `data/termometros/*.json`, `data/termometros/locais_termometros.csv` | `feat: leitura e anonimização das planilhas dos termômetros da UNAS` |
| 3 | Mapas — conversão e dados | `models/geografia.py`, `scripts/preparar_dados_geograficos.py`, `data/geo/*.geojson`, `data/geo/metadados_geo.json` | `feat: conversão dos Shapefiles da UNAS para GeoJSON` |
| 4 | Controllers novos | `controllers/termometros_controller.py`, `controllers/mapa_controller.py`, `controllers/sistema.py`, `controllers/__init__.py`, `services/config.py`, `services/conectividade.py`, `services/__init__.py` | `feat: controllers dos termômetros e do mapa` |
| 5 | Página Temperatura e Umidade | `views/pagina_termometros.py`, `views/filtros_termometros.py`, `views/graficos_comunidade.py` | `feat: página Temperatura e Umidade com comparação, dia típico e exportação` |
| 6 | Página do Mapa | `views/pagina_mapa.py` | `feat: mapa interativo de Heliópolis com quebradas, glebas e projetos` |
| 7 | Navegação simplificada (feedback UNAS) | `app.py`, `app_pages/`, `views/sessao.py`, `views/pagina_inicio.py`, `views/pagina_qualidade_ar.py`, `views/ar_*.py`, `views/barra_lateral.py`, `views/__init__.py` | `feat: navegação em 7 páginas e filtros só onde são usados (feedback UNAS)` |
| 8 | Explicações na interface (feedback UNAS) | `views/pagina_estatistica.py`, `views/pagina_sobre_dados.py`, `views/pagina_ajuda.py` | `feat: explicações em linguagem simples, glossário e tutorial (feedback UNAS)` |
| 9 | Testes | `tests/` | `test: testes dos termômetros, do mapa e das páginas da V4` |
| 10 | Executável | `executavel/`, `requirements*.txt`, `.gitignore` | `build: executável Windows com PyInstaller` |
| 11 | Documentação | `README.md`, `GUIA_MANUTENCAO.md`, `FEEDBACK_UNAS.md`, `ALTERACOES_V4.md`, `ROTEIRO_VIDEO_FINAL.md`, `CHECKLIST_RUBRICA.md`, `docs/` | `docs: README, guia de manutenção, feedbacks e roteiro da V4` |

Atenção: os blocos 5–8 dependem dos blocos 2–4 (o app só funciona com todos). Faça os commits **em ordem** e
rode `python -m pytest` antes do último.

Comandos de cada commit (exemplo do bloco 2):

```bash
git pull
git add models/termometros.py scripts/preparar_dados_termometros.py scripts/__init__.py data/termometros/medicoes_termometros.csv.gz data/termometros/metadados_termometros.json data/termometros/locais_termometros.csv
git status
git commit -m "feat: leitura e anonimização das planilhas dos termômetros da UNAS"
git push
```

Os arquivos renomeados da V2 (`views/pagina_visao_geral.py` → `views/ar_resumo.py` etc.) devem ir no bloco 7 com
`git add -A views/` para o Git registrar a renomeação.

## 4. Publicar a Release com o executável

1. Gere o executável: `executavel\gerar_executavel.bat` → cria `dist/PainelHeliopolis-Windows.zip`.
2. Faça o teste manual em um computador sem Python (`executavel/LEIA-ME.md`).
3. No GitHub: **Releases → Draft a new release**.
   - *Tag*: `v4.0.0` · *Título*: `V4 — Termômetros da UNAS, mapa e navegação simplificada`
   - Arraste `PainelHeliopolis-Windows.zip` para "Attach binaries".
   - Descrição sugerida: o que é o painel, como usar (os 5 passos de `COMO_USAR.txt`) e o aviso do SmartScreen.
4. Publique e copie o link da Release para o README (topo e seção 4).

Pelo terminal (GitHub CLI), em vez dos passos 3–4:

```bash
gh release create v4.0.0 dist/PainelHeliopolis-Windows.zip --title "V4 — Termômetros da UNAS, mapa e navegação simplificada" --notes-file executavel/COMO_USAR.txt
```

O arquivo zip gerado em 12/11/2026 tem 92,8 MB (a pasta extraída, ~233 MB); o limite por arquivo de Release do GitHub é 2 GB. **Não** versione o
executável no repositório (ele já está no `.gitignore`).
