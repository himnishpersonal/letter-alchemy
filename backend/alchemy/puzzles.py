"""Bank loading and sequence validation."""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .lexicon import ROOT, load_lexicon
from .rules import Rule, allowed_family_count, hamming_distance, matches

BANK = ROOT / "bank"


@dataclass(frozen=True)
class Puzzle:
    number: int
    start: str
    target: str
    rules: tuple[Rule, Rule, Rule, Rule]
    difficulty: str

    def public(self, show_rules: bool = True) -> dict:
        result = {"number": self.number, "start": self.start, "target": self.target}
        if show_rules:
            result["rules"] = [rule.value for rule in self.rules]
        result["difficulty"] = self.difficulty
        return result


def load_bank(path: Path = BANK / "puzzles.json") -> tuple[date, dict[int, Puzzle]]:
    raw = json.loads(path.read_text())
    launch = date.fromisoformat(raw["launch_date"])
    puzzles = {}
    for record in raw["puzzles"]:
        puzzle = Puzzle(number=record["number"], start=record["start"], target=record["target"],
                        rules=tuple(Rule(rule) for rule in record["rules"]), difficulty=record["difficulty"])
        if puzzle.number in puzzles:
            raise ValueError(f"Duplicate puzzle number {puzzle.number}")
        puzzles[puzzle.number] = puzzle
    return launch, puzzles


def load_answer_key(path: Path = BANK / "answer_key.json") -> dict[int, list[str]]:
    """Private canonical paths, keyed by puzzle number. Never exposed by the API."""
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("Answer key must be an object keyed by puzzle number")
    answers = {}
    for number, words in raw.items():
        if not str(number).isdigit() or not isinstance(words, list) or len(words) != 5:
            raise ValueError(f"Invalid answer key entry: {number}")
        if any(not isinstance(word, str) or len(word) != 5 or not word.isascii() or not word.isalpha() or word != word.upper() for word in words):
            raise ValueError(f"Invalid word in answer key entry: {number}")
        answers[int(number)] = words
    return answers


def audit_path(puzzle: Puzzle, path: list[str], valid: frozenset[str]) -> list[str]:
    issues = []
    if len(path) != 5 or path[0] != puzzle.start or path[-1] != puzzle.target:
        return ["path must have five words and match endpoints"]
    if len(set(path)) != 5:
        issues.append("path repeats a word")
    if hamming_distance(puzzle.start, puzzle.target) < 4:
        issues.append("endpoints differ at fewer than four positions")
    if allowed_family_count(puzzle.rules) < 2:
        issues.append("fewer than two rule families")
    for i, (before, after, rule) in enumerate(zip(path, path[1:], puzzle.rules), 1):
        if after not in valid:
            issues.append(f"step {i} word is not in dictionary")
        if not matches(before, after, rule):
            issues.append(f"step {i} violates {rule.value}")
    return issues


def validate_intermediates(puzzle: Puzzle, intermediates: list[str | None], valid: frozenset[str]) -> dict:
    if len(intermediates) != 3:
        raise ValueError("Exactly three intermediate slots are required")
    words = [puzzle.start, *intermediates, puzzle.target]
    steps = []
    for i, rule in enumerate(puzzle.rules):
        before, after = words[i], words[i + 1]
        if before is None or after is None:
            steps.append({"step": i + 1, "status": "pending", "reason": None})
        elif after not in valid:
            steps.append({"step": i + 1, "status": "invalid", "reason": "not_a_word"})
        elif not matches(before, after, rule):
            steps.append({"step": i + 1, "status": "invalid", "reason": "rule_mismatch"})
        elif after in words[: i + 1]:
            steps.append({"step": i + 1, "status": "invalid", "reason": "repeated_word"})
        else:
            steps.append({"step": i + 1, "status": "valid", "reason": None})
    solved = all(step["status"] == "valid" for step in steps)
    return {"solved": solved, "steps": steps}
