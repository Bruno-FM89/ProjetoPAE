"""Página "Qualidade do Ar" (arquivo de página usado pelo st.navigation no app.py)."""
from views import pagina_qualidade_ar
from views.sessao import filtros_ar, obter_sistema

pagina_qualidade_ar.renderizar(obter_sistema(), filtros_ar())
