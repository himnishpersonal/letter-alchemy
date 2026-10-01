from alchemy.generate import extend_bank
from alchemy.puzzles import load_answer_key, load_bank


def test_extension_keeps_published_puzzles_and_answers():
    _, existing = load_bank()
    answer_key = load_answer_key()
    public, extended_key, review = extend_bank(2, 20261101)
    assert [item["number"] for item in public["puzzles"]] == list(range(1, len(existing) + 3))
    assert public["puzzles"][:len(existing)] == [puzzle.public() for puzzle in existing.values()]
    assert {number: extended_key[str(number)] for number in existing} == answer_key
    assert len(review["puzzles"]) == len(existing) + 2
    assert len({word for path in extended_key.values() for word in path}) == 5 * len(extended_key)
