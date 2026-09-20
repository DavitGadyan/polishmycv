#!/usr/bin/env python3
"""Print the polishmycv data home — the repo that holds docs/ and output/.

The skill is installed globally (symlinked into ~/.claude/skills), so it can be invoked from any
directory. Resolution order, first match wins:

  1. $POLISHMYCV_HOME
  2. the nearest directory at or above the current one that contains docs/portfolio-catalogue.json
  3. the repo this script physically lives in (…/skills/polishmycv/scripts/home.py → repo root),
     which is where the symlink points

Usage:  HOME_DIR=$(python3 ~/.claude/skills/polishmycv/scripts/home.py)
        python3 home.py --check   # also verifies the expected files exist
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = Path("docs") / "portfolio-catalogue.json"


def resolve() -> Path:
    env = os.environ.get("POLISHMYCV_HOME")
    if env and (Path(env) / MARKER).exists():
        return Path(env).resolve()
    here = Path.cwd().resolve()
    for d in (here, *here.parents):
        if (d / MARKER).exists():
            return d
    return Path(__file__).resolve().parent.parent.parent.parent


def main() -> int:
    home = resolve()
    print(home)
    if "--check" in sys.argv:
        problems = [str(p) for p in (MARKER, Path("docs/cv/base-cv.json"), Path("docs/cv/headshot.png"))
                    if not (home / p).exists()]
        if problems:
            print("missing: " + ", ".join(problems) + f"  (run `/polishmycv refresh` or set POLISHMYCV_HOME)",
                  file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
