"""Load the pinned five-letter word lists shipped with the service."""

import os
from pathlib import Path

ROOT = Path(os.getenv("ALCHEMY_DATA_ROOT", Path(__file__).resolve().parents[1]))
DATA = ROOT / "data"


def load_words(path: Path) -> frozenset[str]:
    words = frozenset(line.strip().upper() for line in path.read_text().splitlines() if line.strip())
    if any(len(word) != 5 or not word.isascii() or not word.isalpha() for word in words):
        raise ValueError(f"Invalid word in {path}")
    return words


def load_lexicon() -> tuple[frozenset[str], frozenset[str]]:
    valid = load_words(DATA / "valid.txt")
    common = load_words(DATA / "common.txt")
    if not common <= valid:
        raise ValueError("Common words must be valid")
    return valid, common
