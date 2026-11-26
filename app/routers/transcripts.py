import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..cache import list_cache
from ..db import get_db
from ..models import Transcript
from ..schemas import TranscriptCreate, TranscriptOut, TranscriptPage, TranscriptUpdate

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])

# no-cache = the browser may store the response but must revalidate (ETag -> 304).
CACHE_HEADERS = {"Cache-Control": "private, no-cache"}


@router.post("", response_model=TranscriptOut, status_code=201)
def create(payload: TranscriptCreate, db: Session = Depends(get_db)):
    obj = Transcript(text=payload.text.strip(), duration_sec=payload.duration_sec)
    db.add(obj)
    db.commit()
    list_cache.invalidate()
    return obj


@router.get("", response_model=TranscriptPage)
def list_(
    request: Request,
    response: Response,
    q: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    key = (q or "", limit, offset)
    entry = list_cache.get(key)
    if entry is None:
        stmt = select(Transcript)
        count_stmt = select(func.count()).select_from(Transcript)
        if q:
            cond = Transcript.text.ilike(f"%{q}%")
            stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
        rows = db.scalars(
            stmt.order_by(Transcript.created_at.desc()).limit(limit).offset(offset)
        ).all()
        data = {
            "items": [TranscriptOut.model_validate(r).model_dump(mode="json") for r in rows],
            "total": db.scalar(count_stmt),
        }
        etag = '"' + hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest() + '"'
        entry = (etag, data)
        list_cache.set(key, entry)
    etag, data = entry

    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, **CACHE_HEADERS})
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = CACHE_HEADERS["Cache-Control"]
    return data


@router.get("/{tid}", response_model=TranscriptOut)
def get(tid: str, db: Session = Depends(get_db)):
    obj = db.get(Transcript, tid)
    if not obj:
        raise HTTPException(404, "Transcript not found")
    return obj


@router.put("/{tid}", response_model=TranscriptOut)
def update(tid: str, payload: TranscriptUpdate, db: Session = Depends(get_db)):
    obj = db.get(Transcript, tid)
    if not obj:
        raise HTTPException(404, "Transcript not found")
    obj.text = payload.text.strip()
    db.commit()
    list_cache.invalidate()
    return obj


@router.delete("/{tid}", status_code=204)
def delete(tid: str, db: Session = Depends(get_db)):
    obj = db.get(Transcript, tid)
    if not obj:
        raise HTTPException(404, "Transcript not found")
    db.delete(obj)
    db.commit()
    list_cache.invalidate()
