
from fastapi import APIRouter

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("/status")
def orders_status():
    return {
        "status": "ok",
        "message": "Ali Kuryer buyurtmalar API tayyor"
    }
