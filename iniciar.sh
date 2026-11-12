#!/usr/bin/env bash
# Inicia o painel no Linux/macOS: cria o ambiente virtual e instala as dependências na primeira vez.
# set -e: se um comando falhar, o script para (em vez de seguir com erro).
set -e
# Entra na pasta onde este arquivo está (a pasta do projeto).
cd "$(dirname "$0")"

# Procura um Python 3.10 ou mais novo (tenta "python3" e depois "python").
PY=""
for candidato in python3 python; do
    if command -v "$candidato" >/dev/null 2>&1 && \
       "$candidato" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$candidato"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "Python 3.10 ou mais novo nao encontrado. Instale em https://www.python.org/downloads/ e rode de novo."
    read -r -p "Pressione Enter para sair..." _ || true
    exit 1
fi

# Ambiente virtual (.venv): uma cópia isolada do Python só para este projeto.
if [ ! -x ".venv/bin/python" ]; then
    echo "Criando ambiente virtual (so na primeira vez)..."
    "$PY" -m venv .venv
fi

# Se as bibliotecas ainda não estão instaladas no ambiente, instala a partir do requirements.txt.
if ! .venv/bin/python -c "import streamlit, pandas, plotly" >/dev/null 2>&1; then
    echo "Instalando dependencias (so na primeira vez, pode levar alguns minutos)..."
    .venv/bin/python -m pip install --upgrade pip >/dev/null 2>&1 || true
    .venv/bin/python -m pip install -r requirements.txt
fi

# evita que o Streamlit pare na primeira execucao pedindo um e-mail
if [ ! -f "$HOME/.streamlit/credentials.toml" ]; then
    mkdir -p "$HOME/.streamlit"
    printf '[general]\nemail = ""\n' > "$HOME/.streamlit/credentials.toml"
fi

echo "Iniciando o painel. O navegador abre em instantes. Para encerrar, pressione Ctrl+C ou feche esta janela."
exec .venv/bin/python -m streamlit run app.py
