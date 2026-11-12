"""Carrega o dataset de DEMONSTRAÇÃO (fictício) numa tabela PostgreSQL/Supabase.

Para que serve
--------------
Mostra, na prática, a integração com banco de dados vista nas aulas: o CSV é
lido pelo Python e inserido numa tabela. Depois, o app pode ler a tabela
(fonte "Banco de dados (PostgreSQL)") em vez do arquivo. A estrutura da
tabela é a do dataset fictício (``docs/schema.sql``).

Uso (a partir da raiz do projeto):

    pip install -r requirements-db.txt
    # defina DATABASE_URL no ambiente ou em um arquivo .env (veja .env.example)
    python scripts/carregar_csv_no_banco.py               # carga inicial
    python scripts/carregar_csv_no_banco.py --substituir  # apaga e recarrega os registros desta fonte

Os valores ausentes do CSV viram NULL no banco; o tratamento continua sendo feito pelo app.
"""

from __future__ import annotations

import argparse  # lê as opções digitadas no terminal (ex.: --substituir)
import sys
from pathlib import Path

# O script fica em <raiz>/scripts; para importar os módulos do projeto
# (models, services) colocamos a raiz no caminho de busca do Python.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from models.fontes import ErroFonteDados, FonteCSV, FontePostgres  # noqa: E402 (import depois do sys.path)
from services.config import Configuracao  # noqa: E402

#: Nome com que o arquivo fica registrado na tabela "fontes".
NOME_FONTE = "CSV ambiental_heliopolis (fictício)"


def main() -> int:
    """Executa a carga. Retorna 0 (sucesso), 1 (erro de configuração) ou 2 (dados já existem)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--substituir", action="store_true", help="apaga os registros existentes desta fonte antes de inserir")
    args = parser.parse_args()

    config = Configuracao.carregar()
    if not config.usa_banco:
        print("DATABASE_URL não definida. Veja o arquivo .env.example.", file=sys.stderr)
        return 1

    try:
        # text() marca um texto como comando SQL; create_engine cria a conexão com o banco.
        from sqlalchemy import create_engine, text
    except ImportError:
        print("Instale as dependências do banco: pip install -r requirements-db.txt", file=sys.stderr)
        return 1

    try:
        df = FonteCSV("CSV", config.caminho_csv).carregar_dados()  # tabela larga: Data + 8 colunas
    except ErroFonteDados as erro:
        print(f"Erro ao ler o CSV: {erro}", file=sys.stderr)
        return 1

    # Inverte o dicionário {coluna_banco: coluna_csv} para renomear do CSV para o banco.
    colunas_banco = {v: k for k, v in FontePostgres.COLUNAS_BANCO.items()}
    engine = create_engine(config.database_url)
    try:
        # engine.begin() abre uma TRANSAÇÃO: se algo falhar no meio, nada é gravado pela metade.
        with engine.begin() as conexao:
            conexao.exec_driver_sql((RAIZ / "docs" / "schema.sql").read_text(encoding="utf-8"))  # cria as tabelas
            # ON CONFLICT DO NOTHING: se a fonte já existe, não duplica.
            conexao.execute(
                text("INSERT INTO fontes (nome, tipo) VALUES (:nome, 'CSV') ON CONFLICT (nome) DO NOTHING"),
                {"nome": NOME_FONTE},
            )
            fonte_id = conexao.execute(text("SELECT id FROM fontes WHERE nome = :nome"), {"nome": NOME_FONTE}).scalar_one()
            existentes = conexao.execute(
                text(f"SELECT COUNT(*) FROM {config.tabela} WHERE fonte_id = :f"), {"f": fonte_id}
            ).scalar_one()
            if existentes and not args.substituir:
                print(f"A tabela já tem {existentes} registros desta fonte. Use --substituir para recarregar.", file=sys.stderr)
                return 2
            if existentes:
                conexao.execute(text(f"DELETE FROM {config.tabela} WHERE fonte_id = :f"), {"f": fonte_id})

            registros = df.rename(columns=colunas_banco)
            registros.insert(0, "fonte_id", fonte_id)
            # to_sql insere a tabela do Pandas no banco, em blocos de 500 linhas.
            registros.to_sql(config.tabela, conexao, if_exists="append", index=False, method="multi", chunksize=500)
    finally:
        engine.dispose()  # fecha todas as conexões

    print(f"{len(df)} registros carregados na tabela '{config.tabela}'.")
    return 0


if __name__ == "__main__":
    # Só executa main() quando o arquivo é rodado diretamente (não quando é importado).
    raise SystemExit(main())
