#!/usr/bin/env python3
"""Run every offline validation shipped with the skill."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
REFERENCES = ROOT / "references"

COMMANDS = [
    [
        sys.executable,
        str(SCRIPTS / "check_glossary.py"),
        str(REFERENCES / "glossary"),
    ],
    [
        sys.executable,
        str(SCRIPTS / "check_community_terms.py"),
        str(REFERENCES / "community-terms.tsv"),
    ],
    [
        sys.executable,
        str(SCRIPTS / "check_translation_cases.py"),
        str(REFERENCES / "translation-regression-cases.tsv"),
    ],
    [sys.executable, str(SCRIPTS / "smoke_test.py")],
]


def main() -> int:
    for command in COMMANDS:
        subprocess.run(command, check=True)
    print("OK: all offline validations passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
