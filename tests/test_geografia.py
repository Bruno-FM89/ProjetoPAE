"""Testes do mapa: geometria, camadas convertidas dos Shapefiles e Controller do mapa."""

import json

import pandas as pd
import pytest

from controllers.mapa_controller import MapaController
from models.fontes import ErroFonteDados
from models.geografia import CamadasGeograficas, ponto_no_anel, ponto_no_poligono
from scripts.preparar_dados_geograficos import area_m2
from services.config import Configuracao

QUADRADO = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
BURACO = [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]


def test_ponto_no_poligono_com_buraco():
    geometria = {"type": "Polygon", "coordinates": [QUADRADO, BURACO]}
    assert ponto_no_anel(1, 1, QUADRADO)
    assert ponto_no_poligono(2, 2, geometria)
    assert not ponto_no_poligono(5, 5, geometria)   # dentro do buraco = fora
    assert not ponto_no_poligono(11, 5, geometria)


def test_area_desconta_buraco():
    assert area_m2({"type": "Polygon", "coordinates": [QUADRADO]}) == pytest.approx(100)
    assert area_m2({"type": "Polygon", "coordinates": [QUADRADO, BURACO]}) == pytest.approx(96)
    assert area_m2({"type": "MultiPolygon", "coordinates": [[QUADRADO], [BURACO]]}) == pytest.approx(104)


def test_pasta_sem_quebradas_gera_erro_claro(tmp_path):
    with pytest.raises(ErroFonteDados, match="quebradas"):
        CamadasGeograficas(tmp_path)


def test_camada_opcional_ausente_vira_aviso(tmp_path):
    feicao = {"type": "Feature", "properties": {"nome": "A", "area_m2": 100.0}, "geometry": {"type": "Polygon", "coordinates": [QUADRADO]}}
    (tmp_path / "quebradas.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [feicao]}), encoding="utf-8")
    camadas = CamadasGeograficas(tmp_path)
    assert len(camadas.avisos) == 3                      # recorte, glebas e projetos ausentes
    assert camadas.quebradas()["nome"].tolist() == ["A"]
    assert camadas.projetos().empty


@pytest.fixture(scope="module")
def mapa_real():
    config = Configuracao.carregar({})
    termometros = pd.DataFrame({"nome": ["Termômetro 9"], "quebrada": ["Mina"], "localizacao_validada": [True]})
    return MapaController.a_partir_da_configuracao(config, termometros)


def test_camadas_reais_convertidas(mapa_real):
    assert len(mapa_real.quebradas()) == 7
    assert len(mapa_real.glebas()) == 15
    assert len(mapa_real.projetos()) == 52
    assert mapa_real.area_recorte_km2() == pytest.approx(2.46, abs=0.01)


def test_coordenadas_em_sao_paulo(mapa_real):
    """Depois da conversão de UTM (metros) para graus, tudo deve cair perto de Heliópolis."""
    lon, lat = mapa_real.centro()
    assert -46.62 < lon < -46.56 and -23.64 < lat < -23.59


def test_areas_conferem_com_tabela_original(mapa_real):
    conferencia = mapa_real.conferencia_areas()
    assert (conferencia["diferenca_pct"] < 0.1).all()


def test_projetos_por_quebrada(mapa_real):
    projetos = mapa_real.projetos()
    assert (projetos["quebrada"] == "Mina").sum() == 13
    assert projetos["dentro_recorte"].sum() == 27
    assert "CEI" in mapa_real.tipos_projeto()
    assert set(mapa_real.projetos(["CEI"])["tipo"]) == {"CEI"}


def test_termometros_validados_por_quebrada(mapa_real):
    quebradas = mapa_real.quebradas().set_index("nome")
    assert quebradas.loc["Mina", "termometros_validados"] == 1
    assert mapa_real.termometros_na_quebrada("Mina", True) == ["Termômetro 9"]
    assert mapa_real.termometros_na_quebrada("Mina", False) == []
