# Guia de manutenção (para iniciantes)

Este guia explica como o painel funciona por dentro e como fazer as mudanças mais comuns, **sem precisar
conhecer Streamlit ou Pandas a fundo**. Cada arquivo `.py` do projeto também tem comentários explicando o
que faz cada parte.

---

## 1. Como executar

**Jeito mais fácil (dois cliques):**

| Sistema | Arquivo |
|---|---|
| Windows | `iniciar.bat` |
| macOS | `iniciar.command` (se bloquear: botão direito → Abrir) |
| Linux | `./iniciar.sh` |

Na primeira vez, o iniciador cria um ambiente virtual (`.venv`) e instala as bibliotecas. Isso exige internet
e Python 3.11 ou mais novo. Depois, o navegador abre em `http://localhost:8501`.

**Pelo terminal:**

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

**Testes automáticos** (conferem se tudo continua funcionando depois de uma mudança):

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Se aparecer `passed` e nenhum `failed`, está tudo certo.

---

## 2. Como os arquivos se comunicam (MVC)

```text
 ┌──────────────────── VIEW (o que aparece na tela) ────────────────────┐
 │ app.py ── menu (7 páginas) e, quando preciso, filtros do ar          │
 │ app_pages/*.py ── um arquivo curto por página do menu                │
 │ views/pagina_*.py ── conteúdo das páginas                            │
 │ views/ar_*.py ── seções de qualidade do ar usadas dentro das páginas │
 │ views/filtros_termometros.py ── filtros numerados dos termômetros    │
 │ views/graficos.py, graficos_comunidade.py ── gráficos e mapa (Plotly)│
 │ views/estilo.py ── cores, textos padrão, formatação                  │
 │ views/sessao.py ── carrega os dados uma vez e guarda os filtros      │
 └───────────────▲─────────────────────────────────┬────────────────────┘
                 │ tabelas e frases prontas          │ filtros escolhidos
 ┌───────────────┴──────────── CONTROLLER ─────────▼────────────────────┐
 │ controllers/painel_controller.py ── qualidade do ar                   │
 │ controllers/termometros_controller.py ── termômetros da UNAS          │
 │ controllers/mapa_controller.py ── mapa de Heliópolis                  │
 │ controllers/sistema.py ── cria os três (um erro não derruba os outros)│
 └───────────────▲─────────────────────────────────┬────────────────────┘
                 │                                   │
 ┌───────────────┴──────────────── MODEL ──────────▼────────────────────┐
 │ models/fontes.py, conjunto.py, tratamento.py, estatistica.py,         │
 │   qualidade_ar.py, parametros.py, localizacao.py ── qualidade do ar   │
 │ models/termometros.py ── leitura das planilhas e cálculos             │
 │ models/geografia.py ── camadas GeoJSON e "ponto dentro da área"       │
 └───────────────────────────────▲──────────────────────────────────────┘
                                 │
   data/ (reais/, termometros/, geo/, demonstracao/, qualar/)
```

**Regra de ouro:** a tela (View) nunca lê arquivos nem faz contas; ela só pede ao Controller.
O Controller não desenha nada; ele pede ao Model. Assim, uma mudança na fonte de dados não exige
mexer nas telas.

**Caminho de um clique.** Quando você troca a estação na barra lateral:

1. o Streamlit roda `app.py` de novo, de cima para baixo;
2. `barra_lateral.renderizar` lê a escolha e cria um `Filtros`;
3. a página chama, por exemplo, `ctrl.indicadores(filtros)`;
4. o Controller pega a tabela da estação (`ConjuntoDados.tabela_larga`), recorta o período e calcula
   (`AnaliseEstatistica`);
5. a página mostra os números e gráficos.

Os dados são lidos do disco **uma vez só** (`@st.cache_resource` em `views/sessao.py`). Por isso, depois de trocar um
arquivo de dados, é preciso **reiniciar o painel** (feche a janela do terminal e abra de novo).

