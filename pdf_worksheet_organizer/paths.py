import pathlib


FILE = pathlib.Path(__file__)
IN_DIR = FILE.parent / "in"
OUT_DIR = FILE.parent / "out"

IN_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

PDF_PATHS = list(IN_DIR.glob("*.pdf"))
PDF_PATH = PDF_PATHS[0]
