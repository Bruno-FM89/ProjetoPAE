"""Página "Temperatura e Umidade" (arquivo de página usado pelo st.navigation no app.py)."""
from views import pagina_termometros
from views.sessao import obter_sistema

pagina_termometros.renderizar(obter_sistema())