---

## 3. Como atualizar os dados

| Quero... | Faça |
|---|---|
| Atualizar os dados reais (novo ano do MonitorAr) | Baixe o zip no portal do MMA e rode `python scripts/preparar_dados_monitorar.py arquivo1.zip arquivo2.zip --data-download AAAA-MM-DD`. Detalhes em `docs/FONTES_DE_DADOS.md`. |
| Trocar ou acrescentar estações | Edite `data/reais/estacoes.csv` (uma linha por estação, com a fonte das coordenadas) e rode o script de novo. |
| Usar concentrações do QUALAR | Exporte o CSV no QUALAR (exige login) e salve em `data/qualar/`. |
| Usar outro arquivo fictício | Defina `PAE_CSV_PATH` no arquivo `.env` (veja `.env.example`). |
| Atualizar os termômetros (novas planilhas) | Veja "Atualizar os dados dos termômetros", abaixo. |
| Atualizar os mapas | Veja "Atualizar os mapas", abaixo. |

### Atualizar os dados dos termômetros

1. Baixe as planilhas do Drive da UNAS ("Dados dos termômetros") e coloque-as em `data/termometros/bruto/`.
   Essa pasta **não vai para o GitHub** (o nome dos arquivos identifica moradores).
2. Rode `python scripts/preparar_dados_termometros.py`.
   - Cada planilha recebe um número anônimo (T1, T2...). A correspondência fica em
     `data/termometros/bruto/correspondencia.csv` (privada). Planilhas novas recebem o próximo número; as antigas
     mantêm o seu.
   - O script mostra quantas leituras leu e se encontrou problemas (datas inválidas, valores vazios, interrupções).
3. Abra `data/termometros/locais_termometros.csv` (Excel ou Bloco de Notas) e, para cada termômetro, preencha:
   `nome_exibicao` (ex.: "Termômetro 6"), `quebrada` (nome igual ao do mapa, ex.: "Lagoa") e
   `localizacao_validada` = `sim` **somente** quando a UNAS confirmar. **Nunca escreva endereço.**
4. Reinicie o painel e confira *Sobre os Dados → Termômetros* (a conferência com o aparelho deve dar "confere").

### Atualizar os mapas

1. Baixe do Drive da UNAS a pasta do Shapefile **completa** (todos os arquivos com o mesmo nome:
   `.shp`, `.shx`, `.dbf`, `.prj` e `.cpg`) e coloque em `data/geo/bruto/<camada>/<camada>.*`
   (camadas: `recorte`, `quebradas`, `glebas`, `projetos_unas`).
2. Rode `python scripts/preparar_dados_geograficos.py`. Ele converte as coordenadas (SIRGAS 2000 / UTM 23S, em
   metros) para latitude/longitude e grava `data/geo/*.geojson`.
3. Para incluir outra camada, acrescente-a no dicionário `CAMADAS` do script e em `ARQUIVOS_CAMADAS`
   (`models/geografia.py`), e desenhe-a em `views/graficos_comunidade.py` (`mapa_heliopolis`).

**Nunca edite à mão** o arquivo `data/reais/monitorar_estacoes_proximas.csv.gz`. Ele é gerado pelo script e
sua origem está registrada em `metadados_monitorar.json`.

---

## 4. Como adicionar uma nova variável (parâmetro)

Exemplo: o arquivo passou a trazer "PTS" (partículas totais em suspensão).

1. **`models/parametros.py`** → dentro de `PARAMETROS`, acrescente:

   ```python
   Parametro(
       "PTS", "PTS", "Partículas Totais em Suspensão",
       "Explicação simples, sem afirmações médicas.",
       "poluente", 9,   # 9 = posição nas listas
   ),
   ```

   Se o arquivo escrever o nome de outro jeito (ex.: "PTS (Partículas...)"), a função
   `normalizar_codigo` já pega a sigla antes do parêntese. Para outros apelidos, acrescente em `_APELIDOS`.
