# Origem dos dados

> **V4:** o painel passou a ter três conjuntos de dados independentes: **qualidade do ar** (seções 1–7, abaixo), **termômetros da UNAS** (seção 8) e **arquivos geográficos da UNAS** (seção 9). Eles nunca são misturados. A análise dos dois Drives da UNAS foi feita em **12/11/2026**.

Este documento registra **de onde vêm os dados do painel**, como foram verificados, o que foi
feito com eles e como atualizá-los. Toda informação abaixo foi conferida em **08/11/2026**.

> **Resumo:** os dados reais são medições oficiais da **CETESB**, publicadas no **MonitorAr**
> (Ministério do Meio Ambiente) como arquivos anuais de dados abertos. Usamos as **6 estações mais
> próximas de Heliópolis**, a 6,7–9,8 km em linha reta. **Nenhuma delas fica dentro do bairro.**
> Para essas estações, o arquivo traz o **Índice de Qualidade do Ar (IQAr)**, e não a concentração
> dos poluentes nem dados de temperatura e umidade.

## 1. Fontes verificadas

| Fonte | Acesso | O que oferece | Usada? |
|---|---|---|---|
| **MonitorAr — Portal de Dados Abertos do MMA** | Público, sem login. Licença Creative Commons Atribuição | Arquivos anuais (2022–2025), um CSV por ano dentro de um zip, com dados horários de todas as redes integradas | **Sim**: 2024 e 2025 |
| **QUALAR — CETESB** | Exige login (cadastro gratuito) para exportar | CSV com médias horárias de **concentração** (µg/m³, ppm), temperatura, umidade e vento, por estação e parâmetro | **Infraestrutura pronta**: importador em `data/qualar` |
| **Serviço ArcGIS da CETESB** (`.../QUALAR/CETESB_QUALAR/MapServer`) | Público (consulta) | Lista das 62 estações ativas com endereço e coordenadas, e **só as últimas 48 horas** de MP10, MP2,5, O3, CO, NO2 e SO2 (campos `M1`…`M48`) | **Só as coordenadas das estações** |
| Portal de Dados Abertos da CETESB (ficha "LEIA-ME") | Público | Aponta para o QUALAR, boletins e relatórios | Para referência (condição de uso: citar a fonte) |

### Por que o serviço ArcGIS não foi usado como série de dados

O serviço foi testado de verdade (consultas `query` com retorno em JSON). Ele funciona, mas:

- guarda apenas as **48 horas mais recentes** (campos `M1`…`M48` com as datas em `TM1`…`TM48`), então não há histórico;
- **não documenta a unidade** dos valores `M1`…`M48` (concentração ou índice), e o enunciado proíbe tratar
  unidades duvidosas como equivalentes;
- não traz temperatura nem umidade.

Ele foi usado apenas como fonte oficial das **coordenadas e endereços** das estações
(camada `QUALAR_DADOSHORARIOS_PTO`).

## 2. Estações usadas

O ponto de referência de Heliópolis vem do **OpenStreetMap** (área residencial "HELIOPOLIS",
objeto *way* 566841451, distrito Ipiranga, coordenadas −23,6073672 / −46,5810343, consultado pelo
serviço Nominatim). É um ponto **aproximado**, usado só para estimar distâncias em linha reta.

| Estação | Município | Distância (km) | Horas com IQAr | Poluentes no arquivo | Código QUALAR* |
|---|---|---|---|---|---|
| Mooca | São Paulo | 6,7 | 88% | MP2,5, O3, CO | 85 |
| Ibirapuera | São Paulo | 8,3 | 92% | MP2,5, O3, NO2 | 83 |
| Parque D. Pedro II | São Paulo | 8,4 | 90% | MP2,5, MP10, O3, NO2 | 72 |
| Congonhas | São Paulo | 8,5 | 89% | MP2,5, MP10, NO2, CO, SO2 | 73 |
| Diadema | Diadema | 9,3 | 77% | MP10, O3 | 92 |
| S. André-Capuava | Santo André | 9,8 | 92% | MP10, O3, NO2, SO2, benzeno | 100 |

\* Códigos usados na exportação do QUALAR, conforme a tabela `cetesb_aqs` do pacote científico
**qualR** (rOpenSci). Confira-os na tela do QUALAR.

**Estações procuradas e não usadas**

- **São Caetano do Sul**: existia na rede da CETESB (código 86 no qualR), mas **não aparece entre as 62 estações
  ativas** do serviço da CETESB consultado. Também não há linhas dela nos arquivos do MonitorAr de 2024–2025.
