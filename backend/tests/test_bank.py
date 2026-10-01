from alchemy.audit import audit
from alchemy.puzzles import load_answer_key, load_bank


def test_published_bank_passes_full_audit():
    report = audit()
    assert report["ok"], report["errors"]
    assert report["puzzle_count"] == 30


def test_every_puzzle_has_a_private_answer_key():
    _, puzzles = load_bank()
    answer_key = load_answer_key()
    assert set(answer_key) == set(puzzles)
    for number, puzzle in puzzles.items():
        assert answer_key[number][0] == puzzle.start
        assert answer_key[number][-1] == puzzle.target
