# Roteiro do vídeo final — V4 (8 a 10 minutos)

Este vídeo também será **material de estudo da UNAS**: fale devagar, mostre a tela e explique o "porquê" de cada
coisa. Sugestão: dividir as falas entre os integrantes (coluna "Quem"). Grave em tela cheia, com o navegador em
zoom de 110–125% para as letras ficarem legíveis.

**Preparação:** abra o painel pelo **executável** (`PainelHeliopolis.exe`) antes de gravar; deixe abertos, em
abas, o repositório no GitHub (README e Releases) e o VS Code com `models/termometros.py`.

| Tempo | Quem | Parte |
|---|---|---|
| 0:00–0:45 | *(integrante 1)* | 1. Abertura: objetivo e equipe |
| 0:45–1:30 | *(integrante 1)* | 2. Os dados reais (três conjuntos) |
| 1:30–3:30 | *(integrante 2)* | 3. Temperatura e Umidade (termômetros da UNAS) |
| 3:30–4:30 | *(integrante 2)* | 4. Mapa de Heliópolis |
| 4:30–5:15 | *(integrante 3)* | 5. Qualidade do Ar e Análise Estatística |
| 5:15–7:00 | *(integrante 3)* | 6. **Feedbacks da UNAS: o que mudou** |
| 7:00–8:15 | *(integrante 4)* | 7. Código, arquitetura e organização |
| 8:15–9:15 | *(integrante 4)* | 8. Executável, GitHub e README |
| 9:15–9:45 | todos | 9. Encerramento: limitações e próximos passos |

---

## 1. Abertura (0:00–0:45)

**Mostrar:** a página *Visão Geral*.

> "Olá! Somos [nomes]. Este é o painel **Inteligência Climática para Heliópolis**, feito para a comunidade e para
> a equipe da UNAS acompanharem o calor, a umidade e a qualidade do ar. A ideia é que qualquer pessoa consiga
> usar, sem saber programação nem estatística."

## 2. Os dados reais (0:45–1:30)

**Mostrar:** os três cartões da Visão Geral; depois *Sobre os Dados*.

> "O painel trabalha com três conjuntos de dados, que **nunca são misturados**:
> 1. **termômetros da UNAS**, instalados em cinco casas de Heliópolis — são as únicas medições feitas dentro
>    da comunidade;
> 2. **qualidade do ar** das estações oficiais da CETESB mais próximas — que ficam entre 6,7 e 9,8 km do bairro,
>    ou seja, fora de Heliópolis;
> 3. os **mapas** da UNAS: o contorno de Heliópolis, as quebradas, as glebas e os projetos."

**Mostrar** *Sobre os Dados → Termômetros → Conferência*: "30 de 30 valores conferem".

> "Para garantir que lemos as planilhas corretamente, comparamos nossos cálculos com o resumo que o próprio
> aparelho grava. Os 30 valores conferem."

## 3. Temperatura e Umidade (1:30–3:30)

**Mostrar e falar, passo a passo:**

1. Caixa verde no topo: "medições feitas DENTRO de Heliópolis... os termômetros aparecem como Termômetro 1, 2,
   3, sem nomes nem endereços" → **explique a proteção dos moradores**.
2. Abrir "Quem é cada termômetro e quando mediu" → mostrar que os períodos são diferentes.
3. Filtros numerados: **1** termômetros (clicar para tirar e pôr um), **2** período "Quando todos mediram juntos"
   (explicar por que é a comparação justa), **3** forma de mostrar os valores, **4** temperatura ou umidade.
