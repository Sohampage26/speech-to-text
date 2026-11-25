# Speech to Text (Hindi + English, real-time)

Live multilingual transcription with a CRUD history dashboard.

**Stack:** FastAPI · Gemini Live API (input transcription) · PostgreSQL (Neon) · vanilla JS (AudioWorklet + WebSocket) · Render

## How it works
Browser mic → AudioWorklet (16 kHz PCM16) → `wss://…/ws/transcribe` → FastAPI → Gemini Live → live text back to the browser.
Click **Save** to store the transcript; the history table supports search, edit, delete and pagination (`/api/transcripts`).

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # fill in DATABASE_URL and GEMINI_API_KEY
uvicorn app.main:app --reload
```
Open http://localhost:8000 (mic works on localhost without HTTPS).

## API
| Method | Path | Purpose |
|---|---|---|
| POST | /api/transcripts | create |
| GET | /api/transcripts?q=&limit=&offset= | list/search |
| GET | /api/transcripts/{id} | read |
| PUT | /api/transcripts/{id} | update |
| DELETE | /api/transcripts/{id} | delete |
| WS | /ws/transcribe | stream PCM16 audio, receive `partial`/`final` JSON |

## Deploy (Render + Neon)
1. Create a Neon Postgres DB; copy the pooled connection string as `postgresql+psycopg2://…?sslmode=require`.
2. Push to GitHub, create a Render **Blueprint** from this repo (`render.yaml`).
3. Set `DATABASE_URL` and `GEMINI_API_KEY` in Render env vars.

## Notes
- Two STT providers, chosen by `STT_PROVIDER`: `chunked` (default; standard Gemini API, audio sent in ~4 s chunks to `GEMINI_STT_MODEL`) and `live` (Gemini Live API, word-by-word, needs Live API access on the key).
- STT is behind an `STTProvider` interface (`app/services/stt_base.py`), so an open-source engine such as faster-whisper can be added as another provider.
- Uses Google's dedicated `gemini-3.5-transcribe-live` model (text output, auto language detection). Sessions are capped at about 10 minutes of streaming.
