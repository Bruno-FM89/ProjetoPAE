"""Testes do script que prepara o recorte de dados reais a partir dos zips oficiais."""

import importlib.util
import json
import sys
import zipfile

import pandas as pd

from tests.conftest import RAIZ, linha_monitorar

# Carrega o script como módulo (ele fica em scripts/, fora dos pacotes do projeto).
_spec = importlib.util.spec_from_file_location("preparar", RAIZ / "scripts" / "preparar_dados_monitorar.py")
preparar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preparar)


def _zip_oficial_falso(caminho, linhas):
    """Cria um zip com um CSV no formato do MonitorAr (dados de teste, não reais)."""
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("Dados_MonitorAr_2024.csv", pd.DataFrame(linhas).to_csv(index=False))


def test_script_filtra_estacoes_sem_alterar_valores(tmp_path, monkeypatch):
    linhas = [
        linha_monitorar("2024-01-01 00:00:00.000", "22.000", id_estacao="128", nome="Mooca"),
        linha_monitorar("2024-01-01 01:00:00.000", "07.500", id_estacao="128", nome="Mooca"),
        linha_monitorar("2024-01-01 00:00:00.000", "50.000", id_estacao="999", nome="Fora da lista"),
        {**linha_monitorar("2024-01-01 00:00:00.000", "33.000", id_estacao="128"), "sg_uf": "RJ"},
    ]
    zip_teste = tmp_path / "dados_monitorar_2024.zip"
    _zip_oficial_falso(zip_teste, linhas)
    estacoes = tmp_path / "estacoes.csv"
    estacoes.write_text("id_estacao_monitorar,nome\n128,Mooca\n", encoding="utf-8")

    # Redireciona as saídas do script para a pasta temporária do teste.
    monkeypatch.setattr(preparar, "PASTA_REAIS", tmp_path)
    monkeypatch.setattr(preparar, "ARQUIVO_ESTACOES", estacoes)
    monkeypatch.setattr(preparar, "ARQUIVO_SAIDA", tmp_path / "saida.csv.gz")
    monkeypatch.setattr(preparar, "ARQUIVO_METADADOS", tmp_path / "meta.json")
    monkeypatch.setattr(preparar, "RAIZ", tmp_path)
    monkeypatch.setattr(sys, "argv", ["preparar", str(zip_teste), "--data-download", "2026-11-08"])

    assert preparar.main() == 0
    saida = pd.read_csv(tmp_path / "saida.csv.gz", dtype=str, keep_default_na=False)
    assert saida["nu_iqar"].tolist() == ["22.000", "07.500"]  # textos copiados sem mudança
    assert set(saida["arquivo_origem"]) == {"dados_monitorar_2024.zip"}
    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["total_de_linhas"] == 2
    assert meta["arquivos_originais"][0]["sha256"] == preparar.sha256_arquivo(zip_teste)
    assert meta["arquivos_originais"][0]["url"].startswith("https://dados.mma.gov.br/")


def test_script_avisa_arquivo_inexistente(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["preparar", str(tmp_path / "nao_existe.zip")])
    assert preparar.main() == 1
