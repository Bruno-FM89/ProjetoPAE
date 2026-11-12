# -*- mode: python ; coding: utf-8 -*-
"""Receita do PyInstaller para gerar o executável do painel (Windows).

Rodar a partir da pasta do projeto:  pyinstaller executavel/painel_heliopolis.spec --noconfirm
(ou simplesmente: executavel\\gerar_executavel.bat)

Ideias principais
-----------------
* Modo "pasta" (onedir): o resultado é a pasta dist/PainelHeliopolis com o .exe e
  uma subpasta _internal. Abre bem mais rápido que o modo "arquivo único", que
  precisaria descompactar tudo a cada abertura.
* O Streamlit executa app.py e as páginas de app_pages/ como ARQUIVOS; por isso
  eles vão como dados. Os pacotes do projeto (views, controllers, models, services)
  vão como "hiddenimports", para o PyInstaller incluir também as bibliotecas que
  eles usam (pandas, plotly...).
* Só os dados PREPARADOS entram. As pastas "bruto" (planilhas com nomes de
  moradores e Shapefiles originais) ficam de fora, por privacidade.
* O mapa não precisa de bibliotecas geográficas (GDAL, pyproj...): o app lê GeoJSON
  já convertido. Isso evita os problemas mais comuns de empacotamento.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, copy_metadata

RAIZ = Path(SPECPATH).parent  # SPECPATH = pasta deste arquivo (executavel/)

# --- arquivos do painel ---------------------------------------------------------------
datas = [
    (str(RAIZ / "app.py"), "."),
    (str(RAIZ / "app_pages"), "app_pages"),
    (str(RAIZ / ".streamlit" / "config.toml"), ".streamlit"),
    # dados preparados (sem as pastas "bruto")
    (str(RAIZ / "data" / "reais"), "data/reais"),
    (str(RAIZ / "data" / "demonstracao"), "data/demonstracao"),
    (str(RAIZ / "data" / "qualar" / "LEIA-ME.md"), "data/qualar"),
]
for arquivo in ("medicoes_termometros.csv.gz", "metadados_termometros.json", "locais_termometros.csv"):
    datas.append((str(RAIZ / "data" / "termometros" / arquivo), "data/termometros"))
for arquivo in sorted((RAIZ / "data" / "geo").glob("*.*json")):
    datas.append((str(arquivo), "data/geo"))

# --- bibliotecas ----------------------------------------------------------------------------
binaries = []
hiddenimports = []
for pacote in ("streamlit",):
    d, b, h = collect_all(pacote)  # código, arquivos do site (HTML/JS) e submódulos do Streamlit
    datas += d
    binaries += b
    hiddenimports += h
datas += collect_data_files("plotly")  # o Plotly guarda definições dos gráficos em arquivos JSON
datas += copy_metadata("streamlit") + copy_metadata("plotly") + copy_metadata("pandas") + copy_metadata("numpy")
for pacote in ("views", "controllers", "models", "services"):
    hiddenimports += collect_submodules(pacote)

a = Analysis(
    [str(RAIZ / "executavel" / "iniciar_painel.py")],
    pathex=[str(RAIZ)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        # não usados pelo painel (deixam o executável menor)
        "tkinter", "matplotlib", "IPython", "jupyter", "notebook", "pytest", "openpyxl",
        "pyproj", "shapefile", "sqlalchemy", "psycopg2", "PyInstaller",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PainelHeliopolis",
    console=True,  # a janela preta mostra o endereço do painel e permite encerrá-lo
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="PainelHeliopolis", upx=False)