2. **`views/estilo.py`** → dê uma cor em `COR_PARAMETRO`: `"PTS": "#5a6b7c",`.
3. **(Opcional) `models/qualidade_ar.py`** → se houver limites oficiais, acrescente em
   `LIMITES_CONCENTRACAO`, com o **período de média** e a **unidade** corretos e a fonte citada.
4. Rode `python -m pytest` e abra o painel.

Não é preciso criar colunas: as variáveis aparecem sozinhas quando existem no arquivo.

---

## 5. Como adicionar um gráfico

1. **O cálculo** (se for novo) vai em `models/estatistica.py`, como um método de `AnaliseEstatistica` que
   devolve uma tabela (DataFrame).
2. **O Controller** ganha um método que aplica os filtros e chama o cálculo, como `padroes()` em
   `controllers/painel_controller.py`.
3. **O desenho** vai em `views/graficos.py`: uma função que recebe a tabela e devolve `fig`. Copie uma
   existente (por exemplo, `barras`) e use `_base(fig, titulo, altura)` para manter o visual.
4. **Na página** (`views/pagina_*.py`):

   ```python
   tabela = ctrl.meu_metodo(f)
   st.plotly_chart(graficos.meu_grafico(tabela, v), width="stretch", config=CONFIG_PLOTLY)
   estilo.explicar_grafico(
       "O que o gráfico mostra (uma frase).",
       "Como interpretar (eixos, cores, cuidados).",
       estilo.texto_fonte(ctx),          # sempre informe a fonte
   )
   ```

Regras do projeto: título em português, eixo com unidade, uma cor fixa por parâmetro, nunca dois eixos
verticais com escalas diferentes, e explicação abaixo de todo gráfico.

---

## 6. Como alterar textos e cores

| O quê | Onde |
|---|---|
| Títulos e descrições das páginas | Início de cada `views/pagina_*.py` (`estilo.cabecalho(...)`) |
| Explicações dos termômetros ("Entenda os indicadores") | `views/pagina_termometros.py` → `_entenda()` |
| Nome de cada termômetro e sua quebrada | `data/termometros/locais_termometros.csv` |
| Glossário e perguntas frequentes | `views/pagina_ajuda.py` (lista `GLOSSARIO` e lista `duvidas`) |
| Explicação de cada parâmetro | `models/parametros.py` (campo `descricao`) |
| Textos de ajuda dos filtros | `views/barra_lateral.py` (parâmetro `help=`) |
| Cores do tema (botões, fundo) | `.streamlit/config.toml` **e** os tokens no topo de `views/estilo.py` |
| Cor de cada parâmetro | `views/estilo.py` → `COR_PARAMETRO` |
| Cores das faixas N1–N5 | `models/qualidade_ar.py` → `FAIXAS_IQAR` |
| Nomes das páginas no menu | `app.py` → lista `PAGINAS` |

Frases com **números** (interpretações automáticas) não ficam escritas à mão: elas são montadas em
`PainelController.interpretacoes()` a partir dos cálculos. Ajuste a redação ali, não o número.

---

## 7. Como modificar os filtros

Existem dois conjuntos de filtros:

- **Qualidade do ar** — barra lateral (`views/barra_lateral.py`). O `app.py` só a desenha nas páginas que usam
  esses filtros (função `_precisa_filtros_ar`) e guarda as escolhas ao trocar de página (`_manter_filtros_ar`).
- **Termômetros** — no topo da própria página (`views/filtros_termometros.py`), numerados 1, 2, 3. O parâmetro
  `persist_state="session"` faz o Streamlit lembrar a escolha ao trocar de página (exige Streamlit 1.59+; o
  painel todo exige 1.67+ por causa do `st.Page(help=...)` no `app.py` — veja `requirements.txt`).

**Período dos termômetros — cuidado com data × data e hora.** O filtro devolve dois tipos de período:

