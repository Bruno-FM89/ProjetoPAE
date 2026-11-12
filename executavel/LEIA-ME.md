# Executável do painel (Windows)

| Arquivo | Para que serve |
|---|---|
| `iniciar_painel.py` | Liga o servidor do Streamlit dentro do executável, escolhe uma porta livre, abre o navegador e mostra erros em português (gravando `erro_ao_iniciar.txt`). |
| `painel_heliopolis.spec` | Receita do PyInstaller: o que entra no executável (código, dados preparados, arquivos do Streamlit e do Plotly). |
| `gerar_executavel.bat` | Gera tudo com dois cliques: `dist/PainelHeliopolis/` e `dist/PainelHeliopolis-Windows.zip`. |
| `COMO_USAR.txt` | Instruções para quem vai usar (copiado para dentro da pasta do executável). |

## Gerar

```bash
executavel\gerar_executavel.bat
```

Requisitos: Windows, Python 3.11–3.13 (o executável é gerado com 3.13) e os dados preparados em `data/` (o script confere). Leva de 5 a 10
minutos. Último resultado (12/11/2026): pasta de ~227 MB e zip de 92,8 MB (SHA-256 em `docs/TESTES_REALIZADOS.md`).

## Por que estas escolhas

- **Pasta + zip (onedir), não arquivo único:** o modo arquivo único descompacta ~230 MB a cada abertura (lento e
  frequentemente bloqueado por antivírus).
- **Sem bibliotecas geográficas:** os mapas já vêm convertidos em GeoJSON; o executável não precisa de GDAL/PROJ.
- **`global.developmentMode = False`:** sem isso o Streamlit empacotado acha que está em desenvolvimento e não
  serve a página.
- **Janela de console visível:** mostra o endereço do painel e serve para encerrá-lo (basta fechar).

## Teste manual OBRIGATÓRIO em um computador sem Python

O teste automático foi feito na máquina de desenvolvimento simulando a ausência de Python (veja
`docs/TESTES_REALIZADOS.md`). Isso **não substitui** o teste num computador limpo. Antes de entregar:

1. Use um computador (ou máquina virtual / Windows Sandbox) **sem Python instalado**. Confirme: abra o Prompt de
   Comando e digite `python --version` — deve dizer que não foi encontrado (ou abrir a Microsoft Store).
2. Baixe `PainelHeliopolis-Windows.zip` **da Release do GitHub** (não de um pendrive), para testar o arquivo real.
3. Confira se o arquivo é o mesmo que foi gerado: no PowerShell, `Get-FileHash PainelHeliopolis-Windows.zip` deve
   mostrar o SHA-256 registrado em `docs/TESTES_REALIZADOS.md`.
4. Extraia, abra `PainelHeliopolis.exe` e anote:

| Verificação | OK? |
|---|---|
| O SmartScreen apareceu? Conseguiu "Executar assim mesmo"? | |
| A janela preta mostrou o endereço (http://localhost:85xx)? | |
| O navegador abriu sozinho em menos de 1 minuto? | |
| Visão Geral mostra 5 termômetros, 6 estações e 7 quebradas? | |
| Temperatura e Umidade: gráficos aparecem; o botão "Baixar esta tabela" baixa o CSV? | |
| Temperatura e Umidade: o período diz "17/02/2025 às 19h00 a 12/06/2025 às 00h10" e "Leituras analisadas 82.240"? | |
| Mapa aparece (com ruas, se houver internet)? | |
| **Sem internet** (Wi-Fi desligado): o painel abre e o mapa aparece sobre fundo branco? | |
| Qualidade do Ar, Análise Estatística, Sobre os Dados e Ajuda abrem sem erro? | |
| Fechar a janela preta encerra o painel? | |
| Abrir duas vezes: a segunda usa outra porta (8502) e funciona? | |

5. Registre o resultado (data, versão do Windows, quem testou) em `docs/TESTES_REALIZADOS.md` e no
   `CHECKLIST_RUBRICA.md`.
