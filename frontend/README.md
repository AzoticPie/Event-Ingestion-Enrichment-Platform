# Frontend MVP

React + TypeScript dashboard for exercising backend APIs end-to-end.

## Coverage

- `GET /health/live`
- `GET /health/ready`
- `POST /v1/ingest/events`
- `POST /v1/ingest/events:batch`
- `GET /v1/events`
- `GET /v1/events/{event_id}`
- `GET /v1/aggregates/count`
- `GET /v1/aggregates/top-event-types`
- `GET /v1/aggregates/top-urls`
- `GET /v1/aggregates/unique-users`

## Setup

1. Ensure Node.js 20+ and npm are installed.
2. Copy env file:

   ```bash
   cp .env.example .env
   ```

3. Install dependencies:

   ```bash
   npm install
   ```

4. Run dev server:

   ```bash
   npm run dev
   ```

App runs on `http://localhost:5173` by default.

## Runtime settings

- Configure API base URL and `X-Ingest-Key` in the **Settings** page.
- Settings are stored in `sessionStorage` for current tab/session only.
- Key is masked in UI and not printed in request summaries.

## Build

```bash
npm run build
npm run preview
```

## Containerized frontend

Frontend image is defined in [`frontend/Dockerfile`](frontend/Dockerfile) and served with Nginx using [`frontend/nginx.conf`](frontend/nginx.conf).

Run with root compose setup:

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`

