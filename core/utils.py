from pathlib import Path


META_FILES = ["README.md", "pyproject.toml"]


def _fmt_src(file: str | Path, base_dir: Path):
    if isinstance(file, str):
        relative_path = file
    else:
        relative_path = file.relative_to(base_dir)
    txt = f"--- {relative_path} ---\n```"
    with open(file, mode="r") as f:
        for line in f.readlines():
            txt += line
    txt += "```\n\n"
    return txt


def get_snapshot():
    root_dir = Path(__file__).parent.parent
    snap_txt = ""

    for file in META_FILES:
        snap_txt += _fmt_src(file, root_dir)

    for file in root_dir.rglob("*.py"):
        if ".venv" not in str(file):
            snap_txt += _fmt_src(file, root_dir)
    return snap_txt
