"""Prepara o recorte de dados REAIS usado pelo dashboard (arquivos oficiais do MonitorAr).

O que este script faz, passo a passo
-----------------------------------
1. Lê os arquivos anuais oficiais do MonitorAr (``dados_monitorar_AAAA.zip``),
   baixados do Portal de Dados Abertos do Ministério do Meio Ambiente.
2. Calcula a "impressão digital" SHA-256 de cada arquivo. Quem baixar o mesmo
   arquivo do portal pode recalcular o SHA-256 e conferir que é idêntico.
3. Guarda SOMENTE as linhas das estações listadas em ``data/reais/estacoes.csv``
   (as estações da CETESB mais próximas de Heliópolis). Nenhum valor é
   alterado: os textos de cada célula são copiados exatamente como estão.
4. Acrescenta uma única coluna, ``arquivo_origem``, com o nome do arquivo
   oficial de onde cada linha saiu.
5. Grava o recorte compactado em ``data/reais/monitorar_estacoes_proximas.csv.gz``
   e um arquivo de metadados (``metadados_monitorar.json``) com a origem, a
   licença, o SHA-256, o filtro aplicado e a contagem de linhas.

Como usar (a partir da pasta do projeto)
---------------------------------------
    python scripts/preparar_dados_monitorar.py CAMINHO/dados_monitorar_2024.zip CAMINHO/dados_monitorar_2025.zip

Opcional: ``--data-download AAAA-MM-DD`` registra a data em que você baixou os arquivos.

Onde baixar os arquivos: veja ``docs/FONTES_DE_DADOS.md``.
"""

# --- imports (bibliotecas usadas) ------------------------------------------
from __future__ import annotations

import argparse  # lê os argumentos digitados no terminal (os caminhos dos zips)
import hashlib  # calcula o SHA-256 dos arquivos
import json  # grava os metadados em formato JSON (texto estruturado)
import sys  # permite encerrar o script com um código de erro
import zipfile  # abre arquivos .zip sem precisar descompactá-los no disco
from datetime import date, datetime  # datas de download e de geração
from pathlib import Path  # manipula caminhos de arquivos de forma portátil (Windows/Linux/Mac)

import pandas as pd  # leitura e escrita de tabelas (CSV)

# Pasta raiz do projeto: este arquivo está em <raiz>/scripts/, então subimos um nível.
RAIZ = Path(__file__).resolve().parent.parent
PASTA_REAIS = RAIZ / "data" / "reais"
ARQUIVO_ESTACOES = PASTA_REAIS / "estacoes.csv"
ARQUIVO_SAIDA = PASTA_REAIS / "monitorar_estacoes_proximas.csv.gz"
ARQUIVO_METADADOS = PASTA_REAIS / "metadados_monitorar.json"

# Página oficial do conjunto de dados e endereço de cada arquivo anual,
# copiados do catálogo do portal (API CKAN do dados.mma.gov.br) em 08/11/2026.
PORTAL = "https://dados.mma.gov.br/dataset/5be05b46-3bda-4f6e-9bf2-810e716fff33"
URLS_OFICIAIS = {
    "dados_monitorar_2022.zip": (
        PORTAL + "/resource/3ed97dc4-9b37-4a2f-81e1-b69c5f654d65/download/dados_monitorar_2022.zip",
        "2025-12-19",
    ),
    "dados_monitorar_2023.zip": (
        PORTAL + "/resource/ad6a4436-db18-4037-bfd1-77f3b9669b35/download/dados_monitorar_2023.zip",
        "2025-12-19",
    ),
    "dados_monitorar_2024.zip": (
        PORTAL + "/resource/b24d6cfa-4465-4124-a6c4-ec96ff7b7f9f/download/dados_monitorar_2024.zip",
        "2025-12-19",
    ),
    "dados_monitorar_2025.zip": (
        PORTAL + "/resource/e4f35322-b8a7-423c-bc12-21bbd0804a0a/download/dados_monitorar_2025.zip",
        "2026-02-04",
    ),
}


def sha256_arquivo(caminho: Path) -> str:
    """Calcula o SHA-256 de um arquivo, lendo-o em pedaços de 1 MB.

    Ler em pedaços evita carregar o arquivo inteiro na memória de uma vez.
    O resultado é um texto de 64 caracteres; se um único byte do arquivo mudar,
    o texto muda completamente.
    """
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:  # "rb" = ler em modo binário
        # iter(função, b"") repete arquivo.read(...) até ele devolver vazio (fim do arquivo)
        for pedaco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(pedaco)
    return resumo.hexdigest()


