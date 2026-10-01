# Render deployment and daily puzzle operations

The current deployment shape is **Render Free web service + Supabase Postgres**. Render runs the Python FastAPI container; Supabase stores anonymous completion results. The frontend is a separate project. [Frontend API contract](API.md).

## First deployment

1. Review the generated puzzles in `bank/review.json` and `bank/answer_key.json`. Decide whether to replace the two puzzles that rely on Y as a consonant. Set the intended launch date before players begin. Puzzle #1 is currently dated 2026-10-01; the server can override it with `ALCHEMY_LAUNCH_DATE=YYYY-MM-DD`.
2. Put this project in a **private Git repository** and connect it to Render. A public repository would expose future puzzles and the editorial answer key.
3. Create a Supabase project. In its dashboard, choose **Connect → Session pooler**, and copy the Postgres connection string on port 5432. Session mode is appropriate for this persistent Python service and supports IPv4. Put that string in Render's `DATABASE_URL` environment variable. Do not commit it to the repo. The backend creates its V1 completion table on startup.
4. In Render, create a **Blueprint** from the repository's root `render.yaml`. It defines a free Docker web service with `backend/` as the build context and `/healthz` as its health check. Render prompts for `DATABASE_URL` because its value is omitted from the YAML.
5. Set `ALCHEMY_LAUNCH_DATE` in the Render dashboard if the actual launch date differs from the bank's date. Once the frontend has a deployed origin, set `ALCHEMY_CORS_ORIGINS` to that origin (for example `https://game.example`). The backend defaults to localhost development origins only.
6. Check the assigned `onrender.com` URL: `/healthz`, `/puzzle/today`, `/docs`, validation, completion, and stats. Check that a future archive number returns 404. Confirm that a recorded completion remains after a new deployment.

The Dockerfile ships `puzzles.json` and the dictionary. It does not ship `answer_key.json` or other editorial files. Render's free service sleeps after 15 minutes without requests, so the first daily request after idle can take around a minute. Supabase's free project can pause after a week of low database activity. Both are limitations of the free plans, rather than puzzle-generation jobs.

## Puzzle generation schedule

**Daily release is automatic; generation is not daily.** Each request calculates the puzzle number from the server's UTC date and launch date, then reads that day's pre-generated puzzle. No cron job runs at midnight. A Render cron job would add cost and would not improve this flow.

For V1, generate and review **30 new puzzles about once a month**, before the bank has fewer than 30 days left. Generation happens on a developer machine, not on Render. Run:

```sh
cd backend
uv sync --extra dev --extra pipeline
uv run --extra pipeline alchemy-generate --append --count 30 --seed 20261101
uv run --extra pipeline alchemy-audit
uv run --extra dev --extra pipeline pytest -q
```

`--append` preserves the already published puzzle numbers, rules, and answer keys. The new puzzles appear at the end of the bank. Review the new paths and difficulty in `bank/review.json` and `bank/answer_key.json`, then commit and push the public bank, private answer key, and review report together. Render deploys the updated bank from that commit. **Never use the generator without `--append` after launch:** its fresh-bank mode starts numbering from 1.

This process is manual by design while puzzle quality still needs human review. If generation later becomes scheduled, schedule a monthly candidate build and review request, not automatic publication. Keep at least one month of approved puzzles ahead of today. The current 30-day bank ends after puzzle #30; with the current launch date, that is 2026-10-30.
