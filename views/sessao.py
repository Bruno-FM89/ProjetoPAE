"""Acesso compartilhado aos dados durante a sessão (View).

Todas as páginas (arquivos da pasta ``app_pages/``) precisam dos mesmos
Controllers e dos filtros da qualidade do ar escolhidos na barra lateral.
Este módulo guarda essas duas coisas num só lugar:

* ``obter_sistema()`` carrega os dados UMA vez (``st.cache_resource``) e
  devolve sempre o mesmo objeto enquanto o servidor estiver ligado;
* ``filtros_ar()`` devolve os filtros que o ``app.py`` desenhou na barra
  lateral nesta execução (ou ``None`` quando a página não usa esses filtros).
"""

from __future__ import annotations

import streamlit as st

from controllers.painel_controller import Filtros
from controllers.sistema import Sistema, criar_sistema
from services.config import Configuracao

CHAVE_FILTROS_AR = "_filtros_ar"


@st.cache_resource(show_spinner="Carregando os dados…")
def obter_sistema() -> Sistema:
    """Cria os Controllers uma única vez enquanto o servidor estiver rodando."""
    return criar_sistema(Configuracao.carregar())


def guardar_filtros_ar(filtros: Filtros | None) -> None:
    """Chamado pelo app.py depois de desenhar a barra lateral."""
    st.session_state[CHAVE_FILTROS_AR] = filtros


def filtros_ar() -> Filtros | None:
    """Filtros da qualidade do ar desta execução (None se a barra lateral não os mostrou)."""
    return st.session_state.get(CHAVE_FILTROS_AR)
