"""Página "Visão Geral" (arquivo de página usado pelo st.navigation no app.py)."""
from views import pagina_inicio
from views.sessao import obter_sistema

pagina_inicio.renderizar(obter_sistema())
