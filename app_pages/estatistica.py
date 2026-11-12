"""Página "Análise Estatística" (arquivo de página usado pelo st.navigation no app.py)."""
from views import pagina_estatistica
from views.sessao import filtros_ar, obter_sistema

pagina_estatistica.renderizar(obter_sistema(), filtros_ar())