- **Ipiranga / Cambuci**: não existe estação "Ipiranga" na Região Metropolitana; Cambuci (código 90 no qualR)
  não está entre as ativas.
- **S. Bernardo-Paulicéia** (7,1 km): tem só 1.984 registros esparsos de MP10 em 2024–2025 e não está na lista de ativas da CETESB.
- **Santo Amaro**: no arquivo do MonitorAr aparece com município "Santo André" e com as coordenadas da Capuava, o que a colocaria a 7,6 km. Pela coordenada da CETESB, fica a cerca de 14 km e por isso não entrou.
- **S. Bernardo-Centro** (10,8 km): ativa, mas mais distante que as seis escolhidas. Pode ser acrescentada em `estacoes.csv`.

## 3. Arquivos oficiais e verificação

| Arquivo | Publicado no portal | Tamanho | SHA-256 |
|---|---|---|---|
| `dados_monitorar_2024.zip` | 19/12/2025 | 22.074.775 bytes | `765e2e0e4fa9569d463e6816af5891daefba05fb04c777d25feaa8b6914659b6` |
| `dados_monitorar_2025.zip` | 04/02/2026 | 31.784.392 bytes | `5a19031caf1c989286ed4fa49f62b1dab2ce2ae6a19200c731d60ebcfee7b010` |

Página do conjunto: <https://dados.mma.gov.br/dataset/5be05b46-3bda-4f6e-9bf2-810e716fff33>.
O **dicionário de dados oficial** está em `docs/fontes/arquivo-auxiliar-dados-monitorar.pdf`.

Para conferir: baixe o arquivo no portal e calcule o SHA-256 (no Windows: `certutil -hashfile arquivo.zip SHA256`;
no Linux/Mac: `sha256sum arquivo.zip`). O valor precisa ser idêntico ao da tabela.

**O recorte do projeto** (`data/reais/monitorar_estacoes_proximas.csv.gz`, 92.753 linhas) contém as linhas
dessas 6 estações **copiadas sem nenhuma alteração** (todas as células lidas como texto). Foi acrescentada uma
única coluna, `arquivo_origem`. Os detalhes estão em `data/reais/metadados_monitorar.json`.

## 4. Características dos dados (descobertas na análise)

1. **Só índice, sem concentração.** Para as linhas da CETESB, a coluna `nu_concentracao` está vazia em 100% dos
   casos; só `nu_iqar` é preenchida. Também não há temperatura nem umidade. O painel mostra essas
   informações como **indisponíveis**.
2. **Um único poluente por hora.** Nas 92.753 linhas, nenhuma estação tem dois poluentes na mesma hora. O
   comportamento é compatível com o arquivo trazer o índice do poluente que definiu a classificação da estação
   naquela hora, mas **o dicionário não explica essa regra**. Consequências tratadas no painel:
   - foi criada a variável **"IQAr da estação"**: em cada hora, o maior índice entre os poluentes, que é a regra de
     classificação da CETESB. É a série mais completa e a variável padrão;
   - a média de um poluente só cobre as horas em que ele foi o registrado: o painel avisa;
   - **correlações entre esses indicadores não são calculadas**, e a tela explica o motivo.
3. **Cobertura parcial**: a estação com mais horas tem IQAr em 92% delas. As lacunas não são preenchidas na versão original.
4. **Coordenadas incoerentes em 2025**: várias estações da capital aparecem com a mesma coordenada genérica
   (−23,5475 / −46,636111). Por isso as coordenadas vêm do serviço oficial da CETESB.
5. **Coluna renomeada entre anos**: o status da medição se chama `st_situacao_item` em 2024 e `st_situacao` em
   2025. Na leitura, as duas são unificadas em `situacao`.
6. **Aviso da própria fonte**: os dados "podem conter inconsistências, falhas de medição, lacunas temporais ou
   registros ainda não submetidos aos procedimentos de validação técnica". Para estudos técnicos, a fonte recomenda
   os dados validados do órgão responsável (no caso, o QUALAR da CETESB).

## 5. Como atualizar os dados reais (MonitorAr, sem login)

1. Acesse a página do conjunto (link acima) e baixe os arquivos `dados_monitorar_AAAA.zip` desejados.
2. Na pasta do projeto, rode (um ou mais arquivos):

   ```bash
   python scripts/preparar_dados_monitorar.py CAMINHO/dados_monitorar_2024.zip CAMINHO/dados_monitorar_2025.zip --data-download AAAA-MM-DD
   ```

3. O script substitui `data/reais/monitorar_estacoes_proximas.csv.gz` e `metadados_monitorar.json`.
4. Reinicie o painel.

