from fastapi import APIRouter

router = APIRouter(tags=["Panels"])


@router.get("/api/panels")
def panels_status():
    return {
        "status": "ok",
        "message": "Ali Kuryer panellari API",
        "panels": [
            "admin",
            "restaurant",
            "courier"
        ]
    }
