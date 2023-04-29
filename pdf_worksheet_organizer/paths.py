import pathlib


REPO_DIR = pathlib.Path(__file__).parents[1]
IN_DIR = REPO_DIR / "in"
OUT_DIR = REPO_DIR / "out"

IN_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

PDF_PATHS = list(IN_DIR.glob("*.pdf"))
PDF_PATH = PDF_PATHS[0]

CWD = pathlib.Path.cwd()
OUT_FILE = OUT_DIR / f"{PDF_PATH.stem}-replaced.pdf".replace(" ", "-")
RELATIVE_OUT_FILE = OUT_FILE.relative_to(CWD)