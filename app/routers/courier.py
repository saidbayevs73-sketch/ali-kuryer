
from fastapi import APIRouter

router = APIRouter(prefix="/api/courier", tags=["Courier"])


@router.get("/status")
def courier_status():
    return {
        "status": "ok",
        "message": "Ali Kuryer kuryer API tayyor"
    }
