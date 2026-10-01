# Letter Alchemy

The backend lives in [`backend/`](backend/). `frontend/` is intentionally empty.

## Flow

```mermaid
flowchart LR
  L[Word lists] --> G[Offline generator]
  G --> A[Bank audit and human playtest]
  A --> B[Published puzzle bank]
  B --> API[FastAPI]
  API --> V[Shared rules engine]
  API --> DB[(Completions DB)]
  Browser[Browser client] --> API
```

See [backend/README.md](backend/README.md) for backend setup and rules.

Frontend integration: [backend/API.md](backend/API.md). Render deployment and puzzle cadence: [backend/DEPLOY.md](backend/DEPLOY.md).
