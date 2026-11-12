"""Camada MODEL do MVC: leitura dos dados e cálculos.

Nada aqui conhece o Streamlit (a tela). Por isso tudo pode ser testado sozinho.

* ``fontes.py``       — fontes de dados de qualidade do ar (herança e polimorfismo);
* ``conjunto.py``, ``tratamento.py``, ``estatistica.py``, ``qualidade_ar.py``, ``parametros.py``,
  ``localizacao.py`` — organização, tratamento e estatística da qualidade do ar;
* ``termometros.py``  — leitura das planilhas dos termômetros e seus cálculos;
* ``geografia.py``    — camadas do mapa (GeoJSON) e geometria simples.
"""
