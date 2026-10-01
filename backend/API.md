# Letter Alchemy API contract

This is the frontend integration contract for the current Python backend. Set the API base URL to the Render service URL in production (for example, `https://letter-alchemy-api.onrender.com`) or `http://127.0.0.1:8000` locally. The live OpenAPI explorer is at `/docs`.

All endpoints send and receive JSON except `/docs`. No user account or authentication is required in V1. Do not put `bank/answer_key.json` in a frontend bundle: it is an editorial answer key, and the API accepts any valid route.

## Daily flow

1. Fetch `GET /puzzle/today`. Render its five-letter `start` and `target`, four ordered rule cards, and **three** empty intermediate slots.
2. Let the player fill any slot. Send the current three slots to `POST /puzzle/{number}/validate` when they ask to check, or after a complete entry. Send `null` for blank slots.
3. Use each returned step status to explain errors. `solved: true` means all four links in the chain are legal.
4. On success, send the same three words to `POST /puzzle/{number}/complete` with a device UUID, elapsed seconds, and hint count. Store one random UUID in browser local storage and reuse it for future days.
5. Optionally fetch `/puzzle/{number}/stats` for the share screen.

The server chooses the daily puzzle by **UTC date**. Puzzle #1 is `ALCHEMY_LAUNCH_DATE` (currently 2026-10-01 unless overridden by the server). The number advances automatically at 00:00 UTC. The client does not submit its local date, and future puzzle numbers return 404. The current bank has 30 puzzles; extend it before day 31.

## Endpoints

### `GET /healthz`

```json
{"status":"ok","bank_size":30}
```

### `GET /puzzle/today` and `GET /puzzle/{number}`

The archive route serves only puzzle numbers already released. Both routes return the same shape:

```json
{
  "number": 1,
  "start": "THANK",
  "target": "MIGHT",
  "rules": ["vowel", "consonant", "anagram", "alphabet_retreat"],
  "difficulty": "easy"
}
```

`difficulty` is an automatic estimate; it is not a scoring contract. A puzzle before launch, a future puzzle, or a number missing from the bank returns HTTP 404:

```json
{"detail":"Puzzle not available"}
```

### `POST /puzzle/{number}/validate`

Request body has exactly three entries, in chain order. Words are case-insensitive on input and must contain exactly five ASCII letters. `null` is allowed for an empty slot.

```json
{"intermediates":["THINK",null,null]}
```

Response:

```json
{
  "solved": false,
  "steps": [
    {"step": 1, "status": "valid", "reason": null},
    {"step": 2, "status": "pending", "reason": null},
    {"step": 3, "status": "pending", "reason": null},
    {"step": 4, "status": "pending", "reason": null}
  ]
}
```

Each step checks the link from the prior word to the next word, including the final link to `target`. `status` is `valid`, `invalid`, or `pending`. `reason` for an invalid step is one of:

| Reason | Meaning |
| --- | --- |
| `not_a_word` | The next word is outside the accepted five-letter dictionary. |
| `rule_mismatch` | The next word does not follow that step's displayed rule. |
| `repeated_word` | That word already appeared earlier in the chain. |

A step is `pending` if either adjacent slot is blank. A later step may be `valid` even if an earlier step is invalid; `solved` is true only when **all four** steps are valid. A filled word may be legal without matching the editorial answer key.

Malformed requests return HTTP 422 with FastAPI's standard validation-error shape. Missing or unreleased puzzle numbers return 404.

### `POST /puzzle/{number}/complete`

Call after a full legal chain. Generate `device_id` once using `crypto.randomUUID()` and keep it in local storage. `seconds` is an integer from 1 to 86400. `hints_used` is an integer from 0 to 3.

```json
{
  "intermediates": ["THINK", "THING", "NIGHT"],
  "device_id": "b96bc2be-4a51-47f3-b5d2-fdfc79875c03",
  "seconds": 85,
  "hints_used": 0
}
```

The server replays the chain; it does not accept a claimed win without valid words and rules. First completion for a puzzle/device:

```json
{"recorded":true,"already_completed":false}
```

Repeated completion for the same puzzle/device:

```json
{"recorded":false,"already_completed":true}
```

An invalid chain returns HTTP 422 with the validation result under `detail`. Input-shape errors also return 422. Timing, hint count, and the anonymous UUID are client-reported, so they are casual game metrics rather than verified leaderboard data.

### `GET /puzzle/{number}/stats`

```json
{"completions":12,"median_seconds":91.5}
```

`median_seconds` is `null` when no completions have been recorded. The archive release restriction also applies to stats.

## Rule card meanings

All transformations produce another five-letter word in the accepted dictionary. Only one rule card is applied at each step.

| Card value | Legal transformation |
| --- | --- |
| `vowel` | Replace exactly one of A, E, I, O, U with a different vowel. |
| `consonant` | Replace exactly one consonant with a different consonant. **Y counts as a consonant** in this game. |
| `reverse` | Reverse all five letter positions exactly. |
| `anagram` | Rearrange the same five letters into a different word. An exact reversal uses `reverse`, not `anagram`. |
| `duplicate` | Replace exactly one letter with a copy of a different letter already present elsewhere in the word. |
| `alphabet_advance` | Advance exactly one letter by one alphabet position, such as C → D. Z does not wrap. |
| `alphabet_retreat` | Retreat exactly one letter by one alphabet position, such as L → K. A does not wrap. |
| `keyboard_left` | Replace exactly one letter with its immediate left neighbor on the same US QWERTY row. |
| `keyboard_right` | Replace exactly one letter with its immediate right neighbor on the same US QWERTY row. |

Keyboard rows are `QWERTYUIOP`, `ASDFGHJKL`, and `ZXCVBNM`. There is no wrapping between rows.

## Current limitations relevant to the UI

- There is no hint endpoint yet. The completion route records a client-supplied hint count; agree on hint behavior before adding a public hint button.
- There is no account or server-managed streak. Keep a V1 streak locally in the browser.
- The backend allows configured browser origins through CORS. Set `ALCHEMY_CORS_ORIGINS` on Render to the deployed frontend origin. Local defaults allow `http://localhost:3000` and `http://localhost:5173`.
- A free Render service can sleep when idle, so the first request after inactivity can be slow. Show a loading state for the daily fetch.
