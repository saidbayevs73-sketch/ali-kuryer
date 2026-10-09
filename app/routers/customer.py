from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_db

router = APIRouter(prefix="/api/customer", tags=["Customer"])


@router.get("/restaurants")
def list_restaurants(db: Session = Depends(get_db)):
    # Only approved restaurants are visible to customers.
    return db.query(models.Restaurant).filter(
        models.Restaurant.is_approved.is_(True)
    ).all()


@router.get("/restaurants/{restaurant_id}/menu")
def restaurant_menu(restaurant_id: int, db: Session = Depends(get_db)):
    rest = db.get(models.Restaurant, restaurant_id)
    if rest is None or not rest.is_approved:
        raise HTTPException(404, "Tasdiqlangan oshxona topilmadi")

    items = db.query(models.MenuItem).filter(
        models.MenuItem.restaurant_id == restaurant_id,
        models.MenuItem.is_available.is_(True),
    ).all()
    extras = {
        e.menu_item_id: e for e in db.query(models.MenuExtra).filter(
            models.MenuExtra.menu_item_id.in_([i.id for i in items])
        ).all()
    }
    return {"restaurant_id": restaurant_id, "items": [
        {
            "id": item.id, "restaurant_id": item.restaurant_id,
            "name": item.name, "price": item.price,
            "image_url": item.image_url, "is_available": item.is_available,
            "category": extras[item.id].category if item.id in extras else "",
            "description": extras[item.id].description if item.id in extras else "",
        }
        for item in items
    ]}
