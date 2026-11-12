"""Localização: ponto de referência de Heliópolis e cálculo de distâncias (Model).

Por que este arquivo existe
---------------------------
O enunciado exige deixar claro, em todas as telas, ONDE cada dado foi medido.
Não há estação oficial dentro de Heliópolis. Por isso o sistema trabalha com
estações próximas e mostra a distância aproximada de cada uma até um ponto
de referência do bairro.

Este módulo guarda:

* o ponto de referência usado para Heliópolis e de onde ele veio;
* os "tipos de localização" que um dado pode ter (medido no bairro, medido
  numa estação próxima, estimado por modelo, fictício);
* a função que calcula a distância em linha reta entre dois pontos do globo.
"""

# "annotations" faz o Python aceitar dicas de tipo modernas (ex.: float | None)
# mesmo em versões um pouco mais antigas da linguagem.
from __future__ import annotations

# math traz funções matemáticas prontas (seno, cosseno, raiz quadrada...).
import math

# dataclass gera automaticamente o "molde" de uma classe que só guarda dados
# (o construtor __init__, a comparação entre objetos etc.).
from dataclasses import dataclass


@dataclass(frozen=True)
class PontoReferencia:
    """Um ponto no mapa, com a explicação de onde suas coordenadas vieram.

    Atributos:
        nome: como o ponto aparece na interface.
        latitude: graus decimais (negativo = hemisfério sul).
        longitude: graus decimais (negativo = oeste de Greenwich).
        fonte: de onde as coordenadas foram tiradas (para quem quiser conferir).

    ``frozen=True`` torna o objeto imutável: depois de criado, ninguém
    consegue alterar suas coordenadas por engano.
    """

    nome: str
    latitude: float
    longitude: float
    fonte: str


# Ponto de referência de Heliópolis.
# As coordenadas vêm do OpenStreetMap (base de dados colaborativa de mapas,
# licença ODbL). A busca "Heliópolis, São Paulo, Brasil" no serviço Nominatim,
# feita em 08/11/2026, retornou a área residencial "HELIOPOLIS" (objeto OSM do
# tipo "way", número 566841451), no distrito do Ipiranga. Ela é um ponto
# APROXIMADO do bairro: serve só para estimar distâncias até as estações.
REFERENCIA_HELIOPOLIS = PontoReferencia(
    nome="Heliópolis (ponto de referência aproximado)",
    latitude=-23.6073672,
    longitude=-46.5810343,
    fonte=(
        "OpenStreetMap / Nominatim, área residencial 'HELIOPOLIS' (way 566841451, distrito Ipiranga), "
        "consultado em 08/11/2026. Dados © colaboradores do OpenStreetMap, licença ODbL."
    ),
)


# Tipos de localização que um conjunto de dados pode ter.
# A chave (à esquerda) é usada dentro do código; o texto (à direita) é o que
# o usuário lê na tela. Manter os textos aqui evita escrever versões
# diferentes da mesma frase em vários arquivos.
TIPOS_LOCALIZACAO = {
    "heliopolis": "Medido dentro de Heliópolis",
    "estacao_proxima": "Medido em estação próxima (fora de Heliópolis)",
    "estacao": "Medido em estação de monitoramento (localização não verificada neste projeto)",
    "estimado": "Estimado por modelo (não é medição)",
    "ficticio": "Dado fictício (didático, não é medição)",
}


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta, em quilômetros, entre dois pontos do globo.

    Usa a fórmula de Haversine, que considera a Terra como uma esfera de raio
    médio 6.371 km. Para distâncias de poucos quilômetros, o erro dessa
    simplificação é desprezível para o nosso uso (só informar a distância).

    Parâmetros:
        lat1, lon1: latitude e longitude do primeiro ponto, em graus.
        lat2, lon2: latitude e longitude do segundo ponto, em graus.

    Retorna:
        A distância em km (número decimal). Não é a distância por ruas.
    """
    raio_terra_km = 6371.0088

    # As funções trigonométricas do Python trabalham em radianos, não em graus.
    # math.radians faz a conversão (180 graus = π radianos).
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Fórmula de Haversine:
    #   a = sen²(Δφ/2) + cos φ1 · cos φ2 · sen²(Δλ/2)
    #   distância = 2 · R · arcsen(√a)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * raio_terra_km * math.asin(math.sqrt(a))


def distancia_ate_heliopolis(latitude: float | None, longitude: float | None) -> float | None:
    """Distância (km) de um ponto até a referência de Heliópolis.

    Retorna ``None`` quando a localização não é conhecida, para que a tela
    mostre "localização não verificada" em vez de um número inventado.
    """
    # "x != x" só é verdadeiro quando x é NaN (valor numérico ausente).
    # Assim tratamos tanto None quanto NaN como "sem coordenada".
    if latitude is None or longitude is None or latitude != latitude or longitude != longitude:
        return None
    return distancia_km(REFERENCIA_HELIOPOLIS.latitude, REFERENCIA_HELIOPOLIS.longitude, latitude, longitude)
