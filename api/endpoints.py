from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from .db.database import Database
import logging

# logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    logger.log(msg='Working Fine!', level=1)
    return JSONResponse(
        content={"status": "healthy", "service": "Banana API"},
        status_code=200
    )
