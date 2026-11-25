from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Transcript
from ..schemas import TranscriptCreate, TranscriptOut, TranscriptPage, TranscriptUpdate

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


@router.post("", response_model=TranscriptOut, status_code=201)
def create(payload: TranscriptCreate, db: Session = Depends(get_db)):
    obj = Transcript(text=payload.text.strip(), duration_sec=payload.duration_sec)
    db.add(obj)
    db.commit()
    return obj


@router.get("", response_model=TranscriptPage)
def list_(
    q: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Transcript)
    count_stmt = select(func.count()).select_from(Transcript)
    if q:
        cond = Transcript.text.ilike(f"%{q}%")
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
    items = db.scalars(stmt.order_by(Transcript.created_at.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": db.scalar(count_stmt)}


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
    return obj


@router.delete("/{tid}", status_code=204)
def delete(tid: str, db: Session = Depends(get_db)):
    obj = db.get(Transcript, tid)
    if not obj:
        raise HTTPException(404, "Transcript not found")
    db.delete(obj)
    db.commit()
