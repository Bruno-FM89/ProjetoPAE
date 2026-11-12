# Dados que Transformam: Inteligência Climática para Heliópolis — V4

Painel interativo (Python + Streamlit) para a comunidade de **Heliópolis** e a equipe da **UNAS** acompanharem
**calor, umidade e qualidade do ar**, com mapas da comunidade e explicações em linguagem simples em todas as telas.

> **Baixe e use sem instalar nada:** veja [Como usar sem Python](#4-como-usar-sem-python-executável-windows).
> Link da Release com o executável: **`<COLE AQUI O LINK DA RELEASE>`** *(ex.: `https://github.com/USUARIO/REPOSITORIO/releases/latest` — preencher após publicar; veja `docs/GITHUB_E_RELEASE.md`)*

## 1. Contexto e propósito

Heliópolis é uma das maiores comunidades de São Paulo, na região do Ipiranga, zona sul da cidade. A **UNAS**
(União de Núcleos, Associações dos Moradores de Heliópolis e Região) desenvolve projetos sociais, culturais e
educacionais no território e instalou **termômetros em casas de moradores** para entender o calor e a umidade
dentro da comunidade.

Este projeto, feito para a PAE ("Dados que Transformam"), transforma esses dados — e dados oficiais de qualidade
do ar — num painel que **uma pessoa sem conhecimento técnico consegue usar sozinha**. A V4 incorporou os dados
da UNAS e os **feedbacks reais** da equipe da UNAS (veja [`FEEDBACK_UNAS.md`](FEEDBACK_UNAS.md)).

## 2. Funcionalidades

O menu tem 7 partes:

| Página | O que faz |
|---|---|
| **Visão Geral** | Página inicial: um cartão por conjunto de dados com os números principais, botões para cada assunto e "como usar em 3 passos". |
| **Temperatura e Umidade** | Termômetros da UNAS: escolher um ou vários termômetros e o período; média, mínima e máxima; comparação entre locais; evolução no tempo; faixa diária (mín–máx); "dia típico" (hora a hora); mês a mês; tempo acima de um valor escolhido; tabela e download em CSV. |
| **Qualidade do Ar** | Índice de Qualidade do Ar (IQAr) das 6 estações da CETESB mais próximas (6,7–9,8 km), com seções: resumo do período, evolução e padrões no tempo, comparação entre indicadores e estações. |
| **Mapa de Heliópolis** | Mapa interativo com o recorte de Heliópolis, as 7 quebradas, as 15 glebas, os 52 projetos da UNAS (filtráveis por tipo) e as estações da CETESB; ao escolher uma quebrada, mostra área, projetos e termômetros. Funciona sem internet (fundo branco). |
| **Análise Estatística** | Para os dois conjuntos (separados): estatística descritiva, distribuição, boxplot e relação entre medidas (ex.: "Relação entre temperatura e umidade"), sempre com explicação. |
| **Sobre os Dados** | Origem, tratamento, **conferências** (o sistema calcula o mesmo que os aparelhos; as áreas convertidas batem com as originais), inconsistências encontradas, privacidade e limitações. |
| **Ajuda e Tutorial** | Passo a passo com exemplos, glossário (IQAr, umidade relativa, amplitude, quebrada, gleba...) e perguntas frequentes. |

Todo gráfico tem título, unidade, fonte, uma frase sobre o que mostra e a seção "Como interpretar este gráfico".
Todo filtro tem um ícone **?** com explicação.

## 3. Fontes de dados

| Conjunto | Origem | Onde fica no projeto |
|---|---|---|
| **Temperatura e umidade** | Termômetros RC-51H instalados pela UNAS em 5 residências (leitura a cada 10 min; nov/2024–set/2025). Drive "Dados dos termômetros". | `data/termometros/` (anônimo) |
| **Mapas** | Shapefiles da UNAS (recorte, quebradas, glebas, projetos 2020), em SIRGAS 2000 / UTM 23S. Drive de dados geográficos. | `data/geo/` (GeoJSON convertido) |
| **Qualidade do ar** | MonitorAr (Ministério do Meio Ambiente), medições da CETESB, 2024–2025, 6 estações próximas — **fora** de Heliópolis. | `data/reais/` |
| Demonstração | Conjunto fictício da V1, sempre identificado como fictício. | `data/demonstracao/` |

Os três conjuntos **nunca são misturados**. Detalhes, verificações e limitações: [`docs/FONTES_DE_DADOS.md`](docs/FONTES_DE_DADOS.md)
e a página *Sobre os Dados* do painel.

**Privacidade:** os nomes de moradores (presentes no nome das planilhas) foram trocados por "Termômetro 1 a 5";
endereços, fotos e dados pessoais não entram no repositório, no painel nem no executável. Os termômetros não
aparecem como pontos no mapa.

## 4. Como usar sem Python (executável Windows)

1. Na página de **Releases** do repositório, baixe `PainelHeliopolis-Windows.zip`.
2. Clique com o botão direito no arquivo → **Extrair tudo...** (não abra de dentro do .zip).
3. Na pasta extraída, dê dois cliques em **`PainelHeliopolis.exe`**.
4. Uma janela preta abre e, em alguns segundos, o painel aparece no navegador. **Deixe a janela preta aberta**
   enquanto usa; para encerrar, feche-a.
5. Se o Windows mostrar "O Windows protegeu o computador", clique em **Mais informações → Executar assim mesmo**.

Não precisa de internet (só o fundo de ruas do mapa usa internet). Instruções completas: `COMO_USAR.txt`, dentro da pasta.

## 5. Uso para a equipe da UNAS (passo a passo)

1. Abra o painel (executável ou `iniciar.bat`). A **Visão Geral** mostra o que existe e onde clicar.
2. **Qual casa ficou mais quente?** → *Temperatura e Umidade* → deixe o período "Quando todos mediram juntos" →
   *Comparar termômetros*.
3. **A que horas esquenta?** → mesma página → *Dia típico*.
4. **Como está o ar perto do bairro?** → *Qualidade do Ar* → escolha a estação na barra lateral.
5. **Onde ficam os projetos?** → *Mapa de Heliópolis* → ligue "Projetos da UNAS" e escolha uma quebrada.
6. **Baixar os dados** → *Temperatura e Umidade → Tabela e download*.
7. Dúvidas → *Ajuda e Tutorial*.

## 6. Instalação para desenvolvedores

Requisitos: Python 3.11 ou mais novo (testado com 3.13 e 3.14; o executável foi gerado com 3.13) e Streamlit 1.67 ou
mais novo — o `requirements.txt` já garante isso. Com Streamlit mais antigo o painel não abre.

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt   # para rodar o painel
streamlit run app.py
```

Ferramentas de desenvolvimento (testes, preparação dos dados, executável):

```bash
pip install -r requirements-dev.txt
python -m pytest                  # 238 testes automáticos
```

Quem já tem Python pode usar os iniciadores de dois cliques: `iniciar.bat` (Windows), `iniciar.command` (macOS),
`iniciar.sh` (Linux).

## 7. Como atualizar as bases

| Base | Comando | Observação |
|---|---|---|
| Termômetros | `python scripts/preparar_dados_termometros.py` | Planilhas em `data/termometros/bruto/` (fora do Git). Depois, preencha a quebrada de cada termômetro em `data/termometros/locais_termometros.csv`. |
| Mapas | `python scripts/preparar_dados_geograficos.py` | Shapefiles completos em `data/geo/bruto/<camada>/`. |
| Qualidade do ar | `python scripts/preparar_dados_monitorar.py dados_monitorar_2024.zip dados_monitorar_2025.zip` | Arquivos do portal de dados abertos do MMA. |
| Executável | `executavel\gerar_executavel.bat` | Gera `dist/PainelHeliopolis-Windows.zip` para a Release. |

Passo a passo para iniciantes: [`GUIA_MANUTENCAO.md`](GUIA_MANUTENCAO.md).

## 8. Tecnologias

Python · Streamlit (interface web) · Pandas e NumPy (dados) · Plotly (gráficos e mapa) · PyInstaller (executável)
· pyshp e pyproj (só na conversão dos Shapefiles) · openpyxl (só na leitura das planilhas) · pytest (testes)
· SQLAlchemy/PostgreSQL (opcional).

## 9. Arquitetura (MVC) e estrutura do repositório

```text
Usuário → View (app.py, app_pages/, views/) → Controller (controllers/) → Model (models/) → data/
```

```text
├── app.py                 ponto de entrada: menu com 7 páginas
├── app_pages/             um arquivo por página
├── controllers/           painel (qualidade do ar), termômetros, mapa, sistema
├── models/                leitura e cálculos (fontes, termometros, geografia, estatística...)
├── views/                 páginas, gráficos, filtros, estilo
├── services/              configuração e teste de internet
├── scripts/               preparação dos dados
├── executavel/            inicializador e receita do executável (PyInstaller)
├── data/                  dados preparados (as pastas bruto/ ficam fora do Git)
├── docs/                  fontes de dados, arquitetura, GitHub/Release, testes, roteiros
├── tests/                 testes automáticos
├── FEEDBACK_UNAS.md       feedbacks da UNAS e o que foi feito
├── GUIA_MANUTENCAO.md     guia para iniciantes
├── ROTEIRO_VIDEO_FINAL.md roteiro do vídeo
└── CHECKLIST_RUBRICA.md   auditoria da rubrica
```

Detalhes: [`docs/REQUISITOS_E_ARQUITETURA.md`](docs/REQUISITOS_E_ARQUITETURA.md) e [`ALTERACOES_V4.md`](ALTERACOES_V4.md).

## 10. Limitações

- **Termômetros:** 5 casas não representam toda a comunidade; medem o ambiente onde o aparelho foi colocado
  (provavelmente dentro das casas), não a rua; cômodo e altura de instalação ainda não foram registrados; os
  aparelhos mediram em períodos diferentes (por isso a comparação usa, por padrão, só o intervalo — com data e
  hora — em que todos mediram juntos; o primeiro e o último dia desse intervalo são incompletos, igualmente para
  todos); a quebrada de cada termômetro ainda **não foi confirmada** pela UNAS.
- **Qualidade do ar:** não há estação dentro de Heliópolis; os dados do MonitorAr são automáticos e não validados
  pela fonte e trazem o índice (não a concentração).
- **Mapas:** arquivos de 2019–2020; as quebradas mapeadas não cobrem todo o recorte.
- O painel descreve os dados: não faz previsões nem aponta causas.
- O executável é só para Windows e **ainda precisa do teste manual em um computador sem Python**
  (veja [`docs/TESTES_REALIZADOS.md`](docs/TESTES_REALIZADOS.md)).

## 11. Integrantes do grupo

| Nome | RA / matrícula | Principais contribuições |
|---|---|---|
| *(Bruno Fabrini /24.10075-2)* | | |
| *(preencher)* | | |
| *(preencher)* | | |

## Fontes e créditos

- UNAS Heliópolis e Região — dados dos termômetros e arquivos geográficos (Google Drive da UNAS).
- MMA — MonitorAr, dados abertos: <https://dados.mma.gov.br/dataset/5be05b46-3bda-4f6e-9bf2-810e716fff33>
- CETESB — QUALAR: <https://cetesb.sp.gov.br/ar/qualar/> · Padrões de qualidade do ar: <https://cetesb.sp.gov.br/ar/padroes-de-qualidade-do-ar/>
- Fundo do mapa: © colaboradores do OpenStreetMap (ODbL).