| Opção | O que o filtro manda | Como o recorte (`DadosTermometros.recorte`) entende |
|---|---|---|
| Quando todos mediram juntos | `datetime` (data **e hora**) | Exatamente daquele instante até aquele instante |
| Todo o período / Escolher datas | `date` (só a data) | Dias inteiros, de 00h00 do início a 23h59 do fim |

Não troque o período em comum por só a data (`.date()`): o recorte voltaria a pegar o dia inteiro e um termômetro
ficaria com horas que os outros não têm (era o erro corrigido após a auditoria; os testes
`test_periodo_comum_*` e `test_dados_reais_periodo_comum_tem_as_mesmas_horas_para_todos` acusam isso).

Para um filtro novo da qualidade do ar:

1. **Desenhar o controle**: `views/barra_lateral.py`. Use um `key="nome"` único.
2. **Levar o valor adiante**: acrescente um campo no `Filtros` (`controllers/painel_controller.py`) e passe o
   valor no `return Filtros(...)` da barra lateral.
3. **Usar o valor**: normalmente em `PainelController.dados_filtrados()`, que todas as páginas usam.

Cuidado: se o novo filtro depender da estação (como o período), corrija valores inválidos em
`_ajustar_estado()` **antes** de desenhar os controles. O Streamlit só permite alterar `st.session_state`
antes de o controle ser criado.

---

## 8. Erros comuns e como resolver

| Mensagem ou sintoma | Causa provável | Solução |
|---|---|---|
| `Python ... não foi encontrado` | Python não instalado ou fora do PATH | Instale em python.org marcando "Add python.exe to PATH" |
| `ModuleNotFoundError: No module named 'streamlit'` | Bibliotecas não instaladas no ambiente ativo | Ative o `.venv` e rode `pip install -r requirements.txt` (ou use o `iniciar.bat`) |
| Aviso "Recorte de dados reais não encontrado" | Falta `data/reais/monitorar_estacoes_proximas.csv.gz` | Rode `scripts/preparar_dados_monitorar.py` (seção 3) |
| "Nenhuma fonte de dados pôde ser carregada" | Todos os arquivos de dados faltam ou estão corrompidos | Restaure a pasta `data/` a partir do ZIP do projeto |
| QUALAR: "colunas não encontradas: ..." | Cabeçalho do CSV diferente do esperado | Abra o CSV, veja o nome real da coluna e acrescente em `_CANDIDATAS_QUALAR` (`models/fontes.py`) |
| `Port 8501 is already in use` | O painel já está aberto em outra janela | Feche a outra janela ou rode `streamlit run app.py --server.port 8502` |
| O navegador não abriu | Bloqueio do sistema | Abra manualmente `http://localhost:8501` |
| Mudei um arquivo de dados e nada mudou | Dados em cache | Reinicie o painel |
| Mapa sem fundo | O fundo do mapa vem da internet | Normal sem internet; os pontos continuam corretos |
| Página "Temperatura e Umidade" diz que os dados não foram encontrados | Falta `data/termometros/medicoes_termometros.csv.gz` | Rode `scripts/preparar_dados_termometros.py` (seção 3) |
| "Mapa indisponível" | Falta `data/geo/quebradas.geojson` | Rode `scripts/preparar_dados_geograficos.py` (seção 3) |
| O executável fecha logo depois de abrir | Pasta incompleta ou bloqueio do antivírus | Extraia o .zip inteiro; leia `erro_ao_iniciar.txt` na pasta do executável |
| `ModuleNotFoundError` só no executável | Biblioteca nova não incluída no pacote | Acrescente-a em `hiddenimports` (ou `collect_all`) em `executavel/painel_heliopolis.spec` e gere de novo |
| Erro vermelho numa página depois de editar código | Erro de digitação ou de lógica | Leia a última linha do erro (arquivo e linha), desfaça a mudança e rode `python -m pytest` |

