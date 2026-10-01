"""Deterministic offline candidate generation. Never runs during an API request."""

import argparse
import json
import random
from collections import Counter
from datetime import date

from wordfreq import zipf_frequency

from .graph import WordGraph
from .lexicon import load_lexicon
from .puzzles import BANK, Puzzle, audit_path
from .rules import Rule, allowed_family_count, hamming_distance

RULES = tuple(Rule)


def route_count(graph: WordGraph, start: str, target: str, rules: tuple[Rule, ...], limit: int = 5) -> int:
    """Count common-word routes, stopping after limit."""
    count = 0

    def walk(word: str, depth: int, used: set[str]) -> None:
        nonlocal count
        if count >= limit:
            return
        if depth == 4:
            count += word == target
            return
        for next_word in graph.neighbors(word, rules[depth]):
            if next_word in used or (depth == 3 and next_word != target) or (depth < 3 and next_word == target):
                continue
            walk(next_word, depth + 1, used | {next_word})
            if count >= limit:
                return

    walk(start, 0, {start})
    return count


def candidate_paths(graph: WordGraph, starts: list[str], rng: random.Random):
    for start in starts:
        for _ in range(120):
            word = start
            path = [start]
            rules = []
            for depth in range(4):
                options = [(rule, graph.neighbors(word, rule)) for rule in RULES]
                options = [(rule, neighbors) for rule, neighbors in options if neighbors]
                if not options:
                    break
                # Favor constrained cards, whose instruction gives a useful clue.
                rule, neighbors = rng.choice(options)
                alternatives = [neighbor for neighbor in neighbors if neighbor not in path]
                if not alternatives:
                    break
                word = rng.choice(alternatives)
                rules.append(rule)
                path.append(word)
            if len(path) == 5 and hamming_distance(start, word) >= 4 and allowed_family_count(tuple(rules)) >= 2:
                yield path, tuple(rules)


def build_bank(count: int, seed: int, launch: date, start_number: int = 1,
               reserved_words: frozenset[str] = frozenset()) -> tuple[dict, dict, dict]:
    valid, common = load_lexicon()
    graph = WordGraph(common)
    rng = random.Random(seed)
    starts = [word for word in common if zipf_frequency(word.lower(), "en") >= 4.0]
    starts.sort()
    rng.shuffle(starts)
    candidates = []
    signatures = set()
    for path, rules in candidate_paths(graph, starts, rng):
        signature = (path[0], path[-1], rules)
        if signature in signatures:
            continue
        signatures.add(signature)
        if zipf_frequency(path[-1].lower(), "en") < 4.0:
            continue
        routes = route_count(graph, path[0], path[-1], rules)
        if not 1 <= routes <= 3:
            continue
        min_frequency = min(zipf_frequency(word.lower(), "en") for word in path)
        branching = sum(len(graph.neighbors(word, rule)) for word, rule in zip(path, rules))
        score = min_frequency * 10 - branching / 8 - (routes - 1) * 3
        candidates.append((score, path, rules, routes, branching))
        if len(candidates) >= max(count * 100, 3000):
            break
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = []
    used_words = set(reserved_words)
    rule_counts = Counter()
    for score, path, rules, routes, branching in candidates:
        if len(selected) >= count:
            break
        if used_words.intersection(path):
            continue
        # Balance the cards across the first bank rather than repeating one template.
        family_counts = Counter(rule.family for rule in rules)
        if any(rule_counts[family] > count * 1.5 for family in family_counts):
            continue
        number = start_number + len(selected)
        difficulty = "easy" if branching <= 8 and routes == 1 else "medium" if branching <= 20 else "hard"
        puzzle = Puzzle(number, path[0], path[-1], rules, difficulty)
        if audit_path(puzzle, path, valid):
            continue
        selected.append((puzzle, path, score, routes, branching))
        used_words.update(path)
        rule_counts.update(rule.family for rule in rules)
    if len(selected) < count:
        raise RuntimeError(f"Only found {len(selected)} puzzles; requested {count}")
    public = {"launch_date": launch.isoformat(), "puzzles": [puzzle.public() for puzzle, *_ in selected]}
    answer_key = {str(puzzle.number): path for puzzle, path, *_ in selected}
    review = {"status": "generated_candidates_needing_playtest", "seed": seed,
              "puzzles": [{"number": puzzle.number, "path": path, "score": round(score, 2),
                           "common_route_count": routes, "branching_total": branching}
                          for puzzle, path, score, routes, branching in selected],
              "rule_families": dict(rule_counts)}
    return public, answer_key, review


def extend_bank(count: int, seed: int) -> tuple[dict, dict, dict]:
    """Add candidate days without changing any existing puzzle or answer."""
    existing_public = json.loads((BANK / "puzzles.json").read_text())
    existing_answers = json.loads((BANK / "answer_key.json").read_text())
    existing_review = json.loads((BANK / "review.json").read_text())
    old_puzzles = existing_public["puzzles"]
    if [item["number"] for item in old_puzzles] != list(range(1, len(old_puzzles) + 1)):
        raise ValueError("Existing puzzle numbers are not contiguous")
    if set(existing_answers) != {str(item["number"]) for item in old_puzzles}:
        raise ValueError("Existing answer key does not match puzzle bank")
    launch = date.fromisoformat(existing_public["launch_date"])
    reserved = frozenset(word for path in existing_answers.values() for word in path)
    new_public, new_answers, new_review = build_bank(count, seed, launch,
                                                      start_number=len(old_puzzles) + 1,
                                                      reserved_words=reserved)
    combined_public = {"launch_date": existing_public["launch_date"],
                       "puzzles": old_puzzles + new_public["puzzles"]}
    combined_answers = {**existing_answers, **new_answers}
    combined_review = {**existing_review,
                       "puzzles": existing_review["puzzles"] + new_review["puzzles"],
                       "append_runs": existing_review.get("append_runs", []) + [
                           {"seed": seed, "first_number": len(old_puzzles) + 1,
                            "last_number": len(combined_public["puzzles"])}]}
    counts = Counter(existing_review["rule_families"])
    counts.update(new_review["rule_families"])
    combined_review["rule_families"] = dict(counts)
    return combined_public, combined_answers, combined_review


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--launch-date", type=date.fromisoformat, default=date(2026, 10, 1))
    parser.add_argument("--append", action="store_true", help="Preserve existing puzzles and add --count new days")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")
    public, answer_key, review = (extend_bank(args.count, args.seed) if args.append else
                                  build_bank(args.count, args.seed, args.launch_date))
    BANK.mkdir(exist_ok=True)
    for name, data in (("puzzles.json", public), ("answer_key.json", answer_key), ("review.json", review)):
        (BANK / name).write_text(json.dumps(data, indent=2) + "\n")
    print(f"Bank now has {len(public['puzzles'])} puzzles; review new candidates before deployment")


if __name__ == "__main__":
    main()
