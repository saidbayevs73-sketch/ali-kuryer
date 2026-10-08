from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal

router = APIRouter(prefix="/api/customer", tags=["Customer"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/restaurants")
def list_restaurants(db: Session = Depends(get_db)):
    restaurants = db.query(models.Restaurant).all()
    return restaurants


@router.get("/restaurants/{restaurant_id}/menu")
def restaurant_menu(
    restaurant_id: int,
    db: Session = Depends(get_db)
):
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restoran topilmadi"
        )

    items = db.query(models.MenuItem).filter(
        models.MenuItem.restaurant_id == restaurant_id
    ).all()

    return {
        "restaurant_id": restaurant_id,
        "items": items
    }