---

## 9. Partes que exigem cuidado

- **`models/fontes.py`**: a leitura dos arquivos. Um erro aqui pode trocar valores ou unidades sem dar erro
  visível. Depois de mexer, rode os testes (`tests/test_fontes.py` confere valores contra o arquivo oficial).
- **`models/conjunto.py`**: monta a tabela horária de cada estação. Ela **nunca** deve misturar estações nem
  preencher horas vazias.
- **`models/qualidade_ar.py`**: limites oficiais. Só altere com fonte oficial e respeitando o período de média
  de cada poluente.
- **`views/barra_lateral.py` (`_ajustar_estado`)**: a lógica que mantém os filtros coerentes ao trocar fonte ou
  estação.
- **`data/reais/`**: arquivos gerados com origem registrada; não edite à mão.
- **`data/reais/estacoes.csv`**: toda coordenada precisa de fonte (coluna `fonte_localizacao`).
- **Privacidade (termômetros)**: nunca coloque no repositório, no app ou no executável as planilhas originais,
  o documento de resumo da UNAS (tem endereços) nem a tabela `correspondencia.csv`. O `.gitignore` já bloqueia
  as pastas `bruto/`; confira com `git status` antes de cada commit.
- **`executavel/painel_heliopolis.spec`**: lista do que entra no executável. Só entram dados preparados.
- **Textos de interpretação**: nunca escreva conclusões fixas ("o ar de Heliópolis é...") nem afirme causas.
  Os dados são de estações **próximas**, não do bairro.

---

## 10. Onde está cada coisa

```text
PAE-Heliopolis/
├── app.py                          ponto de entrada (menu e filtros do ar)
├── app_pages/                      um arquivo por página do menu (7)
├── iniciar.bat / .command / .sh    abrir com dois cliques (quem tem Python)
├── controllers/                    painel_controller, termometros_controller, mapa_controller, sistema
├── models/                         fontes, conjunto, tratamento, estatistica, qualidade_ar, parametros,
│                                   localizacao, termometros, geografia
├── views/                          páginas, seções do ar, filtros, gráficos, estilo, sessão
├── services/                       config.py (caminhos), conectividade.py (teste de internet)
├── scripts/                        preparar_dados_monitorar / _termometros / _geograficos, carregar_csv_no_banco
├── executavel/                     inicializador, receita do PyInstaller, script de geração, COMO_USAR.txt
├── data/reais/                     qualidade do ar (recorte oficial, estações, metadados)
├── data/termometros/               medições anônimas, metadados e locais (bruto/ fica fora do Git)
├── data/geo/                       camadas do mapa em GeoJSON (bruto/ fica fora do Git)
├── data/qualar/                    coloque aqui exportações do QUALAR
├── data/demonstracao/              dataset fictício da V1
├── docs/                           requisitos, arquitetura, fontes de dados, GitHub/Release, testes
└── tests/                          testes automáticos (pytest)
```

---

## 11. Como gerar o executável (Windows)

1. Confira que os dados preparados existem (`data/termometros/*.csv.gz` e `data/geo/*.geojson`).
2. Dê dois cliques em `executavel/gerar_executavel.bat` (ou rode-o no terminal, na pasta do projeto).
   Ele instala as dependências, roda o PyInstaller e cria:
   - `dist/PainelHeliopolis/PainelHeliopolis.exe` (para testar);
   - `dist/PainelHeliopolis-Windows.zip` (para publicar na Release do GitHub).
3. Teste o `.exe` e depois faça o **teste obrigatório em um computador sem Python** (veja `executavel/LEIA-ME.md`).

Como funciona: `executavel/iniciar_painel.py` liga o servidor do Streamlit dentro do executável e abre o
navegador. O detalhe mais importante é a opção `global.developmentMode = False`: sem ela, o Streamlit
empacotado tenta usar um servidor de desenvolvimento que não existe e a página não abre.
