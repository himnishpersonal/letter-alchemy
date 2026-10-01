"""Publish gate for generated puzzle banks."""

import hashlib
import json
import sys
from collections import Counter

from .generate import route_count
from .graph import WordGraph
from .lexicon import DATA, load_lexicon
from .puzzles import BANK, audit_path, load_answer_key, load_bank


def audit() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    valid, common = load_lexicon()
    graph = WordGraph(common)
    launch, puzzles = load_bank()
    answer_key = load_answer_key()
    source = json.loads((DATA / "source.json").read_text())
    for name in ("valid.txt", "common.txt", "blocklist.txt"):
        digest = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
        if digest != source.get(name + "_sha256"):
            errors.append(f"{name} differs from pinned source metadata")
    if sorted(puzzles) != list(range(1, len(puzzles) + 1)):
        errors.append("Puzzle numbers must be contiguous starting at 1")
    if set(answer_key) != set(puzzles):
        errors.append("Answer key numbers do not match public bank")
    used_words = set()
    rule_counts = Counter()
    for number, puzzle in puzzles.items():
        path = answer_key.get(number)
        if not isinstance(path, list):
            continue
        for issue in audit_path(puzzle, path, valid):
            errors.append(f"Puzzle {number}: {issue}")
        if any(word not in common for word in path):
            errors.append(f"Puzzle {number}: curated path contains non-common word")
        if used_words.intersection(path):
            errors.append(f"Puzzle {number}: word repeats elsewhere in bank")
        used_words.update(path)
        routes = route_count(graph, puzzle.start, puzzle.target, puzzle.rules)
        if routes not in (1, 2, 3):
            errors.append(f"Puzzle {number}: {routes} common-word routes, expected 1-3")
        rule_counts.update(rule.value for rule in puzzle.rules)
    if not any("reverse" == rule for rule in rule_counts):
        warnings.append("No reverse rule in this bank: familiar five-letter reverse pairs are scarce")
    return {"ok": not errors, "launch_date": launch.isoformat(), "puzzle_count": len(puzzles),
            "valid_words": len(valid), "common_words": len(common), "rule_counts": dict(rule_counts),
            "errors": errors, "warnings": warnings}


def main() -> None:
    report = audit()
    (BANK / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
