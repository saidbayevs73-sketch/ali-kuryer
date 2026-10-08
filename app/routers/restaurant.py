from fastapi import APIRouter

router = APIRouter(prefix="/api/restaurant", tags=["Restaurant"])


@router.get("/status")
def restaurant_status():
    return {
        "status": "ok",
        "message": "Ali Kuryer restoran API tayyor"
    }
  
