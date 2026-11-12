@echo off
setlocal
cd /d "%~dp0"
title Inteligencia Climatica - Heliopolis

rem --- procura um Python 3.10 ou mais novo (primeiro o lancador "py", depois "python") ---
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo.
    echo Python 3.10 ou mais novo nao foi encontrado.
    echo Instale em https://www.python.org/downloads/ e marque "Add python.exe to PATH".
    echo Depois de instalar, de dois cliques neste arquivo de novo.
    echo.
    pause
    exit /b 1
)

rem --- ambiente virtual (.venv): copia isolada do Python so para este projeto ---
rem --- as bibliotecas do requirements.txt sao instaladas so na primeira vez ---
if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual ^(so na primeira vez^)...
    %PY% -m venv .venv
    if errorlevel 1 goto erro
)

".venv\Scripts\python.exe" -c "import streamlit, pandas, plotly" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias ^(so na primeira vez, pode levar alguns minutos^)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto erro
)

rem --- evita que o Streamlit pare na primeira execucao pedindo um e-mail ---
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    mkdir "%USERPROFILE%\.streamlit" >nul 2>nul
    > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

echo.
echo Iniciando o painel. O navegador abre em instantes.
echo Para encerrar, feche esta janela.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto erro
exit /b 0

:erro
echo.
echo Ocorreu um erro. Leia a mensagem acima.
pause
exit /b 1
