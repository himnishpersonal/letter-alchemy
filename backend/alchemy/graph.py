"""Dictionary-constrained neighbors for the offline generator and audits."""

from collections import defaultdict

from .rules import ALPHABET, KEYBOARD_POSITION, KEYBOARD_ROWS, VOWELS, Rule


class WordGraph:
    def __init__(self, words: frozenset[str]):
        self.words = words
        groups = defaultdict(list)
        for word in words:
            groups["".join(sorted(word))].append(word)
        self.anagrams = {key: tuple(sorted(values)) for key, values in groups.items()}
        self._cache: dict[tuple[str, Rule], tuple[str, ...]] = {}

    def neighbors(self, word: str, rule: Rule) -> tuple[str, ...]:
        key = (word, rule)
        if key in self._cache:
            return self._cache[key]
        candidates: set[str] = set()
        if rule == Rule.REVERSE:
            candidates.add(word[::-1])
        elif rule == Rule.ANAGRAM:
            candidates.update(self.anagrams.get("".join(sorted(word)), ()))
            candidates.discard(word[::-1])
        else:
            for i, old in enumerate(word):
                if rule == Rule.VOWEL:
                    letters = VOWELS if old in VOWELS else ()
                elif rule == Rule.CONSONANT:
                    letters = (letter for letter in ALPHABET if letter not in VOWELS) if old not in VOWELS else ()
                elif rule == Rule.DUPLICATE:
                    letters = set(word[:i] + word[i + 1 :])
                elif rule == Rule.ALPHABET_ADVANCE:
                    letters = (chr(ord(old) + 1),) if old != "Z" else ()
                elif rule == Rule.ALPHABET_RETREAT:
                    letters = (chr(ord(old) - 1),) if old != "A" else ()
                else:
                    row, col = KEYBOARD_POSITION[old]
                    offset = -1 if rule == Rule.KEYBOARD_LEFT else 1
                    letters = (KEYBOARD_ROWS[row][col + offset],) if 0 <= col + offset < len(KEYBOARD_ROWS[row]) else ()
                for letter in letters:
                    if letter != old:
                        candidates.add(word[:i] + letter + word[i + 1 :])
        result = tuple(sorted(candidates & self.words - {word}))
        self._cache[key] = result
        return result
