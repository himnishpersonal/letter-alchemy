from alchemy.rules import Rule, matches


def test_each_rule():
    assert matches("BREAD", "BROAD", Rule.VOWEL)
    assert matches("BOARD", "HOARD", Rule.CONSONANT)
    assert matches("DEVIL", "LIVED", Rule.REVERSE)
    assert matches("BROAD", "BOARD", Rule.ANAGRAM)
    assert matches("STATE", "STATS", Rule.DUPLICATE)
    assert matches("STEAL", "STEAM", Rule.ALPHABET_ADVANCE)
    assert matches("LOVER", "LOWER", Rule.ALPHABET_ADVANCE)
    assert matches("TEARS", "YEARS", Rule.KEYBOARD_RIGHT)
    assert matches("THREE", "THREW", Rule.KEYBOARD_LEFT)


def test_boundaries_and_distinct_rules():
    assert not matches("ZEBRA", "AEBRA", Rule.ALPHABET_ADVANCE)
    assert not matches("APPLE", "QPPLE", Rule.KEYBOARD_LEFT)
    assert not matches("DEVIL", "LIVED", Rule.ANAGRAM)
    assert not matches("ABCDE", "ABCDE", Rule.ANAGRAM)
    assert not matches("BREAD", "BROAD", Rule.CONSONANT)
    assert not matches("STATE", "STATS", Rule.VOWEL)
    assert not matches("AAAAA", "AAAAB", Rule.DUPLICATE)
