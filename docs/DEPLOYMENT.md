# Jinsie AI Video Studio v1.0 Beta Deployment

This is the minimal production deployment setup for the FastAPI backend and Vue/Vite frontend.

## Frontend

- Platform: Vercel
- Root Directory: `frontend`
- Install Command: `npm ci`
- Build Command: `npm run build`
- Output Directory: `dist`
- Production Branch: `master`
- Domain: `studio.jinsie.com`
- Environment variable:
  - `VITE_API_BASE_URL=https://api.studio.jinsie.com`

Vite environment variables are build-time values. After changing `VITE_API_BASE_URL`, redeploy the frontend so the generated bundle uses the new backend URL.

The frontend uses Vue history mode. `frontend/vercel.json` rewrites all routes to `/index.html` so refreshed routes such as `/studio` continue to load the SPA.

## Backend

- Platform: Docker runtime using the root `Dockerfile`
- Health check: `GET /health`
- Process model: single instance, single worker
- Runtime system dependencies:
  - `ffmpeg`
  - `fontconfig`
  - `fonts-noto-cjk`
- Domain: `api.studio.jinsie.com`
- CORS:
  - `CORS_ALLOW_ORIGINS=https://studio.jinsie.com`

All model API keys, tokens, and provider credentials must be configured only as backend platform environment variables. Do not put production API keys in the frontend, Git, Docker image, or local `.env` files that are committed.

The Docker command expands the platform `PORT` value and falls back to `8004`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8004}
```

## Persistent Storage

Mount the persistent disk at:

```text
/app/assets/mock
```

Do not mount the entire `/app/assets` directory. The image contains built-in sample assets under `/app/assets/samples`, and mounting all of `/app/assets` would hide those files.

Storage layout:

- `/app/assets/samples`: bundled in the Docker image, used for built-in samples
- `/app/assets/mock`: persistent runtime output directory

Runtime content stored under `/app/assets/mock` includes:

- `status.json`
- `outputs.json`
- generated images
- audio files
- subtitle files
- final videos
- history / generated work data

Without a persistent disk, generated history and runtime outputs will be lost when the instance restarts or is redeployed.

## Beta Limits

- Text-to-image character consistency still has model-level limits.
- Complex multi-character scenes may require regeneration.
- External LLM, SiliconFlow, image, and TTS providers may time out, rate-limit, or return 5xx errors.
- The first production version is not designed for multiple backend instances or multiple workers.
- Until access control is added, do not expose unlimited real generation capability publicly.