def filtrar_arquivo(caminho: Path, ids_estacoes: set[str]) -> tuple[pd.DataFrame, list[str]]:
    """Lê um zip oficial e devolve só as linhas das estações escolhidas.

    Parâmetros:
        caminho: caminho do arquivo ``dados_monitorar_AAAA.zip`` (ou de um .csv).
        ids_estacoes: identificadores (coluna ``id_estacao``) das estações a manter.

    Retorna:
        (tabela filtrada, lista com os nomes das colunas originais do arquivo).
    """
    partes = []
    colunas_originais: list[str] = []

    def ler(fluxo) -> None:
        """Lê um CSV de dentro do zip como texto puro (sem converter nada)."""
        # dtype=str: lê TUDO como texto, para não alterar nenhum valor
        # (por exemplo, "22.000" continua "22.000", e "" continua vazio).
        # keep_default_na=False: impede o pandas de transformar textos vazios em NaN.
        # chunksize: lê 500 mil linhas por vez, porque o arquivo descompactado
        # tem quase 1 GB e não precisa caber inteiro na memória.
        for bloco in pd.read_csv(fluxo, dtype=str, keep_default_na=False, chunksize=500_000):
            if not colunas_originais:
                colunas_originais.extend(bloco.columns)
            # Mantemos apenas São Paulo (sg_uf) e as estações da lista.
            filtro = (bloco["sg_uf"] == "SP") & (bloco["id_estacao"].isin(ids_estacoes))
            partes.append(bloco[filtro])

    if caminho.suffix.lower() == ".zip":
        with zipfile.ZipFile(caminho) as pacote:
            nomes_csv = [n for n in pacote.namelist() if n.lower().endswith(".csv")]
            if len(nomes_csv) != 1:
                raise ValueError(f"Esperava 1 CSV dentro de {caminho.name}, encontrei {len(nomes_csv)}.")
            with pacote.open(nomes_csv[0]) as fluxo:
                ler(fluxo)
    else:
        ler(caminho)

    filtrado = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=colunas_originais)
    filtrado["arquivo_origem"] = caminho.name
    return filtrado, colunas_originais


def main() -> int:
    """Ponto de entrada: lê os argumentos, filtra, grava o recorte e os metadados."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("arquivos", nargs="+", type=Path, help="zips oficiais dados_monitorar_AAAA.zip")
    parser.add_argument("--data-download", default=date.today().isoformat(), help="data em que os arquivos foram baixados")
    args = parser.parse_args()

    # Lista de estações: lida do CSV curado (com a fonte de cada coordenada).
    estacoes = pd.read_csv(ARQUIVO_ESTACOES, dtype=str)
    ids = set(estacoes["id_estacao_monitorar"])

    tabelas, registros_arquivos, colunas_por_arquivo = [], [], {}
    for caminho in args.arquivos:
        if not caminho.is_file():
            print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
            return 1
        print(f"Lendo {caminho.name} ...")
        tabela, colunas = filtrar_arquivo(caminho, ids)
        tabelas.append(tabela)
        colunas_por_arquivo[caminho.name] = colunas
        url, publicado = URLS_OFICIAIS.get(caminho.name, ("não informado", "não informado"))
        registros_arquivos.append(
            {
                "nome": caminho.name,
                "url": url,
                "publicado_no_portal_em": publicado,
                "bytes": caminho.stat().st_size,
                "sha256": sha256_arquivo(caminho),
                "data_download": args.data_download,
                "linhas_mantidas": int(len(tabela)),
            }
        )

    # pd.concat junta as tabelas dos vários anos. Se uma coluna existir só em
    # um ano (o nome da coluna de status mudou de 2024 para 2025), ela fica
    # vazia nas linhas do outro ano. Nada é renomeado aqui; isso é feito na
    # leitura pelo app e fica registrado nos metadados.
    recorte = pd.concat(tabelas, ignore_index=True).fillna("")
    recorte = recorte.sort_values(["id_estacao", "cd_normalizado", "dh_medicao"], kind="stable")
    PASTA_REAIS.mkdir(parents=True, exist_ok=True)
    recorte.to_csv(ARQUIVO_SAIDA, index=False, compression="gzip")

    contagem = recorte.groupby(["id_estacao", "no_estacao", "cd_normalizado"]).size()
    metadados = {
        "titulo": "Recorte do MonitorAr: estações da CETESB próximas a Heliópolis",
        "fonte": "Sistema Nacional de Gestão da Qualidade do Ar - MonitorAr (Ministério do Meio Ambiente e Mudança do Clima)",
        "orgao_responsavel_pelas_medicoes": "Companhia Ambiental do Estado de São Paulo - CETESB",
        "pagina_do_conjunto": PORTAL,
        "licenca": "Creative Commons Atribuição (conforme o portal dados.mma.gov.br)",
        "aviso_da_fonte": (
            "Dados obtidos de forma automática; podem conter inconsistências, falhas de medição, lacunas "
            "temporais ou registros ainda não submetidos à validação técnica (dicionário de dados do MonitorAr)."
        ),
        "arquivos_originais": registros_arquivos,
        "colunas_originais_por_arquivo": colunas_por_arquivo,
        "filtro_aplicado": {"sg_uf": "SP", "id_estacao": sorted(ids)},
        "colunas_acrescentadas": {"arquivo_origem": "nome do arquivo oficial de onde a linha foi copiada"},
        "valores_alterados": "nenhum (todas as células copiadas como texto)",
        "linhas_por_estacao_e_parametro": {f"{i}|{n}|{p}": int(q) for (i, n, p), q in contagem.items()},
        "total_de_linhas": int(len(recorte)),
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "gerado_por": "scripts/preparar_dados_monitorar.py",
    }
    ARQUIVO_METADADOS.write_text(json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(recorte)} linhas gravadas em {ARQUIVO_SAIDA.relative_to(RAIZ)}")
    print(f"Metadados em {ARQUIVO_METADADOS.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
