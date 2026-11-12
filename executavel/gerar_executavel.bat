@echo off
rem Gera o executavel do painel para Windows (pasta dist\PainelHeliopolis e o arquivo .zip para a Release).
rem Requisitos: Python 3.11 a 3.13 instalado e as dependencias de desenvolvimento.
rem Uso: de dois cliques neste arquivo OU rode "executavel\gerar_executavel.bat" na pasta do projeto.
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -3.13 -m venv .venv || py -3 -m venv .venv || goto erro
)
echo Instalando dependencias (inclui PyInstaller)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt || goto erro

echo Conferindo se os dados preparados existem...
if not exist "data\termometros\medicoes_termometros.csv.gz" (
    echo FALTA data\termometros\medicoes_termometros.csv.gz. Rode scripts\preparar_dados_termometros.py antes.
    goto erro
)
if not exist "data\geo\quebradas.geojson" (
    echo FALTA data\geo\quebradas.geojson. Rode scripts\preparar_dados_geograficos.py antes.
    goto erro
)

echo Gerando o executavel (pode levar alguns minutos)...
".venv\Scripts\python.exe" -m PyInstaller executavel\painel_heliopolis.spec --noconfirm --clean --distpath dist --workpath build || goto erro

echo Copiando instrucoes de uso para a pasta do executavel...
copy /Y "executavel\COMO_USAR.txt" "dist\PainelHeliopolis\COMO_USAR.txt" >nul

echo Compactando para a Release do GitHub...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\PainelHeliopolis' -DestinationPath 'dist\PainelHeliopolis-Windows.zip' -Force" || goto erro

echo.
echo Pronto! Arquivo para publicar: dist\PainelHeliopolis-Windows.zip
echo Teste: abra dist\PainelHeliopolis\PainelHeliopolis.exe
pause
exit /b 0

:erro
echo.
echo Ocorreu um erro. Leia as mensagens acima.
pause
exit /b 1
