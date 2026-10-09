"""Internal video meeting links for Ali Kuryer staff.

Links are restricted in this app, but the external Jitsi room itself uses a
shared URL rather than verified identity; do not discuss sensitive data there
until a managed/video provider with access control is configured.
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_current_user, get_db

router = APIRouter(tags=["Panels"])


def staff_user(user: models.User = Depends(get_current_user)):
    if not user.is_active or user.role not in ("admin", "courier", "restaurant"):
        raise HTTPException(403, "Faqat Ali Kuryer xodimlari uchun")
    return user


def admin_user(user: models.User = Depends(staff_user)):
    if user.role != "admin":
        raise HTTPException(403, "Faqat administrator xonani ochadi")
    return user


class MeetingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)


def meeting_public_fields(room):
    return {
        "id": room.id,
        "title": room.title,
        "join_url": "https://meet.jit.si/AliKuryer-" + room.room_code,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


@router.get("/api/panels")
def panels_status():
    return {
        "status": "ok",
        "message": "Ali Kuryer panellari API",
        "panels": ["admin", "restaurant", "courier"],
    }


@router.post("/api/panels/meetings", status_code=201)
def create_video_meeting(
    data: MeetingCreate,
    user: models.User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    room = models.VideoRoom(
        room_code=secrets.token_urlsafe(24),
        title=data.title.strip(), created_by=user.id, active=True,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return meeting_public_fields(room)


@router.get("/api/panels/meetings")
def list_video_meetings(
    user: models.User = Depends(staff_user),
    db: Session = Depends(get_db),
):
    rooms = db.query(models.VideoRoom).filter_by(active=True).order_by(
        models.VideoRoom.id.desc()
    ).limit(20).all()
    return [meeting_public_fields(r) for r in rooms]


@router.post("/api/panels/meetings/{room_id}/close")
def close_video_meeting(
    room_id: int,
    user: models.User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    room = db.get(models.VideoRoom, room_id)
    if room is None:
        raise HTTPException(404, "Xona topilmadi")
    room.active = False
    db.commit()
    return {"id": room_id, "status": "closed"}
