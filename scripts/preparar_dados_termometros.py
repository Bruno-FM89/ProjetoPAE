"""Prepara os dados dos termômetros da UNAS para o painel (planilhas → arquivo único e anônimo).

Por que este script existe
--------------------------
As planilhas originais (Drive "Dados dos termômetros") têm o NOME DE MORADORES
no nome do arquivo, e o documento de resumo traz ENDEREÇOS. Esses dados não
podem ir para o GitHub nem para o executável. Este script:

1. lê cada planilha da pasta ``data/termometros/bruto/`` (pasta ignorada pelo Git);
2. troca o nome do arquivo por um identificador anônimo (T1, T2, ...), usando
   a tabela PRIVADA ``data/termometros/bruto/correspondencia.csv`` — se ela
   não existir, é criada em ordem alfabética dos arquivos;
3. junta todas as leituras num só arquivo compactado
   ``data/termometros/medicoes_termometros.csv.gz`` (só id, data/hora,
   temperatura e umidade);
4. grava ``metadados_termometros.json`` com o modelo do aparelho, intervalo,
   período, o resumo do próprio aparelho e os problemas encontrados;
5. cria ``locais_termometros.csv`` (se ainda não existir) para a equipe
   informar em qual QUEBRADA cada termômetro está — nunca o endereço.

Como usar (a partir da pasta do projeto)
---------------------------------------
    python scripts/preparar_dados_termometros.py
    python scripts/preparar_dados_termometros.py --pasta OUTRA/PASTA

Requer a biblioteca ``openpyxl`` (``pip install -r requirements-dev.txt``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # permite importar os módulos do projeto (models/...)

from models.termometros import COL_DATA, COL_ID, COL_TEMP, COL_UMID, ler_planilha_rc51h  # noqa: E402

PASTA_SAIDA = RAIZ / "data" / "termometros"
PASTA_BRUTO = PASTA_SAIDA / "bruto"
EXTENSOES = {".xls", ".xlsx"}


def sha256(caminho: Path) -> str:
    """Impressão digital do arquivo: permite conferir se a planilha original mudou."""
    h = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def correspondencia(pasta: Path, arquivos: list[Path]) -> dict[str, str]:
    """Lê (ou cria) a tabela PRIVADA "nome do arquivo → id anônimo".

    Novos arquivos recebem o próximo número livre, então os ids antigos nunca
    mudam quando chega uma planilha nova.
    """
    caminho = pasta / "correspondencia.csv"
    mapa: dict[str, str] = {}
    if caminho.is_file():
        tabela = pd.read_csv(caminho, sep=";", dtype=str)
        mapa = dict(zip(tabela["arquivo"], tabela["termometro_id"]))
    proximo = max((int(v.lstrip("T")) for v in mapa.values()), default=0) + 1
    for arquivo in arquivos:
        if arquivo.name not in mapa:
            mapa[arquivo.name] = f"T{proximo}"
            proximo += 1
    pd.DataFrame({"arquivo": list(mapa), "termometro_id": list(mapa.values())}).to_csv(caminho, sep=";", index=False)
    return mapa


def main(argv: list[str] | None = None) -> int:
    """Executa a preparação: lê as planilhas, anonimiza e grava os arquivos usados pelo app. Devolve 0 se deu certo."""
    parser = argparse.ArgumentParser(description="Prepara os dados dos termômetros da UNAS.")
    parser.add_argument("--pasta", type=Path, default=PASTA_BRUTO, help="pasta com as planilhas originais")
    args = parser.parse_args(argv)

    arquivos = sorted(p for p in args.pasta.glob("*") if p.suffix.lower() in EXTENSOES)
    if not arquivos:
        print(f"Nenhuma planilha .xls/.xlsx encontrada em {args.pasta}.")
        return 1

    mapa = correspondencia(args.pasta, arquivos)
    tabelas, aparelhos = [], []
    for arquivo in arquivos:
        tid = mapa[arquivo.name]
        dados, info = ler_planilha_rc51h(arquivo)
        dados.insert(0, COL_ID, tid)
        tabelas.append(dados)
        conteudo_xlsx = open(arquivo, "rb").read(4) == b"PK\x03\x04"  # assinatura de arquivo .xlsx (zip)
        if arquivo.suffix.lower() == ".xls" and conteudo_xlsx:
            info["problemas"].insert(0, "O arquivo termina em .xls, mas o conteúdo é do formato .xlsx (Excel 2007+).")
        aparelhos.append({
            "termometro_id": tid,
            "sha256_arquivo_original": sha256(arquivo),
            "leituras": int(len(dados)),
            "primeira_leitura_lista": str(dados[COL_DATA].min()),
            "ultima_leitura_lista": str(dados[COL_DATA].max()),
            **info,
        })
        print(f"{tid}: {len(dados)} leituras de {dados[COL_DATA].min()} a {dados[COL_DATA].max()}; problemas: {len(info['problemas'])}")

    medicoes = pd.concat(tabelas, ignore_index=True)
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    medicoes.to_csv(
        PASTA_SAIDA / "medicoes_termometros.csv.gz", index=False, columns=[COL_ID, COL_DATA, COL_TEMP, COL_UMID],
        date_format="%Y-%m-%d %H:%M:%S", compression={"method": "gzip", "mtime": 0},  # mtime=0: arquivo idêntico a cada execução
    )
    metadados = {
        "descricao": "Medições de temperatura e umidade relativa do ar feitas por registradores instalados pela UNAS em residências de Heliópolis.",
        "origem": "Google Drive da UNAS — pasta 'Dados dos termômetros' (planilhas exportadas do programa do registrador).",
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "privacidade": (
            "Os nomes dos arquivos (nomes de moradores) foram substituídos por identificadores anônimos; endereços não "
            "são usados. A correspondência fica só em data/termometros/bruto/correspondencia.csv, fora do Git."
        ),
        "unidades": {COL_TEMP: "°C", COL_UMID: "% (umidade relativa)"},
        "aparelhos": aparelhos,
    }
    (PASTA_SAIDA / "metadados_termometros.json").write_text(json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8")

    locais = PASTA_SAIDA / "locais_termometros.csv"
    if not locais.is_file():
        pd.DataFrame({
            "termometro_id": sorted(mapa.values(), key=lambda t: int(t.lstrip("T"))),
            "nome_exibicao": "", "quebrada": "", "localizacao_validada": "nao", "observacao": "",
        }).to_csv(locais, sep=";", index=False)
        print(f"Criado {locais}: preencha a quebrada de cada termômetro e marque 'sim' quando a UNAS confirmar.")
    print(f"Pronto: {len(medicoes)} leituras de {len(arquivos)} termômetros em {PASTA_SAIDA}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
