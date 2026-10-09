"""Protected admin complaint review and response endpoints."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def require_admin(user: models.User = Depends(get_current_user)):
    if not user.is_active or user.role != "admin":
        raise HTTPException(status_code=403, detail="Faqat administrator uchun")
    return user


class ComplaintReply(BaseModel):
    reply: str = Field(min_length=2, max_length=2000)
    status: Literal["answered", "closed"] = "answered"


@router.get("/status")
def admin_status():
    return {"status": "ok", "message": "Ali Kuryer admin API tayyor"}


@router.get("/complaints")
def list_complaints(
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    complaints = db.query(models.Complaint).order_by(models.Complaint.id.desc()).limit(200).all()
    return [{
        "id": c.id, "order_id": c.order_id, "name": c.name,
        "phone": c.phone, "message": c.message, "status": c.status,
        "reply": c.reply,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in complaints]


@router.post("/complaints/{complaint_id}/reply")
def reply_to_complaint(
    complaint_id: int,
    data: ComplaintReply,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    complaint = db.get(models.Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(404, "Murojaat topilmadi")
    complaint.reply = data.reply.strip()
    complaint.status = data.status
    db.commit()
    return {"complaint_id": complaint_id, "status": complaint.status}
