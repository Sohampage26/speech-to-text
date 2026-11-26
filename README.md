# Speech to Text: real-time Hindi + English transcription

A web app where you speak (Hindi, English, or a mix of both, plus 20+ other Indian languages) and see the text appear live. Transcripts can be saved and managed from a history dashboard (search, edit, delete).

**Stack:** FastAPI · Sarvam realtime STT (`saaras:v4`) · PostgreSQL (Neon) · vanilla JS · Render

## How it's designed

```
Browser (mic) ──PCM16 16 kHz──► FastAPI /ws/transcribe ──► Sarvam realtime STT
     ▲                               │                          │
     └────── partial / final text ◄──┴──────────────────────────┘

Dashboard ◄──► REST /api/transcripts ◄──► Neon PostgreSQL (+ in-memory cache)
```

- **Streaming path:** an AudioWorklet downsamples mic audio to 16 kHz PCM16 and sends ~100 ms chunks over a WebSocket. The server relays them to Sarvam and streams back interim text (shown while speaking) and final text (appended). The Sarvam key stays on the server.
- **Pluggable STT:** providers implement `STTProvider` (`app/services/stt_base.py`). `get_provider()` is the one place to swap the engine.
- **Language:** chosen in the UI and sent as `?lang=` (default `hi-IN`, handles Hindi mixed with English). It isn't stored.
- **Persistence:** the user clicks **Save** to store a transcript. CRUD is a standard REST API on one `transcripts` table (`id`, `text`, `duration_sec`, `created_at`, `updated_at`).
- **Caching:** list queries use a short in-memory TTL cache (cleared on every write) plus `ETag`/304 so repeat loads are cheap. Single instance only; swap for Redis to scale out.

```
app/
  main.py             app, static files, /health
  routers/ws.py       WebSocket streaming + /api/languages
  routers/transcripts.py   CRUD + cached list
  services/           STT interface, Sarvam provider, language list
  cache.py  db.py  models.py  schemas.py  config.py
static/               index.html, app.js, worklet.js, styles.css
```

## Run locally
```bash
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env     # then fill in DATABASE_URL and SARVAM_API_KEY
uvicorn app.main:app --reload
```
Open http://localhost:8000 (the mic works on localhost without HTTPS).

## API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/transcripts` | create |
| GET | `/api/transcripts?q=&limit=&offset=` | list / search |
| GET | `/api/transcripts/{id}` | read |
| PUT | `/api/transcripts/{id}` | update |
| DELETE | `/api/transcripts/{id}` | delete |
| GET | `/api/languages` | languages for the dropdown |
| WS | `/ws/transcribe?lang=` | send PCM16 audio, receive `partial` / `final` / `error` JSON |

## Deploy (Render + Neon)
1. Create a Neon Postgres database and copy the **pooled** connection string as `postgresql+psycopg2://…?sslmode=require` (remove `channel_binding`).
2. Push to GitHub and create a Render **Blueprint** from this repo (`render.yaml`).
3. Set `DATABASE_URL` and `SARVAM_API_KEY` in Render's environment variables.

Free-tier note: Render sleeps after ~15 minutes idle (first request takes a while). An uptime ping on `/health` keeps it awake.
