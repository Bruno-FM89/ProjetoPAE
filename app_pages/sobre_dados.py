"""Página "Sobre os Dados" (arquivo de página usado pelo st.navigation no app.py)."""
from views import pagina_sobre_dados
from views.sessao import filtros_ar, obter_sistema

pagina_sobre_dados.renderizar(obter_sistema(), filtros_ar())
