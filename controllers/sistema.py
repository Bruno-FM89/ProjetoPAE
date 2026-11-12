"""Monta todos os Controllers do sistema num único objeto (ponto de partida do app).

Por que existe
--------------
O painel agora trabalha com TRÊS conjuntos de dados independentes:

* qualidade do ar (``PainelController``),
* termômetros da comunidade (``TermometrosController``),
* mapas de Heliópolis (``MapaController``).

Se um deles falhar (por exemplo, um arquivo apagado por engano), os outros
devem continuar funcionando. Por isso cada um é criado separadamente e o erro
fica guardado em ``erros`` para a tela explicar o problema na seção afetada.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from controllers.mapa_controller import MapaController
from controllers.painel_controller import ErroFonteDados, PainelController
from controllers.termometros_controller import TermometrosController
from services.config import Configuracao


@dataclass
class Sistema:
    """Os três Controllers (qualquer um pode ser ``None`` se seus dados faltarem).

    Atributos:
        painel: qualidade do ar (CETESB/MonitorAr e demais fontes).
        termometros: termômetros da UNAS.
        mapa: camadas geográficas.
        erros: mensagem de erro de cada parte que não pôde ser carregada
            (chaves "qualidade_ar", "termometros", "mapa").
    """

    painel: PainelController | None = None
    termometros: TermometrosController | None = None
    mapa: MapaController | None = None
    erros: dict[str, str] = field(default_factory=dict)


def criar_sistema(config: Configuracao) -> Sistema:
    """Carrega os três conjuntos de dados; um erro em um não impede os outros.

    A ordem importa: o mapa usa informações dos termômetros (região de cada
    um) e das estações de qualidade do ar (coordenadas e distâncias).
    """
    sistema = Sistema()
    try:
        sistema.painel = PainelController.a_partir_da_configuracao(config)
    except ErroFonteDados as erro:
        sistema.erros["qualidade_ar"] = str(erro)
    try:
        sistema.termometros = TermometrosController.a_partir_da_configuracao(config)
    except (ErroFonteDados, OSError, ValueError) as erro:
        sistema.erros["termometros"] = str(erro)
    try:
        termometros = sistema.termometros.tabela_termometros() if sistema.termometros else None
        estacoes = _estacoes_reais(sistema.painel)
        sistema.mapa = MapaController.a_partir_da_configuracao(config, termometros, estacoes)
    except (ErroFonteDados, OSError, ValueError) as erro:
        sistema.erros["mapa"] = str(erro)
    return sistema


def _estacoes_reais(painel: PainelController | None):
    """Estações da primeira fonte de dados REAIS (a fictícia não entra no mapa)."""
    if painel is None:
        return None
    for fonte in painel.nomes_fontes:
        if not painel.eh_ficticia(fonte):
            return painel.estacoes(fonte)
    return None
