"""Rebuild the shipped word lists from pinned ESDB and wordfreq.

Run from backend/: uv run --extra pipeline python scripts/build_lexicon.py
Review resulting words before publishing a new bank.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.request import urlopen

from wordfreq import top_n_list, zipf_frequency

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BLOCKED = {line.strip().lower() for line in (DATA / "blocklist.txt").read_text().splitlines()
           if line.strip() and not line.startswith("#")}
ESDB_URL = "https://raw.githubusercontent.com/en-wl/wordlist/rel-2026.02.25/data/scowl-pre.txt"
ESDB_SHA256 = "c4f5cfaabce46bc6fe151c2aa29b121425aa045a14166ed6daaffe2cc872f0f3"
ENTRY = re.compile(r"(\d{2})\b[^:]*:\s*(.*)")
WORD = re.compile(r"(?<![A-Za-z])[a-z]{5}(?![A-Za-z])")


def clean_word(word: str) -> bool:
    return len(word) == 5 and word.isascii() and word.isalpha() and word.islower() and word not in BLOCKED


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--esdb-source", type=Path, help="Use a previously downloaded pinned ESDB source file")
    args = parser.parse_args()
    source_bytes = args.esdb_source.read_bytes() if args.esdb_source else urlopen(ESDB_URL, timeout=30).read()
    if hashlib.sha256(source_bytes).hexdigest() != ESDB_SHA256:
        raise ValueError("ESDB source hash differs from pinned release")
    dictionary_words = set()
    for line in source_bytes.decode("utf-8").splitlines():
        match = ENTRY.match(line)
        if match and int(match[1]) <= 60:
            dictionary_words.update(WORD.findall(match[2]))
    words = {word for word in top_n_list("en", 100_000) if clean_word(word)}
    valid = sorted(word.upper() for word in words & dictionary_words if zipf_frequency(word, "en") >= 2.5)
    common = sorted(word.upper() for word in words & dictionary_words if zipf_frequency(word, "en") >= 3.5)
    for name, contents in (("valid.txt", valid), ("common.txt", common)):
        (DATA / name).write_text("\n".join(contents) + "\n")
    metadata = {"source": "ESDB scowl-pre plus wordfreq", "esdb_release": "rel-2026.02.25",
                "esdb_url": ESDB_URL, "esdb_sha256": ESDB_SHA256, "esdb_size_max": 60,
                "wordfreq_version": "3.1.1", "language": "en",
                "top_n": 100000, "valid_min_zipf": 2.5, "common_min_zipf": 3.5,
                "valid_count": len(valid), "common_count": len(common)}
    for name in ("valid.txt", "common.txt", "blocklist.txt"):
        metadata[name + "_sha256"] = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
    (DATA / "source.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {len(valid)} valid and {len(common)} common words")


if __name__ == "__main__":
    main()
