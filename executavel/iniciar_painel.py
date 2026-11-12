"""Inicializador do painel para o EXECUTÁVEL (Windows, sem Python instalado).

O que este arquivo faz
----------------------
O Streamlit não é um programa de janela: ele liga um pequeno SERVIDOR no próprio
computador e mostra o painel no NAVEGADOR (Chrome, Edge...). Quando a pessoa dá
dois cliques no ``PainelHeliopolis.exe``, este código:

1. descobre a pasta onde estão os arquivos do painel (dentro do executável);
2. escolhe uma "porta" livre (8501, ou a próxima disponível) para o servidor;
3. liga o servidor do Streamlit com ``app.py`` e abre o navegador sozinho;
4. se algo der errado, mostra uma mensagem em português e grava os detalhes em
   ``erro_ao_iniciar.txt``, ao lado do executável, para a equipe técnica.

A janela preta (console) precisa ficar aberta enquanto o painel é usado.
Fechá-la desliga o painel.

Como gerar o executável: ``executavel\\gerar_executavel.bat`` (veja executavel/LEIA-ME.md).
Este arquivo também roda com Python normal (``python executavel/iniciar_painel.py``),
o que ajuda a testar sem gerar o executável.
"""

from __future__ import annotations

import os
import socket
import sys
import traceback
from pathlib import Path

TITULO = "Inteligência Climática para Heliópolis"


def pasta_do_painel() -> Path:
    """Pasta com app.py e data/.

    No executável gerado pelo PyInstaller, os arquivos ficam numa pasta interna
    indicada por ``sys._MEIPASS``. Rodando com Python normal, é a pasta do projeto.
    """
    if getattr(sys, "frozen", False):  # "frozen" = rodando como executável
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def porta_livre(preferida: int = 8501, tentativas: int = 20) -> int:
    """Primeira porta livre a partir de ``preferida`` (outra cópia do painel pode estar aberta)."""
    for porta in range(preferida, preferida + tentativas):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", porta)) != 0:  # ninguém respondeu: porta livre
                return porta
    raise RuntimeError(f"Nenhuma porta livre entre {preferida} e {preferida + tentativas - 1}.")


def iniciar() -> None:
    """Configura e liga o servidor do Streamlit (só volta quando o painel é encerrado)."""
    base = pasta_do_painel()
    app = base / "app.py"
    if not app.is_file():
        raise FileNotFoundError(f"Arquivo principal não encontrado: {app}")
    os.chdir(base)  # o Streamlit lê .streamlit/config.toml (cores do painel) da pasta atual
    sys.path.insert(0, str(base))  # permite "import views", "import controllers"...

    porta = porta_livre()
    print("=" * 64)
    print(f"  {TITULO}")
    print("=" * 64)
    print(f"  Abrindo o painel no navegador: http://localhost:{porta}")
    print("  Se o navegador não abrir sozinho, copie o endereço acima.")
    print("  IMPORTANTE: deixe esta janela aberta enquanto usa o painel.")
    print("  Para encerrar, feche esta janela.")
    print("=" * 64, flush=True)

    from streamlit import config as st_config
    from streamlit.web import bootstrap

    opcoes = {
        # No executável o Streamlit acharia que está em "modo de desenvolvimento"
        # (porque não está instalado em site-packages) e não serviria a página.
        "global.developmentMode": False,
        "server.port": porta,
        "server.address": "localhost",  # só este computador acessa o painel
        "server.headless": False,       # False = o Streamlit abre o navegador quando o servidor estiver pronto
        "server.fileWatcherType": "none",  # não fica vigiando arquivos (não há código para editar)
        "server.runOnSave": False,
        "browser.gatherUsageStats": False,  # não envia estatísticas de uso
        "browser.serverAddress": "localhost",
        "client.toolbarMode": "minimal",
    }
    bootstrap.load_config_options(flag_options=opcoes)
    for chave, valor in opcoes.items():  # garante os valores mesmo se algum arquivo de configuração discordar
        st_config.set_option(chave, valor)
    bootstrap.run(str(app), False, [], opcoes)


def main() -> int:
    """Liga o painel; em caso de erro, explica o problema e espera a pessoa ler a mensagem."""
    try:
        iniciar()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:  # qualquer erro: mensagem amigável + detalhes num arquivo
        detalhes = traceback.format_exc()
        pasta_exe = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
        arquivo_log = pasta_exe / "erro_ao_iniciar.txt"
        try:
            arquivo_log.write_text(detalhes, encoding="utf-8")
        except OSError:
            arquivo_log = None
        print("\n" + "!" * 64)
        print("  Não foi possível iniciar o painel.")
        print("  O que tentar:")
        print("   1. Feche outras janelas do painel e abra de novo.")
        print("   2. Confirme que a pasta foi extraída por completo do arquivo .zip")
        print("      (não abra o programa de dentro do .zip).")
        print("   3. Se o antivírus bloqueou o programa, peça para liberá-lo.")
        if arquivo_log:
            print(f"  Detalhes técnicos foram salvos em: {arquivo_log}")
        print("  Envie esse arquivo para a equipe que mantém o painel.")
        print("!" * 64)
        print("\nDetalhe do erro:\n" + detalhes.strip().splitlines()[-1])
        try:
            input("\nPressione Enter para fechar esta janela...")
        except EOFError:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