Para mudar as estações, edite `data/reais/estacoes.csv` (coluna `id_estacao_monitorar` = coluna `id_estacao`
do arquivo oficial) e rode o script de novo. Informe a fonte de cada coordenada nova.

## 6. Como obter concentrações e meteorologia (QUALAR, com login)

O QUALAR é o sistema oficial da CETESB. A exportação **exige login**. O cadastro é gratuito e deve ser feito
pela própria pessoa usuária; este projeto **não** guarda nem usa credenciais.

1. Acesse <https://qualar.cetesb.sp.gov.br/> e entre com seu usuário (ou cadastre-se).
2. Abra **Consultas → Exportar Dados**.
3. Escolha: **Rede** automática; **Tipo de dado**: média horária; a **estação** (veja os códigos na seção 2);
   o **parâmetro** (ex.: MP10, MP2.5, O3, NO2, TEMP, UR) e o **período**.
4. Exporte em **CSV** e salve o arquivo na pasta `data/qualar` do projeto, um arquivo por consulta.
5. Reinicie o painel: aparece a fonte "Dados reais — QUALAR importado (CETESB)".

**Formato esperado.** Não foi possível obter um arquivo real de exportação durante o desenvolvimento, porque o
QUALAR exige login. O leitor (`ler_exportacao_qualar` em `models/fontes.py`) procura as colunas **pelo nome**:
`Data`, `Hora`, `Nome Estação`, `Nome Parâmetro`, `Unidade de Medida`, `Média Horária` e `Válido`, com
separador `;` e decimal com vírgula. Esses nomes seguem a tabela lida pelo pacote **qualR** (rOpenSci), que
acessa a mesma exportação. Se o arquivo real for diferente, a mensagem de erro diz qual coluna faltou; ajuste
a lista `_CANDIDATAS_QUALAR`. O horário "24:00" é convertido para 00:00 do dia seguinte, e linhas com
`Válido = Não` são descartadas (o arquivo original não é alterado).

## 7. Como citar

> Ministério do Meio Ambiente e Mudança do Clima. *Sistema Nacional de Gestão da Qualidade do Ar — MonitorAr*.
> Dados de 2024 e 2025 (medições da CETESB). Portal de Dados Abertos do MMA, licença Creative Commons Atribuição.
> Acesso em 08/11/2026.

Faixas de qualidade do ar: CETESB, "Padrões de qualidade do ar" (Resolução CONAMA nº 491/2018).
Ponto de referência de Heliópolis: © colaboradores do OpenStreetMap (ODbL).


---

## 8. Termômetros da UNAS (temperatura e umidade dentro de Heliópolis)

**Origem:** Google Drive da UNAS, pasta "Dados dos termômetros": 5 planilhas e o documento "Dados dos
termômetros". **Os nomes dos arquivos (primeiros nomes de moradores) não aparecem no projeto**: no painel, nos
dados preparados, no executável e nesta documentação os aparelhos são "Termômetro 1 a 5". A correspondência
fica só em `data/termometros/bruto/correspondencia.csv`, no computador da equipe (fora do Git).

### 8.1 Estrutura das planilhas (verificada em todas as 5)

| Item | Valor encontrado |
|---|---|
| Formato real | Excel 2007+ (**.xlsx**), apesar da extensão `.xls` |
| Abas | `Resumo` (relatório do aparelho), `Lista` (série completa), `Gráfico` (só uma imagem) |
| Aparelho | registrador **RC-51H**, sensor "Temperatura & Umidade (Interna)" = sensor embutido no aparelho |
| Colunas da `Lista` | Nº da leitura · Tempo (`AAAA-MM-DD hh:mm:ss`) · Temperatura (°C) · Umidade (%RH) |
| Formato dos números | **texto** com vírgula decimal ("28,6") |
| Intervalo | 10 minutos (configurado e observado) |
| Fuso horário | UTC −03:00 (horário de Brasília) |
| Leituras por aparelho | **32.000** em todos (memória cheia: 222 dias, 5 h e 10 min) |
| Valores ausentes | **nenhum** |
| Horários repetidos ou fora de ordem | **nenhum** |
| Interrupções na sequência de 10 min | **nenhuma** |
| Umidade fora de 0–100 % | **nenhuma** |

### 8.2 Período de cada aparelho

| Termômetro | Primeira leitura | Última leitura |
|---|---|---|
| Termômetro 1 | 11/02/2025 18:00 | 21/09/2025 23:10 |
| Termômetro 2 | 17/02/2025 19:00 | 28/09/2025 00:10 |
| Termômetro 3 | 01/11/2024 19:00 | 12/06/2025 00:10 |
| Termômetro 4 | 11/02/2025 18:20 | 21/09/2025 23:30 |
| Termômetro 5 | 11/02/2025 18:00 | 21/09/2025 23:10 |