4. Faixa de números (média, máxima, mínima) e a caixa **"O que os dados mostram"** (frases calculadas).
5. **Comparar termômetros**: ler o gráfico em voz alta ("cada linha vai do menor ao maior valor; o círculo é a
   média"). Mostrar a tabela e o "Quanto tempo ficou acima de um valor?" (arrastar o controle).
6. **Ao longo do tempo** → passar o mouse, clicar na legenda; mostrar a faixa do dia de um termômetro.
7. **Dia típico** → "a temperatura costuma subir até cerca de 15h e cair até cerca de 7h".
8. **Mês a mês** → comparar períodos. **Tabela e download** → baixar o CSV.
9. Abrir "Como interpretar este gráfico" e "Entenda os indicadores".

## 4. Mapa de Heliópolis (3:30–4:30)

1. Explicar a linha preta (recorte) e as cores (quebradas, com nomes).
2. Ligar "Projetos da UNAS" e filtrar por "CEI"; passar o mouse num ponto.
3. Escolher a quebrada **Lagoa** → área, projetos e termômetros.
4. Ligar "Estações de qualidade do ar": "vejam como as estações ficam longe do bairro".
5. Mostrar "Termômetros no mapa": "por privacidade, nunca mostramos a casa. No máximo a quebrada, e só depois
   que a UNAS confirmar".
6. Se der, desligar o Wi-Fi e mostrar o mapa sobre fundo branco: "funciona sem internet".

## 5. Qualidade do Ar e Análise Estatística (4:30–5:15)

1. *Qualidade do Ar*: mostrar o aviso "NÃO foram medidos dentro de Heliópolis", a estação e a distância na barra
   lateral, o Resumo (faixas Boa/Moderada) e o seletor "O que você quer ver?".
2. *Análise Estatística → Relação entre temperatura e umidade*: "quando a casa esquenta, o ar fica mais seco —
   a relação é negativa", e abrir "O que significa cada coluna?".

## 6. Feedbacks da UNAS: o que mudou (5:15–7:00)

> "A UNAS usou a versão anterior e nos deu quatro retornos. Vamos mostrar o que fizemos com cada um."

**Quais dificuldades a UNAS identificou** (mostrar `FEEDBACK_UNAS.md` rapidamente):
1. o site precisava ser mais fácil de usar;
2. faltava explicar o que cada seção, gráfico, tabela e indicador mostra;
3. a navegação era complicada para quem tem pouca familiaridade com tecnologia;
4. o código precisava de comentários simples para facilitar a manutenção.

**Como a interface foi simplificada — mostrar o antes e depois:**
- *Antes:* 6 itens de menu, todos de qualidade do ar, e 8 filtros na barra lateral em todas as páginas.
  *Depois:* 7 itens por **assunto**, começando pela Visão Geral; a barra lateral só tem filtros na Qualidade do
  Ar (navegar entre Mapa e Qualidade do Ar para mostrar).
- Os filtros dos termômetros ficaram **numerados** no topo da página.
- O painel **lembra** as escolhas ao trocar de página (trocar de estação, ir ao Mapa e voltar).
- No mapa, a rodinha do mouse rola a página em vez de dar zoom (evita ficar "preso").

**Quais explicações foram adicionadas — mostrar exemplos concretos:**
- frase de objetivo no topo de cada página;
- "Como interpretar este gráfico" embaixo de todos os gráficos;
- "Correlação de Pearson" virou **"Relação entre temperatura e umidade"**, com o resultado em palavras;
- glossário novo (umidade relativa, amplitude, quebrada, gleba...) e tutorial com exemplos em *Ajuda*.

**Como o back-end ficou mais compreensível:** abrir `models/termometros.py` e mostrar o comentário do topo
("De onde vêm estes dados") e a docstring de `periodo_comum`; abrir `GUIA_MANUTENCAO.md`, seção "Atualizar os
dados dos termômetros".

**Atendidos e pendentes:**
> "Os quatro pedidos foram implementados e testados por nós. O que **falta** é a validação com pessoas da UNAS
> usando o painel — deixamos um roteiro de 10 minutos no `FEEDBACK_UNAS.md`. Também depende da UNAS confirmar em
> qual quebrada está cada termômetro e registrar o cômodo e a altura dos aparelhos."

## 7. Código, arquitetura e organização (7:00–8:15)

1. Mostrar as pastas: `models/` (dados e contas), `controllers/` (organiza os pedidos), `views/` e `app_pages/`
   (telas) — **MVC**.
2. Seguir um clique: filtro da página → `FiltrosTermometros` → `TermometrosController.resumo` →
   `AnaliseTermometros.resumo` → tabela de volta para a página.
3. `scripts/preparar_dados_termometros.py`: troca os nomes por números e grava um arquivo único;
   `scripts/preparar_dados_geograficos.py`: converte as coordenadas dos Shapefiles (metros → latitude/longitude).
4. Rodar `python -m pytest` (ou mostrar o resultado gravado): 228 testes passando.

## 8. Executável, GitHub e README (8:15–9:15)

1. No GitHub, **Releases** → `PainelHeliopolis-Windows.zip`.
2. Extrair, dois cliques em `PainelHeliopolis.exe`, janela preta, navegador abrindo. Mostrar `COMO_USAR.txt`.
3. README: seções "Como usar sem Python", "Uso para a equipe da UNAS" e "Como atualizar as bases".
4. Histórico de commits: cada integrante com seus commits.

## 9. Encerramento (9:15–9:45)

> "Limitações: são só cinco casas; os aparelhos mediram em períodos diferentes; a qualidade do ar vem de
> estações fora do bairro; e os mapas são de 2019–2020. Próximos passos: validar o painel com a equipe da UNAS,
> confirmar a localização dos termômetros e incluir novas medições. Obrigado!"
