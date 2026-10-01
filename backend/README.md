# Letter Alchemy backend

FastAPI serves a pre-generated daily puzzle bank. The same pure Python rules engine checks generation and player submissions. The server never generates a puzzle during a request and never returns the stored solution path. Thirty generated puzzles are included for review; they pass the automated audit but still need human playtesting before a public launch. See the [frontend API contract](API.md) and [Render deployment guide](DEPLOY.md).

## Game contract

- Start and target are five ASCII letters. Exactly four ordered rule cards and three intermediate words form a solution.
- Every intermediate word must be in `data/valid.txt`. Published solutions use `data/common.txt`, a smaller frequency-filtered list.
- The start and target differ in at least four positions. Each path has five distinct words and at least two rule families.
- Vowels are A, E, I, O, U; Y is a consonant. A vowel or consonant change replaces exactly one letter with another of the same class.
- Anagram rearranges the same five letters into a different word; exact reversal belongs only to `reverse`.
- Duplicate replaces one position with a copy of a letter already in another position of that word.
- Alphabet advance/retreat changes one letter by one alphabet position, with no A/Z wrap.
- Keyboard left/right changes one letter to its immediate horizontal neighbor on a US QWERTY row, with no row wrap.
- Different valid routes are accepted. The bank's path is used for review only. Submitted timings and anonymous device IDs are client supplied and should be treated as casual game metrics.

## Run locally

```sh
cd backend
uv sync --extra dev --extra pipeline
uv run --extra dev uvicorn alchemy.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for OpenAPI. Local completions use `backend/alchemy.sqlite3` by default. Puzzle #1 is released on 2026-10-01 UTC. Set `ALCHEMY_LAUNCH_DATE=YYYY-MM-DD` to schedule that first puzzle for a different UTC day. The bank ends after #30; generate and review more puzzles before it runs out.

## API

| Route | Behavior |
| --- | --- |
| `GET /healthz` | Process and bank check |
| `GET /puzzle/today` | UTC daily puzzle |
| `GET /puzzle/{number}` | Released archive puzzle; future numbers return 404 |
| `POST /puzzle/{number}/validate` | Check each of three slots; incomplete edges are `pending` |
| `POST /puzzle/{number}/complete` | Replay full path and record one result per puzzle/device |
| `GET /puzzle/{number}/stats` | Completion count and median submitted duration |

Submit `{"intermediates":["THINK","THING","NIGHT"]}` to `/puzzle/1/validate`. Strings are case-insensitive; a slot can be `null` during partial validation. A completion also includes `device_id` (a random UUID), `seconds` (1–86400), and `hints_used` (0–3). A completion with an invalid path returns 422. Repeating a successful completion for the same device and puzzle returns `already_completed: true` without changing stats.

## Rebuild and review the bank

```sh
cd backend
uv run --extra pipeline python scripts/build_lexicon.py
uv run --extra pipeline alchemy-generate --count 30 --seed 20261001 --launch-date 2026-10-01
uv run --extra pipeline alchemy-audit
uv run --extra dev --extra pipeline pytest -q
```

After launch, use `alchemy-generate --append --count 30 --seed YYYYMMDD` to add days while preserving published puzzles. The full monthly workflow is in [DEPLOY.md](DEPLOY.md).

`data/source.json` pins the word list inputs and hashes. The builder intersects five-letter entries parsed from the pinned ESDB release (size 60 or below) with `wordfreq` 3.1.1 English frequency data. This is a conservative game lexicon rather than a full spelling dictionary. ESDB's required notice is in `data/ESDB_LICENSE.txt`; `data/blocklist.txt` removes manually identified inappropriate words and proper names. `bank/puzzles.json` is public data. `bank/answer_key.json` privately maps every puzzle number to its five-word canonical path; the audit checks each path against the public rules. `bank/review.json` records route counts and generation metrics. The container copies only public bank data. An editor should play each candidate and review spelling, meaning, clue quality, and difficulty before publishing it.

## Deploy

Use the root [render.yaml](../render.yaml) for a Render Free Docker web service and set `DATABASE_URL` to a persistent Supabase PostgreSQL connection string in Render's dashboard. The service refuses to start on Render without it because local container storage is temporary. Set `ALCHEMY_CORS_ORIGINS` to the frontend origins separated by commas. See [DEPLOY.md](DEPLOY.md) for the full setup and release process.

The API serves only released numbers according to server UTC. Browser local time can be used for display and streaks; it does not control access to future puzzles. Database tables are created on startup for this small V1; use a migration tool before evolving the schema. `/stats` currently reads durations from the results table, so add cached aggregates if traffic grows. No accounts, trusted timing, or leaderboard are included.
