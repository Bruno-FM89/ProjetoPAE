"""Verifica se há acesso à internet (Service).

Para que serve
--------------
Todos os DADOS do painel ficam no computador e funcionam sem internet. Só o
"fundo" do mapa (ruas do OpenStreetMap) vem da internet. Se não houver
conexão, o mapa mostra as camadas sobre fundo branco e avisa o usuário, em vez
de exibir um quadro cinza sem explicação.
"""

from __future__ import annotations

import socket  # biblioteca padrão do Python para conexões de rede


def tem_internet(host: str = "tile.openstreetmap.org", porta: int = 443, tempo_limite: float = 1.5) -> bool:
    """Tenta abrir uma conexão rápida com o servidor de mapas.

    Parâmetros:
        host, porta: servidor testado (o mesmo que fornece o fundo do mapa).
        tempo_limite: segundos de espera antes de desistir.

    Retorna ``True`` se a conexão abriu; ``False`` se não houver internet,
    se o servidor estiver fora do ar ou se uma rede bloquear o acesso.
    """
    try:
        with socket.create_connection((host, porta), timeout=tempo_limite):
            return True
    except OSError:
        return False