Período em que **todos** mediram: **17/02/2025 a 12/06/2025**. Por isso o painel usa esse período, por padrão,
para comparar locais.

### 8.3 Diferenças e inconsistências

- Extensão `.xls` com conteúdo `.xlsx` (o leitor abre pelo conteúdo).
- O Termômetro 3 mediu num período diferente dos demais (nov/2024–jun/2025). Não foi possível verificar, pelos
  arquivos, se o relógio do aparelho estava certo; registrar com a UNAS.
- O documento de resumo traz os mesmos máximos, mínimos e médias do relatório dos aparelhos. As médias do
  aparelho são **cortadas** na 1ª casa decimal (ex.: 21,77 → 21,7), por isso diferem até 0,09 do cálculo exato.
  O painel confere os 30 valores (5 aparelhos × 2 medidas × máx/mín/média): **30 de 30 conferem**.
- O documento lista **6 locais** (inclui endereços), mas há **5 planilhas**; a correspondência local ↔ planilha
  não está documentada. **Os endereços não foram usados nem copiados para o projeto.**
- O documento indica dados ainda não coletados: cômodo, altura de instalação, número de moradores etc.
- O resumo do documento **não** substitui as séries: o painel usa as 160.000 leituras originais.

### 8.4 Tratamento

Script `scripts/preparar_dados_termometros.py` (código comentado em `models/termometros.py`):
texto → número (sem arredondar); verificação de datas, duplicatas, vazios, faixa de umidade e interrupções;
nenhum valor preenchido, estimado ou removido; anonimização; gravação em
`data/termometros/medicoes_termometros.csv.gz` + `metadados_termometros.json` (com SHA-256 de cada planilha).

### 8.5 Localização

Nenhuma coordenada foi atribuída a residências ou sensores. O arquivo `data/termometros/locais_termometros.csv`
guarda apenas a **quebrada** (região) de cada termômetro e se ela foi **validada** pela UNAS. Situação atual:
nenhuma validada; Termômetros 3 e 4 com região sugerida "Lagoa" (pelo nome da planilha), a confirmar.

---

## 9. Arquivos geográficos da UNAS (mapa)

**Origem:** Google Drive da UNAS com dados geográficos de Heliópolis (dezenas de camadas). Foram usadas as 4
camadas pedidas para a V4:

| Camada (pasta no Drive) | Tipo | Itens | Atributos | Observações |
|---|---|---|---|---|
| `SIRGAS_SHP_recorte_heliópolis` | polígono | 1 | ID, NOME, area, area_m, AREA_1 | Contorno de Heliópolis (2,46 km²). O atributo NOME traz "Cazinhas", que não descreve a camada. |
| `SIRGAS_SHP_quebradas_heliópolis` | polígono | 7 | ID, NOME, area, area km | Mina, Lagoa, Paquistão, Heliópolis, Imperador / Pilões, COHAB, Redondinhos / João Lanhoso. Somam 1,37 km² (não cobrem todo o recorte). |
| `SIRGAS_SHP_glebas_heliópolis` | polígono | 15 | Nome, ID | Glebas A a N (inclui "L L 2" e "L1"). |
| `SIRGAS_SHP_Projetos_UNAS_Atualizado2020` | ponto (com Z) | 52 | Name, descriptio, Tipo | CEIs, CCAs, cultura, esporte etc.; 27 dentro do recorte, os demais em bairros vizinhos. Descrições cortadas em 254 caracteres (limite do .dbf). |

Todas as partes de cada Shapefile (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`; algumas também `.qpj`/`.qgz`) foram
baixadas e lidas **juntas**. Sistema de coordenadas: **SIRGAS 2000 / UTM zona 23S (EPSG:31983)**; codificação
das tabelas: UTF-8 (confirmada).

**Conversão** (`scripts/preparar_dados_geograficos.py`): para WGS 84 (latitude/longitude) com pyproj;
gravação em GeoJSON (`data/geo/`). Para a escala de um bairro, SIRGAS 2000 e WGS 84 diferem menos de 1 m.
**Conferência:** as áreas calculadas pelo sistema diferem menos de 0,02 % das áreas gravadas na tabela original.

**Camadas não usadas (ainda):** setores censitários (2000 e 2010), logradouros, relevo, declividade, educação,
assistência, esporte, cultura, conectividade, bairros do entorno, distrito e prefeitura regional do Ipiranga,
quebradas individuais (redundantes com a camada combinada) e outras. Podem ser acrescentadas seguindo o
`GUIA_MANUTENCAO.md`.
