from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import Base, engine
from .routers import debug, transcripts, ws

app = FastAPI(title="Speech to Text")

# Simple bootstrap; swap for Alembic migrations when schema evolves.
Base.metadata.create_all(bind=engine)

app.include_router(transcripts.router)
app.include_router(ws.router)
app.include_router(debug.router)  # TEMP: remove before submission


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
