"""Página "Ajuda e Tutorial" (arquivo de página usado pelo st.navigation no app.py)."""
from views import pagina_ajuda
from views.sessao import obter_sistema

pagina_ajuda.renderizar(obter_sistema().painel)
