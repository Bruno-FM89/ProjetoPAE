import pandas as pd
import streamlit as st
import math
import plotly.express as px

st.set_page_config(page_title="Qualidade do Ar em Heliópolis", layout="wide") #titulo da aba e largura da tela
st.title("Inteligencia Climática em Heliópolis") #titulo grande no topo da pagina
st.caption("Dataset fictício, gerado para fins didáticos") #texto pequeno de legenda

#puxar os dados para um dataset
df = pd.read_csv("ambiental_heliopolis.csv", sep=";", encoding="latin1", parse_dates=["Data"]) #leitura csv

st.subheader("Primeiras linhas") #subtitulo
st.dataframe(df.head()) #printa primeiras 5 linhas do DF

st.subheader("Infos gerais")
st.write(f"Linhas: {df.shape[0]} | Colunas {df.shape[1]}") #atd de linhas e colunas
st.write(df.dtypes) #tipo de dado de cada coluna

#Limpeza de dados
## Valores vazios

st.subheader("Valores ausentes por coluna")
st.write(df.isna().sum()) #conta quantos NaN tem na tabela

colunas_poluentes = ["MP10","MP2.5", "O3", "CO", "CO2", "NO2"]
for col in colunas_poluentes: #percorre cada nome da lista um por vez
    df[col] = df[col].fillna(df[col].median()) #preenche os NaN com valores da mediana

##Outliers

def remove_outliers_iqr(df, coluna):
    q1 = df[coluna].quantile(0.25) #valores abaixo do primeiro quartil (25%)
    q3 = df[coluna].quantile(0.75) #valores abaixo do terceiro quartil (75%)
    iqr = q3 - q1 #meio dos dados
    limite_inferior = q1 - 1.5 * iqr #tudo abaixo é considerado outlier baixo
    limite_superior = q3 + 1.5 * iqr #tudo acima é considerado outlier alto
    return df[(df[coluna] >= limite_inferior) & (df[coluna] <= limite_superior)] #devolve o intervalo ok

df_limpo = remove_outliers_iqr(df, "MP2.5") #executa a funcao para a coluna MP2.5

st.write(f"Linhas antes: {df.shape[0]} | Linhas depos da limpeza na coluna MP2.5: {df_limpo.shape[0]}")

#Estatistica Descritiva

st.subheader("Estatistica Descritiva com Pandas")
st.dataframe(df_limpo.describe()) #resumo de estatistica descritiva da tabela 

#Padroes temporais
df_limpo["hora"] = df_limpo["Data"].dt.hour #Cria uma coluna só de hora
df_limpo["dia_semana"] = df_limpo["Data"].dt.day_name() #Cria uma coluna de nome de dia da semana

media_por_hora = df_limpo.groupby("hora")["MP2.5"].mean().reset_index() #agrupa as linhas por hora, tira a media e reset volta para a tablea original

fig_hora = px.line(media_por_hora, x="hora", y="MP2.5", title="MP2.5 médio por hora do dia") #cria o grafico
st.plotly_chart(fig_hora, use_container_width=True)

media_por_dia = df_limpo.groupby("dia_semana")["MP2.5"].mean().reset_index() #agrupa linhas pelo dia da semana

fig_dia = px.bar(media_por_dia, x="dia_semana", y="MP2.5", title="MP2.5 médio por dia da semana")
st.plotly_chart(fig_dia, use_container_width=True)

#Correlação
colunas_correlacao = ["MP10","MP2.5", "O3", "CO", "CO2", "NO2", "Temp", "Umidade"]
matriz_corr = df_limpo[colunas_correlacao].corr() #cria a correlação

fig_corr = px.imshow(matriz_corr, text_auto=".2f", title="Correlação entre poluentes e variáveis meteorológicas")
st.plotly_chart(fig_corr, use_container_width=True)