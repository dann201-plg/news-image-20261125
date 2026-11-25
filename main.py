"""Entry program for news-image-20261125 (Python 3.13, standard library only).

The deliverable is the pre-rendered image entry.png sitting next to this
file. Running the program copies that image, byte for byte, to the
grader's output directory, so the two grading runs produce identical
bytes. When run outside the grader container, the output directory can
be overridden with MAKEFUN_OUTPUT_DIR:

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py

The image itself is produced by draw_news25.py from
stories-20261125.json; see README.md for the reproduce command.
"""

import os
import shutil
from pathlib import Path


def main():
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    src = Path(__file__).with_name("entry.png")
    shutil.copyfile(src, out_dir / "entry.png")


if __name__ == "__main__":
    main()
