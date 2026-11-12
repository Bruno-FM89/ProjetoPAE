"""Camada CONTROLLER do MVC.

Recebe os pedidos da tela (filtros escolhidos pelo usuário), pede ao Model os dados
e os cálculos e devolve tabelas e frases prontas para a View. Não desenha nada e não
faz contas estatísticas.

* ``painel_controller.py``      — qualidade do ar (CETESB/MonitorAr, QUALAR, banco, demonstração);
* ``termometros_controller.py`` — termômetros da UNAS;
* ``mapa_controller.py``        — camadas geográficas de Heliópolis;
* ``sistema.py``                — cria os três Controllers de uma vez.
"""
