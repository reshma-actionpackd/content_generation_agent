# AI Social Media Video Generator

A production-ready full-stack app that generates business-focused short videos from prompts using AI scripts + HeyGen avatars.

## Features

- Prompt-based video generation with modes: `ad`, `reel`, `presentation`
- Optional audience and tone controls
- Optional logo upload for branding overlay (top-left)
- Script + caption generation using LangChain and OpenAI
- Video generation via HeyGen API
- FFmpeg logo compositing pipeline (`overlay=10:10`, max logo width ~100px)
- Local temp video storage in `/tmp`
- Auto-cleanup of videos older than 10 minutes
- Video preview + download in modern animated Next.js UI
- Railway-ready frontend and backend services

## Folder Structure

```text
Generative_agent/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── package.json
│   ├── next.config.mjs
│   ├── postcss.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── next-env.d.ts
│   ├── Dockerfile
│   └── .env.example
└── README.md
```

## Environment Variables

### Backend (`backend/.env`)

Use `backend/.env.example`:

```env
OPENAI_API_KEY=your_openai_api_key
HEYGEN_API_KEY=your_heygen_api_key
OPENAI_MODEL=gpt-4o-mini
HEYGEN_AVATAR_ID=Josh_lite20230714
HEYGEN_VOICE_ID=1bd001e7e50f421d891986aad5158bc8
FFMPEG_BINARY=ffmpeg
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend (`frontend/.env.local`)

Use `frontend/.env.example`:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Local Setup

### 1) Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend endpoints:
- `POST /generate`
- `GET /video/{id}`
- `GET /health`

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## API Contract

### `POST /generate`

Accepts either JSON or multipart form.

JSON body:

```json
{
  "prompt": "Launch campaign for eco-friendly skincare",
  "mode": "ad",
  "audience": "Women 20-35 interested in sustainable products",
  "tone": "Energetic"
}
```

Response:

```json
{
  "video_url": "/video/<uuid>",
  "script": "...",
  "caption": "..."
}
```

### `GET /video/{id}`
Returns `video/mp4` from `/tmp/{id}.mp4`.

### `GET /health`
Returns `{ "status": "OK" }`.

## Railway Deployment

Deploy as two services from the same repository.

### Backend Service

- Root Directory: `backend`
- Build: Dockerfile (auto-detected)
- Start Command: from Dockerfile (`uvicorn main:app --host 0.0.0.0 --port 8000`)
- Add env vars from `backend/.env.example`
- Ensure port `8000` exposed by service

### Frontend Service

- Root Directory: `frontend`
- Build: Dockerfile (auto-detected)
- Add env var:
  - `NEXT_PUBLIC_BACKEND_URL=https://<your-backend-domain>`
- Railway starts Next.js via Dockerfile on port `3000`

## Notes

- `/tmp` storage is ephemeral and suited for short-lived generated files.
- Video files are cleaned every 60 seconds if older than 10 minutes.
- Uploaded logos are stored at `/tmp/logo.png` and composited on generated output videos in the top-left corner.
