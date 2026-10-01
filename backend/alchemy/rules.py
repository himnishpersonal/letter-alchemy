"""The single source of truth for legal word transformations."""

from enum import StrEnum
from itertools import combinations

VOWELS = frozenset("AEIOU")
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KEYBOARD_ROWS = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")
KEYBOARD_POSITION = {letter: (row, col) for row, letters in enumerate(KEYBOARD_ROWS) for col, letter in enumerate(letters)}


class Rule(StrEnum):
    CONSONANT = "consonant"
    VOWEL = "vowel"
    REVERSE = "reverse"
    ANAGRAM = "anagram"
    DUPLICATE = "duplicate"
    ALPHABET_ADVANCE = "alphabet_advance"
    ALPHABET_RETREAT = "alphabet_retreat"
    KEYBOARD_LEFT = "keyboard_left"
    KEYBOARD_RIGHT = "keyboard_right"

    @property
    def family(self) -> str:
        return self.value.split("_")[0]


def changed_position(before: str, after: str) -> tuple[int, str, str] | None:
    if len(before) != 5 or len(after) != 5:
        return None
    changed = [(i, a, b) for i, (a, b) in enumerate(zip(before, after)) if a != b]
    return changed[0] if len(changed) == 1 else None


def matches(before: str, after: str, rule: Rule) -> bool:
    """Check only the transformation; dictionary membership is a separate check."""
    if len(before) != 5 or len(after) != 5 or not before.isascii() or not after.isascii():
        return False
    if not before.isalpha() or not after.isalpha() or before != before.upper() or after != after.upper():
        return False
    if before == after:
        return False
    if rule == Rule.REVERSE:
        return after == before[::-1]
    if rule == Rule.ANAGRAM:
        return sorted(after) == sorted(before) and after != before[::-1]
    changed = changed_position(before, after)
    if changed is None:
        return False
    index, old, new = changed
    if rule == Rule.VOWEL:
        return old in VOWELS and new in VOWELS
    if rule == Rule.CONSONANT:
        return old not in VOWELS and new not in VOWELS
    if rule == Rule.DUPLICATE:
        return new in (before[:index] + before[index + 1 :])
    if rule == Rule.ALPHABET_ADVANCE:
        return ord(new) == ord(old) + 1
    if rule == Rule.ALPHABET_RETREAT:
        return ord(new) == ord(old) - 1
    if rule in (Rule.KEYBOARD_LEFT, Rule.KEYBOARD_RIGHT):
        row, col = KEYBOARD_POSITION[old]
        offset = -1 if rule == Rule.KEYBOARD_LEFT else 1
        new_col = col + offset
        return 0 <= new_col < len(KEYBOARD_ROWS[row]) and KEYBOARD_ROWS[row][new_col] == new
    raise ValueError(f"Unknown rule: {rule}")


def hamming_distance(left: str, right: str) -> int:
    return sum(a != b for a, b in zip(left, right))


def allowed_family_count(rules: tuple[Rule, ...]) -> int:
    return len({rule.family for rule in rules})
