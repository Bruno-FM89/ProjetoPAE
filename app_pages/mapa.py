"""Página "Mapa de Heliópolis" (arquivo de página usado pelo st.navigation no app.py)."""
from views import pagina_mapa
from views.sessao import obter_sistema

pagina_mapa.renderizar(obter_sistema())
